"""
Rate Limiting Middleware

FastAPI middleware for API rate limiting using Redis.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.services.rate_limiter import get_rate_limiter, RateLimiter, UsageType

logger = logging.getLogger(__name__)

# Endpoints that don't require rate limiting
EXEMPT_PATHS = {
    "/health",
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Endpoints with custom rate limits (path prefix -> requests per minute)
CUSTOM_RATE_LIMITS = {
    "/api/v1/analyze": 10,  # Full pipeline is expensive
    "/api/v1/sites/{site_id}/audits": 20,
    "/api/v1/sites/{site_id}/keywords/discover": 20,
    "/api/v1/sites/{site_id}/rankings/update": 10,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.

    Uses Redis sliding window rate limiting per tenant.
    Adds rate limit headers to all responses.
    """

    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or get_rate_limiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if rate limiting is disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip exempt paths
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith("/static"):
            return await call_next(request)

        # Get tenant ID from request state (set by auth dependency)
        tenant_id = getattr(request.state, "tenant_id", None)

        if not tenant_id:
            # No tenant context - use IP-based limiting for unauthenticated requests
            client_ip = request.client.host if request.client else "unknown"
            tenant_id = f"ip:{client_ip}"
            limit_per_minute = 30  # Lower limit for unauthenticated
        else:
            # Get plan-specific limit
            plan = getattr(request.state, "tenant_plan", "free")
            limit_per_minute = self._get_rate_limit(path, plan)

        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(
            tenant_id=str(tenant_id),
            limit_per_minute=limit_per_minute,
            endpoint=self._normalize_path(path),
        )

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded for tenant {tenant_id} on {path}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": result.retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_at),
                    "Retry-After": str(result.retry_after or 60),
                },
            )

        # Track API call usage
        if tenant_id and not tenant_id.startswith("ip:"):
            await self.rate_limiter.increment_usage(
                str(tenant_id),
                UsageType.API_CALL,
                1,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_at)

        return response

    def _get_rate_limit(self, path: str, plan: str) -> int:
        """Get rate limit for a path based on plan."""
        # Check custom limits first
        for pattern, limit in CUSTOM_RATE_LIMITS.items():
            if self._path_matches(path, pattern):
                # Scale by plan
                if plan == "pro":
                    return limit * 4
                elif plan == "enterprise":
                    return limit * 20
                return limit

        # Default limits by plan
        if plan == "enterprise":
            return 600
        elif plan == "pro":
            return 120
        return settings.RATE_LIMIT_DEFAULT_PER_MINUTE

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern (simple prefix match)."""
        # Convert pattern to prefix
        prefix = pattern.split("{")[0]
        return path.startswith(prefix)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for rate limiting key."""
        # Remove IDs and UUIDs from path
        parts = path.split("/")
        normalized = []
        for part in parts:
            # Skip UUIDs and numeric IDs
            if len(part) == 36 and "-" in part:  # UUID
                normalized.append("{id}")
            elif part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)


def setup_rate_limit_middleware(app):
    """Add rate limiting middleware to the app."""
    app.add_middleware(RateLimitMiddleware)
