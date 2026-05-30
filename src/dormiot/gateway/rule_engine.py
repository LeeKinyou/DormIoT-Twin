from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from loguru import logger

from dormiot.config import settings
from dormiot.schemas.alert import AlertEvent, AlertLevel
from dormiot.schemas.device import MeterReport


@dataclass
class Rule:
    """单条告警规则"""

    name: str
    alert_type: str
    alert_level: AlertLevel
    check: Callable[[MeterReport], bool]
    message_tpl: str
    trigger_tpl: Callable[[MeterReport], dict]


@dataclass
class RuleEngine:
    """规则引擎：对每条 MeterReport 评估告警规则

    内置三条规则：
    1. 功率 >1500W → 违章电器 (HIGH)
    2. 功率 >800W  → 恶性负载 (MEDIUM)
    3. 烟雾 >0.40  → 火灾特级 (CRITICAL)

    同设备同类告警有冷却时间（默认 60s），避免重复触发。
    """

    power_illegal: float = field(default_factory=lambda: settings.power_threshold_illegal)
    power_overload: float = field(default_factory=lambda: settings.power_threshold_overload)
    smoke_critical: float = field(default_factory=lambda: settings.smoke_threshold_critical)
    cooldown_seconds: int = 60

    def __post_init__(self) -> None:
        self._last_alert: dict[str, float] = {}  # key: "{device_id}:{alert_type}" → timestamp
        self._rules: list[Rule] = [
            Rule(
                name="违章电器",
                alert_type="illegal_appliance",
                alert_level=AlertLevel.HIGH,
                check=lambda r: r.metrics.current_power > self.power_illegal,
                message_tpl="宿舍 {device_id} 检测到违章电器，当前功率 {power:.0f}W 超过阈值 {threshold:.0f}W",
                trigger_tpl=lambda r: {"current_power": r.metrics.current_power, "threshold": self.power_illegal},
            ),
            Rule(
                name="恶性负载",
                alert_type="overload",
                alert_level=AlertLevel.MEDIUM,
                check=lambda r: r.metrics.current_power > self.power_overload,
                message_tpl="宿舍 {device_id} 负载过高，当前功率 {power:.0f}W 超过阈值 {threshold:.0f}W",
                trigger_tpl=lambda r: {"current_power": r.metrics.current_power, "threshold": self.power_overload},
            ),
            Rule(
                name="火灾特级",
                alert_type="fire_critical",
                alert_level=AlertLevel.CRITICAL,
                check=lambda r: r.metrics.smoke_density > self.smoke_critical,
                message_tpl="宿舍 {device_id} 烟雾浓度 {smoke:.2f}ppm 超过阈值 {threshold:.2f}ppm，疑似火灾",
                trigger_tpl=lambda r: {"smoke_density": r.metrics.smoke_density, "threshold": self.smoke_critical},
            ),
        ]

    def _is_cooling(self, device_id: str, alert_type: str) -> bool:
        key = f"{device_id}:{alert_type}"
        last = self._last_alert.get(key, 0)
        return (time.time() - last) < self.cooldown_seconds

    def _record_alert(self, device_id: str, alert_type: str) -> None:
        key = f"{device_id}:{alert_type}"
        self._last_alert[key] = time.time()

    def evaluate(self, report: MeterReport) -> list[AlertEvent]:
        """评估一条上报数据，返回触发的告警列表（可能为空）"""
        alerts: list[AlertEvent] = []
        # 解析 device_id 获取 building/room: MOCK_METER_BLDG5_RM401
        parts = report.device_id.split("_")
        building_id = parts[2].replace("BLDG", "") if len(parts) > 2 else ""
        room_id = parts[3].replace("RM", "") if len(parts) > 3 else ""

        for rule in self._rules:
            if not rule.check(report):
                continue
            if self._is_cooling(report.device_id, rule.alert_type):
                continue

            self._record_alert(report.device_id, rule.alert_type)
            alert = AlertEvent(
                device_id=report.device_id,
                building_id=building_id,
                room_id=room_id,
                alert_level=rule.alert_level,
                alert_type=rule.alert_type,
                trigger_value=rule.trigger_tpl(report),
                message=rule.message_tpl.format(
                    device_id=report.device_id,
                    power=report.metrics.current_power,
                    smoke=report.metrics.smoke_density,
                    threshold=self.power_illegal if "illegal" in rule.alert_type else (
                        self.smoke_critical if "fire" in rule.alert_type else self.power_overload
                    ),
                ),
                timestamp=report.timestamp,
            )
            alerts.append(alert)
            logger.warning(f"规则引擎触发告警: {alert.alert_type} - {alert.device_id}")

        return alerts

    def reset_cooldown(self) -> None:
        """清除所有冷却记录"""
        self._last_alert.clear()
