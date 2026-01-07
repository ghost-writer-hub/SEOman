# ✅ Startup Scripts Created Successfully!

## Scripts Created

All three scripts are located in `/root/docker/SEOman/` and have executable permissions (755):

### 1. `start.sh` (9.4K)
**Main startup script with admin account creation**

**Features:**
- Starts all Docker services
- Automatically creates admin account if it doesn't exist
- Supports `--rebuild` flag for rebuilding without cache
- Supports `--skip-start` flag for admin-only creation
- Color-coded output for easy reading
- Error handling and retry logic
- Displays access URLs and credentials

**Admin Account Created:**
- Email: `cgp@novumbc.com`
- Password: `morrosco`
- Name: SEOman Admin
- Role: Administrator

**Usage:**
```bash
# Normal start
./start.sh

# Rebuild containers (no cache)
./start.sh --rebuild

# Only create admin (skip starting services)
./start.sh --skip-start

# Show help
./start.sh --help
```

### 2. `ctl` (1.7K)
**Quick control script for common operations**

**Features:**
- Fast access to common Docker commands
- Simplified syntax
- Service-specific operations
- Database and Redis access

**Usage:**
```bash
# Start services
./ctl start

# Rebuild (no cache)
./ctl rebuild

# Stop services
./ctl stop

# Restart services
./ctl restart

# View logs
./ctl logs
./ctl logs backend

# Check status
./ctl status

# Access database shell
./ctl db

# Access Redis CLI
./ctl redis

# Execute command in container
./ctl shell backend bash

# Clean everything (removes all data!)
./ctl clean
```

### 3. `setup.sh` (2.5K)
**Initial setup wizard (from previous step)**

**Features:**
- Checks Docker/Docker Compose installation
- Copies `.env.example` to `.env`
- Creates directory structure
- Starts services
- Provides setup guidance

**Usage:**
```bash
./setup.sh
```

## Quick Start

### First Time Setup

```bash
cd /root/docker/SEOman

# Run setup wizard (creates .env)
./setup.sh

# Edit environment variables
nano .env

# Start services and create admin
./start.sh
```

### Daily Operations

```bash
# Start everything
./ctl start

# View logs
./ctl logs

# Check status
./ctl status

# Stop when done
./ctl stop
```

### After Code Changes

```bash
# Rebuild without cache
./ctl rebuild

# Or
./start.sh --rebuild
```

## What `start.sh` Does

1. **Validates** `.env` file exists
2. **Starts/rebuilds** Docker services
3. **Waits** for PostgreSQL to be ready (up to 30 retries)
4. **Waits** for Casdoor to initialize (up to 30 retries)
5. **Checks** if admin user exists in database
6. **Creates** admin user if needed:
   - First tries Casdoor API (if available)
   - Falls back to direct database insertion
7. **Displays** access URLs and credentials

## Admin Account Creation Methods

### Method 1: Casdoor API (Preferred)

Script attempts to create user via Casdoor API:
1. Gets JWT token using default admin (admin/123)
2. Calls Casdoor's `/api/add-user` endpoint
3. Sets user as administrator

### Method 2: Database Insert (Fallback)

If API fails, script inserts directly into PostgreSQL:
1. Gets organization ID (seoman)
2. Gets application ID (seoman-app)
3. Generates UUIDs for user and avatar
4. Inserts user record with hashed password
5. Sets `is_admin = true`
6. Creates permission rule for organization access

Both methods create the same admin account with full permissions.

## Script Comparison

| Feature | start.sh | ctl | setup.sh |
|---------|-----------|------|----------|
| Start services | ✅ | ✅ | ✅ |
| Create admin | ✅ | ❌ | ❌ |
| Rebuild | ✅ | ✅ | ❌ |
| Stop services | ❌ | ✅ | ❌ |
| View logs | ❌ | ✅ | ❌ |
| Database access | ❌ | ✅ | ❌ |
| Redis access | ❌ | ✅ | ❌ |
| Environment setup | ❌ | ❌ | ✅ |
| Color output | ✅ | ❌ | ✅ |
| Progress indicators | ✅ | ❌ | ✅ |

## Admin Credentials

⚠️ **IMPORTANT**: These are hardcoded in the script. Change password after first login!

```
Email:    cgp@novumbc.com
Password: morrosco
Role:     Administrator
```

## Access URLs (After Startup)

| Service | URL | Login |
|---------|-----|-------|
| Frontend | http://localhost:3011 | cgp@novumbc.com / morrosco |
| Backend API | http://localhost:8000 | API key or JWT |
| API Docs | http://localhost:8000/docs | - |
| Casdoor Web | http://localhost:7001 | admin/123 (default) |
| MinIO Console | http://localhost:9001 | seoman_admin / seoman_minio_password |

## Troubleshooting

### Script Won't Run

```bash
# Check permissions
ls -l start.sh ctl setup.sh

# Make executable if needed
chmod +x start.sh ctl setup.sh
```

### Admin Not Created

```bash
# Try again with skip-start
./start.sh --skip-start

# Or create manually via Casdoor Web:
# 1. Visit http://localhost:7001
# 2. Login with admin/123
# 3. Go to Users → Add User
# 4. Fill in: SEOman Admin, cgp@novumbc.com, morrosco
# 5. Set as administrator
```

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Rebuild without cache
./ctl rebuild

# Clean and start fresh
./ctl clean
./start.sh --rebuild
```

### Database Connection Issues

```bash
# Wait for database
docker-compose exec postgres pg_isready -U seoman

# Check if running
docker-compose ps postgres

# View logs
docker-compose logs postgres
```

## Tips

1. **Use `ctl` for daily operations** - Faster and simpler
2. **Use `start.sh` for initial startup** - Creates admin automatically
3. **Use `--rebuild` sparingly** - Takes time to rebuild all containers
4. **Change admin password** after first login via Casdoor Web UI
5. **Check logs** if something fails - `./ctl logs` or `docker-compose logs`
6. **Use `./ctl db`** to directly access PostgreSQL for debugging

## Common Workflows

### Development Cycle

```bash
# Start day
./ctl start

# Make code changes...

# Restart affected service
docker-compose restart backend

# View logs
./ctl logs backend

# End of day
./ctl stop
```

### Testing Changes

```bash
# Rebuild backend
docker-compose build --no-cache backend

# Restart backend
docker-compose up -d backend

# Check logs
./ctl logs backend
```

### Fresh Start

```bash
# Clean everything
./ctl clean

# Start fresh
./start.sh --rebuild
```

## Documentation

- `STARTUP_GUIDE.md` - Detailed startup script guide
- `QUICK_START.md` - Quick start instructions
- `README.md` - Full documentation
- `NGINX_CONFIG.md` - Nginx Proxy Manager setup

## Summary

You now have three powerful scripts:

1. **`start.sh`** - One-command startup with admin creation
2. **`ctl`** - Quick control for all operations
3. **`setup.sh`** - Initial environment setup

All scripts are executable and ready to use!

## Next Steps

```bash
cd /root/docker/SEOman

# If first time, run setup
./setup.sh

# Or just start with admin creation
./start.sh

# Access services at URLs shown above
```

---

**Created**: All scripts executable with proper permissions (755)
**Location**: `/root/docker/SEOman/`
**Admin**: cgp@novumbc.com / morrosco
**Ready to use**: Yes! ✅
