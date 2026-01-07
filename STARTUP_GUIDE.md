# Startup Script Documentation

## Overview

Three scripts are provided for easy management of the SEOman docker environment:

1. **`start.sh`** - Main startup script with admin account creation
2. **`ctl`** - Quick control script for common operations
3. **`setup.sh`** - Initial setup wizard (environment configuration)

## start.sh

Main startup script that:
- Starts all Docker services
- Creates admin account automatically
- Handles rebuilds without cache
- Provides detailed status information

### Usage

```bash
./start.sh [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `--rebuild` | Rebuild all containers without cache |
| `--skip-start` | Skip starting containers (only create admin user) |
| `-h, --help` | Show help message |

### Examples

```bash
# Normal start
./start.sh

# Rebuild containers (no cache)
./start.sh --rebuild

# Only create admin account (services already running)
./start.sh --skip-start
```

### What It Does

1. Validates `.env` file exists
2. Starts/rebuilds Docker services
3. Waits for PostgreSQL to be ready
4. Waits for Casdoor to initialize
5. Checks if admin user exists
6. Creates admin user if needed (via API or database)
7. Displays access URLs and credentials

### Admin Account Created

- **Email**: `cgp@novumbc.com`
- **Password**: `morrosco`
- **Name**: SEOman Admin
- **Role**: Administrator

The script attempts two methods to create the admin:
1. **Casdoor API** (preferred, if available)
2. **Direct database insertion** (fallback)

Both methods set the user as an administrator in the Casdoor system.

## ctl

Quick control script for common Docker operations.

### Usage

```bash
./ctl COMMAND [args]
```

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `start` / `up` | Start services and create admin | `./ctl start` |
| `rebuild` | Rebuild without cache | `./ctl rebuild` |
| `stop` / `down` | Stop all services | `./ctl stop` |
| `restart` | Restart all services | `./ctl restart` |
| `logs` | View logs (optional service) | `./ctl logs backend` |
| `status` / `ps` | Show service status | `./ctl status` |
| `shell` / `sh` | Execute in container | `./ctl shell backend bash` |
| `db` | Access database shell | `./ctl db` |
| `redis` | Access Redis CLI | `./ctl redis` |
| `clean` | Remove everything | `./ctl clean` |

### Examples

```bash
# Quick start
./ctl start

# View all logs
./ctl logs

# View backend logs only
./ctl logs backend

# Check status
./ctl status

# Access database
./ctl db

# Access Redis
./ctl redis

# Restart backend
docker-compose restart backend

# Clean everything (WARNING: deletes data!)
./ctl clean
```

## setup.sh

Initial setup wizard that:
- Checks for Docker/Docker Compose
- Creates `.env` from `.env.example`
- Creates necessary directories
- Starts services
- Provides guidance for configuration

### Usage

```bash
./setup.sh
```

### What It Does

1. Verifies Docker and Docker Compose are installed
2. Copies `.env.example` to `.env`
3. Prompts user to configure environment variables
4. Creates required directory structure
5. Starts all Docker services
6. Displays setup instructions

Use this only for the **first time setup**. For normal operations, use `start.sh` or `ctl`.

## Workflow Examples

### First Time Setup

```bash
cd /root/docker/SEOman

# 1. Run setup wizard
./setup.sh

# 2. Edit .env file
nano .env

# 3. Start services with admin creation
./start.sh
```

### Daily Development

```bash
# Start everything
./ctl start

# Or
./start.sh

# View logs
./ctl logs

# Stop when done
./ctl stop
```

### After Code Changes

```bash
# Rebuild and restart
./ctl rebuild

# Or
./start.sh --rebuild
```

### Just Create Admin (Services Already Running)

```bash
./start.sh --skip-start
```

## Script Comparison

| Script | Best For | Features |
|--------|----------|----------|
| `start.sh` | Starting services + admin creation | Automatic admin creation, status display |
| `ctl` | Daily operations | Quick commands, shell access |
| `setup.sh` | Initial setup only | Environment setup wizard |

## Admin Account Management

### Checking if Admin Exists

```bash
# Via database
docker-compose exec postgres psql -U seoman -d casdoor \
  -c "SELECT name, email, is_admin FROM user WHERE email = 'cgp@novumbc.com';"
```

### Manually Creating Admin

If the script fails, you can manually create the admin via Casdoor Web UI:

1. Visit http://localhost:7001
2. Login with `admin/123`
3. Go to "Users"
4. Click "Add User"
5. Fill in:
   - Name: SEOman Admin
   - Email: cgp@novumbc.com
   - Password: morrosco
   - Set as administrator: Yes
6. Click "Save"

### Resetting Admin Password

```bash
# Via Casdoor Web UI (recommended)
# Login as admin and reset user password

# Or via database (advanced)
docker-compose exec postgres psql -U seoman -d casdoor
UPDATE user SET password = '<new-hash>' WHERE email = 'cgp@novumbc.com';
```

## Troubleshooting

### Script Permissions Error

```bash
chmod +x /root/docker/SEOman/start.sh
chmod +x /root/docker/SEOman/ctl
chmod +x /root/docker/SEOman/setup.sh
```

### .env File Not Found

```bash
cp .env.example .env
nano .env  # Edit configuration
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

### Admin Not Created

```bash
# Try again with skip-start
./start.sh --skip-start

# Or create manually via Casdoor Web UI
# Visit http://localhost:7001 and create user manually
```

### Database Connection Issues

```bash
# Wait for database to be ready
docker-compose exec postgres pg_isready -U seoman

# Check if service is running
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres
```

## Tips

1. **Use `ctl` for daily operations** - It's faster and simpler
2. **Use `start.sh` for initial startup** - It creates the admin account
3. **Use `--rebuild` sparingly** - It takes time to rebuild all containers
4. **Check logs if something fails** - Use `./ctl logs` or `docker-compose logs`
5. **Save your admin credentials** - Don't lose the password
6. **Change the default password** - After first login, change from "morrosco"

## Next Steps

After running the startup script:

1. **Access Casdoor**: http://localhost:7001
2. **Configure OAuth**: Set up Google OAuth in Casdoor
3. **Access Application**: http://localhost:3011
4. **Check API Docs**: http://localhost:8000/docs
5. **Configure Nginx Proxy Manager**: See `NGINX_CONFIG.md`

## See Also

- `QUICK_START.md` - Quick start guide
- `README.md` - Full documentation
- `QUICK_REFERENCE.md` - Quick reference
- `NGINX_CONFIG.md` - Nginx Proxy Manager setup
