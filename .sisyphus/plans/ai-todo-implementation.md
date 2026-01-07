# SEOman Implementation Tasks

This file contains the ordered task list for implementation. Each task is atomic and can be verified independently.

---

## Phase 0: GitHub Setup

```yaml
- id: GH-001
  task: Create GitHub repository ghost-writer-hub/SEOman
  command: |
    gh repo create ghost-writer-hub/SEOman --public --description "Multi-tenant SEO Platform with AI-powered analysis"
  verification: gh repo view ghost-writer-hub/SEOman
  status: pending

- id: GH-002
  task: Initialize git in project
  command: |
    cd /home/carlos/docker/SEOman
    git init
    git remote add origin https://github.com/ghost-writer-hub/SEOman.git
  verification: git remote -v
  status: pending

- id: GH-003
  task: Create comprehensive .gitignore
  file: .gitignore
  status: pending
```

---

## Phase 1: MVP1 - Core Platform

### 1.1 Database Layer

```yaml
- id: DB-001
  task: Create database.py with async SQLAlchemy engine
  file: backend/app/database.py
  template: code-templates.md#1-databasepy
  verification: python -c "from app.database import engine; print('OK')"
  dependencies: []
  status: pending

- id: DB-002
  task: Create models/__init__.py
  file: backend/app/models/__init__.py
  content: |
    from app.models.base import Base, BaseModel, TenantBaseModel
    from app.models.tenant import Tenant, TenantStatus
    from app.models.user import User, UserRole, UserStatus
    from app.models.site import Site
    from app.models.crawl import CrawlJob, CrawlPage, JobStatus
    from app.models.audit import AuditRun, SeoIssue, IssueSeverity, IssueStatus
  dependencies: [DB-003, DB-004, DB-005, DB-006, DB-007]
  status: pending

- id: DB-003
  task: Create base model with mixins
  file: backend/app/models/base.py
  template: code-templates.md#2-modelsbasepy
  dependencies: [DB-001]
  status: pending

- id: DB-004
  task: Create Tenant model
  file: backend/app/models/tenant.py
  template: code-templates.md#3-modelstenantpy
  dependencies: [DB-003]
  status: pending

- id: DB-005
  task: Create User model
  file: backend/app/models/user.py
  template: code-templates.md#4-modelsuserpy
  dependencies: [DB-004]
  status: pending

- id: DB-006
  task: Create Site model
  file: backend/app/models/site.py
  template: code-templates.md#5-modelssitepy
  dependencies: [DB-004]
  status: pending

- id: DB-007
  task: Create CrawlJob and CrawlPage models
  file: backend/app/models/crawl.py
  template: code-templates.md#6-modelscrawlpy
  dependencies: [DB-006]
  status: pending

- id: DB-008
  task: Create AuditRun and SeoIssue models
  file: backend/app/models/audit.py
  template: code-templates.md#7-modelsauditpy
  dependencies: [DB-007]
  status: pending

- id: DB-009
  task: Initialize Alembic for migrations
  command: |
    cd backend
    alembic init alembic
  verification: ls backend/alembic/versions
  dependencies: [DB-002]
  status: pending

- id: DB-010
  task: Configure Alembic env.py for async
  file: backend/alembic/env.py
  dependencies: [DB-009]
  status: pending

- id: DB-011
  task: Create initial database migration
  command: |
    cd backend
    alembic revision --autogenerate -m "Initial schema"
    alembic upgrade head
  verification: alembic current
  dependencies: [DB-010]
  status: pending
```

### 1.2 Core Security

```yaml
- id: SEC-001
  task: Create core/__init__.py
  file: backend/app/core/__init__.py
  content: |
    from app.core.security import hash_password, verify_password, create_access_token, decode_token
    from app.core.deps import get_current_user, get_current_active_user, CurrentUser
  dependencies: [SEC-002, SEC-003]
  status: pending

- id: SEC-002
  task: Create security utilities
  file: backend/app/core/security.py
  template: code-templates.md#8-coresecuritypy
  dependencies: []
  status: pending

- id: SEC-003
  task: Create FastAPI dependencies
  file: backend/app/core/deps.py
  template: code-templates.md#9-coredepspy
  dependencies: [SEC-002, DB-005]
  status: pending

- id: SEC-004
  task: Create custom exceptions
  file: backend/app/core/exceptions.py
  content: |
    from fastapi import HTTPException, status

    class NotFoundError(HTTPException):
        def __init__(self, resource: str = "Resource"):
            super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")

    class ForbiddenError(HTTPException):
        def __init__(self, detail: str = "Access denied"):
            super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    class BadRequestError(HTTPException):
        def __init__(self, detail: str):
            super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    class ConflictError(HTTPException):
        def __init__(self, detail: str):
            super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
  dependencies: []
  status: pending
```

