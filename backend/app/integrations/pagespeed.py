"""
Google PageSpeed Insights API client.

Provides Core Web Vitals analysis and performance metrics.
"""
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class PageSpeedClient:
    """HTTP client for Google PageSpeed Insights API."""

    BASE_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    # Core Web Vitals thresholds (milliseconds or ratio)
    CWV_THRESHOLDS = {
        "lcp": {"good": 2500, "needs_improvement": 4000},
        "fid": {"good": 100, "needs_improvement": 300},
        "cls": {"good": 0.1, "needs_improvement": 0.25},
        "fcp": {"good": 1800, "needs_improvement": 3000},
        "ttfb": {"good": 800, "needs_improvement": 1800},
        "inp": {"good": 200, "needs_improvement": 500},
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.PAGESPEED_API_KEY
        self.timeout = settings.PAGESPEED_TIMEOUT

    async def analyze(
        self,
        url: str,
        strategy: str = "mobile",
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a URL with PageSpeed Insights.

        Args:
            url: The URL to analyze
            strategy: 'mobile' or 'desktop'
            categories: List of categories to analyze (default: ['performance'])

        Returns:
            Parsed analysis results with score, metrics, and opportunities
        """
        if not self.api_key:
            logger.warning("PageSpeed API key not configured")
            return {
                "success": False,
                "error": "PageSpeed API key not configured",
                "url": url,
                "strategy": strategy,
            }

        categories = categories or ["performance"]

        params = {
            "url": url,
            "strategy": strategy,
            "key": self.api_key,
        }

        # Add categories
        for cat in categories:
            params[f"category"] = cat

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"[PSI] Analyzing {url} ({strategy})")
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            return self._parse_response(data, url, strategy)

        except httpx.TimeoutException:
            logger.error(f"[PSI] Timeout analyzing {url}")
            return {
                "success": False,
                "error": "Request timeout",
                "url": url,
                "strategy": strategy,
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            if e.response.status_code == 429:
                error_msg = "Rate limit exceeded"
            elif e.response.status_code == 400:
                error_msg = "Invalid URL or request"
            logger.error(f"[PSI] Error analyzing {url}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "url": url,
                "strategy": strategy,
            }
        except Exception as e:
            logger.error(f"[PSI] Unexpected error analyzing {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "strategy": strategy,
            }

    async def analyze_batch(
        self,
        urls: list[str],
        strategy: str = "mobile",
        delay_seconds: float = 1.0,
    ) -> list[dict[str, Any]]:
        """
        Analyze multiple URLs sequentially.

        Args:
            urls: List of URLs to analyze
            strategy: 'mobile' or 'desktop'
            delay_seconds: Delay between requests to respect rate limits

        Returns:
            List of analysis results
        """
        import asyncio

        results = []
        for i, url in enumerate(urls):
            result = await self.analyze(url, strategy)
            results.append(result)

            # Add delay between requests (except for last one)
            if i < len(urls) - 1:
                await asyncio.sleep(delay_seconds)

        return results

    def _parse_response(
        self,
        data: dict,
        url: str,
        strategy: str,
    ) -> dict[str, Any]:
        """Parse PSI API response into structured format."""
        lighthouse = data.get("lighthouseResult", {})
        loading_experience = data.get("loadingExperience", {})

        # Extract performance score (0-100)
        categories = lighthouse.get("categories", {})
        performance = categories.get("performance", {})
        score = performance.get("score")
        performance_score = int(score * 100) if score is not None else None

        # Extract Core Web Vitals from lab data
        audits = lighthouse.get("audits", {})
        metrics = self._extract_metrics(audits)

        # Extract field data (CrUX) if available
        field_data = self._extract_field_data(loading_experience)

        # Extract opportunities
        opportunities = self._extract_opportunities(audits)

        # Extract diagnostics
        diagnostics = self._extract_diagnostics(audits)

        # Determine CWV status
        cwv_status = self._calculate_cwv_status(metrics)

        return {
            "success": True,
            "url": url,
            "strategy": strategy,
            "performance_score": performance_score,
            "metrics": metrics,
            "field_data": field_data,
            "opportunities": opportunities,
            "diagnostics": diagnostics,
            "cwv_status": cwv_status,
        }

    def _extract_metrics(self, audits: dict) -> dict[str, Any]:
        """Extract Core Web Vitals and other metrics from audits."""
        metrics = {}

        # Largest Contentful Paint
        lcp = audits.get("largest-contentful-paint", {})
        if lcp.get("numericValue") is not None:
            metrics["lcp_ms"] = int(lcp["numericValue"])

        # First Input Delay (or INP if available)
        # Note: PSI uses TBT as a proxy for interactivity
        tbt = audits.get("total-blocking-time", {})
        if tbt.get("numericValue") is not None:
            metrics["tbt_ms"] = int(tbt["numericValue"])

        # Cumulative Layout Shift
        cls = audits.get("cumulative-layout-shift", {})
        if cls.get("numericValue") is not None:
            metrics["cls"] = round(cls["numericValue"], 3)

        # First Contentful Paint
        fcp = audits.get("first-contentful-paint", {})
        if fcp.get("numericValue") is not None:
            metrics["fcp_ms"] = int(fcp["numericValue"])

        # Time to First Byte (Server Response Time)
        ttfb = audits.get("server-response-time", {})
        if ttfb.get("numericValue") is not None:
            metrics["ttfb_ms"] = int(ttfb["numericValue"])

        # Speed Index
        si = audits.get("speed-index", {})
        if si.get("numericValue") is not None:
            metrics["speed_index_ms"] = int(si["numericValue"])

        # Interactive (Time to Interactive)
        tti = audits.get("interactive", {})
        if tti.get("numericValue") is not None:
            metrics["tti_ms"] = int(tti["numericValue"])

        return metrics

    def _extract_field_data(self, loading_experience: dict) -> dict[str, Any]:
        """Extract Chrome User Experience Report (CrUX) field data."""
        if not loading_experience or not loading_experience.get("metrics"):
            return {}

        field_metrics = loading_experience.get("metrics", {})
        field_data = {}

        # Map PSI field metric names to our names
        metric_map = {
            "LARGEST_CONTENTFUL_PAINT_MS": "lcp_ms",
            "FIRST_INPUT_DELAY_MS": "fid_ms",
            "CUMULATIVE_LAYOUT_SHIFT_SCORE": "cls",
            "FIRST_CONTENTFUL_PAINT_MS": "fcp_ms",
            "INTERACTION_TO_NEXT_PAINT": "inp_ms",
            "EXPERIMENTAL_TIME_TO_FIRST_BYTE": "ttfb_ms",
        }

        for psi_name, our_name in metric_map.items():
            metric = field_metrics.get(psi_name, {})
            if metric.get("percentile"):
                value = metric["percentile"]
                # CLS is a ratio, others are milliseconds
                if our_name == "cls":
                    value = value / 100  # PSI returns CLS * 100
                field_data[our_name] = value

            # Also capture distribution
            if metric.get("distributions"):
                field_data[f"{our_name}_distribution"] = metric["distributions"]

        # Overall category from CrUX
        if loading_experience.get("overall_category"):
            field_data["overall_category"] = loading_experience["overall_category"]

        return field_data

    def _extract_opportunities(self, audits: dict) -> list[dict[str, Any]]:
        """Extract optimization opportunities from audits."""
        opportunities = []

        # Opportunity audit IDs
        opportunity_ids = [
            "render-blocking-resources",
            "unused-css-rules",
            "unused-javascript",
            "modern-image-formats",
            "offscreen-images",
            "unminified-css",
            "unminified-javascript",
            "efficient-animated-content",
            "uses-optimized-images",
            "uses-responsive-images",
            "uses-text-compression",
            "server-response-time",
            "redirects",
            "uses-rel-preconnect",
            "uses-rel-preload",
            "font-display",
            "third-party-summary",
            "lcp-lazy-loaded",
        ]

        for audit_id in opportunity_ids:
            audit = audits.get(audit_id, {})

            # Only include if there's a potential savings
            if audit.get("score") is not None and audit["score"] < 1:
                savings_ms = audit.get("numericValue", 0)
                savings_bytes = 0

                # Extract byte savings from details
                details = audit.get("details", {})
                if details.get("overallSavingsBytes"):
                    savings_bytes = details["overallSavingsBytes"]
                if details.get("overallSavingsMs"):
                    savings_ms = details["overallSavingsMs"]

                opportunities.append({
                    "id": audit_id,
                    "title": audit.get("title", audit_id),
                    "description": audit.get("description", ""),
                    "score": audit.get("score", 0),
                    "savings_ms": int(savings_ms) if savings_ms else 0,
                    "savings_bytes": int(savings_bytes) if savings_bytes else 0,
                    "display_value": audit.get("displayValue", ""),
                })

        # Sort by potential savings (ms first, then bytes)
        opportunities.sort(key=lambda x: (x["savings_ms"], x["savings_bytes"]), reverse=True)

        return opportunities

    def _extract_diagnostics(self, audits: dict) -> dict[str, Any]:
        """Extract diagnostic information from audits."""
        diagnostics = {}

        # Diagnostic audit IDs
        diagnostic_ids = [
            "largest-contentful-paint-element",
            "layout-shift-elements",
            "long-tasks",
            "main-thread-tasks",
            "bootup-time",
            "mainthread-work-breakdown",
            "dom-size",
            "network-requests",
            "resource-summary",
            "third-party-facades",
            "critical-request-chains",
        ]

        for audit_id in diagnostic_ids:
            audit = audits.get(audit_id, {})
            if audit:
                diagnostics[audit_id] = {
                    "title": audit.get("title", ""),
                    "description": audit.get("description", ""),
                    "display_value": audit.get("displayValue", ""),
                    "score": audit.get("score"),
                }

                # Include details for specific diagnostics
                if audit_id in ["dom-size", "bootup-time", "mainthread-work-breakdown"]:
                    details = audit.get("details", {})
                    if details.get("items"):
                        diagnostics[audit_id]["items"] = details["items"][:10]

        return diagnostics

    def _calculate_cwv_status(self, metrics: dict) -> str:
        """
        Calculate overall Core Web Vitals status.

        Returns: 'good', 'needs_improvement', or 'poor'
        """
        statuses = []

        # Check LCP
        lcp = metrics.get("lcp_ms")
        if lcp is not None:
            if lcp <= self.CWV_THRESHOLDS["lcp"]["good"]:
                statuses.append("good")
            elif lcp <= self.CWV_THRESHOLDS["lcp"]["needs_improvement"]:
                statuses.append("needs_improvement")
            else:
                statuses.append("poor")

        # Check CLS
        cls = metrics.get("cls")
        if cls is not None:
            if cls <= self.CWV_THRESHOLDS["cls"]["good"]:
                statuses.append("good")
            elif cls <= self.CWV_THRESHOLDS["cls"]["needs_improvement"]:
                statuses.append("needs_improvement")
            else:
                statuses.append("poor")

        # Check TBT (proxy for INP/FID)
        tbt = metrics.get("tbt_ms")
        if tbt is not None:
            # TBT thresholds are different - using 200ms/600ms
            if tbt <= 200:
                statuses.append("good")
            elif tbt <= 600:
                statuses.append("needs_improvement")
            else:
                statuses.append("poor")

        if not statuses:
            return "unknown"

        # Overall status is the worst of all metrics
        if "poor" in statuses:
            return "poor"
        elif "needs_improvement" in statuses:
            return "needs_improvement"
        else:
            return "good"

    async def health_check(self) -> bool:
        """Check if the API key is valid and service is accessible."""
        if not self.api_key:
            return False

        try:
            # Test with a simple, fast URL
            result = await self.analyze("https://www.google.com", strategy="desktop")
            return result.get("success", False)
        except Exception:
            return False
