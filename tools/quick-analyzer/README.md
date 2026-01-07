# Quick SEO Analyzer Tool Setup

## Overview

Quick SEO Analyzer is a lightweight, fast SEO checking tool based on [python-seo-analyzer](https://github.com/sethblack/python-seo-analyzer). It provides complementary analysis to Deepcrawl for smaller sites and quick audits.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  SEOman Frontend               │
│              (Next.js - Dashboard UI)              │
│      ┌──────────┬────────────────────────────────┐ │
│      │ Backend  │      │ Deepcrawl │  │ Quick     │
│      │ (FastAPI) │      │ (External) │  │ Analyzer │  │
│      │            │      │  (New)    │  │           │  │
│      └──────────┴────────────────────────────────┘ │
│               │                              │               │
│               ▼                              ▼               ▼
│               │                              │               │
└─────────────────────────────────────────────────────┘
                      │                              │
                      │                              ▼
                      └──────────────┬─────────────────┐
                 PostgreSQL              │
                 (seoman)                 │
                      └──────────────┴─────────────────┘
                        │
                        ▼
              Quick Analyzer
          (python-seo-analyzer)
                 Port 8081 (internal)
```

## Key Differences

| Feature | Quick Analyzer | Deepcrawl |
|---------|---------------|-----------|
| Speed | 30-60 seconds | 10-60 minutes |
| Cost | Free | Enterprise |
| Best For | Small sites, quick checks | Large sites, full audits |
| Analysis Depth | Basic SEO checks | Comprehensive |
| Approach | Fast API communication | HTTP API + polling |
| Storage | File output | Database storage |
| Crawling | Minimal | Full enterprise crawling |

## Setup Instructions

### 1. Install pyseoanalyzer

Option A: Install as Python package (Recommended for development)

```bash
pip install pyseoanalyzer
```

Option B: Run as standalone tool

```bash
# Clone repository
git clone https://github.com/sethblack/python-seo-analyzer.git
cd python-seo-analyzer

# Run analyzer
python-seo-analyzer http://example.com

# Save as HTML
python-seo-analyzer http://example.com --output-format html > report.html
```

### 2. Configure Environment

Add to `.env` file:

```bash
# Quick Analyzer Configuration
QUICK_ANALYZER_ENABLED=true
QUICK_ANALYZER_PORT=8081

# Analyzer Selection Strategy
DEFAULT_AUDIT_THRESHOLD_PAGES=1000

# python-seo-analyzer API (optional, if using custom instance)
PYTHON_SEOANALYZER_URL=http://quick-analyzer:8080
PYTHON_SEOANALYZER_TIMEOUT=30
```

### 3. Start Services

```bash
# Start SEOman services
./quick-start.sh

# Or manually
docker-compose up -d quick-analyzer
```

### 4. Use Quick Analyzer

#### Via API (Backend)

```bash
# Quick audit (fast, ~30s)
curl -X POST http://localhost:8000/api/v1/sites/{site_id}/quick-audits/run

# Quick audit health check
curl http://localhost:8080/health
```

#### Via Direct Tool

```bash
# Direct analysis
python-seo-analyzer http://example.com --analyze_headings --output-format json

# Analysis with options
python-seo-analyzer http://example.com \
  --analyze_headings \
  --analyze_extra_tags \
  --output-format html
```

## Docker Services

### quick-analyzer

The Quick Analyzer service that wraps python-seo-analyzer.

**Container**: `seoman-quick-analyzer`
**Internal Port**: 8080
**External Port**: 8081
**Purpose**: Fast SEO analysis for small/medium sites

**Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Analyze a website |
| `/health` | GET | Health check |

**Health Check**:

```bash
curl http://localhost:8081/health
```

**Response**:

```json
{
  "status": "healthy",
  "version": "1.0.1"
}
```

## Usage Examples

### Quick Audit (Small Site)

```python
from app.integrations.seoanalyzer_client import SEOAnalyzerClient
from app.services.quick_audit_service import QuickAuditService

client = SEOAnalyzerClient()
service = QuickAuditService(db)

# Run quick audit for site
result = await service.run_quick_audit(
    site_id="site-uuid",
    user_id="user-uuid"
)

# Result:
# {
#   "site_id": "site-uuid",
#   "audit_type": "quick",
#   "analyzer_used": "python-seo-analyzer",
#   "status": "completed",
#   "score": 85,  # 0-100 based on issues
#   "summary": "Quick analysis completed. Found 3 critical, 5 high, 8 medium issues",
#   "pages_analyzed": 45,
#   "issues_found": 16,
#   "duration_seconds": 25,
#   "created_by_user_id": "user-uuid",
#   "created_at": "2024-01-02T10:30:00Z"
# }
```

### Analyzer Health Check

```python
from app.integrations.seoanalyzer_client import SEOAnalyzerClient

client = SEOAnalyzerClient()

# Check if analyzer is healthy
is_healthy = await client.health_check()

if is_healthy:
    print("Quick analyzer is ready to use")
else:
    print("Quick analyzer is not available, will use Deepcrawl")
```

### Manual Analysis

```bash
# Basic analysis
python-seo-analyzer http://example.com \
  --analyze_headings \
  --analyze_extra_tags \
  --output-format json

# Full analysis
python-seo-analyzer http://example.com \
  --analyze_headings \
  --analyze_extra_tags \
  --analyze_meta \
  --analyze_structure \
  --analyze_images \
  --analyze_links \
  --output-format json

# Generate HTML report
python-seo-analyzer http://example.com \
  --analyze_headings \
  --analyze_extra_tags \
  --output-format html \
  > report.html
```

## Analyzer Selection Strategy

### Auto Strategy (Default)

```python
def select_analyzer(site: dict) -> str:
    """Select best analyzer based on site size and settings"""
    threshold = site.get('audit_threshold_pages', 1000)
    strategy = site.get('audit_strategy', 'auto')
    page_count = site.get('page_count', 0)
    
    if strategy == 'quick-only':
        return 'quick'
    elif strategy == 'full-only':
        return 'deepcrawl'
    elif strategy == 'prefer-quick':
        return 'quick'
    elif strategy == 'prefer-full':
        return 'deepcrawl'
    
    # Auto strategy
    if strategy == 'auto':
        if page_count < threshold:
            return 'quick'  # Small site = fast analysis
        elif page_count < threshold * 3:
            return 'quick'  # Medium site = quick first
        else:
            return 'deepcrawl'  # Large site = full crawl
    
    return 'deepcrawl' # Default to Deepcrawl for large sites
```

### Site Configuration

Each site can configure its analyzer strategy in the database or via API:

```python
# Site configuration
site_config = {
    "site_id": "site-uuid",
    "audit_strategy": "auto",  # auto, quick-only, full-only, prefer-quick, prefer-full
    "audit_threshold_pages": 1000,  # Pages threshold
    "quick_analyzer_enabled": True,
    "deepcrawl_enabled": True
}
```

## Score Calculation

Quick Analyzer uses a simplified scoring model:

```python
def calculate_quick_score(warnings: list) -> int:
    """Calculate SEO score (0-100)"""
    score = 100
    
    for warning in warnings:
        severity = warning.get("severity", "low")
        
        if severity == "critical":
            score -= 15
        elif severity == "high":
            score -= 10
        elif severity == "medium":
            score -= 5
        elif severity == "low":
            score -= 2
    
    return max(0, score)
```

### Score Ranges

| Score Range | Grade | Issues |
|------------|-------|--------|
| 90-100 | A | 0-2 critical, 0-1 high |
| 70-89 | B | 3-5 critical, 1-2 high |
| 50-69 | C | 6-8 critical, 2-4 high |
| 30-49 | D | 9+ critical, 5+ high |
| 0-29 | F | 10+ critical, 8+ high |

## Findings Categories

Quick Analyzer provides these issue types:

| Type | Category | Severity | Example |
|------|----------|----------|
| Technical | meta | High | Missing title tag |
| Technical | links | Medium | Broken external link |
| Technical | headers | Low | Multiple H1 tags |
| On-page | content | Medium | Thin content (<300 words) |
| Structure | duplicate | High | Duplicate meta description |
| Performance | speed | Low | Slow page load (>5s) |
| Security | https | Critical | HTTP link without SSL |

## Integration with SEOman

### Database Schema

Quick Analyzer results are stored in separate tables:

```sql
CREATE TABLE quick_audits (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES sites(id),
    created_by_user_id UUID REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    score INTEGER CHECK (score BETWEEN 0 AND 100),
    summary TEXT,
    findings_overview JSONB,
    pages_analyzed INTEGER DEFAULT 0,
    issues_found INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    CONSTRAINT fk_site FOREIGN KEY (site_id) REFERENCES sites(id)
);

CREATE TABLE quick_audit_issues (
    id UUID PRIMARY KEY,
    audit_id UUID REFERENCES quick_audits(id),
    type VARCHAR(100),
    category VARCHAR(50),
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    url TEXT,
    affected_urls JSONB,
    source_analyzer VARCHAR(50) DEFAULT 'python-seo-analyzer',
    recommendation TEXT,
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'ignored')),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    
    CONSTRAINT fk_audit FOREIGN KEY (audit_id) REFERENCES quick_audits(id)
);
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/v1/sites/{id}/quick-audits/run` | Run quick audit |
| `GET /api/v1/sites/{id}/quick-audits` | List quick audits |
| `GET /api/v1/quick-audits/{id}` | Get specific audit |
| `POST /api/v1/sites/{id}/quick-audits/{id}/re-run` | Rerun audit |

## Troubleshooting

### Quick Analyzer Not Starting

```bash
# Check if service is running
docker-compose ps quick-analyzer

