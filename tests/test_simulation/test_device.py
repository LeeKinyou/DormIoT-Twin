from dormiot.schemas.device import DeviceStatus, MeterReport
from dormiot.simulation.device import DeviceConfig, VirtualIoTDevice


class TestVirtualIoTDevice:
    def _make_device(self, building_id="5", room_id="401") -> VirtualIoTDevice:
        return VirtualIoTDevice(DeviceConfig(building_id=building_id, room_id=room_id))

    def test_device_id_format(self):
        device = self._make_device("5", "401")
        assert device.device_id == "MOCK_METER_BLDG5_RM401"

    def test_topic_format(self):
        device = self._make_device("5", "401")
        assert device.topic == "dormiot/campus/5/401/meter"

    def test_initial_state_is_normal(self):
        device = self._make_device()
        assert device.state == DeviceStatus.NORMAL

    def test_generate_returns_meter_report(self):
        device = self._make_device()
        report = device.generate_metrics()
        assert isinstance(report, MeterReport)
        assert report.device_id == device.device_id
        assert report.status in (DeviceStatus.NORMAL, DeviceStatus.WARNING, DeviceStatus.ALARM)

    def test_normal_metrics_range(self):
        device = self._make_device()
        for _ in range(100):
            report = device.generate_metrics()
            # 正常态功率应在基准值附近
            assert 0 < report.metrics.current_power < 200
            assert 200 < report.metrics.voltage < 240
            assert 0 <= report.metrics.smoke_density < 0.1

    def test_alarm_metrics_elevated(self):
        device = self._make_device()
        device.force_state(DeviceStatus.ALARM)
        report = device.generate_metrics()
        assert report.metrics.current_power > 1500
        assert report.metrics.smoke_density > 0.30

    def test_warning_metrics_elevated(self):
        device = self._make_device()
        device.force_state(DeviceStatus.WARNING)
        report = device.generate_metrics()
        assert 800 <= report.metrics.current_power <= 1500

    def test_force_state(self):
        device = self._make_device()
        device.force_state(DeviceStatus.ALARM)
        assert device.state == DeviceStatus.ALARM

    def test_json_serializable(self):
        device = self._make_device()
        report = device.generate_metrics()
        json_str = report.model_dump_json()
        restored = MeterReport.model_validate_json(json_str)
        assert restored.device_id == report.device_id
