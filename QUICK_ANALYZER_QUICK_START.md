# Quick SEO Analyzer Integration - Quick Start Guide

## Overview

Quick SEO Analyzer is a fast, lightweight SEO checking tool that complements Deepcrawl for smaller sites and quick audits.

## Quick Start

### Option 1: Quick Start Script (Easiest)

```bash
cd /root/docker/SEOman
./quick-start.sh
```

This will:
1. Start all SEOman services
2. Quick Analyzer service starts automatically
3. Check health status at http://localhost:8080/health

### Option 2: Manual Start

```bash
# 1. Start core services
docker-compose up -d postgres redis minio backend frontend worker beat

# 2. Start Quick Analyzer
docker-compose up -d quick-analyzer

# 3. Verify services
curl http://localhost:8080/health
docker-compose ps
```

## Quick Analyzer Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Analyze a website |
| `/health` | GET | Check if analyzer is running |
| `/` | GET | API root (usage info) |

### Running Quick Audit

#### Via Backend API

```bash
# Quick audit for a site
curl -X POST http://localhost:8000/api/v1/sites/{site_id}/quick-audits/run \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

#### Via Direct Analyzer

```bash
# Quick analysis (fast, ~30s)
python-seo-analyzer http://localhost:8080/analyze \
  --analyze_headings \
  --analyze_extra_tags \
  --output-format json

# With HTML output (better for reports)
python-seo-analyzer http://localhost:8080/analyze \
  --analyze_headings \
  --analyze_extra_tags \
  --output-format html \
  > report.html
```

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Enable Quick Analyzer
QUICK_ANALYZER_ENABLED=true

# Analyzer Configuration
QUICK_ANALYZER_PORT=8081
PYTHON_SEOANALYZER_URL=http://quick-analyzer:8080
PYTHON_SEOANALYZER_TIMEOUT=30

# Analyzer Selection Strategy
DEFAULT_AUDIT_THRESHOLD_PAGES=1000
ANALYZER_STRATEGY=auto  # options: auto, quick-only, full-only, prefer-quick, prefer-full
```

### Analyzer Strategy Settings

```bash
ANALYZER_STRATEGY=auto
```

**Behavior**:

| Strategy | Threshold | Behavior |
|----------|-----------|----------|
| `auto` | <1000 pages | Use Quick Analyzer |
| `quick-only` | Any size | Always use Quick Analyzer |
| `full-only` | Any size | Always use Deepcrawl |
| `prefer-quick` | <1000 pages | Use Quick Analyzer |
| `prefer-full` | <3000 pages | Use Quick Analyzer first, Deepcrawl for details |

## Score Ranges

| Score | Grade | Issues | Description |
|-------|-------|--------|------------|
| 90-100 | A | 0-2 critical, 0-1 high, 2-5 medium, 6+ low |
| 70-89 | B | 3-6 critical, 6-12 high, 13-20 medium, 21+ low |
| 50-69 | C | 7-15 critical, 15-30 high, 31-60 medium, 61+ low |
| 30-49 | D | 15+ critical, 30-45 high, 46-75 medium, 76+ low |
| 0-29 | F | 20+ critical, 45-75 high, 76+ medium, 151+ low |

## Use Cases

### 1. New Small Sites (Development/Staging)

**Trigger**: Site addition → Run quick audit
**Analyzer**: Quick
**Time**: 30-60 seconds
**Why**: Fast feedback, free, no Deepcrawl quota

```bash
# Backend API
curl -X POST http://localhost:8000/api/v1/sites/{site_id}/quick-audits/run \
  -H "Authorization: Bearer YOUR_TOKEN"

# Quick Analyzer (standalone)
python-seo-analyzer http://your-site.com \
  --analyze_headings \
  --analyze_extra_tags \
  --output_format json
```

### 2. Regular Monitoring (Production)

**Trigger**: Scheduled via UI or API
**Analyzer**: Quick (to detect regressions)
**Frequency**: Daily or weekly
**Why**: Fast, catch issues early without full crawl

```bash
# Re-run previous audit
curl -X POST http://localhost:8000/api/v1/quick-audits/{audit_id}/re-run
```

### 3. Pre-Deepcrawl Analysis (Large Sites)

**Trigger**: Before committing to full crawl
**Analyzer**: Quick (baseline)
**Why**: Get baseline SEO health
**Cost**: Save Deepcrawl quota for when you need full crawl

```bash
# Quick baseline audit
python-seo-analyzer http://your-site.com \
  --analyze_headings \
  --analyze_extra_tags \
  --output-format json
```

Then run Deepcrawl full audit and compare results.

### 4. Issue Investigation

**Trigger**: Alert or specific concern
**Analyzer**: Quick
**Why**: Rapid diagnosis
**Cost**: Save Deepcrawl quota

