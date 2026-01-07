# SEOman - Quick Reference

## Environment Variables (Key Ones)

```bash
# Authentication (CHANGE THESE IN PRODUCTION!)
JWT_SECRET=your-random-secret-here
CASDOOR_JWT_SECRET=another-random-secret-here

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# LLM Configuration
LLM_PROVIDER=local
LLM_BASE_URL=http://host.docker.internal:1234/v1
LLM_MODEL=llama-3-8b-instruct

# Database
POSTGRES_USER=seoman
POSTGRES_PASSWORD=change-me
POSTGRES_DB=seoman

# External APIs
DATAFORSEO_API_LOGIN=your-login
DATAFORSEO_API_PASSWORD=your-password
```

## Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f
docker-compose logs -f backend  # specific service

# Rebuild services
docker-compose up -d --build

# Access database
docker-compose exec postgres psql -U seoman -d seoman

# Access Redis
docker-compose exec redis redis-cli -a seoman_dev_password

# Run migrations
docker-compose exec backend alembic upgrade head

# Restart specific service
docker-compose restart backend
```

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3011 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Casdoor Web | http://localhost:7001 |
| MinIO Console | http://localhost:9001 |

## Database Connection

```
Host: localhost (or postgres container name)
Port: 5433
Database: seoman
User: seoman
Password: seoman_dev_password
```

## Redis Connection

```
Host: localhost (or redis container name)
Port: 6380
Password: seoman_dev_password
```

## MinIO Connection

```
API Endpoint: http://localhost:9000
Console: http://localhost:9001
Access Key: seoman_admin
Secret: seoman_minio_password
```

## Directory Structure

```
/root/docker/SEOman/
├── backend/                 # Python/FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── agents/         # LangGraph workflows
│   │   └── integrations/   # External API clients
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── src/app/           # App router pages
│   ├── src/components/    # React components
│   └── package.json
├── docker-compose.yml      # Docker services
├── .env                   # Environment variables
└── README.md              # Full documentation
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs <service-name>
docker-compose up -d --build <service-name>
```

### Database connection failed
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Frontend can't connect to backend
1. Check CORS_ORIGINS in .env
2. Check backend is running: `docker-compose ps backend`
3. Check backend logs: `docker-compose logs backend`

### LLM not working
1. Verify LM Studio is running: `curl http://localhost:1234/v1/models`
2. Check LLM_BASE_URL in .env (should be `http://host.docker.internal:1234/v1`)
3. Check backend logs for LLM errors

## Getting Help

- Full documentation: `README.md`
- Nginx config: `NGINX_CONFIG.md`
- Project structure: `PROJECT_STRUCTURE.md`
- Business requirements: `businessRequirements.md`
- Technical spec: `specification.json`