### 1.3 Schemas

```yaml
- id: SCH-001
  task: Create schemas/__init__.py
  file: backend/app/schemas/__init__.py
  dependencies: [SCH-002, SCH-003, SCH-004, SCH-005, SCH-006, SCH-007]
  status: pending

- id: SCH-002
  task: Create common schemas
  file: backend/app/schemas/common.py
  template: code-templates.md#11-schemascommonpy
  dependencies: []
  status: pending

- id: SCH-003
  task: Create auth schemas
  file: backend/app/schemas/auth.py
  template: code-templates.md#12-schemasauthpy
  dependencies: [SCH-002]
  status: pending

- id: SCH-004
  task: Create tenant schemas
  file: backend/app/schemas/tenant.py
  content: |
    from uuid import UUID
    from app.models.tenant import TenantStatus
    from app.schemas.common import BaseSchema, IDSchema, TimestampSchema

    class TenantCreate(BaseSchema):
        name: str
        slug: str
        plan: str = "free"

    class TenantUpdate(BaseSchema):
        name: str | None = None
        status: TenantStatus | None = None
        plan: str | None = None

    class TenantResponse(IDSchema, TimestampSchema):
        name: str
        slug: str
        status: TenantStatus
        plan: str
  dependencies: [SCH-002]
  status: pending

- id: SCH-005
  task: Create site schemas
  file: backend/app/schemas/site.py
  content: |
    from uuid import UUID
    from app.schemas.common import BaseSchema, IDSchema, TimestampSchema

    class SiteCreate(BaseSchema):
        name: str
        primary_domain: str
        additional_domains: list[str] = []
        default_language: str = "en"
        target_countries: list[str] = ["US"]
        cms_type: str | None = None
        brand_tone: dict = {}
        enabled_features: list[str] = ["audit", "keywords", "content"]

    class SiteUpdate(BaseSchema):
        name: str | None = None
        primary_domain: str | None = None
        additional_domains: list[str] | None = None
        default_language: str | None = None
        target_countries: list[str] | None = None
        cms_type: str | None = None
        brand_tone: dict | None = None
        enabled_features: list[str] | None = None

    class SiteResponse(IDSchema, TimestampSchema):
        tenant_id: UUID
        name: str
        primary_domain: str
        additional_domains: list[str]
        default_language: str
        target_countries: list[str]
        cms_type: str | None
        brand_tone: dict
        enabled_features: list[str]
  dependencies: [SCH-002]
  status: pending

- id: SCH-006
  task: Create crawl schemas
  file: backend/app/schemas/crawl.py
  content: |
    from datetime import datetime
    from uuid import UUID
    from app.models.crawl import JobStatus
    from app.schemas.common import BaseSchema, IDSchema, TimestampSchema

    class CrawlConfig(BaseSchema):
        max_depth: int = 3
        max_pages: int = 1000
        allowed_domains: list[str] = []
        user_agent: str = "SEOman Bot/1.0"
        crawl_delay_ms: int = 100

    class CrawlJobCreate(BaseSchema):
        config: CrawlConfig = CrawlConfig()

    class CrawlJobResponse(IDSchema):
        site_id: UUID
        status: JobStatus
        config: dict
        pages_crawled: int
        errors_count: int
        started_at: datetime | None
        completed_at: datetime | None
        error_message: str | None
        created_at: datetime

    class CrawlPageResponse(IDSchema):
        url: str
        status_code: int | None
        title: str | None
        meta_description: str | None
        h1: str | None
        word_count: int | None
        noindex: bool
        nofollow: bool
        created_at: datetime
  dependencies: [SCH-002]
  status: pending

- id: SCH-007
  task: Create audit schemas
  file: backend/app/schemas/audit.py
  content: |
    from datetime import datetime
    from uuid import UUID
    from app.models.crawl import JobStatus
    from app.models.audit import IssueSeverity, IssueStatus
    from app.schemas.common import BaseSchema, IDSchema

    class AuditCreate(BaseSchema):
        audit_type: str = "quick"
        crawl_job_id: UUID | None = None

    class AuditRunResponse(IDSchema):
        site_id: UUID
        crawl_job_id: UUID | None
        audit_type: str
        status: JobStatus
        score: int | None
        summary: str | None
        findings_overview: dict
        started_at: datetime | None
        completed_at: datetime | None
        error_message: str | None
        created_at: datetime

    class SeoIssueResponse(IDSchema):
        type: str
        category: str
        severity: IssueSeverity
        title: str
        description: str | None
        suggested_fix: str | None
        affected_urls: list[str]
        status: IssueStatus
        created_at: datetime

    class AuditDetailResponse(BaseSchema):
        audit_run: AuditRunResponse
        issues: list[SeoIssueResponse]
  dependencies: [SCH-002]
  status: pending
```

