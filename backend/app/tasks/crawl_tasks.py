"""
Crawl Tasks

Background tasks for website crawling operations.
Uses SEOman v2.0 crawler and audit engine.
"""

import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.crawl import CrawlJob, JobStatus, CrawlPage
from app.models.site import Site
from app.services.crawler import SEOmanCrawler, CrawlConfig, CrawledPage


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
    """Start a new crawl job using SEOman v2.0 crawler."""
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
        crawl.status = JobStatus.RUNNING
        crawl.started_at = datetime.utcnow()
        await session.commit()
        
        try:
            # Get crawl configuration
            config_data = crawl.config or {}
            max_pages = config_data.get("max_pages", 100)
            max_depth = config_data.get("max_depth", 10)
            
            # Create crawler config
            config = CrawlConfig(
                max_pages=max_pages,
                max_depth=max_depth,
                concurrent_requests=5,
                request_delay_ms=100,
                timeout_seconds=30,
                respect_robots_txt=True,
                store_html=True,
            )
            
            # Build site URL
            site_url = f"https://{site.primary_domain}"
            
            # Create and run crawler
            crawler = SEOmanCrawler(
                site_url=site_url,
                config=config,
                tenant_id=tenant_id,
                site_id=site_id,
                crawl_id=crawl_id,
            )
            
            pages = await crawler.crawl()
            
            # Store pages in database
            pages_stored = 0
            issues_found = 0
            
            for page_data in pages:
                crawl_page = _create_crawl_page(crawl.id, site.id, page_data)
                session.add(crawl_page)
                pages_stored += 1
                issues_found += len(page_data.errors)
            
            # Update crawl status
            crawl.status = JobStatus.COMPLETED
            crawl.completed_at = datetime.utcnow()
            crawl.pages_crawled = pages_stored
            crawl.errors_count = issues_found
            
            await session.commit()
            
            return {
                "crawl_id": crawl_id,
                "status": crawl.status.value,
                "pages_crawled": pages_stored,
                "issues_found": issues_found,
            }
            
        except Exception as e:
            crawl.status = JobStatus.FAILED
            crawl.error_message = str(e)
            crawl.completed_at = datetime.utcnow()
            await session.commit()
            
            raise task.retry(exc=e, countdown=60)


def _create_crawl_page(crawl_id: UUID, site_id: UUID, page: CrawledPage) -> CrawlPage:
    """Convert CrawledPage dataclass to CrawlPage model."""
    # Get first H1 as string for the model
    h1_text = page.h1[0] if page.h1 else None
    
    return CrawlPage(
        crawl_job_id=crawl_id,
        site_id=site_id,
        url=page.url,
        status_code=page.status_code,
        content_type=page.content_type,
        canonical_url=page.canonical_url or None,
        meta_robots=page.meta_robots or None,
        title=page.title or None,
        meta_description=page.meta_description or None,
        h1=h1_text,
        h2=page.h2,
        h3=page.h3,
        word_count=page.word_count,
        internal_links=page.internal_links,
        external_links=page.external_links,
        noindex=page.noindex,
        nofollow=page.nofollow,
        load_time_ms=page.load_time_ms,
        issues=page.errors,
        raw_html_path=page.raw_html_path or None,
        markdown_path=page.markdown_path or None,
        structured_data=page.structured_data,
        open_graph=page.open_graph,
        hreflang=page.hreflang,
        twitter_cards=page.twitter_cards,
        images=page.images,
        scripts_count=page.scripts_count,
        stylesheets_count=page.stylesheets_count,
        text_content_hash=page.text_content_hash or None,
    )


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
                CrawlJob.status == JobStatus.RUNNING,
                CrawlJob.started_at < stale_threshold,
            )
            .values(
                status=JobStatus.FAILED,
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
        
        if crawl.status != JobStatus.PAUSED:
            return {"error": f"Crawl is not paused, status: {crawl.status}"}
        
        crawl.status = JobStatus.RUNNING
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
        
        if crawl.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            return {"error": f"Cannot cancel crawl with status: {crawl.status}"}
        
        crawl.status = JobStatus.CANCELLED
        crawl.completed_at = datetime.utcnow()
        await session.commit()
        
        return {"crawl_id": crawl_id, "status": "cancelled"}
