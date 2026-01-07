"""
SEOman v2.0 Audit API Endpoints

Exposes the 100-check SEO audit system with detailed results.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.tasks.pipeline_tasks import run_full_seo_pipeline


router = APIRouter(prefix="/v2/audit", tags=["Audit v2.0"])


class AuditV2Request(BaseModel):
    """Request for v2.0 audit."""
    
    url: str = Field(..., description="Website URL to audit")
    max_pages: int = Field(default=50, ge=1, le=500, description="Maximum pages to crawl")
    generate_plan: bool = Field(default=True, description="Generate SEO improvement plan")
    generate_briefs: bool = Field(default=False, description="Generate content briefs")
    seed_keywords: list[str] = Field(default_factory=list, description="Optional seed keywords")


class AuditV2Response(BaseModel):
    """Response from v2.0 audit request."""
    
    task_id: str = Field(..., description="Async task ID for tracking")
    status: str = Field(default="processing", description="Current status")
    message: str = Field(..., description="Status message")


class AuditCheckResult(BaseModel):
    """Individual audit check result."""
    
    check_id: int
    category: str
    check_name: str
    passed: bool
    severity: str
    affected_count: int = 0
    affected_urls: list[str] = []
    details: dict[str, Any] = {}
    recommendation: str = ""


class AuditCategoryScore(BaseModel):
    """Score for an audit category."""
    
    category: str
    total_checks: int
    passed: int
    failed: int
    score: int


class AuditV2DetailResponse(BaseModel):
    """Detailed v2.0 audit response."""
    
    report_id: str
    url: str
    status: str
    score: int
    pages_crawled: int
    checks_run: int
    issues_count: int
    duration_seconds: float | None = None
    category_scores: list[AuditCategoryScore] = []
    checks: list[AuditCheckResult] = []
    files: dict[str, Any] = {}
    summary: dict[str, Any] = {}


@router.post(
    "/run",
    response_model=AuditV2Response,
    summary="Run 100-check SEO audit",
    description="""
    Run a comprehensive 100-check SEO audit on a website.
    
    The audit covers 10 categories:
    - Crawlability & Indexability (checks 1-10)
    - On-Page SEO (checks 11-20)
    - Technical Performance (checks 21-30)
    - URL Structure (checks 31-40)
    - Internal Linking (checks 41-50)
    - Content Quality (checks 51-60)
    - Structured Data (checks 61-70)
    - Security & Accessibility (checks 71-80)
    - Mobile Optimization (checks 81-90)
    - Server & Infrastructure (checks 91-100)
    
    Returns a task_id to track progress via /v2/audit/status/{task_id}
    """,
)
async def run_audit_v2(request: AuditV2Request) -> AuditV2Response:
    """Start a v2.0 100-check audit."""
    
    task = run_full_seo_pipeline.delay(
        url=request.url,
        tenant_id=None,
        options={
            "max_pages": request.max_pages,
            "generate_briefs": request.generate_briefs,
            "seed_keywords": request.seed_keywords,
        },
    )
    
    return AuditV2Response(
        task_id=task.id,
        status="processing",
        message=f"100-check audit started for {request.url}. Use /v2/audit/status/{task.id} to check progress.",
    )


@router.get(
    "/status/{task_id}",
    response_model=AuditV2DetailResponse,
    summary="Get audit status and results",
    description="Get detailed results of a v2.0 audit including all 100 checks.",
)
async def get_audit_status(task_id: str) -> AuditV2DetailResponse:
    """Get status and results of a v2.0 audit."""
    
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id)
    
    if result.state == "PENDING":
        return AuditV2DetailResponse(
            report_id=task_id,
            url="",
            status="pending",
            score=0,
            pages_crawled=0,
            checks_run=0,
            issues_count=0,
        )
    elif result.state in ["STARTED", "PROGRESS"]:
        return AuditV2DetailResponse(
            report_id=task_id,
            url="",
            status="processing",
            score=0,
            pages_crawled=0,
            checks_run=0,
            issues_count=0,
        )
    elif result.state == "SUCCESS":
        data = result.result or {}
        
        return AuditV2DetailResponse(
            report_id=data.get("report_id", task_id),
            url=data.get("url", ""),
            status=data.get("status", "completed"),
            score=data.get("score", 0),
            pages_crawled=data.get("pages_crawled", 0),
            checks_run=data.get("checks_run", 0),
            issues_count=data.get("issues_count", 0),
            duration_seconds=data.get("duration_seconds"),
            files=data.get("files", {}),
            summary=data.get("summary", {}),
        )
    elif result.state == "FAILURE":
        return AuditV2DetailResponse(
            report_id=task_id,
            url="",
            status="failed",
            score=0,
            pages_crawled=0,
            checks_run=0,
            issues_count=0,
            summary={"error": str(result.result) if result.result else "Unknown error"},
        )
    else:
        return AuditV2DetailResponse(
            report_id=task_id,
            url="",
            status=result.state.lower(),
            score=0,
            pages_crawled=0,
            checks_run=0,
            issues_count=0,
        )


@router.get(
    "/checks",
    response_model=dict,
    summary="List all 100 audit checks",
    description="Get the complete list of all 100 SEO checks with their categories and descriptions.",
)
async def list_audit_checks() -> dict:
    """Return the list of all 100 audit checks."""
    
    checks = {
        "total_checks": 100,
        "categories": [
            {
                "id": 1,
                "name": "Crawlability & Indexability",
                "checks": [
                    {"id": 1, "name": "Robots.txt Presence", "severity": "high"},
                    {"id": 2, "name": "Robots.txt Blocking Critical Resources", "severity": "critical"},
                    {"id": 3, "name": "Sitemap.xml Presence", "severity": "high"},
                    {"id": 4, "name": "Sitemap Validity", "severity": "medium"},
                    {"id": 5, "name": "Noindex on Important Pages", "severity": "critical"},
                    {"id": 6, "name": "Canonical Tag Presence", "severity": "high"},
                    {"id": 7, "name": "Canonical Self-Reference", "severity": "medium"},
                    {"id": 8, "name": "Orphan Pages", "severity": "high"},
                    {"id": 9, "name": "Crawl Depth", "severity": "medium"},
                    {"id": 10, "name": "Redirect Chains", "severity": "medium"},
                ],
            },
            {
                "id": 2,
                "name": "On-Page SEO",
                "checks": [
                    {"id": 11, "name": "Missing Title Tag", "severity": "critical"},
                    {"id": 12, "name": "Title Too Long (>60 chars)", "severity": "medium"},
                    {"id": 13, "name": "Title Too Short (<30 chars)", "severity": "medium"},
                    {"id": 14, "name": "Duplicate Title Tags", "severity": "high"},
                    {"id": 15, "name": "Missing Meta Description", "severity": "high"},
                    {"id": 16, "name": "Meta Description Too Long (>160 chars)", "severity": "low"},
                    {"id": 17, "name": "Duplicate Meta Descriptions", "severity": "medium"},
                    {"id": 18, "name": "Missing H1", "severity": "high"},
                    {"id": 19, "name": "Multiple H1 Tags", "severity": "medium"},
                    {"id": 20, "name": "Images Missing Alt Text", "severity": "medium"},
                ],
            },
            {
                "id": 3,
                "name": "Technical Performance",
                "checks": [
                    {"id": 21, "name": "Slow Page Load (>3s)", "severity": "high"},
                    {"id": 22, "name": "Large Page Size (>3MB)", "severity": "medium"},
                    {"id": 23, "name": "Too Many HTTP Requests", "severity": "medium"},
                    {"id": 24, "name": "Missing GZIP Compression", "severity": "medium"},
                    {"id": 25, "name": "Unoptimized Images", "severity": "medium"},
                    {"id": 26, "name": "Render-Blocking Resources", "severity": "medium"},
                    {"id": 27, "name": "No Browser Caching", "severity": "low"},
                    {"id": 28, "name": "JavaScript Errors", "severity": "high"},
                    {"id": 29, "name": "Core Web Vitals - LCP", "severity": "high"},
                    {"id": 30, "name": "Core Web Vitals - CLS", "severity": "high"},
                ],
            },
            {
                "id": 4,
                "name": "URL Structure",
                "checks": [
                    {"id": 31, "name": "URL Too Long (>75 chars)", "severity": "low"},
                    {"id": 32, "name": "Uppercase Characters in URL", "severity": "low"},
                    {"id": 33, "name": "Underscores in URL", "severity": "low"},
                    {"id": 34, "name": "Special Characters in URL", "severity": "medium"},
                    {"id": 35, "name": "URL Parameters Issues", "severity": "medium"},
                    {"id": 36, "name": "Deep URL Path (>4 levels)", "severity": "medium"},
                    {"id": 37, "name": "Non-Descriptive URLs", "severity": "low"},
                    {"id": 38, "name": "Missing Trailing Slash Consistency", "severity": "low"},
                    {"id": 39, "name": "Duplicate Content URLs", "severity": "high"},
                    {"id": 40, "name": "URL Not Lowercase", "severity": "low"},
                ],
            },
            {
                "id": 5,
                "name": "Internal Linking",
                "checks": [
                    {"id": 41, "name": "Orphan Pages", "severity": "high"},
                    {"id": 42, "name": "Pages with Few Internal Links (<3)", "severity": "medium"},
                    {"id": 43, "name": "Broken Internal Links", "severity": "critical"},
                    {"id": 44, "name": "Too Many Internal Links (>100)", "severity": "low"},
                    {"id": 45, "name": "Generic Anchor Text", "severity": "medium"},
                    {"id": 46, "name": "Missing Breadcrumbs", "severity": "low"},
                    {"id": 47, "name": "Nofollow Internal Links", "severity": "medium"},
                    {"id": 48, "name": "Pagination Issues", "severity": "medium"},
                    {"id": 49, "name": "Link Depth Issues", "severity": "medium"},
                    {"id": 50, "name": "Internal Link to Redirects", "severity": "medium"},
                ],
            },
            {
                "id": 6,
                "name": "Content Quality",
                "checks": [
                    {"id": 51, "name": "Thin Content (<300 words)", "severity": "high"},
                    {"id": 52, "name": "Duplicate Content (Internal)", "severity": "high"},
                    {"id": 53, "name": "Low Content-to-HTML Ratio", "severity": "medium"},
                    {"id": 54, "name": "Missing Structured Content", "severity": "low"},
                    {"id": 55, "name": "Keyword Stuffing Risk", "severity": "medium"},
                    {"id": 56, "name": "Readability Issues", "severity": "low"},
                    {"id": 57, "name": "Missing Open Graph Tags", "severity": "low"},
                    {"id": 58, "name": "Missing Twitter Cards", "severity": "low"},
                    {"id": 59, "name": "Broken External Links", "severity": "medium"},
                    {"id": 60, "name": "Low Word Count Pages", "severity": "medium"},
                ],
            },
            {
                "id": 7,
                "name": "Structured Data",
                "checks": [
                    {"id": 61, "name": "Missing Structured Data", "severity": "medium"},
                    {"id": 62, "name": "Invalid JSON-LD Syntax", "severity": "high"},
                    {"id": 63, "name": "Missing Organization Schema", "severity": "low"},
                    {"id": 64, "name": "Missing Breadcrumb Schema", "severity": "low"},
                    {"id": 65, "name": "Missing Article Schema (Blog)", "severity": "low"},
                    {"id": 66, "name": "Missing Local Business Schema", "severity": "medium"},
                    {"id": 67, "name": "Missing Product Schema (E-commerce)", "severity": "medium"},
                    {"id": 68, "name": "Missing FAQ Schema", "severity": "low"},
                    {"id": 69, "name": "Deprecated Schema Types", "severity": "low"},
                    {"id": 70, "name": "Schema Validation Errors", "severity": "medium"},
                ],
            },
            {
                "id": 8,
                "name": "Security & Accessibility",
                "checks": [
                    {"id": 71, "name": "Not Using HTTPS", "severity": "critical"},
                    {"id": 72, "name": "Mixed Content", "severity": "high"},
                    {"id": 73, "name": "Missing HSTS Header", "severity": "medium"},
                    {"id": 74, "name": "Missing Security Headers", "severity": "medium"},
                    {"id": 75, "name": "Insecure External Links", "severity": "low"},
                    {"id": 76, "name": "Missing Lang Attribute", "severity": "medium"},
                    {"id": 77, "name": "Missing Hreflang Tags", "severity": "medium"},
                    {"id": 78, "name": "Invalid Hreflang Implementation", "severity": "high"},
                    {"id": 79, "name": "Missing Form Labels", "severity": "low"},
                    {"id": 80, "name": "Low Contrast Text", "severity": "low"},
                ],
            },
            {
                "id": 9,
                "name": "Mobile Optimization",
                "checks": [
                    {"id": 81, "name": "Missing Viewport Meta Tag", "severity": "critical"},
                    {"id": 82, "name": "Content Wider Than Screen", "severity": "high"},
                    {"id": 83, "name": "Small Touch Targets", "severity": "medium"},
                    {"id": 84, "name": "Small Font Size (<12px)", "severity": "medium"},
                    {"id": 85, "name": "No Mobile-Friendly Design", "severity": "high"},
                    {"id": 86, "name": "Flash Content", "severity": "critical"},
                    {"id": 87, "name": "Intrusive Interstitials", "severity": "high"},
                    {"id": 88, "name": "Missing Touch Icons", "severity": "low"},
                    {"id": 89, "name": "Horizontal Scrolling Required", "severity": "high"},
                    {"id": 90, "name": "Mobile Redirect Issues", "severity": "high"},
                ],
            },
            {
                "id": 10,
                "name": "Server & Infrastructure",
                "checks": [
                    {"id": 91, "name": "4xx Error Pages", "severity": "high"},
                    {"id": 92, "name": "5xx Server Errors", "severity": "critical"},
                    {"id": 93, "name": "Slow Server Response (>500ms)", "severity": "high"},
                    {"id": 94, "name": "Missing Cache Headers", "severity": "medium"},
                    {"id": 95, "name": "No CDN Detected", "severity": "low"},
                    {"id": 96, "name": "DNS Resolution Issues", "severity": "high"},
                    {"id": 97, "name": "Multiple Redirects", "severity": "medium"},
                    {"id": 98, "name": "WWW/Non-WWW Redirect Missing", "severity": "medium"},
                    {"id": 99, "name": "Incorrect Content-Type Headers", "severity": "medium"},
                    {"id": 100, "name": "Server Downtime History", "severity": "high"},
                ],
            },
        ],
    }
    
    return checks


@router.get(
    "/categories",
    response_model=list[dict],
    summary="List audit categories",
    description="Get a summary of the 10 audit categories and their check counts.",
)
async def list_audit_categories() -> list[dict]:
    """Return the list of audit categories."""
    
    return [
        {"id": 1, "name": "Crawlability & Indexability", "checks_range": "1-10", "check_count": 10},
        {"id": 2, "name": "On-Page SEO", "checks_range": "11-20", "check_count": 10},
        {"id": 3, "name": "Technical Performance", "checks_range": "21-30", "check_count": 10},
        {"id": 4, "name": "URL Structure", "checks_range": "31-40", "check_count": 10},
        {"id": 5, "name": "Internal Linking", "checks_range": "41-50", "check_count": 10},
        {"id": 6, "name": "Content Quality", "checks_range": "51-60", "check_count": 10},
        {"id": 7, "name": "Structured Data", "checks_range": "61-70", "check_count": 10},
        {"id": 8, "name": "Security & Accessibility", "checks_range": "71-80", "check_count": 10},
        {"id": 9, "name": "Mobile Optimization", "checks_range": "81-90", "check_count": 10},
        {"id": 10, "name": "Server & Infrastructure", "checks_range": "91-100", "check_count": 10},
    ]
