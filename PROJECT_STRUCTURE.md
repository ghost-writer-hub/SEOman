seoman/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Configuration management
│   │   ├── database.py            # Database connection
│   │   ├── models/                # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── site.py
│   │   │   ├── crawl.py
│   │   │   ├── audit.py
│   │   │   ├── keyword.py
│   │   │   ├── content.py
│   │   │   └── plan.py
│   │   ├── schemas/               # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── site.py
│   │   │   ├── crawl.py
│   │   │   └── audit.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py            # Dependencies (auth, db, etc.)
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── tenants.py
│   │   │   │   ├── sites.py
│   │   │   │   ├── crawls.py
│   │   │   │   ├── audits.py
│   │   │   │   ├── keywords.py
│   │   │   │   ├── plans.py
│   │   │   │   └── content.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py        # JWT, password hashing
│   │   │   ├── casdoor.py         # Casdoor integration
│   │   │   └── rbac.py            # Role-based access control
│   │   ├── integrations/
│   │   │   ├── __init__.py
│   │   │   ├── deepcrawl.py
│   │   │   ├── dataforseo.py
│   │   │   ├── llm.py
│   │   │   └── storage.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── workflow.py        # LangGraph workflows
│   │   │   ├── tools.py           # Agent tools
│   │   │   └── chains.py          # LangChain chains
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── audit_service.py
│   │   │   ├── keyword_service.py
│   │   │   ├── content_service.py
│   │   │   └── crawl_service.py
│   │   └── worker.py              # Celery worker
│   ├── database/
│   │   └── init/
│   │       └── 01-init.sql         # Initial database setup
│   ├── alembic/
│   │   └── ...                    # Database migrations
│   ├── tests/
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── (dashboard)/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── page.tsx
│   │   │   │   ├── sites/
│   │   │   │   ├── audits/
│   │   │   │   ├── keywords/
│   │   │   │   └── content/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── auth/
│   │   │   └── dashboard/
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── casdoor.ts
│   │   ├── types/
│   │   └── styles/
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
