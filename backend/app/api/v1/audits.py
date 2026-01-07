"""
Audit endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, require_permission
from app.models.crawl import JobStatus
from app.models.audit import IssueSeverity, IssueStatus
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.audit import (
    AuditCreate,
    AuditDetailResponse,
    AuditRunResponse,
    SeoIssueResponse,
    SeoIssueUpdate,
)
from app.services.audit_service import AuditService
from app.services.site_service import SiteService

router = APIRouter(tags=["Audits"])


@router.post(
    "/sites/{site_id}/audits",
    response_model=AuditRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_audit(
    site_id: UUID,
    data: AuditCreate,
    current_user: Annotated[CurrentUser, Depends(require_permission("audit:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Start a new audit for a site."""
    # Verify site access
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    audit_service = AuditService(db)
    audit = await audit_service.create(site_id, data, current_user.id)
    
    await db.commit()
    
    from app.tasks.audit_tasks import run_audit
    run_audit.delay(str(audit.id), str(site_id), str(current_user.tenant_id))
    
    return AuditRunResponse.model_validate(audit)


@router.get("/sites/{site_id}/audits", response_model=PaginatedResponse[AuditRunResponse])
async def list_audits(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: JobStatus | None = None,
):
    """List audits for a site."""
    # Verify site access
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    audit_service = AuditService(db)
    audits, total = await audit_service.list_audits(site_id, page, per_page, status)
    
    return PaginatedResponse.create(
        items=[AuditRunResponse.model_validate(a) for a in audits],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/audits/{audit_id}", response_model=AuditDetailResponse)
async def get_audit(
    audit_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get audit details with issues."""
    audit_service = AuditService(db)
    audit = await audit_service.get_by_id(audit_id)
    
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )
    
    # Verify tenant access
    site_service = SiteService(db)
    site = await site_service.get_by_id(audit.site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    issues = await audit_service.get_issues(audit_id)
    
    # Calculate issue stats
    issues_by_severity = {}
    issues_by_category = {}
    for issue in issues:
        sev = issue.severity.value
        cat = issue.category
        issues_by_severity[sev] = issues_by_severity.get(sev, 0) + 1
        issues_by_category[cat] = issues_by_category.get(cat, 0) + 1
    
    return AuditDetailResponse(
        audit_run=AuditRunResponse.model_validate(audit),
        issues=[SeoIssueResponse.model_validate(i) for i in issues],
        issues_by_severity=issues_by_severity,
        issues_by_category=issues_by_category,
    )


@router.patch("/issues/{issue_id}", response_model=SeoIssueResponse)
async def update_issue(
    issue_id: UUID,
    data: SeoIssueUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an issue status."""
    audit_service = AuditService(db)
    
    if data.status:
        issue = await audit_service.update_issue_status(issue_id, data.status)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided",
        )
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    
    return SeoIssueResponse.model_validate(issue)
