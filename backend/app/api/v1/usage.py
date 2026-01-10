"""
Usage and quota management endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, SuperAdmin, TenantAdmin, get_rate_limiter_dep
from app.database import get_db
from app.models.tenant import Tenant
from app.models.usage import TenantQuota
from app.schemas.usage import (
    QuotaLimitsResponse,
    RateLimitStatusResponse,
    TenantQuotaUpdate,
    UsageHistoryItemResponse,
    UsageSummaryResponse,
)
from app.services.rate_limiter import (
    get_rate_limiter,
    PLAN_QUOTAS,
    RateLimiter,
    UsageTracker,
)

router = APIRouter(prefix="/usage", tags=["Usage & Quotas"])


@router.get("", response_model=UsageSummaryResponse)
async def get_usage_summary(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
):
    """
    Get current usage summary for the authenticated user's tenant.

    Returns usage statistics for the current billing period including:
    - API calls
    - Pages crawled
    - Keywords researched
    - Audits run
    - Content generations
    - JS renders
    """
    # Get tenant plan
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    tracker = UsageTracker(db, rate_limiter)
    summary = await tracker.get_usage_summary(current_user.tenant_id)

    return UsageSummaryResponse(**summary)


@router.get("/history", response_model=list[UsageHistoryItemResponse])
async def get_usage_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
    months: int = Query(default=6, ge=1, le=12, description="Number of months to retrieve"),
):
    """
    Get usage history for the past N months.

    Returns monthly usage statistics for historical analysis and reporting.
    """
    tracker = UsageTracker(db, rate_limiter)
    history = await tracker.get_usage_history(current_user.tenant_id, months)

    return [UsageHistoryItemResponse(**item) for item in history]


@router.get("/quotas", response_model=QuotaLimitsResponse)
async def get_quota_limits(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
):
    """
    Get quota limits for the current user's plan.

    Returns the maximum allowed usage for each metric based on the
    tenant's plan, including any custom overrides.
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    tracker = UsageTracker(db, rate_limiter)
    quotas = await tracker.get_tenant_quotas(current_user.tenant_id, tenant.plan)

    return QuotaLimitsResponse(
        plan=tenant.plan,
        api_calls=quotas.api_calls,
        crawl_pages=quotas.crawl_pages,
        keyword_lookups=quotas.keyword_lookups,
        audits=quotas.audits,
        content_generations=quotas.content_generations,
        js_renders=quotas.js_renders,
        rate_limit_per_minute=quotas.rate_limit_per_minute,
    )


@router.get("/rate-limit", response_model=RateLimitStatusResponse)
async def get_rate_limit_status(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
):
    """
    Get current rate limit status.

    Returns the current rate limit window status including remaining
    requests and reset time.
    """
    # Get tenant plan for rate limit
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    plan_quotas = PLAN_QUOTAS.get(tenant.plan, PLAN_QUOTAS["free"])

    # Check current rate limit status (without incrementing)
    rate_result = await rate_limiter.check_rate_limit(
        tenant_id=str(current_user.tenant_id),
        limit_per_minute=plan_quotas.rate_limit_per_minute,
        endpoint="status_check",
    )

    return RateLimitStatusResponse(
        limit=rate_result.limit,
        remaining=rate_result.remaining,
        reset_at=rate_result.reset_at,
    )


# Admin endpoints for managing tenant quotas


@router.get("/tenants/{tenant_id}", response_model=UsageSummaryResponse)
async def get_tenant_usage(
    tenant_id: UUID,
    _: SuperAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
):
    """
    Get usage summary for a specific tenant (super admin only).
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    tracker = UsageTracker(db, rate_limiter)
    summary = await tracker.get_usage_summary(tenant_id)

    return UsageSummaryResponse(**summary)


@router.patch("/tenants/{tenant_id}/quotas", response_model=QuotaLimitsResponse)
async def update_tenant_quotas(
    tenant_id: UUID,
    data: TenantQuotaUpdate,
    _: SuperAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
):
    """
    Update custom quota overrides for a tenant (super admin only).

    Custom quotas override the plan defaults. Set to null to use plan default.
    """
    # Verify tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Get or create quota record
    result = await db.execute(
        select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
    )
    quota = result.scalar_one_or_none()

    if not quota:
        quota = TenantQuota(tenant_id=tenant_id)
        db.add(quota)

    # Update quota fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quota, field, value)

    await db.flush()

    # Return updated quotas
    tracker = UsageTracker(db, rate_limiter)
    quotas = await tracker.get_tenant_quotas(tenant_id, tenant.plan)

    return QuotaLimitsResponse(
        plan=tenant.plan,
        api_calls=quotas.api_calls,
        crawl_pages=quotas.crawl_pages,
        keyword_lookups=quotas.keyword_lookups,
        audits=quotas.audits,
        content_generations=quotas.content_generations,
        js_renders=quotas.js_renders,
        rate_limit_per_minute=quotas.rate_limit_per_minute,
    )


@router.delete("/tenants/{tenant_id}/quotas")
async def reset_tenant_quotas(
    tenant_id: UUID,
    _: SuperAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Reset custom quota overrides for a tenant (super admin only).

    Removes all custom overrides, reverting to plan defaults.
    """
    result = await db.execute(
        select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
    )
    quota = result.scalar_one_or_none()

    if quota:
        await db.delete(quota)

    return {"message": "Quota overrides reset to plan defaults"}
