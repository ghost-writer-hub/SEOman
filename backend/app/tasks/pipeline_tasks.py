"""
Pipeline Tasks

End-to-end SEO analysis pipeline that orchestrates:
1. Site crawling using SEOman v2.0 Crawler
2. 100-point SEO audit using new Audit Engine
3. AI-powered plan generation
4. Content brief creation
5. Markdown report generation
6. Upload to S3/B2 storage
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_sync_compatible_session_maker
from app.models.site import Site
from app.models.tenant import Tenant
from app.models.audit import AuditRun, SeoIssue, SEOAuditCheck
from app.models.plan import SeoPlan, SeoTask
from app.models.crawl import JobStatus
from app.services.crawler import SEOmanCrawler, CrawlConfig, crawl_site, pages_to_dict_list
from app.services.audit_engine import SEOAuditEngine, CrawlData, fetch_robots_txt, fetch_sitemap
from app.integrations.llm import get_llm_client, analyze_seo_issues
from app.integrations.storage import get_storage_client, SEOmanStoragePaths
from app.services.markdown_generator import MarkdownGenerator, generate_full_report_package
from app.agents.workflows.plan_workflow import run_plan_workflow

# Configure logging
logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_full_seo_pipeline(
    self,
    url: str,
    tenant_id: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run complete SEO analysis pipeline for a URL.
    
    This is the main entry point that orchestrates:
    1. Site crawling using SEOman v2.0 Crawler
    2. 100-point technical SEO audit
    3. AI-powered issue analysis
    4. SEO improvement plan generation
    5. Content brief generation (optional)
    6. Markdown report generation
    7. Upload to S3/B2 storage
    
    Args:
        url: Website URL to analyze
        tenant_id: Optional tenant ID (creates default if not provided)
        options: Pipeline options:
            - max_pages: Maximum pages to crawl (default: 100)
            - generate_briefs: Whether to generate content briefs (default: True)
            - plan_duration_weeks: Plan duration in weeks (default: 12)
            - seed_keywords: Optional seed keywords for planning
    
    Returns:
        Dictionary with report URLs and summary
    """
    return run_async(_run_full_seo_pipeline(self, url, tenant_id, options))


