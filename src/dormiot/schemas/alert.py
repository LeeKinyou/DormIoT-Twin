from __future__ import annotations

import time
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    """告警级别"""

    CRITICAL = "CRITICAL"  # 火灾特级
    HIGH = "HIGH"  # 违章电器
    MEDIUM = "MEDIUM"  # 恶性负载


class AlertEvent(BaseModel):
    """规则引擎生成的告警事件"""

    device_id: str = Field(..., description="触发告警的设备 ID")
    building_id: str = Field(..., description="楼栋号")
    room_id: str = Field(..., description="房间号")
    alert_level: AlertLevel
    alert_type: str = Field(..., description="告警类型码，如 fire_critical / illegal_appliance")
    trigger_value: dict = Field(default_factory=dict, description="触发时的指标快照")
    message: str = Field(..., description="告警描述")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="告警触发时间戳")
    resolved: bool = False
    resolved_at: datetime | None = None
