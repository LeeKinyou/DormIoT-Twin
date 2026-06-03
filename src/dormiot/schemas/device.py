from __future__ import annotations

import time
from enum import Enum

from pydantic import BaseModel, Field


class DeviceStatus(str, Enum):
    """设备自检状态"""

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    ALARM = "ALARM"
    ALARM_RESISTOR = "ALARM_RESISTOR"    # 热得快/吹风机
    ALARM_MICROWAVE = "ALARM_MICROWAVE"  # 微波炉


class MetricsSnapshot(BaseModel):
    """单次采集的设备指标快照"""

    current_power: float = Field(..., description="当前宿舍总功率 (W)", ge=0)
    voltage: float = Field(..., description="当前供电电压 (V)", ge=0, le=300)
    smoke_density: float = Field(..., description="烟雾浓度探测值 (ppm)", ge=0)


class MeterReport(BaseModel):
    """虚拟/物理节点上报的标准数据格式"""

    device_id: str = Field(..., description="设备唯一标识，全局唯一", min_length=1)
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="秒级 UNIX 时间戳")
    metrics: MetricsSnapshot
    status: DeviceStatus = DeviceStatus.NORMAL
