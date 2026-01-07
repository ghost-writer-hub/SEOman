"""
Keyword Workflow

LangGraph workflow for keyword research, metrics collection, and clustering.

Flow:
1. Discover keywords from seed
2. Get keyword metrics
3. Analyze SERP for top keywords
4. Cluster keywords by intent
5. Generate keyword strategy
"""

from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from app.agents.tools import (
    discover_keywords,
    get_keyword_metrics,
    cluster_keywords,
    analyze_serp,
)
from app.integrations.llm import get_llm_client, Message


class KeywordState(TypedDict):
    """State for keyword workflow."""
    # Input
    seed_keyword: str
    location: str
    language: str
    limit: int
    # Process state
    discovered_keywords: Optional[List[Dict[str, Any]]]
    keyword_metrics: Optional[List[Dict[str, Any]]]
    serp_analysis: Optional[Dict[str, Any]]
    clusters: Optional[List[Dict[str, Any]]]
    # Output
    strategy: Optional[Dict[str, Any]]
    error: Optional[str]
    completed: bool


async def discover_keywords_node(state: KeywordState) -> Dict[str, Any]:
    """Discover related keywords from seed."""
    result = await discover_keywords.ainvoke({
        "seed_keyword": state["seed_keyword"],
        "location": state.get("location", "United States"),
        "language": state.get("language", "en"),
        "limit": state.get("limit", 50),
    })
    
    if result.get("error"):
        return {"error": result["error"], "completed": True}
    
    return {"discovered_keywords": result.get("keywords", [])}


async def get_metrics_node(state: KeywordState) -> Dict[str, Any]:
    """Get metrics for discovered keywords."""
    if state.get("error"):
        return {}
    
    keywords = state.get("discovered_keywords", [])
    if not keywords:
        return {"keyword_metrics": []}
    
    # Extract keyword strings
    keyword_strings = [
        kw.get("keyword") if isinstance(kw, dict) else kw
        for kw in keywords[:30]  # Limit to 30 for API
    ]
    
    result = await get_keyword_metrics.ainvoke({
        "keywords": keyword_strings,
        "location": state.get("location", "United States"),
        "language": state.get("language", "en"),
    })
    
    if result.get("error"):
        # Non-fatal: continue with basic keyword data
        return {"keyword_metrics": keywords}
    
    return {"keyword_metrics": result.get("keywords", [])}


async def analyze_serp_node(state: KeywordState) -> Dict[str, Any]:
    """Analyze SERP for the seed keyword."""
    if state.get("error"):
        return {}
    
    result = await analyze_serp.ainvoke({
        "keyword": state["seed_keyword"],
        "location": state.get("location", "United States"),
        "language": state.get("language", "en"),
    })
    
    if result.get("error"):
        # Non-fatal: continue without SERP data
        return {"serp_analysis": {"error": result["error"]}}
    
    return {"serp_analysis": result}


async def cluster_keywords_node(state: KeywordState) -> Dict[str, Any]:
    """Cluster keywords by topic and intent."""
    if state.get("error"):
        return {}
    
    # Get keyword strings for clustering
    metrics = state.get("keyword_metrics", [])
    keyword_strings = []
    
    for kw in metrics:
        if isinstance(kw, dict):
            keyword_strings.append(kw.get("keyword", ""))
        else:
            keyword_strings.append(str(kw))
    
    # Filter empty strings
    keyword_strings = [k for k in keyword_strings if k]
    
    if len(keyword_strings) < 3:
        return {"clusters": [{"name": "All Keywords", "keywords": keyword_strings, "intent": "mixed"}]}
    
    result = await cluster_keywords.ainvoke({"keywords": keyword_strings})
    
    if result.get("error"):
        # Non-fatal: return unclustered
        return {"clusters": [{"name": "All Keywords", "keywords": keyword_strings, "intent": "mixed"}]}
    
    return {"clusters": result.get("clusters", [])}


