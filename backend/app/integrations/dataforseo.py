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
        keyword_text = kw_data.get("keyword") or keyword_info.get("keyword", "")

        # Try API intent first, fall back to heuristic classification
        api_intent = self._parse_intent(keyword_info.get("search_intent_info", {}))
        intent = api_intent or self._classify_intent_heuristic(keyword_text)

        return {
            "text": keyword_text,
            "search_volume": keyword_info.get("search_volume"),
            "cpc": keyword_info.get("cpc"),
            "competition": keyword_info.get("competition"),
            "difficulty": kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
            "intent": intent,
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

    def _classify_intent_heuristic(self, keyword: str) -> str:
        """
        Classify search intent using keyword pattern analysis.

        Intent types:
        - transactional: User wants to complete an action (buy, book, reserve)
        - commercial: User is researching before purchase (best, reviews, compare)
        - informational: User seeks information (how, what, why, guide)
        - navigational: User looking for specific site/brand
        """
        keyword_lower = keyword.lower()

        # Transactional patterns - user wants to take action
        transactional_patterns = [
            "book", "reserve", "reserva", "reservar", "buy", "comprar", "purchase",
            "order", "price", "precio", "cheap", "barato", "discount", "descuento",
            "deal", "oferta", "coupon", "cupon", "sale", "booking", "disponibilidad",
            "availability", "quote", "presupuesto", "hire", "contratar"
        ]

        # Commercial patterns - user researching before decision
        commercial_patterns = [
            "best", "mejor", "top", "review", "reseña", "compare", "comparar",
            "vs", "versus", "alternative", "alternativa", "recommended", "recomendado",
            "rating", "valoracion", "opinion", "opiniones", "which", "cual",
            "worth", "value", "quality", "calidad"
        ]

        # Informational patterns - user seeking knowledge
        informational_patterns = [
            "how", "como", "what", "que", "why", "por que", "when", "cuando",
            "where", "donde", "who", "quien", "guide", "guia", "tutorial",
            "tips", "consejos", "ideas", "example", "ejemplo", "definition",
            "meaning", "significado", "history", "historia", "list", "lista"
        ]

        # Check for transactional intent (highest priority for commercial keywords)
        for pattern in transactional_patterns:
            if pattern in keyword_lower:
                return "transactional"

        # Check for commercial investigation
        for pattern in commercial_patterns:
            if pattern in keyword_lower:
                return "commercial"

        # Check for informational intent
        for pattern in informational_patterns:
            if pattern in keyword_lower:
                return "informational"

        # Navigational: specific brand/hotel names (check for proper nouns pattern)
        # Keywords with hotel names + location are typically navigational
        hotel_indicators = ["hotel", "hotels", "hoteles", "resort", "hostel"]
        location_indicators = ["mallorca", "barcelona", "tenerife", "lanzarote",
                               "menorca", "costa brava", "spain", "españa"]

        has_hotel = any(h in keyword_lower for h in hotel_indicators)
        has_location = any(loc in keyword_lower for loc in location_indicators)

        if has_hotel and has_location:
            # Hotel + location = likely commercial (researching options)
            return "commercial"
        elif has_hotel:
            # Just hotel name = navigational
            return "navigational"

        # Default to informational for general queries
        return "informational"
    
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

    async def get_serp_with_features(
        self,
        keyword: str,
        country: str = "US",
        language: str = "en",
        depth: int = 100,
    ) -> dict:
        """
        Get detailed SERP results including SERP features.

        Returns:
            - organic: List of organic results with position, url, title
            - serp_features: Dict of detected SERP features (featured_snippet, paa, local_pack, etc.)
            - competitor_positions: List of top 10 competitors with their positions
        """
        try:
            data = [{
                "keyword": keyword,
                "location_code": self._get_location_code(country),
                "language_code": language,
                "depth": depth,
            }]

            result = await self._request("POST", "/serp/google/organic/live/regular", data)

            organic = []
            serp_features = {
                "featured_snippet": False,
                "people_also_ask": False,
                "local_pack": False,
                "knowledge_panel": False,
                "video_carousel": False,
                "image_pack": False,
                "top_stories": False,
                "shopping_results": False,
                "sitelinks": False,
                "reviews": False,
            }
            all_items = []

            if result.get("tasks"):
                for task in result["tasks"]:
                    if task.get("result"):
                        for item in task["result"]:
                            items = item.get("items", [])
                            all_items = items

                            for res in items:
                                item_type = res.get("type", "")

                                # Collect organic results
                                if item_type == "organic":
                                    organic.append({
                                        "url": res.get("url", ""),
                                        "title": res.get("title", ""),
                                        "description": res.get("description", ""),
                                        "position": res.get("rank_group"),
                                        "domain": res.get("domain", ""),
                                    })

                                # Detect SERP features
                                if item_type == "featured_snippet":
                                    serp_features["featured_snippet"] = True
                                elif item_type == "people_also_ask":
                                    serp_features["people_also_ask"] = True
                                elif item_type == "local_pack":
                                    serp_features["local_pack"] = True
                                elif item_type == "knowledge_graph":
                                    serp_features["knowledge_panel"] = True
                                elif item_type == "video":
                                    serp_features["video_carousel"] = True
                                elif item_type == "images":
                                    serp_features["image_pack"] = True
                                elif item_type == "top_stories":
                                    serp_features["top_stories"] = True
                                elif item_type == "shopping":
                                    serp_features["shopping_results"] = True

                                # Check for sitelinks in organic results
                                if item_type == "organic" and res.get("links"):
                                    serp_features["sitelinks"] = True

                                # Check for reviews
                                if item_type == "organic" and res.get("rating"):
                                    serp_features["reviews"] = True

            # Build competitor positions (top 10)
            competitor_positions = [
                {
                    "position": r["position"],
                    "domain": r["domain"],
                    "url": r["url"],
                }
                for r in organic[:10]
            ]

            return {
                "success": True,
                "keyword": keyword,
                "organic": organic,
                "serp_features": serp_features,
                "competitor_positions": competitor_positions,
                "total_results": len(organic),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "keyword": keyword,
                "organic": [],
                "serp_features": {},
                "competitor_positions": [],
            }

    async def get_rankings_batch(
        self,
        keywords: list[str],
        country: str = "US",
        language: str = "en",
        batch_size: int = 10,
    ) -> list[dict]:
        """
        Get SERP rankings for multiple keywords in batches.

        Args:
            keywords: List of keywords to check
            country: Country code
            language: Language code
            batch_size: Number of keywords per API call (max 100)

        Returns:
            List of SERP results for each keyword
        """
        import asyncio

        results = []

        # Process in batches to avoid rate limits
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i + batch_size]

            # Run batch concurrently
            tasks = [
                self.get_serp_with_features(kw, country, language)
                for kw in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for kw, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "success": False,
                        "keyword": kw,
                        "error": str(result),
                        "organic": [],
                        "serp_features": {},
                        "competitor_positions": [],
                    })
                else:
                    results.append(result)

            # Small delay between batches to respect rate limits
            if i + batch_size < len(keywords):
                await asyncio.sleep(1)

        return results
    
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
