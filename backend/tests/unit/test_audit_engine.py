"""
Unit tests for SEOman Audit Engine.

Tests the 100-point SEO audit engine covering all 10 categories:
1. Crawlability & Indexability
2. On-Page SEO
3. Technical Performance
4. URL Structure
5. Internal Linking
6. Content Quality
7. Structured Data
8. Security & Accessibility
9. Mobile Optimization
10. Server & Infrastructure
"""
import pytest
from app.services.audit_engine import (
    SEOAuditEngine,
    CrawlData,
    AuditCheckResult,
    create_crawl_data_from_pages,
)


class TestAuditEngineInitialization:
    """Test audit engine initialization."""

    def test_create_crawl_data(self, sample_crawl_pages, sample_robots_txt, sample_sitemap):
        """Test creating CrawlData from pages."""
        crawl_data = create_crawl_data_from_pages(
            base_url="https://example.com",
            pages=sample_crawl_pages,
            robots=sample_robots_txt,
            sitemap=sample_sitemap,
        )

        assert crawl_data.base_url == "https://example.com"
        assert len(crawl_data.pages) == 3
        assert crawl_data.robots_txt["exists"] is True
        assert crawl_data.sitemap["exists"] is True

    def test_engine_initialization(self, sample_crawl_pages):
        """Test SEOAuditEngine initialization."""
        crawl_data = CrawlData(
            base_url="https://example.com",
            pages=sample_crawl_pages,
        )
        engine = SEOAuditEngine(crawl_data)

        assert engine.domain == "example.com"
        assert len(engine.results) == 0


class TestCrawlabilityChecks:
    """Test Category 1: Crawlability & Indexability (Checks 1-10)."""

    @pytest.fixture
    def engine_with_full_data(self, sample_crawl_pages, sample_robots_txt, sample_sitemap):
        """Engine with complete crawl data."""
        crawl_data = CrawlData(
            base_url="https://example.com",
            pages=sample_crawl_pages,
            robots_txt=sample_robots_txt,
            sitemap=sample_sitemap,
        )
        return SEOAuditEngine(crawl_data)

    def test_robots_txt_presence_pass(self, engine_with_full_data):
        """Test Check 1: Robots.txt exists."""
        engine_with_full_data.run_all_checks()
        check = next(r for r in engine_with_full_data.results if r.check_id == 1)

        assert check.passed is True
        assert check.check_name == "Robots.txt Presence"

    def test_robots_txt_presence_fail(self, sample_crawl_pages):
        """Test Check 1: Robots.txt missing."""
        crawl_data = CrawlData(
            base_url="https://example.com",
            pages=sample_crawl_pages,
            robots_txt={"exists": False},
        )
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 1)
        assert check.passed is False
        assert check.severity == "high"

    def test_robots_blocking_critical_resources(self, sample_crawl_pages):
        """Test Check 2: Robots.txt blocking CSS/JS."""
        crawl_data = CrawlData(
            base_url="https://example.com",
            pages=sample_crawl_pages,
            robots_txt={
                "exists": True,
                "content": "User-agent: *\nDisallow: /css\nDisallow: /js",
            },
        )
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 2)
        assert check.passed is False
        assert check.severity == "critical"

    def test_sitemap_presence(self, engine_with_full_data):
        """Test Check 3: Sitemap.xml exists."""
        engine_with_full_data.run_all_checks()
        check = next(r for r in engine_with_full_data.results if r.check_id == 3)

        assert check.passed is True

    def test_noindex_on_important_pages(self, sample_crawl_pages):
        """Test Check 5: Noindex tags on important pages."""
        pages = sample_crawl_pages.copy()
        pages[0]["noindex"] = True  # Add noindex to homepage

        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 5)
        assert check.passed is False
        assert check.severity == "critical"

    def test_canonical_tag_presence(self, sample_crawl_pages):
        """Test Check 6: Canonical tag presence."""
        pages = sample_crawl_pages.copy()
        pages[0]["canonical_url"] = ""  # Remove canonical

        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 6)
        assert check.passed is False


