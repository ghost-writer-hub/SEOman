"""
Alert management endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.alert import (
    AlertEventAcknowledge,
    AlertEventResolve,
    AlertEventResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    TestEmailRequest,
    TestWebhookRequest,
    UptimeCheckResponse,
    UptimeSummary,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# === Alert Rules ===


@router.get("/rules", response_model=PaginatedResponse[AlertRuleResponse])
async def list_alert_rules(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    site_id: UUID | None = None,
    alert_type: str | None = None,
    rule_status: str | None = Query(default=None, alias="status"),
):
    """List alert rules for the current tenant."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    rules, total = await service.list_rules(
        current_user.tenant_id,
        site_id=site_id,
        alert_type=alert_type,
        status=rule_status,
        page=page,
        per_page=per_page,
    )

    return PaginatedResponse.create(
        items=[AlertRuleResponse.model_validate(r) for r in rules],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    data: AlertRuleCreate,
    current_user: Annotated[CurrentUser, Depends(require_permission("alert:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new alert rule."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    rule = await service.create_rule(current_user.tenant_id, data)
    await db.commit()

    return AlertRuleResponse.model_validate(rule)


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get an alert rule by ID."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    rule = await service.get_rule_by_id(rule_id, current_user.tenant_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    return AlertRuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: UUID,
    data: AlertRuleUpdate,
    current_user: Annotated[CurrentUser, Depends(require_permission("alert:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an alert rule."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    rule = await service.update_rule(rule_id, current_user.tenant_id, data)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    await db.commit()
    return AlertRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", response_model=MessageResponse)
async def delete_alert_rule(
    rule_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("alert:delete"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an alert rule."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    deleted = await service.delete_rule(rule_id, current_user.tenant_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    await db.commit()
    return MessageResponse(message="Alert rule deleted successfully")


# === Alert Events ===


@router.get("/events", response_model=PaginatedResponse[AlertEventResponse])
async def list_alert_events(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    site_id: UUID | None = None,
    alert_type: str | None = None,
    event_status: str | None = Query(default=None, alias="status"),
):
    """List alert events for the current tenant."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    events, total = await service.list_events(
        current_user.tenant_id,
        site_id=site_id,
        alert_type=alert_type,
        status=event_status,
        page=page,
        per_page=per_page,
    )

    return PaginatedResponse.create(
        items=[AlertEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/events/{event_id}", response_model=AlertEventResponse)
async def get_alert_event(
    event_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get an alert event by ID."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    event = await service.get_event_by_id(event_id, current_user.tenant_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert event not found",
        )

    return AlertEventResponse.model_validate(event)


@router.post("/events/{event_id}/acknowledge", response_model=AlertEventResponse)
async def acknowledge_alert_event(
    event_id: UUID,
    data: AlertEventAcknowledge,
    current_user: Annotated[CurrentUser, Depends(require_permission("alert:acknowledge"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Acknowledge an alert event."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    event = await service.acknowledge_event(
        event_id, current_user.tenant_id, current_user.id, data.notes
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert event not found",
        )

    await db.commit()
    return AlertEventResponse.model_validate(event)


@router.post("/events/{event_id}/resolve", response_model=AlertEventResponse)
async def resolve_alert_event(
    event_id: UUID,
    data: AlertEventResolve,
    current_user: Annotated[CurrentUser, Depends(require_permission("alert:resolve"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resolve an alert event."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)
    event = await service.resolve_event(
        event_id, current_user.tenant_id, data.resolution_notes
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert event not found",
        )

    await db.commit()
    return AlertEventResponse.model_validate(event)


# === Uptime ===


@router.get("/uptime/{site_id}/summary", response_model=UptimeSummary)
async def get_uptime_summary(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get uptime summary for a site."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    service = AlertService(db)

    # Get stats for different periods
    stats_24h = await service.get_uptime_stats(site_id, days=1)
    stats_7d = await service.get_uptime_stats(site_id, days=7)
    stats_30d = await service.get_uptime_stats(site_id, days=30)

    # Get last check
    last_check = await service.get_last_uptime_check(site_id)

    # Get incident count
    incidents = await service.get_downtime_incidents_count(site_id, days=30)

    # Determine current status
    if last_check is None:
        current_status = "unknown"
    elif last_check.is_up:
        current_status = "up"
    else:
        current_status = "down"

    return UptimeSummary(
        site_id=site_id,
        uptime_percentage_24h=stats_24h["uptime_percentage"],
        uptime_percentage_7d=stats_7d["uptime_percentage"],
        uptime_percentage_30d=stats_30d["uptime_percentage"],
        last_check=UptimeCheckResponse.model_validate(last_check) if last_check else None,
        current_status=current_status,
        downtime_incidents_30d=incidents,
    )


@router.get("/uptime/{site_id}/checks", response_model=PaginatedResponse[UptimeCheckResponse])
async def list_uptime_checks(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
):
    """List uptime check history for a site."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    from sqlalchemy import func, select

    from app.models.alert import UptimeCheck

    # Build query
    query = select(UptimeCheck).where(UptimeCheck.site_id == site_id)
    count_query = select(func.count(UptimeCheck.id)).where(UptimeCheck.site_id == site_id)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(UptimeCheck.checked_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    checks = result.scalars().all()

    return PaginatedResponse.create(
        items=[UptimeCheckResponse.model_validate(c) for c in checks],
        total=total,
        page=page,
        per_page=per_page,
    )


# === Notification Testing ===


@router.post("/test/email", response_model=MessageResponse)
async def test_email_notification(
    data: TestEmailRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("alert:create"))],
):
    """Test email notification configuration."""
    service = NotificationService()
    result = await service.test_email(data.recipients)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Email test failed"),
        )

    return MessageResponse(message="Test email sent successfully")


@router.post("/test/webhook", response_model=MessageResponse)
async def test_webhook_notification(
    data: TestWebhookRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("alert:create"))],
):
    """Test webhook notification configuration."""
    service = NotificationService()
    result = await service.test_webhook(data.url, data.headers)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Webhook test failed"),
        )

    return MessageResponse(message="Test webhook sent successfully")
