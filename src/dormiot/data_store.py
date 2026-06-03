"""内存驱动的数据存储层

提供线程安全的波形数据队列和后台采集线程，替代原有的 MQTT/Redis/MySQL 管线。
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from dormiot.simulation.synthesizer import WaveformSynthesizer


class DataStore:
    """线程安全的波形数据存储（单例）

    内部维护一个 deque（最多保留 60 个 tick），每个 tick 是一个
    {room_id: {power, voltage, smoke_density, status}} 字典。
    """

    _instance: DataStore | None = None
    _lock = threading.Lock()
    MAX_HISTORY = 60  # 最多保留 60 秒

    def __new__(cls) -> DataStore:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._history: deque[dict[str, dict[str, Any]]] = deque(maxlen=self.MAX_HISTORY)
        self._data_lock = threading.Lock()

    def reset(self) -> None:
        """清空所有数据"""
        with self._data_lock:
            self._history.clear()

    def push_tick(self, tick_data: dict[str, dict[str, Any]]) -> None:
        """推入一个 tick 的数据

        Args:
            tick_data: {room_id: {power, voltage, smoke_density, status}}
        """
        with self._data_lock:
            self._history.append(tick_data)

    @property
    def history_length(self) -> int:
        """当前历史记录数"""
        with self._data_lock:
            return len(self._history)

    @property
    def latest_snapshot(self) -> dict[str, dict[str, Any]]:
        """返回最新一个 tick 的数据，无数据时返回空字典"""
        with self._data_lock:
            if not self._history:
                return {}
            return dict(self._history[-1])

    def get_room_history(self, room_id: str) -> list[dict[str, Any]]:
        """获取指定房间的历史数据序列

        Returns:
            按时间排列的该房间每次 tick 的数据列表
        """
        with self._data_lock:
            return [
                tick[room_id]
                for tick in self._history
                if room_id in tick
            ]

    def get_power_array(self, room_id: str) -> list[float]:
        """获取指定房间的功率数组（用于波形分析/LLM 研判）

        Returns:
            功率值列表，按时间排列
        """
        with self._data_lock:
            return [
                tick[room_id]["power"]
                for tick in self._history
                if room_id in tick
            ]

    def detect_power_spike(
        self, room_id: str, threshold: float = 1000.0, window: int = 2
    ) -> bool:
        """检测功率飙升

        判断最近 window 个 tick 内，功率是否飙升超过 threshold。

        Args:
            room_id: 房间号
            threshold: 飙升阈值（W）
            window: 检测窗口（tick 数）

        Returns:
            是否检测到飙升
        """
        with self._data_lock:
            if len(self._history) < window + 1:
                return False

            # 取最近 window+1 个 tick 中该房间的功率
            recent = []
            for tick in list(self._history)[-(window + 1):]:
                if room_id in tick:
                    recent.append(tick[room_id]["power"])

            if len(recent) < window + 1:
                return False

            # 检查是否有超过 threshold 的差值
            old_power = min(recent[:-1])  # 窗口内的最低功率
            new_power = recent[-1]        # 最新功率
            return (new_power - old_power) > threshold


class BackgroundCollector:
    """后台数据采集守护线程

    每隔 interval_s 秒调用 WaveformSynthesizer 获取所有房间数据，
    并推入 DataStore。
    """

    def __init__(self, interval_s: float = 1.0) -> None:
        self._interval_s = interval_s
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._synth = WaveformSynthesizer()
        self._store = DataStore()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    @property
    def thread(self) -> threading.Thread | None:
        return self._thread

    def start(self) -> None:
        """启动采集线程"""
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(
            target=self._collect_loop,
            daemon=True,
            name="bg-collector",
        )
        self._thread.start()

    def stop(self) -> None:
        """停止采集线程"""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_s * 2)
            self._thread = None

    def _collect_loop(self) -> None:
        """采集主循环"""
        while self._running.is_set():
            try:
                tick_data = self._synth.get_next_tick()
                self._store.push_tick(tick_data)
            except Exception:
                pass  # 采集失败不影响后续循环
            time.sleep(self._interval_s)
