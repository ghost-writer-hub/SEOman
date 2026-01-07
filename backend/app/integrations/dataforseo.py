"""
DataForSEO API client for keyword research.
"""
import base64
from typing import Any

import httpx

from app.config import settings


class DataForSEOClient:
    """HTTP client for DataForSEO API."""
    
    BASE_URL = "https://api.dataforseo.com/v3"
    
    def __init__(
        self,
        login: str | None = None,
        password: str | None = None,
    ):
        self.login = login or settings.DATAFORSEO_API_LOGIN
        self.password = password or settings.DATAFORSEO_API_PASSWORD
        
        # Create basic auth header
        credentials = f"{self.login}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded}"
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to DataForSEO."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            if method.upper() == "POST":
                response = await client.post(url, json=data, headers=headers)
            else:
                response = await client.get(url, headers=headers)
            
            response.raise_for_status()
            return response.json()
    
    async def keywords_for_site(
        self,
        domain: str,
        country: str = "US",
        language: str = "en",
        limit: int = 100,
    ) -> list[dict]:
        """
        Get keywords for a domain.
        
        Uses the Keywords for Site endpoint to discover keywords
        that a domain is ranking for.
        """
        data = [{
            "target": domain,
            "location_code": self._get_location_code(country),
            "language_code": language,
            "include_serp_info": True,
            "include_subdomains": True,
            "limit": limit,
        }]
        
        result = await self._request("POST", "/dataforseo_labs/google/keywords_for_site/live", data)
        
        keywords = []
        if result.get("tasks"):
            for task in result["tasks"]:
                if task.get("result"):
                    for item in task["result"]:
                        for kw in item.get("items", []):
                            keywords.append(self._parse_keyword(kw))
        
        return keywords
    
    async def keywords_for_keywords(
        self,
        seed_keywords: list[str],
        country: str = "US",
        language: str = "en",
        limit: int = 100,
    ) -> list[dict]:
        """
        Expand keywords from seed keywords.
        
        Uses the Related Keywords endpoint to find related keywords.
        """
        data = [{
            "keywords": seed_keywords,
            "location_code": self._get_location_code(country),
            "language_code": language,
            "limit": limit,
            "include_seed_keyword": True,
        }]
        
        result = await self._request("POST", "/dataforseo_labs/google/related_keywords/live", data)
        
        keywords = []
        if result.get("tasks"):
            for task in result["tasks"]:
                if task.get("result"):
                    for item in task["result"]:
                        for kw in item.get("items", []):
                            if kw.get("keyword_data"):
                                keywords.append(self._parse_keyword(kw["keyword_data"]))
        
        return keywords
    
    async def keyword_overview(
        self,
        keywords: list[str],
        country: str = "US",
        language: str = "en",
    ) -> list[dict]:
        """
        Get metrics for specific keywords.
        
        Uses the Keyword Overview endpoint for detailed metrics.
        """
        data = [{
            "keywords": keywords,
            "location_code": self._get_location_code(country),
            "language_code": language,
        }]
        
        result = await self._request("POST", "/dataforseo_labs/google/bulk_keyword_difficulty/live", data)
        
        keyword_data = []
        if result.get("tasks"):
            for task in result["tasks"]:
                if task.get("result"):
                    for item in task["result"]:
                        for kw in item.get("items", []):
                            keyword_data.append({
                                "text": kw.get("keyword"),
                                "difficulty": kw.get("keyword_difficulty"),
                            })
        
        return keyword_data
    
    async def serp_overview(
        self,
        keyword: str,
        country: str = "US",
        language: str = "en",
    ) -> dict:
        """
        Get SERP overview for a keyword.
        """
        data = [{
            "keyword": keyword,
            "location_code": self._get_location_code(country),
            "language_code": language,
        }]
        
        result = await self._request("POST", "/dataforseo_labs/google/serp_competitors/live", data)
        
        if result.get("tasks"):
            for task in result["tasks"]:
                if task.get("result"):
                    return task["result"][0] if task["result"] else {}
        
        return {}
    
    def _parse_keyword(self, kw_data: dict) -> dict:
        """Parse raw keyword data into structured format."""
        keyword_info = kw_data.get("keyword_info", kw_data)
        
        return {
            "text": kw_data.get("keyword") or keyword_info.get("keyword", ""),
            "search_volume": keyword_info.get("search_volume"),
            "cpc": keyword_info.get("cpc"),
            "competition": keyword_info.get("competition"),
            "difficulty": kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
            "intent": self._parse_intent(keyword_info.get("search_intent_info", {})),
            "trend": keyword_info.get("monthly_searches", []),
            "dataforseo_raw": kw_data,
        }
    
    def _parse_intent(self, intent_info: dict) -> str | None:
        """Parse search intent from DataForSEO response."""
        if not intent_info:
            return None
        
        intents = []
        for intent_type in ["informational", "navigational", "commercial", "transactional"]:
            if intent_info.get(intent_type):
                intents.append(intent_type)
        
        return intents[0] if intents else None
    
    def _get_location_code(self, country: str) -> int:
        """Get DataForSEO location code for a country."""
        location_codes = {
            "US": 2840,
            "GB": 2826,
            "CA": 2124,
            "AU": 2036,
            "DE": 2276,
            "FR": 2250,
            "ES": 2724,
            "IT": 2380,
            "BR": 2076,
            "MX": 2484,
        }
        return location_codes.get(country.upper(), 2840)
    
    def _get_location_name_code(self, location_name: str) -> int:
        """Get location code from location name."""
        location_name_codes = {
            "united states": 2840,
            "united kingdom": 2826,
            "canada": 2124,
            "australia": 2036,
            "germany": 2276,
            "france": 2250,
            "spain": 2724,
            "italy": 2380,
            "brazil": 2076,
            "mexico": 2484,
        }
        return location_name_codes.get(location_name.lower(), 2840)
    
    async def get_keyword_ideas(
        self,
        keyword: str,
        location_name: str = "United States",
        language_code: str = "en",
        limit: int = 100,
    ) -> dict:
        """
        Alias for keywords_for_keywords with single keyword.
        Returns format expected by keyword_tasks.py.
        """
        try:
            keywords = await self.keywords_for_keywords(
                seed_keywords=[keyword],
                country=self._country_from_location(location_name),
                language=language_code,
                limit=limit,
            )
            return {
                "success": True,
                "keywords": keywords,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "keywords": [],
            }
    
    async def get_serp(
        self,
        keyword: str,
        location_name: str = "United States",
        language_code: str = "en",
    ) -> dict:
        """
        Get SERP results for a keyword.
        Returns format expected by keyword_tasks.py.
        """
        try:
            data = [{
                "keyword": keyword,
                "location_code": self._get_location_name_code(location_name),
                "language_code": language_code,
                "depth": 100,
            }]
            
            result = await self._request("POST", "/serp/google/organic/live/regular", data)
            
            organic = []
            if result.get("tasks"):
                for task in result["tasks"]:
                    if task.get("result"):
                        for item in task["result"]:
                            for res in item.get("items", []):
                                if res.get("type") == "organic":
                                    organic.append({
                                        "url": res.get("url", ""),
                                        "title": res.get("title", ""),
                                        "description": res.get("description", ""),
                                        "position": res.get("rank_group"),
                                    })
            
            return {
                "success": True,
                "organic": organic,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "organic": [],
            }
    
    def _country_from_location(self, location_name: str) -> str:
        """Convert location name to country code."""
        location_to_country = {
            "united states": "US",
            "united kingdom": "GB",
            "canada": "CA",
            "australia": "AU",
            "germany": "DE",
            "france": "FR",
            "spain": "ES",
            "italy": "IT",
            "brazil": "BR",
            "mexico": "MX",
        }
        return location_to_country.get(location_name.lower(), "US")