async def _run_full_seo_pipeline(
    task,
    url: str,
    tenant_id: str | None,
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    """Async implementation of the full SEO pipeline using v2.0 components."""
    
    options = options or {}
    max_pages = options.get("max_pages", 100)
    generate_briefs = options.get("generate_briefs", True)
    plan_duration_weeks = options.get("plan_duration_weeks", 12)
    seed_keywords = options.get("seed_keywords", [])
    
    report_id = str(uuid4())
    started_at = datetime.utcnow()
    
    logger.info("=" * 60)
    logger.info(f"[PIPELINE v2.0] Starting SEO pipeline for: {url}")
    logger.info(f"[PIPELINE v2.0] Report ID: {report_id}")
    logger.info(f"[PIPELINE v2.0] Options: max_pages={max_pages}, generate_briefs={generate_briefs}, duration={plan_duration_weeks}w")
    logger.info("=" * 60)
    
    result: dict[str, Any] = {
        "report_id": report_id,
        "url": url,
        "status": "processing",
        "started_at": started_at.isoformat(),
    }
    
    try:
        session_maker = get_sync_compatible_session_maker()
        async with session_maker() as session:
            # Step 1: Get or create tenant and site
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 1/8: Get or create tenant and site...")
            tenant, site = await _get_or_create_site(session, url, tenant_id)
            tenant_id_str = str(tenant.id)
            site_id_str = str(site.id)
            logger.info(f"[PIPELINE v2.0] Step 1/8: Complete in {time.time() - step_start:.2f}s - tenant={tenant_id_str}, site={site_id_str}")
            
            result["tenant_id"] = tenant_id_str
            result["site_id"] = site_id_str
            
            # Step 2: Crawl site using v2.0 crawler
            step_start = time.time()
            logger.info(f"[PIPELINE v2.0] Step 2/8: Crawling site (max {max_pages} pages)...")
            pages, robots_info, sitemap_info = await crawl_site(
                site_url=url,
                max_pages=max_pages,
                tenant_id=tenant_id_str,
                site_id=site_id_str,
                crawl_id=report_id,
            )
            pages_dict = pages_to_dict_list(pages)
            logger.info(f"[PIPELINE v2.0] Step 2/8: Complete in {time.time() - step_start:.2f}s - crawled {len(pages)} pages")
            
            result["pages_crawled"] = len(pages)
            
            # Step 3: Run 100-point audit
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 3/8: Running 100-point SEO audit...")
            crawl_data = CrawlData(
                base_url=url,
                pages=pages_dict,
                robots_txt=robots_info,
                sitemap=sitemap_info,
            )
            audit_engine = SEOAuditEngine(crawl_data)
            audit_results = audit_engine.run_all_checks()
            audit_summary = audit_engine.get_summary()
            score = audit_engine.calculate_score()
            
            # Convert audit results to issues format for compatibility
            issues = _convert_audit_results_to_issues(audit_results)
            audit_data = {
                "score": score,
                "issues": issues,
                "audit_results": [r.to_dict() for r in audit_results],
                "summary": audit_summary,
            }
            
            logger.info(f"[PIPELINE v2.0] Step 3/8: Complete in {time.time() - step_start:.2f}s - score={score}, checks={len(audit_results)}, issues={len(issues)}")
            
            result["score"] = score
            result["issues_count"] = len(issues)
            result["checks_run"] = len(audit_results)
            
            # Step 4: Get AI recommendations (if LLM available)
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 4/8: Getting AI recommendations...")
            try:
                llm = get_llm_client()
                if await llm.health_check():
                    logger.info(f"[PIPELINE v2.0] Step 4/8: LLM available, analyzing {len(issues)} issues...")
                    recommendations = await analyze_seo_issues(llm, url, issues)
                    audit_data["recommendations"] = recommendations
                    logger.info(f"[PIPELINE v2.0] Step 4/8: Complete in {time.time() - step_start:.2f}s - got AI recommendations")
                else:
                    logger.warning("[PIPELINE v2.0] Step 4/8: LLM not available, skipping AI analysis")
            except Exception as e:
                logger.warning(f"[PIPELINE v2.0] Step 4/8: AI analysis failed (non-critical) - {type(e).__name__}: {e}")
            
            # Step 5: Generate SEO Plan
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 5/8: Generating SEO plan...")
            plan_data = await _generate_plan(
                url=url,
                audit_data=audit_data,
                seed_keywords=seed_keywords,
                plan_duration_weeks=plan_duration_weeks,
            )
            action_items = len(plan_data.get("action_plan", []))
            content_items = len(plan_data.get("content_calendar", []))
            logger.info(f"[PIPELINE v2.0] Step 5/8: Complete in {time.time() - step_start:.2f}s - {action_items} action items, {content_items} content items")
            
            # Step 6: Generate Content Briefs (optional)
            step_start = time.time()
            briefs_data: list[dict[str, Any]] = []
            if generate_briefs and plan_data.get("content_calendar"):
                logger.info(f"[PIPELINE v2.0] Step 6/8: Generating content briefs for {content_items} items...")
                briefs_data = await _generate_briefs(
                    plan_data.get("content_calendar", []),
                    plan_data.get("keyword_clusters", []),
                )
                logger.info(f"[PIPELINE v2.0] Step 6/8: Complete in {time.time() - step_start:.2f}s - {len(briefs_data)} briefs generated")
            else:
                logger.info(f"[PIPELINE v2.0] Step 6/8: Skipped (generate_briefs={generate_briefs}, content_items={content_items})")
            
            # Step 7: Generate Markdown Reports
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 7/8: Generating markdown reports...")
            reports = generate_full_report_package(
                site_url=url,
                audit_data=audit_data,
                plan_data=plan_data,
                briefs_data=briefs_data,
            )
            report_keys = list(reports.keys())
            logger.info(f"[PIPELINE v2.0] Step 7/8: Complete in {time.time() - step_start:.2f}s - reports: {report_keys}")
            
            # Step 8: Upload to Storage and Save to DB
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 8/8: Uploading reports and saving to database...")
            file_urls = await _upload_reports(
                tenant_id=tenant_id_str,
                site_id=site_id_str,
                report_id=report_id,
                reports=reports,
            )
            
            # Save audit to database with individual checks
            await _save_audit_to_db(
                session=session,
                site=site,
                audit_data=audit_data,
                audit_results=audit_results,
                report_id=report_id,
            )
            
            await session.commit()
            logger.info(f"[PIPELINE v2.0] Step 8/8: Complete in {time.time() - step_start:.2f}s - {len(file_urls)} files uploaded")
            
            completed_at = datetime.utcnow()
            duration_seconds = (completed_at - started_at).total_seconds()
            
            result.update({
                "status": "completed",
                "completed_at": completed_at.isoformat(),
                "duration_seconds": duration_seconds,
                "files": file_urls,
                "summary": {
                    "score": score,
                    "pages_crawled": len(pages),
                    "checks_run": len(audit_results),
                    "issues_found": len(issues),
                    "action_items": action_items,
                    "content_pieces_planned": content_items,
                    "briefs_generated": len(briefs_data),
                },
            })
            
            logger.info("=" * 60)
            logger.info(f"[PIPELINE v2.0] COMPLETED in {duration_seconds:.2f}s")
            logger.info(f"[PIPELINE v2.0] Score: {score}/100")
            logger.info(f"[PIPELINE v2.0] Pages: {len(pages)}")
            logger.info(f"[PIPELINE v2.0] Checks: {len(audit_results)}")
            logger.info(f"[PIPELINE v2.0] Issues: {len(issues)}")
            logger.info("=" * 60)
            
            return result
            
    except Exception as e:
        logger.error(f"[PIPELINE v2.0] FAILED: {type(e).__name__}: {e}", exc_info=True)
        result.update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        })
        
        # Retry on transient errors
        if "connection" in str(e).lower() or "timeout" in str(e).lower():
            logger.info("[PIPELINE v2.0] Transient error detected, scheduling retry...")
            raise task.retry(exc=e)
        
        return result


