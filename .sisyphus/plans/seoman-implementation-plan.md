# SEOman Implementation Plan

## Executive Summary

This plan outlines the complete implementation of SEOman, a multi-tenant SEO platform with AI-powered analysis. The project will be built in 4 phases over approximately 16-20 weeks, culminating in a production-ready application deployed to GitHub.

**Target Repository**: `https://github.com/ghost-writer-hub/SEOman`

---

## Table of Contents

1. [Phase 1: MVP1 - Core Platform](#phase-1-mvp1---core-platform)
2. [Phase 2: MVP2 - Keyword Research](#phase-2-mvp2---keyword-research)
3. [Phase 3: AI Features](#phase-3-ai-features)
4. [Phase 4: Documentation](#phase-4-documentation)
5. [GitHub Setup & Deployment](#github-setup--deployment)
6. [File Specifications](#file-specifications)
7. [API Contracts](#api-contracts)
8. [Database Schema](#database-schema)

---

## Phase 1: MVP1 - Core Platform

**Duration**: 4-6 weeks
**Goal**: Working audit platform with basic CRUD operations

### 1.1 Database Layer

#### Files to Create:

```
backend/app/
├── database.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── tenant.py
│   ├── user.py
│   ├── site.py
│   ├── crawl.py
│   └── audit.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| DB-001 | Create database.py with async SQLAlchemy engine | config.py | P0 |
| DB-002 | Create base model with tenant_id mixin | DB-001 | P0 |
| DB-003 | Create Tenant model | DB-002 | P0 |
| DB-004 | Create User model with roles | DB-003 | P0 |
| DB-005 | Create Site model | DB-004 | P0 |
| DB-006 | Create CrawlJob model | DB-005 | P0 |
| DB-007 | Create CrawlPage model | DB-006 | P0 |
| DB-008 | Create AuditRun model | DB-007 | P0 |
| DB-009 | Create SeoIssue model | DB-008 | P0 |
| DB-010 | Setup Alembic migrations | DB-009 | P0 |
| DB-011 | Create initial migration | DB-010 | P0 |

### 1.2 Core Security

#### Files to Create:

```
backend/app/core/
├── __init__.py
├── security.py
├── deps.py
└── exceptions.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| SEC-001 | Create password hashing utilities | - | P0 |
| SEC-002 | Create JWT token generation/validation | SEC-001 | P0 |
| SEC-003 | Create authentication dependencies | SEC-002 | P0 |
| SEC-004 | Create RBAC permission checker | SEC-003 | P0 |
| SEC-005 | Create custom HTTP exceptions | - | P0 |

### 1.3 API Layer

#### Files to Create:

```
backend/app/
├── main.py
├── schemas/
│   ├── __init__.py
│   ├── common.py
│   ├── auth.py
│   ├── tenant.py
│   ├── user.py
│   ├── site.py
│   ├── crawl.py
│   └── audit.py
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       ├── auth.py
│       ├── tenants.py
│       ├── users.py
│       ├── sites.py
│       ├── crawls.py
│       └── audits.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| API-001 | Create main.py FastAPI application | DB-001 | P0 |
| API-002 | Create common schemas (pagination, responses) | - | P0 |
| API-003 | Create auth schemas | API-002 | P0 |
| API-004 | Create tenant schemas | API-002 | P0 |
| API-005 | Create user schemas | API-002 | P0 |
| API-006 | Create site schemas | API-002 | P0 |
| API-007 | Create crawl schemas | API-002 | P0 |
| API-008 | Create audit schemas | API-002 | P0 |
| API-009 | Create auth endpoints (login, register, me) | SEC-003, API-003 | P0 |
| API-010 | Create tenant endpoints (CRUD) | API-004 | P0 |
| API-011 | Create user endpoints (CRUD, invite) | API-005 | P0 |
| API-012 | Create site endpoints (CRUD) | API-006 | P0 |
| API-013 | Create crawl endpoints (start, status, pages) | API-007 | P0 |
| API-014 | Create audit endpoints (run, list, detail) | API-008 | P0 |
| API-015 | Create health check endpoint | API-001 | P0 |
| API-016 | Create v1 router aggregating all routes | API-009 to API-015 | P0 |

### 1.4 Services Layer

#### Files to Create:

```
backend/app/services/
├── __init__.py
├── tenant_service.py
├── user_service.py
├── site_service.py
├── crawl_service.py
└── audit_service.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| SVC-001 | Create tenant service (CRUD operations) | DB-003 | P0 |
| SVC-002 | Create user service (CRUD, auth) | DB-004 | P0 |
| SVC-003 | Create site service (CRUD) | DB-005 | P0 |
| SVC-004 | Create crawl service (trigger, status) | DB-006, DB-007 | P0 |
| SVC-005 | Create audit service (run, analyze) | DB-008, DB-009 | P0 |

### 1.5 Quick Analyzer Integration

#### Files to Create:

```
backend/app/integrations/
├── __init__.py
├── seoanalyzer.py
└── storage.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| INT-001 | Create SEO analyzer HTTP client | config.py | P0 |
| INT-002 | Create MinIO storage client | config.py | P1 |
| INT-003 | Integrate analyzer with audit service | INT-001, SVC-005 | P0 |

### 1.6 Background Workers

#### Files to Create:

```
backend/app/
├── worker.py
└── tasks/
    ├── __init__.py
    ├── crawl_tasks.py
    └── audit_tasks.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| WRK-001 | Create Celery app configuration | config.py | P0 |
| WRK-002 | Create crawl background tasks | SVC-004 | P0 |
| WRK-003 | Create audit background tasks | SVC-005 | P0 |

### 1.7 Frontend - Core Dashboard

#### Files to Create:

```
frontend/src/
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── utils.ts
├── stores/
│   ├── auth.ts
│   └── sites.ts
├── components/
│   ├── ui/
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── card.tsx
│   │   ├── table.tsx
│   │   ├── badge.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown.tsx
│   │   ├── tabs.tsx
│   │   └── toast.tsx
│   ├── layout/
│   │   ├── header.tsx
│   │   ├── sidebar.tsx
│   │   └── shell.tsx
│   └── forms/
│       ├── login-form.tsx
│       ├── site-form.tsx
│       └── audit-form.tsx
├── app/
│   ├── layout.tsx (update)
│   ├── page.tsx (update - landing)
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── register/
│   │       └── page.tsx
│   └── (dashboard)/
│       ├── layout.tsx
│       ├── page.tsx
│       ├── sites/
│       │   ├── page.tsx
│       │   ├── [id]/
│       │   │   └── page.tsx
│       │   └── new/
│       │       └── page.tsx
│       └── audits/
│           ├── page.tsx
│           └── [id]/
│               └── page.tsx
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| FE-001 | Create API client with axios | - | P0 |
| FE-002 | Create auth utilities (token storage) | FE-001 | P0 |
| FE-003 | Create Zustand auth store | FE-002 | P0 |
| FE-004 | Create base UI components (shadcn style) | - | P0 |
| FE-005 | Create layout components (header, sidebar, shell) | FE-004 | P0 |
| FE-006 | Create login page | FE-003, FE-004 | P0 |
| FE-007 | Create register page | FE-003, FE-004 | P0 |
| FE-008 | Create dashboard layout with protected routes | FE-005, FE-003 | P0 |
| FE-009 | Create dashboard home page | FE-008 | P0 |
| FE-010 | Create sites list page | FE-008 | P0 |
| FE-011 | Create site detail page | FE-010 | P0 |
| FE-012 | Create new site form page | FE-010 | P0 |
| FE-013 | Create audits list page | FE-008 | P0 |
| FE-014 | Create audit detail page with issues | FE-013 | P0 |
| FE-015 | Create sites Zustand store | FE-001 | P0 |

---

## Phase 2: MVP2 - Keyword Research

**Duration**: 2-3 weeks
**Goal**: DataForSEO integration with keyword discovery and clustering

### 2.1 DataForSEO Integration

#### Files to Create:

```
backend/app/
├── integrations/
│   └── dataforseo.py
├── models/
│   └── keyword.py
├── schemas/
│   └── keyword.py
├── services/
│   └── keyword_service.py
├── api/v1/
│   └── keywords.py
└── tasks/
    └── keyword_tasks.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| KW-001 | Create DataForSEO HTTP client | config.py | P0 |
| KW-002 | Create Keyword model | DB-002 | P0 |
| KW-003 | Create KeywordCluster model | KW-002 | P0 |
| KW-004 | Create keyword schemas | API-002 | P0 |
| KW-005 | Create keyword service (discover, expand, metrics) | KW-001, KW-002 | P0 |
| KW-006 | Create keyword clustering algorithm | KW-005 | P0 |
| KW-007 | Create keyword API endpoints | KW-004, KW-005 | P0 |
| KW-008 | Create keyword background tasks | KW-005 | P0 |
| KW-009 | Add migration for keyword tables | KW-002, KW-003 | P0 |

### 2.2 Frontend - Keyword Research

#### Files to Create:

```
frontend/src/
├── stores/
│   └── keywords.ts
├── components/
│   ├── keywords/
│   │   ├── keyword-table.tsx
│   │   ├── cluster-card.tsx
│   │   └── keyword-filters.tsx
│   └── forms/
│       └── keyword-discovery-form.tsx
└── app/(dashboard)/
    └── keywords/
        ├── page.tsx
        └── clusters/
            └── [id]/
                └── page.tsx
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| KW-FE-001 | Create keywords Zustand store | FE-001 | P0 |
| KW-FE-002 | Create keyword table component | FE-004 | P0 |
| KW-FE-003 | Create cluster card component | FE-004 | P0 |
| KW-FE-004 | Create keyword discovery form | FE-004 | P0 |
| KW-FE-005 | Create keywords list page | KW-FE-001 to KW-FE-004 | P0 |
| KW-FE-006 | Create cluster detail page | KW-FE-003 | P0 |

---

## Phase 3: AI Features

**Duration**: 3-4 weeks
**Goal**: LangGraph workflows for audit analysis, SEO plans, and content generation

### 3.1 LLM Integration

#### Files to Create:

```
backend/app/
├── integrations/
│   └── llm.py
├── agents/
│   ├── __init__.py
│   ├── config.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── crawl_tools.py
│   │   ├── keyword_tools.py
│   │   ├── audit_tools.py
│   │   └── content_tools.py
│   └── workflows/
│       ├── __init__.py
│       ├── audit_workflow.py
│       ├── keyword_workflow.py
│       ├── plan_workflow.py
│       └── content_workflow.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| AI-001 | Create LLM client abstraction (local/OpenAI/Anthropic) | config.py | P0 |
| AI-002 | Create agent configuration | AI-001 | P0 |
| AI-003 | Create crawl tools for agents | SVC-004 | P0 |
| AI-004 | Create keyword tools for agents | KW-005 | P0 |
| AI-005 | Create audit tools for agents | SVC-005 | P0 |
| AI-006 | Create content tools for agents | - | P0 |
| AI-007 | Create audit analysis workflow (LangGraph) | AI-002, AI-005 | P0 |
| AI-008 | Create keyword research workflow | AI-002, AI-004 | P0 |
| AI-009 | Create SEO plan workflow | AI-007, AI-008 | P0 |
| AI-010 | Create content generation workflow | AI-006, AI-004 | P0 |

### 3.2 SEO Plan Models & API

#### Files to Create:

```
backend/app/
├── models/
│   └── plan.py
├── schemas/
│   └── plan.py
├── services/
│   └── plan_service.py
├── api/v1/
│   └── plans.py
└── tasks/
    └── plan_tasks.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| PLAN-001 | Create SeoPlan model | DB-002 | P0 |
| PLAN-002 | Create SeoTask model | PLAN-001 | P0 |
| PLAN-003 | Create plan schemas | API-002 | P0 |
| PLAN-004 | Create plan service | PLAN-001, AI-009 | P0 |
| PLAN-005 | Create plan API endpoints | PLAN-003, PLAN-004 | P0 |
| PLAN-006 | Create plan background tasks | PLAN-004 | P0 |
| PLAN-007 | Add migration for plan tables | PLAN-001, PLAN-002 | P0 |

### 3.3 Content Generation Models & API

#### Files to Create:

```
backend/app/
├── models/
│   └── content.py
├── schemas/
│   └── content.py
├── services/
│   └── content_service.py
├── api/v1/
│   └── content.py
└── tasks/
    └── content_tasks.py
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| CNT-001 | Create ContentBrief model | DB-002 | P0 |
| CNT-002 | Create ContentDraft model | CNT-001 | P0 |
| CNT-003 | Create content schemas | API-002 | P0 |
| CNT-004 | Create content service | CNT-001, AI-010 | P0 |
| CNT-005 | Create content API endpoints | CNT-003, CNT-004 | P0 |
| CNT-006 | Create content background tasks | CNT-004 | P0 |
| CNT-007 | Add migration for content tables | CNT-001, CNT-002 | P0 |

### 3.4 Frontend - AI Features

#### Files to Create:

```
frontend/src/
├── stores/
│   ├── plans.ts
│   └── content.ts
├── components/
│   ├── plans/
│   │   ├── plan-timeline.tsx
│   │   ├── task-card.tsx
│   │   └── task-board.tsx
│   ├── content/
│   │   ├── brief-card.tsx
│   │   ├── draft-editor.tsx
│   │   └── content-preview.tsx
│   └── ai/
│       ├── generation-progress.tsx
│       └── ai-suggestions.tsx
└── app/(dashboard)/
    ├── plans/
    │   ├── page.tsx
    │   └── [id]/
    │       └── page.tsx
    └── content/
        ├── page.tsx
        ├── briefs/
        │   └── [id]/
        │       └── page.tsx
        └── drafts/
            └── [id]/
                └── page.tsx
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| AI-FE-001 | Create plans Zustand store | FE-001 | P0 |
| AI-FE-002 | Create content Zustand store | FE-001 | P0 |
| AI-FE-003 | Create plan timeline component | FE-004 | P0 |
| AI-FE-004 | Create task card/board components | FE-004 | P0 |
| AI-FE-005 | Create content brief card | FE-004 | P0 |
| AI-FE-006 | Create draft editor (markdown) | FE-004 | P0 |
| AI-FE-007 | Create AI generation progress indicator | FE-004 | P0 |
| AI-FE-008 | Create plans list page | AI-FE-001, AI-FE-003 | P0 |
| AI-FE-009 | Create plan detail page with tasks | AI-FE-004 | P0 |
| AI-FE-010 | Create content briefs list page | AI-FE-002, AI-FE-005 | P0 |
| AI-FE-011 | Create brief detail page | AI-FE-005 | P0 |
| AI-FE-012 | Create draft editor page | AI-FE-006 | P0 |

---

## Phase 4: Documentation

**Duration**: 1-2 weeks
**Goal**: Comprehensive documentation site using Docusaurus under /docs

### 4.1 Documentation Setup

#### Files to Create:

```
docs/
├── docusaurus.config.js
├── package.json
├── sidebars.js
├── static/
│   └── img/
│       ├── logo.svg
│       └── favicon.ico
├── src/
│   ├── css/
│   │   └── custom.css
│   └── pages/
│       └── index.tsx
└── docs/
    ├── intro.md
    ├── getting-started/
    │   ├── installation.md
    │   ├── configuration.md
    │   └── quick-start.md
    ├── architecture/
    │   ├── overview.md
    │   ├── backend.md
    │   ├── frontend.md
    │   ├── database.md
    │   └── agents.md
    ├── api/
    │   ├── overview.md
    │   ├── authentication.md
    │   ├── tenants.md
    │   ├── sites.md
    │   ├── crawls.md
    │   ├── audits.md
    │   ├── keywords.md
    │   ├── plans.md
    │   └── content.md
    ├── guides/
    │   ├── running-audit.md
    │   ├── keyword-research.md
    │   ├── creating-seo-plan.md
    │   ├── generating-content.md
    │   └── multi-tenancy.md
    ├── integrations/
    │   ├── deepcrawl.md
    │   ├── dataforseo.md
    │   └── llm-providers.md
    ├── deployment/
    │   ├── docker.md
    │   ├── kubernetes.md
    │   └── production.md
    └── contributing/
        ├── development.md
        └── code-style.md
```

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| DOC-001 | Initialize Docusaurus project | - | P0 |
| DOC-002 | Configure theme and branding | DOC-001 | P0 |
| DOC-003 | Write introduction and overview | DOC-001 | P0 |
| DOC-004 | Write getting started guides | DOC-003 | P0 |
| DOC-005 | Write architecture documentation | DOC-003 | P0 |
| DOC-006 | Write API reference documentation | DOC-005 | P0 |
| DOC-007 | Write user guides | DOC-006 | P0 |
| DOC-008 | Write integration documentation | DOC-005 | P0 |
| DOC-009 | Write deployment documentation | DOC-004 | P0 |
| DOC-010 | Write contributing guidelines | DOC-001 | P1 |
| DOC-011 | Add OpenAPI/Swagger integration | DOC-006 | P1 |
| DOC-012 | Configure static site generation | DOC-002 | P0 |

---

## GitHub Setup & Deployment

### 5.1 Repository Setup

#### Task Breakdown:

| Task ID | Task | Dependencies | Priority |
|---------|------|--------------|----------|
| GH-001 | Create repository ghost-writer-hub/SEOman | - | P0 |
| GH-002 | Initialize git in project | GH-001 | P0 |
| GH-003 | Create .gitignore (comprehensive) | GH-002 | P0 |
| GH-004 | Create GitHub Actions CI/CD workflow | GH-002 | P1 |
| GH-005 | Create release automation | GH-004 | P2 |
| GH-006 | Push initial commit | GH-003 | P0 |
| GH-007 | Create development branch | GH-006 | P0 |
| GH-008 | Configure branch protection | GH-007 | P1 |

### 5.2 CI/CD Workflows

#### Files to Create:

```
.github/
├── workflows/
│   ├── ci.yml
│   ├── deploy-docs.yml
│   └── release.yml
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   └── feature_request.md
├── PULL_REQUEST_TEMPLATE.md
└── CODEOWNERS
```

---

## File Specifications

### Backend File Specifications

#### `backend/app/database.py`

```python
"""
Database connection and session management.

Requirements:
- Async SQLAlchemy engine using asyncpg
- Session factory with proper scoping
- Context manager for session handling
- Connection pool configuration

Functions:
- get_async_engine() -> AsyncEngine
- get_async_session() -> AsyncGenerator[AsyncSession, None]
- init_db() -> None (create tables)
"""
```

#### `backend/app/models/base.py`

```python
"""
Base model with common fields.

Requirements:
- UUID primary key generation
- created_at, updated_at timestamps
- TenantMixin for multi-tenant models
- Soft delete support (optional)

Classes:
- Base (declarative base)
- TimestampMixin
- TenantMixin
- UUIDMixin
"""
```

#### `backend/app/models/tenant.py`

```python
"""
Tenant model for multi-tenancy.

Fields:
- id: UUID (PK)
- name: str (required)
- slug: str (unique, URL-safe)
- status: enum (active, suspended)
- plan: str (free, pro, enterprise)
- settings: JSONB (optional config)
- created_at, updated_at: datetime

Relationships:
- users: List[User]
- sites: List[Site]
"""
```

#### `backend/app/models/user.py`

```python
"""
User model with role-based access.

Fields:
- id: UUID (PK)
- tenant_id: UUID (FK, nullable for super_admin)
- email: str (unique per tenant)
- password_hash: str
- name: str
- role: enum (super_admin, tenant_admin, seo_manager, read_only)
- status: enum (active, inactive, pending)
- last_login_at: datetime (nullable)
- created_at, updated_at: datetime

Relationships:
- tenant: Tenant
"""
```

#### `backend/app/models/site.py`

```python
"""
Site model for monitored websites.

Fields:
- id: UUID (PK)
- tenant_id: UUID (FK)
- name: str
- primary_domain: str
- additional_domains: JSONB (list)
- default_language: str (ISO code)
- target_countries: JSONB (list of ISO codes)
- cms_type: str (nullable)
- brand_tone: JSONB (voice settings)
- enabled_features: JSONB (list)
- created_at, updated_at: datetime

Relationships:
- tenant: Tenant
- crawl_jobs: List[CrawlJob]
- audit_runs: List[AuditRun]
- keywords: List[Keyword]
"""
```

#### `backend/app/core/security.py`

```python
"""
Security utilities for authentication.

Requirements:
- Password hashing with bcrypt
- JWT token creation/verification
- Token refresh logic
- Permission checking

Functions:
- hash_password(password: str) -> str
- verify_password(plain: str, hashed: str) -> bool
- create_access_token(data: dict, expires_delta: timedelta) -> str
- decode_token(token: str) -> dict
- get_current_user(token: str) -> User
- check_permission(user: User, permission: str) -> bool
"""
```

#### `backend/app/integrations/dataforseo.py`

```python
"""
DataForSEO API client.

Requirements:
- HTTP client with retry logic
- Rate limiting awareness
- Error handling for API errors
- Response parsing

Classes:
- DataForSEOClient
  - __init__(login, password, base_url)
  - async keywords_for_site(domain, country, language, limit) -> List[KeywordData]
  - async keywords_for_keywords(seeds, country, language, limit) -> List[KeywordData]
  - async keyword_overview(keywords, country, language) -> List[KeywordMetrics]
  - async serp_data(keyword, country, language) -> SerpResult
"""
```

#### `backend/app/agents/workflows/audit_workflow.py`

```python
"""
LangGraph workflow for SEO audit analysis.

Requirements:
- StateGraph with typed state
- Nodes for each analysis step
- Tool integration for data access
- Human-readable output generation

Workflow Steps:
1. fetch_crawl_data - Get crawl results
2. analyze_technical_issues - Check status codes, redirects, etc.
3. analyze_onpage_issues - Check meta, headings, content
4. score_issues - Assign severity and impact
5. generate_summary - Create executive summary
6. save_results - Persist to database

State:
- site_id: str
- crawl_job_id: str
- pages: List[CrawlPage]
- issues: List[SeoIssue]
- summary: str
- score: int
"""
```

### Frontend File Specifications

#### `frontend/src/lib/api.ts`

```typescript
/**
 * API client configuration.
 * 
 * Requirements:
 * - Axios instance with base URL from env
 * - Request interceptor for auth token
 * - Response interceptor for error handling
 * - Token refresh on 401
 * 
 * Exports:
 * - api: AxiosInstance
 * - setAuthToken(token: string): void
 * - clearAuthToken(): void
 */
```

#### `frontend/src/stores/auth.ts`

```typescript
/**
 * Zustand store for authentication state.
 * 
 * State:
 * - user: User | null
 * - token: string | null
 * - isAuthenticated: boolean
 * - isLoading: boolean
 * 
 * Actions:
 * - login(email, password): Promise<void>
 * - register(data): Promise<void>
 * - logout(): void
 * - refreshToken(): Promise<void>
 * - loadUser(): Promise<void>
 */
```

#### `frontend/src/components/ui/button.tsx`

```typescript
/**
 * Reusable button component.
 * 
 * Props:
 * - variant: 'default' | 'outline' | 'ghost' | 'destructive'
 * - size: 'sm' | 'md' | 'lg'
 * - isLoading: boolean
 * - disabled: boolean
 * - children: ReactNode
 * - onClick: () => void
 * 
 * Styling: TailwindCSS with cva for variants
 */
```

---

## API Contracts

### Authentication

```yaml
POST /api/v1/auth/login:
  request:
    email: string
    password: string
  response:
    access_token: string
    token_type: "bearer"
    user:
      id: uuid
      email: string
      name: string
      role: string
      tenant_id: uuid | null

POST /api/v1/auth/register:
  request:
    email: string
    password: string
    name: string
    tenant_name: string (optional, creates new tenant)
  response:
    access_token: string
    user: User

GET /api/v1/auth/me:
  headers:
    Authorization: "Bearer {token}"
  response:
    id: uuid
    email: string
    name: string
    role: string
    tenant: Tenant
```

### Sites

```yaml
GET /api/v1/sites:
  headers:
    Authorization: "Bearer {token}"
  query:
    page: int (default: 1)
    per_page: int (default: 20)
  response:
    items: Site[]
    total: int
    page: int
    per_page: int

POST /api/v1/sites:
  headers:
    Authorization: "Bearer {token}"
  request:
    name: string
    primary_domain: string
    default_language: string (default: "en")
    target_countries: string[] (default: ["US"])
  response:
    Site

GET /api/v1/sites/{site_id}:
  response:
    Site with relationships

DELETE /api/v1/sites/{site_id}:
  response:
    success: boolean
```

### Audits

```yaml
POST /api/v1/sites/{site_id}/audits:
  request:
    audit_type: "quick" | "full" (default: "quick")
    options:
      max_pages: int (optional)
  response:
    audit_run:
      id: uuid
      status: "pending" | "running"
      created_at: datetime

GET /api/v1/sites/{site_id}/audits:
  response:
    items: AuditRun[]
    total: int

GET /api/v1/audits/{audit_id}:
  response:
    audit_run: AuditRun
    issues: SeoIssue[]
    summary: string
    score: int
```

### Keywords

```yaml
POST /api/v1/sites/{site_id}/keywords/discover:
  request:
    country: string (default: "US")
    language: string (default: "en")
    max_keywords: int (default: 100)
  response:
    job_id: uuid
    status: "pending"

GET /api/v1/sites/{site_id}/keywords:
  query:
    cluster_id: uuid (optional)
    search: string (optional)
  response:
    items: Keyword[]
    total: int

GET /api/v1/sites/{site_id}/keyword-clusters:
  response:
    items: KeywordCluster[]
```

### SEO Plans

```yaml
POST /api/v1/sites/{site_id}/plans/generate:
  request:
    timeframe_months: int (default: 6)
    goals: string[]
  response:
    plan:
      id: uuid
      status: "generating"

GET /api/v1/plans/{plan_id}:
  response:
    plan: SeoPlan
    tasks: SeoTask[]
    timeline: TimelineData

PATCH /api/v1/tasks/{task_id}:
  request:
    status: "todo" | "in_progress" | "done"
  response:
    SeoTask
```

### Content

```yaml
POST /api/v1/sites/{site_id}/content/briefs:
  request:
    keyword_cluster_id: uuid
    page_type: "blog" | "landing" | "product"
    word_count_target: int (optional)
  response:
    brief:
      id: uuid
      status: "generating"

POST /api/v1/briefs/{brief_id}/drafts:
  request:
    generate_full: boolean (default: true)
  response:
    draft:
      id: uuid
      status: "generating"

GET /api/v1/drafts/{draft_id}:
  response:
    draft: ContentDraft
    brief: ContentBrief
```

---

## Database Schema

### SQL Schema (PostgreSQL)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enums
CREATE TYPE user_role AS ENUM ('super_admin', 'tenant_admin', 'seo_manager', 'read_only');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'pending');
CREATE TYPE tenant_status AS ENUM ('active', 'suspended');
CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE issue_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE issue_status AS ENUM ('open', 'resolved', 'ignored');
CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done');
CREATE TYPE task_category AS ENUM ('technical', 'content', 'on_page', 'authority', 'other');
CREATE TYPE page_type AS ENUM ('landing', 'blog', 'category', 'product', 'other');
CREATE TYPE draft_status AS ENUM ('draft', 'approved', 'rejected', 'published');

-- Tenants
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status tenant_status DEFAULT 'active',
    plan VARCHAR(50) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'read_only',
    status user_status DEFAULT 'active',
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

-- Sites
CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    primary_domain VARCHAR(255) NOT NULL,
    additional_domains JSONB DEFAULT '[]',
    default_language VARCHAR(10) DEFAULT 'en',
    target_countries JSONB DEFAULT '["US"]',
    cms_type VARCHAR(100),
    brand_tone JSONB DEFAULT '{}',
    enabled_features JSONB DEFAULT '["audit", "keywords", "content"]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Crawl Jobs
CREATE TABLE crawl_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    status job_status DEFAULT 'pending',
    config JSONB DEFAULT '{}',
    pages_crawled INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Crawl Pages
CREATE TABLE crawl_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawl_job_id UUID NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status_code INTEGER,
    content_type VARCHAR(100),
    canonical_url TEXT,
    meta_robots VARCHAR(100),
    title TEXT,
    meta_description TEXT,
    h1 TEXT,
    h2 JSONB DEFAULT '[]',
    h3 JSONB DEFAULT '[]',
    word_count INTEGER,
    internal_links JSONB DEFAULT '[]',
    external_links JSONB DEFAULT '[]',
    noindex BOOLEAN DEFAULT FALSE,
    nofollow BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit Runs
CREATE TABLE audit_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    crawl_job_id UUID REFERENCES crawl_jobs(id),
    created_by_user_id UUID REFERENCES users(id),
    audit_type VARCHAR(50) DEFAULT 'quick',
    status job_status DEFAULT 'pending',
    score INTEGER,
    summary TEXT,
    findings_overview JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- SEO Issues
CREATE TABLE seo_issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_run_id UUID NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    severity issue_severity NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    suggested_fix TEXT,
    affected_urls JSONB DEFAULT '[]',
    status issue_status DEFAULT 'open',
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Keywords
CREATE TABLE keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    text VARCHAR(500) NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    country VARCHAR(10) DEFAULT 'US',
    search_volume INTEGER,
    cpc DECIMAL(10, 2),
    competition DECIMAL(5, 4),
    difficulty INTEGER,
    intent VARCHAR(50),
    trend JSONB DEFAULT '[]',
    dataforseo_raw JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(site_id, text, language, country)
);

-- Keyword Clusters
CREATE TABLE keyword_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    label VARCHAR(255) NOT NULL,
    description TEXT,
    language VARCHAR(10) DEFAULT 'en',
    country VARCHAR(10) DEFAULT 'US',
    primary_keyword_id UUID REFERENCES keywords(id),
    mapped_url TEXT,
    is_new_page_recommended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Keyword to Cluster mapping
CREATE TABLE keyword_cluster_members (
    keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES keyword_clusters(id) ON DELETE CASCADE,
    PRIMARY KEY (keyword_id, cluster_id)
);

-- SEO Plans
CREATE TABLE seo_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    timeframe_months INTEGER DEFAULT 6,
    goals JSONB DEFAULT '[]',
    timeline_summary JSONB DEFAULT '{}',
    generated_from_audit_id UUID REFERENCES audit_runs(id),
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- SEO Tasks
CREATE TABLE seo_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seo_plan_id UUID NOT NULL REFERENCES seo_plans(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    category task_category NOT NULL,
    impact issue_severity NOT NULL,
    effort issue_severity NOT NULL,
    assignee_type VARCHAR(50),
    status task_status DEFAULT 'todo',
    due_month INTEGER,
    related_issue_ids JSONB DEFAULT '[]',
    related_cluster_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content Briefs
CREATE TABLE content_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    keyword_cluster_id UUID REFERENCES keyword_clusters(id),
    target_keyword VARCHAR(500) NOT NULL,
    secondary_keywords JSONB DEFAULT '[]',
    search_intent VARCHAR(100),
    suggested_slug VARCHAR(255),
    page_type page_type DEFAULT 'blog',
    outline JSONB DEFAULT '{}',
    internal_link_suggestions JSONB DEFAULT '[]',
    word_count_target INTEGER DEFAULT 1500,
    tone_guidelines JSONB DEFAULT '{}',
    language VARCHAR(10) DEFAULT 'en',
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content Drafts
CREATE TABLE content_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    content_brief_id UUID NOT NULL REFERENCES content_briefs(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,
    title_tag VARCHAR(70),
    meta_description VARCHAR(160),
    h1 VARCHAR(255),
    body_markdown TEXT,
    body_html TEXT,
    faq JSONB DEFAULT '[]',
    word_count INTEGER,
    status draft_status DEFAULT 'draft',
    created_by_user_id UUID REFERENCES users(id),
    updated_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sites_tenant ON sites(tenant_id);
CREATE INDEX idx_sites_domain ON sites(primary_domain);
CREATE INDEX idx_crawl_jobs_site ON crawl_jobs(site_id);
CREATE INDEX idx_crawl_pages_job ON crawl_pages(crawl_job_id);
CREATE INDEX idx_crawl_pages_site ON crawl_pages(site_id);
CREATE INDEX idx_audit_runs_site ON audit_runs(site_id);
CREATE INDEX idx_seo_issues_audit ON seo_issues(audit_run_id);
CREATE INDEX idx_seo_issues_site ON seo_issues(site_id);
CREATE INDEX idx_keywords_site ON keywords(site_id);
CREATE INDEX idx_keyword_clusters_site ON keyword_clusters(site_id);
CREATE INDEX idx_seo_plans_site ON seo_plans(site_id);
CREATE INDEX idx_seo_tasks_plan ON seo_tasks(seo_plan_id);
CREATE INDEX idx_content_briefs_site ON content_briefs(site_id);
CREATE INDEX idx_content_drafts_brief ON content_drafts(content_brief_id);
```

---

## Implementation Order Summary

### Week 1-2: Foundation
1. DB-001 to DB-011 (Database layer)
2. SEC-001 to SEC-005 (Security)
3. API-001 to API-003 (FastAPI setup, common schemas)

### Week 3-4: Core API
4. API-004 to API-016 (All API endpoints)
5. SVC-001 to SVC-005 (Services)
6. INT-001 to INT-003 (Integrations)
7. WRK-001 to WRK-003 (Workers)

### Week 5-6: Frontend Core
8. FE-001 to FE-015 (All frontend MVP1)

### Week 7-8: Keyword Research
9. KW-001 to KW-009 (Backend keywords)
10. KW-FE-001 to KW-FE-006 (Frontend keywords)

### Week 9-11: AI Features
11. AI-001 to AI-010 (LangGraph workflows)
12. PLAN-001 to PLAN-007 (SEO Plans)
13. CNT-001 to CNT-007 (Content Generation)
14. AI-FE-001 to AI-FE-012 (Frontend AI features)

### Week 12-13: Documentation
15. DOC-001 to DOC-012 (Docusaurus docs)

### Week 14: GitHub & Polish
16. GH-001 to GH-008 (GitHub setup)
17. Final testing and bug fixes

---

## Success Criteria

### MVP1 Complete When:
- [ ] User can register and login
- [ ] User can create a site
- [ ] User can run a quick audit
- [ ] User can see audit results with issues
- [ ] All tests pass
- [ ] API documentation accessible at /docs

### MVP2 Complete When:
- [ ] User can discover keywords for a site
- [ ] Keywords are clustered automatically
- [ ] User can view keyword metrics and clusters
- [ ] DataForSEO integration working

### AI Features Complete When:
- [ ] User can generate SEO plan from audit
- [ ] User can generate content briefs from clusters
- [ ] User can generate full content drafts
- [ ] LangGraph workflows are observable

### Documentation Complete When:
- [ ] Docusaurus site builds without errors
- [ ] All API endpoints documented
- [ ] Getting started guide works end-to-end
- [ ] Architecture diagrams included

### Deployment Complete When:
- [ ] Code pushed to ghost-writer-hub/SEOman
- [ ] CI/CD pipeline passes
- [ ] README complete with badges
- [ ] Docker Compose runs all services

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| DataForSEO API limits | High | Implement caching, mock mode for dev |
| LLM cost/latency | Medium | Support local LLM, async processing |
| Multi-tenancy bugs | High | Comprehensive tenant isolation tests |
| Frontend complexity | Medium | Use shadcn/ui, focus on MVP features |
| Casdoor complexity | Medium | Defer to Phase 2, use simple JWT first |

---

## Notes for Implementation Agent

1. **Start with database models** - Everything depends on them
2. **Use async throughout** - Backend is async-first with SQLAlchemy 2.0
3. **Test tenant isolation** - Every query must filter by tenant_id
4. **Mock external APIs** - Create mock modes for DataForSEO, LLM
5. **Frontend last** - Backend API must be stable first
6. **Documentation concurrent** - Write docs as you build features
