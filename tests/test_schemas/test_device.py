import pytest
from pydantic import ValidationError

from dormiot.schemas.device import DeviceStatus, MetricsSnapshot, MeterReport


class TestMetricsSnapshot:
    def test_valid_metrics(self):
        m = MetricsSnapshot(current_power=245.3, voltage=220.1, smoke_density=0.02)
        assert m.current_power == 245.3
        assert m.voltage == 220.1
        assert m.smoke_density == 0.02

    def test_zero_values_allowed(self):
        m = MetricsSnapshot(current_power=0, voltage=0, smoke_density=0)
        assert m.current_power == 0

    def test_negative_power_rejected(self):
        with pytest.raises(ValidationError):
            MetricsSnapshot(current_power=-1, voltage=220, smoke_density=0)

    def test_negative_smoke_rejected(self):
        with pytest.raises(ValidationError):
            MetricsSnapshot(current_power=100, voltage=220, smoke_density=-0.1)

    def test_voltage_over_300_rejected(self):
        with pytest.raises(ValidationError):
            MetricsSnapshot(current_power=100, voltage=301, smoke_density=0)


class TestDeviceStatus:
    def test_enum_values(self):
        assert DeviceStatus.NORMAL == "NORMAL"
        assert DeviceStatus.WARNING == "WARNING"
        assert DeviceStatus.ALARM == "ALARM"


class TestMeterReport:
    def test_valid_report(self):
        report = MeterReport(
            device_id="MOCK_METER_BLDG5_RM402",
            timestamp=1716987600,
            metrics=MetricsSnapshot(current_power=2150.5, voltage=220.4, smoke_density=0.02),
            status=DeviceStatus.NORMAL,
        )
        assert report.device_id == "MOCK_METER_BLDG5_RM402"
        assert report.timestamp == 1716987600
        assert report.status == DeviceStatus.NORMAL

    def test_default_status_is_normal(self):
        report = MeterReport(
            device_id="MOCK_METER_BLDG5_RM402",
            metrics=MetricsSnapshot(current_power=100, voltage=220, smoke_density=0),
        )
        assert report.status == DeviceStatus.NORMAL

    def test_default_timestamp_auto_generated(self):
        report = MeterReport(
            device_id="MOCK_METER_BLDG5_RM402",
            metrics=MetricsSnapshot(current_power=100, voltage=220, smoke_density=0),
        )
        assert report.timestamp > 0

    def test_empty_device_id_rejected(self):
        with pytest.raises(ValidationError):
            MeterReport(
                device_id="",
                metrics=MetricsSnapshot(current_power=100, voltage=220, smoke_density=0),
            )

    def test_missing_metrics_rejected(self):
        with pytest.raises(ValidationError):
            MeterReport(device_id="TEST")

    def test_json_roundtrip(self):
        report = MeterReport(
            device_id="MOCK_METER_BLDG5_RM402",
            timestamp=1716987600,
            metrics=MetricsSnapshot(current_power=2150.5, voltage=220.4, smoke_density=0.02),
        )
        json_str = report.model_dump_json()
        restored = MeterReport.model_validate_json(json_str)
        assert restored == report