### 1.4 API Endpoints

```yaml
- id: API-001
  task: Create main.py FastAPI application
  file: backend/app/main.py
  template: code-templates.md#10-mainpy
  dependencies: [DB-001, API-016]
  status: pending

- id: API-002
  task: Create api/__init__.py
  file: backend/app/api/__init__.py
  content: ""
  dependencies: []
  status: pending

- id: API-003
  task: Create api/v1/__init__.py
  file: backend/app/api/v1/__init__.py
  content: ""
  dependencies: []
  status: pending

- id: API-004
  task: Create auth endpoints
  file: backend/app/api/v1/auth.py
  template: code-templates.md#13-apiv1authpy
  dependencies: [SEC-003, SCH-003, DB-005]
  status: pending

- id: API-005
  task: Create tenants endpoints
  file: backend/app/api/v1/tenants.py
  dependencies: [SEC-003, SCH-004, DB-004]
  status: pending

- id: API-006
  task: Create users endpoints
  file: backend/app/api/v1/users.py
  dependencies: [SEC-003, SCH-003, DB-005]
  status: pending

- id: API-007
  task: Create sites endpoints
  file: backend/app/api/v1/sites.py
  dependencies: [SEC-003, SCH-005, DB-006]
  status: pending

- id: API-008
  task: Create crawls endpoints
  file: backend/app/api/v1/crawls.py
  dependencies: [SEC-003, SCH-006, DB-007]
  status: pending

- id: API-009
  task: Create audits endpoints
  file: backend/app/api/v1/audits.py
  dependencies: [SEC-003, SCH-007, DB-008]
  status: pending

- id: API-016
  task: Create v1 router
  file: backend/app/api/v1/router.py
  template: code-templates.md#14-apiv1routerpy
  dependencies: [API-004, API-005, API-006, API-007, API-008, API-009]
  status: pending
```

### 1.5 Services

```yaml
- id: SVC-001
  task: Create services/__init__.py
  file: backend/app/services/__init__.py
  content: ""
  dependencies: []
  status: pending

- id: SVC-002
  task: Create tenant service
  file: backend/app/services/tenant_service.py
  dependencies: [DB-004]
  status: pending

- id: SVC-003
  task: Create user service
  file: backend/app/services/user_service.py
  dependencies: [DB-005, SEC-002]
  status: pending

- id: SVC-004
  task: Create site service
  file: backend/app/services/site_service.py
  dependencies: [DB-006]
  status: pending

- id: SVC-005
  task: Create crawl service
  file: backend/app/services/crawl_service.py
  dependencies: [DB-007, INT-001]
  status: pending

- id: SVC-006
  task: Create audit service
  file: backend/app/services/audit_service.py
  dependencies: [DB-008, INT-001]
  status: pending
```

### 1.6 Integrations

