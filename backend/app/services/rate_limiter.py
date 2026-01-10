"""
Rate Limiter Service

Redis-based rate limiting and usage tracking for the SEOman API.
Implements:
- Sliding window rate limiting per tenant/user
- Monthly quota enforcement
- Usage tracking and reporting
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant
from app.models.usage import TenantUsage, TenantQuota, RateLimitEvent, UsageType

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: Optional[int] = None  # Seconds until retry


@dataclass
class QuotaResult:
    """Result of a quota check."""
    allowed: bool
    quota_type: str
    limit: int
    used: int
    remaining: int


@dataclass
class PlanQuotas:
    """Quota limits for a plan."""
    api_calls: int
    crawl_pages: int
    keyword_lookups: int
    audits: int
    content_generations: int
    js_renders: int
    rate_limit_per_minute: int


# Plan configurations
PLAN_QUOTAS = {
    "free": PlanQuotas(
        api_calls=settings.QUOTA_FREE_API_CALLS,
        crawl_pages=settings.QUOTA_FREE_CRAWL_PAGES,
        keyword_lookups=settings.QUOTA_FREE_KEYWORD_LOOKUPS,
        audits=settings.QUOTA_FREE_AUDITS,
        content_generations=settings.QUOTA_FREE_CONTENT_GENERATIONS,
        js_renders=settings.QUOTA_FREE_JS_RENDERS,
        rate_limit_per_minute=30,
    ),
    "pro": PlanQuotas(
        api_calls=settings.QUOTA_PRO_API_CALLS,
        crawl_pages=settings.QUOTA_PRO_CRAWL_PAGES,
        keyword_lookups=settings.QUOTA_PRO_KEYWORD_LOOKUPS,
        audits=settings.QUOTA_PRO_AUDITS,
        content_generations=settings.QUOTA_PRO_CONTENT_GENERATIONS,
        js_renders=settings.QUOTA_PRO_JS_RENDERS,
        rate_limit_per_minute=120,
    ),
    "enterprise": PlanQuotas(
        api_calls=settings.QUOTA_ENTERPRISE_API_CALLS,
        crawl_pages=settings.QUOTA_ENTERPRISE_CRAWL_PAGES,
        keyword_lookups=settings.QUOTA_ENTERPRISE_KEYWORD_LOOKUPS,
        audits=settings.QUOTA_ENTERPRISE_AUDITS,
        content_generations=settings.QUOTA_ENTERPRISE_CONTENT_GENERATIONS,
        js_renders=settings.QUOTA_ENTERPRISE_JS_RENDERS,
        rate_limit_per_minute=600,
    ),
}


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Uses a sorted set per tenant to track request timestamps,
    allowing for accurate rate limiting with minimal memory usage.
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _rate_limit_key(self, tenant_id: str, endpoint: str = "default") -> str:
        """Generate Redis key for rate limiting."""
        return f"ratelimit:{tenant_id}:{endpoint}"

    def _quota_key(self, tenant_id: str, usage_type: str) -> str:
        """Generate Redis key for quota tracking."""
        month = date.today().strftime("%Y-%m")
        return f"quota:{tenant_id}:{usage_type}:{month}"

    async def check_rate_limit(
        self,
        tenant_id: str,
        limit_per_minute: int,
        endpoint: str = "default",
    ) -> RateLimitResult:
        """
        Check if request is within rate limit using sliding window.

        Args:
            tenant_id: Tenant ID
            limit_per_minute: Maximum requests per minute
            endpoint: Optional endpoint-specific limit

        Returns:
            RateLimitResult with allowed status and metadata
        """
        if not settings.RATE_LIMIT_ENABLED:
            return RateLimitResult(
                allowed=True,
                limit=limit_per_minute,
                remaining=limit_per_minute,
                reset_at=0,
            )

        r = await self.get_redis()
        key = self._rate_limit_key(tenant_id, endpoint)
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - 60  # 1 minute window

        pipe = r.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry on key
        pipe.expire(key, 120)  # 2 minutes

        results = await pipe.execute()
        current_count = results[1]

        # Calculate remaining
        remaining = max(0, limit_per_minute - current_count - 1)
        reset_at = int(now + 60)

        if current_count >= limit_per_minute:
            # Over limit - remove the request we just added
            await r.zrem(key, str(now))

            # Calculate retry after
            oldest = await r.zrange(key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1] + 60 - now) if oldest else 60

            return RateLimitResult(
                allowed=False,
                limit=limit_per_minute,
                remaining=0,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        return RateLimitResult(
            allowed=True,
            limit=limit_per_minute,
            remaining=remaining,
            reset_at=reset_at,
        )

    async def increment_usage(
        self,
        tenant_id: str,
        usage_type: UsageType,
        amount: int = 1,
    ) -> int:
        """
        Increment usage counter in Redis.

        Args:
            tenant_id: Tenant ID
            usage_type: Type of usage
            amount: Amount to increment

        Returns:
            New usage count
        """
        r = await self.get_redis()
        key = self._quota_key(tenant_id, usage_type.value)

        # Increment and set expiry (40 days to cover month boundary)
        pipe = r.pipeline()
        pipe.incrby(key, amount)
        pipe.expire(key, 60 * 60 * 24 * 40)
        results = await pipe.execute()

        return results[0]

    async def get_usage(self, tenant_id: str, usage_type: UsageType) -> int:
        """Get current usage count from Redis."""
        r = await self.get_redis()
        key = self._quota_key(tenant_id, usage_type.value)
        value = await r.get(key)
        return int(value) if value else 0

    async def check_quota(
        self,
        tenant_id: str,
        usage_type: UsageType,
        quota_limit: int,
        increment: int = 1,
    ) -> QuotaResult:
        """
        Check if usage is within quota.

        Args:
            tenant_id: Tenant ID
            usage_type: Type of usage to check
            quota_limit: Maximum allowed (0 = unlimited)
            increment: Amount to add if allowed

        Returns:
            QuotaResult with allowed status and usage info
        """
        # Unlimited quota
        if quota_limit == 0:
            if increment > 0:
                await self.increment_usage(tenant_id, usage_type, increment)
            return QuotaResult(
                allowed=True,
                quota_type=usage_type.value,
                limit=0,
                used=0,
                remaining=0,
            )

        current = await self.get_usage(tenant_id, usage_type)
        remaining = max(0, quota_limit - current)

        if current + increment > quota_limit:
            return QuotaResult(
                allowed=False,
                quota_type=usage_type.value,
                limit=quota_limit,
                used=current,
                remaining=remaining,
            )

        # Increment usage
        if increment > 0:
            new_value = await self.increment_usage(tenant_id, usage_type, increment)
            remaining = max(0, quota_limit - new_value)

        return QuotaResult(
            allowed=True,
            quota_type=usage_type.value,
            limit=quota_limit,
            used=current + increment,
            remaining=remaining - increment if remaining > 0 else 0,
        )

    async def get_all_usage(self, tenant_id: str) -> dict[str, int]:
        """Get all usage counts for a tenant."""
        usage = {}
        for usage_type in UsageType:
            usage[usage_type.value] = await self.get_usage(tenant_id, usage_type)
        return usage


class UsageTracker:
    """
    Database-backed usage tracking for persistence and reporting.

    Syncs with Redis for real-time tracking but also stores in PostgreSQL
    for historical reporting and analytics.
    """

    def __init__(self, db: AsyncSession, rate_limiter: RateLimiter):
        self.db = db
        self.rate_limiter = rate_limiter

    async def get_or_create_monthly_usage(self, tenant_id: UUID) -> TenantUsage:
        """Get or create usage record for current month."""
        current_month = date.today().replace(day=1)

        result = await self.db.execute(
            select(TenantUsage).where(
                TenantUsage.tenant_id == tenant_id,
                TenantUsage.month == current_month,
            )
        )
        usage = result.scalar_one_or_none()

        if not usage:
            usage = TenantUsage(
                tenant_id=tenant_id,
                month=current_month,
            )
            self.db.add(usage)
            await self.db.flush()

        return usage

    async def get_tenant_quotas(self, tenant_id: UUID, plan: str) -> PlanQuotas:
        """Get quota limits for a tenant, considering custom overrides."""
        # Get base plan quotas
        base_quotas = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])

        # Check for custom quota overrides
        result = await self.db.execute(
            select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        )
        custom = result.scalar_one_or_none()

        if not custom:
            return base_quotas

        # Apply overrides
        return PlanQuotas(
            api_calls=custom.monthly_api_calls or base_quotas.api_calls,
            crawl_pages=custom.monthly_crawl_pages or base_quotas.crawl_pages,
            keyword_lookups=custom.monthly_keyword_lookups or base_quotas.keyword_lookups,
            audits=custom.monthly_audits or base_quotas.audits,
            content_generations=custom.monthly_content_generations or base_quotas.content_generations,
            js_renders=custom.monthly_js_renders or base_quotas.js_renders,
            rate_limit_per_minute=custom.rate_limit_per_minute or base_quotas.rate_limit_per_minute,
        )

    async def sync_usage_to_db(self, tenant_id: UUID):
        """Sync Redis usage counters to database."""
        usage = await self.get_or_create_monthly_usage(tenant_id)
        redis_usage = await self.rate_limiter.get_all_usage(str(tenant_id))

        usage.api_calls = redis_usage.get(UsageType.API_CALL.value, 0)
        usage.pages_crawled = redis_usage.get(UsageType.CRAWL_PAGE.value, 0)
        usage.keywords_researched = redis_usage.get(UsageType.KEYWORD_LOOKUP.value, 0)
        usage.audits_run = redis_usage.get(UsageType.AUDIT_RUN.value, 0)
        usage.content_generated = redis_usage.get(UsageType.CONTENT_GENERATION.value, 0)
        usage.js_renders = redis_usage.get(UsageType.JS_RENDER.value, 0)

        await self.db.flush()

    async def log_rate_limit_event(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID],
        endpoint: str,
        limit_type: str,
        limit_value: int,
        current_value: int,
    ):
        """Log a rate limit or quota exceeded event."""
        event = RateLimitEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            endpoint=endpoint,
            limit_type=limit_type,
            limit_value=limit_value,
            current_value=current_value,
        )
        self.db.add(event)
        await self.db.flush()

    async def get_usage_summary(self, tenant_id: UUID) -> dict:
        """Get usage summary for a tenant."""
        quotas = await self.get_tenant_quotas(tenant_id, "free")  # Get plan from tenant
        redis_usage = await self.rate_limiter.get_all_usage(str(tenant_id))

        return {
            "period": date.today().strftime("%Y-%m"),
            "usage": {
                "api_calls": {
                    "used": redis_usage.get(UsageType.API_CALL.value, 0),
                    "limit": quotas.api_calls,
                    "remaining": max(0, quotas.api_calls - redis_usage.get(UsageType.API_CALL.value, 0)) if quotas.api_calls > 0 else None,
                },
                "crawl_pages": {
                    "used": redis_usage.get(UsageType.CRAWL_PAGE.value, 0),
                    "limit": quotas.crawl_pages,
                    "remaining": max(0, quotas.crawl_pages - redis_usage.get(UsageType.CRAWL_PAGE.value, 0)) if quotas.crawl_pages > 0 else None,
                },
                "keyword_lookups": {
                    "used": redis_usage.get(UsageType.KEYWORD_LOOKUP.value, 0),
                    "limit": quotas.keyword_lookups,
                    "remaining": max(0, quotas.keyword_lookups - redis_usage.get(UsageType.KEYWORD_LOOKUP.value, 0)) if quotas.keyword_lookups > 0 else None,
                },
                "audits": {
                    "used": redis_usage.get(UsageType.AUDIT_RUN.value, 0),
                    "limit": quotas.audits,
                    "remaining": max(0, quotas.audits - redis_usage.get(UsageType.AUDIT_RUN.value, 0)) if quotas.audits > 0 else None,
                },
                "content_generations": {
                    "used": redis_usage.get(UsageType.CONTENT_GENERATION.value, 0),
                    "limit": quotas.content_generations,
                    "remaining": max(0, quotas.content_generations - redis_usage.get(UsageType.CONTENT_GENERATION.value, 0)) if quotas.content_generations > 0 else None,
                },
                "js_renders": {
                    "used": redis_usage.get(UsageType.JS_RENDER.value, 0),
                    "limit": quotas.js_renders,
                    "remaining": max(0, quotas.js_renders - redis_usage.get(UsageType.JS_RENDER.value, 0)) if quotas.js_renders > 0 else None,
                },
            },
            "rate_limit": {
                "requests_per_minute": quotas.rate_limit_per_minute,
            },
        }

    async def get_usage_history(
        self,
        tenant_id: UUID,
        months: int = 6,
    ) -> list[dict]:
        """Get usage history for past N months."""
        result = await self.db.execute(
            select(TenantUsage)
            .where(TenantUsage.tenant_id == tenant_id)
            .order_by(TenantUsage.month.desc())
            .limit(months)
        )
        records = result.scalars().all()

        return [
            {
                "month": record.month.strftime("%Y-%m"),
                "api_calls": record.api_calls,
                "pages_crawled": record.pages_crawled,
                "keywords_researched": record.keywords_researched,
                "audits_run": record.audits_run,
                "content_generated": record.content_generated,
                "js_renders": record.js_renders,
            }
            for record in records
        ]


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def close_rate_limiter():
    """Close the global rate limiter."""
    global _rate_limiter
    if _rate_limiter:
        await _rate_limiter.close()
        _rate_limiter = None
