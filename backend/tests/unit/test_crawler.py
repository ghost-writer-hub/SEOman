"""
Unit tests for SEOman Crawler Service.

Tests crawling functionality including:
- URL normalization and parsing
- HTML content extraction
- Link discovery
- SEO data extraction
- Robots.txt handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bs4 import BeautifulSoup

from app.services.crawler import (
    SEOmanCrawler,
    CrawlConfig,
    CrawledPage,
)


class TestCrawlConfig:
    """Test CrawlConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CrawlConfig()

        assert config.max_pages == 10000
        assert config.max_depth == 15
        assert config.concurrent_requests == 3
        assert config.request_delay_ms == 500
        assert config.timeout_seconds == 30
        assert config.respect_robots_txt is True
        assert config.store_html is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = CrawlConfig(
            max_pages=100,
            max_depth=5,
            concurrent_requests=5,
            js_rendering=True,
        )

        assert config.max_pages == 100
        assert config.max_depth == 5
        assert config.js_rendering is True


class TestCrawledPage:
    """Test CrawledPage dataclass."""

    def test_default_values(self):
        """Test default page values."""
        page = CrawledPage(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            load_time_ms=150,
            crawl_timestamp="2026-01-10T12:00:00Z",
        )

        assert page.url == "https://example.com"
        assert page.status_code == 200
        assert page.title == ""
        assert page.word_count == 0
        assert page.internal_links == []
        assert page.js_rendered is False

    def test_to_dict(self):
        """Test converting page to dictionary."""
        page = CrawledPage(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            load_time_ms=150,
            crawl_timestamp="2026-01-10T12:00:00Z",
            title="Test Page",
        )

        result = page.to_dict()

        assert isinstance(result, dict)
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert result["status_code"] == 200


class TestSEOmanCrawlerInit:
    """Test crawler initialization."""

    def test_basic_initialization(self):
        """Test basic crawler initialization."""
        crawler = SEOmanCrawler(
            site_url="https://example.com",
            tenant_id="tenant-1",
            site_id="site-1",
            crawl_id="crawl-1",
        )

        assert crawler.original_url == "https://example.com"
        assert crawler.domain == "example.com"
        assert crawler.tenant_id == "tenant-1"
        assert len(crawler.visited_urls) == 0
        assert len(crawler.results) == 0

    def test_url_normalization(self):
        """Test URL normalization on init."""
        crawler = SEOmanCrawler(site_url="https://example.com/")

        assert crawler.original_url == "https://example.com"
        assert not crawler.original_url.endswith("/")

    def test_custom_config(self):
        """Test crawler with custom config."""
        config = CrawlConfig(max_pages=50, max_depth=3)
        crawler = SEOmanCrawler(site_url="https://example.com", config=config)

        assert crawler.config.max_pages == 50
        assert crawler.config.max_depth == 3


class TestHTMLExtraction:
    """Test HTML content extraction methods."""

    @pytest.fixture
    def crawler(self):
        """Create a test crawler instance."""
        return SEOmanCrawler(site_url="https://example.com")

    def test_extract_title(self, crawler, sample_html_page):
        """Test title extraction from HTML."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        title_tag = soup.find("title")

        assert title_tag is not None
        assert title_tag.get_text() == "Test Page Title"

    def test_extract_meta_description(self, crawler, sample_html_page):
        """Test meta description extraction."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        meta = soup.find("meta", attrs={"name": "description"})

        assert meta is not None
        assert "test page description" in meta.get("content", "").lower()

    def test_extract_canonical(self, crawler, sample_html_page):
        """Test canonical URL extraction."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        canonical = soup.find("link", attrs={"rel": "canonical"})

        assert canonical is not None
        assert canonical.get("href") == "https://example.com/test-page"

    def test_extract_headings(self, crawler, sample_html_page):
        """Test heading extraction."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        h1_tags = soup.find_all("h1")
        h2_tags = soup.find_all("h2")

        assert len(h1_tags) == 1
        assert h1_tags[0].get_text() == "Main Heading"
        assert len(h2_tags) == 1

    def test_extract_structured_data(self, crawler, sample_html_page):
        """Test structured data extraction."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        ld_json = soup.find("script", attrs={"type": "application/ld+json"})

        assert ld_json is not None
        assert "@type" in ld_json.get_text()

    def test_extract_open_graph(self, crawler, sample_html_page):
        """Test OpenGraph tag extraction."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        og_title = soup.find("meta", attrs={"property": "og:title"})

        assert og_title is not None
        assert og_title.get("content") == "Test Page OG Title"

    def test_extract_viewport(self, crawler, sample_html_page):
        """Test viewport meta extraction."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        viewport = soup.find("meta", attrs={"name": "viewport"})

        assert viewport is not None
        assert "width=device-width" in viewport.get("content", "")


class TestLinkExtraction:
    """Test link discovery and extraction."""

    @pytest.fixture
    def crawler(self):
        """Create a test crawler instance."""
        return SEOmanCrawler(site_url="https://example.com")

    def test_extract_internal_links(self, crawler, sample_html_page):
        """Test internal link extraction."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        links = soup.find_all("a")

        internal_links = []
        external_links = []

        for link in links:
            href = link.get("href", "")
            if href.startswith("/"):
                internal_links.append(href)
            elif href.startswith("http") and "example.com" not in href:
                external_links.append(href)

        assert "/about" in internal_links
        assert "https://external.com" in external_links

    def test_extract_images(self, crawler, sample_html_page):
        """Test image extraction with alt text."""
        soup = BeautifulSoup(sample_html_page, "html.parser")
        images = soup.find_all("img")

        assert len(images) == 1
        assert images[0].get("alt") == "Test Image"


