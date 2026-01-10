"""
Database connection and session management for SEOman.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import settings
from app.models.base import Base

# Convert sync URL to async
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async_session_maker = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions (for background tasks)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_compatible_session_maker():
    """Create a fresh session maker for sync/Celery task execution.
    
    This creates a new engine and session maker that can be used in
    Celery workers running with their own event loops.
    """
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    task_engine = create_async_engine(db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return async_sessionmaker(task_engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Initialize database tables."""
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.site import Site
    from app.models.crawl import CrawlJob, CrawlPage
    from app.models.audit import AuditRun, SeoIssue
    from app.models.keyword import Keyword, KeywordCluster
    from app.models.plan import SeoPlan, SeoTask
    from app.models.content import ContentBrief, ContentDraft
    from app.models.usage import TenantUsage, TenantQuota, RateLimitEvent

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
