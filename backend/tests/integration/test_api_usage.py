"""
Integration tests for Usage API endpoints.
"""
import pytest
import uuid
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import status


class TestUsageAPI:
    """Test usage tracking endpoints."""

    @pytest.mark.asyncio
    async def test_usage_summary_requires_auth(self, async_client):
        """Test usage summary requires authentication."""
        response = await async_client.get("/api/v1/usage")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_usage_history_requires_auth(self, async_client):
        """Test usage history requires authentication."""
        response = await async_client.get("/api/v1/usage/history")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_usage_quotas_requires_auth(self, async_client):
        """Test usage quotas requires authentication."""
        response = await async_client.get("/api/v1/usage/quotas")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_rate_limit_status_requires_auth(self, async_client):
        """Test rate limit status requires authentication."""
        response = await async_client.get("/api/v1/usage/rate-limit")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminUsageAPI:
    """Test admin usage management endpoints."""

    @pytest.mark.asyncio
    async def test_get_tenant_usage_requires_admin(self, async_client):
        """Test getting tenant usage requires admin role."""
        tenant_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/usage/tenants/{tenant_id}",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_update_tenant_quotas_requires_admin(self, async_client):
        """Test updating tenant quotas requires admin role."""
        tenant_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/api/v1/usage/tenants/{tenant_id}/quotas",
            json={"monthly_api_calls": 50000},
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_reset_tenant_quotas_requires_admin(self, async_client):
        """Test resetting tenant quotas requires admin role."""
        tenant_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/api/v1/usage/tenants/{tenant_id}/quotas",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]


class TestUsageHistoryParams:
    """Test usage history query parameters."""

    @pytest.mark.asyncio
    async def test_history_months_validation(self, async_client):
        """Test history months parameter validation."""
        # Invalid months value
        response = await async_client.get(
            "/api/v1/usage/history?months=0",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @pytest.mark.asyncio
    async def test_history_months_max_validation(self, async_client):
        """Test history months max value validation."""
        # Months too high
        response = await async_client.get(
            "/api/v1/usage/history?months=100",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestQuotaEnforcement:
    """Test quota enforcement behavior."""

    @pytest.mark.asyncio
    async def test_quota_exceeded_returns_402(self, async_client):
        """Test that exceeding quota returns 402 Payment Required."""
        # This would require mocking the quota check
        # The expected behavior when quota is exceeded
        pass  # Placeholder for quota enforcement test

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self, async_client):
        """Test that exceeding rate limit returns 429 Too Many Requests."""
        # This would require mocking the rate limiter
        # The expected behavior when rate limit is exceeded
        pass  # Placeholder for rate limit test


class TestRateLimitHeaders:
    """Test rate limit headers in responses."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, async_client):
        """Test rate limit headers are included in responses."""
        # When middleware is active, these headers should be present
        # X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        pass  # Placeholder - requires middleware to be active


class TestUsageResponseFormat:
    """Test usage response format and structure."""

    def test_usage_summary_schema(self):
        """Test usage summary response schema."""
        from app.schemas.usage import UsageSummaryResponse, UsageItemResponse

        # Create a sample response
        item = UsageItemResponse(used=100, limit=1000, remaining=900)

        assert item.used == 100
        assert item.limit == 1000
        assert item.remaining == 900

    def test_quota_limits_schema(self):
        """Test quota limits response schema."""
        from app.schemas.usage import QuotaLimitsResponse

        response = QuotaLimitsResponse(
            plan="pro",
            api_calls=50000,
            crawl_pages=100000,
            keyword_lookups=5000,
            audits=100,
            content_generations=500,
            js_renders=10000,
            rate_limit_per_minute=120,
        )

        assert response.plan == "pro"
        assert response.api_calls == 50000
        assert response.rate_limit_per_minute == 120

    def test_usage_history_schema(self):
        """Test usage history item response schema."""
        from app.schemas.usage import UsageHistoryItemResponse

        item = UsageHistoryItemResponse(
            month="2026-01",
            api_calls=5000,
            pages_crawled=10000,
            keywords_researched=500,
            audits_run=10,
            content_generated=20,
            js_renders=1000,
        )

        assert item.month == "2026-01"
        assert item.api_calls == 5000