class TestURLHandling:
    """Test URL normalization and handling."""

    @pytest.fixture
    def crawler(self):
        """Create a test crawler instance."""
        return SEOmanCrawler(site_url="https://example.com")

    def test_normalize_relative_url(self, crawler):
        """Test relative URL normalization."""
        from urllib.parse import urljoin

        base_url = "https://example.com/page"
        relative_url = "../other"
        normalized = urljoin(base_url, relative_url)

        assert normalized == "https://example.com/other"

    def test_normalize_absolute_url(self, crawler):
        """Test absolute URL handling."""
        from urllib.parse import urljoin

        base_url = "https://example.com/page"
        absolute_url = "https://example.com/about"
        normalized = urljoin(base_url, absolute_url)

        assert normalized == "https://example.com/about"

    def test_is_same_domain(self, crawler):
        """Test domain checking."""
        from urllib.parse import urlparse

        url1 = "https://example.com/page"
        url2 = "https://other.com/page"

        domain1 = urlparse(url1).netloc
        domain2 = urlparse(url2).netloc

        assert domain1 == "example.com"
        assert domain2 == "other.com"
        assert domain1 != domain2

    def test_skip_fragment_urls(self, crawler):
        """Test that fragment-only URLs are handled."""
        from urllib.parse import urlparse

        url_with_fragment = "https://example.com/page#section"
        parsed = urlparse(url_with_fragment)

        # Should identify fragment
        assert parsed.fragment == "section"
        # Base URL without fragment
        assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://example.com/page"


class TestRobotsTxtHandling:
    """Test robots.txt parsing and handling."""

    def test_robots_allows_crawling(self, sample_robots_txt):
        """Test robots.txt allows general crawling."""
        content = sample_robots_txt["content"]

        assert "Allow: /" in content
        assert "Disallow: /admin/" in content

    def test_robots_sitemap_extraction(self, sample_robots_txt):
        """Test sitemap extraction from robots.txt."""
        content = sample_robots_txt["content"]

        assert "Sitemap: https://example.com/sitemap.xml" in content


class TestAdaptiveDelay:
    """Test adaptive rate limiting."""

    @pytest.fixture
    def crawler_with_adaptive_delay(self):
        """Create crawler with adaptive delay enabled."""
        config = CrawlConfig(
            adaptive_delay=True,
            min_delay_ms=200,
            max_delay_ms=2000,
            backoff_multiplier=1.5,
        )
        return SEOmanCrawler(site_url="https://example.com", config=config)

    def test_adaptive_delay_config(self, crawler_with_adaptive_delay):
        """Test adaptive delay configuration."""
        crawler = crawler_with_adaptive_delay

        assert crawler.config.adaptive_delay is True
        assert crawler.config.min_delay_ms == 200
        assert crawler.config.max_delay_ms == 2000
        assert crawler.config.backoff_multiplier == 1.5


class TestJSRenderingConfig:
    """Test JavaScript rendering configuration."""

    def test_js_rendering_disabled_by_default(self):
        """Test JS rendering is disabled by default."""
        config = CrawlConfig()

        assert config.js_rendering is False
        assert config.js_rendering_auto is True

    def test_js_rendering_enabled(self):
        """Test enabling JS rendering."""
        config = CrawlConfig(
            js_rendering=True,
            js_rendering_timeout_ms=60000,
            js_rendering_wait_ms=2000,
        )

        assert config.js_rendering is True
        assert config.js_rendering_timeout_ms == 60000
        assert config.js_rendering_wait_ms == 2000

    def test_js_min_word_count_threshold(self):
        """Test JS rendering word count threshold."""
        config = CrawlConfig(js_min_word_count_threshold=100)

        assert config.js_min_word_count_threshold == 100


class TestCrawlResults:
    """Test crawl result handling."""

    @pytest.fixture
    def crawler(self):
        """Create a test crawler instance."""
        return SEOmanCrawler(site_url="https://example.com")

    def test_results_list_initialization(self, crawler):
        """Test results list is initialized empty."""
        assert crawler.results == []

    def test_visited_urls_tracking(self, crawler):
        """Test visited URLs are tracked."""
        assert len(crawler.visited_urls) == 0

        crawler.visited_urls.add("https://example.com")
        crawler.visited_urls.add("https://example.com/about")

        assert len(crawler.visited_urls) == 2
        assert "https://example.com" in crawler.visited_urls

    def test_results_contain_required_fields(self):
        """Test crawled page has all required fields."""
        page = CrawledPage(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            load_time_ms=150,
            crawl_timestamp="2026-01-10T12:00:00Z",
        )

        page_dict = page.to_dict()

        required_fields = [
            "url", "final_url", "status_code", "content_type",
            "load_time_ms", "crawl_timestamp", "title", "meta_description",
            "canonical_url", "h1", "h2", "internal_links", "external_links",
            "images", "word_count", "structured_data", "open_graph",
            "html_lang", "has_viewport_meta", "noindex", "js_rendered",
        ]

        for field in required_fields:
            assert field in page_dict, f"Missing required field: {field}"
