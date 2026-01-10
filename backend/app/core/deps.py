"""
FastAPI dependencies for authentication and database.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import check_permission, decode_token
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.usage import UsageType
from app.services.rate_limiter import (
    get_rate_limiter,
    RateLimiter,
    UsageTracker,
    PLAN_QUOTAS,
)

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user is active."""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_permission(permission: str):
    """Dependency factory for permission checking."""
    
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not check_permission(current_user.role.value, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user
    
    return permission_checker


def require_roles(*roles: UserRole):
    """Dependency factory for role checking."""
    
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {', '.join(r.value for r in roles)}",
            )
        return current_user
    
    return role_checker


# Common dependencies
CurrentUser = Annotated[User, Depends(get_current_active_user)]
SuperAdmin = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]
TenantAdmin = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN))]


# Rate limiter dependency
async def get_rate_limiter_dep() -> RateLimiter:
    """Get rate limiter instance."""
    return get_rate_limiter()


# Quota enforcement dependencies
def require_quota(usage_type: UsageType, amount: int = 1):
    """
    Dependency factory for quota enforcement.

    Checks if tenant has remaining quota before allowing the operation.
    Raises 402 Payment Required if quota is exceeded.
    """

    async def quota_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
        rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
    ) -> User:
        from app.models.tenant import Tenant

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

        # Get quota limits for plan
        plan_quotas = PLAN_QUOTAS.get(tenant.plan, PLAN_QUOTAS["free"])

        # Get quota limit for this usage type
        quota_map = {
            UsageType.API_CALL: plan_quotas.api_calls,
            UsageType.CRAWL_PAGE: plan_quotas.crawl_pages,
            UsageType.KEYWORD_LOOKUP: plan_quotas.keyword_lookups,
            UsageType.AUDIT_RUN: plan_quotas.audits,
            UsageType.CONTENT_GENERATION: plan_quotas.content_generations,
            UsageType.JS_RENDER: plan_quotas.js_renders,
        }

        quota_limit = quota_map.get(usage_type, 0)

        # Check quota (0 = unlimited)
        if quota_limit > 0:
            quota_result = await rate_limiter.check_quota(
                tenant_id=str(current_user.tenant_id),
                usage_type=usage_type,
                quota_limit=quota_limit,
                increment=amount,
            )

            if not quota_result.allowed:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "message": f"Monthly {usage_type.value} quota exceeded",
                        "quota_type": usage_type.value,
                        "limit": quota_result.limit,
                        "used": quota_result.used,
                        "remaining": quota_result.remaining,
                        "upgrade_url": "/settings/billing",
                    },
                )

        return current_user

    return quota_checker


def track_usage(usage_type: UsageType, amount: int = 1):
    """
    Dependency for tracking usage without enforcing quota.

    Use this for operations where you want to track but not block.
    """

    async def usage_tracker(
        current_user: Annotated[User, Depends(get_current_active_user)],
        rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
    ) -> User:
        await rate_limiter.increment_usage(
            tenant_id=str(current_user.tenant_id),
            usage_type=usage_type,
            amount=amount,
        )
        return current_user

    return usage_tracker


async def set_tenant_context(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Set tenant context on request for middleware.

    This allows the rate limiting middleware to access tenant info.
    """
    from app.models.tenant import Tenant

    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if tenant:
        request.state.tenant_id = str(tenant.id)
        request.state.tenant_plan = tenant.plan

    return current_user


# Convenience dependencies for common quota checks
RequireCrawlQuota = Annotated[User, Depends(require_quota(UsageType.CRAWL_PAGE, 1))]
RequireAuditQuota = Annotated[User, Depends(require_quota(UsageType.AUDIT_RUN, 1))]
RequireKeywordQuota = Annotated[User, Depends(require_quota(UsageType.KEYWORD_LOOKUP, 1))]
RequireContentQuota = Annotated[User, Depends(require_quota(UsageType.CONTENT_GENERATION, 1))]
RequireJSRenderQuota = Annotated[User, Depends(require_quota(UsageType.JS_RENDER, 1))]