def _convert_audit_results_to_issues(audit_results: list) -> list[dict[str, Any]]:
    """Convert AuditCheckResult objects to issue format for compatibility."""
    issues = []
    
    for result in audit_results:
        if not result.passed:
            issue = {
                "type": f"check_{result.check_id}",
                "category": result.category,
                "severity": result.severity,
                "title": result.check_name,
                "description": result.recommendation,
                "suggested_fix": result.recommendation,
                "affected_urls": result.affected_urls[:10],
                "affected_count": result.affected_count,
                "check_id": result.check_id,
                "details": result.details,
            }
            issues.append(issue)
    
    return issues


async def _get_or_create_site(
    session: AsyncSession,
    url: str,
    tenant_id: str | None,
) -> tuple:
    """Get or create tenant and site for the URL."""
    
    # Clean URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    
    # Get or create tenant
    if tenant_id:
        tenant = await session.get(Tenant, UUID(tenant_id))
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
    else:
        # Find or create default tenant
        stmt = select(Tenant).where(Tenant.slug == "default")
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            tenant = Tenant(
                name="Default Tenant",
                slug="default",
            )
            session.add(tenant)
            await session.flush()
    
    # Find or create site
    stmt = select(Site).where(Site.primary_domain == domain, Site.tenant_id == tenant.id)
    result = await session.execute(stmt)
    site = result.scalar_one_or_none()
    
    if not site:
        site = Site(
            tenant_id=tenant.id,
            name=domain,
            primary_domain=domain,
        )
        session.add(site)
        await session.flush()
    
    return tenant, site


