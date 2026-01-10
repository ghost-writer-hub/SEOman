"""
SEOman v2.0 Crawler Service

Full site crawler with:
- Async HTTP requests
- HTML storage to S3
- SEO data extraction
- Link discovery and following
- Robots.txt respect
- Rate limiting
- JavaScript rendering (Playwright)
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.integrations.storage import get_storage_client, SEOmanStoragePaths

logger = logging.getLogger(__name__)

# JS Crawler import with graceful fallback
try:
    from app.services.js_crawler import (
        JSCrawler,
        JSCrawlConfig,
        JSRenderedPage,
        detect_spa_from_html,
        should_use_js_rendering,
        PLAYWRIGHT_AVAILABLE,
    )
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    JSCrawler = None
    logger.warning("JS Crawler not available")


@dataclass
class CrawledPage:
    url: str
    final_url: str
    status_code: int
    content_type: str
    load_time_ms: int
    crawl_timestamp: str
    crawl_depth: int = 0

    title: str = ""
    meta_description: str = ""
    meta_robots: str = ""
    canonical_url: str = ""
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)

    internal_links: list[dict] = field(default_factory=list)
    external_links: list[dict] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)

    word_count: int = 0
    text_content_hash: str = ""

    structured_data: list[dict] = field(default_factory=list)
    open_graph: dict = field(default_factory=dict)
    twitter_cards: dict = field(default_factory=dict)
    hreflang: list[dict] = field(default_factory=list)

    html_lang: str = ""
    has_viewport_meta: bool = False
    viewport_content: str = ""
    noindex: bool = False
    nofollow: bool = False

    scripts_count: int = 0
    stylesheets_count: int = 0

    response_headers: dict = field(default_factory=dict)
    raw_html_path: str = ""
    markdown_path: str = ""
    errors: list[str] = field(default_factory=list)

    # JS rendering info
    js_rendered: bool = False
    js_render_time_ms: int = 0
    spa_detected: bool = False
    framework_detected: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CrawlConfig:
    max_pages: int = 10000
    max_depth: int = 15
    concurrent_requests: int = 3
    request_delay_ms: int = 500
    timeout_seconds: int = 30
    respect_robots_txt: bool = True
    follow_external_links: bool = False
    store_html: bool = True
    user_agent: str = "SEOmanBot/2.0 (+https://seoman.ai/bot; respectful crawler)"
    adaptive_delay: bool = True
    min_delay_ms: int = 200
    max_delay_ms: int = 2000
    backoff_multiplier: float = 1.5

    # JS rendering options
    js_rendering: bool = False  # Enable JS rendering for all pages
    js_rendering_auto: bool = True  # Auto-detect SPAs and use JS rendering
    js_rendering_timeout_ms: int = 30000
    js_rendering_wait_ms: int = 1000  # Wait after load for dynamic content
    js_min_word_count_threshold: int = 50  # Re-render if word count below this


class SEOmanCrawler:
    """Async web crawler for SEO analysis."""

    def __init__(
        self,
        site_url: str,
        config: CrawlConfig | None = None,
        tenant_id: str = "",
        site_id: str = "",
        crawl_id: str = "",
    ):
        self.original_url = site_url.rstrip("/")
        self.base_url = self.original_url
        self.domain = urlparse(self.base_url).netloc
        self.allowed_domains: set[str] = set()
        self.config = config or CrawlConfig()
        self.tenant_id = tenant_id
        self.site_id = site_id
        self.crawl_id = crawl_id

        self.visited_urls: set[str] = set()
        self.url_queue: asyncio.Queue = asyncio.Queue()
        self.results: list[CrawledPage] = []
        self.robots_parser: RobotFileParser | None = None
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(self.config.concurrent_requests)

        # Adaptive rate limiting state
        self._current_delay_ms: float = float(self.config.request_delay_ms)
        self._consecutive_errors: int = 0
        self._robots_crawl_delay: float | None = None

        # JS rendering
        self._js_crawler: JSCrawler | None = None
        self._js_rendering_available = PLAYWRIGHT_AVAILABLE and (self.config.js_rendering or self.config.js_rendering_auto)
        self._pages_needing_js: set[str] = set()  # URLs that need JS re-rendering

        self.storage = None
        if self.config.store_html and tenant_id and site_id and crawl_id:
            try:
                self.storage = get_storage_client()
            except Exception as e:
                logger.warning(f"Could not initialize storage: {e}")

    async def crawl(self, seed_urls: list[str] | None = None) -> list[CrawledPage]:
        """Run the crawl and return results.

        Args:
            seed_urls: Optional list of URLs from sitemap to seed the queue.
        """
        logger.info(f"Starting crawl of {self.base_url} (max {self.config.max_pages} pages)")
        start_time = time.time()

        resolved_url = await self._resolve_start_url()
        if resolved_url:
            self.base_url = resolved_url.rstrip("/")
            self.domain = urlparse(self.base_url).netloc
            logger.info(f"Resolved start URL to: {self.base_url}")

        self._setup_allowed_domains()

        if self.config.respect_robots_txt:
            await self._fetch_robots_txt()

        # Initialize JS crawler if needed
        if self._js_rendering_available and self.config.js_rendering:
            await self._init_js_crawler()
            logger.info("JS rendering enabled for all pages")

        await self.url_queue.put((self.base_url, 0))

        if seed_urls:
            urls_added = 0
            for url in seed_urls:
                if urls_added >= self.config.max_pages:
                    break
                if self._is_internal_domain(urlparse(url).netloc):
                    await self.url_queue.put((url, 1))
                    urls_added += 1
            logger.info(f"Seeded queue with {urls_added} URLs from sitemap")

        workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.config.concurrent_requests)
        ]

        await self.url_queue.join()

        for worker in workers:
            worker.cancel()

        # Process pages that need JS rendering (auto-detected)
        if self._js_rendering_available and self.config.js_rendering_auto and self._pages_needing_js:
            await self._process_js_pages()

        # Cleanup JS crawler
        await self._cleanup_js_crawler()

        elapsed = time.time() - start_time
        js_rendered_count = sum(1 for p in self.results if p.js_rendered)
        logger.info(f"Crawl complete: {len(self.results)} pages in {elapsed:.2f}s ({js_rendered_count} JS-rendered)")
        return self.results

    async def _init_js_crawler(self):
        """Initialize the JS crawler."""
        if self._js_crawler is None and JSCrawler is not None:
            js_config = JSCrawlConfig(
                timeout_ms=self.config.js_rendering_timeout_ms,
                wait_after_load_ms=self.config.js_rendering_wait_ms,
                user_agent=self.config.user_agent,
            )
            self._js_crawler = JSCrawler(js_config)
            await self._js_crawler.start()

    async def _cleanup_js_crawler(self):
        """Cleanup JS crawler resources."""
        if self._js_crawler:
            await self._js_crawler.stop()
            self._js_crawler = None

    async def _process_js_pages(self):
        """Re-process pages that need JS rendering."""
        if not self._pages_needing_js:
            return

        logger.info(f"Processing {len(self._pages_needing_js)} pages with JS rendering")
        await self._init_js_crawler()

        # Find pages that need re-rendering
        pages_to_rerender = []
        page_index_map = {}

        for i, page in enumerate(self.results):
            if page.url in self._pages_needing_js:
                pages_to_rerender.append(page)
                page_index_map[page.url] = i

        # Render in batches
        batch_size = 5
        for i in range(0, len(pages_to_rerender), batch_size):
            batch = pages_to_rerender[i:i + batch_size]
            urls = [p.url for p in batch]

            js_results = await self._js_crawler.render_batch(urls)

            for page, js_result in zip(batch, js_results):
                if js_result.success:
                    # Re-extract data from JS-rendered HTML
                    updated_page = self._extract_page_data(
                        url=page.url,
                        final_url=js_result.final_url,
                        status_code=js_result.status_code,
                        html=js_result.html,
                        load_time_ms=js_result.load_time_ms,
                        depth=page.crawl_depth,
                        headers=page.response_headers,
                    )

                    # Copy JS rendering info
                    updated_page.js_rendered = True
                    updated_page.js_render_time_ms = js_result.render_time_ms
                    updated_page.spa_detected = js_result.spa_detected
                    updated_page.framework_detected = js_result.framework_detected
                    updated_page.raw_html_path = page.raw_html_path

                    # Store updated HTML if configured
                    if self.storage and self.config.store_html:
                        await self._store_html(updated_page, js_result.html)

                    # Update in results
                    idx = page_index_map[page.url]
                    self.results[idx] = updated_page

                    logger.debug(f"JS rendered: {page.url} (word count: {page.word_count} -> {updated_page.word_count})")

            # Small delay between batches
            if i + batch_size < len(pages_to_rerender):
                await asyncio.sleep(1)

    async def _resolve_start_url(self) -> str | None:
        """Try to resolve the start URL, attempting www/non-www variants if needed."""
        urls_to_try = [self.base_url]
        parsed = urlparse(self.base_url)

        if parsed.netloc.startswith("www."):
            urls_to_try.append(f"{parsed.scheme}://{parsed.netloc[4:]}{parsed.path}")
        else:
            urls_to_try.append(f"{parsed.scheme}://www.{parsed.netloc}{parsed.path}")

        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": self.config.user_agent},
        ) as client:
            for url in urls_to_try:
                try:
                    logger.debug(f"Trying URL: {url}")
                    response = await client.head(url)
                    final_url = str(response.url).rstrip("/")
                    logger.info(f"Successfully resolved {url} -> {final_url}")
                    return final_url
                except httpx.ConnectError as e:
                    logger.debug(f"Connect error for {url}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error trying {url}: {e}")
                    continue

        logger.warning(f"Could not resolve any URL variant for {self.base_url}")
        return None

    def _setup_allowed_domains(self):
        """Setup allowed domains for internal link detection."""
        base_domain = self.domain.replace("www.", "")
        self.allowed_domains = {
            base_domain,
            f"www.{base_domain}",
            self.domain,
        }
        logger.debug(f"Allowed domains: {self.allowed_domains}")

    def _is_internal_domain(self, netloc: str) -> bool:
        """Check if a domain is internal (belongs to the site being crawled)."""
        if not netloc:
            return False
        if netloc in self.allowed_domains:
            return True
        base_domain = self.domain.replace("www.", "")
        if netloc.endswith(f".{base_domain}"):
            return True
        return False

    async def _worker(self, name: str):
        """Worker that processes URLs from the queue with adaptive rate limiting."""
        while True:
            try:
                url, depth = await asyncio.wait_for(self.url_queue.get(), timeout=5.0)

                if url in self.visited_urls:
                    self.url_queue.task_done()
                    continue

                if len(self.results) >= self.config.max_pages:
                    self.url_queue.task_done()
                    continue

                if depth > self.config.max_depth:
                    self.url_queue.task_done()
                    continue

                self.visited_urls.add(url)
                success = await self._crawl_url(url, depth)
                self.url_queue.task_done()

                # Adaptive delay logic
                await self._apply_adaptive_delay(success)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{name} error: {e}")
                try:
                    self.url_queue.task_done()
                except ValueError:
                    pass

    async def _apply_adaptive_delay(self, success: bool):
        """Apply delay between requests with adaptive backoff."""
        if self.config.adaptive_delay:
            if success:
                # Successful request: gradually reduce delay (but not below minimum)
                self._consecutive_errors = 0
                new_delay = max(
                    self.config.min_delay_ms,
                    self._current_delay_ms / self.config.backoff_multiplier
                )
                if new_delay != self._current_delay_ms:
                    self._current_delay_ms = new_delay
            else:
                # Failed request: exponential backoff
                self._consecutive_errors += 1
                new_delay = min(
                    self.config.max_delay_ms,
                    self._current_delay_ms * (self.config.backoff_multiplier ** self._consecutive_errors)
                )
                if new_delay != self._current_delay_ms:
                    logger.info(f"Backing off: delay increased to {new_delay:.0f}ms (consecutive errors: {self._consecutive_errors})")
                    self._current_delay_ms = new_delay

        # Use robots.txt crawl-delay if specified and higher
        effective_delay = self._current_delay_ms
        if self._robots_crawl_delay is not None:
            effective_delay = max(effective_delay, self._robots_crawl_delay * 1000)

        if effective_delay > 0:
            await asyncio.sleep(effective_delay / 1000)

    async def _crawl_url(self, url: str, depth: int) -> bool:
        """Crawl a single URL.

        Returns:
            True if request succeeded (2xx/3xx), False if error or rate-limited.
        """
        if self.robots_parser and not self.robots_parser.can_fetch(self.config.user_agent, url):
            logger.debug(f"Blocked by robots.txt: {url}")
            return True  # Not an error, just blocked

        # If JS rendering is enabled for all pages, use JS crawler directly
        if self.config.js_rendering and self._js_crawler:
            return await self._crawl_url_with_js(url, depth)

        async with self.semaphore:
            try:
                start_time = time.time()
                async with httpx.AsyncClient(
                    timeout=self.config.timeout_seconds,
                    follow_redirects=True,
                    headers={"User-Agent": self.config.user_agent},
                ) as client:
                    response = await client.get(url)
                    load_time_ms = int((time.time() - start_time) * 1000)

                    # Check for rate limiting responses
                    if response.status_code in (429, 503):
                        logger.warning(f"Rate limited ({response.status_code}): {url}")
                        self.results.append(CrawledPage(
                            url=url, final_url=url, status_code=response.status_code,
                            content_type="", load_time_ms=load_time_ms,
                            crawl_timestamp=datetime.utcnow().isoformat(),
                            crawl_depth=depth, errors=[f"Rate limited: {response.status_code}"],
                        ))
                        return False  # Trigger backoff

                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type.lower():
                        logger.debug(f"Skipping non-HTML: {url} ({content_type})")
                        return True  # Not an error

                    html = response.text
                    page = self._extract_page_data(url, str(response.url), response.status_code, html, load_time_ms, depth, dict(response.headers))

                    # Check if page needs JS rendering (auto-detection)
                    if self._js_rendering_available and self.config.js_rendering_auto:
                        needs_js, reason = await self._check_needs_js_rendering(html, page.word_count)
                        if needs_js:
                            logger.debug(f"Page needs JS rendering: {url} - {reason}")
                            self._pages_needing_js.add(url)
                            # Detect SPA info from initial HTML
                            spa_detected, framework, _ = detect_spa_from_html(html)
                            page.spa_detected = spa_detected
                            page.framework_detected = framework

                    if self.storage and self.config.store_html:
                        await self._store_html(page, html)

                    self.results.append(page)

                    for link in page.internal_links:
                        link_url = link.get("url", "")
                        if link_url and link_url not in self.visited_urls:
                            await self.url_queue.put((link_url, depth + 1))

                    return True  # Success

            except httpx.TimeoutException:
                logger.warning(f"Timeout: {url}")
                self.results.append(CrawledPage(
                    url=url, final_url=url, status_code=0,
                    content_type="", load_time_ms=self.config.timeout_seconds * 1000,
                    crawl_timestamp=datetime.utcnow().isoformat(),
                    crawl_depth=depth, errors=["Request timed out"],
                ))
                return False  # Trigger backoff
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                self.results.append(CrawledPage(
                    url=url, final_url=url, status_code=0,
                    content_type="", load_time_ms=0,
                    crawl_timestamp=datetime.utcnow().isoformat(),
                    crawl_depth=depth, errors=[str(e)],
                ))
                return False  # Trigger backoff

    async def _crawl_url_with_js(self, url: str, depth: int) -> bool:
        """Crawl a URL using JS rendering."""
        async with self.semaphore:
            try:
                js_result = await self._js_crawler.render_page(url)

                if not js_result.success:
                    self.results.append(CrawledPage(
                        url=url, final_url=url, status_code=0,
                        content_type="", load_time_ms=js_result.load_time_ms,
                        crawl_timestamp=js_result.timestamp,
                        crawl_depth=depth, errors=js_result.errors,
                        js_rendered=True,
                    ))
                    return False

                page = self._extract_page_data(
                    url=url,
                    final_url=js_result.final_url,
                    status_code=js_result.status_code,
                    html=js_result.html,
                    load_time_ms=js_result.load_time_ms,
                    depth=depth,
                    headers={},
                )

                page.js_rendered = True
                page.js_render_time_ms = js_result.render_time_ms
                page.spa_detected = js_result.spa_detected
                page.framework_detected = js_result.framework_detected

                if self.storage and self.config.store_html:
                    await self._store_html(page, js_result.html)

                self.results.append(page)

                for link in page.internal_links:
                    link_url = link.get("url", "")
                    if link_url and link_url not in self.visited_urls:
                        await self.url_queue.put((link_url, depth + 1))

                return True

            except Exception as e:
                logger.error(f"JS crawl error for {url}: {e}")
                self.results.append(CrawledPage(
                    url=url, final_url=url, status_code=0,
                    content_type="", load_time_ms=0,
                    crawl_timestamp=datetime.utcnow().isoformat(),
                    crawl_depth=depth, errors=[str(e)],
                    js_rendered=True,
                ))
                return False

    async def _check_needs_js_rendering(self, html: str, word_count: int) -> tuple[bool, str]:
        """Check if a page needs JS rendering."""
        # Low word count check
        if word_count < self.config.js_min_word_count_threshold:
            return True, f"Low word count ({word_count})"

        # SPA detection
        needs_js, framework, reasons = detect_spa_from_html(html)
        if needs_js:
            return True, f"SPA detected ({framework}): {reasons[0] if reasons else 'unknown'}"

        return False, ""

    def _extract_page_data(
        self,
        url: str,
        final_url: str,
        status_code: int,
        html: str,
        load_time_ms: int,
        depth: int,
        headers: dict,
    ) -> CrawledPage:
        """Extract SEO data from HTML."""
        soup = BeautifulSoup(html, "lxml")

        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        meta_description = ""
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        if meta_desc_tag:
            meta_description = meta_desc_tag.get("content", "")

        meta_robots = ""
        meta_robots_tag = soup.find("meta", attrs={"name": "robots"})
        if meta_robots_tag:
            meta_robots = meta_robots_tag.get("content", "")

        canonical_url = ""
        canonical_tag = soup.find("link", attrs={"rel": "canonical"})
        if canonical_tag:
            canonical_url = canonical_tag.get("href", "")

        h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")][:20]
        h3_tags = [h.get_text(strip=True) for h in soup.find_all("h3")][:20]

        internal_links = []
        external_links = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue

            full_url = urljoin(final_url, href)
            parsed = urlparse(full_url)

            if parsed.scheme not in ["http", "https"]:
                continue

            link_data = {
                "url": full_url,
                "text": a.get_text(strip=True)[:100],
                "nofollow": "nofollow" in a.get("rel", []),
            }

            if self._is_internal_domain(parsed.netloc):
                internal_links.append(link_data)
            else:
                external_links.append(link_data)

        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if src:
                images.append({
                    "url": urljoin(final_url, src),
                    "alt": img.get("alt", ""),
                    "width": img.get("width"),
                    "height": img.get("height"),
                })

        text_content = soup.get_text(separator=" ", strip=True)
        word_count = len(text_content.split())
        text_hash = hashlib.md5(text_content.encode()).hexdigest()

        structured_data = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    structured_data.extend(data)
                else:
                    structured_data.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

        open_graph = {}
        for meta in soup.find_all("meta", property=re.compile(r"^og:")):
            prop = meta.get("property", "")
            open_graph[prop] = meta.get("content", "")

        twitter_cards = {}
        for meta in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
            name = meta.get("name", "")
            twitter_cards[name] = meta.get("content", "")

        hreflang = []
        for link in soup.find_all("link", rel="alternate", hreflang=True):
            hreflang.append({
                "lang": link.get("hreflang", ""),
                "url": link.get("href", ""),
            })

        html_tag = soup.find("html")
        html_lang = html_tag.get("lang", "") if html_tag else ""

        has_viewport = False
        viewport_content = ""
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        if viewport_meta:
            has_viewport = True
            viewport_content = viewport_meta.get("content", "")

        noindex = "noindex" in meta_robots.lower()
        nofollow = "nofollow" in meta_robots.lower()

        scripts_count = len(soup.find_all("script", src=True))
        stylesheets_count = len(soup.find_all("link", rel="stylesheet"))

        response_headers = {k.lower(): v for k, v in headers.items()}

        return CrawledPage(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=headers.get("content-type", ""),
            load_time_ms=load_time_ms,
            crawl_timestamp=datetime.utcnow().isoformat(),
            crawl_depth=depth,
            title=title,
            meta_description=meta_description,
            meta_robots=meta_robots,
            canonical_url=canonical_url,
            h1=h1_tags,
            h2=h2_tags,
            h3=h3_tags,
            internal_links=internal_links[:200],
            external_links=external_links[:100],
            images=images[:100],
            word_count=word_count,
            text_content_hash=text_hash,
            structured_data=structured_data,
            open_graph=open_graph,
            twitter_cards=twitter_cards,
            hreflang=hreflang,
            html_lang=html_lang,
            has_viewport_meta=has_viewport,
            viewport_content=viewport_content,
            noindex=noindex,
            nofollow=nofollow,
            scripts_count=scripts_count,
            stylesheets_count=stylesheets_count,
            response_headers=response_headers,
        )

    async def _store_html(self, page: CrawledPage, html: str):
        """Store HTML to S3/storage."""
        try:
            url_hash = hashlib.md5(page.url.encode()).hexdigest()[:12]
            html_key = f"{SEOmanStoragePaths.crawl_pages(self.tenant_id, self.site_id, self.crawl_id)}{url_hash}.html"

            self.storage.upload_bytes(
                key=html_key,
                data=html.encode("utf-8"),
                content_type="text/html",
                metadata={"url": page.url, "crawl_timestamp": page.crawl_timestamp},
            )
            page.raw_html_path = html_key
        except Exception as e:
            logger.error(f"Failed to store HTML for {page.url}: {e}")

    async def _fetch_robots_txt(self):
        """Fetch and parse robots.txt, including crawl-delay directive."""
        robots_url = f"{self.base_url}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    robots_content = response.text
                    self.robots_parser = RobotFileParser()
                    self.robots_parser.parse(robots_content.splitlines())
                    logger.info(f"Loaded robots.txt from {robots_url}")

                    # Extract Crawl-delay directive
                    self._robots_crawl_delay = self._extract_crawl_delay(robots_content)
                    if self._robots_crawl_delay:
                        logger.info(f"Robots.txt crawl-delay: {self._robots_crawl_delay}s")
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt: {e}")

    def _extract_crawl_delay(self, robots_content: str) -> float | None:
        """Extract crawl-delay from robots.txt content."""
        current_agent = None
        crawl_delay = None
        wildcard_delay = None

        for line in robots_content.splitlines():
            line = line.strip().lower()
            if line.startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.startswith("crawl-delay:") and current_agent:
                try:
                    delay = float(line.split(":", 1)[1].strip())
                    if current_agent == "*":
                        wildcard_delay = delay
                    elif "seoman" in self.config.user_agent.lower() or current_agent == "*":
                        crawl_delay = delay
                except ValueError:
                    pass

        return crawl_delay or wildcard_delay


async def resolve_site_url(site_url: str) -> str:
    """Resolve site URL, trying www/non-www variants if needed."""
    urls_to_try = [site_url.rstrip("/")]
    parsed = urlparse(site_url)

    if parsed.netloc.startswith("www."):
        urls_to_try.append(f"{parsed.scheme}://{parsed.netloc[4:]}")
    else:
        urls_to_try.append(f"{parsed.scheme}://www.{parsed.netloc}")

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for url in urls_to_try:
            try:
                response = await client.head(url)
                return str(response.url).rstrip("/")
            except Exception:
                continue

    return site_url.rstrip("/")


async def crawl_site(
    site_url: str,
    max_pages: int = 100,
    tenant_id: str = "",
    site_id: str = "",
    crawl_id: str = "",
) -> tuple[list[CrawledPage], dict, dict]:
    """
    Convenience function to crawl a site.
    Returns (pages, robots_txt_info, sitemap_info).
    """
    from app.services.audit_engine import fetch_robots_txt, fetch_sitemap

    resolved_url = await resolve_site_url(site_url)
    logger.info(f"Resolved site URL: {site_url} -> {resolved_url}")

    robots_info = await fetch_robots_txt(resolved_url)
    sitemap_info = await fetch_sitemap(resolved_url, robots_info.get("content"))

    sitemap_urls = sitemap_info.get("urls", [])
    if sitemap_urls:
        logger.info(f"Found {len(sitemap_urls)} URLs in sitemap, will use to seed crawler")

    config = CrawlConfig(max_pages=max_pages, store_html=bool(tenant_id))
    crawler = SEOmanCrawler(
        site_url=resolved_url,
        config=config,
        tenant_id=tenant_id,
        site_id=site_id,
        crawl_id=crawl_id,
    )

    pages = await crawler.crawl(seed_urls=sitemap_urls)

    return pages, robots_info, sitemap_info


def pages_to_dict_list(pages: list[CrawledPage]) -> list[dict]:
    """Convert CrawledPage objects to dict list for database storage."""
    return [page.to_dict() for page in pages]
