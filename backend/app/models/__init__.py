"""
SQLAlchemy models for SEOman.
"""
from app.models.base import Base, BaseModel, TenantBaseModel
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User, UserRole, UserStatus
from app.models.site import Site
from app.models.crawl import CrawlJob, CrawlPage, JobStatus
from app.models.audit import AuditRun, SeoIssue, SEOAuditCheck, IssueSeverity, IssueStatus
from app.models.keyword import Keyword, KeywordCluster, KeywordGap, KeywordGapStatus
from app.models.plan import SeoPlan, SeoTask, TaskStatus, TaskCategory
from app.models.content import ContentBrief, ContentDraft, DraftStatus, PageType

__all__ = [
    "Base",
    "BaseModel",
    "TenantBaseModel",
    "Tenant",
    "TenantStatus",
    "User",
    "UserRole",
    "UserStatus",
    "Site",
    "CrawlJob",
    "CrawlPage",
    "JobStatus",
    "AuditRun",
    "SeoIssue",
    "SEOAuditCheck",
    "IssueSeverity",
    "IssueStatus",
    "Keyword",
    "KeywordCluster",
    "KeywordGap",
    "KeywordGapStatus",
    "SeoPlan",
    "SeoTask",
    "TaskStatus",
    "TaskCategory",
    "ContentBrief",
    "ContentDraft",
    "DraftStatus",
    "PageType",
]
