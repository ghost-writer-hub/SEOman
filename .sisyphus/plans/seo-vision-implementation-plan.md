# SEOman Vision Implementation Plan

## Target Vision

**Goal**: SEO audit of any given site with SEO-oriented plan (articles + page modifications), all outputs stored as `.md` files in Backblaze B2.

**User Acceptance Criteria**:
1. Given any URL, perform a complete SEO audit
2. Generate an SEO improvement plan with:
   - Article suggestions (new content to create)
   - Page modification recommendations (existing pages to fix)
3. Store all outputs as Markdown files in Backblaze B2 (S3-compatible)

---

## Implementation Status: COMPLETE

All critical gaps have been addressed. Here's what was implemented:

| Task | Status | Files Changed |
|------|--------|---------------|
| Fix Audit Task Bug | ✅ Done | `audit_tasks.py` |
| B2 Configuration | ✅ Done | `config.py`, `.env.example` |
| Storage Client Update | ✅ Done | `storage.py` (B2 support + markdown upload) |
| Markdown Generator | ✅ Done | `markdown_generator.py` (NEW) |
| Pipeline Task | ✅ Done | `pipeline_tasks.py` (NEW) |
| Analyze API | ✅ Done | `analyze.py` (NEW), `router.py` |
| Wire Audit API | ✅ Done | `audits.py` |

---

## How to Use

### API Endpoints

**Full Analysis Pipeline** (async):
```bash
POST /api/v1/analyze
{
  "url": "https://example.com",
  "options": {
    "max_pages": 100,
    "generate_briefs": true,
    "plan_duration_weeks": 12
  }
}
```

**Check Status**:
```bash
GET /api/v1/analyze/status/{report_id}
```

**Quick Analysis** (sync):
```bash
POST /api/v1/analyze/quick
{
  "url": "https://example.com"
}
```

### Output Files (stored in B2)

```
tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/
├── audit-report.md      # Full SEO audit with issues
├── seo-plan.md          # Action plan with phases
├── page-fixes.md        # Page-by-page modification guide
├── briefs/
│   ├── article-01-*.md  # Content briefs for new articles
│   └── ...
└── metadata.json        # Report metadata
```

### B2 Configuration

Set in `.env`:
```bash
STORAGE_PROVIDER=b2
B2_ENDPOINT=s3.us-west-004.backblazeb2.com
B2_KEY_ID=your-application-key-id
B2_APPLICATION_KEY=your-application-key
B2_BUCKET=your-bucket-name
```

---

## Original Analysis (for reference)

### What Was Already Working
| Component | Status | Notes |
|-----------|--------|-------|
| MinIO/S3 Storage Client | ✅ Ready | Full implementation with multi-tenant paths |
| LLM Integration | ✅ Ready | Supports Local/OpenAI/Anthropic |
| SEO Analyzer Client | ✅ Ready | On-page analysis via python-seo-analyzer |
| DataForSEO Integration | ✅ Ready | Keyword research and SERP data |
| Database Models | ✅ Ready | Full schema for audits, plans, issues, tasks |
| LangGraph Workflows | ✅ Ready | Audit, Plan, Content, Keyword workflows |
| Celery Task Infrastructure | ✅ Ready | Queues, workers, scheduling configured |

### Critical Gaps (Now Fixed)

| Gap | Impact | Status |
|-----|--------|--------|
| **Markdown Output Generator** | No .md files generated - only JSON | ✅ FIXED |
| **Backblaze B2 Configuration** | MinIO client configured for localhost only | ✅ FIXED |
| **API → Task Wiring** | Task triggers commented out with TODOs | ✅ FIXED |
| **Audit Task Bug** | Calls `analyzer.analyze` instead of `analyzer.analyze_site` | ✅ FIXED |
| **End-to-End Pipeline** | No unified flow from audit → plan → markdown → B2 | ✅ FIXED |
| **Standalone CLI/API** | No simple way to trigger full pipeline for a URL | ✅ FIXED |

---

## Implementation Plan

### Phase 1: Core Bug Fixes & Configuration (P0)

#### 1.1 Fix Audit Task Bug
**File**: `backend/app/tasks/audit_tasks.py`
**Issue**: Line 58 calls `analyzer.analyze()` but method is `analyze_site()`
**Fix**: Change to `analyzer.analyze_site()`

#### 1.2 Backblaze B2 Configuration
**Files**: `backend/app/config.py`, `.env.example`
**Changes**:
- Add B2-specific endpoint configuration
- Support both MinIO (dev) and B2 (prod) modes
- Add B2 region and application key settings

#### 1.3 Wire API Endpoints to Tasks
**Files**: `backend/app/api/v1/audits.py`, `plans.py`
**Changes**: Uncomment/implement Celery `.delay()` calls

---

### Phase 2: Markdown Output System (P0)

#### 2.1 Create Markdown Report Generator
**New File**: `backend/app/services/markdown_generator.py`

Generate structured markdown reports for:
1. **SEO Audit Report** (`audit-report.md`)
   - Executive summary with score
   - Issues by severity (Critical → Low)
   - Affected URLs with specific recommendations
   - Technical details