class TestOnPageSEOChecks:
    """Test Category 2: On-Page SEO (Checks 11-20)."""

    def test_missing_title_tag(self):
        """Test Check 11: Missing title tag."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "title": ""},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 11)
        assert check.passed is False
        assert check.severity == "high"

    def test_title_too_short(self):
        """Test Check 12: Title too short (<30 chars)."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "title": "Short Title"},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 12)
        assert check.passed is False

    def test_title_too_long(self):
        """Test Check 13: Title too long (>60 chars)."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "title": "This is an extremely long title that exceeds sixty characters limit for SEO",
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 13)
        assert check.passed is False

    def test_duplicate_title_tags(self):
        """Test Check 14: Duplicate title tags."""
        pages = [
            {"url": "https://example.com/page1", "status_code": 200, "title": "Same Title"},
            {"url": "https://example.com/page2", "status_code": 200, "title": "Same Title"},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 14)
        assert check.passed is False
        assert check.affected_count == 2

    def test_missing_meta_description(self):
        """Test Check 15: Missing meta description."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "title": "Test", "meta_description": ""},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 15)
        assert check.passed is False

    def test_missing_h1(self):
        """Test Check 17: Missing H1."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "title": "Test", "h1": []},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 17)
        assert check.passed is False

    def test_multiple_h1s(self):
        """Test Check 18: Multiple H1 tags."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "h1": ["First H1", "Second H1"]},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 18)
        assert check.passed is False

    def test_missing_image_alt(self, sample_crawl_pages):
        """Test Check 20: Missing image alt text."""
        # sample_crawl_pages[2] has an image without alt
        crawl_data = CrawlData(base_url="https://example.com", pages=sample_crawl_pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 20)
        assert check.passed is False


