"""
Pydantic schemas for SEOman API.
"""
from app.schemas.common import (
    BaseSchema,
    IDSchema,
    TimestampSchema,
    PaginationParams,
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
)
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
)
from app.schemas.site import (
    SiteCreate,
    SiteUpdate,
    SiteResponse,
)
from app.schemas.crawl import (
    CrawlConfig,
    CrawlJobCreate,
    CrawlJobResponse,
    CrawlPageResponse,
)
from app.schemas.audit import (
    AuditCreate,
    AuditRunResponse,
    SeoIssueResponse,
    AuditDetailResponse,
)
from app.schemas.keyword import (
    KeywordDiscoverRequest,
    KeywordExpandRequest,
    KeywordResponse,
    KeywordClusterResponse,
)
from app.schemas.plan import (
    PlanGenerateRequest,
    SeoPlanResponse,
    SeoTaskResponse,
    SeoTaskUpdate,
)
from app.schemas.content import (
    ContentBriefCreate,
    ContentBriefResponse,
    ContentDraftCreate,
    ContentDraftResponse,
    ContentDraftUpdate,
)

__all__ = [
    # Common
    "BaseSchema",
    "IDSchema",
    "TimestampSchema",
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "AuthResponse",
    # Tenant
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    # Site
    "SiteCreate",
    "SiteUpdate",
    "SiteResponse",
    # Crawl
    "CrawlConfig",
    "CrawlJobCreate",
    "CrawlJobResponse",
    "CrawlPageResponse",
    # Audit
    "AuditCreate",
    "AuditRunResponse",
    "SeoIssueResponse",
    "AuditDetailResponse",
    # Keyword
    "KeywordDiscoverRequest",
    "KeywordExpandRequest",
    "KeywordResponse",
    "KeywordClusterResponse",
    # Plan
    "PlanGenerateRequest",
    "SeoPlanResponse",
    "SeoTaskResponse",
    "SeoTaskUpdate",
    # Content
    "ContentBriefCreate",
    "ContentBriefResponse",
    "ContentDraftCreate",
    "ContentDraftResponse",
    "ContentDraftUpdate",
]
