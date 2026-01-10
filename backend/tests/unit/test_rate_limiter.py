"""
Unit tests for SEOman Rate Limiter Service.

Tests rate limiting functionality including:
- Redis-based sliding window rate limiting
- Monthly quota enforcement
- Usage tracking
- Plan-based limits
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rate_limiter import (
    RateLimiter,
    RateLimitResult,
    QuotaResult,
    PlanQuotas,
    PLAN_QUOTAS,
)
from app.models.usage import UsageType


class TestRateLimitResult:
    """Test RateLimitResult dataclass."""

    def test_allowed_result(self):
        """Test allowed rate limit result."""
        result = RateLimitResult(
            allowed=True,
            limit=100,
            remaining=95,
            reset_at=1704902400,
        )

        assert result.allowed is True
        assert result.limit == 100
        assert result.remaining == 95
        assert result.retry_after is None

    def test_blocked_result(self):
        """Test blocked rate limit result."""
        result = RateLimitResult(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=1704902400,
            retry_after=30,
        )

        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 30


class TestQuotaResult:
    """Test QuotaResult dataclass."""

    def test_allowed_quota(self):
        """Test allowed quota result."""
        result = QuotaResult(
            allowed=True,
            quota_type="api_call",
            limit=10000,
            used=500,
            remaining=9500,
        )

        assert result.allowed is True
        assert result.used == 500
        assert result.remaining == 9500

    def test_exceeded_quota(self):
        """Test exceeded quota result."""
        result = QuotaResult(
            allowed=False,
            quota_type="crawl_page",
            limit=5000,
            used=5000,
            remaining=0,
        )

        assert result.allowed is False
        assert result.remaining == 0


class TestPlanQuotas:
    """Test plan quota configurations."""

    def test_free_plan_quotas(self):
        """Test free plan has limited quotas."""
        free_quotas = PLAN_QUOTAS["free"]

        assert isinstance(free_quotas, PlanQuotas)
        assert free_quotas.rate_limit_per_minute == 30
        # Free tier should have limits
        assert free_quotas.api_calls > 0
        assert free_quotas.crawl_pages > 0

    def test_pro_plan_quotas(self):
        """Test pro plan has higher quotas than free."""
        free_quotas = PLAN_QUOTAS["free"]
        pro_quotas = PLAN_QUOTAS["pro"]

        assert pro_quotas.api_calls >= free_quotas.api_calls
        assert pro_quotas.crawl_pages >= free_quotas.crawl_pages
        assert pro_quotas.rate_limit_per_minute > free_quotas.rate_limit_per_minute

    def test_enterprise_plan_unlimited(self):
        """Test enterprise plan has unlimited quotas (0 = unlimited)."""
        enterprise_quotas = PLAN_QUOTAS["enterprise"]

        # 0 means unlimited
        assert enterprise_quotas.api_calls == 0
        assert enterprise_quotas.crawl_pages == 0
        assert enterprise_quotas.audits == 0
        # But rate limit should still exist
        assert enterprise_quotas.rate_limit_per_minute > 0

    def test_all_plans_exist(self):
        """Test all expected plans are defined."""
        assert "free" in PLAN_QUOTAS
        assert "pro" in PLAN_QUOTAS
        assert "enterprise" in PLAN_QUOTAS


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance."""
        return RateLimiter(redis_url="redis://localhost:6379")

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.incrby = AsyncMock(return_value=1)
        mock.expire = AsyncMock(return_value=True)

        # Pipeline mock
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 0, 1, True])

        mock.pipeline = MagicMock(return_value=pipeline_mock)
        mock.zrem = AsyncMock(return_value=1)
        mock.zrange = AsyncMock(return_value=[])
        mock.close = AsyncMock()

        return mock

    def test_rate_limit_key_generation(self, rate_limiter):
        """Test rate limit key format."""
        key = rate_limiter._rate_limit_key("tenant-123", "api")

        assert "ratelimit" in key
        assert "tenant-123" in key
        assert "api" in key

    def test_quota_key_generation(self, rate_limiter):
        """Test quota key format includes month."""
        key = rate_limiter._quota_key("tenant-123", "api_call")

        current_month = date.today().strftime("%Y-%m")
        assert "quota" in key
        assert "tenant-123" in key
        assert "api_call" in key
        assert current_month in key

    @pytest.mark.asyncio
    async def test_check_rate_limit_disabled(self, rate_limiter):
        """Test rate limiting when disabled."""
        with patch("app.services.rate_limiter.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = False

            result = await rate_limiter.check_rate_limit(
                tenant_id="tenant-123",
                limit_per_minute=60,
            )

            assert result.allowed is True
            assert result.remaining == 60

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit allows request when under limit."""
        rate_limiter._redis = mock_redis

        # Simulate under limit (0 current requests)
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[0, 0, 1, True])

        with patch("app.services.rate_limiter.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True

            result = await rate_limiter.check_rate_limit(
                tenant_id="tenant-123",
                limit_per_minute=60,
            )

            assert result.allowed is True
            assert result.remaining == 59  # 60 - 0 - 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limit blocks request when over limit."""
        rate_limiter._redis = mock_redis

        # Simulate at limit (60 current requests)
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[0, 60, 1, True])
        mock_redis.zrange = AsyncMock(return_value=[("1704902400", 1704902400)])

        with patch("app.services.rate_limiter.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True

            result = await rate_limiter.check_rate_limit(
                tenant_id="tenant-123",
                limit_per_minute=60,
            )

            assert result.allowed is False
            assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_increment_usage(self, rate_limiter, mock_redis):
        """Test usage increment."""
        rate_limiter._redis = mock_redis

        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[5, True])

        result = await rate_limiter.increment_usage(
            tenant_id="tenant-123",
            usage_type=UsageType.API_CALL,
            amount=1,
        )

        assert result == 5

    @pytest.mark.asyncio
    async def test_get_usage(self, rate_limiter, mock_redis):
        """Test getting current usage."""
        rate_limiter._redis = mock_redis
        mock_redis.get = AsyncMock(return_value="42")

        result = await rate_limiter.get_usage(
            tenant_id="tenant-123",
            usage_type=UsageType.API_CALL,
        )

        assert result == 42

    @pytest.mark.asyncio
    async def test_get_usage_none(self, rate_limiter, mock_redis):
        """Test getting usage when no data exists."""
        rate_limiter._redis = mock_redis
        mock_redis.get = AsyncMock(return_value=None)

        result = await rate_limiter.get_usage(
            tenant_id="tenant-123",
            usage_type=UsageType.API_CALL,
        )

        assert result == 0

    @pytest.mark.asyncio
    async def test_check_quota_unlimited(self, rate_limiter, mock_redis):
        """Test quota check with unlimited quota (0)."""
        rate_limiter._redis = mock_redis

        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[1, True])

        result = await rate_limiter.check_quota(
            tenant_id="tenant-123",
            usage_type=UsageType.API_CALL,
            quota_limit=0,  # Unlimited
            increment=1,
        )

        assert result.allowed is True
        assert result.limit == 0

    @pytest.mark.asyncio
    async def test_check_quota_allowed(self, rate_limiter, mock_redis):
        """Test quota check when under limit."""
        rate_limiter._redis = mock_redis
        mock_redis.get = AsyncMock(return_value="50")

        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[51, True])

        result = await rate_limiter.check_quota(
            tenant_id="tenant-123",
            usage_type=UsageType.API_CALL,
            quota_limit=100,
            increment=1,
        )

        assert result.allowed is True
        assert result.used == 51

    @pytest.mark.asyncio
    async def test_check_quota_exceeded(self, rate_limiter, mock_redis):
        """Test quota check when over limit."""
        rate_limiter._redis = mock_redis
        mock_redis.get = AsyncMock(return_value="100")

        result = await rate_limiter.check_quota(
            tenant_id="tenant-123",
            usage_type=UsageType.API_CALL,
            quota_limit=100,
            increment=1,
        )

        assert result.allowed is False
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_get_all_usage(self, rate_limiter, mock_redis):
        """Test getting all usage types."""
        rate_limiter._redis = mock_redis

        # Return different values for different usage types
        async def mock_get(key):
            if "api_call" in key:
                return "100"
            elif "crawl_page" in key:
                return "50"
            return "0"

        mock_redis.get = mock_get

        result = await rate_limiter.get_all_usage("tenant-123")

        assert isinstance(result, dict)
        assert UsageType.API_CALL.value in result
        assert UsageType.CRAWL_PAGE.value in result

    @pytest.mark.asyncio
    async def test_close_connection(self, rate_limiter, mock_redis):
        """Test closing Redis connection."""
        rate_limiter._redis = mock_redis

        await rate_limiter.close()

        mock_redis.close.assert_called_once()
        assert rate_limiter._redis is None


