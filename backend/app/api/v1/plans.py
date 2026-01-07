"""
SEO Plan endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.plan import (
    PlanGenerateRequest,
    SeoPlanDetail,
    SeoPlanResponse,
    SeoTaskResponse,
    SeoTaskUpdate,
)
from app.services.plan_service import PlanService
from app.services.site_service import SiteService

router = APIRouter(tags=["SEO Plans"])


@router.post(
    "/sites/{site_id}/plans/generate",
    response_model=SeoPlanResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_plan(
    site_id: UUID,
    data: PlanGenerateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("plan:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate a new SEO plan for a site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    plan_service = PlanService(db)
    plan = await plan_service.create(site_id, data, current_user.id)
    
    # TODO: Trigger background task for plan generation
    # from app.tasks.plan_tasks import generate_plan_task
    # generate_plan_task.delay(str(plan.id))
    
    return SeoPlanResponse.model_validate(plan)


@router.get("/sites/{site_id}/seo-plans", response_model=PaginatedResponse[SeoPlanResponse])
async def list_plans(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """List SEO plans for a site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    plan_service = PlanService(db)
    plans, total = await plan_service.list_plans(site_id, page, per_page)
    
    # Add stats to each plan
    items = []
    for plan in plans:
        stats = await plan_service.get_plan_stats(plan.id)
        response = SeoPlanResponse.model_validate(plan)
        response.tasks_count = stats["tasks_count"]
        response.completed_tasks_count = stats["completed_tasks_count"]
        items.append(response)
    
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/plans/{plan_id}", response_model=SeoPlanDetail)
async def get_plan(
    plan_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get SEO plan with tasks."""
    plan_service = PlanService(db)
    plan = await plan_service.get_by_id(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    
    # Verify access
    site_service = SiteService(db)
    site = await site_service.get_by_id(plan.site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    stats = await plan_service.get_plan_stats(plan_id)
    
    response = SeoPlanDetail.model_validate(plan)
    response.tasks = [SeoTaskResponse.model_validate(t) for t in plan.tasks]
    response.tasks_count = stats["tasks_count"]
    response.completed_tasks_count = stats["completed_tasks_count"]
    response.tasks_by_status = stats["tasks_by_status"]
    
    # Calculate tasks by category
    tasks_by_category = {}
    for task in plan.tasks:
        cat = task.category.value
        tasks_by_category[cat] = tasks_by_category.get(cat, 0) + 1
    response.tasks_by_category = tasks_by_category
    
    return response


@router.patch("/tasks/{task_id}", response_model=SeoTaskResponse)
async def update_task(
    task_id: UUID,
    data: SeoTaskUpdate,
    current_user: Annotated[CurrentUser, Depends(require_permission("plan:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a task."""
    plan_service = PlanService(db)
    task = await plan_service.update_task(task_id, data)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    return SeoTaskResponse.model_validate(task)
