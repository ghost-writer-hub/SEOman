"""
Performance schemas for PageSpeed Insights API.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class PerformanceSnapshotResponse(IDSchema, TimestampSchema):
    """Performance snapshot response."""

    tenant_id: UUID
    site_id: UUID
    audit_run_id: UUID | None
    url: str
    template_type: str | None
    strategy: str

    # Score
    performance_score: int | None

    # Core Web Vitals
    lcp_ms: int | None
    fid_ms: int | None
    cls: float | None
    fcp_ms: int | None
    ttfb_ms: int | None
    tbt_ms: int | None
    speed_index_ms: int | None
    tti_ms: int | None
    inp_ms: int | None

    # Status
    cwv_status: str | None

    # Timestamps
    checked_at: datetime


class PerformanceSnapshotDetail(PerformanceSnapshotResponse):
    """Detailed performance snapshot with opportunities and diagnostics."""

    opportunities: list[dict[str, Any]]
    diagnostics: dict[str, Any]
    field_data: dict[str, Any]


class PerformanceSummary(BaseSchema):
    """Aggregated performance summary for a site."""

    site_id: UUID
    total_snapshots: int
    pages_analyzed: int

    # Average scores
    avg_mobile_score: float | None
    avg_desktop_score: float | None

    # CWV pass rates (percentage of pages with "good" status)
    cwv_pass_rate: float

    # Average metrics
    avg_lcp_ms: int | None
    avg_cls: float | None
    avg_fcp_ms: int | None
    avg_ttfb_ms: int | None

    # Worst performers
    worst_lcp_pages: list[dict[str, Any]]
    worst_cls_pages: list[dict[str, Any]]
    slowest_pages: list[dict[str, Any]]

    # Common opportunities across pages
    common_opportunities: list[dict[str, Any]]

    # Last analysis
    last_analyzed: datetime | None


class PerformanceHistoryPoint(BaseSchema):
    """Single point in performance history."""

    checked_at: datetime
    performance_score: int | None
    lcp_ms: int | None
    cls: float | None
    fcp_ms: int | None
    cwv_status: str | None


class PerformanceHistory(BaseSchema):
    """Performance history for a URL."""

    url: str
    strategy: str
    history: list[PerformanceHistoryPoint]


class AnalyzeRequest(BaseSchema):
    """Request to trigger performance analysis."""

    urls: list[str] | None = Field(
        default=None,
        description="Specific URLs to analyze. If not provided, auto-selects top pages per template.",
    )
    strategy: str = Field(
        default="both",
        description="Strategy: 'mobile', 'desktop', or 'both'",
    )
    max_pages: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum pages to analyze if URLs not specified",
    )


class AnalyzeResponse(BaseSchema):
    """Response from performance analysis trigger."""

    success: bool
    message: str
    pages_queued: int
    urls: list[str]


class OpportunitySummary(BaseSchema):
    """Aggregated optimization opportunity."""

    id: str
    title: str
    description: str
    affected_pages: int
    total_savings_ms: int
    total_savings_bytes: int
    avg_score: float
    pages: list[dict[str, Any]]


class CWVMetrics(BaseSchema):
    """Core Web Vitals metrics with status."""

    lcp_ms: int | None
    lcp_status: str
    cls: float | None
    cls_status: str
    fcp_ms: int | None
    fcp_status: str
    ttfb_ms: int | None
    ttfb_status: str
    tbt_ms: int | None
    overall_status: str


class PagePerformance(BaseSchema):
    """Performance data for a single page."""

    url: str
    template_type: str | None
    mobile_score: int | None
    desktop_score: int | None
    mobile_cwv: CWVMetrics | None
    desktop_cwv: CWVMetrics | None
    last_checked: datetime | None
