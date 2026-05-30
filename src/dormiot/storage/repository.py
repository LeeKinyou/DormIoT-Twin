from __future__ import annotations

from datetime import datetime

from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from dormiot.config import settings
from dormiot.schemas.alert import AlertEvent, AlertLevel
from dormiot.storage.models import Base, SecurityAlert


class AlertRepository:
    """告警数据持久化 CRUD"""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.mysql_url
        self._engine = create_engine(self._url, echo=False, pool_pre_ping=True)
        self._session_factory = sessionmaker(bind=self._engine)

    def create_tables(self) -> None:
        """创建所有表（幂等）"""
        Base.metadata.create_all(self._engine)
        logger.info("MySQL 表结构已就绪")

    def _session(self) -> Session:
        return self._session_factory()

    def save_alert(self, alert: AlertEvent) -> int:
        """保存一条告警，返回自增 ID"""
        with self._session() as session:
            row = SecurityAlert(
                device_id=alert.device_id,
                building_id=alert.building_id,
                room_id=alert.room_id,
                alert_level=alert.alert_level.value,
                alert_type=alert.alert_type,
                trigger_value=str(alert.trigger_value),
                message=alert.message,
                timestamp=alert.timestamp,
                resolved=alert.resolved,
            )
            session.add(row)
            session.commit()
            return row.id

    def query_alerts(
        self,
        alert_level: AlertLevel | None = None,
        building_id: str | None = None,
        device_id: str | None = None,
        resolved: bool | None = None,
        since: int | None = None,
        until: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SecurityAlert]:
        """查询告警列表，支持多条件筛选"""
        stmt = select(SecurityAlert)
        if alert_level:
            stmt = stmt.where(SecurityAlert.alert_level == alert_level.value)
        if building_id:
            stmt = stmt.where(SecurityAlert.building_id == building_id)
        if device_id:
            stmt = stmt.where(SecurityAlert.device_id == device_id)
        if resolved is not None:
            stmt = stmt.where(SecurityAlert.resolved == resolved)
        if since:
            stmt = stmt.where(SecurityAlert.timestamp >= since)
        if until:
            stmt = stmt.where(SecurityAlert.timestamp <= until)
        stmt = stmt.order_by(SecurityAlert.timestamp.desc()).limit(limit).offset(offset)
        with self._session() as session:
            return list(session.scalars(stmt).all())

    def resolve_alert(self, alert_id: int) -> bool:
        """标记告警为已处理，返回是否成功"""
        with self._session() as session:
            row = session.get(SecurityAlert, alert_id)
            if row is None:
                return False
            row.resolved = True
            row.resolved_at = datetime.now()
            session.commit()
            return True

    def count_unresolved(self) -> int:
        """统计未处理告警数"""
        stmt = select(SecurityAlert).where(SecurityAlert.resolved == False)
        with self._session() as session:
            return len(list(session.scalars(stmt).all()))

    def close(self) -> None:
        self._engine.dispose()
