from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SecurityAlert(Base):
    """安全告警持久化表"""

    __tablename__ = "security_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    building_id: Mapped[str] = mapped_column(String(16), nullable=False)
    room_id: Mapped[str] = mapped_column(String(16), nullable=False)
    alert_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_value: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_alert_level_timestamp", "alert_level", "timestamp"),
        Index("ix_device_resolved", "device_id", "resolved"),
    )

    def __repr__(self) -> str:
        return f"<SecurityAlert(id={self.id}, device={self.device_id}, level={self.alert_level})>"
