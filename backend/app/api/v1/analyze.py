"""
Analyze API Endpoint

Simple API for triggering the full SEO analysis pipeline.
This is the main entry point for the SEO vision: 
URL in -> Audit + Plan + Briefs -> Markdown files in S3/B2
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field

from app.tasks.pipeline_tasks import run_full_seo_pipeline, get_pipeline_status


router = APIRouter(prefix="/analyze", tags=["Analyze"])


class AnalyzeRequest(BaseModel):
    """Request to analyze a website."""
    
    url: HttpUrl = Field(
        ...,
        description="Website URL to analyze",
        examples=["https://example.com"],
    )
    tenant_id: Optional[str] = Field(
        None,
        description="Optional tenant ID. Creates default tenant if not provided.",
    )
    options: Optional[dict] = Field(
        default_factory=dict,
        description="Analysis options",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "options": {
                    "max_pages": 100,
                    "generate_briefs": True,
                    "plan_duration_weeks": 12,
                    "seed_keywords": ["seo", "marketing"],
                }
            }
        }


class AnalyzeOptions(BaseModel):
    """Options for the analysis pipeline."""
    
    max_pages: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum pages to crawl",
    )
    generate_briefs: bool = Field(
        default=True,
        description="Whether to generate content briefs",
    )
    plan_duration_weeks: int = Field(
        default=12,
        ge=4,
        le=52,
        description="Plan duration in weeks",
    )
    seed_keywords: List[str] = Field(
        default_factory=list,
        description="Optional seed keywords for content planning",
    )


class AnalyzeResponse(BaseModel):
    """Response from analyze request."""
    
    report_id: str = Field(..., description="Unique report ID")
    status: str = Field(..., description="Current status: processing, completed, failed")
    message: str = Field(..., description="Status message")
    url: str = Field(..., description="URL being analyzed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "message": "Analysis started. Check /analyze/status/{report_id} for updates.",
                "url": "https://example.com",
            }
        }


class ReportStatusResponse(BaseModel):
    """Response with report status and files."""
    
    report_id: str
    status: str
    url: Optional[str] = None
    score: Optional[int] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    files: Optional[dict] = None
    summary: Optional[dict] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "url": "https://example.com",
                "score": 72,
                "completed_at": "2024-01-15T10:30:00Z",
                "duration_seconds": 45.2,
                "files": {
                    "audit_report": "https://b2.example.com/reports/audit-report.md",
                    "seo_plan": "https://b2.example.com/reports/seo-plan.md",
                    "page_fixes": "https://b2.example.com/reports/page-fixes.md",
                    "briefs": [
                        {"keyword": "seo tips", "url": "https://b2.example.com/briefs/article-01-seo-tips.md"}
                    ],
                },
                "summary": {
                    "issues_found": 15,
                    "action_items": 12,
                    "content_pieces_planned": 3,
                    "briefs_generated": 3,
                },
            }
        }


@router.post(
    "",
    response_model=AnalyzeResponse,
    summary="Analyze a website",
    description="""
    Start a comprehensive SEO analysis of a website.
    
    This endpoint triggers the full pipeline:
    1. Crawl and audit the website for SEO issues
    2. Generate AI-powered recommendations
    3. Create an SEO improvement plan
    4. Generate content briefs for new articles
    5. Save all reports as Markdown files in S3/B2 storage
    
    The analysis runs asynchronously. Use the returned `report_id` to check
    status and retrieve results via `/analyze/status/{report_id}`.
    """,
)
async def analyze_website(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> AnalyzeResponse:
    """Start SEO analysis for a website."""
    
    url = str(request.url)
    
    # Merge options
    options = request.options or {}
    
    # Trigger the pipeline task
    task = run_full_seo_pipeline.delay(
        url=url,
        tenant_id=request.tenant_id,
        options=options,
    )
    
    return AnalyzeResponse(
        report_id=task.id,
        status="processing",
        message="Analysis started. Check /analyze/status/{report_id} for updates.",
        url=url,
    )


@router.get(
    "/status/{report_id}",
    response_model=ReportStatusResponse,
    summary="Get analysis status",
    description="Check the status of an analysis and retrieve report URLs when complete.",
)
async def get_analysis_status(report_id: str) -> ReportStatusResponse:
    """Get the status of an analysis by report ID."""
    
    from celery.result import AsyncResult
    
    result = AsyncResult(report_id)
    
    if result.state == "PENDING":
        return ReportStatusResponse(
            report_id=report_id,
            status="pending",
        )
    elif result.state == "STARTED" or result.state == "PROGRESS":
        return ReportStatusResponse(
            report_id=report_id,
            status="processing",
        )
    elif result.state == "SUCCESS":
        data = result.result or {}
        return ReportStatusResponse(
            report_id=report_id,
            status=data.get("status", "completed"),
            url=data.get("url"),
            score=data.get("score"),
            completed_at=data.get("completed_at"),
            duration_seconds=data.get("duration_seconds"),
            files=data.get("files"),
            summary=data.get("summary"),
            error=data.get("error"),
        )
    elif result.state == "FAILURE":
        return ReportStatusResponse(
            report_id=report_id,
            status="failed",
            error=str(result.result) if result.result else "Unknown error",
        )
    else:
        return ReportStatusResponse(
            report_id=report_id,
            status=result.state.lower(),
        )


@router.post(
    "/quick",
    response_model=dict,
    summary="Quick analysis (synchronous)",
    description="""
    Run a quick synchronous SEO analysis. 
    
    This is simpler but blocks until complete (timeout: 60s).
    For larger sites, use the async `/analyze` endpoint instead.
    """,
)
async def quick_analyze(
    request: AnalyzeRequest,
) -> dict:
    """Run a quick synchronous analysis."""
    
    from app.integrations.seoanalyzer import SEOAnalyzerClient
    
    url = str(request.url)
    
    try:
        analyzer = SEOAnalyzerClient()
        
        # Check health
        if not await analyzer.health_check():
            raise HTTPException(
                status_code=503,
                detail="SEO analyzer service is not available",
            )
        
        # Run analysis
        result = await analyzer.analyze_site(
            url=url,
            analyze_headings=True,
            analyze_extra_tags=True,
        )
        
        # Parse issues
        issues = analyzer.parse_issues(result)
        score = analyzer.calculate_score(issues)
        
        return {
            "url": url,
            "score": score,
            "issues_count": len(issues),
            "issues": issues,
            "raw_pages": len(result.get("pages", [])),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )
