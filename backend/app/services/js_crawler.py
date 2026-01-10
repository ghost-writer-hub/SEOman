"""
SEOman JS Crawler Service

Headless browser-based crawler for JavaScript-rendered pages using Playwright.
Handles SPAs, React, Vue, Angular, and other JS-heavy frameworks.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Playwright imports with graceful fallback
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None
    PlaywrightTimeout = TimeoutError  # Use built-in TimeoutError as fallback
    logger.warning("Playwright not available. JS rendering will be disabled.")


@dataclass
class JSRenderedPage:
    """Result of JS rendering a page."""
    url: str
    final_url: str
    status_code: int
    html: str
    load_time_ms: int
    render_time_ms: int
    timestamp: str

    # Performance metrics
    dom_content_loaded_ms: int = 0
    load_event_ms: int = 0

    # JS execution info
    console_errors: list[str] = field(default_factory=list)
    network_requests: int = 0
    js_errors: list[str] = field(default_factory=list)

    # Screenshot (optional)
    screenshot_path: str = ""

    # Detection info
    spa_detected: bool = False
    framework_detected: str = ""

    errors: list[str] = field(default_factory=list)
    success: bool = True


@dataclass
class JSCrawlConfig:
    """Configuration for JS rendering."""
    timeout_ms: int = 30000
    wait_until: str = "networkidle"  # load, domcontentloaded, networkidle
    wait_after_load_ms: int = 1000  # Additional wait after page load
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = "SEOmanBot/2.0 (+https://seoman.ai/bot; JS renderer)"
    block_resources: list[str] = field(default_factory=lambda: ["font", "media"])
    take_screenshot: bool = False
    screenshot_full_page: bool = False
    max_concurrent_pages: int = 3
    browser_type: str = "chromium"  # chromium, firefox, webkit
    headless: bool = True
    ignore_https_errors: bool = True


class JSCrawler:
    """
    Headless browser crawler for JavaScript-rendered pages.

    Uses Playwright to render pages and extract content after JS execution.
    """

    def __init__(self, config: JSCrawlConfig | None = None):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Run: pip install playwright && playwright install chromium")

        self.config = config or JSCrawlConfig()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._playwright = None
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_pages)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        """Start the browser instance."""
        if self._browser is not None:
            return

        logger.info(f"Starting Playwright {self.config.browser_type} browser")
        self._playwright = await async_playwright().start()

        browser_launcher = getattr(self._playwright, self.config.browser_type)
        self._browser = await browser_launcher.launch(
            headless=self.config.headless,
        )

        self._context = await self._browser.new_context(
            viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
            user_agent=self.config.user_agent,
            ignore_https_errors=self.config.ignore_https_errors,
            java_script_enabled=True,
        )

        logger.info("Playwright browser started successfully")

    async def stop(self):
        """Stop the browser instance."""
        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Playwright browser stopped")

    async def render_page(self, url: str) -> JSRenderedPage:
        """
        Render a single page with JavaScript.

        Args:
            url: URL to render

        Returns:
            JSRenderedPage with rendered HTML and metadata
        """
        if not self._browser:
            await self.start()

        async with self._semaphore:
            return await self._render_page_internal(url)

    async def _render_page_internal(self, url: str) -> JSRenderedPage:
        """Internal method to render a page."""
        page: Page | None = None
        start_time = time.time()
        console_errors: list[str] = []
        js_errors: list[str] = []
        network_requests = 0

        try:
            page = await self._context.new_page()

            # Set up event listeners
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: js_errors.append(str(err)))

            # Track network requests
            async def on_request(request):
                nonlocal network_requests
                network_requests += 1

            page.on("request", on_request)

            # Block unnecessary resources to speed up rendering
            if self.config.block_resources:
                await page.route("**/*", lambda route: self._handle_route(route))

            # Navigate to the page
            render_start = time.time()

            response = await page.goto(
                url,
                timeout=self.config.timeout_ms,
                wait_until=self.config.wait_until,
            )

            # Wait additional time for dynamic content
            if self.config.wait_after_load_ms > 0:
                await page.wait_for_timeout(self.config.wait_after_load_ms)

            render_time_ms = int((time.time() - render_start) * 1000)

            # Get performance metrics
            metrics = await self._get_performance_metrics(page)

            # Get final URL after redirects
            final_url = page.url

            # Get rendered HTML
            html = await page.content()

            # Detect SPA/framework
            spa_detected, framework = await self._detect_spa_framework(page, html)

            # Take screenshot if configured
            screenshot_path = ""
            if self.config.take_screenshot:
                screenshot_path = await self._take_screenshot(page, url)

            load_time_ms = int((time.time() - start_time) * 1000)

            return JSRenderedPage(
                url=url,
                final_url=final_url,
                status_code=response.status if response else 0,
                html=html,
                load_time_ms=load_time_ms,
                render_time_ms=render_time_ms,
                timestamp=datetime.utcnow().isoformat(),
                dom_content_loaded_ms=metrics.get("dom_content_loaded", 0),
                load_event_ms=metrics.get("load_event", 0),
                console_errors=console_errors[:20],
                network_requests=network_requests,
                js_errors=js_errors[:10],
                screenshot_path=screenshot_path,
                spa_detected=spa_detected,
                framework_detected=framework,
                success=True,
            )

        except PlaywrightTimeout:
            logger.warning(f"Timeout rendering {url}")
            return JSRenderedPage(
                url=url,
                final_url=url,
                status_code=0,
                html="",
                load_time_ms=self.config.timeout_ms,
                render_time_ms=self.config.timeout_ms,
                timestamp=datetime.utcnow().isoformat(),
                errors=["Timeout waiting for page to load"],
                success=False,
            )

        except Exception as e:
            logger.error(f"Error rendering {url}: {e}")
            return JSRenderedPage(
                url=url,
                final_url=url,
                status_code=0,
                html="",
                load_time_ms=int((time.time() - start_time) * 1000),
                render_time_ms=0,
                timestamp=datetime.utcnow().isoformat(),
                errors=[str(e)],
                success=False,
            )

        finally:
            if page:
                await page.close()

    async def _handle_route(self, route):
        """Handle resource blocking."""
        resource_type = route.request.resource_type
        if resource_type in self.config.block_resources:
            await route.abort()
        else:
            await route.continue_()

    async def _get_performance_metrics(self, page: Page) -> dict:
        """Get performance timing metrics."""
        try:
            metrics = await page.evaluate("""
                () => {
                    const timing = performance.timing;
                    return {
                        dom_content_loaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                        load_event: timing.loadEventEnd - timing.navigationStart,
                    };
                }
            """)
            return metrics
        except Exception:
            return {}

    async def _detect_spa_framework(self, page: Page, html: str) -> tuple[bool, str]:
        """
        Detect if page is a SPA and identify the framework.

        Returns:
            Tuple of (is_spa, framework_name)
        """
        try:
            # Check for common SPA frameworks via JavaScript
            framework = await page.evaluate("""
                () => {
                    // React
                    if (window.React || document.querySelector('[data-reactroot]') ||
                        document.querySelector('[data-reactid]') || window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
                        return 'react';
                    }
                    // Vue.js
                    if (window.Vue || window.__VUE__ || document.querySelector('[data-v-]')) {
                        return 'vue';
                    }
                    // Angular
                    if (window.angular || window.ng || document.querySelector('[ng-version]') ||
                        document.querySelector('[_ngcontent-]')) {
                        return 'angular';
                    }
                    // Next.js
                    if (window.__NEXT_DATA__ || document.querySelector('#__next')) {
                        return 'nextjs';
                    }
                    // Nuxt.js
                    if (window.__NUXT__ || document.querySelector('#__nuxt')) {
                        return 'nuxt';
                    }
                    // Svelte
                    if (document.querySelector('[class*="svelte-"]')) {
                        return 'svelte';
                    }
                    // Gatsby
                    if (window.___gatsby) {
                        return 'gatsby';
                    }
                    // Ember
                    if (window.Ember || document.querySelector('[id^="ember"]')) {
                        return 'ember';
                    }
                    // Generic SPA detection
                    if (document.querySelector('#app') || document.querySelector('#root')) {
                        const body = document.body.innerHTML;
                        if (body.length < 500 && document.querySelectorAll('script').length > 3) {
                            return 'unknown-spa';
                        }
                    }
                    return '';
                }
            """)

            is_spa = bool(framework)

            # Additional HTML-based detection
            if not is_spa:
                soup = BeautifulSoup(html, "lxml")
                body = soup.find("body")
                if body:
                    body_text = body.get_text(strip=True)
                    scripts = soup.find_all("script", src=True)
                    # Likely SPA if minimal body content but many scripts
                    if len(body_text) < 200 and len(scripts) > 5:
                        is_spa = True
                        framework = "suspected-spa"

            return is_spa, framework

        except Exception as e:
            logger.debug(f"SPA detection error: {e}")
            return False, ""

    async def _take_screenshot(self, page: Page, url: str) -> str:
        """Take a screenshot of the page."""
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            screenshot_path = f"/tmp/screenshots/{url_hash}.png"

            await page.screenshot(
                path=screenshot_path,
                full_page=self.config.screenshot_full_page,
            )
            return screenshot_path
        except Exception as e:
            logger.warning(f"Screenshot failed for {url}: {e}")
            return ""

    async def render_batch(self, urls: list[str]) -> list[JSRenderedPage]:
        """
        Render multiple pages concurrently.

        Args:
            urls: List of URLs to render

        Returns:
            List of JSRenderedPage results
        """
        if not self._browser:
            await self.start()

        tasks = [self.render_page(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                processed.append(JSRenderedPage(
                    url=url,
                    final_url=url,
                    status_code=0,
                    html="",
                    load_time_ms=0,
                    render_time_ms=0,
                    timestamp=datetime.utcnow().isoformat(),
                    errors=[str(result)],
                    success=False,
                ))
            else:
                processed.append(result)

        return processed


def detect_spa_from_html(html: str) -> tuple[bool, str, list[str]]:
    """
    Detect if HTML likely requires JS rendering.

    Args:
        html: Raw HTML content

    Returns:
        Tuple of (needs_js_rendering, detected_framework, reasons)
    """
    soup = BeautifulSoup(html, "lxml")
    reasons = []
    framework = ""

    # Get body content
    body = soup.find("body")
    body_text = body.get_text(strip=True) if body else ""

    # Count scripts
    scripts = soup.find_all("script", src=True)
    inline_scripts = soup.find_all("script", src=False)

    # Check for React
    if soup.find(attrs={"data-reactroot": True}) or soup.find(attrs={"data-reactid": True}):
        framework = "react"
        reasons.append("React root element detected")

    # Check for Vue
    if soup.find(attrs={"data-v-": True}) or soup.find(id="app"):
        if not framework:
            framework = "vue"
        reasons.append("Vue.js markers detected")

    # Check for Angular
    if soup.find(attrs={"ng-version": True}) or soup.find(attrs={"_ngcontent-": True}):
        framework = "angular"
        reasons.append("Angular markers detected")

    # Check for Next.js
    if soup.find(id="__next"):
        framework = "nextjs"
        reasons.append("Next.js root element detected")

    # Check for Nuxt
    if soup.find(id="__nuxt"):
        framework = "nuxt"
        reasons.append("Nuxt.js root element detected")

    # Check for minimal content with many scripts
    if len(body_text) < 300 and len(scripts) > 5:
        reasons.append(f"Minimal body content ({len(body_text)} chars) with {len(scripts)} external scripts")

    # Check for common SPA patterns
    root_div = soup.find(id="root") or soup.find(id="app")
    if root_div and len(root_div.get_text(strip=True)) < 100:
        reasons.append("Empty or minimal root container element")

    # Check for loading indicators
    loading_indicators = soup.find_all(class_=lambda x: x and "loading" in x.lower() if x else False)
    if loading_indicators:
        reasons.append("Loading indicators found in HTML")

    # Check for noscript fallback
    noscript = soup.find("noscript")
    if noscript:
        noscript_text = noscript.get_text(strip=True)
        if "javascript" in noscript_text.lower() or "enable" in noscript_text.lower():
            reasons.append("Noscript tag suggests JS requirement")

    needs_js = bool(reasons)

    return needs_js, framework, reasons


async def should_use_js_rendering(url: str, html: str, word_count: int) -> tuple[bool, str]:
    """
    Determine if a page should be re-crawled with JS rendering.

    Args:
        url: Page URL
        html: Raw HTML from HTTP request
        word_count: Word count from initial crawl

    Returns:
        Tuple of (should_render, reason)
    """
    needs_js, framework, reasons = detect_spa_from_html(html)

    if needs_js:
        return True, f"SPA detected ({framework or 'unknown'}): {', '.join(reasons[:2])}"

    # Very low word count might indicate JS-rendered content
    if word_count < 50:
        return True, f"Very low word count ({word_count}), may need JS rendering"

    # Check for common JS framework script sources
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script", src=True)

    js_frameworks = ["react", "vue", "angular", "next", "nuxt", "gatsby", "svelte"]
    for script in scripts:
        src = script.get("src", "").lower()
        for fw in js_frameworks:
            if fw in src:
                return True, f"JavaScript framework detected in script: {fw}"

    return False, "No JS rendering needed"


# Convenience function for one-off rendering
async def render_url(url: str, config: JSCrawlConfig | None = None) -> JSRenderedPage:
    """
    Render a single URL with JavaScript.

    Convenience function that handles browser lifecycle.

    Args:
        url: URL to render
        config: Optional configuration

    Returns:
        JSRenderedPage with rendered content
    """
    async with JSCrawler(config) as crawler:
        return await crawler.render_page(url)