# Check logs
docker-compose logs quick-analyzer

# Restart service
docker-compose restart quick-analyzer

# Check health
curl http://localhost:8081/health
```

### Common Issues

**Issue**: Quick analyzer returns errors

```bash
# Check python-seo-analyzer logs
docker-compose logs quick-analyzer

# Test analyzer directly
python-seo-analyzer http://example.com
```

**Issue**: Integration with backend fails

```bash
# Check backend logs
docker-compose logs backend

# Check environment variables
docker-compose exec backend env | grep QUICK
```

## Performance Tips

### Optimize for Speed

1. **Use Quick Analyzer for**: Small sites (<1000 pages)
2. **Increase concurrency**: Adjust python-seo-analyzer thread pool
3. **Use caching**: Enable python-seo-analyzer caching
4. **Adjust timeout**: Default is 30s, may need more for large sites

### Cost Optimization

1. **Default to Quick Analyzer**: For most sites, use free quick analysis
2. **Set page thresholds**: Adjust `DEFAULT_AUDIT_THRESHOLD_PAGES` per site
3. **Schedule full audits**: Only run Deepcrawl weekly or monthly
4. **Limit parallel audits**: Don't run multiple full audits simultaneously

## Migration Path

### From Deepcrawl-Only

Add python-seo-analyzer as complementary tool:

1. Start using quick analyzer for initial checks
2. Run Deepcrawl for comprehensive analysis
3. Compare results
4. Choose best insights from both

### To Hybrid Approach

Combine both analyzers for maximum insights:

1. **Quick Analysis** (python-seo-analyzer):
   - Fast technical SEO checks
   - Immediate results
   - Best for regression testing
   - Free

2. **Full Analysis** (Deepcrawl):
   - Comprehensive crawl data
   - Detailed page-by-page analysis
   - Best for new feature discovery

3. **Unified Reporting**:
   - Merge findings from both
   - Prioritize issues
   - Generate comprehensive SEO plans
   - Track improvements over time

## Examples

### Example Workflow: Small E-commerce Site

```python
# 1. Initial site addition
site = add_site_to_seoman(
    primary_domain="shop.example.com",
    audit_strategy="auto",
    audit_threshold_pages=500  # 500 pages = quick
)