async def _generate_plan(
    url: str,
    audit_data: dict[str, Any],
    seed_keywords: list[str],
    plan_duration_weeks: int,
) -> dict[str, Any]:
    """Generate SEO improvement plan."""
    
    # Use the plan workflow
    try:
        result = await run_plan_workflow(
            url=url,
            seed_keywords=seed_keywords or ["seo", "optimization"],
            plan_duration_weeks=plan_duration_weeks,
            provided_audit={
                "score": audit_data.get("score", 0),
                "issues": audit_data.get("issues", []),
            },
        )
        
        if result.get("success"):
            return result
    except Exception:
        pass
    
    # Fallback: generate basic plan from audit issues
    issues = audit_data.get("issues", [])
    action_plan: list[dict[str, Any]] = []
    content_calendar: list[dict[str, Any]] = []
    
    # Phase 1: Quick wins (low severity issues)
    low_effort_issues = [i for i in issues if i.get("severity") in ["low", "medium"]]
    for idx, issue in enumerate(low_effort_issues[:5]):
        action_plan.append({
            "phase": 1,
            "phase_name": "Quick Wins",
            "week_start": 1,
            "week_end": 2,
            "priority": idx + 1,
            "task": f"Fix: {issue.get('title', 'Unknown issue')}",
            "description": issue.get("suggested_fix", ""),
            "type": "technical",
            "effort": "low",
            "expected_impact": "medium",
        })
    
    # Phase 2: Technical fixes (high severity issues)
    high_issues = [i for i in issues if i.get("severity") in ["high", "critical"]]
    for idx, issue in enumerate(high_issues[:5]):
        action_plan.append({
            "phase": 2,
            "phase_name": "Technical Optimization",
            "week_start": 2,
            "week_end": 4,
            "priority": len(action_plan) + 1,
            "task": f"Fix: {issue.get('title', 'Unknown issue')}",
            "description": issue.get("suggested_fix", ""),
            "type": "technical",
            "effort": "medium",
            "expected_impact": "high",
        })
    
    # Phase 3: Content (if seed keywords provided)
    if seed_keywords:
        for idx, keyword in enumerate(seed_keywords[:3]):
            week = 4 + (idx * 2)
            action_plan.append({
                "phase": 3,
                "phase_name": "Content Strategy",
                "week_start": week,
                "week_end": week + 2,
                "priority": len(action_plan) + 1,
                "task": f"Create content for: {keyword}",
                "description": f"Write comprehensive content targeting '{keyword}'",
                "type": "content",
                "effort": "high",
                "expected_impact": "high",
                "target_keywords": [keyword],
                "content_type": "Blog post",
            })
            
            content_calendar.append({
                "week": week,
                "publish_date": "",
                "title": f"Content for: {keyword}",
                "content_type": "Blog post",
                "target_keywords": [keyword],
                "status": "planned",
            })
    
    return {
        "success": True,
        "summary": {
            "current_score": audit_data.get("score", 0),
            "plan_duration_weeks": plan_duration_weeks,
            "total_action_items": len(action_plan),
            "technical_tasks": sum(1 for a in action_plan if a["type"] == "technical"),
            "content_tasks": sum(1 for a in action_plan if a["type"] == "content"),
            "content_pieces_planned": len(content_calendar),
            "phases": [
                {"number": 1, "name": "Quick Wins", "weeks": "1-2", "focus": "Low-effort fixes", "tasks": sum(1 for a in action_plan if a.get("phase") == 1)},
                {"number": 2, "name": "Technical Optimization", "weeks": "2-4", "focus": "Critical fixes", "tasks": sum(1 for a in action_plan if a.get("phase") == 2)},
                {"number": 3, "name": "Content Strategy", "weeks": f"4-{plan_duration_weeks}", "focus": "Content creation", "tasks": sum(1 for a in action_plan if a.get("phase") == 3)},
            ],
            "expected_outcomes": [
                f"Fix {len(issues)} technical issues",
                f"Create {len(content_calendar)} content pieces",
                f"Improve SEO score from {audit_data.get('score', 0)} to 85+",
            ],
        },
        "action_plan": action_plan,
        "content_calendar": content_calendar,
        "keyword_clusters": [],
    }


