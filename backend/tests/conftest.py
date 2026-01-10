"""
Pytest configuration and fixtures for SEOman tests.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event, JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Disable rate limiting for tests
os.environ["RATE_LIMIT_ENABLED"] = "false"

# IMPORTANT: Patch PostgreSQL types for SQLite compatibility
# Must be done before importing any models
import sqlalchemy.dialects.postgresql as pg_dialect
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator, CHAR
import uuid as uuid_module

# Custom UUID type that works with SQLite
class SQLiteUUID(TypeDecorator):
    """SQLite-compatible UUID type."""
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid_module.UUID(value)
        return value

pg_dialect.JSONB = JSON
pg_dialect.UUID = SQLiteUUID

from app.config import settings
from app.database import get_db
from app.models.base import Base
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User, UserRole, UserStatus
from app.models.site import Site
from app.models.usage import TenantUsage, TenantQuota, UsageType

# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session_with_data(db_session: AsyncSession) -> AsyncSession:
    """Database session with sample data pre-loaded."""
    # Create test tenant
    tenant = Tenant(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Test Tenant",
        slug="test-tenant",
        status=TenantStatus.ACTIVE,
        plan="pro",
    )
    db_session.add(tenant)

    # Create test user
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        email="test@example.com",
        name="Test User",
        password_hash="$2b$12$test_hash_for_testing_only",
        tenant_id=tenant.id,
        role=UserRole.TENANT_ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)

    # Create test site
    site = Site(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        tenant_id=tenant.id,
        name="Test Site",
        primary_domain="example.com",
    )
    db_session.add(site)

    await db_session.commit()

    return db_session


# ============================================================================
# FastAPI App Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def app(db_session: AsyncSession) -> FastAPI:
    """Create test FastAPI application."""
    from app.main import app as main_app

    async def override_get_db():
        yield db_session

    main_app.dependency_overrides[get_db] = override_get_db

    yield main_app

    main_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app: FastAPI) -> TestClient:
    """Create synchronous test client."""
    return TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def auth_headers() -> dict:
    """Create authentication headers with a valid test token."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={"sub": "00000000-0000-0000-0000-000000000002"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def super_admin_headers() -> dict:
    """Create authentication headers for super admin."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={"sub": "00000000-0000-0000-0000-000000000099"}
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client for rate limiting tests."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.incr = AsyncMock(return_value=1)
    mock.incrby = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.pipeline = MagicMock(return_value=mock)
    mock.execute = AsyncMock(return_value=[None, 0, True, True])
    mock.zremrangebyscore = AsyncMock(return_value=0)
    mock.zcard = AsyncMock(return_value=0)
    mock.zadd = AsyncMock(return_value=1)
    mock.zrem = AsyncMock(return_value=1)
    mock.zrange = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for crawler tests."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_storage():
    """Mock storage client for file operations."""
    mock = MagicMock()
    mock.upload_file = AsyncMock(return_value="https://storage.example.com/file.html")
    mock.download_file = AsyncMock(return_value=b"<html></html>")
    mock.delete_file = AsyncMock(return_value=True)
    mock.file_exists = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_dataforseo():
    """Mock DataForSEO client."""
    mock = AsyncMock()
    mock.get_keywords_for_site = AsyncMock(return_value=[
        {"keyword": "test keyword", "search_volume": 1000, "competition": 0.5},
    ])
    mock.get_serp_with_features = AsyncMock(return_value={
        "organic_results": [{"position": 1, "url": "https://example.com"}],
        "serp_features": {},
        "competitor_positions": [],
    })
    mock.get_rankings_batch = AsyncMock(return_value=[])
    return mock


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_crawl_pages() -> list[dict]:
    """Sample crawl page data for audit engine tests."""
    return [
        {
            "url": "https://example.com",
            "status_code": 200,
            "title": "Example Website - Home",
            "meta_description": "Welcome to our example website with great content.",
            "h1": ["Welcome to Example"],
            "h2": ["About Us", "Our Services"],
            "word_count": 500,
            "canonical_url": "https://example.com",
            "internal_links": [
                {"url": "https://example.com/about", "text": "About"},
                {"url": "https://example.com/services", "text": "Services"},
            ],
            "external_links": [],
            "images": [{"url": "https://example.com/logo.png", "alt": "Logo"}],
            "structured_data": [{"@type": "Organization", "name": "Example Inc"}],
            "open_graph": {"og:title": "Example Website"},
            "html_lang": "en",
            "has_viewport_meta": True,
            "noindex": False,
        },
        {
            "url": "https://example.com/about",
            "status_code": 200,
            "title": "About Us - Example Website",
            "meta_description": "Learn more about our company and team.",
            "h1": ["About Our Company"],
            "h2": ["Our Mission", "Our Team"],
            "word_count": 400,
            "canonical_url": "https://example.com/about",
            "internal_links": [
                {"url": "https://example.com", "text": "Home"},
            ],
            "external_links": [],
            "images": [],
            "structured_data": [],
            "html_lang": "en",
            "has_viewport_meta": True,
            "noindex": False,
        },
        {
            "url": "https://example.com/services",
            "status_code": 200,
            "title": "Services",  # Short title
            "meta_description": "",  # Missing description
            "h1": [],  # Missing H1
            "word_count": 150,  # Thin content
            "canonical_url": "https://example.com/services",
            "internal_links": [],
            "external_links": [],
            "images": [{"url": "https://example.com/service.jpg", "alt": ""}],  # Missing alt
            "structured_data": [],
            "html_lang": "",
            "has_viewport_meta": False,
            "noindex": False,
        },
    ]


@pytest.fixture
def sample_html_page() -> str:
    """Sample HTML page for crawler tests."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Page Title</title>
        <meta name="description" content="This is a test page description for SEO testing.">
        <link rel="canonical" href="https://example.com/test-page">
        <meta property="og:title" content="Test Page OG Title">
        <meta property="og:description" content="Test OG description">
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Test Page"
        }
        </script>
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>This is some test content for the page.</p>
        <h2>Secondary Heading</h2>
        <p>More content here with enough words to pass thin content checks.</p>
        <a href="/about">About Us</a>
        <a href="https://external.com">External Link</a>
        <img src="/image.jpg" alt="Test Image">
    </body>
    </html>
    """


@pytest.fixture
def sample_robots_txt() -> dict:
    """Sample robots.txt data."""
    return {
        "exists": True,
        "content": """
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /private/

Sitemap: https://example.com/sitemap.xml
        """,
        "url": "https://example.com/robots.txt",
    }


@pytest.fixture
def sample_sitemap() -> dict:
    """Sample sitemap data."""
    return {
        "exists": True,
        "url": "https://example.com/sitemap.xml",
        "urls": [
            "https://example.com",
            "https://example.com/about",
            "https://example.com/services",
            "https://example.com/contact",
        ],
        "url_count": 4,
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def freeze_time():
    """Fixture to freeze time at a specific datetime."""
    frozen_time = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = frozen_time
        mock_datetime.utcnow.return_value = frozen_time
        yield frozen_time


@pytest.fixture
def tenant_id() -> uuid.UUID:
    """Default test tenant ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def user_id() -> uuid.UUID:
    """Default test user ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def site_id() -> uuid.UUID:
    """Default test site ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000003")
