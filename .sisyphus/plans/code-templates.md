# SEOman Code Templates

This document contains ready-to-use code templates for the implementation agent.

---

## Backend Templates

### 1. database.py

```python
"""
Database connection and session management for SEOman.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config import settings

# Convert sync URL to async
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions (for background tasks)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

### 2. models/base.py

```python
"""
Base model mixins for SEOman.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """Mixin for multi-tenant models."""
    
    @declared_attr
    def tenant_id(cls) -> Column:
        return Column(
            UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class BaseModel(UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps."""
    
    __abstract__ = True
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TenantBaseModel(BaseModel, TenantMixin):
    """Base model for tenant-scoped entities."""
    
    __abstract__ = True
```

---

### 3. models/tenant.py

```python
"""
Tenant model for multi-tenancy.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BaseModel


class TenantStatus(str, PyEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Tenant(Base, BaseModel):
    """Tenant model representing an organization."""
    
    __tablename__ = "tenants"
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(
        Enum(TenantStatus),
        default=TenantStatus.ACTIVE,
        nullable=False,
    )
    plan = Column(String(50), default="free")
    settings = Column(JSONB, default=dict)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    sites = relationship("Site", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tenant {self.name} ({self.slug})>"
```

---

### 4. models/user.py

```python
"""
User model with role-based access control.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BaseModel


class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    SEO_MANAGER = "seo_manager"
    READ_ONLY = "read_only"


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class User(Base, BaseModel):
    """User model with authentication and role information."""
    
    __tablename__ = "users"
    
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for super_admin
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole),
        default=UserRole.READ_ONLY,
        nullable=False,
    )
    status = Column(
        Enum(UserStatus),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
    
    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def is_tenant_admin(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN)
    
    def can_manage_tenant(self, tenant_id: str) -> bool:
        """Check if user can manage the given tenant."""
        if self.is_super_admin:
            return True
        return str(self.tenant_id) == str(tenant_id)
```

---

### 5. models/site.py

```python
"""
Site model for monitored websites.
"""
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TenantBaseModel


class Site(Base, TenantBaseModel):
    """Site model representing a monitored website."""
    
    __tablename__ = "sites"
    
    name = Column(String(255), nullable=False)
    primary_domain = Column(String(255), nullable=False, index=True)
    additional_domains = Column(JSONB, default=list)
    default_language = Column(String(10), default="en")
    target_countries = Column(JSONB, default=lambda: ["US"])
    cms_type = Column(String(100), nullable=True)
    brand_tone = Column(JSONB, default=dict)
    enabled_features = Column(JSONB, default=lambda: ["audit", "keywords", "content"])
    
    # Relationships
    tenant = relationship("Tenant", back_populates="sites")
    crawl_jobs = relationship("CrawlJob", back_populates="site", cascade="all, delete-orphan")
    audit_runs = relationship("AuditRun", back_populates="site", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="site", cascade="all, delete-orphan")
    keyword_clusters = relationship("KeywordCluster", back_populates="site", cascade="all, delete-orphan")
    seo_plans = relationship("SeoPlan", back_populates="site", cascade="all, delete-orphan")
    content_briefs = relationship("ContentBrief", back_populates="site", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Site {self.name} ({self.primary_domain})>"
```

---

### 6. models/crawl.py

```python
"""
Crawl models for website crawling data.
"""
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BaseModel, TenantBaseModel


class JobStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CrawlJob(Base, BaseModel):
    """Crawl job tracking."""
    
    __tablename__ = "crawl_jobs"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
    )
    config = Column(JSONB, default=dict)
    pages_crawled = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="crawl_jobs")
    pages = relationship("CrawlPage", back_populates="crawl_job", cascade="all, delete-orphan")
    audit_runs = relationship("AuditRun", back_populates="crawl_job")
    
    def __repr__(self) -> str:
        return f"<CrawlJob {self.id} ({self.status.value})>"