```yaml
- id: INT-001
  task: Create integrations/__init__.py
  file: backend/app/integrations/__init__.py
  content: ""
  dependencies: []
  status: pending

- id: INT-002
  task: Create SEO analyzer client
  file: backend/app/integrations/seoanalyzer.py
  dependencies: []
  status: pending

- id: INT-003
  task: Create MinIO storage client
  file: backend/app/integrations/storage.py
  dependencies: []
  status: pending
```

### 1.7 Background Workers

```yaml
- id: WRK-001
  task: Create Celery worker configuration
  file: backend/app/worker.py
  dependencies: []
  status: pending

- id: WRK-002
  task: Create tasks/__init__.py
  file: backend/app/tasks/__init__.py
  content: ""
  dependencies: []
  status: pending

- id: WRK-003
  task: Create crawl tasks
  file: backend/app/tasks/crawl_tasks.py
  dependencies: [SVC-005, WRK-001]
  status: pending

- id: WRK-004
  task: Create audit tasks
  file: backend/app/tasks/audit_tasks.py
  dependencies: [SVC-006, WRK-001]
  status: pending
```

### 1.8 Frontend Core

```yaml
- id: FE-001
  task: Install frontend dependencies
  command: |
    cd frontend
    npm install class-variance-authority lucide-react @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-tabs react-hot-toast
  dependencies: []
  status: pending

- id: FE-002
  task: Create lib/api.ts
  file: frontend/src/lib/api.ts
  template: code-templates.md#1-libapits
  dependencies: [FE-001]
  status: pending

- id: FE-003
  task: Create lib/utils.ts
  file: frontend/src/lib/utils.ts
  template: code-templates.md#4-libutilsts
  dependencies: [FE-001]
  status: pending

- id: FE-004
  task: Create stores/auth.ts
  file: frontend/src/stores/auth.ts
  template: code-templates.md#2-storesauthts
  dependencies: [FE-002]
  status: pending

- id: FE-005
  task: Create stores/sites.ts
  file: frontend/src/stores/sites.ts
  dependencies: [FE-002]
  status: pending

- id: FE-006
  task: Create components/ui/button.tsx
  file: frontend/src/components/ui/button.tsx
  template: code-templates.md#3-componentsuibuttontsx
  dependencies: [FE-003]
  status: pending

- id: FE-007
  task: Create components/ui/input.tsx
  file: frontend/src/components/ui/input.tsx
  dependencies: [FE-003]
  status: pending

- id: FE-008
  task: Create components/ui/card.tsx
  file: frontend/src/components/ui/card.tsx
  dependencies: [FE-003]
  status: pending

- id: FE-009
  task: Create components/ui/badge.tsx
  file: frontend/src/components/ui/badge.tsx
  dependencies: [FE-003]
  status: pending

- id: FE-010
  task: Create components/ui/table.tsx
  file: frontend/src/components/ui/table.tsx
  dependencies: [FE-003]
  status: pending

- id: FE-011
  task: Create components/layout/header.tsx
  file: frontend/src/components/layout/header.tsx
  dependencies: [FE-006]
  status: pending

- id: FE-012
  task: Create components/layout/sidebar.tsx
  file: frontend/src/components/layout/sidebar.tsx
  dependencies: [FE-006]
  status: pending

- id: FE-013
  task: Create components/layout/shell.tsx
  file: frontend/src/components/layout/shell.tsx
  dependencies: [FE-011, FE-012]
  status: pending

- id: FE-014
  task: Update app/layout.tsx with providers
  file: frontend/src/app/layout.tsx
  dependencies: [FE-004]
  status: pending

- id: FE-015
  task: Update app/page.tsx (landing page)
  file: frontend/src/app/page.tsx
  dependencies: [FE-006]
  status: pending

- id: FE-016
  task: Create app/(auth)/login/page.tsx
  file: frontend/src/app/(auth)/login/page.tsx
  dependencies: [FE-004, FE-006, FE-007]
  status: pending

- id: FE-017
  task: Create app/(auth)/register/page.tsx
  file: frontend/src/app/(auth)/register/page.tsx
  dependencies: [FE-004, FE-006, FE-007]
  status: pending

- id: FE-018
  task: Create app/(dashboard)/layout.tsx
  file: frontend/src/app/(dashboard)/layout.tsx
  dependencies: [FE-013, FE-004]
  status: pending

- id: FE-019
  task: Create app/(dashboard)/page.tsx (dashboard home)
  file: frontend/src/app/(dashboard)/page.tsx
  dependencies: [FE-018, FE-008]
  status: pending

- id: FE-020
  task: Create app/(dashboard)/sites/page.tsx
  file: frontend/src/app/(dashboard)/sites/page.tsx
  dependencies: [FE-005, FE-010]
  status: pending

- id: FE-021
  task: Create app/(dashboard)/sites/[id]/page.tsx
  file: frontend/src/app/(dashboard)/sites/[id]/page.tsx
  dependencies: [FE-020]
  status: pending

- id: FE-022
  task: Create app/(dashboard)/sites/new/page.tsx
  file: frontend/src/app/(dashboard)/sites/new/page.tsx
  dependencies: [FE-020]
  status: pending

- id: FE-023
  task: Create app/(dashboard)/audits/page.tsx
  file: frontend/src/app/(dashboard)/audits/page.tsx
  dependencies: [FE-010]
  status: pending

- id: FE-024
  task: Create app/(dashboard)/audits/[id]/page.tsx
  file: frontend/src/app/(dashboard)/audits/[id]/page.tsx
  dependencies: [FE-023, FE-009]
  status: pending
```

