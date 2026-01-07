"""
Python SEO Analyzer client for quick audits.
"""
import httpx
from typing import Any

from app.config import settings


class SEOAnalyzerClient:
    """HTTP client for python-seo-analyzer service."""
    
    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = base_url or settings.PYTHON_SEOANALYZER_URL
        self.timeout = timeout or settings.PYTHON_SEOANALYZER_TIMEOUT
    
    async def health_check(self) -> bool:
        """Check if the analyzer service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def analyze_site(
        self,
        url: str,
        sitemap: str | None = None,
        analyze_headings: bool = True,
        analyze_extra_tags: bool = True,
    ) -> dict[str, Any]:
        """
        Analyze a website and return SEO issues.
        
        Args:
            url: The URL to analyze
            sitemap: Optional sitemap URL
            analyze_headings: Whether to analyze headings
            analyze_extra_tags: Whether to analyze extra meta tags
        
        Returns:
            Dictionary with analysis results
        """
        params = {
            "url": url,
            "analyze_headings": analyze_headings,
            "analyze_extra_tags": analyze_extra_tags,
        }
        if sitemap:
            params["sitemap"] = sitemap
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/analyze",
                params=params,
            )
            response.raise_for_status()
            return response.json()
    
    def parse_issues(self, analysis_result: dict) -> list[dict]:
        """
        Parse analysis results into structured issues.
        
        Args:
            analysis_result: Raw analysis result from analyzer
        
        Returns:
            List of structured issue dictionaries
        """
        issues = []
        
        # Parse different issue types
        for page in analysis_result.get("pages", []):
            url = page.get("url", "")
            
            # Check title issues
            title = page.get("title", "")
            if not title:
                issues.append({
                    "type": "missing_title",
                    "category": "On-Page",
                    "severity": "high",
                    "title": "Missing Title Tag",
                    "description": f"The page is missing a title tag.",
                    "suggested_fix": "Add a unique, descriptive title tag between 50-60 characters.",
                    "affected_urls": [url],
                })
            elif len(title) < 30:
                issues.append({
                    "type": "short_title",
                    "category": "On-Page",
                    "severity": "medium",
                    "title": "Title Tag Too Short",
                    "description": f"The title tag is only {len(title)} characters.",
                    "suggested_fix": "Expand the title to 50-60 characters for better SEO.",
                    "affected_urls": [url],
                })
            elif len(title) > 60:
                issues.append({
                    "type": "long_title",
                    "category": "On-Page",
                    "severity": "low",
                    "title": "Title Tag Too Long",
                    "description": f"The title tag is {len(title)} characters and may be truncated.",
                    "suggested_fix": "Shorten the title to under 60 characters.",
                    "affected_urls": [url],
                })
            
            # Check meta description
            description = page.get("description", "")
            if not description:
                issues.append({
                    "type": "missing_description",
                    "category": "On-Page",
                    "severity": "high",
                    "title": "Missing Meta Description",
                    "description": "The page is missing a meta description.",
                    "suggested_fix": "Add a compelling meta description between 150-160 characters.",
                    "affected_urls": [url],
                })
            elif len(description) < 70:
                issues.append({
                    "type": "short_description",
                    "category": "On-Page",
                    "severity": "medium",
                    "title": "Meta Description Too Short",
                    "description": f"The meta description is only {len(description)} characters.",
                    "suggested_fix": "Expand the description to 150-160 characters.",
                    "affected_urls": [url],
                })
            
            # Check H1
            h1_tags = page.get("h1", [])
            if not h1_tags:
                issues.append({
                    "type": "missing_h1",
                    "category": "On-Page",
                    "severity": "high",
                    "title": "Missing H1 Tag",
                    "description": "The page is missing an H1 heading.",
                    "suggested_fix": "Add a single H1 tag containing your primary keyword.",
                    "affected_urls": [url],
                })
            elif len(h1_tags) > 1:
                issues.append({
                    "type": "multiple_h1",
                    "category": "On-Page",
                    "severity": "medium",
                    "title": "Multiple H1 Tags",
                    "description": f"The page has {len(h1_tags)} H1 tags instead of one.",
                    "suggested_fix": "Use only one H1 tag per page.",
                    "affected_urls": [url],
                })
            
            # Check word count
            word_count = page.get("word_count", 0)
            if word_count < 300:
                issues.append({
                    "type": "thin_content",
                    "category": "Content",
                    "severity": "high",
                    "title": "Thin Content",
                    "description": f"The page only has {word_count} words.",
                    "suggested_fix": "Add more valuable content, aim for at least 500-1000 words.",
                    "affected_urls": [url],
                })
        
        return issues
    
    def calculate_score(self, issues: list[dict]) -> int:
        """
        Calculate an SEO score based on issues.
        
        Args:
            issues: List of issues
        
        Returns:
            Score from 0-100
        """
        score = 100
        
        severity_penalties = {
            "critical": 15,
            "high": 10,
            "medium": 5,
            "low": 2,
        }
        
        for issue in issues:
            severity = issue.get("severity", "low")
            penalty = severity_penalties.get(severity, 1)
            score -= penalty
        
        return max(0, score)
