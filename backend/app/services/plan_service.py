"""
SEO Plan service for roadmap management.
"""
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.plan import SeoPlan, SeoTask, TaskStatus
from app.schemas.plan import PlanGenerateRequest, SeoTaskUpdate


class PlanService:
    """Service for SEO plan operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, plan_id: UUID, site_id: UUID | None = None) -> SeoPlan | None:
        """Get plan by ID."""
        query = select(SeoPlan).where(SeoPlan.id == plan_id)
        if site_id:
            query = query.where(SeoPlan.site_id == site_id)
        query = query.options(selectinload(SeoPlan.tasks))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_plans(
        self,
        site_id: UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[SeoPlan], int]:
        """List plans for a site."""
        query = select(SeoPlan).where(SeoPlan.site_id == site_id)
        count_query = select(func.count(SeoPlan.id)).where(SeoPlan.site_id == site_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(SeoPlan.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        
        return list(result.scalars().all()), total
    
    async def create(
        self,
        site_id: UUID,
        data: PlanGenerateRequest,
        user_id: UUID | None = None,
        audit_id: UUID | None = None,
    ) -> SeoPlan:
        """Create a new SEO plan."""
        plan = SeoPlan(
            site_id=site_id,
            name=data.name or f"SEO Plan - {data.timeframe_months} months",
            timeframe_months=data.timeframe_months,
            goals=data.goals,
            generated_from_audit_id=audit_id,
            created_by_user_id=user_id,
        )
        self.db.add(plan)
        await self.db.flush()
        await self.db.refresh(plan)
        return plan
    
    async def add_tasks(
        self,
        plan_id: UUID,
        site_id: UUID,
        tasks_data: list[dict],
    ) -> list[SeoTask]:
        """Add tasks to a plan."""
        tasks = []
        for task_data in tasks_data:
            task = SeoTask(
                seo_plan_id=plan_id,
                site_id=site_id,
                **task_data,
            )
            self.db.add(task)
            tasks.append(task)
        
        await self.db.flush()
        for task in tasks:
            await self.db.refresh(task)
        
        return tasks
    
    async def get_task_by_id(self, task_id: UUID) -> SeoTask | None:
        """Get task by ID."""
        result = await self.db.execute(
            select(SeoTask).where(SeoTask.id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def update_task(self, task_id: UUID, data: SeoTaskUpdate) -> SeoTask | None:
        """Update a task."""
        task = await self.get_task_by_id(task_id)
        if not task:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        await self.db.flush()
        await self.db.refresh(task)
        return task
    
    async def get_plan_stats(self, plan_id: UUID) -> dict:
        """Get statistics for a plan."""
        # Tasks by status
        status_result = await self.db.execute(
            select(SeoTask.status, func.count(SeoTask.id))
            .where(SeoTask.seo_plan_id == plan_id)
            .group_by(SeoTask.status)
        )
        tasks_by_status = {str(row[0].value): row[1] for row in status_result.all()}
        
        # Total tasks
        total_result = await self.db.execute(
            select(func.count(SeoTask.id)).where(SeoTask.seo_plan_id == plan_id)
        )
        total = total_result.scalar()
        
        completed = tasks_by_status.get("done", 0)
        
        return {
            "tasks_count": total,
            "completed_tasks_count": completed,
            "tasks_by_status": tasks_by_status,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
        }