class TestUsageType:
    """Test UsageType enum."""

    def test_usage_types_exist(self):
        """Test all expected usage types exist."""
        assert UsageType.API_CALL.value == "api_call"
        assert UsageType.CRAWL_PAGE.value == "crawl_page"
        assert UsageType.KEYWORD_LOOKUP.value == "keyword_lookup"
        assert UsageType.AUDIT_RUN.value == "audit_run"
        assert UsageType.CONTENT_GENERATION.value == "content_generation"
        assert UsageType.JS_RENDER.value == "js_render"

    def test_usage_type_iteration(self):
        """Test iterating over usage types."""
        usage_types = list(UsageType)

        assert len(usage_types) == 6


class TestRateLimiterIntegration:
    """Integration-style tests for rate limiter (mocked Redis)."""

    @pytest.fixture
    def rate_limiter_with_mock(self, mock_redis):
        """Create rate limiter with mocked Redis."""
        limiter = RateLimiter()
        limiter._redis = mock_redis
        return limiter

    @pytest.mark.asyncio
    async def test_rate_limit_workflow(self, rate_limiter_with_mock, mock_redis):
        """Test typical rate limit check workflow."""
        limiter = rate_limiter_with_mock

        # Configure mock for under-limit scenario
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[0, 5, 1, True])

        with patch("app.services.rate_limiter.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True

            # First request - should be allowed
            result = await limiter.check_rate_limit(
                tenant_id="tenant-123",
                limit_per_minute=10,
            )

            assert result.allowed is True
            assert result.remaining == 4  # 10 - 5 - 1

    @pytest.mark.asyncio
    async def test_quota_workflow(self, rate_limiter_with_mock, mock_redis):
        """Test typical quota check workflow."""
        limiter = rate_limiter_with_mock

        # Start with no usage
        mock_redis.get = AsyncMock(return_value="0")
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[1, True])

        # Check quota
        result = await limiter.check_quota(
            tenant_id="tenant-123",
            usage_type=UsageType.AUDIT_RUN,
            quota_limit=10,
            increment=1,
        )

        assert result.allowed is True
        assert result.remaining == 8  # 10 - 1 - 1 (initial was 0, incremented to 1)

    @pytest.mark.asyncio
    async def test_burst_handling(self, rate_limiter_with_mock, mock_redis):
        """Test handling burst of requests."""
        limiter = rate_limiter_with_mock

        # Simulate burst - many requests in short time
        pipeline_mock = mock_redis.pipeline.return_value

        # First few requests allowed
        pipeline_mock.execute = AsyncMock(return_value=[0, 8, 1, True])

        with patch("app.services.rate_limiter.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True

            result = await limiter.check_rate_limit(
                tenant_id="tenant-123",
                limit_per_minute=10,
            )

            assert result.allowed is True
            assert result.remaining == 1  # Almost at limit