```bash
# Quick investigation
python-seo-analyzer http://your-site.com \
  --analyze_headings \
  --analyze_extra_tags \
  --output_format json
```

### 5. A/B Testing

**Analyzer A**: Quick audit
**Analyzer B**: Deepcrawl full audit

Compare scores and findings:
- Which found more issues?
- Score differences?
- Overlapping findings?
- Different insights?

### 6. Multi-Analyzer Approach

Run both analyzers and merge results:

```python
# Analyzer A (Quick)
result_a = analyze_site_a(site_url, options_a)
score_a = result_a["score"]

# Analyzer B (Deepcrawl)
result_b = analyze_site_b(site_url, options_b)
score_b = result_b["score"]

# Compare and merge
print(f"Quick score: {score_a}, Deepcrawl score: {score_b}")
print(f"Found {len(result_a['issues'])} issues in Quick")
print(f"Found {len(result_b['issues'])} issues in Deepcrawl")
```

## Troubleshooting

### Quick Analyzer Not Starting

```bash
# Check service status
docker-compose ps quick-analyzer

# Check logs
docker-compose logs quick-analyzer

# Check health
curl http://localhost:8081/health

# Restart service
docker-compose restart quick-analyzer

# Check logs
docker-compose logs -f quick-analyzer
```

### Issues with Analysis

**Score doesn't seem accurate**: Adjust threshold or findings mapping
**Timeout errors**: Increase `PYTHON_SEOANALYZER_TIMEOUT`
**Parse errors**: Check page is accessible, returns HTTP errors

## Architecture Decisions

### Current Stack

```
┌─────────────────┐
│   Frontend (Next.js)     │
├─────────────────┼─────────────────────────┘
│   Backend (FastAPI)      │   Quick Analyzer (HTTP API)
│   Database (PostgreSQL)  │   Deepcrawl (HTTP API - future)
│   Redis                   │   MinIO (Storage)
│   Celery Worker           │   LLM (Local)
│   Celery Beat           │
└──────────────────────────────────────────┘
```

**Quick Analyzer Integration**:
- Backend → HTTP POST to `/analyze` endpoint
- Stores results in `quick_audits` table
- Fast, no DB access for analyzer

## Database Schema

Quick Analyzer results stored in:

```sql
quick_audits (
    id UUID PRIMARY KEY,
    site_id UUID NOT NULL,
    created_by_user_id UUID NOT NULL,
    status VARCHAR(20),
    score INTEGER,
    summary TEXT,
    findings_overview JSONB,
    pages_analyzed INTEGER,
    issues_found INTEGER,
    duration_seconds INTEGER,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

quick_audit_issues (
    id UUID PRIMARY KEY,
    audit_id UUID NOT NULL REFERENCES quick_audits(id),
    type VARCHAR(100),
    category VARCHAR(50),
    severity VARCHAR(10),
    description TEXT,
    url TEXT,
    affected_urls JSONB,
    source_analyzer VARCHAR(50) NOT NULL,
    recommendation TEXT,
    status VARCHAR(20),
    created_at TIMESTAMP,
    resolved_at TIMESTAMP
);
```

## Implementation Progress

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Infrastructure | ✅ Completed | Docker service, HTTP client, environment |
| Phase 2: Backend Services | ✅ In Progress | Quick audit service, config updates |
| Phase 3: Database | ⏳ Pending | Unified audit tables |
| Phase 4: API Endpoints | ⏳ Pending | Quick audit routes |
| Phase 5: Frontend | ⏳ Pending | Quick audit UI |
| Phase 6: Agent | ⏳ Pending | LangGraph workflow |
| Phase 7: Testing | ⏳ Pending | Integration tests |
| Phase 8: Documentation | ✅ Completed | This guide |

## Quick Start Commands

```bash
# Start everything with Quick Analyzer
./quick-start.sh

# Start only Quick Analyzer service
docker-compose up -d quick-analyzer

# Check analyzer health
curl http://localhost:8081/health

# Run quick audit via API
curl -X POST http://localhost:8000/api/v1/sites/{id}/quick-audits/run \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Summary

**Quick Analyzer Features**:
✅ Fast SEO checks (30-60s)
✅ Technical SEO analysis
✅ Heading structure check
✅ Metadata validation
✅ Word count
✅ JSON API output
✅ HTTP-based (no DB access needed)

**Benefits**:
- 10-20x faster than Deepcrawl for small sites
- Free to use
- Perfect for development/testing
- Lightweight and fast
- Complements Deepcrawl
- Cost-efficient

**Integration**:
- HTTP API wrapper for backend
- Unified audit results in database
- Configurable threshold (default 1000 pages)
- Multiple analyzer strategies
- Health check endpoint

**Next**: Implement API endpoints and LangGraph workflow integration
