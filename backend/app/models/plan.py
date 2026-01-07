"""
SEO Plan models for task management.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel
from app.models.audit import IssueSeverity


class TaskStatus(str, PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskCategory(str, PyEnum):
    TECHNICAL = "technical"
    CONTENT = "content"
    ON_PAGE = "on_page"
    AUTHORITY = "authority"
    OTHER = "other"


class SeoPlan(Base, BaseModel):
    """SEO Plan/Roadmap."""
    
    __tablename__ = "seo_plans"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    timeframe_months = Column(Integer, default=6)
    goals = Column(JSONB, default=list)
    timeline_summary = Column(JSONB, default=dict)
    generated_from_audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id"),
        nullable=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Relationships
    site = relationship("Site", back_populates="seo_plans")
    generated_from_audit = relationship("AuditRun", back_populates="seo_plans")
    tasks = relationship("SeoTask", back_populates="seo_plan", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<SeoPlan {self.name}>"


class SeoTask(Base, BaseModel):
    """Individual SEO task within a plan."""
    
    __tablename__ = "seo_tasks"
    
    seo_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("seo_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        Enum(TaskCategory),
        nullable=False,
    )
    impact = Column(
        Enum(IssueSeverity),
        nullable=False,
    )
    effort = Column(
        Enum(IssueSeverity),
        nullable=False,
    )
    assignee_type = Column(String(50), nullable=True)
    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.TODO,
        nullable=False,
    )
    due_month = Column(Integer, nullable=True)
    related_issue_ids = Column(JSONB, default=list)
    related_cluster_ids = Column(JSONB, default=list)
    
    # Relationships
    seo_plan = relationship("SeoPlan", back_populates="tasks")
    
    def __repr__(self) -> str:
        return f"<SeoTask {self.title[:30]}... ({self.status.value})>"
