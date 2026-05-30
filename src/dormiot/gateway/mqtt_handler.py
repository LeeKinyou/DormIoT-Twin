from __future__ import annotations

import threading
import uuid
from typing import Callable

import paho.mqtt.client as mqtt
from loguru import logger

from dormiot.schemas.device import MeterReport


class MQTTHandler:
    """MQTT 后台监听器

    在独立守护线程中订阅 MQTT 主题，收到消息后：
    1. 反序列化 JSON → MeterReport
    2. 调用回调函数传递给上层（规则引擎 / Streamlit session state）
    """

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic: str = "campus/+/+/meter",
        on_message: Callable[[MeterReport], None] | None = None,
    ) -> None:
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._topic = topic
        self._on_message = on_message
        client_id = f"dormiot-handler-{uuid.uuid4().hex[:8]}"
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_mqtt_message
        self._client.on_disconnect = self._on_disconnect
        self._thread: threading.Thread | None = None
        self._running = False

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc) -> None:
        if rc == 0:
            logger.info(f"MQTT 已连接: {self._broker_host}:{self._broker_port}")
            client.subscribe(self._topic, qos=0)
            logger.info(f"MQTT 已订阅: {self._topic}")
        else:
            logger.error(f"MQTT 连接失败, rc={rc}")

    def _on_disconnect(self, client: mqtt.Client, userdata, rc) -> None:
        if rc != 0:
            logger.warning(f"MQTT 意外断开 (rc={rc})，将自动重连")

    def _on_mqtt_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        try:
            report = MeterReport.model_validate_json(msg.payload)
            if self._on_message:
                self._on_message(report)
        except Exception as e:
            logger.warning(f"MQTT 消息解析失败: {e}")

    def start(self) -> None:
        """启动后台监听线程"""
        if self._running:
            return
        self._running = True
        self._client.connect(self._broker_host, self._broker_port)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="mqtt-handler")
        self._thread.start()
        logger.info("MQTT 后台监听线程已启动")

    def _loop(self) -> None:
        self._client.loop_forever()

    def stop(self) -> None:
        """停止监听"""
        if self._running:
            self._running = False
            self._client.disconnect()
            logger.info("MQTT 后台监听已停止")

    @property
    def on_message(self) -> Callable[[MeterReport], None] | None:
        return self._on_message

    @on_message.setter
    def on_message(self, callback: Callable[[MeterReport], None] | None) -> None:
        self._on_message = callback

    @property
    def is_running(self) -> bool:
        return self._running
