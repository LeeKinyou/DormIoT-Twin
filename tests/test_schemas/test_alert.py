import pytest
from pydantic import ValidationError

from dormiot.schemas.alert import AlertEvent, AlertLevel


class TestAlertLevel:
    def test_enum_values(self):
        assert AlertLevel.CRITICAL == "CRITICAL"
        assert AlertLevel.HIGH == "HIGH"
        assert AlertLevel.MEDIUM == "MEDIUM"


class TestAlertEvent:
    def test_valid_alert(self):
        alert = AlertEvent(
            device_id="MOCK_METER_BLDG5_RM402",
            building_id="5",
            room_id="402",
            alert_level=AlertLevel.HIGH,
            alert_type="illegal_appliance",
            trigger_value={"current_power": 2150.5},
            message="违章电器：BLDG5_RM402 功率 2150.5W 超限",
        )
        assert alert.device_id == "MOCK_METER_BLDG5_RM402"
        assert alert.alert_level == AlertLevel.HIGH
        assert alert.resolved is False
        assert alert.resolved_at is None

    def test_default_timestamp(self):
        alert = AlertEvent(
            device_id="TEST",
            building_id="1",
            room_id="101",
            alert_level=AlertLevel.MEDIUM,
            alert_type="sustained_overload",
            message="test",
        )
        assert alert.timestamp > 0

    def test_json_roundtrip(self):
        alert = AlertEvent(
            device_id="MOCK_METER_BLDG5_RM402",
            building_id="5",
            room_id="402",
            alert_level=AlertLevel.CRITICAL,
            alert_type="fire_critical",
            trigger_value={"smoke_density": 0.45},
            message="火灾特级警报",
        )
        json_str = alert.model_dump_json()
        restored = AlertEvent.model_validate_json(json_str)
        assert restored == alert
