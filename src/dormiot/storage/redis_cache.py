from __future__ import annotations

import json

import redis
from loguru import logger

from dormiot.config import settings
from dormiot.schemas.device import MeterReport


class RedisCache:
    """宿舍设备状态 Redis 缓存

    使用 Hash 结构存储每个设备的最新指标快照。
    Key 格式: device:{device_id}
    TTL: 默认 30 秒，设备持续上报时自动刷新。
    """

    DEVICE_PREFIX = "device:"
    DEFAULT_TTL = 30  # 秒

    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.redis_url
        self._client: redis.Redis | None = None

    def connect(self) -> None:
        self._client = redis.from_url(self._url, decode_responses=True)
        self._client.ping()
        logger.info(f"Redis 已连接: {self._url}")

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis 未连接，请先调用 connect()")
        return self._client

    def update_device(self, report: MeterReport, ttl: int = DEFAULT_TTL) -> None:
        """将设备最新上报数据写入 Redis Hash"""
        key = f"{self.DEVICE_PREFIX}{report.device_id}"
        data = {
            "device_id": report.device_id,
            "timestamp": str(report.timestamp),
            "current_power": str(report.metrics.current_power),
            "voltage": str(report.metrics.voltage),
            "smoke_density": str(report.metrics.smoke_density),
            "status": report.status.value,
        }
        pipe = self.client.pipeline()
        pipe.hset(key, mapping=data)
        pipe.expire(key, ttl)
        pipe.execute()

    def get_device(self, device_id: str) -> dict | None:
        """读取设备缓存，不存在返回 None"""
        key = f"{self.DEVICE_PREFIX}{device_id}"
        data = self.client.hgetall(key)
        if not data:
            return None
        return data

    def get_all_devices(self) -> dict[str, dict]:
        """读取所有设备缓存"""
        pattern = f"{self.DEVICE_PREFIX}*"
        result = {}
        for key in self.client.scan_iter(match=pattern, count=100):
            device_id = key.removeprefix(self.DEVICE_PREFIX)
            result[device_id] = self.client.hgetall(key)
        return result

    def get_device_ids(self) -> list[str]:
        """获取所有缓存中的设备 ID"""
        pattern = f"{self.DEVICE_PREFIX}*"
        return [key.removeprefix(self.DEVICE_PREFIX) for key in self.client.scan_iter(match=pattern, count=100)]

    def delete_device(self, device_id: str) -> None:
        """删除设备缓存"""
        key = f"{self.DEVICE_PREFIX}{device_id}"
        self.client.delete(key)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
