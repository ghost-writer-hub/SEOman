# SEOman v2.0 - Complete Redesign Plan

**Version:** 2.0  
**Date:** 2026-01-07  
**Status:** Planning Phase

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current System Analysis](#2-current-system-analysis)
3. [The 100-Point Technical SEO Audit Framework](#3-the-100-point-technical-seo-audit-framework)
4. [Crawling & Scraping Architecture](#4-crawling--scraping-architecture)
5. [Keyword Research System](#5-keyword-research-system)
6. [Report Generation Engine](#6-report-generation-engine)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Technical Architecture](#8-technical-architecture)
9. [Appendix: Existing Codebase Inventory](#9-appendix-existing-codebase-inventory)

---

## 1. Executive Summary

### The Problem

The current SEOman system generates **embarrassingly shallow reports** that check only 3 basic factors:
- Title tag length
- Meta description presence
- H1 tag presence

This is approximately **3% of what a professional SEO audit should cover**. Real SEO tools like Screaming Frog, Sitebulb, and Ahrefs check 100+ factors across crawlability, performance, content quality, structured data, and more.

### The Vision

SEOman v2.0 will be a **comprehensive, AI-powered SEO platform** that:

1. **Crawls entire websites** (not just single pages) and stores HTML for re-analysis
2. **Audits 100+ technical SEO factors** across 10 categories
3. **Performs intelligent keyword research** using DataForSEO + LLM clustering
4. **Generates actionable, professional-grade reports** with prioritized recommendations
5. **Identifies content gaps** by comparing against competitors
6. **Provides ongoing monitoring** with scheduled audits and ranking tracking

### Key Deliverables

| Component | Current State | v2.0 Target |
|-----------|---------------|-------------|
| SEO Checks | 3 basic | 100+ comprehensive |
| Crawl Depth | Single page | Full site (100k+ pages) |
| HTML Storage | None | Full archive in S3 |
| Keyword Research | Stubbed | Full DataForSEO integration |
| Content Gap Analysis | None | Competitor comparison |
| Report Quality | Basic | Professional-grade |

---

## 2. Current System Analysis

### 2.1 What Exists and Works

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| **Database Models** | `backend/app/models/` | ✅ Solid | CrawlJob, CrawlPage, Keyword, KeywordCluster, AuditRun, SeoIssue |
| **DataForSEO Client** | `backend/app/integrations/dataforseo.py` | ✅ Functional | Keywords for site, related keywords, SERP overview |
| **LLM Integration** | `backend/app/integrations/llm.py` | ✅ Functional | OpenAI/Anthropic/Local LLM support, keyword clustering |
| **LangGraph Workflows** | `backend/app/agents/workflows/` | ✅ Partial | Plan workflow works, others need wiring |
| **Storage Client** | `backend/app/integrations/storage.py` | ✅ Functional | Local + S3/MinIO support |
| **Celery Workers** | `backend/app/tasks/` | ✅ Functional | Pipeline, crawl, keyword tasks |
| **Markdown Generator** | `backend/app/services/markdown_generator.py` | ⚠️ Basic | Works but template-based, limited checks |

### 2.2 What's Broken or Missing

| Component | Issue | Impact |
|-----------|-------|--------|
| **Quick Analyzer** | Only uses `pyseoanalyzer` with `follow_links=False` | Single-page analysis only |
| **SEO Checks** | Only 3 checks implemented | 97% of audit criteria missing |
| **HTML Storage** | Pages not stored, only metadata | Cannot re-analyze without re-crawling |
| **Keyword API Wiring** | Method name mismatches (`get_keyword_ideas` vs `keywords_for_keywords`) | Keyword tasks fail silently |
| **Gap Analysis** | `_analyze_keyword_gaps` is empty placeholder | No competitor analysis |
| **Model Discrepancies** | `CrawlPage` model missing `load_time_ms`, `issues` fields | Data loss |
| **JS Rendering** | No Playwright/headless browser | Cannot crawl SPAs |

### 2.3 Current Report Output (What's Wrong)

The current audit report for `quercuscareclinic.es` found only 3 issues:
1. Missing Meta Description
2. Missing H1 Tag  
3. Title Tag Too Short

**What a real audit should find (examples):**
- robots.txt validation
- Sitemap presence and validity
- Core Web Vitals scores
- Mobile usability issues
- Structured data errors
- Internal linking problems
- Redirect chains
- Broken links
- Image optimization issues
- Security (HTTPS, mixed content)
- And 90+ more checks...

---

## 3. The 100-Point Technical SEO Audit Framework

### 3.1 Audit Categories Overview

| Category | Checks | Priority |
|----------|--------|----------|
| **1. Crawlability & Indexability** | 10 | Critical |
| **2. On-Page SEO** | 10 | High |
| **3. Technical Performance (Core Web Vitals)** | 10 | High |
| **4. URL Structure** | 10 | Medium |
| **5. Internal Linking** | 10 | High |
| **6. Content Quality** | 10 | High |
| **7. Structured Data** | 10 | Medium |
| **8. Security & Accessibility** | 10 | High |
| **9. Mobile Optimization** | 10 | High |
| **10. Server & Infrastructure** | 10 | Medium |

### 3.2 Complete Audit Checklist

#### Category 1: Crawlability & Indexability

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 1 | Robots.txt Presence | High | Fetch `/robots.txt`, parse directives |
| 2 | Robots.txt Blocking Critical Resources | Critical | Check if CSS/JS/images blocked |
| 3 | Sitemap.xml Presence | High | Check `/sitemap.xml` and robots.txt |
| 4 | Sitemap Validity | Medium | Validate XML, check for errors |
| 5 | Noindex Tags on Important Pages | Critical | Parse `<meta name="robots">` |
| 6 | Canonical Tag Presence | Medium | Check `<link rel="canonical">` |
| 7 | Canonical Self-Referencing | Medium | Ensure canonical points to self |
| 8 | X-Robots-Tag in Headers | High | Check HTTP response headers |
| 9 | Orphan Pages | High | Pages with no internal links |
| 10 | Crawl Depth > 4 | Medium | Track clicks from homepage |

#### Category 2: On-Page SEO

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 11 | Missing Title Tag | High | Parse `<title>` |
| 12 | Title Too Short (<30 chars) | Medium | Length check |
| 13 | Title Too Long (>60 chars) | Low | Length check |
| 14 | Duplicate Title Tags | High | Compare across pages |
| 15 | Missing Meta Description | High | Parse `<meta name="description">` |
| 16 | Meta Description Length | Low | 120-160 chars optimal |
| 17 | Missing H1 | High | Parse `<h1>` |
| 18 | Multiple H1s | Medium | Count H1 tags |
| 19 | Heading Hierarchy Broken | Low | Check H1->H2->H3 order |
| 20 | Missing Image Alt Text | Medium | Check all `<img alt>` |

#### Category 3: Technical Performance

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 21 | LCP > 2.5s | High | Lighthouse/PageSpeed API |
| 22 | INP > 200ms | Medium | Lighthouse/PageSpeed API |
| 23 | CLS > 0.1 | High | Lighthouse/PageSpeed API |
| 24 | TTFB > 800ms | Medium | Measure from crawl |
| 25 | Render-Blocking Resources | High | Lighthouse audit |
| 26 | Uncompressed Images | Medium | Check file sizes |
| 27 | Missing Image Dimensions | Medium | Check width/height attributes |
| 28 | No Text Compression | Medium | Check Content-Encoding header |
| 29 | Unminified CSS/JS | Low | Check for whitespace |
| 30 | Third-Party Script Impact | Medium | Count external scripts |

#### Category 4: URL Structure

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 31 | URL Length > 100 chars | Low | Measure URL length |
| 32 | Non-ASCII Characters | Medium | Regex check |
| 33 | Underscores in URLs | Low | Pattern check |
| 34 | Uppercase in URLs | Low | Case check |
| 35 | Trailing Slash Inconsistency | Medium | Compare with canonical |
| 36 | URL Depth > 4 levels | Medium | Count path segments |
| 37 | Dynamic Parameters | Medium | Check for `?` in URLs |
| 38 | Session IDs in URLs | High | Pattern detection |
| 39 | Duplicate Content URLs | High | Same content, different URLs |
| 40 | Missing Keywords in URL | Low | Compare with H1/title |

#### Category 5: Internal Linking

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 41 | Orphan Pages | High | No incoming internal links |
| 42 | Broken Internal Links (404) | High | Follow and check status |
| 43 | Redirect Chains (Internal) | Medium | Follow redirects |
| 44 | Nofollow on Internal Links | Medium | Check `rel="nofollow"` |
| 45 | Generic Anchor Text | Medium | "Click here", "Read more" |
| 46 | Low Internal Link Count | Medium | Pages with < 3 internal links |
| 47 | High Internal Link Count | Low | Pages with > 100 internal links |
| 48 | Missing Breadcrumbs | Low | Check for breadcrumb markup |
| 49 | Deep Pages (> 4 clicks) | Medium | Calculate from homepage |
| 50 | Pagination Issues | Medium | Check rel="next/prev" |

#### Category 6: Content Quality

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 51 | Thin Content (< 300 words) | High | Word count |
| 52 | Duplicate Content (Internal) | High | Content fingerprinting |
| 53 | Near-Duplicate Content | Medium | Similarity scoring |
| 54 | Missing Content | High | Pages with only navigation |
| 55 | Keyword Stuffing | Medium | Keyword density > 3% |
| 56 | Outdated Content | Low | Check for old dates |
| 57 | Broken Images | Medium | Check image 404s |
| 58 | Missing OpenGraph Tags | Low | Check og:title, og:image |
| 59 | Missing Twitter Cards | Low | Check twitter:card |
| 60 | Low Readability Score | Low | Flesch-Kincaid check |

#### Category 7: Structured Data

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 61 | No Structured Data | Medium | Check for JSON-LD/Microdata |
| 62 | Schema Syntax Errors | High | Validate against schema.org |
| 63 | Missing Organization Schema | Medium | Homepage check |
| 64 | Missing Breadcrumb Schema | Low | Check BreadcrumbList |
| 65 | Missing Article Schema | Medium | Blog/news pages |
| 66 | Missing Product Schema | High | E-commerce pages |
| 67 | Missing LocalBusiness Schema | High | Local business sites |
| 68 | Missing FAQ Schema | Low | FAQ pages |
| 69 | Missing Review Schema | Medium | Review pages |
| 70 | Incomplete Schema Fields | Medium | Required fields missing |

#### Category 8: Security & Accessibility

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 71 | Not HTTPS | Critical | Check protocol |
| 72 | Mixed Content | High | HTTP resources on HTTPS |
| 73 | Missing SSL Certificate | Critical | Certificate validation |
| 74 | Expired SSL Certificate | Critical | Check expiry date |
| 75 | Missing HSTS Header | Medium | Check Strict-Transport-Security |
| 76 | Missing Language Declaration | Medium | Check `<html lang>` |
| 77 | Missing/Invalid Hreflang | High | International sites |
| 78 | Low Color Contrast | Low | WCAG check |
| 79 | Missing Form Labels | Medium | Accessibility check |
| 80 | Missing Skip Links | Low | Accessibility check |

#### Category 9: Mobile Optimization

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 81 | Missing Viewport Meta | High | Check `<meta name="viewport">` |
| 82 | Viewport Not Responsive | High | Check content width |
| 83 | Tap Targets Too Small | Medium | < 48x48px |
| 84 | Font Size Too Small | Medium | < 12px |
| 85 | Content Wider Than Screen | High | Horizontal scroll |
| 86 | Intrusive Interstitials | Medium | Popup detection |
| 87 | Mobile-Only 404s | High | Compare mobile vs desktop |
| 88 | Flash Content | High | Detect Flash |
| 89 | Plugins Required | High | Detect unsupported plugins |
| 90 | Touch Elements Too Close | Medium | Spacing check |

#### Category 10: Server & Infrastructure

| # | Check | Severity | Implementation |
|---|-------|----------|----------------|
| 91 | 4xx Errors | High | Status code check |
| 92 | 5xx Errors | Critical | Status code check |
| 93 | Redirect Chains | Medium | > 2 redirects |
| 94 | Redirect Loops | High | Detect loops |
| 95 | 302 Instead of 301 | Medium | Check redirect type |
| 96 | Missing Custom 404 Page | Low | Check 404 response |
| 97 | No Browser Caching | Low | Check Cache-Control |
| 98 | No CDN Detected | Low | Check response headers |
| 99 | Slow Server Response | Medium | TTFB > 600ms |
| 100 | IP Canonicalization | Medium | IP access check |

### 3.3 Implementation Strategy

Each check will be implemented as a modular function:

```python
class SEOAuditEngine:
    def __init__(self, crawl_data: CrawlData):
        self.data = crawl_data
        self.issues = []
    
    def run_all_checks(self) -> List[SEOIssue]:
        # Crawlability
        self.check_robots_txt()
        self.check_sitemap()
        self.check_noindex()
        self.check_canonicals()
        # ... 96 more checks
        return self.issues
    
    def check_robots_txt(self):
        if not self.data.robots_txt.exists:
            self.issues.append(SEOIssue(
                check_id=1,
                category="Crawlability",
                severity="high",
                title="Missing robots.txt",
                description="No robots.txt file found at /robots.txt",
                recommendation="Create a robots.txt file...",
                affected_urls=[self.data.base_url + "/robots.txt"]
            ))
```

---

## 4. Crawling & Scraping Architecture

### 4.1 Requirements

1. **Full Site Crawl**: Discover all pages via sitemap + link following
2. **HTML Storage**: Store raw HTML in S3 for re-analysis
3. **JavaScript Rendering**: Support SPAs with Playwright
4. **Metadata Extraction**: Extract all SEO-relevant data
5. **Politeness**: Respect robots.txt, rate limiting
6. **Scale**: Handle 100k+ page sites

### 4.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CRAWL ORCHESTRATOR                        │
│                    (Celery Task: start_crawl)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DISCOVERY LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Sitemap      │  │ Robots.txt   │  │ Link Extraction      │   │
│  │ Parser       │  │ Parser       │  │ (recursive)          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          CRAWL ENGINE                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Crawlee (Python) with Playwright                          │   │
│  │ - Async HTTP requests for static pages                    │   │
│  │ - Headless Chrome for JS-rendered pages                   │   │
│  │ - Automatic retry, rate limiting, proxy rotation          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                            │
│  ┌──────────────────────┐    ┌──────────────────────────────┐   │
│  │ PostgreSQL           │    │ S3 / MinIO                    │   │
│  │ - CrawlJob metadata  │    │ - Raw HTML files              │   │
│  │ - CrawlPage metadata │    │ - Markdown conversions        │   │
│  │ - Extracted SEO data │    │ - Screenshots                 │   │
│  └──────────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ANALYSIS LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ SEO Audit Engine (100 checks)                             │   │
│  │ Content Analyzer (keyword extraction, readability)        │   │
│  │ Performance Analyzer (Core Web Vitals via Lighthouse)     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Data Extraction Per Page

For each crawled page, extract and store:

```python
@dataclass
class CrawledPage:
    # Identity
    url: str
    final_url: str  # After redirects
    crawl_timestamp: datetime
    
    # HTTP Response
    status_code: int
    content_type: str
    response_time_ms: int
    headers: Dict[str, str]
    
    # HTML Content
    raw_html: str  # Store in S3
    markdown_content: str  # Converted for LLM analysis
    
    # SEO Elements
    title: str
    meta_description: str
    meta_robots: str
    canonical_url: str
    h1: List[str]
    h2: List[str]
    h3: List[str]
    
    # Links
    internal_links: List[Link]
    external_links: List[Link]
    
    # Images
    images: List[Image]  # url, alt, width, height, size
    
    # Structured Data
    json_ld: List[Dict]
    microdata: List[Dict]
    
    # Content Metrics
    word_count: int
    text_ratio: float  # Text vs HTML ratio
    
    # Technical
    robots_directives: List[str]
    hreflang_tags: List[Dict]
    open_graph: Dict
    twitter_cards: Dict
```

### 4.4 HTML to Markdown Conversion

For content analysis and LLM processing:

```python
from html2text import HTML2Text

def html_to_markdown(html: str, url: str) -> str:
    """Convert HTML to clean Markdown for content analysis."""
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # No wrapping
    
    # Extract main content (skip nav, footer, sidebar)
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('main') or soup.find('article') or soup.find('body')
    
    # Remove non-content elements
    for element in main_content.find_all(['nav', 'footer', 'aside', 'script', 'style']):
        element.decompose()
    
    return h.handle(str(main_content))
```

### 4.5 Crawlee Implementation

```python
# backend/app/services/crawler.py
from crawlee.playwright_crawler import PlaywrightCrawler
from crawlee.storages import RequestQueue

class SEOmanCrawler:
    def __init__(self, site_url: str, max_pages: int = 1000):
        self.site_url = site_url
        self.max_pages = max_pages
        self.pages_crawled = 0
        
    async def crawl(self) -> List[CrawledPage]:
        crawler = PlaywrightCrawler(
            max_requests_per_crawl=self.max_pages,
            request_handler=self.handle_page,
        )
        
        # Start with sitemap URLs + homepage
        start_urls = await self.discover_start_urls()
        await crawler.run(start_urls)
        
        return self.results
    
    async def handle_page(self, context):
        page = context.page
        request = context.request
        
        # Wait for JS rendering
        await page.wait_for_load_state('networkidle')
        
        # Extract all data
        crawled = CrawledPage(
            url=request.url,
            final_url=page.url,
            status_code=context.response.status,
            raw_html=await page.content(),
            title=await page.title(),
            # ... extract everything
        )
        
        # Store HTML in S3
        await self.storage.upload_html(crawled)
        
        # Store metadata in PostgreSQL
        await self.db.save_page(crawled)
        
        # Enqueue discovered links
        await context.enqueue_links(
            strategy='same-domain',
            transformRequestFunction=self.filter_urls
        )
```

---

## 5. Keyword Research System

### 5.1 Current State Issues

1. **Method Naming Mismatch**: `keyword_tasks.py` calls `get_keyword_ideas()` but `dataforseo.py` defines `keywords_for_keywords()`
2. **Gap Analysis Empty**: `_analyze_keyword_gaps()` returns 0
3. **API Endpoints Stubbed**: REST endpoints don't trigger actual tasks

### 5.2 Complete Keyword Research Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    KEYWORD RESEARCH PIPELINE                     │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ 1. DISCOVERY  │      │ 2. EXPANSION  │      │ 3. COMPETITOR │
│ Extract from  │      │ DataForSEO    │      │ Gap Analysis  │
│ crawled pages │      │ related_kw    │      │               │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     4. METRICS ENRICHMENT                        │
│          DataForSEO: volume, CPC, difficulty, intent            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     5. SEMANTIC CLUSTERING                       │
│               LLM-based grouping by intent/topic                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      6. OPPORTUNITY SCORING                      │
│        Prioritize: high volume + low competition + gaps         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    7. CONTENT RECOMMENDATIONS                    │
│           Map clusters to content types and briefs              │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Keyword Discovery from Content

```python
async def extract_keywords_from_content(pages: List[CrawledPage]) -> List[str]:
    """Extract potential keywords from crawled content using LLM."""
    
    # Combine all page content
    all_content = "\n\n".join([
        f"Title: {p.title}\nH1: {p.h1[0] if p.h1 else ''}\nContent: {p.markdown_content[:2000]}"
        for p in pages[:50]  # Sample 50 pages
    ])
    
    prompt = f"""Analyze this website content and extract:
    1. Primary topic/niche (1-3 words)
    2. Main service/product keywords (10-20)
    3. Long-tail keyword opportunities (20-30)
    4. Question-based keywords (10-15)
    
    Content:
    {all_content}
    
    Return as JSON with keys: niche, main_keywords, longtail_keywords, questions
    """
    
    response = await llm.generate(prompt)
    return parse_keywords(response)
```

### 5.4 Gap Analysis Implementation

```python
async def analyze_keyword_gaps(
    our_domain: str,
    competitors: List[str],
    country: str = "US"
) -> List[KeywordGap]:
    """Find keywords competitors rank for that we don't."""
    
    client = DataForSEOClient()
    
    # Get our keywords
    our_keywords = set()
    our_data = await client.keywords_for_site(our_domain, country)
    for kw in our_data:
        if kw.get('position', 100) <= 20:
            our_keywords.add(kw['text'].lower())
    
    # Get competitor keywords
    competitor_keywords = {}
    for comp in competitors:
        comp_data = await client.keywords_for_site(comp, country)
        for kw in comp_data:
            if kw.get('position', 100) <= 10:
                keyword = kw['text'].lower()
                if keyword not in competitor_keywords:
                    competitor_keywords[keyword] = {
                        'keyword': keyword,
                        'volume': kw.get('search_volume', 0),
                        'competitors': [],
                        'avg_position': 0
                    }
                competitor_keywords[keyword]['competitors'].append(comp)
    
    # Find gaps
    gaps = []
    for kw, data in competitor_keywords.items():
        if kw not in our_keywords and data['volume'] > 100:
            gaps.append(KeywordGap(
                keyword=data['keyword'],
                search_volume=data['volume'],
                competitor_count=len(data['competitors']),
                competitors=data['competitors'],
                priority=calculate_gap_priority(data)
            ))
    
    # Sort by priority
    gaps.sort(key=lambda x: x.priority, reverse=True)
    return gaps[:100]
```

### 5.5 Semantic Clustering

```python
async def cluster_keywords_semantically(
    keywords: List[Dict],
    num_clusters: int = 10
) -> List[KeywordCluster]:
    """Group keywords by semantic similarity using LLM."""
    
    keyword_texts = [kw['text'] for kw in keywords]
    
    prompt = f"""Group these keywords into {num_clusters} semantic clusters based on:
    1. Search intent (informational, transactional, navigational)
    2. Topic similarity
    3. User journey stage (awareness, consideration, decision)
    
    Keywords:
    {json.dumps(keyword_texts)}
    
    Return JSON array of clusters:
    [
        {{
            "name": "Cluster Name",
            "intent": "informational|transactional|navigational",
            "stage": "awareness|consideration|decision",
            "keywords": ["kw1", "kw2"],
            "recommended_content_type": "blog|landing|product|comparison",
            "content_angle": "What unique angle to take"
        }}
    ]
    """
    
    response = await llm.generate(prompt)
    clusters = json.loads(response)
    
    # Enrich with metrics
    for cluster in clusters:
        cluster_kws = [kw for kw in keywords if kw['text'] in cluster['keywords']]
        cluster['total_volume'] = sum(kw.get('search_volume', 0) for kw in cluster_kws)
        cluster['avg_difficulty'] = avg([kw.get('difficulty', 50) for kw in cluster_kws])
    
    return [KeywordCluster(**c) for c in clusters]
```

---

## 6. Report Generation Engine

### 6.1 Report Types

| Report | Purpose | Audience |
|--------|---------|----------|
| **Executive Summary** | High-level overview with score | C-suite, clients |
| **Technical Audit** | Detailed 100-point checklist | SEO team |
| **Content Analysis** | Keyword coverage, gaps | Content team |
| **Action Plan** | Prioritized tasks by week | Implementation team |
| **Competitor Report** | Gap analysis, benchmarks | Strategy team |
| **Page-by-Page Fixes** | Specific fixes per URL | Developers |

### 6.2 Report Structure (Technical Audit)

```markdown
# Technical SEO Audit Report

**Site:** example.com
**Crawled:** 2026-01-07
**Pages Analyzed:** 1,234
**Overall Score:** 72/100

---

## Executive Summary

Your site has **significant technical issues** that are likely impacting search visibility.

### Critical Issues (Immediate Action Required)
- 23 pages returning 5xx server errors
- SSL certificate expires in 7 days
- 15 pages blocked by robots.txt that shouldn't be

### Key Metrics
| Metric | Value | Status |
|--------|-------|--------|
| Pages Crawled | 1,234 | ✅ |
| Indexable Pages | 1,156 | ✅ |
| Avg. Load Time | 3.2s | ⚠️ |
| Mobile Friendly | 87% | ⚠️ |
| Core Web Vitals Pass | 34% | ❌ |

---

## Detailed Findings

### 1. Crawlability & Indexability (8/10)

#### ✅ Passing Checks
- [x] Robots.txt present and valid
- [x] XML Sitemap found (1,456 URLs)
- [x] No critical pages blocked

#### ❌ Issues Found

##### 1.1 Orphan Pages (23 found)
**Severity:** High
**Impact:** These pages have no internal links and may not be discovered by search engines.

| URL | Page Type | Recommendation |
|-----|-----------|----------------|
| /old-product-123 | Product | Add to category or redirect |
| /blog/draft-post | Blog | Publish or delete |
| ... | ... | ... |

**How to Fix:**
1. Review each orphan page
2. Add internal links from relevant pages
3. Or add to sitemap and navigation

---

[... continue for all 10 categories ...]

---

## Appendix

### A. Full Issue List (CSV Export Available)
### B. Crawl Statistics
### C. Technical Details
```

### 6.3 Jinja2 Template System

Replace current string concatenation with Jinja2:

```python
# backend/app/services/report_templates/audit_report.html.j2

{% extends "base.html.j2" %}

{% block content %}
# Technical SEO Audit Report

**Site:** {{ site_url }}
**Crawled:** {{ crawl_date | date }}
**Pages Analyzed:** {{ pages_count | number }}
**Overall Score:** {{ score }}/100

---

## Executive Summary

{{ executive_summary }}

### Critical Issues
{% for issue in critical_issues %}
- {{ issue.title }}: {{ issue.count }} occurrences
{% endfor %}

---

{% for category in categories %}
## {{ loop.index }}. {{ category.name }} ({{ category.score }}/10)

{% for check in category.checks %}
### {{ category_loop.index }}.{{ loop.index }} {{ check.name }}
**Status:** {{ "✅ Pass" if check.passed else "❌ Fail" }}
{% if not check.passed %}
**Severity:** {{ check.severity }}
**Affected:** {{ check.affected_count }} pages

{{ check.description }}

**Recommendation:** {{ check.recommendation }}
{% endif %}
{% endfor %}
{% endfor %}
{% endblock %}
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Fix CrawlPage model discrepancies | High | 2h | Backend |
| Fix DataForSEO method naming | High | 1h | Backend |
| Implement Crawlee crawler service | High | 16h | Backend |
| Add HTML storage to S3 | High | 4h | Backend |
| Set up Playwright for JS rendering | High | 8h | DevOps |

### Phase 2: Audit Engine (Weeks 3-4)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Implement 10 crawlability checks | High | 8h | Backend |
| Implement 10 on-page checks | High | 8h | Backend |
| Implement 10 performance checks | High | 12h | Backend |
| Implement 10 URL structure checks | Medium | 6h | Backend |
| Implement 10 internal linking checks | High | 10h | Backend |

### Phase 3: Audit Engine Continued (Weeks 5-6)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Implement 10 content quality checks | High | 10h | Backend |
| Implement 10 structured data checks | Medium | 8h | Backend |
| Implement 10 security checks | High | 6h | Backend |
| Implement 10 mobile checks | High | 8h | Backend |
| Implement 10 server checks | Medium | 6h | Backend |

### Phase 4: Keyword Research (Weeks 7-8)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Fix keyword API wiring | High | 4h | Backend |
| Implement content keyword extraction | High | 8h | Backend |
| Implement gap analysis | High | 12h | Backend |
| Implement semantic clustering | High | 8h | Backend |
| Connect to LangGraph workflow | Medium | 4h | Backend |

### Phase 5: Reports & Polish (Weeks 9-10)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Create Jinja2 report templates | High | 16h | Backend |
| Implement executive summary | High | 4h | Backend |
| Implement competitor comparison | Medium | 8h | Backend |
| Create PDF export | Low | 8h | Backend |
| UI/UX for report viewing | Medium | 16h | Frontend |

### Phase 6: Testing & Launch (Weeks 11-12)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Integration testing | High | 16h | QA |
| Performance testing (large sites) | High | 8h | QA |
| Documentation | Medium | 8h | Docs |
| Beta testing with real sites | High | 16h | Team |
| Production deployment | High | 4h | DevOps |

---

## 8. Technical Architecture

### 8.1 New Services Required

```yaml
# docker-compose.yml additions

services:
  # Replace quick-analyzer with full crawler
  seoman-crawler:
    build: ./crawler
    environment:
      - PLAYWRIGHT_BROWSERS_PATH=/browsers
    volumes:
      - playwright-browsers:/browsers
    depends_on:
      - seoman-redis
      
  # PageSpeed/Lighthouse API for Core Web Vitals
  lighthouse-server:
    image: nickrediean/lighthouse-server:latest
    ports:
      - "9411:9411"
```

### 8.2 Database Schema Updates

```sql
-- Add missing fields to crawl_pages
ALTER TABLE crawl_pages ADD COLUMN load_time_ms INTEGER;
ALTER TABLE crawl_pages ADD COLUMN issues JSONB DEFAULT '[]';
ALTER TABLE crawl_pages ADD COLUMN raw_html_path TEXT;  -- S3 path
ALTER TABLE crawl_pages ADD COLUMN markdown_path TEXT;  -- S3 path
ALTER TABLE crawl_pages ADD COLUMN structured_data JSONB;
ALTER TABLE crawl_pages ADD COLUMN open_graph JSONB;
ALTER TABLE crawl_pages ADD COLUMN hreflang JSONB;

-- New table for audit checks
CREATE TABLE seo_audit_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_run_id UUID REFERENCES audit_runs(id) ON DELETE CASCADE,
    check_id INTEGER NOT NULL,  -- 1-100
    category VARCHAR(50) NOT NULL,
    check_name VARCHAR(100) NOT NULL,
    passed BOOLEAN NOT NULL,
    severity VARCHAR(20),
    affected_count INTEGER DEFAULT 0,
    affected_urls JSONB DEFAULT '[]',
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- New table for keyword gaps
CREATE TABLE keyword_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    search_volume INTEGER,
    difficulty INTEGER,
    competitor_count INTEGER,
    competitors JSONB DEFAULT '[]',
    priority_score FLOAT,
    status VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 8.3 API Endpoints

```python
# New/Updated API routes

# Crawl Management
POST   /api/v1/crawl/start          # Start full site crawl
GET    /api/v1/crawl/{id}/status    # Get crawl progress
GET    /api/v1/crawl/{id}/pages     # List crawled pages
DELETE /api/v1/crawl/{id}           # Cancel/delete crawl

# Audit
POST   /api/v1/audit/run            # Run audit on crawled data
GET    /api/v1/audit/{id}           # Get audit results
GET    /api/v1/audit/{id}/checks    # Get all 100 checks
GET    /api/v1/audit/{id}/issues    # Get issues only

# Keywords
POST   /api/v1/keywords/discover    # Extract from content
POST   /api/v1/keywords/expand      # DataForSEO expansion
POST   /api/v1/keywords/gaps        # Competitor gap analysis
GET    /api/v1/keywords/clusters    # Get semantic clusters

# Reports
GET    /api/v1/reports/{id}         # Get report
GET    /api/v1/reports/{id}/pdf     # Download PDF
GET    /api/v1/reports/{id}/csv     # Download raw data
```

---

## 9. Appendix: Existing Codebase Inventory

### 9.1 Files to Modify

| File | Changes Needed |
|------|----------------|
| `backend/app/models/crawl.py` | Add `load_time_ms`, `issues`, `raw_html_path`, `markdown_path`, `structured_data` |
| `backend/app/integrations/dataforseo.py` | Add alias methods for compatibility |
| `backend/app/tasks/keyword_tasks.py` | Fix method calls, implement gap analysis |
| `backend/app/tasks/crawl_tasks.py` | Replace with Crawlee-based crawler |
| `backend/app/services/markdown_generator.py` | Replace with Jinja2 templates |
| `backend/app/integrations/seoanalyzer.py` | Replace with new audit engine |

### 9.2 New Files to Create

| File | Purpose |
|------|---------|
| `backend/app/services/crawler.py` | Crawlee-based full site crawler |
| `backend/app/services/audit_engine.py` | 100-check audit implementation |
| `backend/app/services/report_generator.py` | Jinja2-based report generation |
| `backend/app/services/gap_analyzer.py` | Competitor keyword gap analysis |
| `backend/app/services/templates/*.j2` | Report templates |
| `crawler/Dockerfile` | Crawler service container |
| `crawler/requirements.txt` | Crawlee, Playwright deps |

### 9.3 Files That Work Well (Keep As-Is)

| File | Notes |
|------|-------|
| `backend/app/models/keyword.py` | Good schema |
| `backend/app/models/audit.py` | Good schema |
| `backend/app/integrations/llm.py` | Solid LLM integration |
| `backend/app/integrations/storage.py` | Works for S3/local |
| `backend/app/agents/workflows/plan_workflow.py` | Good LangGraph structure |
| `backend/app/worker.py` | Celery config is fine |

---

## Conclusion

SEOman v2.0 represents a complete overhaul from a proof-of-concept to a professional-grade SEO platform. The key changes are:

1. **100x more comprehensive auditing** (3 checks → 100 checks)
2. **Full site crawling** with HTML storage for re-analysis
3. **Complete keyword research** with gap analysis
4. **Professional reports** using Jinja2 templates
5. **AI-powered insights** via LLM integration

The 12-week roadmap is aggressive but achievable with focused development. Each phase builds on the previous, with core infrastructure (crawling) coming first, followed by the audit engine, keyword research, and finally reporting.

---

*Document prepared by SEOman Development Team*  
*Last updated: 2026-01-07*