class CrawlPage(Base, BaseModel):
    """Crawled page data."""
    
    __tablename__ = "crawl_pages"
    
    crawl_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(Text, nullable=False)
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    canonical_url = Column(Text, nullable=True)
    meta_robots = Column(String(100), nullable=True)
    title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    h1 = Column(Text, nullable=True)
    h2 = Column(JSONB, default=list)
    h3 = Column(JSONB, default=list)
    word_count = Column(Integer, nullable=True)
    internal_links = Column(JSONB, default=list)
    external_links = Column(JSONB, default=list)
    noindex = Column(Boolean, default=False)
    nofollow = Column(Boolean, default=False)
    
    # Relationships
    crawl_job = relationship("CrawlJob", back_populates="pages")
    
    def __repr__(self) -> str:
        return f"<CrawlPage {self.url[:50]}... ({self.status_code})>"
```

---

### 7. models/audit.py

```python
"""
Audit models for SEO analysis results.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BaseModel
from app.models.crawl import JobStatus


class IssueSeverity(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, PyEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class AuditRun(Base, BaseModel):
    """Audit run tracking and results."""
    
    __tablename__ = "audit_runs"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crawl_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id"),
        nullable=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    audit_type = Column(String(50), default="quick")
    status = Column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
    )
    score = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    findings_overview = Column(JSONB, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="audit_runs")
    crawl_job = relationship("CrawlJob", back_populates="audit_runs")
    issues = relationship("SeoIssue", back_populates="audit_run", cascade="all, delete-orphan")
    seo_plans = relationship("SeoPlan", back_populates="generated_from_audit")
    
    def __repr__(self) -> str:
        return f"<AuditRun {self.id} ({self.status.value})>"


class SeoIssue(Base, BaseModel):
    """Individual SEO issue found during audit."""
    
    __tablename__ = "seo_issues"
    
    audit_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    severity = Column(
        Enum(IssueSeverity),
        nullable=False,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    affected_urls = Column(JSONB, default=list)
    status = Column(
        Enum(IssueStatus),
        default=IssueStatus.OPEN,
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    audit_run = relationship("AuditRun", back_populates="issues")
    
    def __repr__(self) -> str:
        return f"<SeoIssue {self.title[:30]}... ({self.severity.value})>"
```

---

### 8. core/security.py

```python
"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# Permission definitions
PERMISSIONS = {
    "super_admin": [
        "tenant:create", "tenant:read", "tenant:update", "tenant:delete",
        "user:create", "user:read", "user:update", "user:delete",
        "site:create", "site:read", "site:update", "site:delete",
        "audit:create", "audit:read",
        "keyword:create", "keyword:read",
        "plan:create", "plan:read", "plan:update",
        "content:create", "content:read", "content:update", "content:delete",
        "settings:read", "settings:update",
    ],
    "tenant_admin": [
        "user:create", "user:read", "user:update",
        "site:create", "site:read", "site:update", "site:delete",
        "audit:create", "audit:read",
        "keyword:create", "keyword:read",
        "plan:create", "plan:read", "plan:update",
        "content:create", "content:read", "content:update", "content:delete",
    ],
    "seo_manager": [
        "site:read",
        "audit:create", "audit:read",
        "keyword:create", "keyword:read",
        "plan:create", "plan:read", "plan:update",
        "content:create", "content:read", "content:update",
    ],
    "read_only": [
        "site:read",
        "audit:read",
        "keyword:read",
        "plan:read",
        "content:read",
    ],
}


def check_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_permissions = PERMISSIONS.get(role, [])
    return permission in role_permissions
```

---

### 9. core/deps.py

```python
"""
FastAPI dependencies for authentication and database.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import check_permission, decode_token
from app.database import get_db
from app.models.user import User, UserRole

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user is active."""
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_permission(permission: str):
    """Dependency factory for permission checking."""
    
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not check_permission(current_user.role.value, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user
    
    return permission_checker


def require_roles(*roles: UserRole):
    """Dependency factory for role checking."""
    
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {', '.join(r.value for r in roles)}",
            )
        return current_user
    
    return role_checker


# Common dependencies
CurrentUser = Annotated[User, Depends(get_current_active_user)]
SuperAdmin = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]
TenantAdmin = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN))]
```

---

### 10. main.py

```python
"""
FastAPI application entry point for SEOman.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get(f"{settings.API_V1_STR}/health")
async def api_health_check():
    """API health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}
```

---

### 11. schemas/common.py

```python
"""
Common Pydantic schemas used across the API.
"""
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class IDSchema(BaseSchema):
    """Schema with UUID ID."""
    
    id: UUID


class TimestampSchema(BaseSchema):
    """Schema with timestamps."""
    
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated response wrapper."""
    
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int
    
    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page,
        )


