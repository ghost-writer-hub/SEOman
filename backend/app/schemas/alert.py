"""
Alert schemas for API request/response.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, HttpUrl

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


# === Condition Schemas ===


class UptimeConditions(BaseSchema):
    """Conditions for uptime monitoring."""

    check_interval_minutes: int = Field(default=5, ge=1, le=60)
    consecutive_failures: int = Field(default=2, ge=1, le=10)
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class RankingDropConditions(BaseSchema):
    """Conditions for ranking drop alerts."""

    position_drop: int = Field(
        default=10,
        ge=1,
        description="Alert when position drops by N positions",
    )
    keyword_ids: list[UUID] | None = Field(
        default=None,
        description="Specific keyword IDs to monitor, or null for all tracked keywords",
    )
    min_position: int = Field(
        default=100,
        description="Only alert for keywords previously in top N",
    )


class AuditScoreDropConditions(BaseSchema):
    """Conditions for audit score drop alerts."""

    threshold: int = Field(
        default=70,
        ge=0,
        le=100,
        description="Alert when score drops below this threshold",
    )
    drop_percentage: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Or alert when score drops by this percentage",
    )


class IndexStatusConditions(BaseSchema):
    """Conditions for index status change alerts."""

    check_noindex: bool = Field(default=True)
    check_404: bool = Field(default=True)
    check_deindex_count: int = Field(
        default=5,
        description="Alert when this many pages are deindexed",
    )


# === Notification Config Schemas ===


class EmailNotificationConfig(BaseSchema):
    """Email notification configuration."""

    recipients: list[str] = Field(min_length=1)
    include_details: bool = True


class WebhookNotificationConfig(BaseSchema):
    """Webhook notification configuration."""

    url: str = Field(description="Webhook URL (Slack, Discord, custom)")
    headers: dict[str, str] = Field(default_factory=dict)
    include_payload: bool = True


class NotificationConfig(BaseSchema):
    """Combined notification configuration."""

    email: EmailNotificationConfig | None = None
    webhook: WebhookNotificationConfig | None = None


# === Alert Rule Schemas ===


class AlertRuleCreate(BaseSchema):
    """Create alert rule request."""

    site_id: UUID
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    alert_type: str = Field(
        description="Alert type: uptime, ranking_drop, audit_score_drop, index_status"
    )
    conditions: dict = Field(default_factory=dict)
    notification_channels: list[str] = Field(default=["email"])
    notification_config: dict = Field(default_factory=dict)
    cooldown_minutes: int = Field(default=60, ge=5, le=1440)


class AlertRuleUpdate(BaseSchema):
    """Update alert rule request."""

    name: str | None = None
    description: str | None = None
    status: str | None = None  # active, paused, disabled
    conditions: dict | None = None
    notification_channels: list[str] | None = None
    notification_config: dict | None = None
    cooldown_minutes: int | None = Field(default=None, ge=5, le=1440)


class AlertRuleResponse(IDSchema, TimestampSchema):
    """Alert rule response."""

    tenant_id: UUID
    site_id: UUID
    name: str
    description: str | None
    alert_type: str
    status: str
    conditions: dict
    notification_channels: list[str]
    notification_config: dict
    cooldown_minutes: int
    last_triggered_at: datetime | None


# === Alert Event Schemas ===


class AlertEventResponse(IDSchema, TimestampSchema):
    """Alert event response."""

    tenant_id: UUID
    site_id: UUID
    rule_id: UUID
    alert_type: str
    severity: str
    status: str
    title: str
    message: str | None
    details: dict
    notifications_sent: list[dict]
    acknowledged_at: datetime | None
    acknowledged_by_user_id: UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None


class AlertEventAcknowledge(BaseSchema):
    """Acknowledge alert event request."""

    notes: str | None = None


class AlertEventResolve(BaseSchema):
    """Resolve alert event request."""

    resolution_notes: str | None = None


# === Uptime Check Schemas ===


class UptimeCheckResponse(IDSchema, TimestampSchema):
    """Uptime check response."""

    site_id: UUID
    is_up: bool
    status_code: int | None
    response_time_ms: int | None
    error_message: str | None
    checked_at: datetime


class UptimeSummary(BaseSchema):
    """Uptime summary for a site."""

    site_id: UUID
    uptime_percentage_24h: float
    uptime_percentage_7d: float
    uptime_percentage_30d: float
    last_check: UptimeCheckResponse | None
    current_status: str  # "up", "down", "unknown"
    downtime_incidents_30d: int


# === Test Notification Schemas ===


class TestEmailRequest(BaseSchema):
    """Test email notification request."""

    recipients: list[str] = Field(min_length=1)


class TestWebhookRequest(BaseSchema):
    """Test webhook notification request."""

    url: str
    headers: dict[str, str] = Field(default_factory=dict)
