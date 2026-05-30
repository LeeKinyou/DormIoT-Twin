"""Redis 缓存集成测试

需要运行中的 Redis（docker compose up -d redis）才能通过。
无 Redis 时自动跳过。
"""
from __future__ import annotations

import socket
import time

import pytest

from dormiot.schemas.device import DeviceStatus, MeterReport, MetricsSnapshot
from dormiot.storage.redis_cache import RedisCache


def _redis_available() -> bool:
    try:
        with socket.create_connection(("localhost", 6379), timeout=2):
            return True
    except OSError:
        return False


requires_redis = pytest.mark.skipif(
    not _redis_available(),
    reason="Redis 未运行，跳过集成测试（docker compose up -d redis）",
)


def _make_report(device_id: str = "MOCK_METER_BLDG5_RM401") -> MeterReport:
    return MeterReport(
        device_id=device_id,
        timestamp=int(time.time()),
        metrics=MetricsSnapshot(current_power=50.0, voltage=220.0, smoke_density=0.01),
        status=DeviceStatus.NORMAL,
    )


@requires_redis
class TestRedisCache:
    def setup_method(self):
        self.cache = RedisCache()
        self.cache.connect()

    def teardown_method(self):
        self.cache.close()

    def test_update_and_get(self):
        report = _make_report()
        self.cache.update_device(report)
        data = self.cache.get_device("MOCK_METER_BLDG5_RM401")
        assert data is not None
        assert data["device_id"] == "MOCK_METER_BLDG5_RM401"
        assert float(data["current_power"]) == pytest.approx(50.0)

    def test_get_nonexistent(self):
        data = self.cache.get_device("NONEXISTENT")
        assert data is None

    def test_overwrite(self):
        report1 = _make_report()
        self.cache.update_device(report1)
        report2 = MeterReport(
            device_id="MOCK_METER_BLDG5_RM401",
            timestamp=int(time.time()),
            metrics=MetricsSnapshot(current_power=999.0, voltage=220.0, smoke_density=0.01),
            status=DeviceStatus.WARNING,
        )
        self.cache.update_device(report2)
        data = self.cache.get_device("MOCK_METER_BLDG5_RM401")
        assert float(data["current_power"]) == pytest.approx(999.0)
        assert data["status"] == "WARNING"

    def test_ttl_expires(self):
        report = _make_report()
        self.cache.update_device(report, ttl=1)
        assert self.cache.get_device("MOCK_METER_BLDG5_RM401") is not None
        time.sleep(1.5)
        assert self.cache.get_device("MOCK_METER_BLDG5_RM401") is None

    def test_get_all_devices(self):
        for i in range(3):
            self.cache.update_device(_make_report(f"MOCK_METER_BLDG5_RM{401+i}"))
        all_devs = self.cache.get_all_devices()
        assert len(all_devs) >= 3

    def test_get_device_ids(self):
        for i in range(3):
            self.cache.update_device(_make_report(f"MOCK_METER_BLDG5_RM{401+i}"))
        ids = self.cache.get_device_ids()
        assert len(ids) >= 3

    def test_delete_device(self):
        report = _make_report()
        self.cache.update_device(report)
        self.cache.delete_device("MOCK_METER_BLDG5_RM401")
        assert self.cache.get_device("MOCK_METER_BLDG5_RM401") is None
