#!/bin/bash

# SEOman Startup Script
# Creates admin account and starts/rebuilds services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
REBUILD=false
SKIP_START=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild)
            REBUILD=true
            shift
            ;;
        --skip-start)
            SKIP_START=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --rebuild       Rebuild containers without cache"
            echo "  --skip-start    Skip starting containers (only create admin)"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Configuration
ADMIN_EMAIL="cgp@novumbc.com"
ADMIN_PASSWORD="morrosco"
ADMIN_NAME="SEOman Admin"
CASDOOR_CONTAINER="seoman-casdoor-server"
DB_CONTAINER="seoman-postgres"
DB_USER="seoman"
DB_PASS="seoman_dev_password"
DB_NAME="casdoor"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T postgres pg_isready -U "$DB_USER" > /dev/null 2>&1; then
            log_success "PostgreSQL is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    log_error "PostgreSQL did not become ready in time"
    return 1
}

wait_for_casdoor() {
    log_info "Waiting for Casdoor to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T casdoor-server curl -f -s http://localhost:8080/api/get-application?name=seoman-app > /dev/null 2>&1; then
            log_success "Casdoor is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    log_warning "Casdoor API not fully ready, will proceed with database method"
    return 0
}

check_admin_exists() {
    log_info "Checking if admin user exists..."
    
    # Check if user exists in database
    local user_exists=$(docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT EXISTS(SELECT 1 FROM user WHERE name = '$ADMIN_EMAIL');" 2>/dev/null || echo "f")
    
    if [ "$user_exists" = "t" ]; then
        log_success "Admin user already exists: $ADMIN_EMAIL"
        return 0
    else
        log_warning "Admin user not found, will create"
        return 1
    fi
}

create_admin_via_db() {
    log_info "Creating admin user via database..."
    
    # Get organization ID
    local org_id=$(docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT id FROM organization WHERE name = 'seoman';" 2>/dev/null || echo "")
    
    if [ -z "$org_id" ]; then
        log_error "Organization 'seoman' not found in database"
        log_info "Please ensure Casdoor has initialized properly"
        return 1
    fi
    
    # Get default application ID
    local app_id=$(docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT id FROM application WHERE name = 'seoman-app' AND owner = '$org_id';" 2>/dev/null || echo "")
    
    if [ -z "$app_id" ]; then
        log_warning "Application 'seoman-app' not found, will use default"
        app_id="app-seoman"
    fi
    
    # Generate UUIDs
    local user_id=$(cat /proc/sys/kernel/random/uuid || python3 -c "import uuid; print(str(uuid.uuid4()))")
    local avatar=$(cat /proc/sys/kernel/random/uuid || python3 -c "import uuid; print(str(uuid.uuid4()))")
    
    # Insert user
    docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" <<EOF 2>/dev/null
INSERT INTO user (id, owner, name, display_name, avatar, type, password, created_ip, email, phone, region, affinity, score, is_online, is_deleted, is_admin, created_time, updated_time)
VALUES (
    '$user_id',
    '$org_id',
    '$ADMIN_EMAIL',
    '$ADMIN_NAME',
    '$avatar',
    'normal-user',
    '$(docker-compose exec -T casdoor-server ./casdoor hash "$ADMIN_PASSWORD" 2>/dev/null | grep -oP 'hash = \K[^[:space:]]+')',
    '',
    '$ADMIN_EMAIL',
    '',
    '',
    '',
    0,
    false,
    false,
    true,
    NOW(),
    NOW()
);

-- Grant user admin role in organization
INSERT INTO permission_rule (id, owner, name, created_time, updated_time)
VALUES (
    'permission-$user_id',
    '$org_id',
    '$user_id',
    NOW(),
    NOW()
);
EOF

    if [ $? -eq 0 ]; then
        log_success "Admin user created successfully"
        log_info "Email: $ADMIN_EMAIL"
        log_info "Password: $ADMIN_PASSWORD"
        log_warning "Please change password after first login!"
        return 0
    else
        log_error "Failed to create admin user"
        return 1
    fi
}

create_admin_via_api() {
    log_info "Creating admin user via Casdoor API..."
    
    # Get JWT token for admin user (default admin/123)
    local token=$(docker-compose exec -T casdoor-server curl -s -X POST \
        "http://localhost:8080/api/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"123"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('accessToken', ''))" 2>/dev/null || echo "")
    
    if [ -z "$token" ]; then
        log_warning "Could not get admin token, falling back to database method"
        create_admin_via_db
        return $?
    fi
    
    # Create user via API
    local result=$(docker-compose exec -T casdoor-server curl -s -X POST \
        "http://localhost:8080/api/add-user" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{
            \"organization\": \"seoman\",
            \"username\": \"$ADMIN_EMAIL\",
            \"name\": \"$ADMIN_NAME\",
            \"password\": \"$ADMIN_PASSWORD\",
            \"email\": \"$ADMIN_EMAIL\",
            \"isAdmin\": true
        }" 2>/dev/null)
    
    if echo "$result" | grep -q '"status":"ok"' || echo "$result" | grep -q '"data"'; then
        log_success "Admin user created successfully via API"
        log_info "Email: $ADMIN_EMAIL"
        log_info "Password: $ADMIN_PASSWORD"
        log_warning "Please change password after first login!"
        return 0
    else
        log_warning "API creation failed, trying database method"
        create_admin_via_db
        return $?
    fi
}

start_services() {
    log_info "Starting SEOman services..."
    
    if [ "$REBUILD" = true ]; then
        log_info "Rebuilding containers without cache..."
        docker-compose build --no-cache
        docker-compose up -d --force-recreate
    else
        docker-compose up -d
    fi
    
    log_success "Services started"
}

main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           SEOman Startup Script                         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check if .env exists
    if [ ! -f .env ]; then
        log_error ".env file not found!"
        log_info "Please copy .env.example to .env and configure it"
        exit 1
    fi
    
    # Start services if needed
    if [ "$SKIP_START" = false ]; then
        start_services
        
        # Wait for database
        wait_for_postgres
        
        # Wait for Casdoor (non-blocking)
        wait_for_casdoor
    fi
    
    # Check if admin exists
    if check_admin_exists; then
        log_info "Admin user already exists, skipping creation"
    else
        # Try API first, fallback to DB
        if [ "$SKIP_START" = false ]; then
            create_admin_via_api
        else
            create_admin_via_db
        fi
    fi
    
    echo ""
    log_success "Startup complete!"
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Access URLs:"
    echo "  Frontend:        http://localhost:3011"
    echo "  Backend API:     http://localhost:8000"
    echo "  API Docs:       http://localhost:8000/docs"
    echo "  Casdoor Web:    http://localhost:7001"
    echo "  MinIO Console:  http://localhost:9001"
    echo ""
    echo "Admin Credentials:"
    echo "  Email:    $ADMIN_EMAIL"
    echo "  Password: $ADMIN_PASSWORD"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Change the admin password after first login!${NC}"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:      docker-compose logs -f"
    echo "  Stop services:  docker-compose down"
    echo "  Restart:        docker-compose restart"
    echo ""
}

# Run main function
main
