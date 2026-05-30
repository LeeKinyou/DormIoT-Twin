from __future__ import annotations

from enum import Enum
from typing import Callable

from dormiot.schemas.device import DeviceStatus


class StateTransition:
    """状态转换规则"""

    def __init__(self, target: DeviceStatus, condition: Callable[[], bool]):
        self.target = target
        self.condition = condition


class DeviceStateMachine:
    """设备状态机，管理 NORMAL → WARNING → ALARM 的状态转换

    支持两种触发方式：
    1. 外部指令：调用 force_state() 强制切换
    2. 条件自动：基于当前指标值自动判断转换
    """

    def __init__(self) -> None:
        self._state = DeviceStatus.NORMAL
        self._transitions: dict[DeviceStatus, list[StateTransition]] = {
            DeviceStatus.NORMAL: [
                StateTransition(DeviceStatus.WARNING, lambda: self._should_warn),
                StateTransition(DeviceStatus.ALARM, lambda: self._should_alarm),
            ],
            DeviceStatus.WARNING: [
                StateTransition(DeviceStatus.ALARM, lambda: self._should_alarm),
                StateTransition(DeviceStatus.NORMAL, lambda: not self._should_warn and not self._should_alarm),
            ],
            DeviceStatus.ALARM: [
                StateTransition(DeviceStatus.NORMAL, lambda: not self._should_alarm),
            ],
        }
        self._should_warn = False
        self._should_alarm = False

    @property
    def state(self) -> DeviceStatus:
        return self._state

    def update_signals(self, *, warning: bool = False, alarm: bool = False) -> None:
        """更新外部信号，供条件自动转换判断使用"""
        self._should_warn = warning
        self._should_alarm = alarm

    def tick(self) -> DeviceStatus:
        """执行一次状态转换判断，返回转换后的状态"""
        for transition in self._transitions.get(self._state, []):
            if transition.condition():
                self._state = transition.target
                break
        return self._state

    def force_state(self, state: DeviceStatus) -> None:
        """强制切换到指定状态（用于异常注入）"""
        self._state = state

    def reset(self) -> None:
        """重置为 NORMAL"""
        self._state = DeviceStatus.NORMAL
        self._should_warn = False
        self._should_alarm = False
