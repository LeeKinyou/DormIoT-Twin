"""MQTT 协议仿真层 —— 内存 pub/sub 模拟 Broker

在不依赖外部 EMQX 的情况下，保留 MQTT 的协议语义和 Topic 设计。
用于演示"设备发布 → Broker 路由 → 应用层订阅"的物联网数据流。
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable


class MQTTTopic:
    """MQTT Topic 常量定义（标准宿舍物联网 Topic 设计）"""

    # 设备上报
    METER_REPORT = "dormiot/campus/{building}/{room}/meter"  # 电表数据
    SMOKE_REPORT = "dormiot/campus/{building}/{room}/smoke"  # 烟雾传感器
    DEVICE_STATUS = "dormiot/campus/{building}/{room}/status"  # 设备状态

    # 云端下发
    COMMAND = "dormiot/campus/{building}/{room}/command"  # 控制指令
    ALARM = "dormiot/alarm/{building}/{room}"  # 告警推送

    # 系统级
    SYSTEM_HEARTBEAT = "dormiot/system/heartbeat"  # 心跳
    SYSTEM_BROADCAST = "dormiot/system/broadcast"  # 广播


class MQTTBroker:
    """内存 MQTT Broker（线程安全单例）

    模拟 MQTT Broker 的核心功能：
    - publish(): 发布消息到指定 Topic
    - subscribe(): 订阅 Topic（支持 + 和 # 通配符）
    - get_recent_messages(): 获取最近的消息日志
    """

    _instance: MQTTBroker | None = None
    _lock = threading.Lock()
    _MAX_LOG = 100  # 消息日志上限

    def __new__(cls) -> MQTTBroker:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers: dict[str, list[Callable]] = defaultdict(list)
                cls._instance._message_log: list[dict[str, Any]] = []
                cls._instance._data_lock = threading.Lock()
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例（用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                with cls._instance._data_lock:
                    cls._instance._subscribers.clear()
                    cls._instance._message_log.clear()
                cls._instance = None

    def publish(self, topic: str, payload: dict[str, Any], qos: int = 0) -> None:
        """模拟 MQTT 发布

        Args:
            topic: MQTT Topic 字符串
            payload: 消息载荷（字典）
            qos: 服务质量等级（仿真中仅记录，不实际投递）
        """
        message = {"topic": topic, "payload": payload, "qos": qos}

        with self._data_lock:
            self._message_log.append(message)
            if len(self._message_log) > self._MAX_LOG:
                self._message_log.pop(0)

        # 通知匹配的订阅者
        for pattern, callbacks in list(self._subscribers.items()):
            if self._topic_matches(topic, pattern):
                for callback in callbacks:
                    try:
                        callback(topic, payload)
                    except Exception:
                        pass  # 回调异常不影响 Broker

    def subscribe(self, topic_pattern: str, callback: Callable[[str, dict], None]) -> None:
        """模拟 MQTT 订阅

        Args:
            topic_pattern: Topic 模式（支持 + 单层通配和 # 多层通配）
            callback: 收到匹配消息时的回调函数 (topic, payload) -> None
        """
        with self._data_lock:
            self._subscribers[topic_pattern].append(callback)

    def get_recent_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取最近的消息日志（用于 UI 展示）

        Args:
            limit: 返回的最大消息数

        Returns:
            最近的消息列表，每条包含 topic/payload/qos
        """
        with self._data_lock:
            return list(self._message_log[-limit:])

    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        """Topic 匹配（支持 + 和 # 通配符）

        规则：
        - '#' 匹配任意层级的后续所有内容（多层通配）
        - '+' 匹配单个层级
        - 其他为精确匹配

        Args:
            topic: 实际 Topic
            pattern: 订阅模式

        Returns:
            是否匹配
        """
        if pattern.endswith("#"):
            prefix = pattern[:-2]  # 去掉 "/#"
            return topic.startswith(prefix)

        topic_parts = topic.split("/")
        pattern_parts = pattern.split("/")

        if len(topic_parts) != len(pattern_parts):
            return False

        for t_part, p_part in zip(topic_parts, pattern_parts):
            if p_part == "+":
                continue  # 单层通配，匹配任意
            if t_part != p_part:
                return False

        return True