---

## Phase 2: MVP2 - Keyword Research

```yaml
- id: KW-001
  task: Create DataForSEO client
  file: backend/app/integrations/dataforseo.py
  dependencies: []
  status: pending

- id: KW-002
  task: Create Keyword model
  file: backend/app/models/keyword.py
  dependencies: [DB-003]
  status: pending

- id: KW-003
  task: Create keyword schemas
  file: backend/app/schemas/keyword.py
  dependencies: [SCH-002]
  status: pending

- id: KW-004
  task: Create keyword service
  file: backend/app/services/keyword_service.py
  dependencies: [KW-001, KW-002]
  status: pending

- id: KW-005
  task: Create keywords API endpoints
  file: backend/app/api/v1/keywords.py
  dependencies: [KW-003, KW-004]
  status: pending

- id: KW-006
  task: Create keyword clustering algorithm
  file: backend/app/services/clustering.py
  dependencies: [KW-002]
  status: pending

- id: KW-007
  task: Create keyword background tasks
  file: backend/app/tasks/keyword_tasks.py
  dependencies: [KW-004, WRK-001]
  status: pending

- id: KW-008
  task: Add keyword migration
  command: alembic revision --autogenerate -m "Add keyword tables"
  dependencies: [KW-002]
  status: pending

- id: KW-FE-001
  task: Create stores/keywords.ts
  file: frontend/src/stores/keywords.ts
  dependencies: [FE-002]
  status: pending

- id: KW-FE-002
  task: Create components/keywords/keyword-table.tsx
  file: frontend/src/components/keywords/keyword-table.tsx
  dependencies: [FE-010]
  status: pending

- id: KW-FE-003
  task: Create components/keywords/cluster-card.tsx
  file: frontend/src/components/keywords/cluster-card.tsx
  dependencies: [FE-008]
  status: pending

- id: KW-FE-004
  task: Create app/(dashboard)/keywords/page.tsx
  file: frontend/src/app/(dashboard)/keywords/page.tsx
  dependencies: [KW-FE-001, KW-FE-002]
  status: pending

- id: KW-FE-005
  task: Create app/(dashboard)/keywords/clusters/[id]/page.tsx
  file: frontend/src/app/(dashboard)/keywords/clusters/[id]/page.tsx
  dependencies: [KW-FE-003]
  status: pending
```

---

## Phase 3: AI Features

