"""MQTT 通信集成测试

需要运行中的 EMQX Broker（docker compose up -d emqx）才能通过。
无 Broker 时自动跳过。
"""
from __future__ import annotations

import threading
import time

import pytest

from dormiot.schemas.device import DeviceStatus, MeterReport, MetricsSnapshot
from dormiot.simulation.publisher import MQTTPublisher
from dormiot.gateway.mqtt_handler import MQTTHandler

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TIMEOUT_S = 5


def _broker_available() -> bool:
    """检测 MQTT Broker 是否可达"""
    import socket

    try:
        with socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=2):
            return True
    except OSError:
        return False


requires_broker = pytest.mark.skipif(
    not _broker_available(),
    reason="MQTT Broker 未运行，跳过集成测试（docker compose up -d emqx）",
)


def _make_report(device_id: str = "MOCK_METER_BLDG5_RM401") -> MeterReport:
    return MeterReport(
        device_id=device_id,
        timestamp=int(time.time()),
        metrics=MetricsSnapshot(current_power=50.0, voltage=220.0, smoke_density=0.01),
        status=DeviceStatus.NORMAL,
    )


@requires_broker
class TestMQTTPublishSubscribe:
    """发布 → 订阅 → 解析 端到端测试"""

    def test_publish_and_receive(self):
        """发布一条消息，订阅端能收到并解析为 MeterReport"""
        received: list[MeterReport] = []
        event = threading.Event()

        def on_message(report: MeterReport):
            received.append(report)
            event.set()

        handler = MQTTHandler(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            topic="test/dormiot/integration",
            on_message=on_message,
        )
        handler.start()
        time.sleep(1)  # 等待连接 + 订阅完成

        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        publisher.connect()

        report = _make_report()
        publisher.publish(report, topic="test/dormiot/integration")

        assert event.wait(timeout=TIMEOUT_S), "超时未收到消息"
        assert len(received) == 1
        assert received[0].device_id == report.device_id
        assert received[0].metrics.current_power == pytest.approx(50.0)

        publisher.disconnect()
        handler.stop()

    def test_multiple_messages(self):
        """连续发布多条消息，订阅端全部收到"""
        received: list[MeterReport] = []
        count = 5
        event = threading.Event()

        def on_message(report: MeterReport):
            received.append(report)
            if len(received) >= count:
                event.set()

        handler = MQTTHandler(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            topic="test/dormiot/multi",
            on_message=on_message,
        )
        handler.start()
        time.sleep(1)

        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        publisher.connect()

        for i in range(count):
            report = _make_report(f"MOCK_METER_BLDG5_RM{401 + i}")
            publisher.publish(report, topic="test/dormiot/multi")
            time.sleep(0.1)

        assert event.wait(timeout=TIMEOUT_S), f"超时，仅收到 {len(received)}/{count} 条"
        assert len(received) == count
        device_ids = {r.device_id for r in received}
        assert len(device_ids) == count

        publisher.disconnect()
        handler.stop()

    def test_wildcard_topic(self):
        """使用通配符 topic 订阅，能收到不同 building/room 的消息"""
        received: list[MeterReport] = []
        event = threading.Event()

        def on_message(report: MeterReport):
            received.append(report)
            event.set()

        handler = MQTTHandler(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            topic="test/wildcard/+/meter",
            on_message=on_message,
        )
        handler.start()
        time.sleep(1)

        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        publisher.connect()

        report = _make_report()
        publisher.publish(report, topic="test/wildcard/room401/meter")

        assert event.wait(timeout=TIMEOUT_S)
        assert received[0].device_id == "MOCK_METER_BLDG5_RM401"

        publisher.disconnect()
        handler.stop()

    def test_invalid_message_ignored(self):
        """收到非法 JSON 时不崩溃，静默跳过"""
        received: list[MeterReport] = []
        valid_event = threading.Event()

        def on_message(report: MeterReport):
            received.append(report)
            valid_event.set()

        handler = MQTTHandler(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            topic="test/dormiot/invalid",
            on_message=on_message,
        )
        handler.start()
        time.sleep(1)

        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        publisher.connect()

        # 先发一条非法消息
        publisher._client.publish("test/dormiot/invalid", "not-json", qos=0)
        time.sleep(0.5)

        # 再发一条合法消息
        report = _make_report()
        publisher.publish(report, topic="test/dormiot/invalid")

        assert valid_event.wait(timeout=TIMEOUT_S)
        assert len(received) == 1
        assert received[0].device_id == report.device_id

        publisher.disconnect()
        handler.stop()


@requires_broker
class TestMQTTPublisher:
    def test_connect_and_disconnect(self):
        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        assert not publisher.is_connected
        publisher.connect()
        assert publisher.is_connected
        publisher.disconnect()
        assert not publisher.is_connected

    def test_publish_without_connect_raises(self):
        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        with pytest.raises(RuntimeError, match="MQTT 未连接"):
            publisher.publish(_make_report())

    def test_auto_topic_from_device_id(self):
        """device_id 自动映射到正确的 topic"""
        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        publisher.connect()

        received: list[tuple[str, MeterReport]] = []
        event = threading.Event()

        def on_message(report: MeterReport):
            received.append(report)
            event.set()

        handler = MQTTHandler(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            topic="dormiot/campus/5/401/meter",
            on_message=on_message,
        )
        handler.start()
        time.sleep(1)

        report = _make_report("MOCK_METER_BLDG5_RM401")
        publisher.publish(report)  # 不指定 topic，自动推导

        assert event.wait(timeout=TIMEOUT_S)
        assert received[0].device_id == "MOCK_METER_BLDG5_RM401"

        publisher.disconnect()
        handler.stop()


@requires_broker
class TestMQTTHandler:
    def test_start_stop(self):
        handler = MQTTHandler(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        assert not handler.is_running
        handler.start()
        assert handler.is_running
        handler.stop()
        assert not handler.is_running

    def test_no_callback_no_crash(self):
        """没有设置回调时收到消息不崩溃"""
        handler = MQTTHandler(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            topic="test/dormiot/nocb",
            on_message=None,
        )
        handler.start()
        time.sleep(1)

        publisher = MQTTPublisher(broker_host=BROKER_HOST, broker_port=BROKER_PORT)
        publisher.connect()
        publisher.publish(_make_report(), topic="test/dormiot/nocb")
        time.sleep(1)

        # 不崩溃即通过
        publisher.disconnect()
        handler.stop()
