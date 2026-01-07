"""
Crawl Tasks

Background tasks for website crawling operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.crawl import CrawlJob, CrawlStatus, CrawlPage
from app.models.site import Site
from app.integrations.seoanalyzer import SEOAnalyzerClient


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(bind=True, max_retries=3)
def start_crawl(self, crawl_id: str, site_id: str, tenant_id: str):
    """Start a new crawl job."""
    return run_async(_start_crawl(self, crawl_id, site_id, tenant_id))


async def _start_crawl(task, crawl_id: str, site_id: str, tenant_id: str):
    """Async implementation of crawl start."""
    async with async_session_maker() as session:
        # Get site and crawl job
        site = await session.get(Site, UUID(site_id))
        crawl = await session.get(CrawlJob, UUID(crawl_id))
        
        if not site or not crawl:
            return {"error": "Site or crawl not found"}
        
        # Update status to running
        crawl.status = CrawlStatus.RUNNING
        crawl.started_at = datetime.utcnow()
        await session.commit()
        
        try:
            # Use SEO Analyzer for crawling
            analyzer = SEOAnalyzerClient()
            
            # Run analysis
            result = await analyzer.analyze(
                url=site.url,
                follow_links=True,
                max_pages=crawl.max_pages or 100,
            )
            
            if result.get("success"):
                # Store pages
                pages_data = result.get("pages", [])
                for page_data in pages_data:
                    page = CrawlPage(
                        crawl_id=crawl.id,
                        url=page_data.get("url", ""),
                        status_code=page_data.get("status_code", 200),
                        title=page_data.get("title"),
                        meta_description=page_data.get("meta_description"),
                        h1=page_data.get("h1"),
                        word_count=page_data.get("word_count", 0),
                        load_time_ms=page_data.get("load_time_ms"),
                        issues=page_data.get("issues", []),
                    )
                    session.add(page)
                
                # Update crawl status
                crawl.status = CrawlStatus.COMPLETED
                crawl.completed_at = datetime.utcnow()
                crawl.pages_crawled = len(pages_data)
                crawl.issues_found = sum(
                    len(p.get("issues", [])) for p in pages_data
                )
                
            else:
                crawl.status = CrawlStatus.FAILED
                crawl.error_message = result.get("error", "Unknown error")
                crawl.completed_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "crawl_id": crawl_id,
                "status": crawl.status.value,
                "pages_crawled": crawl.pages_crawled,
            }
            
        except Exception as e:
            crawl.status = CrawlStatus.FAILED
            crawl.error_message = str(e)
            crawl.completed_at = datetime.utcnow()
            await session.commit()
            
            raise task.retry(exc=e, countdown=60)


@shared_task(bind=True)
def check_stale_crawls(self):
    """Check for and handle stale crawl jobs."""
    return run_async(_check_stale_crawls())


async def _check_stale_crawls():
    """Mark long-running crawls as failed."""
    async with async_session_maker() as session:
        # Find crawls running for more than 2 hours
        stale_threshold = datetime.utcnow() - timedelta(hours=2)
        
        stmt = (
            update(CrawlJob)
            .where(
                CrawlJob.status == CrawlStatus.RUNNING,
                CrawlJob.started_at < stale_threshold,
            )
            .values(
                status=CrawlStatus.FAILED,
                error_message="Crawl timed out",
                completed_at=datetime.utcnow(),
            )
        )
        
        result = await session.execute(stmt)
        await session.commit()
        
        return {"stale_crawls_marked": result.rowcount}


@shared_task(bind=True)
def resume_crawl(self, crawl_id: str):
    """Resume a paused crawl job."""
    return run_async(_resume_crawl(crawl_id))


async def _resume_crawl(crawl_id: str):
    """Resume crawl from where it left off."""
    async with async_session_maker() as session:
        crawl = await session.get(CrawlJob, UUID(crawl_id))
        
        if not crawl:
            return {"error": "Crawl not found"}
        
        if crawl.status != CrawlStatus.PAUSED:
            return {"error": f"Crawl is not paused, status: {crawl.status}"}
        
        crawl.status = CrawlStatus.RUNNING
        await session.commit()
        
        # Continue crawl logic here...
        
        return {"crawl_id": crawl_id, "status": "resumed"}


@shared_task(bind=True)
def cancel_crawl(self, crawl_id: str):
    """Cancel a running crawl job."""
    return run_async(_cancel_crawl(crawl_id))


async def _cancel_crawl(crawl_id: str):
    """Cancel and cleanup a crawl job."""
    async with async_session_maker() as session:
        crawl = await session.get(CrawlJob, UUID(crawl_id))
        
        if not crawl:
            return {"error": "Crawl not found"}
        
        if crawl.status not in [CrawlStatus.PENDING, CrawlStatus.RUNNING]:
            return {"error": f"Cannot cancel crawl with status: {crawl.status}"}
        
        crawl.status = CrawlStatus.CANCELLED
        crawl.completed_at = datetime.utcnow()
        await session.commit()
        
        return {"crawl_id": crawl_id, "status": "cancelled"}
