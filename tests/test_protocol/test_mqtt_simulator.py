"""MQTT 协议仿真层测试

测试内存 pub/sub Broker、Topic 通配符匹配、消息日志等核心功能。
"""
from __future__ import annotations

import threading
import pytest

from dormiot.protocol.mqtt_simulator import MQTTBroker, MQTTTopic


@pytest.fixture(autouse=True)
def _reset_broker():
    """每个测试前重置 Broker 单例"""
    MQTTBroker.reset()
    yield
    MQTTBroker.reset()


# ── MQTTTopic 常量 ──


class TestMQTTTopic:
    def test_meter_report_has_placeholder(self):
        assert "{building}" in MQTTTopic.METER_REPORT
        assert "{room}" in MQTTTopic.METER_REPORT

    def test_format_meter_report(self):
        topic = MQTTTopic.METER_REPORT.format(building="5", room="101")
        assert topic == "dormiot/campus/5/101/meter"

    def test_alarm_topic_format(self):
        topic = MQTTTopic.ALARM.format(building="5", room="102")
        assert topic == "dormiot/alarm/5/102"

    def test_system_heartbeat_is_constant(self):
        assert MQTTTopic.SYSTEM_HEARTBEAT == "dormiot/system/heartbeat"


# ── MQTTBroker 基本操作 ──


class TestMQTTBroker:
    def test_singleton(self):
        b1 = MQTTBroker()
        b2 = MQTTBroker()
        assert b1 is b2

    def test_publish_and_get_recent(self):
        broker = MQTTBroker()
        broker.publish("dormiot/campus/5/101/meter", {"power": 52.3})
        msgs = broker.get_recent_messages()
        assert len(msgs) == 1
        assert msgs[0]["topic"] == "dormiot/campus/5/101/meter"
        assert msgs[0]["payload"]["power"] == 52.3

    def test_message_log_limit(self):
        broker = MQTTBroker()
        for i in range(120):
            broker.publish(f"topic/{i}", {"i": i})
        msgs = broker.get_recent_messages(limit=100)
        assert len(msgs) <= 100

    def test_get_recent_with_custom_limit(self):
        broker = MQTTBroker()
        for i in range(10):
            broker.publish(f"topic/{i}", {"i": i})
        msgs = broker.get_recent_messages(limit=3)
        assert len(msgs) == 3


# ── 订阅与回调 ──


class TestSubscribe:
    def test_exact_topic_callback(self):
        broker = MQTTBroker()
        received = []
        broker.subscribe("dormiot/campus/5/101/meter", lambda t, p: received.append(p))
        broker.publish("dormiot/campus/5/101/meter", {"power": 100})
        assert len(received) == 1
        assert received[0]["power"] == 100

    def test_no_callback_on_mismatch(self):
        broker = MQTTBroker()
        received = []
        broker.subscribe("dormiot/campus/5/101/meter", lambda t, p: received.append(p))
        broker.publish("dormiot/campus/5/102/meter", {"power": 200})
        assert len(received) == 0

    def test_wildcard_hash(self):
        broker = MQTTBroker()
        received = []
        broker.subscribe("dormiot/campus/5/#", lambda t, p: received.append(t))
        broker.publish("dormiot/campus/5/101/meter", {"power": 50})
        broker.publish("dormiot/campus/5/102/smoke", {"smoke": 0.01})
        broker.publish("dormiot/campus/6/101/meter", {"power": 60})
        assert len(received) == 2

    def test_multiple_subscribers(self):
        broker = MQTTBroker()
        r1, r2 = [], []
        broker.subscribe("dormiot/#", lambda t, p: r1.append(p))
        broker.subscribe("dormiot/#", lambda t, p: r2.append(p))
        broker.publish("dormiot/campus/5/101/meter", {"power": 50})
        assert len(r1) == 1
        assert len(r2) == 1

    def test_subscribe_with_plus_wildcard(self):
        """测试 + 通配符（单层匹配）"""
        broker = MQTTBroker()
        received = []
        broker.subscribe("dormiot/campus/+/101/meter", lambda t, p: received.append(t))
        broker.publish("dormiot/campus/5/101/meter", {"power": 50})
        broker.publish("dormiot/campus/6/101/meter", {"power": 60})
        broker.publish("dormiot/campus/5/102/meter", {"power": 70})
        assert len(received) == 2


# ── 线程安全 ──


class TestThreadSafety:
    def test_concurrent_publish(self):
        broker = MQTTBroker()
        errors = []

        def pub(n):
            try:
                for i in range(50):
                    broker.publish(f"topic/{n}/{i}", {"n": n, "i": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=pub, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        msgs = broker.get_recent_messages(limit=200)
        assert len(msgs) == 100  # 4 * 50 = 200, but log capped at 100


# ── Topic 匹配逻辑 ──


class TestTopicMatch:
    def test_exact_match(self):
        assert MQTTBroker._topic_matches("a/b/c", "a/b/c") is True

    def test_exact_mismatch(self):
        assert MQTTBroker._topic_matches("a/b/c", "a/b/d") is False

    def test_hash_wildcard(self):
        assert MQTTBroker._topic_matches("a/b/c", "a/b/#") is True

    def test_hash_wildcard_mismatch(self):
        assert MQTTBroker._topic_matches("a/x/c", "a/b/#") is False

    def test_plus_wildcard(self):
        assert MQTTBroker._topic_matches("a/b/c", "a/+/c") is True

    def test_plus_wildcard_mismatch(self):
        assert MQTTBroker._topic_matches("a/b/c", "a/+/d") is False
