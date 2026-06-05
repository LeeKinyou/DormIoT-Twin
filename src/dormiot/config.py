from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，支持 .env 文件与环境变量覆盖"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DORMIOT_",
        env_file_encoding="utf-8",
    )

    # ── 仿真 ──
    simulation_node_count: int = 6
    simulation_report_interval_ms: int = 1000

    # ── 宿舍楼配置 ──
    building_floors: int = 3           # 楼层数（演示用，减少数据量）
    rooms_per_floor: int = 6           # 每层房间数（演示用）
    building_name: str = "5号宿舍楼"   # 楼栋名称

    # ── 规则引擎阈值 ──
    power_threshold_illegal: float = 1500.0
    power_threshold_overload: float = 800.0
    smoke_threshold_critical: float = 0.40

    # ── LLM（OpenAI 兼容格式） ──
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"


settings = Settings()