async def _generate_briefs(
    content_calendar: list[dict[str, Any]],
    keyword_clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate content briefs for planned content."""
    
    briefs: list[dict[str, Any]] = []
    
    # Try to use LLM for brief generation
    llm = None
    try:
        llm = get_llm_client()
        if not await llm.health_check():
            llm = None
    except Exception:
        pass
    
    for item in content_calendar[:5]:  # Limit to 5 briefs
        keywords = item.get("target_keywords", [])
        main_keyword = keywords[0] if keywords else item.get("title", "topic")
        
        if llm:
            try:
                from app.integrations.llm import generate_content_brief
                brief_data = await generate_content_brief(llm, main_keyword, [])
                brief_data["keyword"] = main_keyword
                brief_data["intent"] = "informational"
                briefs.append(brief_data)
                continue
            except Exception:
                pass
        
        # Fallback: basic brief
        briefs.append({
            "keyword": main_keyword,
            "intent": "informational",
            "title_suggestions": [
                f"Complete Guide to {main_keyword.title()}",
                f"How to Master {main_keyword.title()}",
                f"{main_keyword.title()}: Everything You Need to Know",
            ],
            "meta_description": f"Learn everything about {main_keyword}. Comprehensive guide with tips, examples, and best practices.",
            "target_word_count": 1500,
            "content_outline": [
                {"heading": "Introduction", "key_points": ["What is this about", "Why it matters"]},
                {"heading": "Key Concepts", "key_points": ["Main idea 1", "Main idea 2", "Main idea 3"]},
                {"heading": "How To / Best Practices", "key_points": ["Step 1", "Step 2", "Step 3"]},
                {"heading": "Conclusion", "key_points": ["Summary", "Next steps", "Call to action"]},
            ],
            "keywords_to_include": keywords + [main_keyword],
            "differentiation_angle": f"Provide unique insights and practical examples for {main_keyword}.",
        })
    
    return briefs


async def _upload_reports(
    tenant_id: str,
    site_id: str,
    report_id: str,
    reports: dict[str, Any],
) -> dict[str, Any]:
    """Upload markdown reports to storage and return URLs."""
    
    storage = get_storage_client()
    file_urls: dict[str, Any] = {}
    
    # Upload audit report
    if "audit_report" in reports:
        path = SEOmanStoragePaths.audit_report_md(tenant_id, site_id, report_id)
        storage.upload_markdown(path, reports["audit_report"])
        file_urls["audit_report"] = storage.get_presigned_url(path)
    
    # Upload SEO plan
    if "seo_plan" in reports:
        path = SEOmanStoragePaths.seo_plan_md(tenant_id, site_id, report_id)
        storage.upload_markdown(path, reports["seo_plan"])
        file_urls["seo_plan"] = storage.get_presigned_url(path)
    
    # Upload page fixes guide
    if "page_fixes" in reports:
        path = SEOmanStoragePaths.page_fixes_md(tenant_id, site_id, report_id)
        storage.upload_markdown(path, reports["page_fixes"])
        file_urls["page_fixes"] = storage.get_presigned_url(path)
    
    # Upload article briefs
    if "briefs" in reports and reports["briefs"]:
        file_urls["briefs"] = []
        for idx, brief in enumerate(reports["briefs"], 1):
            path = SEOmanStoragePaths.article_brief_md(
                tenant_id, site_id, report_id, idx, brief["slug"]
            )
            storage.upload_markdown(path, brief["content"])
            file_urls["briefs"].append({
                "keyword": brief["keyword"],
                "url": storage.get_presigned_url(path),
            })
    
    # Upload metadata
    metadata = {
        "report_id": report_id,
        "tenant_id": tenant_id,
        "site_id": site_id,
        "generated_at": datetime.utcnow().isoformat(),
        "files": list(file_urls.keys()),
    }
    metadata_path = SEOmanStoragePaths.report_metadata(tenant_id, site_id, report_id)
    storage.upload_json(metadata_path, metadata)
    file_urls["metadata"] = storage.get_presigned_url(metadata_path)
    
    return file_urls


async def _save_audit_to_db(
    session: AsyncSession,
    site: Site,
    audit_data: dict[str, Any],
    audit_results: list,
    report_id: str,
) -> AuditRun:
    """Save audit results to database including individual checks."""
    
    # Create audit run
    audit = AuditRun(
        site_id=site.id,
        audit_type="pipeline_v2",
        status=JobStatus.COMPLETED,
        score=audit_data.get("score", 0),
        summary=str(audit_data.get("summary", "")),
        findings_overview={
            "report_id": report_id,
            "issues_count": len(audit_data.get("issues", [])),
            "checks_run": len(audit_results),
            "audit_summary": audit_data.get("summary", {}),
        },
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    session.add(audit)
    await session.flush()
    
    # Save individual audit checks
    for result in audit_results:
        check = SEOAuditCheck(
            audit_run_id=audit.id,
            check_id=result.check_id,
            category=result.category,
            check_name=result.check_name,
            passed=result.passed,
            severity=result.severity,
            affected_count=result.affected_count,
            affected_urls=result.affected_urls[:20],  # Limit stored URLs
            details=result.details,
            recommendation=result.recommendation,
        )
        session.add(check)
    
    # Save issues (for backward compatibility)
    for issue_data in audit_data.get("issues", []):
        from app.models.audit import IssueSeverity
        
        severity_map = {
            "critical": IssueSeverity.CRITICAL,
            "high": IssueSeverity.HIGH,
            "medium": IssueSeverity.MEDIUM,
            "low": IssueSeverity.LOW,
        }
        
        issue = SeoIssue(
            audit_run_id=audit.id,
            site_id=site.id,
            type=issue_data.get("type", "unknown"),
            category=issue_data.get("category", "General"),
            severity=severity_map.get(issue_data.get("severity", "low"), IssueSeverity.LOW),
            title=issue_data.get("title", "Unknown Issue"),
            description=issue_data.get("description"),
            suggested_fix=issue_data.get("suggested_fix"),
            affected_urls=issue_data.get("affected_urls", []),
        )
        session.add(issue)
    
    return audit


@shared_task(bind=True)
def get_pipeline_status(self, report_id: str) -> dict[str, Any]:
    """Get status of a pipeline run by report ID."""
    try:
        storage = get_storage_client()
        return {
            "report_id": report_id,
            "status": "unknown",
            "message": "Status lookup requires report metadata",
        }
    except Exception as e:
        return {
            "report_id": report_id,
            "status": "error",
            "error": str(e),
        }
