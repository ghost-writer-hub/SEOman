"""
Alert models for real-time monitoring.

Supports:
- Site uptime monitoring
- Keyword ranking drop detection
- Audit score drop alerts
- Index status change monitoring
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class AlertType(str, PyEnum):
    """Types of alerts supported."""
    UPTIME = "uptime"
    RANKING_DROP = "ranking_drop"
    AUDIT_SCORE_DROP = "audit_score_drop"
    INDEX_STATUS = "index_status"


class AlertSeverity(str, PyEnum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationChannel(str, PyEnum):
    """Notification delivery channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertRuleStatus(str, PyEnum):
    """Alert rule status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class AlertEventStatus(str, PyEnum):
    """Alert event status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertRule(Base, BaseModel):
    """
    Alert rule configuration.

    Defines what to monitor and how to notify.
    """

    __tablename__ = "alert_rules"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    status = Column(
        Enum(AlertRuleStatus),
        default=AlertRuleStatus.ACTIVE,
        nullable=False,
    )

    # Condition configuration (JSON structure varies by alert_type)
    # uptime: {"check_interval_minutes": 5, "consecutive_failures": 2, "timeout_seconds": 30}
    # ranking_drop: {"position_drop": 10, "keyword_ids": [...] or null, "min_position": 100}
    # audit_score_drop: {"threshold": 70, "drop_percentage": 10}
    # index_status: {"check_noindex": true, "check_404": true, "check_deindex_count": 5}
    conditions = Column(JSONB, default=dict, nullable=False)

    # Notification settings
    notification_channels = Column(JSONB, default=list)  # ["email", "webhook"]
    notification_config = Column(JSONB, default=dict)
    # Structure:
    # {
    #   "email": {"recipients": ["user@example.com"], "include_details": true},
    #   "webhook": {"url": "https://...", "headers": {}, "include_payload": true}
    # }

    # Rate limiting for notifications
    cooldown_minutes = Column(Integer, default=60)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    site = relationship("Site", back_populates="alert_rules")
    events = relationship(
        "AlertEvent",
        back_populates="rule",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AlertRule {self.name} ({self.alert_type.value})>"


class AlertEvent(Base, BaseModel):
    """
    Triggered alert event.

    Created when an alert condition is met.
    """

    __tablename__ = "alert_events"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(
        Enum(AlertSeverity),
        default=AlertSeverity.WARNING,
        nullable=False,
    )
    status = Column(
        Enum(AlertEventStatus),
        default=AlertEventStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=True)
    details = Column(JSONB, default=dict)
    # Type-specific details:
    # uptime: {"response_code": 503, "response_time_ms": null, "error": "..."}
    # ranking_drop: {"keyword": "...", "old_position": 5, "new_position": 25}
    # audit_score_drop: {"old_score": 85, "new_score": 62, "failing_checks": [...]}
    # index_status: {"deindexed_urls": [...], "newly_noindex": [...]}

    # Notification tracking
    notifications_sent = Column(JSONB, default=list)
    # [{"channel": "email", "sent_at": "...", "success": true}, ...]

    # Resolution tracking
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    rule = relationship("AlertRule", back_populates="events")
    site = relationship("Site", back_populates="alert_events")

    def __repr__(self) -> str:
        return f"<AlertEvent {self.title[:30]}... ({self.status.value})>"


class UptimeCheck(Base, BaseModel):
    """
    Uptime check history for sites.

    Records each uptime check result for monitoring.
    """

    __tablename__ = "uptime_checks"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_up = Column(Boolean, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    site = relationship("Site", back_populates="uptime_checks")

    def __repr__(self) -> str:
        status = "UP" if self.is_up else "DOWN"
        return f"<UptimeCheck {self.site_id} {status}>"
