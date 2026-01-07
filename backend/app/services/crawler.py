"""
SEOman v2.0 Crawler Service

Full site crawler with:
- Async HTTP requests
- HTML storage to S3
- SEO data extraction
- Link discovery and following
- Robots.txt respect
- Rate limiting
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

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CrawlConfig:
    max_pages: int = 100
    max_depth: int = 10
    concurrent_requests: int = 5
    request_delay_ms: int = 100
    timeout_seconds: int = 30
    respect_robots_txt: bool = True
    follow_external_links: bool = False
    store_html: bool = True
    user_agent: str = "SEOmanBot/2.0 (+https://seoman.ai/bot)"


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
        self.base_url = site_url.rstrip("/")
        self.domain = urlparse(self.base_url).netloc
        self.config = config or CrawlConfig()
        self.tenant_id = tenant_id
        self.site_id = site_id
        self.crawl_id = crawl_id

        self.visited_urls: set[str] = set()
        self.url_queue: asyncio.Queue = asyncio.Queue()
        self.results: list[CrawledPage] = []
        self.robots_parser: RobotFileParser | None = None
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(self.config.concurrent_requests)

        self.storage = None
        if self.config.store_html and tenant_id and site_id and crawl_id:
            try:
                self.storage = get_storage_client()
            except Exception as e:
                logger.warning(f"Could not initialize storage: {e}")

    async def crawl(self) -> list[CrawledPage]:
        """Run the crawl and return results."""
        logger.info(f"Starting crawl of {self.base_url} (max {self.config.max_pages} pages)")
        start_time = time.time()

        if self.config.respect_robots_txt:
            await self._fetch_robots_txt()

        await self.url_queue.put((self.base_url, 0))

        workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.config.concurrent_requests)
        ]

        await self.url_queue.join()

        for worker in workers:
            worker.cancel()

        elapsed = time.time() - start_time
        logger.info(f"Crawl complete: {len(self.results)} pages in {elapsed:.2f}s")
        return self.results

    async def _worker(self, name: str):
        """Worker that processes URLs from the queue."""
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
                await self._crawl_url(url, depth)
                self.url_queue.task_done()

                if self.config.request_delay_ms > 0:
                    await asyncio.sleep(self.config.request_delay_ms / 1000)

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

    async def _crawl_url(self, url: str, depth: int):
        """Crawl a single URL."""
        if self.robots_parser and not self.robots_parser.can_fetch(self.config.user_agent, url):
            logger.debug(f"Blocked by robots.txt: {url}")
            return

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

                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type.lower():
                        logger.debug(f"Skipping non-HTML: {url} ({content_type})")
                        return

                    html = response.text
                    page = self._extract_page_data(url, str(response.url), response.status_code, html, load_time_ms, depth, dict(response.headers))

                    if self.storage and self.config.store_html:
                        await self._store_html(page, html)

                    self.results.append(page)

                    for link in page.internal_links:
                        link_url = link.get("url", "")
                        if link_url and link_url not in self.visited_urls:
                            await self.url_queue.put((link_url, depth + 1))

            except httpx.TimeoutException:
                logger.warning(f"Timeout: {url}")
                self.results.append(CrawledPage(
                    url=url, final_url=url, status_code=0,
                    content_type="", load_time_ms=self.config.timeout_seconds * 1000,
                    crawl_timestamp=datetime.utcnow().isoformat(),
                    crawl_depth=depth, errors=["Request timed out"],
                ))
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                self.results.append(CrawledPage(
                    url=url, final_url=url, status_code=0,
                    content_type="", load_time_ms=0,
                    crawl_timestamp=datetime.utcnow().isoformat(),
                    crawl_depth=depth, errors=[str(e)],
                ))

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

            if parsed.netloc == self.domain or parsed.netloc.endswith(f".{self.domain}"):
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
        """Fetch and parse robots.txt."""
        robots_url = f"{self.base_url}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    self.robots_parser = RobotFileParser()
                    self.robots_parser.parse(response.text.splitlines())
                    logger.info(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt: {e}")


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

    robots_info = await fetch_robots_txt(site_url)
    sitemap_info = await fetch_sitemap(site_url, robots_info.get("content"))

    config = CrawlConfig(max_pages=max_pages, store_html=bool(tenant_id))
    crawler = SEOmanCrawler(
        site_url=site_url,
        config=config,
        tenant_id=tenant_id,
        site_id=site_id,
        crawl_id=crawl_id,
    )

    pages = await crawler.crawl()

    return pages, robots_info, sitemap_info


def pages_to_dict_list(pages: list[CrawledPage]) -> list[dict]:
    """Convert CrawledPage objects to dict list for database storage."""
    return [page.to_dict() for page in pages]
