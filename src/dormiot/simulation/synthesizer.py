"""物理波形合成引擎

用 Numpy 合成真实电表数据，替代原有的简单高斯噪声。
支持三种模式：
- NORMAL：基准负载 + 昼夜节律正弦波
- ALARM_RESISTOR：热得快/吹风机 — 瞬间叠加 1800W + 高频毛刺
- ALARM_MICROWAVE：微波炉 — 方波交替 +1200W / +30W
"""
from __future__ import annotations

import threading
import numpy as np

from dormiot.schemas.device import DeviceStatus
from dormiot.config import settings


class WaveformSynthesizer:
    """物理波形合成器（线程安全单例）

    每次调用 get_next_tick() 返回所有宿舍当前时刻的波形数据点。
    支持多楼层、多房间配置。
    内部维护一个全局时钟（tick_count），用于合成昼夜节律和方波周期。
    """

    _instance: WaveformSynthesizer | None = None
    _lock = threading.Lock()

    # ── 物理参数 ──
    BASE_POWER = 50.0        # 基准功率 (W)
    BASE_VOLTAGE = 220.0     # 基准电压 (V)
    BASE_SMOKE = 0.01        # 基准烟雾浓度 (ppm)

    # NORMAL 模式噪声
    NORMAL_POWER_STD = 2.0
    NORMAL_VOLTAGE_STD = 0.5
    NORMAL_SMOKE_STD = 0.005

    # ALARM_RESISTOR 模式
    RESISTOR_OFFSET = 1800.0     # 叠加功率 (W)
    RESISTOR_NOISE_STD = 40.0    # 高频毛刺标准差

    # ALARM_MICROWAVE 模式
    MICROWAVE_HIGH_OFFSET = 1200.0  # 高电平叠加 (W)
    MICROWAVE_LOW_OFFSET = 30.0     # 低电平叠加 (W)
    MICROWAVE_PERIOD = 10            # 方波周期（秒）：5秒高 + 5秒低

    # 昼夜节律
    CIRCADIAN_AMPLITUDE = 5.0    # 正弦波振幅 (W)
    CIRCADIAN_PERIOD = 240       # 正弦波周期（秒，压缩到4分钟模拟一天）

    def __new__(cls) -> WaveformSynthesizer:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._tick_count = 0
        self._alarm_modes: dict[str, DeviceStatus] = {}
        self._rng = np.random.default_rng()
        self._room_lock = threading.Lock()

        # 生成所有房间 ID：楼层号 + 房间号（如 101, 102, ..., 620）
        self.ROOMS = []
        for floor in range(1, settings.building_floors + 1):
            for room in range(1, settings.rooms_per_floor + 1):
                self.ROOMS.append(f"{floor}{room:02d}")

    @property
    def floors(self) -> list[int]:
        """返回楼层列表"""
        return list(range(1, settings.building_floors + 1))

    @property
    def rooms_per_floor(self) -> int:
        """返回每层房间数"""
        return settings.rooms_per_floor

    def get_rooms_on_floor(self, floor: int) -> list[str]:
        """获取指定楼层的所有房间 ID"""
        return [r for r in self.ROOMS if r.startswith(str(floor))]

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def reset(self) -> None:
        """重置合成器状态"""
        with self._room_lock:
            self._tick_count = 0
            self._alarm_modes.clear()

    def set_alarm_mode(self, room_id: str, mode: DeviceStatus) -> bool:
        """设置房间告警模式

        Args:
            room_id: 房间号（如 "101"）
            mode: ALARM_RESISTOR 或 ALARM_MICROWAVE

        Returns:
            是否设置成功
        """
        if room_id not in self.ROOMS:
            return False
        with self._room_lock:
            self._alarm_modes[room_id] = mode
        return True

    def clear_alarm_mode(self, room_id: str) -> None:
        """清除房间告警模式，恢复 NORMAL"""
        with self._room_lock:
            self._alarm_modes.pop(room_id, None)

    def get_next_tick(self) -> dict[str, dict]:
        """获取下一个时间步的所有房间波形数据

        Returns:
            字典，key 为房间号（"101"-"106"），value 包含 power/voltage/smoke_density/status
        """
        with self._room_lock:
            tick = self._tick_count
            self._tick_count += 1
            modes = dict(self._alarm_modes)

        # 昼夜节律：低频正弦波
        circadian = self.CIRCADIAN_AMPLITUDE * np.sin(
            2 * np.pi * tick / self.CIRCADIAN_PERIOD
        )

        result = {}
        for room_id in self.ROOMS:
            mode = modes.get(room_id, DeviceStatus.NORMAL)
            result[room_id] = self._synthesize_room(room_id, mode, tick, circadian)

        return result

    def _synthesize_room(
        self, room_id: str, mode: DeviceStatus, tick: int, circadian: float
    ) -> dict:
        """合成单个房间的波形数据"""
        if mode == DeviceStatus.NORMAL:
            return self._synth_normal(circadian)
        elif mode == DeviceStatus.ALARM_RESISTOR:
            return self._synth_resistor(circadian)
        elif mode == DeviceStatus.ALARM_MICROWAVE:
            return self._synth_microwave(circadian, tick)
        else:
            # WARNING / ALARM 等其他状态，按 NORMAL 处理
            return self._synth_normal(circadian)

    def _synth_normal(self, circadian: float) -> dict:
        """正常模式：基准 + 微小噪声 + 昼夜节律"""
        power = self.BASE_POWER + circadian + self._rng.normal(0, self.NORMAL_POWER_STD)
        voltage = self.BASE_VOLTAGE + self._rng.normal(0, self.NORMAL_VOLTAGE_STD)
        smoke = self.BASE_SMOKE + self._rng.normal(0, self.NORMAL_SMOKE_STD)
        return {
            "power": round(max(0, power), 1),
            "voltage": round(np.clip(voltage, 200, 240), 1),
            "smoke_density": round(max(0, smoke), 4),
            "status": DeviceStatus.NORMAL,
        }

    def _synth_resistor(self, circadian: float) -> dict:
        """热得快/吹风机模式：基准 + 1800W + 高频毛刺"""
        power = (
            self.BASE_POWER
            + circadian
            + self.RESISTOR_OFFSET
            + self._rng.normal(0, self.RESISTOR_NOISE_STD)
        )
        voltage = self.BASE_VOLTAGE + self._rng.normal(0, 1.5)
        smoke = self.BASE_SMOKE + self._rng.normal(0, 0.02)
        return {
            "power": round(max(0, power), 1),
            "voltage": round(np.clip(voltage, 190, 240), 1),
            "smoke_density": round(max(0, smoke), 4),
            "status": DeviceStatus.ALARM_RESISTOR,
        }

    def _synth_microwave(self, circadian: float, tick: int) -> dict:
        """微波炉模式：方波交替 +1200W / +30W（每5秒切换）"""
        # 方波：前 5 秒高电平，后 5 秒低电平
        phase_in_period = tick % self.MICROWAVE_PERIOD
        if phase_in_period < 5:
            offset = self.MICROWAVE_HIGH_OFFSET
        else:
            offset = self.MICROWAVE_LOW_OFFSET

        power = self.BASE_POWER + circadian + offset + self._rng.normal(0, 2)
        voltage = self.BASE_VOLTAGE + self._rng.normal(0, 1.0)
        smoke = self.BASE_SMOKE + self._rng.normal(0, 0.01)
        return {
            "power": round(max(0, power), 1),
            "voltage": round(np.clip(voltage, 200, 240), 1),
            "smoke_density": round(max(0, smoke), 4),
            "status": DeviceStatus.ALARM_MICROWAVE,
        }
