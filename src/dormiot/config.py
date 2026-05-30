from __future__ import annotations

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，支持 .env 文件与环境变量覆盖"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DORMIOT_",
        env_file_encoding="utf-8",
    )

    # ── MQTT ──
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_topic_pattern: str = "campus/+/+/meter"

    # ── Redis ──
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_username: str = ""

    # ── MySQL ──
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "password"
    mysql_database: str = "dormiot"

    # ── 仿真 ──
    simulation_node_count: int = 50
    simulation_report_interval_ms: int = 1000

    # ── 规则引擎阈值 ──
    power_threshold_illegal: float = 1500.0
    power_threshold_overload: float = 800.0
    smoke_threshold_critical: float = 0.40

    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL，自动编码密码中的特殊字符"""
        if self.redis_password:
            user = quote_plus(self.redis_username) if self.redis_username else ""
            pwd = quote_plus(self.redis_password)
            auth = f"{user}:{pwd}@" if user else f"{pwd}@"
            return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def mysql_url(self) -> str:
        """构建 MySQL 连接 URL，自动编码密码中的特殊字符（如 @）"""
        user = quote_plus(self.mysql_user)
        pwd = quote_plus(self.mysql_password)
        return f"mysql+pymysql://{user}:{pwd}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"


settings = Settings()
