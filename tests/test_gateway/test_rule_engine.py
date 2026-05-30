from __future__ import annotations

import time

from dormiot.gateway.rule_engine import RuleEngine
from dormiot.schemas.alert import AlertLevel
from dormiot.schemas.device import DeviceStatus, MeterReport, MetricsSnapshot


def _make_report(
    device_id: str = "MOCK_METER_BLDG5_RM401",
    power: float = 50.0,
    voltage: float = 220.0,
    smoke: float = 0.01,
    status: DeviceStatus = DeviceStatus.NORMAL,
) -> MeterReport:
    return MeterReport(
        device_id=device_id,
        timestamp=int(time.time()),
        metrics=MetricsSnapshot(current_power=power, voltage=voltage, smoke_density=smoke),
        status=status,
    )


class TestRuleEngine:
    def test_normal_no_alert(self):
        engine = RuleEngine()
        alerts = engine.evaluate(_make_report())
        assert len(alerts) == 0

    def test_power_overload_triggers_medium(self):
        engine = RuleEngine()
        report = _make_report(power=900.0)
        alerts = engine.evaluate(report)
        assert len(alerts) >= 1
        overload = [a for a in alerts if a.alert_type == "overload"]
        assert len(overload) == 1
        assert overload[0].alert_level == AlertLevel.MEDIUM

    def test_power_illegal_triggers_high(self):
        engine = RuleEngine()
        report = _make_report(power=1600.0)
        alerts = engine.evaluate(report)
        types = {a.alert_type for a in alerts}
        assert "illegal_appliance" in types
        illegal = [a for a in alerts if a.alert_type == "illegal_appliance"][0]
        assert illegal.alert_level == AlertLevel.HIGH

    def test_smoke_critical_triggers_cr(self):
        engine = RuleEngine()
        report = _make_report(smoke=0.50)
        alerts = engine.evaluate(report)
        fire = [a for a in alerts if a.alert_type == "fire_critical"]
        assert len(fire) == 1
        assert fire[0].alert_level == AlertLevel.CRITICAL

    def test_high_power_triggers_both_overload_and_illegal(self):
        engine = RuleEngine()
        report = _make_report(power=1600.0)
        alerts = engine.evaluate(report)
        types = {a.alert_type for a in alerts}
        assert "overload" in types
        assert "illegal_appliance" in types

    def test_cooldown_prevents_duplicate(self):
        engine = RuleEngine(cooldown_seconds=60)
        report = _make_report(power=1600.0)
        alerts1 = engine.evaluate(report)
        assert len(alerts1) >= 1
        # 立即再次评估，应被冷却拦截
        alerts2 = engine.evaluate(report)
        assert len(alerts2) == 0

    def test_cooldown_expires(self):
        engine = RuleEngine(cooldown_seconds=0)  # 冷却时间为 0
        report = _make_report(power=1600.0)
        alerts1 = engine.evaluate(report)
        assert len(alerts1) >= 1
        alerts2 = engine.evaluate(report)
        assert len(alerts2) >= 1  # 冷却已过期，应再次触发

    def test_different_devices_not_cooling_each_other(self):
        engine = RuleEngine(cooldown_seconds=60)
        report1 = _make_report(device_id="MOCK_METER_BLDG5_RM401", power=1600.0)
        report2 = _make_report(device_id="MOCK_METER_BLDG5_RM402", power=1600.0)
        engine.evaluate(report1)
        alerts2 = engine.evaluate(report2)
        assert len(alerts2) >= 1  # 不同设备不受冷却影响

    def test_building_room_parsed(self):
        engine = RuleEngine()
        report = _make_report(device_id="MOCK_METER_BLDG12_RM301", power=1600.0)
        alerts = engine.evaluate(report)
        assert len(alerts) >= 1
        assert alerts[0].building_id == "12"
        assert alerts[0].room_id == "301"

    def test_reset_cooldown(self):
        engine = RuleEngine(cooldown_seconds=60)
        report = _make_report(power=1600.0)
        engine.evaluate(report)
        engine.reset_cooldown()
        alerts = engine.evaluate(report)
        assert len(alerts) >= 1

    def test_evaluate_performance(self):
        """单条消息匹配耗时 <5ms"""
        engine = RuleEngine()
        report = _make_report(power=1600.0, smoke=0.50)
        start = time.perf_counter()
        for _ in range(1000):
            engine.reset_cooldown()
            engine.evaluate(report)
        elapsed = (time.perf_counter() - start) / 1000
        assert elapsed < 0.005, f"单次评估耗时 {elapsed*1000:.2f}ms，超过 5ms"