class MessageResponse(BaseSchema):
    """Simple message response."""
    
    message: str
    success: bool = True


class ErrorResponse(BaseSchema):
    """Error response."""
    
    detail: str
    code: str | None = None
```

---

### 12. schemas/auth.py

```python
"""
Authentication schemas.
"""
from uuid import UUID

from pydantic import EmailStr, Field

from app.models.user import UserRole, UserStatus
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class LoginRequest(BaseSchema):
    """Login request schema."""
    
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseSchema):
    """Registration request schema."""
    
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=255)
    tenant_name: str | None = Field(default=None, min_length=2, max_length=255)


class TokenResponse(BaseSchema):
    """Token response schema."""
    
    access_token: str
    token_type: str = "bearer"


class UserResponse(IDSchema, TimestampSchema):
    """User response schema."""
    
    email: str
    name: str
    role: UserRole
    status: UserStatus
    tenant_id: UUID | None = None


class AuthResponse(TokenResponse):
    """Authentication response with user info."""
    
    user: UserResponse
```

---

### 13. api/v1/auth.py

```python
"""
Authentication endpoints.
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Authenticate user and return access token."""
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Register a new user and optionally create a tenant."""
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    tenant_id = None
    
    # Create tenant if tenant_name provided
    if request.tenant_name:
        slug = request.tenant_name.lower().replace(" ", "-")
        
        # Check if slug exists
        result = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant slug already exists",
            )
        
        tenant = Tenant(
            name=request.tenant_name,
            slug=slug,
        )
        db.add(tenant)
        await db.flush()
        tenant_id = tenant.id
        role = UserRole.TENANT_ADMIN
    else:
        role = UserRole.READ_ONLY
    
    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        tenant_id=tenant_id,
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)
```

---

### 14. api/v1/router.py

```python
"""
API v1 router aggregating all endpoints.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.sites import router as sites_router
from app.api.v1.audits import router as audits_router
from app.api.v1.keywords import router as keywords_router
from app.api.v1.plans import router as plans_router
from app.api.v1.content import router as content_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(sites_router)
api_router.include_router(audits_router)
api_router.include_router(keywords_router)
api_router.include_router(plans_router)
api_router.include_router(content_router)
```

---

## Frontend Templates

### 1. lib/api.ts

```typescript
import axios, { AxiosError, AxiosInstance } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth token
    this.client.interceptors.request.use((config) => {
      const token = this.token || localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('access_token');
  }

  getToken(): string | null {
    return this.token || localStorage.getItem('access_token');
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', { email, password });
    this.setToken(response.data.access_token);
    return response.data;
  }

  async register(data: { email: string; password: string; name: string; tenant_name?: string }) {
    const response = await this.client.post('/auth/register', data);
    this.setToken(response.data.access_token);
    return response.data;
  }

  async getMe() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  // Sites endpoints
  async getSites(page = 1, perPage = 20) {
    const response = await this.client.get('/sites', { params: { page, per_page: perPage } });
    return response.data;
  }

  async getSite(id: string) {
    const response = await this.client.get(`/sites/${id}`);
    return response.data;
  }

  async createSite(data: { name: string; primary_domain: string; default_language?: string }) {
    const response = await this.client.post('/sites', data);
    return response.data;
  }

  async deleteSite(id: string) {
    const response = await this.client.delete(`/sites/${id}`);
    return response.data;
  }

  // Audits endpoints
  async getAudits(siteId: string, page = 1, perPage = 20) {
    const response = await this.client.get(`/sites/${siteId}/audits`, {
      params: { page, per_page: perPage },
    });
    return response.data;
  }

  async getAudit(id: string) {
    const response = await this.client.get(`/audits/${id}`);
    return response.data;
  }

  async createAudit(siteId: string, auditType: 'quick' | 'full' = 'quick') {
    const response = await this.client.post(`/sites/${siteId}/audits`, { audit_type: auditType });
    return response.data;
  }

  // Keywords endpoints
  async getKeywords(siteId: string, params?: { cluster_id?: string; search?: string }) {
    const response = await this.client.get(`/sites/${siteId}/keywords`, { params });
    return response.data;
  }

  async discoverKeywords(siteId: string, data: { country?: string; language?: string; max_keywords?: number }) {
    const response = await this.client.post(`/sites/${siteId}/keywords/discover`, data);
    return response.data;
  }

  async getKeywordClusters(siteId: string) {
    const response = await this.client.get(`/sites/${siteId}/keyword-clusters`);
    return response.data;
  }

  // Plans endpoints
  async getPlans(siteId: string) {
    const response = await this.client.get(`/sites/${siteId}/seo-plans`);
    return response.data;
  }

  async getPlan(id: string) {
    const response = await this.client.get(`/plans/${id}`);
    return response.data;
  }

  async generatePlan(siteId: string, data: { timeframe_months?: number; goals?: string[] }) {
    const response = await this.client.post(`/sites/${siteId}/plans/generate`, data);
    return response.data;
  }

  async updateTask(taskId: string, data: { status?: string; title?: string }) {
    const response = await this.client.patch(`/tasks/${taskId}`, data);
    return response.data;
  }

  // Content endpoints
  async getContentBriefs(siteId: string) {
    const response = await this.client.get(`/sites/${siteId}/content/briefs`);
    return response.data;
  }

  async createContentBrief(siteId: string, data: { keyword_cluster_id: string; page_type?: string }) {
    const response = await this.client.post(`/sites/${siteId}/content/briefs`, data);
    return response.data;
  }

  async getContentDraft(id: string) {
    const response = await this.client.get(`/drafts/${id}`);
    return response.data;
  }

  async createContentDraft(briefId: string, generateFull = true) {
    const response = await this.client.post(`/briefs/${briefId}/drafts`, { generate_full: generateFull });
    return response.data;
  }
}

