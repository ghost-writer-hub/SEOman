#!/bin/bash

# SEOman Quick Setup Script

set -e

echo "🚀 SEOman Quick Setup"
echo "======================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and update the following values:"
    echo "   - JWT_SECRET (generate a secure random string)"
    echo "   - CASDOOR_JWT_SECRET (generate another secure random string)"
    echo "   - GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET"
    echo "   - DATAFORSEO_API_LOGIN and DATAFORSEO_API_PASSWORD"
    echo ""
    read -p "Press Enter after you've updated .env (or Ctrl+C to cancel)..."
else
    echo "✅ .env file already exists"
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p backend/database/init
mkdir -p backend/app/models
mkdir -p backend/app/schemas
mkdir -p backend/app/core
mkdir -p backend/app/integrations
mkdir -p backend/app/agents
mkdir -p backend/app/services
mkdir -p backend/alembic/versions
mkdir -p frontend/src/app
mkdir -p frontend/src/components
mkdir -p frontend/src/lib
mkdir -p frontend/src/types
echo "✅ Directories created"
echo ""

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check services status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Access Points:"
echo "   Frontend:        http://localhost:3011"
echo "   Backend API:     http://localhost:8000 (docs: /docs)"
echo "   Casdoor Web:     http://localhost:7001"
echo "   MinIO Console:   http://localhost:9001"
echo ""
echo "📝 Next Steps:"
echo "   1. Access Casdoor at http://localhost:7001"
echo "   2. Login with admin/123"
echo "   3. Create organization: 'seoman'"
echo "   4. Create application: 'seoman-app'"
echo "   5. Configure Google OAuth in Casdoor"
echo "   6. Update CASDOOR_CLIENT_ID and SECRET in .env"
echo ""
echo "📚 For more information, see README.md"
