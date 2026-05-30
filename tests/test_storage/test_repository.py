"""MySQL 告警仓储集成测试

需要运行中的 MySQL（docker compose up -d mysql）才能通过。
无 MySQL 时自动跳过。
"""
from __future__ import annotations

import socket
import time

import pytest

from dormiot.schemas.alert import AlertEvent, AlertLevel
from dormiot.storage.repository import AlertRepository


def _mysql_available() -> bool:
    try:
        with socket.create_connection(("localhost", 3306), timeout=2):
            return True
    except OSError:
        return False


requires_mysql = pytest.mark.skipif(
    not _mysql_available(),
    reason="MySQL 未运行，跳过集成测试（docker compose up -d mysql）",
)


def _make_alert(
    device_id: str = "MOCK_METER_BLDG5_RM401",
    alert_type: str = "illegal_appliance",
    alert_level: AlertLevel = AlertLevel.HIGH,
    power: float = 1600.0,
) -> AlertEvent:
    return AlertEvent(
        device_id=device_id,
        building_id="5",
        room_id="401",
        alert_level=alert_level,
        alert_type=alert_type,
        trigger_value={"current_power": power},
        message=f"测试告警: {device_id}",
        timestamp=int(time.time()),
    )


@requires_mysql
class TestAlertRepository:
    def setup_method(self):
        self.repo = AlertRepository()
        self.repo.create_tables()

    def teardown_method(self):
        self.repo.close()

    def test_save_and_query(self):
        alert = _make_alert()
        alert_id = self.repo.save_alert(alert)
        assert alert_id > 0
        results = self.repo.query_alerts(device_id="MOCK_METER_BLDG5_RM401")
        assert len(results) >= 1
        assert results[0].device_id == "MOCK_METER_BLDG5_RM401"

    def test_query_by_level(self):
        self.repo.save_alert(_make_alert(alert_level=AlertLevel.HIGH))
        self.repo.save_alert(_make_alert(alert_level=AlertLevel.CRITICAL, alert_type="fire_critical"))
        results = self.repo.query_alerts(alert_level=AlertLevel.CRITICAL)
        assert all(r.alert_level == "CRITICAL" for r in results)

    def test_resolve_alert(self):
        alert_id = self.repo.save_alert(_make_alert())
        assert self.repo.resolve_alert(alert_id) is True
        results = self.repo.query_alerts(device_id="MOCK_METER_BLDG5_RM401", resolved=True)
        assert len(results) >= 1

    def test_resolve_nonexistent(self):
        assert self.repo.resolve_alert(999999) is False

    def test_count_unresolved(self):
        self.repo.save_alert(_make_alert())
        count = self.repo.count_unresolved()
        assert count >= 1

    def test_query_with_time_range(self):
        now = int(time.time())
        self.repo.save_alert(_make_alert())
        results = self.repo.query_alerts(since=now - 10, until=now + 10)
        assert len(results) >= 1
