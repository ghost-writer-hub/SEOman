"""
Keyword Tools for LangGraph Agents

Tools for keyword research and analysis.
"""

from typing import Dict, Any, List
from langchain_core.tools import tool

from app.integrations.dataforseo import DataForSEOClient
from app.integrations.llm import get_llm_client, cluster_keywords as llm_cluster_keywords


@tool
async def discover_keywords(
    seed_keyword: str,
    location: str = "United States",
    language: str = "en",
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Discover related keywords from a seed keyword.
    
    Args:
        seed_keyword: The seed keyword to expand
        location: Target location (default: United States)
        language: Target language code (default: en)
        limit: Maximum number of keywords to return (default: 50)
    
    Returns:
        List of discovered keywords with metrics
    """
    client = DataForSEOClient()
    
    result = await client.get_keyword_ideas(
        keyword=seed_keyword,
        location_name=location,
        language_code=language,
        limit=limit,
    )
    
    if not result.get("success"):
        return {"error": result.get("error", "Keyword discovery failed")}
    
    keywords = result.get("keywords", [])
    
    return {
        "success": True,
        "seed_keyword": seed_keyword,
        "keywords_found": len(keywords),
        "keywords": keywords,
    }


@tool
async def get_keyword_metrics(
    keywords: List[str],
    location: str = "United States",
    language: str = "en",
) -> Dict[str, Any]:
    """
    Get search metrics for a list of keywords.
    
    Args:
        keywords: List of keywords to analyze
        location: Target location
        language: Target language code
    
    Returns:
        Metrics including search volume, CPC, competition
    """
    client = DataForSEOClient()
    
    result = await client.get_search_volume(
        keywords=keywords,
        location_name=location,
        language_code=language,
    )
    
    if not result.get("success"):
        return {"error": result.get("error", "Failed to get keyword metrics")}
    
    return {
        "success": True,
        "keywords": result.get("keywords", []),
    }


@tool
async def cluster_keywords(keywords: List[str]) -> Dict[str, Any]:
    """
    Cluster keywords by topic and search intent using AI.
    
    Args:
        keywords: List of keywords to cluster
    
    Returns:
        Clustered keywords with intent classification
    """
    if len(keywords) < 3:
        return {"error": "Need at least 3 keywords to cluster"}
    
    llm = get_llm_client()
    
    if not await llm.health_check():
        return {"error": "LLM service unavailable"}
    
    result = await llm_cluster_keywords(llm, keywords)
    
    return {
        "success": True,
        "clusters": result.get("clusters", []),
    }


@tool
async def analyze_serp(
    keyword: str,
    location: str = "United States",
    language: str = "en",
) -> Dict[str, Any]:
    """
    Analyze SERP (Search Engine Results Page) for a keyword.
    
    Args:
        keyword: The keyword to analyze
        location: Target location
        language: Target language
    
    Returns:
        SERP analysis including top results and features
    """
    client = DataForSEOClient()
    
    result = await client.get_serp(
        keyword=keyword,
        location_name=location,
        language_code=language,
    )
    
    if not result.get("success"):
        return {"error": result.get("error", "SERP analysis failed")}
    
    organic = result.get("organic", [])
    
    return {
        "success": True,
        "keyword": keyword,
        "results_count": len(organic),
        "top_results": organic[:10],
        "serp_features": result.get("features", []),
    }
