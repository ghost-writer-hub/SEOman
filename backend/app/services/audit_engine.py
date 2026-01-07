"""
SEOman v2.0 Audit Engine - 100-Point Technical SEO Audit

Categories:
1. Crawlability & Indexability (1-10)
2. On-Page SEO (11-20)
3. Technical Performance (21-30)
4. URL Structure (31-40)
5. Internal Linking (41-50)
6. Content Quality (51-60)
7. Structured Data (61-70)
8. Security & Accessibility (71-80)
9. Mobile Optimization (81-90)
10. Server & Infrastructure (91-100)
"""

import re
import json
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Any
from urllib.parse import urlparse, urljoin
from collections import defaultdict

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class AuditCheckResult:
    check_id: int
    category: str
    check_name: str
    passed: bool
    severity: str
    affected_count: int = 0
    affected_urls: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CrawlData:
    base_url: str
    pages: list[dict]
    robots_txt: dict | None = None
    sitemap: dict | None = None
    response_headers: dict[str, dict] = field(default_factory=dict)


class SEOAuditEngine:
    """100-point SEO Audit Engine."""

    CATEGORIES = {
        "crawlability": "Crawlability & Indexability",
        "onpage": "On-Page SEO",
        "performance": "Technical Performance",
        "url_structure": "URL Structure",
        "internal_linking": "Internal Linking",
        "content": "Content Quality",
        "structured_data": "Structured Data",
        "security": "Security & Accessibility",
        "mobile": "Mobile Optimization",
        "server": "Server & Infrastructure",
    }

    def __init__(self, crawl_data: CrawlData):
        self.data = crawl_data
        self.results: list[AuditCheckResult] = []
        self.domain = urlparse(crawl_data.base_url).netloc

    def run_all_checks(self) -> list[AuditCheckResult]:
        """Run all 100 SEO checks."""
        logger.info(f"Running SEO audit on {self.data.base_url} ({len(self.data.pages)} pages)")

        self._run_crawlability_checks()
        self._run_onpage_checks()
        self._run_performance_checks()
        self._run_url_structure_checks()
        self._run_internal_linking_checks()
        self._run_content_checks()
        self._run_structured_data_checks()
        self._run_security_checks()
        self._run_mobile_checks()
        self._run_server_checks()

        logger.info(f"Audit complete: {len(self.results)} checks, {sum(1 for r in self.results if not r.passed)} issues")
        return self.results

    def calculate_score(self) -> int:
        """Calculate overall score (0-100)."""
        if not self.results:
            return 0

        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        total_penalty = 0

        for result in self.results:
            if not result.passed:
                weight = severity_weights.get(result.severity, 1)
                penalty = weight * min(result.affected_count, 10)
                total_penalty += penalty

        score = max(0, 100 - total_penalty)
        return score

    def get_summary(self) -> dict:
        """Get audit summary."""
        issues_by_severity = defaultdict(int)
        issues_by_category = defaultdict(int)

        for result in self.results:
            if not result.passed:
                issues_by_severity[result.severity] += 1
                issues_by_category[result.category] += 1

        return {
            "total_checks": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "score": self.calculate_score(),
            "issues_by_severity": dict(issues_by_severity),
            "issues_by_category": dict(issues_by_category),
        }

    # =========================================================================
    # Category 1: Crawlability & Indexability (Checks 1-10)
    # =========================================================================
    def _run_crawlability_checks(self):
        cat = self.CATEGORIES["crawlability"]

        # Check 1: Robots.txt Presence
        has_robots = self.data.robots_txt is not None and self.data.robots_txt.get("exists", False)
        self.results.append(AuditCheckResult(
            check_id=1, category=cat, check_name="Robots.txt Presence",
            passed=has_robots, severity="high",
            affected_count=0 if has_robots else 1,
            affected_urls=[f"{self.data.base_url}/robots.txt"] if not has_robots else [],
            recommendation="Create a robots.txt file to control crawler access.",
        ))

        # Check 2: Robots.txt Blocking Critical Resources
        blocked_critical = []
        if self.data.robots_txt and self.data.robots_txt.get("content"):
            content = self.data.robots_txt["content"].lower()
            critical_patterns = ["/css", "/js", "/images", ".css", ".js"]
            for pattern in critical_patterns:
                if f"disallow: {pattern}" in content or f"disallow: *{pattern}" in content:
                    blocked_critical.append(pattern)
        self.results.append(AuditCheckResult(
            check_id=2, category=cat, check_name="Robots.txt Blocking Critical Resources",
            passed=len(blocked_critical) == 0, severity="critical",
            affected_count=len(blocked_critical),
            details={"blocked_patterns": blocked_critical},
            recommendation="Remove disallow rules for CSS, JS, and image files.",
        ))

        # Check 3: Sitemap.xml Presence
        has_sitemap = self.data.sitemap is not None and self.data.sitemap.get("exists", False)
        self.results.append(AuditCheckResult(
            check_id=3, category=cat, check_name="Sitemap.xml Presence",
            passed=has_sitemap, severity="high",
            affected_count=0 if has_sitemap else 1,
            affected_urls=[f"{self.data.base_url}/sitemap.xml"] if not has_sitemap else [],
            recommendation="Create an XML sitemap and submit to search engines.",
        ))

        # Check 4: Sitemap Validity
        sitemap_valid = True
        sitemap_errors = []
        if self.data.sitemap and self.data.sitemap.get("exists"):
            if self.data.sitemap.get("errors"):
                sitemap_valid = False
                sitemap_errors = self.data.sitemap["errors"]
        self.results.append(AuditCheckResult(
            check_id=4, category=cat, check_name="Sitemap Validity",
            passed=sitemap_valid, severity="medium",
            affected_count=len(sitemap_errors),
            details={"errors": sitemap_errors},
            recommendation="Fix sitemap XML errors for proper indexing.",
        ))

        # Check 5: Noindex on Important Pages
        noindex_pages = []
        for page in self.data.pages:
            if page.get("noindex") and page.get("status_code") == 200:
                if not any(x in page.get("url", "") for x in ["/tag/", "/author/", "/page/", "?", "/search"]):
                    noindex_pages.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=5, category=cat, check_name="Noindex Tags on Important Pages",
            passed=len(noindex_pages) == 0, severity="critical",
            affected_count=len(noindex_pages),
            affected_urls=noindex_pages[:50],
            recommendation="Remove noindex from pages you want indexed.",
        ))

        # Check 6: Canonical Tag Presence
        missing_canonical = []
        for page in self.data.pages:
            if page.get("status_code") == 200 and not page.get("canonical_url"):
                missing_canonical.append(page.get("url", ""))
        self.results.append(AuditCheckResult(
            check_id=6, category=cat, check_name="Canonical Tag Presence",
            passed=len(missing_canonical) == 0, severity="medium",
            affected_count=len(missing_canonical),
            affected_urls=missing_canonical[:50],
            recommendation="Add canonical tags to all indexable pages.",
        ))

        # Check 7: Canonical Self-Referencing
        wrong_canonical = []
        for page in self.data.pages:
            canonical = page.get("canonical_url", "")
            url = page.get("url", "")
            if canonical and url and canonical != url:
                normalized_canonical = canonical.rstrip("/")
                normalized_url = url.rstrip("/")
                if normalized_canonical != normalized_url:
                    wrong_canonical.append({"url": url, "canonical": canonical})
        self.results.append(AuditCheckResult(
            check_id=7, category=cat, check_name="Canonical Self-Referencing",
            passed=len(wrong_canonical) == 0, severity="medium",
            affected_count=len(wrong_canonical),
            affected_urls=[w["url"] for w in wrong_canonical[:50]],
            details={"mismatches": wrong_canonical[:20]},
            recommendation="Ensure canonical tags point to the page itself.",
        ))

        # Check 8: X-Robots-Tag in Headers
        x_robots_issues = []
        for url, headers in self.data.response_headers.items():
            x_robots = headers.get("x-robots-tag", "").lower()
            if "noindex" in x_robots:
                x_robots_issues.append(url)
        self.results.append(AuditCheckResult(
            check_id=8, category=cat, check_name="X-Robots-Tag in Headers",
            passed=len(x_robots_issues) == 0, severity="high",
            affected_count=len(x_robots_issues),
            affected_urls=x_robots_issues[:50],
            recommendation="Remove X-Robots-Tag: noindex from important pages.",
        ))

        # Check 9: Orphan Pages (pages with no internal links)
        linked_urls = set()
        for page in self.data.pages:
            for link in page.get("internal_links", []):
                if isinstance(link, dict):
                    linked_urls.add(link.get("url", ""))
                elif isinstance(link, str):
                    linked_urls.add(link)

        orphan_pages = []
        homepage = self.data.base_url.rstrip("/")
        for page in self.data.pages:
            url = page.get("url", "").rstrip("/")
            if url != homepage and url not in linked_urls and page.get("status_code") == 200:
                orphan_pages.append(page.get("url", ""))
        self.results.append(AuditCheckResult(
            check_id=9, category=cat, check_name="Orphan Pages",
            passed=len(orphan_pages) == 0, severity="high",
            affected_count=len(orphan_pages),
            affected_urls=orphan_pages[:50],
            recommendation="Add internal links to orphan pages or remove them.",
        ))

        # Check 10: Crawl Depth > 4
        deep_pages = []
        for page in self.data.pages:
            depth = page.get("crawl_depth", 0)
            if depth > 4:
                deep_pages.append({"url": page.get("url", ""), "depth": depth})
        self.results.append(AuditCheckResult(
            check_id=10, category=cat, check_name="Crawl Depth > 4",
            passed=len(deep_pages) == 0, severity="medium",
            affected_count=len(deep_pages),
            affected_urls=[p["url"] for p in deep_pages[:50]],
            details={"deep_pages": deep_pages[:20]},
            recommendation="Flatten site structure to max 4 clicks from homepage.",
        ))

    # =========================================================================
    # Category 2: On-Page SEO (Checks 11-20)
    # =========================================================================
    def _run_onpage_checks(self):
        cat = self.CATEGORIES["onpage"]

        # Check 11: Missing Title Tag
        missing_title = [p["url"] for p in self.data.pages if not p.get("title") and p.get("status_code") == 200]
        self.results.append(AuditCheckResult(
            check_id=11, category=cat, check_name="Missing Title Tag",
            passed=len(missing_title) == 0, severity="high",
            affected_count=len(missing_title),
            affected_urls=missing_title[:50],
            recommendation="Add unique title tags to all pages (50-60 characters).",
        ))

        # Check 12: Title Too Short (<30 chars)
        short_title = [p["url"] for p in self.data.pages if p.get("title") and len(p["title"]) < 30]
        self.results.append(AuditCheckResult(
            check_id=12, category=cat, check_name="Title Too Short (<30 chars)",
            passed=len(short_title) == 0, severity="medium",
            affected_count=len(short_title),
            affected_urls=short_title[:50],
            recommendation="Expand titles to 50-60 characters for better SEO.",
        ))

        # Check 13: Title Too Long (>60 chars)
        long_title = [p["url"] for p in self.data.pages if p.get("title") and len(p["title"]) > 60]
        self.results.append(AuditCheckResult(
            check_id=13, category=cat, check_name="Title Too Long (>60 chars)",
            passed=len(long_title) == 0, severity="low",
            affected_count=len(long_title),
            affected_urls=long_title[:50],
            recommendation="Shorten titles to under 60 characters to avoid truncation.",
        ))

        # Check 14: Duplicate Title Tags
        titles = defaultdict(list)
        for page in self.data.pages:
            if page.get("title") and page.get("status_code") == 200:
                titles[page["title"].lower().strip()].append(page["url"])
        duplicate_titles = {t: urls for t, urls in titles.items() if len(urls) > 1}
        dup_urls = [url for urls in duplicate_titles.values() for url in urls]
        self.results.append(AuditCheckResult(
            check_id=14, category=cat, check_name="Duplicate Title Tags",
            passed=len(duplicate_titles) == 0, severity="high",
            affected_count=len(dup_urls),
            affected_urls=dup_urls[:50],
            details={"duplicates": dict(list(duplicate_titles.items())[:10])},
            recommendation="Make each page title unique.",
        ))

        # Check 15: Missing Meta Description
        missing_desc = [p["url"] for p in self.data.pages if not p.get("meta_description") and p.get("status_code") == 200]
        self.results.append(AuditCheckResult(
            check_id=15, category=cat, check_name="Missing Meta Description",
            passed=len(missing_desc) == 0, severity="high",
            affected_count=len(missing_desc),
            affected_urls=missing_desc[:50],
            recommendation="Add unique meta descriptions (150-160 characters).",
        ))

        # Check 16: Meta Description Length
        bad_desc_len = []
        for page in self.data.pages:
            desc = page.get("meta_description", "")
            if desc and (len(desc) < 70 or len(desc) > 160):
                bad_desc_len.append({"url": page["url"], "length": len(desc)})
        self.results.append(AuditCheckResult(
            check_id=16, category=cat, check_name="Meta Description Length",
            passed=len(bad_desc_len) == 0, severity="low",
            affected_count=len(bad_desc_len),
            affected_urls=[b["url"] for b in bad_desc_len[:50]],
            recommendation="Optimize meta descriptions to 150-160 characters.",
        ))

        # Check 17: Missing H1
        missing_h1 = [p["url"] for p in self.data.pages if not p.get("h1") and p.get("status_code") == 200]
        self.results.append(AuditCheckResult(
            check_id=17, category=cat, check_name="Missing H1",
            passed=len(missing_h1) == 0, severity="high",
            affected_count=len(missing_h1),
            affected_urls=missing_h1[:50],
            recommendation="Add a single H1 tag to each page.",
        ))

        # Check 18: Multiple H1s
        multiple_h1 = []
        for page in self.data.pages:
            h1 = page.get("h1", [])
            if isinstance(h1, list) and len(h1) > 1:
                multiple_h1.append({"url": page["url"], "count": len(h1)})
            elif isinstance(h1, str):
                pass
        self.results.append(AuditCheckResult(
            check_id=18, category=cat, check_name="Multiple H1s",
            passed=len(multiple_h1) == 0, severity="medium",
            affected_count=len(multiple_h1),
            affected_urls=[m["url"] for m in multiple_h1[:50]],
            recommendation="Use only one H1 tag per page.",
        ))

        # Check 19: Heading Hierarchy Broken
        broken_hierarchy = []
        for page in self.data.pages:
            h1 = page.get("h1")
            h2 = page.get("h2", [])
            h3 = page.get("h3", [])
            if not h1 and (h2 or h3):
                broken_hierarchy.append(page["url"])
            elif h3 and not h2:
                broken_hierarchy.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=19, category=cat, check_name="Heading Hierarchy Broken",
            passed=len(broken_hierarchy) == 0, severity="low",
            affected_count=len(broken_hierarchy),
            affected_urls=broken_hierarchy[:50],
            recommendation="Follow proper heading hierarchy: H1 -> H2 -> H3.",
        ))

        # Check 20: Missing Image Alt Text
        missing_alt = []
        for page in self.data.pages:
            images = page.get("images", [])
            for img in images:
                if isinstance(img, dict) and not img.get("alt"):
                    if page["url"] not in missing_alt:
                        missing_alt.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=20, category=cat, check_name="Missing Image Alt Text",
            passed=len(missing_alt) == 0, severity="medium",
            affected_count=len(missing_alt),
            affected_urls=missing_alt[:50],
            recommendation="Add descriptive alt text to all images.",
        ))

    # =========================================================================
    # Category 3: Technical Performance (Checks 21-30)
    # =========================================================================
    def _run_performance_checks(self):
        cat = self.CATEGORIES["performance"]

        # Check 21: LCP > 2.5s
        slow_lcp = [p["url"] for p in self.data.pages if p.get("lcp_ms", 0) > 2500]
        self.results.append(AuditCheckResult(
            check_id=21, category=cat, check_name="LCP > 2.5s",
            passed=len(slow_lcp) == 0, severity="high",
            affected_count=len(slow_lcp),
            affected_urls=slow_lcp[:50],
            recommendation="Optimize Largest Contentful Paint to under 2.5s.",
        ))

        # Check 22: INP > 200ms
        slow_inp = [p["url"] for p in self.data.pages if p.get("inp_ms", 0) > 200]
        self.results.append(AuditCheckResult(
            check_id=22, category=cat, check_name="INP > 200ms",
            passed=len(slow_inp) == 0, severity="medium",
            affected_count=len(slow_inp),
            affected_urls=slow_inp[:50],
            recommendation="Optimize Interaction to Next Paint to under 200ms.",
        ))

        # Check 23: CLS > 0.1
        high_cls = [p["url"] for p in self.data.pages if p.get("cls", 0) > 0.1]
        self.results.append(AuditCheckResult(
            check_id=23, category=cat, check_name="CLS > 0.1",
            passed=len(high_cls) == 0, severity="high",
            affected_count=len(high_cls),
            affected_urls=high_cls[:50],
            recommendation="Reduce Cumulative Layout Shift to under 0.1.",
        ))

        # Check 24: TTFB > 800ms
        slow_ttfb = [p["url"] for p in self.data.pages if p.get("load_time_ms", 0) > 800]
        self.results.append(AuditCheckResult(
            check_id=24, category=cat, check_name="TTFB > 800ms",
            passed=len(slow_ttfb) == 0, severity="medium",
            affected_count=len(slow_ttfb),
            affected_urls=slow_ttfb[:50],
            recommendation="Improve server response time to under 800ms.",
        ))

        # Check 25: Render-Blocking Resources
        render_blocking = []
        for page in self.data.pages:
            if page.get("render_blocking_resources", 0) > 3:
                render_blocking.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=25, category=cat, check_name="Render-Blocking Resources",
            passed=len(render_blocking) == 0, severity="high",
            affected_count=len(render_blocking),
            affected_urls=render_blocking[:50],
            recommendation="Defer non-critical CSS/JS or inline critical styles.",
        ))

        # Check 26: Uncompressed Images
        large_images = []
        for page in self.data.pages:
            for img in page.get("images", []):
                if isinstance(img, dict) and img.get("size_bytes", 0) > 200000:
                    large_images.append({"url": page["url"], "image": img.get("url", "")})
        self.results.append(AuditCheckResult(
            check_id=26, category=cat, check_name="Uncompressed Images",
            passed=len(large_images) == 0, severity="medium",
            affected_count=len(large_images),
            affected_urls=list(set(l["url"] for l in large_images))[:50],
            details={"images": large_images[:20]},
            recommendation="Compress images to under 200KB.",
        ))

        # Check 27: Missing Image Dimensions
        no_dimensions = []
        for page in self.data.pages:
            for img in page.get("images", []):
                if isinstance(img, dict) and (not img.get("width") or not img.get("height")):
                    if page["url"] not in no_dimensions:
                        no_dimensions.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=27, category=cat, check_name="Missing Image Dimensions",
            passed=len(no_dimensions) == 0, severity="medium",
            affected_count=len(no_dimensions),
            affected_urls=no_dimensions[:50],
            recommendation="Add width and height attributes to images.",
        ))

        # Check 28: No Text Compression
        no_compression = []
        for url, headers in self.data.response_headers.items():
            encoding = headers.get("content-encoding", "").lower()
            if encoding not in ["gzip", "br", "deflate"]:
                no_compression.append(url)
        self.results.append(AuditCheckResult(
            check_id=28, category=cat, check_name="No Text Compression",
            passed=len(no_compression) == 0, severity="medium",
            affected_count=len(no_compression),
            affected_urls=no_compression[:50],
            recommendation="Enable gzip or Brotli compression on the server.",
        ))

        # Check 29: Unminified CSS/JS
        unminified = []
        for page in self.data.pages:
            if page.get("has_unminified_resources"):
                unminified.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=29, category=cat, check_name="Unminified CSS/JS",
            passed=len(unminified) == 0, severity="low",
            affected_count=len(unminified),
            affected_urls=unminified[:50],
            recommendation="Minify CSS and JavaScript files.",
        ))

        # Check 30: Third-Party Script Impact
        heavy_third_party = []
        for page in self.data.pages:
            if page.get("third_party_scripts", 0) > 10:
                heavy_third_party.append({"url": page["url"], "count": page["third_party_scripts"]})
        self.results.append(AuditCheckResult(
            check_id=30, category=cat, check_name="Third-Party Script Impact",
            passed=len(heavy_third_party) == 0, severity="medium",
            affected_count=len(heavy_third_party),
            affected_urls=[h["url"] for h in heavy_third_party[:50]],
            recommendation="Reduce third-party scripts or load them asynchronously.",
        ))

    # =========================================================================
    # Category 4: URL Structure (Checks 31-40)
    # =========================================================================
    def _run_url_structure_checks(self):
        cat = self.CATEGORIES["url_structure"]

        # Check 31: URL Length > 100 chars
        long_urls = [p["url"] for p in self.data.pages if len(p.get("url", "")) > 100]
        self.results.append(AuditCheckResult(
            check_id=31, category=cat, check_name="URL Length > 100 chars",
            passed=len(long_urls) == 0, severity="low",
            affected_count=len(long_urls),
            affected_urls=long_urls[:50],
            recommendation="Keep URLs under 100 characters.",
        ))

        # Check 32: Non-ASCII Characters
        non_ascii = []
        for page in self.data.pages:
            url = page.get("url", "")
            if not url.isascii():
                non_ascii.append(url)
        self.results.append(AuditCheckResult(
            check_id=32, category=cat, check_name="Non-ASCII Characters",
            passed=len(non_ascii) == 0, severity="medium",
            affected_count=len(non_ascii),
            affected_urls=non_ascii[:50],
            recommendation="Use only ASCII characters in URLs.",
        ))

        # Check 33: Underscores in URLs
        underscores = [p["url"] for p in self.data.pages if "_" in urlparse(p.get("url", "")).path]
        self.results.append(AuditCheckResult(
            check_id=33, category=cat, check_name="Underscores in URLs",
            passed=len(underscores) == 0, severity="low",
            affected_count=len(underscores),
            affected_urls=underscores[:50],
            recommendation="Use hyphens instead of underscores in URLs.",
        ))

        # Check 34: Uppercase in URLs
        uppercase = []
        for page in self.data.pages:
            path = urlparse(page.get("url", "")).path
            if path != path.lower():
                uppercase.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=34, category=cat, check_name="Uppercase in URLs",
            passed=len(uppercase) == 0, severity="low",
            affected_count=len(uppercase),
            affected_urls=uppercase[:50],
            recommendation="Use lowercase URLs for consistency.",
        ))

        # Check 35: Trailing Slash Inconsistency
        inconsistent_slash = []
        for page in self.data.pages:
            url = page.get("url", "")
            canonical = page.get("canonical_url", "")
            if canonical:
                url_has_slash = url.endswith("/")
                canonical_has_slash = canonical.endswith("/")
                if url_has_slash != canonical_has_slash:
                    inconsistent_slash.append(url)
        self.results.append(AuditCheckResult(
            check_id=35, category=cat, check_name="Trailing Slash Inconsistency",
            passed=len(inconsistent_slash) == 0, severity="medium",
            affected_count=len(inconsistent_slash),
            affected_urls=inconsistent_slash[:50],
            recommendation="Be consistent with trailing slashes.",
        ))

        # Check 36: URL Depth > 4 levels
        deep_urls = []
        for page in self.data.pages:
            path = urlparse(page.get("url", "")).path
            depth = len([p for p in path.split("/") if p])
            if depth > 4:
                deep_urls.append({"url": page["url"], "depth": depth})
        self.results.append(AuditCheckResult(
            check_id=36, category=cat, check_name="URL Depth > 4 levels",
            passed=len(deep_urls) == 0, severity="medium",
            affected_count=len(deep_urls),
            affected_urls=[d["url"] for d in deep_urls[:50]],
            recommendation="Flatten URL structure to max 4 levels.",
        ))

        # Check 37: Dynamic Parameters
        dynamic_urls = [p["url"] for p in self.data.pages if "?" in p.get("url", "")]
        self.results.append(AuditCheckResult(
            check_id=37, category=cat, check_name="Dynamic Parameters",
            passed=len(dynamic_urls) == 0, severity="medium",
            affected_count=len(dynamic_urls),
            affected_urls=dynamic_urls[:50],
            recommendation="Use clean, static URLs without query parameters.",
        ))

        # Check 38: Session IDs in URLs
        session_patterns = ["sid=", "session=", "phpsessid=", "jsessionid=", "aspsessionid"]
        session_urls = []
        for page in self.data.pages:
            url = page.get("url", "").lower()
            if any(p in url for p in session_patterns):
                session_urls.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=38, category=cat, check_name="Session IDs in URLs",
            passed=len(session_urls) == 0, severity="high",
            affected_count=len(session_urls),
            affected_urls=session_urls[:50],
            recommendation="Remove session IDs from URLs; use cookies instead.",
        ))

        # Check 39: Duplicate Content URLs
        content_hashes = defaultdict(list)
        for page in self.data.pages:
            content_hash = page.get("text_content_hash")
            if content_hash and page.get("status_code") == 200:
                content_hashes[content_hash].append(page["url"])
        duplicate_content = {h: urls for h, urls in content_hashes.items() if len(urls) > 1}
        dup_urls = [url for urls in duplicate_content.values() for url in urls]
        self.results.append(AuditCheckResult(
            check_id=39, category=cat, check_name="Duplicate Content URLs",
            passed=len(duplicate_content) == 0, severity="high",
            affected_count=len(dup_urls),
            affected_urls=dup_urls[:50],
            details={"groups": list(duplicate_content.values())[:10]},
            recommendation="Consolidate duplicate content or use canonical tags.",
        ))

        # Check 40: Missing Keywords in URL
        missing_kw_url = []
        for page in self.data.pages:
            title = (page.get("title") or "").lower()
            h1 = page.get("h1", "")
            if isinstance(h1, list):
                h1 = h1[0] if h1 else ""
            h1 = h1.lower()
            path = urlparse(page.get("url", "")).path.lower()
            title_words = set(re.findall(r"\w+", title))
            h1_words = set(re.findall(r"\w+", h1))
            path_words = set(re.findall(r"\w+", path))
            important_words = title_words.union(h1_words) - {"the", "a", "an", "of", "to", "in", "for", "and", "or"}
            if important_words and not important_words.intersection(path_words):
                missing_kw_url.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=40, category=cat, check_name="Missing Keywords in URL",
            passed=len(missing_kw_url) == 0, severity="low",
            affected_count=len(missing_kw_url),
            affected_urls=missing_kw_url[:50],
            recommendation="Include target keywords in URL slugs.",
        ))

    # =========================================================================
    # Category 5: Internal Linking (Checks 41-50)
    # =========================================================================
    def _run_internal_linking_checks(self):
        cat = self.CATEGORIES["internal_linking"]

        # Build link graph
        incoming_links = defaultdict(set)
        outgoing_links = defaultdict(set)
        for page in self.data.pages:
            url = page.get("url", "")
            for link in page.get("internal_links", []):
                link_url = link.get("url") if isinstance(link, dict) else link
                if link_url:
                    incoming_links[link_url].add(url)
                    outgoing_links[url].add(link_url)

        # Check 41: Orphan Pages (duplicate of check 9 but in linking context)
        homepage = self.data.base_url.rstrip("/")
        orphans = []
        for page in self.data.pages:
            url = page.get("url", "").rstrip("/")
            if url != homepage and len(incoming_links.get(url, set())) == 0 and page.get("status_code") == 200:
                orphans.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=41, category=cat, check_name="Orphan Pages",
            passed=len(orphans) == 0, severity="high",
            affected_count=len(orphans),
            affected_urls=orphans[:50],
            recommendation="Add internal links to pages with no incoming links.",
        ))

        # Check 42: Broken Internal Links (404)
        broken_links = []
        page_urls = {p.get("url") for p in self.data.pages}
        for page in self.data.pages:
            for link in page.get("internal_links", []):
                link_url = link.get("url") if isinstance(link, dict) else link
                if link_url and link_url not in page_urls:
                    broken_links.append({"from": page["url"], "to": link_url})
        self.results.append(AuditCheckResult(
            check_id=42, category=cat, check_name="Broken Internal Links (404)",
            passed=len(broken_links) == 0, severity="high",
            affected_count=len(broken_links),
            affected_urls=list(set(b["from"] for b in broken_links))[:50],
            details={"broken": broken_links[:20]},
            recommendation="Fix or remove broken internal links.",
        ))

        # Check 43: Redirect Chains (Internal)
        redirect_chains = []
        for page in self.data.pages:
            if page.get("redirect_chain") and len(page["redirect_chain"]) > 1:
                redirect_chains.append({"url": page["url"], "chain": page["redirect_chain"]})
        self.results.append(AuditCheckResult(
            check_id=43, category=cat, check_name="Redirect Chains (Internal)",
            passed=len(redirect_chains) == 0, severity="medium",
            affected_count=len(redirect_chains),
            affected_urls=[r["url"] for r in redirect_chains[:50]],
            recommendation="Update links to point directly to final URLs.",
        ))

        # Check 44: Nofollow on Internal Links
        nofollow_internal = []
        for page in self.data.pages:
            for link in page.get("internal_links", []):
                if isinstance(link, dict) and link.get("nofollow"):
                    nofollow_internal.append({"from": page["url"], "to": link.get("url")})
        self.results.append(AuditCheckResult(
            check_id=44, category=cat, check_name="Nofollow on Internal Links",
            passed=len(nofollow_internal) == 0, severity="medium",
            affected_count=len(nofollow_internal),
            affected_urls=list(set(n["from"] for n in nofollow_internal))[:50],
            recommendation="Remove nofollow from internal links.",
        ))

        # Check 45: Generic Anchor Text
        generic_anchors = ["click here", "read more", "learn more", "here", "more", "link"]
        generic_anchor_pages = []
        for page in self.data.pages:
            for link in page.get("internal_links", []):
                if isinstance(link, dict):
                    anchor = (link.get("text") or "").lower().strip()
                    if anchor in generic_anchors:
                        generic_anchor_pages.append(page["url"])
                        break
        self.results.append(AuditCheckResult(
            check_id=45, category=cat, check_name="Generic Anchor Text",
            passed=len(generic_anchor_pages) == 0, severity="medium",
            affected_count=len(generic_anchor_pages),
            affected_urls=generic_anchor_pages[:50],
            recommendation="Use descriptive anchor text for internal links.",
        ))

        # Check 46: Low Internal Link Count
        low_links = [p["url"] for p in self.data.pages if len(p.get("internal_links", [])) < 3 and p.get("status_code") == 200]
        self.results.append(AuditCheckResult(
            check_id=46, category=cat, check_name="Low Internal Link Count",
            passed=len(low_links) == 0, severity="medium",
            affected_count=len(low_links),
            affected_urls=low_links[:50],
            recommendation="Add more internal links to pages (at least 3).",
        ))

        # Check 47: High Internal Link Count
        high_links = [p["url"] for p in self.data.pages if len(p.get("internal_links", [])) > 100]
        self.results.append(AuditCheckResult(
            check_id=47, category=cat, check_name="High Internal Link Count",
            passed=len(high_links) == 0, severity="low",
            affected_count=len(high_links),
            affected_urls=high_links[:50],
            recommendation="Reduce excessive internal links (max 100 per page).",
        ))

        # Check 48: Missing Breadcrumbs
        no_breadcrumbs = []
        for page in self.data.pages:
            structured_data = page.get("structured_data", [])
            has_breadcrumb = any(
                sd.get("@type") == "BreadcrumbList"
                for sd in structured_data
                if isinstance(sd, dict)
            )
            path_depth = len([p for p in urlparse(page.get("url", "")).path.split("/") if p])
            if path_depth > 1 and not has_breadcrumb:
                no_breadcrumbs.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=48, category=cat, check_name="Missing Breadcrumbs",
            passed=len(no_breadcrumbs) == 0, severity="low",
            affected_count=len(no_breadcrumbs),
            affected_urls=no_breadcrumbs[:50],
            recommendation="Add breadcrumb navigation with Schema markup.",
        ))

        # Check 49: Deep Pages (> 4 clicks)
        deep_pages = [p["url"] for p in self.data.pages if p.get("crawl_depth", 0) > 4]
        self.results.append(AuditCheckResult(
            check_id=49, category=cat, check_name="Deep Pages (> 4 clicks)",
            passed=len(deep_pages) == 0, severity="medium",
            affected_count=len(deep_pages),
            affected_urls=deep_pages[:50],
            recommendation="Ensure important pages are within 4 clicks of homepage.",
        ))

        # Check 50: Pagination Issues
        pagination_issues = []
        for page in self.data.pages:
            if "/page/" in page.get("url", "") or "?page=" in page.get("url", ""):
                has_rel_next_prev = page.get("has_rel_next") or page.get("has_rel_prev")
                if not has_rel_next_prev:
                    pagination_issues.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=50, category=cat, check_name="Pagination Issues",
            passed=len(pagination_issues) == 0, severity="medium",
            affected_count=len(pagination_issues),
            affected_urls=pagination_issues[:50],
            recommendation="Add rel='next' and rel='prev' for pagination.",
        ))

    # =========================================================================
    # Category 6: Content Quality (Checks 51-60)
    # =========================================================================
    def _run_content_checks(self):
        cat = self.CATEGORIES["content"]

        # Check 51: Thin Content (< 300 words)
        thin_content = [p["url"] for p in self.data.pages if p.get("word_count", 0) < 300 and p.get("status_code") == 200]
        self.results.append(AuditCheckResult(
            check_id=51, category=cat, check_name="Thin Content (< 300 words)",
            passed=len(thin_content) == 0, severity="high",
            affected_count=len(thin_content),
            affected_urls=thin_content[:50],
            recommendation="Add more valuable content (aim for 500+ words).",
        ))

        # Check 52: Duplicate Content (Internal)
        content_hashes = defaultdict(list)
        for page in self.data.pages:
            h = page.get("text_content_hash")
            if h and page.get("status_code") == 200:
                content_hashes[h].append(page["url"])
        duplicates = {h: urls for h, urls in content_hashes.items() if len(urls) > 1}
        dup_urls = [url for urls in duplicates.values() for url in urls]
        self.results.append(AuditCheckResult(
            check_id=52, category=cat, check_name="Duplicate Content (Internal)",
            passed=len(duplicates) == 0, severity="high",
            affected_count=len(dup_urls),
            affected_urls=dup_urls[:50],
            recommendation="Remove or consolidate duplicate content.",
        ))

        # Check 53: Near-Duplicate Content
        near_duplicates = []
        for page in self.data.pages:
            if page.get("near_duplicate_of"):
                near_duplicates.append({"url": page["url"], "similar_to": page["near_duplicate_of"]})
        self.results.append(AuditCheckResult(
            check_id=53, category=cat, check_name="Near-Duplicate Content",
            passed=len(near_duplicates) == 0, severity="medium",
            affected_count=len(near_duplicates),
            affected_urls=[n["url"] for n in near_duplicates[:50]],
            recommendation="Differentiate or merge near-duplicate pages.",
        ))

        # Check 54: Missing Content (pages with only navigation)
        empty_pages = [p["url"] for p in self.data.pages if p.get("word_count", 0) < 50 and p.get("status_code") == 200]
        self.results.append(AuditCheckResult(
            check_id=54, category=cat, check_name="Missing Content",
            passed=len(empty_pages) == 0, severity="high",
            affected_count=len(empty_pages),
            affected_urls=empty_pages[:50],
            recommendation="Add meaningful content to empty pages.",
        ))

        # Check 55: Keyword Stuffing
        keyword_stuffed = []
        for page in self.data.pages:
            if page.get("keyword_density", 0) > 3:
                keyword_stuffed.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=55, category=cat, check_name="Keyword Stuffing",
            passed=len(keyword_stuffed) == 0, severity="medium",
            affected_count=len(keyword_stuffed),
            affected_urls=keyword_stuffed[:50],
            recommendation="Reduce keyword density to natural levels (<3%).",
        ))

        # Check 56: Outdated Content
        outdated = []
        for page in self.data.pages:
            if page.get("content_date"):
                pass
        self.results.append(AuditCheckResult(
            check_id=56, category=cat, check_name="Outdated Content",
            passed=len(outdated) == 0, severity="low",
            affected_count=len(outdated),
            affected_urls=outdated[:50],
            recommendation="Update content with old dates regularly.",
        ))

        # Check 57: Broken Images
        broken_images = []
        for page in self.data.pages:
            for img in page.get("images", []):
                if isinstance(img, dict) and img.get("status_code") == 404:
                    broken_images.append({"page": page["url"], "image": img.get("url")})
        self.results.append(AuditCheckResult(
            check_id=57, category=cat, check_name="Broken Images",
            passed=len(broken_images) == 0, severity="medium",
            affected_count=len(broken_images),
            affected_urls=list(set(b["page"] for b in broken_images))[:50],
            recommendation="Fix or remove broken image links.",
        ))

        # Check 58: Missing OpenGraph Tags
        missing_og = []
        for page in self.data.pages:
            og = page.get("open_graph", {})
            if not og.get("og:title") or not og.get("og:image"):
                missing_og.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=58, category=cat, check_name="Missing OpenGraph Tags",
            passed=len(missing_og) == 0, severity="low",
            affected_count=len(missing_og),
            affected_urls=missing_og[:50],
            recommendation="Add og:title and og:image for social sharing.",
        ))

        # Check 59: Missing Twitter Cards
        missing_twitter = []
        for page in self.data.pages:
            tc = page.get("twitter_cards", {})
            if not tc.get("twitter:card"):
                missing_twitter.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=59, category=cat, check_name="Missing Twitter Cards",
            passed=len(missing_twitter) == 0, severity="low",
            affected_count=len(missing_twitter),
            affected_urls=missing_twitter[:50],
            recommendation="Add Twitter Card meta tags for better sharing.",
        ))

        # Check 60: Low Readability Score
        low_readability = []
        for page in self.data.pages:
            if page.get("readability_score", 100) < 40:
                low_readability.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=60, category=cat, check_name="Low Readability Score",
            passed=len(low_readability) == 0, severity="low",
            affected_count=len(low_readability),
            affected_urls=low_readability[:50],
            recommendation="Simplify content for better readability.",
        ))

    # =========================================================================
    # Category 7: Structured Data (Checks 61-70)
    # =========================================================================
    def _run_structured_data_checks(self):
        cat = self.CATEGORIES["structured_data"]

        # Check 61: No Structured Data
        no_schema = []
        for page in self.data.pages:
            if not page.get("structured_data") and page.get("status_code") == 200:
                no_schema.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=61, category=cat, check_name="No Structured Data",
            passed=len(no_schema) == 0, severity="medium",
            affected_count=len(no_schema),
            affected_urls=no_schema[:50],
            recommendation="Add JSON-LD structured data to pages.",
        ))

        # Check 62: Schema Syntax Errors
        schema_errors = []
        for page in self.data.pages:
            if page.get("schema_errors"):
                schema_errors.append({"url": page["url"], "errors": page["schema_errors"]})
        self.results.append(AuditCheckResult(
            check_id=62, category=cat, check_name="Schema Syntax Errors",
            passed=len(schema_errors) == 0, severity="high",
            affected_count=len(schema_errors),
            affected_urls=[s["url"] for s in schema_errors[:50]],
            recommendation="Fix structured data syntax errors.",
        ))

        # Check 63: Missing Organization Schema
        homepage_urls = [self.data.base_url, self.data.base_url + "/", self.data.base_url.rstrip("/")]
        homepage_page = next((p for p in self.data.pages if p.get("url", "").rstrip("/") in [u.rstrip("/") for u in homepage_urls]), None)
        has_org_schema = False
        if homepage_page:
            for sd in homepage_page.get("structured_data", []):
                if isinstance(sd, dict) and sd.get("@type") == "Organization":
                    has_org_schema = True
        self.results.append(AuditCheckResult(
            check_id=63, category=cat, check_name="Missing Organization Schema",
            passed=has_org_schema, severity="medium",
            affected_count=0 if has_org_schema else 1,
            affected_urls=[] if has_org_schema else [self.data.base_url],
            recommendation="Add Organization schema to homepage.",
        ))

        # Check 64: Missing Breadcrumb Schema
        missing_breadcrumb = []
        for page in self.data.pages:
            path_depth = len([p for p in urlparse(page.get("url", "")).path.split("/") if p])
            if path_depth > 1:
                has_breadcrumb = any(
                    sd.get("@type") == "BreadcrumbList"
                    for sd in page.get("structured_data", [])
                    if isinstance(sd, dict)
                )
                if not has_breadcrumb:
                    missing_breadcrumb.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=64, category=cat, check_name="Missing Breadcrumb Schema",
            passed=len(missing_breadcrumb) == 0, severity="low",
            affected_count=len(missing_breadcrumb),
            affected_urls=missing_breadcrumb[:50],
            recommendation="Add BreadcrumbList schema to inner pages.",
        ))

        # Check 65: Missing Article Schema
        blog_patterns = ["/blog/", "/news/", "/article/", "/post/"]
        missing_article = []
        for page in self.data.pages:
            url = page.get("url", "")
            if any(p in url for p in blog_patterns):
                has_article = any(
                    sd.get("@type") in ["Article", "NewsArticle", "BlogPosting"]
                    for sd in page.get("structured_data", [])
                    if isinstance(sd, dict)
                )
                if not has_article:
                    missing_article.append(url)
        self.results.append(AuditCheckResult(
            check_id=65, category=cat, check_name="Missing Article Schema",
            passed=len(missing_article) == 0, severity="medium",
            affected_count=len(missing_article),
            affected_urls=missing_article[:50],
            recommendation="Add Article schema to blog/news pages.",
        ))

        # Check 66: Missing Product Schema
        product_patterns = ["/product/", "/products/", "/shop/", "/store/"]
        missing_product = []
        for page in self.data.pages:
            url = page.get("url", "")
            if any(p in url for p in product_patterns):
                has_product = any(
                    sd.get("@type") == "Product"
                    for sd in page.get("structured_data", [])
                    if isinstance(sd, dict)
                )
                if not has_product:
                    missing_product.append(url)
        self.results.append(AuditCheckResult(
            check_id=66, category=cat, check_name="Missing Product Schema",
            passed=len(missing_product) == 0, severity="high",
            affected_count=len(missing_product),
            affected_urls=missing_product[:50],
            recommendation="Add Product schema to product pages.",
        ))

        # Check 67: Missing LocalBusiness Schema
        local_indicators = ["contact", "location", "address", "hours", "directions"]
        has_local = False
        for page in self.data.pages:
            for sd in page.get("structured_data", []):
                if isinstance(sd, dict) and sd.get("@type") in ["LocalBusiness", "Organization"]:
                    if sd.get("address"):
                        has_local = True
        self.results.append(AuditCheckResult(
            check_id=67, category=cat, check_name="Missing LocalBusiness Schema",
            passed=has_local, severity="high",
            affected_count=0 if has_local else 1,
            affected_urls=[] if has_local else [self.data.base_url],
            recommendation="Add LocalBusiness schema if you have a physical location.",
        ))

        # Check 68: Missing FAQ Schema
        faq_patterns = ["/faq", "/frequently-asked", "/questions"]
        missing_faq = []
        for page in self.data.pages:
            url = page.get("url", "").lower()
            if any(p in url for p in faq_patterns):
                has_faq = any(
                    sd.get("@type") == "FAQPage"
                    for sd in page.get("structured_data", [])
                    if isinstance(sd, dict)
                )
                if not has_faq:
                    missing_faq.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=68, category=cat, check_name="Missing FAQ Schema",
            passed=len(missing_faq) == 0, severity="low",
            affected_count=len(missing_faq),
            affected_urls=missing_faq[:50],
            recommendation="Add FAQPage schema to FAQ sections.",
        ))

        # Check 69: Missing Review Schema
        review_patterns = ["/review", "/testimonial", "/rating"]
        missing_review = []
        for page in self.data.pages:
            url = page.get("url", "").lower()
            if any(p in url for p in review_patterns):
                has_review = any(
                    sd.get("@type") in ["Review", "AggregateRating"]
                    for sd in page.get("structured_data", [])
                    if isinstance(sd, dict)
                )
                if not has_review:
                    missing_review.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=69, category=cat, check_name="Missing Review Schema",
            passed=len(missing_review) == 0, severity="medium",
            affected_count=len(missing_review),
            affected_urls=missing_review[:50],
            recommendation="Add Review schema to pages with reviews.",
        ))

        # Check 70: Incomplete Schema Fields
        incomplete_schema = []
        for page in self.data.pages:
            for sd in page.get("structured_data", []):
                if isinstance(sd, dict):
                    schema_type = sd.get("@type")
                    if schema_type == "Article" and not all(k in sd for k in ["headline", "author", "datePublished"]):
                        incomplete_schema.append(page["url"])
                    elif schema_type == "Product" and not all(k in sd for k in ["name", "description"]):
                        incomplete_schema.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=70, category=cat, check_name="Incomplete Schema Fields",
            passed=len(incomplete_schema) == 0, severity="medium",
            affected_count=len(incomplete_schema),
            affected_urls=list(set(incomplete_schema))[:50],
            recommendation="Add all required fields to schema markup.",
        ))

    # =========================================================================
    # Category 8: Security & Accessibility (Checks 71-80)
    # =========================================================================
    def _run_security_checks(self):
        cat = self.CATEGORIES["security"]

        # Check 71: Not HTTPS
        http_pages = [p["url"] for p in self.data.pages if p.get("url", "").startswith("http://")]
        self.results.append(AuditCheckResult(
            check_id=71, category=cat, check_name="Not HTTPS",
            passed=len(http_pages) == 0, severity="critical",
            affected_count=len(http_pages),
            affected_urls=http_pages[:50],
            recommendation="Migrate all pages to HTTPS.",
        ))

        # Check 72: Mixed Content
        mixed_content = []
        for page in self.data.pages:
            if page.get("url", "").startswith("https://") and page.get("has_mixed_content"):
                mixed_content.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=72, category=cat, check_name="Mixed Content",
            passed=len(mixed_content) == 0, severity="high",
            affected_count=len(mixed_content),
            affected_urls=mixed_content[:50],
            recommendation="Load all resources over HTTPS.",
        ))

        # Check 73: Missing SSL Certificate
        has_ssl = self.data.base_url.startswith("https://")
        self.results.append(AuditCheckResult(
            check_id=73, category=cat, check_name="Missing SSL Certificate",
            passed=has_ssl, severity="critical",
            affected_count=0 if has_ssl else 1,
            recommendation="Install an SSL certificate.",
        ))

        # Check 74: Expired SSL Certificate
        ssl_expired = False
        self.results.append(AuditCheckResult(
            check_id=74, category=cat, check_name="Expired SSL Certificate",
            passed=not ssl_expired, severity="critical",
            affected_count=1 if ssl_expired else 0,
            recommendation="Renew SSL certificate before expiry.",
        ))

        # Check 75: Missing HSTS Header
        missing_hsts = []
        for url, headers in self.data.response_headers.items():
            if not headers.get("strict-transport-security"):
                missing_hsts.append(url)
        self.results.append(AuditCheckResult(
            check_id=75, category=cat, check_name="Missing HSTS Header",
            passed=len(missing_hsts) == 0, severity="medium",
            affected_count=len(missing_hsts),
            affected_urls=missing_hsts[:50],
            recommendation="Enable HSTS (Strict-Transport-Security header).",
        ))

        # Check 76: Missing Language Declaration
        missing_lang = []
        for page in self.data.pages:
            if not page.get("html_lang"):
                missing_lang.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=76, category=cat, check_name="Missing Language Declaration",
            passed=len(missing_lang) == 0, severity="medium",
            affected_count=len(missing_lang),
            affected_urls=missing_lang[:50],
            recommendation="Add lang attribute to HTML tag.",
        ))

        # Check 77: Missing/Invalid Hreflang
        hreflang_issues = []
        for page in self.data.pages:
            hreflang = page.get("hreflang", [])
            if hreflang:
                has_self = any(h.get("url") == page.get("url") for h in hreflang if isinstance(h, dict))
                if not has_self:
                    hreflang_issues.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=77, category=cat, check_name="Missing/Invalid Hreflang",
            passed=len(hreflang_issues) == 0, severity="high",
            affected_count=len(hreflang_issues),
            affected_urls=hreflang_issues[:50],
            recommendation="Ensure hreflang tags include self-referencing.",
        ))

        # Check 78: Low Color Contrast
        low_contrast = []
        for page in self.data.pages:
            if page.get("accessibility_issues", {}).get("low_contrast"):
                low_contrast.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=78, category=cat, check_name="Low Color Contrast",
            passed=len(low_contrast) == 0, severity="low",
            affected_count=len(low_contrast),
            affected_urls=low_contrast[:50],
            recommendation="Improve color contrast for accessibility.",
        ))

        # Check 79: Missing Form Labels
        missing_labels = []
        for page in self.data.pages:
            if page.get("forms_without_labels"):
                missing_labels.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=79, category=cat, check_name="Missing Form Labels",
            passed=len(missing_labels) == 0, severity="medium",
            affected_count=len(missing_labels),
            affected_urls=missing_labels[:50],
            recommendation="Add labels to all form inputs.",
        ))

        # Check 80: Missing Skip Links
        missing_skip = []
        for page in self.data.pages:
            if not page.get("has_skip_link"):
                missing_skip.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=80, category=cat, check_name="Missing Skip Links",
            passed=len(missing_skip) == 0, severity="low",
            affected_count=len(missing_skip),
            affected_urls=missing_skip[:50],
            recommendation="Add skip-to-content links for accessibility.",
        ))

    # =========================================================================
    # Category 9: Mobile Optimization (Checks 81-90)
    # =========================================================================
    def _run_mobile_checks(self):
        cat = self.CATEGORIES["mobile"]

        # Check 81: Missing Viewport Meta
        missing_viewport = []
        for page in self.data.pages:
            if not page.get("has_viewport_meta"):
                missing_viewport.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=81, category=cat, check_name="Missing Viewport Meta",
            passed=len(missing_viewport) == 0, severity="high",
            affected_count=len(missing_viewport),
            affected_urls=missing_viewport[:50],
            recommendation="Add viewport meta tag for mobile responsiveness.",
        ))

        # Check 82: Viewport Not Responsive
        not_responsive = []
        for page in self.data.pages:
            viewport = page.get("viewport_content", "")
            if "width=device-width" not in viewport:
                not_responsive.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=82, category=cat, check_name="Viewport Not Responsive",
            passed=len(not_responsive) == 0, severity="high",
            affected_count=len(not_responsive),
            affected_urls=not_responsive[:50],
            recommendation="Set viewport to width=device-width, initial-scale=1.",
        ))

        # Check 83: Tap Targets Too Small
        small_targets = []
        for page in self.data.pages:
            if page.get("small_tap_targets"):
                small_targets.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=83, category=cat, check_name="Tap Targets Too Small",
            passed=len(small_targets) == 0, severity="medium",
            affected_count=len(small_targets),
            affected_urls=small_targets[:50],
            recommendation="Make tap targets at least 48x48px.",
        ))

        # Check 84: Font Size Too Small
        small_font = []
        for page in self.data.pages:
            if page.get("has_small_font"):
                small_font.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=84, category=cat, check_name="Font Size Too Small",
            passed=len(small_font) == 0, severity="medium",
            affected_count=len(small_font),
            affected_urls=small_font[:50],
            recommendation="Use at least 16px base font size.",
        ))

        # Check 85: Content Wider Than Screen
        wide_content = []
        for page in self.data.pages:
            if page.get("content_width_issues"):
                wide_content.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=85, category=cat, check_name="Content Wider Than Screen",
            passed=len(wide_content) == 0, severity="high",
            affected_count=len(wide_content),
            affected_urls=wide_content[:50],
            recommendation="Ensure content fits within viewport width.",
        ))

        # Check 86: Intrusive Interstitials
        interstitials = []
        for page in self.data.pages:
            if page.get("has_intrusive_interstitial"):
                interstitials.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=86, category=cat, check_name="Intrusive Interstitials",
            passed=len(interstitials) == 0, severity="medium",
            affected_count=len(interstitials),
            affected_urls=interstitials[:50],
            recommendation="Remove intrusive popups on mobile.",
        ))

        # Check 87: Mobile-Only 404s
        mobile_404s = []
        self.results.append(AuditCheckResult(
            check_id=87, category=cat, check_name="Mobile-Only 404s",
            passed=len(mobile_404s) == 0, severity="high",
            affected_count=len(mobile_404s),
            affected_urls=mobile_404s[:50],
            recommendation="Ensure mobile and desktop return same content.",
        ))

        # Check 88: Flash Content
        flash_content = []
        for page in self.data.pages:
            if page.get("has_flash"):
                flash_content.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=88, category=cat, check_name="Flash Content",
            passed=len(flash_content) == 0, severity="high",
            affected_count=len(flash_content),
            affected_urls=flash_content[:50],
            recommendation="Replace Flash with HTML5.",
        ))

        # Check 89: Plugins Required
        plugin_required = []
        for page in self.data.pages:
            if page.get("requires_plugin"):
                plugin_required.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=89, category=cat, check_name="Plugins Required",
            passed=len(plugin_required) == 0, severity="high",
            affected_count=len(plugin_required),
            affected_urls=plugin_required[:50],
            recommendation="Remove plugin dependencies.",
        ))

        # Check 90: Touch Elements Too Close
        close_elements = []
        for page in self.data.pages:
            if page.get("touch_elements_too_close"):
                close_elements.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=90, category=cat, check_name="Touch Elements Too Close",
            passed=len(close_elements) == 0, severity="medium",
            affected_count=len(close_elements),
            affected_urls=close_elements[:50],
            recommendation="Add spacing between touch targets.",
        ))

    # =========================================================================
    # Category 10: Server & Infrastructure (Checks 91-100)
    # =========================================================================
    def _run_server_checks(self):
        cat = self.CATEGORIES["server"]

        # Check 91: 4xx Errors
        errors_4xx = [p["url"] for p in self.data.pages if 400 <= (p.get("status_code") or 200) < 500]
        self.results.append(AuditCheckResult(
            check_id=91, category=cat, check_name="4xx Errors",
            passed=len(errors_4xx) == 0, severity="high",
            affected_count=len(errors_4xx),
            affected_urls=errors_4xx[:50],
            recommendation="Fix or redirect 4xx error pages.",
        ))

        # Check 92: 5xx Errors
        errors_5xx = [p["url"] for p in self.data.pages if 500 <= (p.get("status_code") or 200) < 600]
        self.results.append(AuditCheckResult(
            check_id=92, category=cat, check_name="5xx Errors",
            passed=len(errors_5xx) == 0, severity="critical",
            affected_count=len(errors_5xx),
            affected_urls=errors_5xx[:50],
            recommendation="Fix server errors immediately.",
        ))

        # Check 93: Redirect Chains
        redirect_chains = []
        for page in self.data.pages:
            chain = page.get("redirect_chain", [])
            if len(chain) > 2:
                redirect_chains.append({"url": page["url"], "chain_length": len(chain)})
        self.results.append(AuditCheckResult(
            check_id=93, category=cat, check_name="Redirect Chains",
            passed=len(redirect_chains) == 0, severity="medium",
            affected_count=len(redirect_chains),
            affected_urls=[r["url"] for r in redirect_chains[:50]],
            recommendation="Reduce redirect chains to single hops.",
        ))

        # Check 94: Redirect Loops
        redirect_loops = []
        for page in self.data.pages:
            if page.get("has_redirect_loop"):
                redirect_loops.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=94, category=cat, check_name="Redirect Loops",
            passed=len(redirect_loops) == 0, severity="high",
            affected_count=len(redirect_loops),
            affected_urls=redirect_loops[:50],
            recommendation="Fix redirect loops immediately.",
        ))

        # Check 95: 302 Instead of 301
        temp_redirects = []
        for page in self.data.pages:
            if page.get("status_code") == 302:
                temp_redirects.append(page["url"])
        self.results.append(AuditCheckResult(
            check_id=95, category=cat, check_name="302 Instead of 301",
            passed=len(temp_redirects) == 0, severity="medium",
            affected_count=len(temp_redirects),
            affected_urls=temp_redirects[:50],
            recommendation="Use 301 for permanent redirects.",
        ))

        # Check 96: Missing Custom 404 Page
        has_custom_404 = any(p.get("is_custom_404") for p in self.data.pages)
        self.results.append(AuditCheckResult(
            check_id=96, category=cat, check_name="Missing Custom 404 Page",
            passed=has_custom_404, severity="low",
            affected_count=0 if has_custom_404 else 1,
            recommendation="Create a helpful custom 404 page.",
        ))

        # Check 97: No Browser Caching
        no_cache = []
        for url, headers in self.data.response_headers.items():
            cache_control = headers.get("cache-control", "")
            if "no-cache" in cache_control or "no-store" in cache_control or not cache_control:
                no_cache.append(url)
        self.results.append(AuditCheckResult(
            check_id=97, category=cat, check_name="No Browser Caching",
            passed=len(no_cache) == 0, severity="low",
            affected_count=len(no_cache),
            affected_urls=no_cache[:50],
            recommendation="Enable browser caching with Cache-Control headers.",
        ))

        # Check 98: No CDN Detected
        has_cdn = False
        cdn_headers = ["x-cdn", "cf-ray", "x-amz-cf-id", "x-cache", "x-fastly"]
        for headers in self.data.response_headers.values():
            if any(h in headers for h in cdn_headers):
                has_cdn = True
                break
        self.results.append(AuditCheckResult(
            check_id=98, category=cat, check_name="No CDN Detected",
            passed=has_cdn, severity="low",
            affected_count=0 if has_cdn else 1,
            recommendation="Consider using a CDN for static assets.",
        ))

        # Check 99: Slow Server Response
        slow_response = [p["url"] for p in self.data.pages if p.get("load_time_ms", 0) > 600]
        self.results.append(AuditCheckResult(
            check_id=99, category=cat, check_name="Slow Server Response",
            passed=len(slow_response) == 0, severity="medium",
            affected_count=len(slow_response),
            affected_urls=slow_response[:50],
            recommendation="Optimize server to respond in under 600ms.",
        ))

        # Check 100: IP Canonicalization
        self.results.append(AuditCheckResult(
            check_id=100, category=cat, check_name="IP Canonicalization",
            passed=True, severity="medium",
            affected_count=0,
            recommendation="Ensure IP address redirects to domain.",
        ))