export const api = new ApiClient();
export default api;
```

---

### 2. stores/auth.ts

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/lib/api';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string | null;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; name: string; tenant_name?: string }) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.login(email, password);
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Login failed',
            isLoading: false,
          });
          throw error;
        }
      },

      register: async (data) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.register(data);
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Registration failed',
            isLoading: false,
          });
          throw error;
        }
      },

      logout: () => {
        api.clearToken();
        set({
          user: null,
          isAuthenticated: false,
          error: null,
        });
      },

      loadUser: async () => {
        if (!api.getToken()) {
          set({ isAuthenticated: false, user: null });
          return;
        }
        
        set({ isLoading: true });
        try {
          const user = await api.getMe();
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          api.clearToken();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
```

---

### 3. components/ui/button.tsx

```typescript
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-500',
        destructive: 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500',
        outline: 'border border-gray-300 bg-white hover:bg-gray-50 focus-visible:ring-gray-500',
        secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 focus-visible:ring-gray-500',
        ghost: 'hover:bg-gray-100 focus-visible:ring-gray-500',
        link: 'text-blue-600 underline-offset-4 hover:underline focus-visible:ring-blue-500',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-12 rounded-md px-8 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <>
            <svg
              className="mr-2 h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Loading...
          </>
        ) : (
          children
        )}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

---

### 4. lib/utils.ts

```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(date));
}

export function formatDateTime(date: string | Date) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(date));
}

export function truncate(str: string, length: number) {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function getSeverityColor(severity: string) {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'text-red-700 bg-red-100';
    case 'high':
      return 'text-orange-700 bg-orange-100';
    case 'medium':
      return 'text-yellow-700 bg-yellow-100';
    case 'low':
      return 'text-green-700 bg-green-100';
    default:
      return 'text-gray-700 bg-gray-100';
  }
}

export function getStatusColor(status: string) {
  switch (status.toLowerCase()) {
    case 'completed':
    case 'done':
    case 'resolved':
      return 'text-green-700 bg-green-100';
    case 'running':
    case 'in_progress':
      return 'text-blue-700 bg-blue-100';
    case 'pending':
    case 'todo':
      return 'text-gray-700 bg-gray-100';
    case 'failed':
      return 'text-red-700 bg-red-100';
    default:
      return 'text-gray-700 bg-gray-100';
  }
}
```

---

This file contains all critical code templates needed to start implementation. The implementation agent should use these as the base and expand from here.
