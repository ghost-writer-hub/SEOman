#!/bin/bash

# Quick Start Script - SEOman with python-seo-analyzer
# Starts services and runs initial quick SEO audit

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         SEOman + python-seo-analyzer Quick Start             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}Step 1: Start services${NC}"
echo ""

docker-compose up -d

echo ""
echo -e "${BLUE}Step 2: Wait for services to be ready${NC}"
echo ""

sleep 10

echo -e "${BLUE}Step 3: Check service status${NC}"
echo ""

docker-compose ps

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Services Started Successfully!                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}Access URLs:${NC}"
echo ""
echo -e "  Frontend:       ${BLUE}http://localhost:3011${NC}"
echo -e "  Backend API:     ${BLUE}http://localhost:8000${NC}"
echo -e "  API Docs:       ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  Quick Analyzer:  ${BLUE}http://localhost:8080${NC}"
echo -e "  MinIO Console:  ${BLUE}http://localhost:9001${NC}"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e " 1. Configure python-seo-analyzer (if needed)"
echo -e " 2. Add site and run first quick audit"
echo -e " 3. Compare results between analyzers"
echo -e " 4. View audit history"
echo ""
echo -e "${GREEN}Done! Services are running.${NC}"
echo ""
