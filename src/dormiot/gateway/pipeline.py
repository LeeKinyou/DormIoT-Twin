from __future__ import annotations

from loguru import logger

from dormiot.gateway.mqtt_handler import MQTTHandler
from dormiot.gateway.rule_engine import RuleEngine
from dormiot.schemas.device import MeterReport
from dormiot.storage.redis_cache import RedisCache
from dormiot.storage.repository import AlertRepository


class DataPipeline:
    """数据管线：MQTT 消息 → 规则引擎 → Redis 缓存 + MySQL 告警持久化

    作为 MQTTHandler 的回调入口，串联整个数据流。
    """

    def __init__(
        self,
        mqtt_handler: MQTTHandler,
        rule_engine: RuleEngine,
        redis_cache: RedisCache,
        alert_repo: AlertRepository,
    ) -> None:
        self._mqtt = mqtt_handler
        self._rules = rule_engine
        self._cache = redis_cache
        self._repo = alert_repo
        self._message_count = 0
        self._alert_count = 0
        self.on_message_callback = None

    def start(self) -> None:
        """启动管线：创建表 → 连接 Redis → 注册回调 → 启动 MQTT 监听"""
        self._repo.create_tables()
        self._cache.connect()
        self._mqtt.on_message = self.on_message
        self._mqtt.start()
        logger.info("数据管线已启动")

    def stop(self) -> None:
        """停止管线"""
        self._mqtt.stop()
        self._cache.close()
        self._repo.close()
        logger.info(f"数据管线已停止（处理 {self._message_count} 条消息，触发 {self._alert_count} 条告警）")

    def on_message(self, report: MeterReport) -> None:
        """MQTT 消息回调：缓存 → 规则评估 → 持久化告警 → UI 回调"""
        self._message_count += 1

        # 1. 更新 Redis 缓存
        try:
            self._cache.update_device(report)
        except Exception as e:
            logger.error(f"Redis 缓存写入失败: {e}")

        # 2. 规则引擎评估
        alerts = self._rules.evaluate(report)

        # 3. 持久化告警到 MySQL
        for alert in alerts:
            try:
                self._repo.save_alert(alert)
                self._alert_count += 1
            except Exception as e:
                logger.error(f"MySQL 告警写入失败: {e}")

        # 4. UI 回调（写入共享缓冲区）
        if self.on_message_callback:
            self.on_message_callback(report)

    @property
    def message_count(self) -> int:
        return self._message_count

    @property
    def alert_count(self) -> int:
        return self._alert_count
