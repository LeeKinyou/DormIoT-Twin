from __future__ import annotations

from dataclasses import dataclass, field

from dormiot.schemas.device import DeviceStatus
from dormiot.simulation.device import DeviceConfig, VirtualIoTDevice


@dataclass
class ClusterConfig:
    """仿真集群配置"""

    buildings: dict[str, list[str]] = field(default_factory=lambda: {
        "5": [f"{i}" for i in range(401, 407)],   # 5号楼 4层 6间
        "6": [f"{i}" for i in range(401, 407)],   # 6号楼 4层 6间
        "12": [f"{i}" for i in range(301, 307)],  # 12号楼 3层 6间
        "13": [f"{i}" for i in range(301, 307)],  # 13号楼 3层 6间
    })
    report_interval_s: float = 1.0


class SimulationCluster:
    """仿真集群编排器

    管理全校虚拟电表设备的批量创建、启停和异常注入。
    """

    def __init__(self, config: ClusterConfig | None = None) -> None:
        self._config = config or ClusterConfig()
        self._devices: dict[str, VirtualIoTDevice] = {}
        self._build_devices()

    def _build_devices(self) -> None:
        """根据集群配置批量创建虚拟设备"""
        for building_id, rooms in self._config.buildings.items():
            for room_id in rooms:
                device_config = DeviceConfig(
                    building_id=building_id,
                    room_id=room_id,
                    report_interval_s=self._config.report_interval_s,
                )
                device = VirtualIoTDevice(device_config)
                self._devices[device.device_id] = device

    @property
    def devices(self) -> dict[str, VirtualIoTDevice]:
        return self._devices

    @property
    def device_count(self) -> int:
        return len(self._devices)

    def get_device(self, device_id: str) -> VirtualIoTDevice | None:
        return self._devices.get(device_id)

    def generate_all(self) -> list:
        """所有设备各生成一次数据，返回 MeterReport 列表"""
        return [device.generate_metrics() for device in self._devices.values()]

    def inject_anomaly(self, device_id: str, state: DeviceStatus) -> bool:
        """向指定设备注入异常状态，返回是否成功"""
        device = self._devices.get(device_id)
        if device is None:
            return False
        device.force_state(state)
        return True

    def reset_all(self) -> None:
        """重置所有设备为 NORMAL 状态"""
        for device in self._devices.values():
            device.force_state(DeviceStatus.NORMAL)