```yaml
- id: AI-001
  task: Create LLM client abstraction
  file: backend/app/integrations/llm.py
  dependencies: []
  status: pending

- id: AI-002
  task: Create agents/__init__.py
  file: backend/app/agents/__init__.py
  content: ""
  dependencies: []
  status: pending

- id: AI-003
  task: Create agent configuration
  file: backend/app/agents/config.py
  dependencies: [AI-001]
  status: pending

- id: AI-004
  task: Create agent tools
  file: backend/app/agents/tools/__init__.py
  dependencies: [AI-002]
  status: pending

- id: AI-005
  task: Create crawl tools for agents
  file: backend/app/agents/tools/crawl_tools.py
  dependencies: [SVC-005]
  status: pending

- id: AI-006
  task: Create audit tools for agents
  file: backend/app/agents/tools/audit_tools.py
  dependencies: [SVC-006]
  status: pending

- id: AI-007
  task: Create keyword tools for agents
  file: backend/app/agents/tools/keyword_tools.py
  dependencies: [KW-004]
  status: pending

- id: AI-008
  task: Create content tools for agents
  file: backend/app/agents/tools/content_tools.py
  dependencies: []
  status: pending

- id: AI-009
  task: Create audit analysis workflow
  file: backend/app/agents/workflows/audit_workflow.py
  dependencies: [AI-003, AI-006]
  status: pending

- id: AI-010
  task: Create keyword research workflow
  file: backend/app/agents/workflows/keyword_workflow.py
  dependencies: [AI-003, AI-007]
  status: pending

- id: AI-011
  task: Create SEO plan workflow
  file: backend/app/agents/workflows/plan_workflow.py
  dependencies: [AI-009, AI-010]
  status: pending

- id: AI-012
  task: Create content generation workflow
  file: backend/app/agents/workflows/content_workflow.py
  dependencies: [AI-003, AI-008]
  status: pending

- id: PLAN-001
  task: Create SeoPlan and SeoTask models
  file: backend/app/models/plan.py
  dependencies: [DB-003]
  status: pending

- id: PLAN-002
  task: Create plan schemas
  file: backend/app/schemas/plan.py
  dependencies: [SCH-002]
  status: pending

- id: PLAN-003
  task: Create plan service
  file: backend/app/services/plan_service.py
  dependencies: [PLAN-001, AI-011]
  status: pending

- id: PLAN-004
  task: Create plans API endpoints
  file: backend/app/api/v1/plans.py
  dependencies: [PLAN-002, PLAN-003]
  status: pending

- id: PLAN-005
  task: Add plan migration
  command: alembic revision --autogenerate -m "Add SEO plan tables"
  dependencies: [PLAN-001]
  status: pending

- id: CNT-001
  task: Create ContentBrief and ContentDraft models
  file: backend/app/models/content.py
  dependencies: [DB-003]
  status: pending

- id: CNT-002
  task: Create content schemas
  file: backend/app/schemas/content.py
  dependencies: [SCH-002]
  status: pending

- id: CNT-003
  task: Create content service
  file: backend/app/services/content_service.py
  dependencies: [CNT-001, AI-012]
  status: pending

- id: CNT-004
  task: Create content API endpoints
  file: backend/app/api/v1/content.py
  dependencies: [CNT-002, CNT-003]
  status: pending

- id: CNT-005
  task: Add content migration
  command: alembic revision --autogenerate -m "Add content tables"
  dependencies: [CNT-001]
  status: pending

- id: AI-FE-001
  task: Create stores/plans.ts
  file: frontend/src/stores/plans.ts
  dependencies: [FE-002]
  status: pending

- id: AI-FE-002
  task: Create stores/content.ts
  file: frontend/src/stores/content.ts
  dependencies: [FE-002]
  status: pending

- id: AI-FE-003
  task: Create components/plans/plan-timeline.tsx
  file: frontend/src/components/plans/plan-timeline.tsx
  dependencies: [FE-008]
  status: pending

- id: AI-FE-004
  task: Create components/plans/task-board.tsx
  file: frontend/src/components/plans/task-board.tsx
  dependencies: [FE-008]
  status: pending

- id: AI-FE-005
  task: Create components/content/brief-card.tsx
  file: frontend/src/components/content/brief-card.tsx
  dependencies: [FE-008]
  status: pending

- id: AI-FE-006
  task: Create components/content/draft-editor.tsx
  file: frontend/src/components/content/draft-editor.tsx
  dependencies: []
  status: pending

- id: AI-FE-007
  task: Create app/(dashboard)/plans/page.tsx
  file: frontend/src/app/(dashboard)/plans/page.tsx
  dependencies: [AI-FE-001, AI-FE-003]
  status: pending

- id: AI-FE-008
  task: Create app/(dashboard)/plans/[id]/page.tsx
  file: frontend/src/app/(dashboard)/plans/[id]/page.tsx
  dependencies: [AI-FE-004]
  status: pending

- id: AI-FE-009
  task: Create app/(dashboard)/content/page.tsx
  file: frontend/src/app/(dashboard)/content/page.tsx
  dependencies: [AI-FE-002, AI-FE-005]
  status: pending

- id: AI-FE-010
  task: Create app/(dashboard)/content/briefs/[id]/page.tsx
  file: frontend/src/app/(dashboard)/content/briefs/[id]/page.tsx
  dependencies: [AI-FE-005]
  status: pending

- id: AI-FE-011
  task: Create app/(dashboard)/content/drafts/[id]/page.tsx
  file: frontend/src/app/(dashboard)/content/drafts/[id]/page.tsx
  dependencies: [AI-FE-006]
  status: pending
```