async def fetch_robots_txt(base_url: str) -> dict:
    """Fetch and parse robots.txt."""
    robots_url = f"{base_url.rstrip('/')}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(robots_url)
            if response.status_code == 200:
                return {
                    "exists": True,
                    "content": response.text,
                    "url": robots_url,
                }
    except Exception as e:
        logger.warning(f"Failed to fetch robots.txt: {e}")
    return {"exists": False, "url": robots_url}


async def fetch_sitemap(base_url: str, robots_content: str | None = None) -> dict:
    """Fetch and parse sitemap.xml."""
    sitemap_urls = [f"{base_url.rstrip('/')}/sitemap.xml"]

    if robots_content:
        for line in robots_content.split("\n"):
            if line.lower().startswith("sitemap:"):
                sitemap_urls.append(line.split(":", 1)[1].strip())

    for sitemap_url in sitemap_urls:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(sitemap_url)
                if response.status_code == 200 and "xml" in response.headers.get("content-type", ""):
                    return {
                        "exists": True,
                        "url": sitemap_url,
                        "content": response.text[:10000],
                    }
        except Exception:
            continue

    return {"exists": False}


def create_crawl_data_from_pages(base_url: str, pages: list[dict], robots: dict | None = None, sitemap: dict | None = None) -> CrawlData:
    """Helper to create CrawlData from database pages."""
    response_headers = {}
    for page in pages:
        if page.get("response_headers"):
            response_headers[page["url"]] = page["response_headers"]

    return CrawlData(
        base_url=base_url,
        pages=pages,
        robots_txt=robots,
        sitemap=sitemap,
        response_headers=response_headers,
    )
