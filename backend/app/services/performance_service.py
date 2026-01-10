"""
Performance service for PageSpeed Insights analysis.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.pagespeed import PageSpeedClient
from app.models.performance import PerformanceSnapshot

logger = logging.getLogger(__name__)


class PerformanceService:
    """Service for PageSpeed Insights operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = PageSpeedClient()

    async def analyze_urls(
        self,
        site_id: UUID,
        tenant_id: UUID,
        urls_with_templates: list[tuple[str, str]],
        audit_run_id: UUID | None = None,
        strategies: list[str] | None = None,
    ) -> list[PerformanceSnapshot]:
        """
        Analyze URLs with PageSpeed Insights.

        Args:
            site_id: Site ID
            tenant_id: Tenant ID
            urls_with_templates: List of (url, template_type) tuples
            audit_run_id: Optional audit run ID to link results
            strategies: List of strategies ('mobile', 'desktop'). Default: both.

        Returns:
            List of created PerformanceSnapshot records
        """
        strategies = strategies or ["mobile", "desktop"]
        snapshots = []

        for url, template_type in urls_with_templates:
            for strategy in strategies:
                result = await self.client.analyze(url, strategy)

                if not result.get("success"):
                    logger.warning(
                        f"[PSI] Failed to analyze {url} ({strategy}): {result.get('error')}"
                    )
                    continue

                metrics = result.get("metrics", {})

                snapshot = PerformanceSnapshot(
                    tenant_id=tenant_id,
                    site_id=site_id,
                    audit_run_id=audit_run_id,
                    url=url,
                    template_type=template_type,
                    strategy=strategy,
                    performance_score=result.get("performance_score"),
                    lcp_ms=metrics.get("lcp_ms"),
                    fid_ms=metrics.get("fid_ms"),
                    cls=metrics.get("cls"),
                    fcp_ms=metrics.get("fcp_ms"),
                    ttfb_ms=metrics.get("ttfb_ms"),
                    tbt_ms=metrics.get("tbt_ms"),
                    speed_index_ms=metrics.get("speed_index_ms"),
                    tti_ms=metrics.get("tti_ms"),
                    inp_ms=result.get("field_data", {}).get("inp_ms"),
                    cwv_status=result.get("cwv_status"),
                    opportunities=result.get("opportunities", []),
                    diagnostics=result.get("diagnostics", {}),
                    field_data=result.get("field_data", {}),
                    checked_at=datetime.now(timezone.utc),
                )

                self.db.add(snapshot)
                snapshots.append(snapshot)
                logger.info(
                    f"[PSI] Analyzed {url} ({strategy}): score={result.get('performance_score')}"
                )

        if snapshots:
            await self.db.flush()

        return snapshots

    async def analyze_site_pages(
        self,
        site_id: UUID,
        tenant_id: UUID,
        pages: list[dict],
        audit_run_id: UUID | None = None,
        max_per_template: int | None = None,
    ) -> list[PerformanceSnapshot]:
        """
        Analyze top pages per template type.

        Args:
            site_id: Site ID
            tenant_id: Tenant ID
            pages: List of page dicts with 'url', 'template_type', 'word_count'
            audit_run_id: Optional audit run ID
            max_per_template: Max pages per template (default from config)

        Returns:
            List of created PerformanceSnapshot records
        """
        max_per_template = max_per_template or settings.PAGESPEED_MAX_PAGES_PER_TEMPLATE

        # Group pages by template type
        by_template = defaultdict(list)
        for page in pages:
            template = page.get("template_type") or "unknown"
            by_template[template].append(page)

        # Select top N pages per template (by word count)
        urls_to_analyze = []
        for template, template_pages in by_template.items():
            sorted_pages = sorted(
                template_pages,
                key=lambda x: x.get("word_count", 0),
                reverse=True,
            )
            for page in sorted_pages[:max_per_template]:
                urls_to_analyze.append((page["url"], template))

        logger.info(
            f"[PSI] Analyzing {len(urls_to_analyze)} URLs across {len(by_template)} templates"
        )

        return await self.analyze_urls(
            site_id=site_id,
            tenant_id=tenant_id,
            urls_with_templates=urls_to_analyze,
            audit_run_id=audit_run_id,
        )

    async def get_latest_snapshots(
        self,
        site_id: UUID,
        strategy: str | None = None,
        template_type: str | None = None,
        limit: int = 50,
    ) -> list[PerformanceSnapshot]:
        """Get most recent snapshots for a site."""
        # Subquery to get latest checked_at per url/strategy
        subquery = (
            select(
                PerformanceSnapshot.url,
                PerformanceSnapshot.strategy,
                func.max(PerformanceSnapshot.checked_at).label("max_checked"),
            )
            .where(PerformanceSnapshot.site_id == site_id)
            .group_by(PerformanceSnapshot.url, PerformanceSnapshot.strategy)
            .subquery()
        )

        query = (
            select(PerformanceSnapshot)
            .join(
                subquery,
                (PerformanceSnapshot.url == subquery.c.url)
                & (PerformanceSnapshot.strategy == subquery.c.strategy)
                & (PerformanceSnapshot.checked_at == subquery.c.max_checked),
            )
            .where(PerformanceSnapshot.site_id == site_id)
        )

        if strategy:
            query = query.where(PerformanceSnapshot.strategy == strategy)
        if template_type:
            query = query.where(PerformanceSnapshot.template_type == template_type)

        query = query.order_by(PerformanceSnapshot.checked_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_performance_history(
        self,
        site_id: UUID,
        url: str,
        strategy: str = "mobile",
        days: int = 30,
    ) -> list[PerformanceSnapshot]:
        """Get performance history for a specific URL."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(PerformanceSnapshot)
            .where(
                PerformanceSnapshot.site_id == site_id,
                PerformanceSnapshot.url == url,
                PerformanceSnapshot.strategy == strategy,
                PerformanceSnapshot.checked_at >= since,
            )
            .order_by(PerformanceSnapshot.checked_at.asc())
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_site_summary(self, site_id: UUID) -> dict:
        """Get aggregated performance summary for a site."""
        # Get latest snapshots
        snapshots = await self.get_latest_snapshots(site_id, limit=100)

        if not snapshots:
            return {
                "site_id": site_id,
                "total_snapshots": 0,
                "pages_analyzed": 0,
                "avg_mobile_score": None,
                "avg_desktop_score": None,
                "cwv_pass_rate": 0,
                "avg_lcp_ms": None,
                "avg_cls": None,
                "avg_fcp_ms": None,
                "avg_ttfb_ms": None,
                "worst_lcp_pages": [],
                "worst_cls_pages": [],
                "slowest_pages": [],
                "common_opportunities": [],
                "last_analyzed": None,
            }

        # Separate by strategy
        mobile = [s for s in snapshots if s.strategy == "mobile"]
        desktop = [s for s in snapshots if s.strategy == "desktop"]

        # Calculate averages
        def avg(values):
            valid = [v for v in values if v is not None]
            return sum(valid) / len(valid) if valid else None

        mobile_scores = [s.performance_score for s in mobile]
        desktop_scores = [s.performance_score for s in desktop]

        # CWV pass rate (pages with "good" status)
        cwv_statuses = [s.cwv_status for s in snapshots if s.cwv_status]
        cwv_pass_rate = (
            len([s for s in cwv_statuses if s == "good"]) / len(cwv_statuses) * 100
            if cwv_statuses
            else 0
        )

        # Worst LCP pages
        lcp_sorted = sorted(
            [s for s in mobile if s.lcp_ms is not None],
            key=lambda x: x.lcp_ms,
            reverse=True,
        )
        worst_lcp = [
            {"url": s.url, "lcp_ms": s.lcp_ms, "score": s.performance_score}
            for s in lcp_sorted[:5]
        ]

        # Worst CLS pages
        cls_sorted = sorted(
            [s for s in mobile if s.cls is not None],
            key=lambda x: x.cls,
            reverse=True,
        )
        worst_cls = [
            {"url": s.url, "cls": s.cls, "score": s.performance_score}
            for s in cls_sorted[:5]
        ]

        # Slowest pages (by score)
        score_sorted = sorted(
            [s for s in mobile if s.performance_score is not None],
            key=lambda x: x.performance_score,
        )
        slowest = [
            {"url": s.url, "score": s.performance_score, "lcp_ms": s.lcp_ms}
            for s in score_sorted[:5]
        ]

        # Aggregate opportunities
        opp_counts = defaultdict(lambda: {"count": 0, "total_savings_ms": 0})
        for snapshot in snapshots:
            for opp in snapshot.opportunities or []:
                opp_id = opp.get("id", "unknown")
                opp_counts[opp_id]["count"] += 1
                opp_counts[opp_id]["total_savings_ms"] += opp.get("savings_ms", 0)
                opp_counts[opp_id]["title"] = opp.get("title", opp_id)

        common_opportunities = sorted(
            [
                {
                    "id": k,
                    "title": v["title"],
                    "affected_pages": v["count"],
                    "total_savings_ms": v["total_savings_ms"],
                }
                for k, v in opp_counts.items()
            ],
            key=lambda x: x["affected_pages"],
            reverse=True,
        )[:10]

        # Last analyzed
        last_analyzed = max(s.checked_at for s in snapshots) if snapshots else None

        # Unique pages
        unique_urls = set(s.url for s in snapshots)

        return {
            "site_id": site_id,
            "total_snapshots": len(snapshots),
            "pages_analyzed": len(unique_urls),
            "avg_mobile_score": round(avg(mobile_scores), 1) if avg(mobile_scores) else None,
            "avg_desktop_score": round(avg(desktop_scores), 1) if avg(desktop_scores) else None,
            "cwv_pass_rate": round(cwv_pass_rate, 1),
            "avg_lcp_ms": int(avg([s.lcp_ms for s in mobile])) if avg([s.lcp_ms for s in mobile]) else None,
            "avg_cls": round(avg([s.cls for s in mobile]), 3) if avg([s.cls for s in mobile]) else None,
            "avg_fcp_ms": int(avg([s.fcp_ms for s in mobile])) if avg([s.fcp_ms for s in mobile]) else None,
            "avg_ttfb_ms": int(avg([s.ttfb_ms for s in mobile])) if avg([s.ttfb_ms for s in mobile]) else None,
            "worst_lcp_pages": worst_lcp,
            "worst_cls_pages": worst_cls,
            "slowest_pages": slowest,
            "common_opportunities": common_opportunities,
            "last_analyzed": last_analyzed,
        }

    async def get_opportunities_summary(self, site_id: UUID) -> list[dict]:
        """Get aggregated optimization opportunities across all pages."""
        snapshots = await self.get_latest_snapshots(site_id, strategy="mobile", limit=100)

        opp_data = defaultdict(
            lambda: {
                "count": 0,
                "total_savings_ms": 0,
                "total_savings_bytes": 0,
                "scores": [],
                "pages": [],
            }
        )

        for snapshot in snapshots:
            for opp in snapshot.opportunities or []:
                opp_id = opp.get("id", "unknown")
                opp_data[opp_id]["title"] = opp.get("title", opp_id)
                opp_data[opp_id]["description"] = opp.get("description", "")
                opp_data[opp_id]["count"] += 1
                opp_data[opp_id]["total_savings_ms"] += opp.get("savings_ms", 0)
                opp_data[opp_id]["total_savings_bytes"] += opp.get("savings_bytes", 0)
                opp_data[opp_id]["scores"].append(opp.get("score", 0))
                opp_data[opp_id]["pages"].append({
                    "url": snapshot.url,
                    "savings_ms": opp.get("savings_ms", 0),
                    "display_value": opp.get("display_value", ""),
                })

        opportunities = []
        for opp_id, data in opp_data.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            opportunities.append({
                "id": opp_id,
                "title": data["title"],
                "description": data["description"],
                "affected_pages": data["count"],
                "total_savings_ms": data["total_savings_ms"],
                "total_savings_bytes": data["total_savings_bytes"],
                "avg_score": round(avg_score, 2),
                "pages": sorted(data["pages"], key=lambda x: x["savings_ms"], reverse=True)[:10],
            })

        return sorted(opportunities, key=lambda x: x["total_savings_ms"], reverse=True)

    async def list_snapshots(
        self,
        site_id: UUID,
        template_type: str | None = None,
        strategy: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[PerformanceSnapshot], int]:
        """List performance snapshots with pagination."""
        query = select(PerformanceSnapshot).where(PerformanceSnapshot.site_id == site_id)
        count_query = select(func.count(PerformanceSnapshot.id)).where(
            PerformanceSnapshot.site_id == site_id
        )

        if template_type:
            query = query.where(PerformanceSnapshot.template_type == template_type)
            count_query = count_query.where(PerformanceSnapshot.template_type == template_type)

        if strategy:
            query = query.where(PerformanceSnapshot.strategy == strategy)
            count_query = count_query.where(PerformanceSnapshot.strategy == strategy)

        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(PerformanceSnapshot.checked_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_snapshot_by_id(
        self,
        snapshot_id: UUID,
        site_id: UUID,
    ) -> PerformanceSnapshot | None:
        """Get a specific snapshot by ID."""
        result = await self.db.execute(
            select(PerformanceSnapshot).where(
                PerformanceSnapshot.id == snapshot_id,
                PerformanceSnapshot.site_id == site_id,
            )
        )
        return result.scalar_one_or_none()