---

## Phase 4: Documentation

```yaml
- id: DOC-001
  task: Initialize Docusaurus in /docs
  command: |
    npx create-docusaurus@latest docs classic --typescript
  dependencies: []
  status: pending

- id: DOC-002
  task: Configure docusaurus.config.js
  file: docs/docusaurus.config.js
  dependencies: [DOC-001]
  status: pending

- id: DOC-003
  task: Configure sidebars.js
  file: docs/sidebars.js
  dependencies: [DOC-001]
  status: pending

- id: DOC-004
  task: Write docs/intro.md
  file: docs/docs/intro.md
  dependencies: [DOC-001]
  status: pending

- id: DOC-005
  task: Write getting-started/installation.md
  file: docs/docs/getting-started/installation.md
  dependencies: [DOC-004]
  status: pending

- id: DOC-006
  task: Write getting-started/configuration.md
  file: docs/docs/getting-started/configuration.md
  dependencies: [DOC-005]
  status: pending

- id: DOC-007
  task: Write getting-started/quick-start.md
  file: docs/docs/getting-started/quick-start.md
  dependencies: [DOC-006]
  status: pending

- id: DOC-008
  task: Write architecture/overview.md
  file: docs/docs/architecture/overview.md
  dependencies: [DOC-004]
  status: pending

- id: DOC-009
  task: Write architecture/backend.md
  file: docs/docs/architecture/backend.md
  dependencies: [DOC-008]
  status: pending

- id: DOC-010
  task: Write architecture/frontend.md
  file: docs/docs/architecture/frontend.md
  dependencies: [DOC-008]
  status: pending

- id: DOC-011
  task: Write architecture/database.md
  file: docs/docs/architecture/database.md
  dependencies: [DOC-008]
  status: pending

- id: DOC-012
  task: Write architecture/agents.md
  file: docs/docs/architecture/agents.md
  dependencies: [DOC-008]
  status: pending

- id: DOC-013
  task: Write api/overview.md
  file: docs/docs/api/overview.md
  dependencies: [DOC-004]
  status: pending

- id: DOC-014
  task: Write api/authentication.md
  file: docs/docs/api/authentication.md
  dependencies: [DOC-013]
  status: pending

- id: DOC-015
  task: Write api/sites.md
  file: docs/docs/api/sites.md
  dependencies: [DOC-013]
  status: pending

- id: DOC-016
  task: Write api/audits.md
  file: docs/docs/api/audits.md
  dependencies: [DOC-013]
  status: pending

- id: DOC-017
  task: Write api/keywords.md
  file: docs/docs/api/keywords.md
  dependencies: [DOC-013]
  status: pending

- id: DOC-018
  task: Write api/plans.md
  file: docs/docs/api/plans.md
  dependencies: [DOC-013]
  status: pending

- id: DOC-019
  task: Write api/content.md
  file: docs/docs/api/content.md
  dependencies: [DOC-013]
  status: pending

- id: DOC-020
  task: Write guides/running-audit.md
  file: docs/docs/guides/running-audit.md
  dependencies: [DOC-016]
  status: pending

- id: DOC-021
  task: Write guides/keyword-research.md
  file: docs/docs/guides/keyword-research.md
  dependencies: [DOC-017]
  status: pending

- id: DOC-022
  task: Write guides/creating-seo-plan.md
  file: docs/docs/guides/creating-seo-plan.md
  dependencies: [DOC-018]
  status: pending

- id: DOC-023
  task: Write guides/generating-content.md
  file: docs/docs/guides/generating-content.md
  dependencies: [DOC-019]
  status: pending

- id: DOC-024
  task: Write integrations/dataforseo.md
  file: docs/docs/integrations/dataforseo.md
  dependencies: [DOC-008]
  status: pending

- id: DOC-025
  task: Write integrations/llm-providers.md
  file: docs/docs/integrations/llm-providers.md
  dependencies: [DOC-008]
  status: pending

- id: DOC-026
  task: Write deployment/docker.md
  file: docs/docs/deployment/docker.md
  dependencies: [DOC-005]
  status: pending

- id: DOC-027
  task: Write deployment/production.md
  file: docs/docs/deployment/production.md
  dependencies: [DOC-026]
  status: pending
```

