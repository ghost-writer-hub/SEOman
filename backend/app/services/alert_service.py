"""
Alert service for managing alert rules and events.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import (
    AlertEvent,
    AlertEventStatus,
    AlertRule,
    AlertRuleStatus,
    AlertSeverity,
    AlertType,
    UptimeCheck,
)
from app.models.site import Site
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate


class AlertService:
    """Service for alert operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Alert Rules ===

    async def create_rule(self, tenant_id: UUID, data: AlertRuleCreate) -> AlertRule:
        """Create a new alert rule."""
        rule = AlertRule(
            tenant_id=tenant_id,
            site_id=data.site_id,
            name=data.name,
            description=data.description,
            alert_type=AlertType(data.alert_type),
            conditions=data.conditions,
            notification_channels=data.notification_channels,
            notification_config=data.notification_config,
            cooldown_minutes=data.cooldown_minutes,
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def get_rule_by_id(
        self, rule_id: UUID, tenant_id: UUID
    ) -> AlertRule | None:
        """Get alert rule by ID."""
        result = await self.db.execute(
            select(AlertRule).where(
                AlertRule.id == rule_id,
                AlertRule.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_rules(
        self,
        tenant_id: UUID,
        site_id: UUID | None = None,
        alert_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[AlertRule], int]:
        """List alert rules with filters."""
        query = select(AlertRule).where(AlertRule.tenant_id == tenant_id)
        count_query = select(func.count(AlertRule.id)).where(
            AlertRule.tenant_id == tenant_id
        )

        if site_id:
            query = query.where(AlertRule.site_id == site_id)
            count_query = count_query.where(AlertRule.site_id == site_id)
        if alert_type:
            query = query.where(AlertRule.alert_type == AlertType(alert_type))
            count_query = count_query.where(
                AlertRule.alert_type == AlertType(alert_type)
            )
        if status:
            query = query.where(AlertRule.status == AlertRuleStatus(status))
            count_query = count_query.where(
                AlertRule.status == AlertRuleStatus(status)
            )

        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(AlertRule.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_rule(
        self, rule_id: UUID, tenant_id: UUID, data: AlertRuleUpdate
    ) -> AlertRule | None:
        """Update an alert rule."""
        rule = await self.get_rule_by_id(rule_id, tenant_id)
        if not rule:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and value:
                value = AlertRuleStatus(value)
            setattr(rule, field, value)

        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: UUID, tenant_id: UUID) -> bool:
        """Delete an alert rule."""
        rule = await self.get_rule_by_id(rule_id, tenant_id)
        if not rule:
            return False
        await self.db.delete(rule)
        return True

    async def get_active_rules_by_type(
        self, alert_type: AlertType
    ) -> list[AlertRule]:
        """Get all active rules of a specific type (for background tasks)."""
        result = await self.db.execute(
            select(AlertRule)
            .options(selectinload(AlertRule.site))
            .where(
                AlertRule.alert_type == alert_type,
                AlertRule.status == AlertRuleStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())

    # === Alert Events ===

    async def create_event(
        self,
        rule: AlertRule,
        severity: AlertSeverity,
        title: str,
        message: str | None,
        details: dict,
    ) -> AlertEvent:
        """Create a new alert event."""
        event = AlertEvent(
            tenant_id=rule.tenant_id,
            site_id=rule.site_id,
            rule_id=rule.id,
            alert_type=rule.alert_type,
            severity=severity,
            title=title,
            message=message,
            details=details,
        )
        self.db.add(event)

        # Update rule's last triggered timestamp
        rule.last_triggered_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_event_by_id(
        self, event_id: UUID, tenant_id: UUID
    ) -> AlertEvent | None:
        """Get alert event by ID."""
        result = await self.db.execute(
            select(AlertEvent).where(
                AlertEvent.id == event_id,
                AlertEvent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_events(
        self,
        tenant_id: UUID,
        site_id: UUID | None = None,
        alert_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[AlertEvent], int]:
        """List alert events with filters."""
        query = select(AlertEvent).where(AlertEvent.tenant_id == tenant_id)
        count_query = select(func.count(AlertEvent.id)).where(
            AlertEvent.tenant_id == tenant_id
        )

        if site_id:
            query = query.where(AlertEvent.site_id == site_id)
            count_query = count_query.where(AlertEvent.site_id == site_id)
        if alert_type:
            query = query.where(AlertEvent.alert_type == AlertType(alert_type))
            count_query = count_query.where(
                AlertEvent.alert_type == AlertType(alert_type)
            )
        if status:
            query = query.where(AlertEvent.status == AlertEventStatus(status))
            count_query = count_query.where(
                AlertEvent.status == AlertEventStatus(status)
            )

        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(AlertEvent.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def acknowledge_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        notes: str | None = None,
    ) -> AlertEvent | None:
        """Acknowledge an alert event."""
        event = await self.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        event.status = AlertEventStatus.ACKNOWLEDGED
        event.acknowledged_at = datetime.now(timezone.utc)
        event.acknowledged_by_user_id = user_id
        if notes:
            event.resolution_notes = notes

        await self.db.flush()
        return event

    async def resolve_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        resolution_notes: str | None = None,
    ) -> AlertEvent | None:
        """Resolve an alert event."""
        event = await self.get_event_by_id(event_id, tenant_id)
        if not event:
            return None

        event.status = AlertEventStatus.RESOLVED
        event.resolved_at = datetime.now(timezone.utc)
        if resolution_notes:
            event.resolution_notes = resolution_notes

        await self.db.flush()
        return event

    async def can_trigger_alert(self, rule: AlertRule) -> bool:
        """Check if alert can be triggered (respecting cooldown)."""
        if not rule.last_triggered_at:
            return True

        cooldown_end = rule.last_triggered_at + timedelta(
            minutes=rule.cooldown_minutes
        )
        return datetime.now(timezone.utc) >= cooldown_end

    # === Uptime Checks ===

    async def record_uptime_check(
        self,
        site: Site,
        is_up: bool,
        status_code: int | None,
        response_time_ms: int | None,
        error_message: str | None,
    ) -> UptimeCheck:
        """Record an uptime check result."""
        check = UptimeCheck(
            tenant_id=site.tenant_id,
            site_id=site.id,
            is_up=is_up,
            status_code=status_code,
            response_time_ms=response_time_ms,
            error_message=error_message,
            checked_at=datetime.now(timezone.utc),
        )
        self.db.add(check)
        await self.db.flush()
        return check

    async def get_uptime_stats(self, site_id: UUID, days: int = 30) -> dict:
        """Get uptime statistics for a site."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.count(UptimeCheck.id).label("total"),
                func.sum(func.cast(UptimeCheck.is_up, Integer)).label("up_count"),
            ).where(
                UptimeCheck.site_id == site_id,
                UptimeCheck.checked_at >= since,
            )
        )
        row = result.one()

        total = row.total or 0
        up_count = row.up_count or 0

        return {
            "total_checks": total,
            "up_count": up_count,
            "uptime_percentage": (up_count / total * 100) if total > 0 else 100.0,
        }

    async def get_recent_downtime_count(
        self, site_id: UUID, consecutive: int = 2
    ) -> int:
        """Get count of recent consecutive failures."""
        result = await self.db.execute(
            select(UptimeCheck)
            .where(UptimeCheck.site_id == site_id)
            .order_by(UptimeCheck.checked_at.desc())
            .limit(consecutive)
        )
        checks = result.scalars().all()

        if len(checks) < consecutive:
            return 0

        failures = sum(1 for c in checks if not c.is_up)
        return failures

    async def get_last_uptime_check(self, site_id: UUID) -> UptimeCheck | None:
        """Get the most recent uptime check for a site."""
        result = await self.db.execute(
            select(UptimeCheck)
            .where(UptimeCheck.site_id == site_id)
            .order_by(UptimeCheck.checked_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_downtime_incidents_count(
        self, site_id: UUID, days: int = 30
    ) -> int:
        """Count downtime incidents in a period."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(func.count(UptimeCheck.id)).where(
                UptimeCheck.site_id == site_id,
                UptimeCheck.is_up == False,
                UptimeCheck.checked_at >= since,
            )
        )
        return result.scalar() or 0
