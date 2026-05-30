from __future__ import annotations

from dataclasses import dataclass, field

from dormiot.schemas.device import DeviceStatus, MetricsSnapshot, MeterReport
from dormiot.simulation.noise import noisy_value
from dormiot.simulation.state_machine import DeviceStateMachine


@dataclass
class DeviceConfig:
    """虚拟设备配置"""

    building_id: str
    room_id: str
    baseline_power: float = 50.0       # 基准功率 (W)：日光灯 + 充电器
    baseline_voltage: float = 220.0    # 基准电压 (V)
    baseline_smoke: float = 0.01       # 基准烟雾浓度 (ppm)
    noise_std_power: float = 2.0       # 功率高斯噪声标准差
    noise_std_voltage: float = 0.5     # 电压高斯噪声标准差
    noise_std_smoke: float = 0.005     # 烟雾高斯噪声标准差
    report_interval_s: float = 1.0     # 上报周期 (秒)


class VirtualIoTDevice:
    """单个宿舍虚拟电表设备

    每个设备独立生成仿真数据，包含：
    - 常态：基准值 + 高斯噪声
    - WARNING：功率略升（800-1500W）
    - ALARM：功率飙升（>1500W）或烟雾浓度飙升
    """

    def __init__(self, config: DeviceConfig) -> None:
        self.config = config
        self.device_id = f"MOCK_METER_BLDG{config.building_id}_RM{config.room_id}"
        self.topic = f"dormiot/campus/{config.building_id}/{config.room_id}/meter"
        self._sm = DeviceStateMachine()

    @property
    def state(self) -> DeviceStatus:
        return self._sm.state

    def force_state(self, state: DeviceStatus) -> None:
        """强制切换设备状态（用于异常注入）"""
        self._sm.force_state(state)

    def generate_metrics(self) -> MeterReport:
        """生成一次仿真数据，返回标准 MeterReport"""
        cfg = self.config

        # 根据状态机决定指标范围
        match self._sm.state:
            case DeviceStatus.NORMAL:
                power = noisy_value(cfg.baseline_power, cfg.noise_std_power, min_val=0)
                voltage = noisy_value(cfg.baseline_voltage, cfg.noise_std_voltage, min_val=200, max_val=240)
                smoke = noisy_value(cfg.baseline_smoke, cfg.noise_std_smoke, min_val=0)

            case DeviceStatus.WARNING:
                power = noisy_value(1000.0, 100.0, min_val=800, max_val=1500)
                voltage = noisy_value(218.0, 1.0, min_val=200, max_val=240)
                smoke = noisy_value(0.05, 0.01, min_val=0)

            case DeviceStatus.ALARM:
                power = noisy_value(2000.0, 300.0, min_val=1500)
                voltage = noisy_value(210.0, 3.0, min_val=190, max_val=240)
                smoke = noisy_value(0.50, 0.10, min_val=0.30)

        # 更新状态机信号
        self._sm.update_signals(warning=power > 800, alarm=power > 1500 or smoke > 0.40)
        self._sm.tick()

        return MeterReport(
            device_id=self.device_id,
            metrics=MetricsSnapshot(
                current_power=round(power, 1),
                voltage=round(voltage, 1),
                smoke_density=round(smoke, 3),
            ),
            status=self._sm.state,
        )
