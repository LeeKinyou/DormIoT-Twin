from __future__ import annotations

import uuid

import paho.mqtt.client as mqtt

from dormiot.schemas.device import MeterReport


class MQTTPublisher:
    """MQTT 发布客户端，将虚拟设备数据上报到 EMQX"""

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883) -> None:
        self._broker_host = broker_host
        self._broker_port = broker_port
        client_id = f"dormiot-pub-{uuid.uuid4().hex[:8]}"
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._connected = False

    def connect(self) -> None:
        """连接到 MQTT Broker"""
        self._client.connect(self._broker_host, self._broker_port)
        self._client.loop_start()
        self._connected = True

    def disconnect(self) -> None:
        """断开连接"""
        if self._connected:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False

    def publish(self, report: MeterReport, topic: str | None = None) -> None:
        """发布一条 MeterReport 到指定 Topic

        Args:
            report: 要发布的设备数据
            topic: MQTT Topic，为 None 时使用 campus/{building}/{room}/meter
        """
        if not self._connected:
            raise RuntimeError("MQTT 未连接，请先调用 connect()")

        if topic is None:
            parts = report.device_id.split("_")
            # MOCK_METER_BLDG5_RM401 → dormiot/campus/5/401/meter
            building = parts[2].replace("BLDG", "")
            room = parts[3].replace("RM", "")
            topic = f"dormiot/campus/{building}/{room}/meter"

        payload = report.model_dump_json()
        self._client.publish(topic, payload, qos=0)

    @property
    def is_connected(self) -> bool:
        return self._connected