---

## Phase 5: Final Push

```yaml
- id: FINAL-001
  task: Update root README.md
  file: README.md
  dependencies: []
  status: pending

- id: FINAL-002
  task: Create CONTRIBUTING.md
  file: CONTRIBUTING.md
  dependencies: []
  status: pending

- id: FINAL-003
  task: Create LICENSE
  file: LICENSE
  dependencies: []
  status: pending

- id: FINAL-004
  task: Create .github/workflows/ci.yml
  file: .github/workflows/ci.yml
  dependencies: []
  status: pending

- id: FINAL-005
  task: Create .github/workflows/deploy-docs.yml
  file: .github/workflows/deploy-docs.yml
  dependencies: [DOC-001]
  status: pending

- id: FINAL-006
  task: Verify all services start correctly
  command: docker-compose up -d && docker-compose ps
  dependencies: [API-001, FE-024]
  status: pending

- id: FINAL-007
  task: Run backend tests
  command: cd backend && pytest
  dependencies: [API-001]
  status: pending

- id: FINAL-008
  task: Run frontend build
  command: cd frontend && npm run build
  dependencies: [AI-FE-011]
  status: pending

- id: FINAL-009
  task: Build documentation
  command: cd docs && npm run build
  dependencies: [DOC-027]
  status: pending

- id: FINAL-010
  task: Commit and push to GitHub
  command: |
    git add .
    git commit -m "feat: Complete SEOman MVP with AI features and documentation"
    git push -u origin main
  dependencies: [FINAL-006, FINAL-007, FINAL-008, FINAL-009]
  status: pending
```

---

## Summary Statistics

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 0: GitHub | 3 | 0.5 hours |
| Phase 1: MVP1 - Backend | 40 | 4-5 days |
| Phase 1: MVP1 - Frontend | 24 | 3-4 days |
| Phase 2: Keywords | 13 | 2-3 days |
| Phase 3: AI Features | 28 | 4-5 days |
| Phase 4: Documentation | 27 | 2-3 days |
| Phase 5: Final | 10 | 0.5-1 day |
| **Total** | **145 tasks** | **16-21 days** |

---

## Execution Order

The tasks should be executed in this order:

1. **GH-001 to GH-003** - GitHub setup
2. **DB-001 to DB-011** - Database layer
3. **SEC-001 to SEC-004** - Security
4. **SCH-001 to SCH-007** - Schemas
5. **INT-001 to INT-003** - Integrations
6. **SVC-001 to SVC-006** - Services
7. **API-001 to API-016** - API endpoints
8. **WRK-001 to WRK-004** - Workers
9. **FE-001 to FE-024** - Frontend MVP1
10. **KW-001 to KW-FE-005** - Keyword research
11. **AI-001 to AI-FE-011** - AI features
12. **DOC-001 to DOC-027** - Documentation
13. **FINAL-001 to FINAL-010** - Final push

---

## Notes for Implementation Agent

1. **Use the code templates** from `code-templates.md` - they are ready to use
2. **Run migrations after model changes** - Don't forget `alembic upgrade head`
3. **Test each endpoint** before moving on
4. **Commit frequently** with meaningful messages
5. **Update the router** after adding new endpoints
6. **Check Docker health** periodically
