# SEOman - Multi-tenant SEO Platform

A comprehensive multi-tenant SEO platform with AI-powered analysis, crawling, keyword research, and content generation.

## Architecture

### Services

- **Frontend**: Next.js 14 (App Router) + TypeScript + TailwindCSS
- **Backend**: FastAPI + Python 3.11 + SQLAlchemy + Celery
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Object Storage**: MinIO (S3-compatible)
- **Authentication**: Casdoor (OAuth2, RBAC)
- **Agent Framework**: LangGraph (LLM workflows)
- **Worker**: Celery for async job processing
- **Scheduler**: Celery Beat for recurring tasks

### Integrations

- **Deepcrawl**: Website crawling (self-hosted)
- **DataForSEO**: Keyword research and SERP data
- **LM Studio**: Local LLM inference
- **OpenAI/Anthropic**: Cloud LLM support (optional)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- LM Studio running with a local model (or configure cloud LLM)
- Google OAuth credentials (for Casdoor)

### Setup

1. Clone and configure:
```bash
# Copy environment variables
cp .env.example .env

# Edit .env with your configuration
nano .env
```

2. Update key values in `.env`:
```bash
# Update these with your actual values
JWT_SECRET=your-secure-random-string-here
CASDOOR_JWT_SECRET=another-secure-random-string
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
DATAFORSEO_API_LOGIN=your-dataforseo-login
DATAFORSEO_API_PASSWORD=your-dataforseo-password
```

3. Start all services:
```bash
docker-compose up -d
```

4. Initialize Casdoor:
```bash
# Access Casdoor web interface
open http://localhost:7001

# Default admin credentials:
# Username: admin
# Password: 123
```

5. Configure Casdoor:
- Login to Casdoor
- Create organization: "seoman"
- Create application: "seoman-app"
- Add Google OAuth provider
- Create clients for backend and frontend

6. Access the application:
- Frontend: http://localhost:3011
- Backend API: http://localhost:8000 (docs: /docs)
- Casdoor Web: http://localhost:7001
- MinIO Console: http://localhost:9001

## Development

### Backend Development

```bash
# Run backend with hot reload (included in docker-compose)
docker-compose logs -f backend

# Run backend manually (outside docker)
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
# Run frontend with hot reload (included in docker-compose)
docker-compose logs -f frontend

# Run frontend manually (outside docker)
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
# Generate migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migration
docker-compose exec backend alembic upgrade head
```

## Service Ports

| Service | Internal Port | External Port |
|---------|---------------|---------------|
| Frontend | 3000 | 3011 |
| Backend API | 8000 | 8000 |
| Casdoor Server | 8000 | 8000 |
| Casdoor Web | 8001 | 7001 |
| PostgreSQL | 5432 | 5433 |
| Redis | 6379 | 6380 |
| MinIO API | 9000 | 9000 |
| MinIO Console | 9001 | 9001 |

## Nginx Proxy Manager Configuration

Add the following proxy hosts in your Nginx Proxy Manager:

### Frontend
- **Domain**: `seoman.yourdomain.com` (or your domain)
- **Scheme**: http
- **Forward Hostname/IP**: `seoman-frontend`
- **Forward Port**: `3000`

### Backend API
- **Domain**: `api.seoman.yourdomain.com` (or your domain)
- **Scheme**: http
- **Forward Hostname/IP**: `seoman-backend`
- **Forward Port**: `8000`

### Casdoor Web (Optional)
- **Domain**: `auth.seoman.yourdomain.com` (or your domain)
- **Scheme**: http
- **Forward Hostname/IP**: `seoman-casdoor-web`
- **Forward Port**: `8001`

## Monitoring & Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f frontend

# Check service health
docker-compose ps
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Production Deployment

1. **Update environment variables**:
   - Change `ENVIRONMENT=development` to `ENVIRONMENT=production`
   - Update all passwords and secrets
   - Set `LOG_LEVEL=INFO` or `LOG_LEVEL=WARNING`

2. **Use production builds**:
   - Frontend uses production build (already configured)
   - Backend uses production dependencies

3. **Configure external S3** (optional):
   ```bash
   MINIO_ENDPOINT=s3.amazonaws.com
   MINIO_USE_SSL=true
   MINIO_ROOT_USER=your-aws-access-key
   MINIO_ROOT_PASSWORD=your-aws-secret-key
   ```

4. **Set up SSL**:
   - Use Nginx Proxy Manager to configure SSL certificates
   - Update CORS_ORIGINS with https URLs

5. **Configure monitoring**:
   - Set `SENTRY_DSN` for error tracking
   - Set up log aggregation

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs <service-name>

# Rebuild containers
docker-compose up -d --build
```

### Database connection issues
```bash
# Check if database is running
docker-compose ps postgres

# Access database
docker-compose exec postgres psql -U seoman -d seoman
```

### Redis connection issues
```bash
# Check Redis
docker-compose exec redis redis-cli -a seoman_dev_password ping
```

### LLM not working
```bash
# Verify LM Studio is accessible
curl http://localhost:1234/v1/models

# Check backend logs for LLM errors
docker-compose logs backend | grep LLM
```

## Project Structure

See `PROJECT_STRUCTURE.md` for detailed file organization.

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.