async def generate_strategy_node(state: KeywordState) -> Dict[str, Any]:
    """Generate keyword strategy based on analysis."""
    if state.get("error"):
        return {"completed": True}
    
    llm = get_llm_client()
    
    # Build context
    clusters = state.get("clusters", [])
    metrics = state.get("keyword_metrics", [])
    serp = state.get("serp_analysis", {})
    
    # Sort keywords by search volume
    sorted_keywords = sorted(
        metrics,
        key=lambda x: x.get("search_volume", 0) if isinstance(x, dict) else 0,
        reverse=True,
    )
    
    # Build strategy
    strategy = {
        "seed_keyword": state["seed_keyword"],
        "total_keywords": len(metrics),
        "clusters_count": len(clusters),
        "clusters": [],
        "priority_keywords": [],
        "content_opportunities": [],
        "serp_insights": {},
    }
    
    # Add cluster summaries
    for cluster in clusters:
        cluster_keywords = cluster.get("keywords", [])
        # Find metrics for cluster keywords
        cluster_metrics = [
            m for m in metrics
            if isinstance(m, dict) and m.get("keyword") in cluster_keywords
        ]
        
        avg_volume = 0
        if cluster_metrics:
            volumes = [m.get("search_volume", 0) for m in cluster_metrics]
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
        
        strategy["clusters"].append({
            "name": cluster.get("name", ""),
            "intent": cluster.get("intent", ""),
            "keyword_count": len(cluster_keywords),
            "avg_search_volume": int(avg_volume),
            "recommended_content_type": cluster.get("recommended_content_type", ""),
            "top_keywords": cluster_keywords[:5],
        })
    
    # Priority keywords (high volume, reasonable competition)
    for kw in sorted_keywords[:10]:
        if isinstance(kw, dict):
            strategy["priority_keywords"].append({
                "keyword": kw.get("keyword", ""),
                "search_volume": kw.get("search_volume", 0),
                "competition": kw.get("competition", ""),
                "cpc": kw.get("cpc", 0),
            })
    
    # Content opportunities based on clusters
    for cluster in clusters:
        intent = cluster.get("intent", "").lower()
        content_type = cluster.get("recommended_content_type", "")
        
        opportunity = {
            "topic": cluster.get("name", ""),
            "target_intent": intent,
            "suggested_format": content_type or _suggest_format(intent),
            "target_keywords": cluster.get("keywords", [])[:5],
        }
        strategy["content_opportunities"].append(opportunity)
    
    # SERP insights
    if serp and not serp.get("error"):
        strategy["serp_insights"] = {
            "top_competitors": [
                r.get("domain", "") for r in serp.get("top_results", [])[:5]
            ],
            "serp_features": serp.get("serp_features", []),
            "content_types": _analyze_serp_content_types(serp.get("top_results", [])),
        }
    
    return {
        "strategy": strategy,
        "completed": True,
    }


def _suggest_format(intent: str) -> str:
    """Suggest content format based on intent."""
    intent_map = {
        "informational": "Blog post or guide",
        "transactional": "Product page or landing page",
        "commercial": "Comparison or review article",
        "navigational": "Category or pillar page",
    }
    return intent_map.get(intent, "Blog post")


def _analyze_serp_content_types(results: List[Dict[str, Any]]) -> List[str]:
    """Analyze content types in SERP results."""
    content_types = set()
    for result in results:
        url = result.get("url", "").lower()
        title = result.get("title", "").lower()
        
        if "blog" in url or "article" in url:
            content_types.add("Blog post")
        if "guide" in title or "how to" in title:
            content_types.add("Guide/Tutorial")
        if "review" in title:
            content_types.add("Review")
        if "best" in title or "top" in title:
            content_types.add("List/Roundup")
        if "vs" in title or "versus" in title:
            content_types.add("Comparison")
    
    return list(content_types) or ["Article"]


def should_continue(state: KeywordState) -> str:
    """Determine if workflow should continue."""
    if state.get("error"):
        return "end"
    return "continue"


class KeywordWorkflow:
    """LangGraph workflow for keyword research."""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the workflow graph."""
        workflow = StateGraph(KeywordState)
        
        # Add nodes
        workflow.add_node("discover_keywords", discover_keywords_node)
        workflow.add_node("get_metrics", get_metrics_node)
        workflow.add_node("analyze_serp", analyze_serp_node)
        workflow.add_node("cluster_keywords", cluster_keywords_node)
        workflow.add_node("generate_strategy", generate_strategy_node)
        
        # Add edges
        workflow.set_entry_point("discover_keywords")
        
        workflow.add_conditional_edges(
            "discover_keywords",
            should_continue,
            {
                "continue": "get_metrics",
                "end": END,
            },
        )
        
        # Get metrics and analyze SERP can run conceptually in sequence
        workflow.add_edge("get_metrics", "analyze_serp")
        workflow.add_edge("analyze_serp", "cluster_keywords")
        workflow.add_edge("cluster_keywords", "generate_strategy")
        workflow.add_edge("generate_strategy", END)
        
        return workflow.compile()
    
    async def run(
        self,
        seed_keyword: str,
        location: str = "United States",
        language: str = "en",
        limit: int = 50,
    ) -> KeywordState:
        """Run the keyword workflow."""
        initial_state: KeywordState = {
            "seed_keyword": seed_keyword,
            "location": location,
            "language": language,
            "limit": limit,
            "discovered_keywords": None,
            "keyword_metrics": None,
            "serp_analysis": None,
            "clusters": None,
            "strategy": None,
            "error": None,
            "completed": False,
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result


async def run_keyword_workflow(
    seed_keyword: str,
    location: str = "United States",
    language: str = "en",
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Convenience function to run the keyword workflow.
    
    Args:
        seed_keyword: The seed keyword to research
        location: Target location
        language: Target language code
        limit: Maximum keywords to discover
    
    Returns:
        Keyword research results with strategy
    """
    workflow = KeywordWorkflow()
    result = await workflow.run(seed_keyword, location, language, limit)
    
    if result.get("error"):
        return {
            "success": False,
            "error": result["error"],
        }
    
    return {
        "success": True,
        "seed_keyword": seed_keyword,
        "total_keywords": len(result.get("keyword_metrics", [])),
        "clusters": result.get("clusters", []),
        "serp_analysis": result.get("serp_analysis", {}),
        "strategy": result.get("strategy", {}),
    }