class TestPerformanceChecks:
    """Test Category 3: Technical Performance (Checks 21-30)."""

    def test_slow_lcp(self):
        """Test Check 21: LCP > 2.5s."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "lcp_ms": 3000},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 21)
        assert check.passed is False
        assert check.severity == "high"

    def test_high_cls(self):
        """Test Check 23: CLS > 0.1."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "cls": 0.25},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 23)
        assert check.passed is False

    def test_slow_ttfb(self):
        """Test Check 24: TTFB > 800ms."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "load_time_ms": 1500},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 24)
        assert check.passed is False

    def test_no_text_compression(self):
        """Test Check 28: No text compression."""
        pages = [{"url": "https://example.com", "status_code": 200}]
        response_headers = {"https://example.com": {"content-encoding": ""}}

        crawl_data = CrawlData(
            base_url="https://example.com",
            pages=pages,
            response_headers=response_headers,
        )
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 28)
        assert check.passed is False


class TestURLStructureChecks:
    """Test Category 4: URL Structure (Checks 31-40)."""

    def test_url_too_long(self):
        """Test Check 31: URL length > 100 chars."""
        long_url = "https://example.com/" + "a" * 100
        pages = [{"url": long_url, "status_code": 200}]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 31)
        assert check.passed is False

    def test_underscores_in_urls(self):
        """Test Check 33: Underscores in URLs."""
        pages = [{"url": "https://example.com/my_page_name", "status_code": 200}]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 33)
        assert check.passed is False

    def test_uppercase_in_urls(self):
        """Test Check 34: Uppercase in URLs."""
        pages = [{"url": "https://example.com/MyPage", "status_code": 200}]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 34)
        assert check.passed is False

    def test_dynamic_parameters(self):
        """Test Check 37: Dynamic parameters in URL."""
        pages = [{"url": "https://example.com/page?id=123", "status_code": 200}]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 37)
        assert check.passed is False

    def test_session_ids_in_urls(self):
        """Test Check 38: Session IDs in URLs."""
        # Use 'sid=' which is one of the patterns checked by the audit engine
        pages = [{"url": "https://example.com/page?sid=abc123", "status_code": 200}]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 38)
        assert check.passed is False
        assert check.severity == "high"


class TestInternalLinkingChecks:
    """Test Category 5: Internal Linking (Checks 41-50)."""

    def test_broken_internal_links(self):
        """Test Check 42: Broken internal links."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "internal_links": [{"url": "https://example.com/nonexistent", "text": "Link"}],
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 42)
        assert check.passed is False
        assert check.severity == "high"

    def test_nofollow_on_internal_links(self):
        """Test Check 44: Nofollow on internal links."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "internal_links": [{"url": "https://example.com/about", "nofollow": True}],
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 44)
        assert check.passed is False

    def test_generic_anchor_text(self):
        """Test Check 45: Generic anchor text."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "internal_links": [{"url": "https://example.com/about", "text": "click here"}],
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 45)
        assert check.passed is False

    def test_low_internal_link_count(self):
        """Test Check 46: Low internal link count."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "internal_links": [{"url": "https://example.com/about", "text": "About"}],
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 46)
        assert check.passed is False


class TestContentChecks:
    """Test Category 6: Content Quality (Checks 51-60)."""

    def test_thin_content(self):
        """Test Check 51: Thin content (< 300 words)."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "word_count": 100},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 51)
        assert check.passed is False
        assert check.severity == "high"

    def test_duplicate_content(self):
        """Test Check 52: Duplicate content."""
        content_hash = "abc123"
        pages = [
            {"url": "https://example.com/page1", "status_code": 200, "text_content_hash": content_hash},
            {"url": "https://example.com/page2", "status_code": 200, "text_content_hash": content_hash},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 52)
        assert check.passed is False

    def test_missing_content(self):
        """Test Check 54: Pages with only navigation (<50 words)."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "word_count": 20},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 54)
        assert check.passed is False

    def test_keyword_stuffing(self):
        """Test Check 55: Keyword stuffing."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "keyword_density": 5.0},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 55)
        assert check.passed is False

    def test_missing_open_graph(self):
        """Test Check 58: Missing OpenGraph tags."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "open_graph": {}},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 58)
        assert check.passed is False


class TestStructuredDataChecks:
    """Test Category 7: Structured Data (Checks 61-70)."""

    def test_no_structured_data(self):
        """Test Check 61: No structured data."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "structured_data": []},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 61)
        assert check.passed is False

    def test_schema_syntax_errors(self):
        """Test Check 62: Schema syntax errors."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "schema_errors": ["Invalid @type"],
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 62)
        assert check.passed is False

    def test_missing_product_schema(self):
        """Test Check 66: Missing product schema on product page."""
        pages = [
            {
                "url": "https://example.com/product/widget",
                "status_code": 200,
                "structured_data": [],
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 66)
        assert check.passed is False
        assert check.severity == "high"


class TestSecurityChecks:
    """Test Category 8: Security & Accessibility (Checks 71-80)."""

    def test_not_https(self):
        """Test Check 71: Pages not using HTTPS."""
        pages = [
            {"url": "http://example.com", "status_code": 200},
        ]
        crawl_data = CrawlData(base_url="http://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 71)
        assert check.passed is False
        assert check.severity == "critical"

    def test_missing_ssl_certificate(self):
        """Test Check 73: Missing SSL certificate."""
        pages = [{"url": "http://example.com", "status_code": 200}]
        crawl_data = CrawlData(base_url="http://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 73)
        assert check.passed is False
        assert check.severity == "critical"

    def test_missing_hsts_header(self):
        """Test Check 75: Missing HSTS header."""
        pages = [{"url": "https://example.com", "status_code": 200}]
        response_headers = {"https://example.com": {}}

        crawl_data = CrawlData(
            base_url="https://example.com",
            pages=pages,
            response_headers=response_headers,
        )
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 75)
        assert check.passed is False

    def test_missing_language_declaration(self):
        """Test Check 76: Missing language declaration."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "html_lang": ""},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 76)
        assert check.passed is False


class TestMobileChecks:
    """Test Category 9: Mobile Optimization (Checks 81-90)."""

    def test_missing_viewport_meta(self):
        """Test Check 81: Missing viewport meta tag."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "has_viewport_meta": False},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 81)
        assert check.passed is False
        assert check.severity == "high"

    def test_viewport_not_responsive(self):
        """Test Check 82: Viewport not responsive."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "has_viewport_meta": True,
                "viewport_content": "width=1024",
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 82)
        assert check.passed is False

    def test_flash_content(self):
        """Test Check 88: Flash content."""
        pages = [
            {"url": "https://example.com", "status_code": 200, "has_flash": True},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 88)
        assert check.passed is False