2. **SEO Plan Document** (`seo-plan.md`)
   - Overview and goals
   - Phase breakdown (Quick Wins → Technical → Content)
   - Task checklist with priorities
   - Content calendar

3. **Article Briefs** (`briefs/article-{n}.md`)
   - Target keyword and intent
   - Recommended structure (H1, H2s)
   - Key points to cover
   - Word count target

4. **Page Modification Guide** (`page-fixes.md`)
   - Grouped by page URL
   - Specific changes needed
   - Before/after examples

#### 2.2 Storage Path Structure
```
tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/
├── audit-report.md           # Full SEO audit
├── seo-plan.md               # Action plan
├── page-fixes.md             # Page modification guide
├── briefs/
│   ├── article-01-keyword.md # Article briefs
│   ├── article-02-keyword.md
│   └── ...
└── metadata.json             # Report metadata
```

---

### Phase 3: End-to-End Pipeline (P0)

#### 3.1 Create Unified Pipeline Task
**New File**: `backend/app/tasks/pipeline_tasks.py`

Single task that orchestrates the full flow:
```
run_full_seo_pipeline(url, options) -> {
  1. Create/get site record
  2. Run SEO audit (technical analysis)
  3. Generate SEO plan from audit results
  4. Create article briefs for content opportunities
  5. Generate all Markdown reports
  6. Upload to B2 storage
  7. Return report URLs
}
```

#### 3.2 Simple API Endpoint
**New Endpoint**: `POST /api/v1/analyze`
```json
{
  "url": "https://example.com",
  "options": {
    "max_pages": 100,
    "generate_briefs": true,
    "plan_duration_weeks": 12
  }
}
```

Response:
```json
{
  "report_id": "uuid",
  "status": "processing",
  "estimated_time": "5-10 minutes"
}
```

#### 3.3 Results Retrieval
**New Endpoint**: `GET /api/v1/reports/{report_id}`
```json
{
  "status": "completed",
  "score": 72,
  "files": {
    "audit_report": "https://b2.../audit-report.md",
    "seo_plan": "https://b2.../seo-plan.md",
    "page_fixes": "https://b2.../page-fixes.md",
    "briefs": ["https://b2.../briefs/article-01.md", ...]
  }
}
```

---

### Phase 4: Backblaze B2 Integration (P0)

#### 4.1 Configuration Updates
```python
# config.py additions
STORAGE_PROVIDER: str = "minio"  # or "b2"
B2_ENDPOINT: str = ""  # e.g., "s3.us-west-004.backblazeb2.com"
B2_KEY_ID: str = ""
B2_APPLICATION_KEY: str = ""
B2_BUCKET: str = ""
```

#### 4.2 Storage Client Updates
**File**: `backend/app/integrations/storage.py`
- Add B2 endpoint support in `StorageConfig`
- Ensure `secure=True` for B2
- Add `ContentType='text/markdown'` for .md files

---

## Implementation Order

| Step | Task | Files | Est. Time |
|------|------|-------|-----------|
| 1 | Fix audit task bug | `audit_tasks.py` | 5 min |
| 2 | Add B2 config options | `config.py`, `.env.example` | 15 min |
| 3 | Update storage client for B2 | `storage.py` | 20 min |
| 4 | Create markdown generator | `markdown_generator.py` (new) | 60 min |
| 5 | Create pipeline task | `pipeline_tasks.py` (new) | 45 min |
| 6 | Add analyze API endpoint | `api/v1/analyze.py` (new) | 30 min |
| 7 | Wire existing endpoints | `audits.py`, `plans.py` | 20 min |
| 8 | Integration testing | - | 30 min |

**Total Estimated Time**: ~4 hours

---

## File Changes Summary

### New Files
- `backend/app/services/markdown_generator.py` - Markdown report generation
- `backend/app/tasks/pipeline_tasks.py` - End-to-end pipeline orchestration
- `backend/app/api/v1/analyze.py` - Simple analyze endpoint

### Modified Files
- `backend/app/config.py` - B2 configuration options
- `backend/app/integrations/storage.py` - B2 endpoint support
- `backend/app/tasks/audit_tasks.py` - Bug fix
- `backend/app/api/v1/audits.py` - Wire task triggers
- `backend/app/api/v1/plans.py` - Wire task triggers
- `backend/app/api/v1/router.py` - Add analyze routes
- `.env.example` - B2 configuration template

---

## Success Metrics

1. **Functional Test**: Submit any URL → receive markdown reports in B2
2. **Content Quality**: Audit report covers all major SEO factors
3. **Plan Actionability**: Generated plan has specific, implementable tasks
4. **Storage Verification**: All .md files accessible via B2 presigned URLs

---

## Notes

- The scraping speed concern is addressed - the system already supports configurable `max_pages` and async processing
- LLM is optional but recommended for AI-enhanced recommendations
- The python-seo-analyzer service must be running for technical audits
- DataForSEO credentials needed for keyword research (can be skipped for basic audits)
