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
from app.services.template_classifier import classify_site_templates, TemplateClassificationResult
from app.integrations.llm import get_llm_client, analyze_seo_issues
from app.integrations.dataforseo import DataForSEOClient
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
    do_keyword_research = options.get("keyword_research", True)
    classify_templates = options.get("classify_templates", True)
    target_country = options.get("country", "ES")  # Default to Spain for hotel sites
    target_language = options.get("language", "es")
    
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
            logger.info(f"[PIPELINE v2.0] Step 2/10: Complete in {time.time() - step_start:.2f}s - crawled {len(pages)} pages")
            logger.info(f"[PIPELINE v2.0] Sitemap had {sitemap_info.get('url_count', 0)} URLs")

            result["pages_crawled"] = len(pages)
            result["sitemap_urls"] = sitemap_info.get("url_count", 0)

            # Step 3: Classify pages into templates
            step_start = time.time()
            template_data: dict[str, Any] = {}
            if classify_templates and pages_dict:
                logger.info("[PIPELINE v2.0] Step 3/10: Classifying pages into templates...")
                try:
                    template_result = await classify_site_templates(url, pages_dict, use_llm=True)
                    template_data = template_result.to_dict()
                    template_count = len(template_result.templates)
                    logger.info(f"[PIPELINE v2.0] Step 3/10: Complete in {time.time() - step_start:.2f}s - {template_count} templates identified")
                    result["templates_count"] = template_count
                except Exception as e:
                    logger.warning(f"[PIPELINE v2.0] Step 3/10: Template classification failed (non-critical) - {e}")
            else:
                logger.info("[PIPELINE v2.0] Step 3/10: Skipped template classification")

            # Step 3.5: PageSpeed Insights Analysis (optional, runs after template classification)
            psi_snapshots = []
            from app.config import settings as app_settings
            if app_settings.PAGESPEED_API_KEY and pages_dict:
                step_start = time.time()
                logger.info("[PIPELINE v2.0] Step 3.5: Running PageSpeed Insights analysis...")
                try:
                    from app.services.performance_service import PerformanceService
                    from collections import defaultdict

                    # Group pages by template type and pick top 3 per template
                    by_template = defaultdict(list)
                    for page in pages_dict:
                        template = page.get("template_type") or "unknown"
                        by_template[template].append(page)

                    urls_to_analyze = []
                    for template, template_pages in by_template.items():
                        sorted_pages = sorted(
                            template_pages,
                            key=lambda x: x.get("word_count", 0),
                            reverse=True,
                        )
                        for p in sorted_pages[:app_settings.PAGESPEED_MAX_PAGES_PER_TEMPLATE]:
                            urls_to_analyze.append((p["url"], template))

                    if urls_to_analyze:
                        perf_service = PerformanceService(session)
                        psi_snapshots = await perf_service.analyze_urls(
                            site_id=site.id,
                            tenant_id=site.tenant_id,
                            urls_with_templates=urls_to_analyze,
                            strategies=["mobile"],  # Mobile-only for speed
                        )
                        logger.info(f"[PIPELINE v2.0] Step 3.5: Complete in {time.time() - step_start:.2f}s - {len(psi_snapshots)} pages analyzed")
                        result["psi_pages_analyzed"] = len(psi_snapshots)

                        # Calculate average score for result
                        scores = [s.performance_score for s in psi_snapshots if s.performance_score]
                        if scores:
                            result["psi_avg_score"] = sum(scores) // len(scores)
                except Exception as e:
                    logger.warning(f"[PIPELINE v2.0] Step 3.5: PageSpeed analysis failed (non-critical) - {e}")
            else:
                if not app_settings.PAGESPEED_API_KEY:
                    logger.info("[PIPELINE v2.0] Step 3.5: Skipped PageSpeed analysis (API key not configured)")
                else:
                    logger.info("[PIPELINE v2.0] Step 3.5: Skipped PageSpeed analysis (no pages)")

            # Step 4: Keyword research with DataForSEO
            step_start = time.time()
            keyword_data: dict[str, Any] = {"keywords": [], "clusters": []}
            if do_keyword_research and seed_keywords:
                logger.info(f"[PIPELINE v2.0] Step 4/10: Performing keyword research for {len(seed_keywords)} seed keywords...")
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc

                    dataforseo = DataForSEOClient()

                    # Get keywords for the domain
                    domain_keywords = await dataforseo.keywords_for_site(
                        domain=domain,
                        country=target_country,
                        language=target_language,
                        limit=50,
                    )

                    # Expand from seed keywords
                    if seed_keywords:
                        expanded_keywords = await dataforseo.keywords_for_keywords(
                            seed_keywords=seed_keywords[:5],
                            country=target_country,
                            language=target_language,
                            limit=50,
                        )
                        domain_keywords.extend(expanded_keywords)

                    # Deduplicate keywords
                    seen = set()
                    unique_keywords = []
                    for kw in domain_keywords:
                        kw_text = kw.get("text", "").lower()
                        if kw_text and kw_text not in seen:
                            seen.add(kw_text)
                            unique_keywords.append(kw)

                    keyword_data["keywords"] = unique_keywords[:100]
                    logger.info(f"[PIPELINE v2.0] Step 4/10: Complete in {time.time() - step_start:.2f}s - {len(unique_keywords)} keywords found")
                    result["keywords_found"] = len(unique_keywords)
                except Exception as e:
                    logger.warning(f"[PIPELINE v2.0] Step 4/10: Keyword research failed (non-critical) - {e}")
            else:
                logger.info("[PIPELINE v2.0] Step 4/10: Skipped keyword research (no seed keywords or disabled)")

            # Step 5: Run 100-point audit
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 5/10: Running 100-point SEO audit...")
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
            
            logger.info(f"[PIPELINE v2.0] Step 5/10: Complete in {time.time() - step_start:.2f}s - score={score}, checks={len(audit_results)}, issues={len(issues)}")
            
            result["score"] = score
            result["issues_count"] = len(issues)
            result["checks_run"] = len(audit_results)
            
            # Step 6: Get AI recommendations (if LLM available)
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 6/10: Getting AI recommendations...")
            try:
                llm = get_llm_client()
                if await llm.health_check():
                    logger.info(f"[PIPELINE v2.0] Step 6/10: LLM available, analyzing {len(issues)} issues...")
                    recommendations = await analyze_seo_issues(llm, url, issues)
                    audit_data["recommendations"] = recommendations
                    logger.info(f"[PIPELINE v2.0] Step 6/10: Complete in {time.time() - step_start:.2f}s - got AI recommendations")
                else:
                    logger.warning("[PIPELINE v2.0] Step 6/10: LLM not available, skipping AI analysis")
            except Exception as e:
                logger.warning(f"[PIPELINE v2.0] Step 6/10: AI analysis failed (non-critical) - {type(e).__name__}: {e}")

            # Step 7: Generate SEO Plan with templates and keywords
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 7/10: Generating SEO plan...")
            plan_data = await _generate_plan(
                url=url,
                audit_data=audit_data,
                seed_keywords=seed_keywords,
                plan_duration_weeks=plan_duration_weeks,
                template_data=template_data,
                keyword_data=keyword_data,
            )
            action_items = len(plan_data.get("action_plan", []))
            content_items = len(plan_data.get("content_calendar", []))
            logger.info(f"[PIPELINE v2.0] Step 7/10: Complete in {time.time() - step_start:.2f}s - {action_items} action items, {content_items} content items")

            # Step 8: Generate Content Briefs (optional)
            step_start = time.time()
            briefs_data: list[dict[str, Any]] = []
            if generate_briefs and plan_data.get("content_calendar"):
                logger.info(f"[PIPELINE v2.0] Step 8/10: Generating content briefs for {content_items} items...")
                briefs_data = await _generate_briefs(
                    plan_data.get("content_calendar", []),
                    plan_data.get("keyword_clusters", []),
                )
                logger.info(f"[PIPELINE v2.0] Step 8/10: Complete in {time.time() - step_start:.2f}s - {len(briefs_data)} briefs generated")
            else:
                logger.info(f"[PIPELINE v2.0] Step 8/10: Skipped (generate_briefs={generate_briefs}, content_items={content_items})")

            # Step 9: Generate Markdown Reports
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 9/10: Generating markdown reports...")
            reports = generate_full_report_package(
                site_url=url,
                audit_data=audit_data,
                plan_data=plan_data,
                briefs_data=briefs_data,
                template_data=template_data,
                keyword_data=keyword_data,
            )
            report_keys = list(reports.keys())
            logger.info(f"[PIPELINE v2.0] Step 9/10: Complete in {time.time() - step_start:.2f}s - reports: {report_keys}")

            # Step 10: Upload to Storage and Save to DB
            step_start = time.time()
            logger.info("[PIPELINE v2.0] Step 10/10: Uploading reports and saving to database...")
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
            logger.info(f"[PIPELINE v2.0] Step 10/10: Complete in {time.time() - step_start:.2f}s - {len(file_urls)} files uploaded")

            completed_at = datetime.utcnow()
            duration_seconds = (completed_at - started_at).total_seconds()

            result.update({
                "status": "completed",
                "completed_at": completed_at.isoformat(),
                "duration_seconds": duration_seconds,
                "files": file_urls,
                "templates": template_data,
                "keywords": keyword_data.get("keywords", [])[:20],  # Include top 20 keywords in response
                "summary": {
                    "score": score,
                    "pages_crawled": len(pages),
                    "sitemap_urls": sitemap_info.get("url_count", 0),
                    "checks_run": len(audit_results),
                    "issues_found": len(issues),
                    "templates_identified": len(template_data.get("templates", [])),
                    "keywords_found": len(keyword_data.get("keywords", [])),
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
    template_data: dict[str, Any] | None = None,
    keyword_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate SEO improvement plan using templates and keyword research."""

    template_data = template_data or {}
    keyword_data = keyword_data or {}
    keywords_found = keyword_data.get("keywords", [])

    # Use the plan workflow only if we don't have keyword research data
    # (the workflow doesn't use keyword_data, so skip it when we have keywords)
    if not keywords_found:
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

    # Fallback: generate basic plan from audit issues, templates, and keywords
    issues = audit_data.get("issues", [])
    templates = template_data.get("templates", [])
    action_plan: list[dict[str, Any]] = []
    content_calendar: list[dict[str, Any]] = []
    keyword_clusters: list[dict[str, Any]] = []

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

    # Phase 2b: Template-based fixes
    for template in templates[:5]:
        if template.get("seo_recommendations"):
            for rec in template.get("seo_recommendations", [])[:2]:
                action_plan.append({
                    "phase": 2,
                    "phase_name": "Template Optimization",
                    "week_start": 3,
                    "week_end": 4,
                    "priority": len(action_plan) + 1,
                    "task": f"[{template.get('name', 'Template')}] {rec}",
                    "description": f"Apply to all {template.get('page_count', 0)} pages using this template",
                    "type": "technical",
                    "effort": "medium",
                    "expected_impact": "high",
                    "template_id": template.get("template_id"),
                    "affected_pages": template.get("page_count", 0),
                })

    # Phase 3: Content strategy based on keywords
    # Sort keywords by search volume and difficulty
    sorted_keywords = sorted(
        keywords_found,
        key=lambda k: (k.get("search_volume") or 0) / max(k.get("difficulty") or 1, 1),
        reverse=True,
    )

    # Create keyword clusters by intent
    intent_groups: dict[str, list] = {}
    for kw in sorted_keywords[:30]:
        intent = kw.get("intent") or "informational"
        if intent not in intent_groups:
            intent_groups[intent] = []
        intent_groups[intent].append(kw)

    for intent, kws in intent_groups.items():
        keyword_clusters.append({
            "name": f"{intent.title()} Keywords",
            "intent": intent,
            "keywords": [k.get("text") for k in kws[:10]],
            "total_volume": sum(k.get("search_volume") or 0 for k in kws),
        })

    # Create content calendar from top keywords
    week = 4
    for idx, kw in enumerate(sorted_keywords[:10]):
        kw_text = kw.get("text", "")
        search_volume = kw.get("search_volume", 0)
        intent = kw.get("intent", "informational")

        # Determine content type based on intent
        if intent == "transactional":
            content_type = "Landing Page"
        elif intent == "commercial":
            content_type = "Comparison/Review"
        elif intent == "navigational":
            content_type = "Service Page"
        else:
            content_type = "Blog Post"

        action_plan.append({
            "phase": 3,
            "phase_name": "Content Strategy",
            "week_start": week,
            "week_end": week + 2,
            "priority": len(action_plan) + 1,
            "task": f"Create {content_type}: {kw_text}",
            "description": f"Target keyword with {search_volume:,} monthly searches ({intent} intent)",
            "type": "content",
            "effort": "high",
            "expected_impact": "high",
            "target_keywords": [kw_text],
            "content_type": content_type,
            "search_volume": search_volume,
            "intent": intent,
        })

        content_calendar.append({
            "week": week,
            "publish_date": "",
            "title": f"{content_type}: {kw_text}",
            "content_type": content_type,
            "target_keywords": [kw_text],
            "search_volume": search_volume,
            "intent": intent,
            "status": "planned",
        })

        if idx % 2 == 1:
            week += 1

    # Fallback: use seed keywords if no DataForSEO keywords available
    if not content_calendar and seed_keywords:
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
                "content_type": "Blog Post",
            })

            content_calendar.append({
                "week": week,
                "publish_date": "",
                "title": f"Content for: {keyword}",
                "content_type": "Blog Post",
                "target_keywords": [keyword],
                "status": "planned",
            })

    return {
        "success": True,
        "templates": templates,
        "summary": {
            "current_score": audit_data.get("score", 0),
            "plan_duration_weeks": plan_duration_weeks,
            "total_action_items": len(action_plan),
            "technical_tasks": sum(1 for a in action_plan if a["type"] == "technical"),
            "content_tasks": sum(1 for a in action_plan if a["type"] == "content"),
            "content_pieces_planned": len(content_calendar),
            "templates_analyzed": len(templates),
            "keywords_researched": len(keywords_found),
            "phases": [
                {"number": 1, "name": "Quick Wins", "weeks": "1-2", "focus": "Low-effort fixes", "tasks": sum(1 for a in action_plan if a.get("phase") == 1)},
                {"number": 2, "name": "Technical Optimization", "weeks": "2-4", "focus": "Critical fixes + template optimization", "tasks": sum(1 for a in action_plan if a.get("phase") == 2)},
                {"number": 3, "name": "Content Strategy", "weeks": f"4-{plan_duration_weeks}", "focus": "Keyword-driven content", "tasks": sum(1 for a in action_plan if a.get("phase") == 3)},
            ],
            "expected_outcomes": [
                f"Fix {len(issues)} technical issues",
                f"Optimize {sum(t.get('page_count', 0) for t in templates)} pages across {len(templates)} templates",
                f"Create {len(content_calendar)} content pieces targeting {sum(c.get('search_volume', 0) for c in content_calendar):,} monthly searches",
                f"Improve SEO score from {audit_data.get('score', 0)} to 85+",
            ],
        },
        "action_plan": action_plan,
        "content_calendar": content_calendar,
        "keyword_clusters": keyword_clusters,
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
        intent = item.get("intent", "informational")
        content_type = item.get("content_type", "Blog Post")
        search_volume = item.get("search_volume", 0)

        if llm:
            try:
                from app.integrations.llm import generate_content_brief
                brief_data = await generate_content_brief(llm, main_keyword, [])
                brief_data["keyword"] = main_keyword
                brief_data["intent"] = intent
                briefs.append(brief_data)
                continue
            except Exception:
                pass

        # Generate intent-specific brief
        brief = _generate_intent_based_brief(
            main_keyword, intent, content_type, search_volume, keywords
        )
        briefs.append(brief)

    return briefs


def _generate_intent_based_brief(
    keyword: str,
    intent: str,
    content_type: str,
    search_volume: int,
    related_keywords: list[str],
) -> dict[str, Any]:
    """Generate a content brief tailored to the search intent."""

    keyword_title = keyword.title()

    # Intent-specific templates
    if intent == "transactional":
        return {
            "keyword": keyword,
            "intent": intent,
            "content_type": content_type,
            "search_volume": search_volume,
            "title_suggestions": [
                f"Book {keyword_title} - Best Rates & Availability",
                f"{keyword_title} | Official Reservations",
                f"Reserve {keyword_title} - Exclusive Offers Available",
            ],
            "meta_description": f"Book {keyword} with best price guarantee. Check availability, compare rates, and secure your reservation today. Special offers available.",
            "target_word_count": 800,
            "content_outline": [
                {"heading": "Overview", "key_points": ["Location highlights", "Key features & amenities", "Star rating & reviews"]},
                {"heading": "Room Types & Rates", "key_points": ["Room categories", "Price comparison", "What's included"]},
                {"heading": "Booking Information", "key_points": ["How to book", "Cancellation policy", "Payment options"]},
                {"heading": "Special Offers", "key_points": ["Current promotions", "Seasonal deals", "Package deals"]},
                {"heading": "Guest Reviews", "key_points": ["Recent testimonials", "Rating summary", "What guests love"]},
            ],
            "keywords_to_include": list(set(related_keywords + [keyword, "book", "reserve", "rates", "availability"])),
            "differentiation_angle": "Focus on trust signals (reviews, guarantees), clear CTAs, and urgency elements.",
            "cta_suggestions": ["Book Now", "Check Availability", "Get Best Price"],
        }

    elif intent == "commercial":
        return {
            "keyword": keyword,
            "intent": intent,
            "content_type": content_type,
            "search_volume": search_volume,
            "title_suggestions": [
                f"Best {keyword_title} - Expert Reviews & Comparison",
                f"Top {keyword_title} Ranked for 2025",
                f"{keyword_title} Guide: Which One Is Right for You?",
            ],
            "meta_description": f"Compare the best {keyword} options with our expert guide. Detailed reviews, pros & cons, and recommendations to help you choose.",
            "target_word_count": 2000,
            "content_outline": [
                {"heading": "Introduction", "key_points": ["Why this comparison matters", "Selection criteria", "How we evaluated"]},
                {"heading": "Quick Comparison Table", "key_points": ["Side-by-side features", "Price ranges", "Our ratings"]},
                {"heading": "Detailed Reviews", "key_points": ["Option 1 deep-dive", "Option 2 deep-dive", "Option 3 deep-dive"]},
                {"heading": "Pros and Cons", "key_points": ["Strengths of each", "Weaknesses to consider", "Best for whom"]},
                {"heading": "How to Choose", "key_points": ["Key factors to consider", "Budget considerations", "Specific needs matching"]},
                {"heading": "Our Recommendation", "key_points": ["Best overall", "Best value", "Best premium option"]},
            ],
            "keywords_to_include": list(set(related_keywords + [keyword, "best", "review", "compare", "top", "vs"])),
            "differentiation_angle": "Provide genuine comparisons with real pros/cons. Include comparison tables and clear recommendations.",
            "cta_suggestions": ["See Full Details", "Compare Prices", "Read Full Review"],
        }

    elif intent == "navigational":
        return {
            "keyword": keyword,
            "intent": intent,
            "content_type": content_type,
            "search_volume": search_volume,
            "title_suggestions": [
                f"{keyword_title} - Official Information",
                f"About {keyword_title} | Location, Contact & Details",
                f"{keyword_title} - Everything You Need to Know",
            ],
            "meta_description": f"Official information about {keyword}. Find location details, contact information, hours, and everything you need to plan your visit.",
            "target_word_count": 1000,
            "content_outline": [
                {"heading": "About", "key_points": ["What it is", "History/background", "What makes it special"]},
                {"heading": "Location & Access", "key_points": ["Address", "How to get there", "Parking/transport"]},
                {"heading": "Services & Amenities", "key_points": ["Main offerings", "Facilities", "Special features"]},
                {"heading": "Contact Information", "key_points": ["Phone/email", "Business hours", "Social media"]},
                {"heading": "Nearby Attractions", "key_points": ["Points of interest", "Restaurants", "Activities"]},
            ],
            "keywords_to_include": list(set(related_keywords + [keyword, "location", "contact", "hours", "address"])),
            "differentiation_angle": "Focus on accurate, up-to-date practical information. Make it easy to find key details.",
            "cta_suggestions": ["Get Directions", "Contact Us", "Visit Website"],
        }

    else:  # informational (default)
        return {
            "keyword": keyword,
            "intent": intent,
            "content_type": content_type,
            "search_volume": search_volume,
            "title_suggestions": [
                f"Complete Guide to {keyword_title} (2025)",
                f"{keyword_title}: What You Need to Know Before You Go",
                f"Everything About {keyword_title} - Tips & Insights",
            ],
            "meta_description": f"Discover everything about {keyword}. Our comprehensive guide covers tips, recommendations, and insider knowledge to help you make the most of your experience.",
            "target_word_count": 1500,
            "content_outline": [
                {"heading": "Introduction", "key_points": ["What this guide covers", "Why it matters", "Who this is for"]},
                {"heading": "Overview", "key_points": ["Background information", "Key facts", "What to expect"]},
                {"heading": "Key Highlights", "key_points": ["Top features", "Must-see/must-do", "Hidden gems"]},
                {"heading": "Practical Tips", "key_points": ["Best time to visit/use", "Money-saving advice", "Common mistakes to avoid"]},
                {"heading": "Frequently Asked Questions", "key_points": ["Common question 1", "Common question 2", "Common question 3"]},
                {"heading": "Summary & Next Steps", "key_points": ["Key takeaways", "Related topics", "Action items"]},
            ],
            "keywords_to_include": list(set(related_keywords + [keyword, "guide", "tips", "how to", "best"])),
            "differentiation_angle": "Provide actionable insights and practical tips that readers can immediately use.",
            "cta_suggestions": ["Learn More", "Read Related Guide", "Get Started"],
        }


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
    
    # Upload template analysis report
    if "templates" in reports:
        path = f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/templates.md"
        storage.upload_markdown(path, reports["templates"])
        file_urls["templates"] = storage.get_presigned_url(path)

    # Upload keyword research report
    if "keywords" in reports:
        path = f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/keywords.md"
        storage.upload_markdown(path, reports["keywords"])
        file_urls["keywords"] = storage.get_presigned_url(path)

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