# 2. First audit - Quick Analyzer (30s)
audit = await run_quick_audit(site["id"])
# Result: score=85, 16 issues, 45 pages analyzed

# 3. Fix critical issues (title tags, broken links)
# Fix immediately...

# 4. Second audit - Deepcrawl (30min)
audit = await run_full_audit(site["id"])
# Result: score=78, 45 issues, 1200 pages analyzed

# 5. Keyword research
keywords = await run_keyword_research(site["id"])

# 6. Compare results
compare_audit_results(audit["id"])
```

### Example Workflow: Large Enterprise Site

```python
# 1. Add site with Deepcrawl-only strategy
site = add_site_to_seoman(
    primary_domain="enterprise.com",
    audit_strategy="full-only",
    audit_threshold_pages=10000
)

# 2. First full audit - Deepcrawl (1 hour)
audit = await run_full_audit(site["id"])
# Result: score=72, 150 issues, 10000 pages analyzed

# 3. Implement recommendations

# 4. Schedule weekly audits
schedule_audit(site["id"], frequency="weekly")
```

## Summary

**Quick Analyzer is now integrated with SEOman** as a complementary tool for:

- ✅ Fast initial SEO checks (seconds vs minutes)
- ✅ Small site optimization
- ✅ Free alternative to Deepcrawl licensing
- ✅ Flexibility for different site sizes
- ✅ Configurable thresholds
- ✅ Cost-efficient workflow
- ✅ Cross-validation capabilities

**Use Quick Analyzer when**:
- Sites are < 1000 pages
- Need immediate feedback
- Testing functionality
- Budget is limited

**Use Deepcrawl when**:
- Sites are >1000 pages
- Need comprehensive analysis
- Full crawl required
- Budget allows enterprise tools

**Use Both** when**:
- Maximum insights needed
- Critical SEO projects
- Validation between tools