class TestServerChecks:
    """Test Category 10: Server & Infrastructure (Checks 91-100)."""

    def test_4xx_errors(self):
        """Test Check 91: 4xx errors."""
        pages = [
            {"url": "https://example.com/missing", "status_code": 404},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 91)
        assert check.passed is False
        assert check.severity == "high"

    def test_5xx_errors(self):
        """Test Check 92: 5xx errors."""
        pages = [
            {"url": "https://example.com/error", "status_code": 500},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 92)
        assert check.passed is False
        assert check.severity == "critical"

    def test_redirect_chains(self):
        """Test Check 93: Redirect chains."""
        pages = [
            {
                "url": "https://example.com/old",
                "status_code": 301,
                "redirect_chain": [
                    "https://example.com/old",
                    "https://example.com/old2",
                    "https://example.com/new",
                ],
            },
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 93)
        assert check.passed is False

    def test_302_instead_of_301(self):
        """Test Check 95: Using 302 instead of 301."""
        pages = [
            {"url": "https://example.com/temp-redirect", "status_code": 302},
        ]
        crawl_data = CrawlData(base_url="https://example.com", pages=pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        check = next(r for r in engine.results if r.check_id == 95)
        assert check.passed is False


class TestScoring:
    """Test the scoring algorithm."""

    def test_perfect_score(self):
        """Test scoring with all checks passing."""
        pages = [
            {
                "url": "https://example.com",
                "status_code": 200,
                "title": "Perfect Website Title - Great SEO",
                "meta_description": "This is a perfectly optimized meta description that is the right length for search engines.",
                "h1": ["Perfect Main Heading"],
                "h2": ["Section 1", "Section 2"],
                "word_count": 800,
                "canonical_url": "https://example.com",
                "internal_links": [
                    {"url": "https://example.com/about", "text": "About Us"},
                    {"url": "https://example.com/services", "text": "Services"},
                    {"url": "https://example.com/contact", "text": "Contact"},
                ],
                "images": [{"url": "https://example.com/img.jpg", "alt": "Description"}],
                "structured_data": [{"@type": "Organization"}],
                "open_graph": {"og:title": "Title", "og:image": "img.jpg"},
                "html_lang": "en",
                "has_viewport_meta": True,
                "viewport_content": "width=device-width, initial-scale=1",
                "noindex": False,
            },
        ]
        crawl_data = CrawlData(
            base_url="https://example.com",
            pages=pages,
            robots_txt={"exists": True, "content": "User-agent: *\nAllow: /"},
            sitemap={"exists": True, "urls": ["https://example.com"]},
            response_headers={"https://example.com": {"content-encoding": "gzip"}},
        )
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()
        score = engine.calculate_score()

        # Score should be high (above 70)
        assert score >= 70

    def test_low_score_with_issues(self):
        """Test scoring with many issues."""
        pages = [
            {
                "url": "http://example.com",  # No HTTPS
                "status_code": 200,
                "title": "",  # Missing title
                "meta_description": "",  # Missing description
                "h1": [],  # Missing H1
                "word_count": 50,  # Thin content
                "canonical_url": "",  # Missing canonical
                "internal_links": [],
                "images": [],
                "structured_data": [],
                "html_lang": "",
                "has_viewport_meta": False,
            },
        ]
        crawl_data = CrawlData(
            base_url="http://example.com",
            pages=pages,
            robots_txt={"exists": False},
            sitemap={"exists": False},
        )
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()
        score = engine.calculate_score()

        # With ~20 issues out of 100 checks (weighted by severity),
        # score should be notably lower than perfect but not extremely low
        # due to the weighted scoring algorithm
        assert score < 85

    def test_100_checks_returned(self, sample_crawl_pages):
        """Test that exactly 100 checks are performed."""
        crawl_data = CrawlData(base_url="https://example.com", pages=sample_crawl_pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()

        assert len(engine.results) == 100

    def test_summary_generation(self, sample_crawl_pages):
        """Test summary generation."""
        crawl_data = CrawlData(base_url="https://example.com", pages=sample_crawl_pages)
        engine = SEOAuditEngine(crawl_data)
        engine.run_all_checks()
        summary = engine.get_summary()

        assert "total_checks" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "score" in summary
        assert "issues_by_severity" in summary
        assert "issues_by_category" in summary
        assert summary["total_checks"] == 100
        assert summary["passed"] + summary["failed"] == 100


class TestAuditCheckResult:
    """Test AuditCheckResult dataclass."""

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = AuditCheckResult(
            check_id=1,
            category="Test",
            check_name="Test Check",
            passed=True,
            severity="high",
            affected_count=5,
            affected_urls=["https://example.com/page1"],
            details={"key": "value"},
            recommendation="Fix this issue.",
        )

        result_dict = result.to_dict()

        assert result_dict["check_id"] == 1
        assert result_dict["passed"] is True
        assert result_dict["severity"] == "high"
        assert result_dict["affected_count"] == 5
        assert len(result_dict["affected_urls"]) == 1
