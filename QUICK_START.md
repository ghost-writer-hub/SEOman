# SEOman Quick Start Guide

## 🚀 Quick Start

### Method 1: Using the Startup Script (Recommended)

```bash
cd /root/docker/SEOman

# First time setup (creates admin account)
./start.sh

# Rebuild containers without cache
./start.sh --rebuild

# Create admin only (skip starting services)
./start.sh --skip-start
```

### Method 2: Using the Control Script

```bash
cd /root/docker/SEOman

# Start services
./ctl start

# Rebuild (no cache)
./ctl rebuild

# Stop services
./ctl stop

# Restart services
./ctl restart

# View all logs
./ctl logs

# View specific service logs
./ctl logs backend
./ctl logs frontend

# Check status
./ctl status

# Access database shell
./ctl db

# Access Redis CLI
./ctl redis

# Execute command in container
./ctl shell backend bash
./ctl shell postgres psql -U seoman -d seoman

# Clean everything (removes all data!)
./ctl clean
```

### Method 3: Using Docker Compose Directly

```bash
# Start services
docker-compose up -d

# Rebuild without cache
docker-compose build --no-cache
docker-compose up -d --force-recreate

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 👤 Admin Account

The startup script automatically creates an admin account:

- **Email**: `cgp@novumbc.com`
- **Password**: `morrosco`
- **Role**: Administrator

You can use these credentials to:
- Login to Casdoor: http://localhost:7001
- Login to the SEOman application (once frontend auth is implemented)

⚠️ **Important**: Change the password after first login!

## 🌐 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3011 | Admin account |
| Backend API | http://localhost:8000 | API docs at /docs |
| API Documentation | http://localhost:8000/docs | - |
| Casdoor Web | http://localhost:7001 | admin/123 (default) |
| MinIO Console | http://localhost:9001 | seoman_admin / seoman_minio_password |

## 📋 Startup Script Options

```bash
./start.sh [OPTIONS]

Options:
  --rebuild       Rebuild containers without cache
  --skip-start    Skip starting containers (only create admin)
  -h, --help     Show help message
```

## 🔧 Common Workflows

### Initial Setup

```bash
cd /root/docker/SEOman

# 1. Copy environment file
cp .env.example .env

# 2. Edit environment variables
nano .env

# 3. Start services and create admin
./start.sh

# 4. Access Casdoor to configure OAuth
open http://localhost:7001
```

### Development Workflow

```bash
# Start everything
./ctl start

# View backend logs
./ctl logs backend

# Restart backend after code changes
./ctl restart backend

# Access database to check data
./ctl db
```

### Rebuild After Changes

```bash
# Rebuild all containers (no cache)
./ctl rebuild

# Or rebuild specific service
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Troubleshooting

```bash
# Check if services are running
./ctl status

# View all logs
./ctl logs

# Restart specific service
./ctl restart backend

# Check database connectivity
./ctl db

# Check Redis connectivity
./ctl redis ping

# Clean and start fresh (WARNING: deletes data!)
./ctl clean
./start.sh
```

## 📊 Service Status Check

```bash
# Quick status overview
./ctl status

# Detailed status
docker-compose ps

# Check health of specific service
docker-compose ps postgres
docker-compose ps backend
```

## 🔑 Database Access

```bash
# Using control script
./ctl db

# Or directly
docker-compose exec postgres psql -U seoman -d seoman

# Casdoor database
docker-compose exec postgres psql -U seoman -d casdoor

# List databases
docker-compose exec postgres psql -U seoman -d seoman -c "\l"

# List tables
docker-compose exec postgres psql -U seoman -d seoman -c "\dt"
```

## 🔑 Redis Access

```bash
# Using control script
./ctl redis

# Or directly
docker-compose exec redis redis-cli -a seoman_dev_password

# Check connection
docker-compose exec redis redis-cli -a seoman_dev_password ping

# Monitor Redis
docker-compose exec redis redis-cli -a seoman_dev_password monitor
```

## 📝 Logs

```bash
# All logs (follow)
./ctl logs

# Specific service (follow)
./ctl logs backend
./ctl logs frontend
./ctl logs worker

# Last 100 lines (no follow)
docker-compose logs --tail=100 backend

# Export logs to file
docker-compose logs > seoman.log
```

## 🧹 Cleanup

```bash
# Stop services (keeps data)
./ctl stop

# Stop and remove volumes (WARNING: deletes data!)
docker-compose down -v

# Clean everything (containers, volumes, images, networks)
./ctl clean

# Clean unused Docker resources
docker system prune -a

# Remove specific container
docker-compose rm -f backend
```

## 🔄 Updating

```bash
# Pull latest code (if using git)
git pull

# Rebuild and restart
./ctl rebuild

# Or just restart services
./ctl restart
```

## 🐛 Debugging

```bash
# Check container logs for errors
docker-compose logs backend | grep ERROR

# Enter container shell
./ctl shell backend bash

# Check environment variables in container
docker-compose exec backend env | grep -E "POSTGRES|REDIS|LLM"

# Test database connection
docker-compose exec backend python -c "from app.database import engine; print('DB OK')"

# Test Redis connection
docker-compose exec backend python -c "import redis; r = redis.from_url('redis://:seoman_dev_password@redis:6379/0'); print(r.ping())"

# Test MinIO connection
curl http://localhost:9000/minio/health/live
```

## 📱 Nginx Proxy Manager Configuration

After starting services, configure your Nginx Proxy Manager:

1. **Frontend Proxy**
   - Domain: `seoman.yourdomain.com`
   - Forward to: `seoman-frontend:3000`

2. **Backend API Proxy**
   - Domain: `api.seoman.yourdomain.com`
   - Forward to: `seoman-backend:8000`

See `NGINX_CONFIG.md` for detailed instructions.

## ❓ Getting Help

```bash
# Startup script help
./start.sh --help

# Control script help
./ctl

# Makefile commands
make help

# Docker compose help
docker-compose --help
```

## ⚡ Quick Reference

```bash
./ctl start          # Start services
./ctl rebuild         # Rebuild without cache
./ctl stop           # Stop services
./ctl logs           # View logs
./ctl status         # Check status
./ctl db             # Database shell
./ctl redis          # Redis CLI
./ctl clean          # Remove everything

# Admin Credentials:
# Email:    cgp@novumbc.com
# Password: morrosco
```

---

## 📚 Additional Documentation

- `README.md` - Full documentation
- `NGINX_CONFIG.md` - Nginx Proxy Manager setup
- `BUILD_SUMMARY.md` - Build details
- `QUICK_REFERENCE.md` - Quick reference
- `PROJECT_STRUCTURE.md` - File organization
