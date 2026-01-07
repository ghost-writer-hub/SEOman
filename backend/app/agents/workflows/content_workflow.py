"""
Content Workflow

LangGraph workflow for content generation and optimization.

Flow:
1. Analyze SERP competitors
2. Generate content brief
3. Generate content draft
4. Analyze content SEO
5. Optimize content (if needed)
"""

from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from app.agents.tools import (
    analyze_serp,
    generate_brief,
    generate_draft,
    analyze_content,
    optimize_content,
)
from app.integrations.llm import get_llm_client, Message


class ContentState(TypedDict):
    """State for content workflow."""
    # Input
    target_keyword: str
    location: str
    language: str
    target_word_count: int
    # Process state
    serp_data: Optional[Dict[str, Any]]
    competitors: Optional[List[Dict[str, Any]]]
    brief: Optional[Dict[str, Any]]
    draft: Optional[str]
    seo_analysis: Optional[Dict[str, Any]]
    # Output
    final_content: Optional[str]
    content_score: Optional[int]
    metadata: Optional[Dict[str, Any]]
    error: Optional[str]
    completed: bool


async def analyze_competitors_node(state: ContentState) -> Dict[str, Any]:
    """Analyze SERP to understand competitors."""
    result = await analyze_serp.ainvoke({
        "keyword": state["target_keyword"],
        "location": state.get("location", "United States"),
        "language": state.get("language", "en"),
    })
    
    if result.get("error"):
        # Non-fatal: continue without competitor data
        return {
            "serp_data": {},
            "competitors": [],
        }
    
    # Extract competitor info
    competitors = []
    for item in result.get("top_results", [])[:5]:
        competitors.append({
            "url": item.get("url", ""),
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "position": item.get("position", 0),
        })
    
    return {
        "serp_data": result,
        "competitors": competitors,
    }


async def generate_brief_node(state: ContentState) -> Dict[str, Any]:
    """Generate content brief."""
    if state.get("error"):
        return {}
    
    result = await generate_brief.ainvoke({
        "keyword": state["target_keyword"],
        "competitors": state.get("competitors", []),
    })
    
    if result.get("error"):
        return {"error": result["error"], "completed": True}
    
    return {"brief": result.get("brief", {})}


async def generate_draft_node(state: ContentState) -> Dict[str, Any]:
    """Generate content draft from brief."""
    if state.get("error"):
        return {}
    
    brief = state.get("brief", {})
    outline = brief.get("content_outline", [])
    keywords_to_include = brief.get("keywords_to_include", [])
    target_word_count = state.get("target_word_count", 1500)
    
    # Use suggested word count from brief if available
    if brief.get("target_word_count"):
        target_word_count = max(target_word_count, brief["target_word_count"])
    
    result = await generate_draft.ainvoke({
        "keyword": state["target_keyword"],
        "outline": outline,
        "target_word_count": target_word_count,
        "keywords_to_include": keywords_to_include,
    })
    
    if result.get("error"):
        return {"error": result["error"], "completed": True}
    
    return {"draft": result.get("content", "")}


async def analyze_seo_node(state: ContentState) -> Dict[str, Any]:
    """Analyze draft for SEO."""
    if state.get("error"):
        return {}
    
    draft = state.get("draft", "")
    if not draft:
        return {"seo_analysis": {"score": 0, "issues": [{"message": "No content to analyze"}]}}
    
    result = await analyze_content.ainvoke({
        "content": draft,
        "target_keyword": state["target_keyword"],
    })
    
    if result.get("error"):
        # Non-fatal: continue with draft as-is
        return {"seo_analysis": {"score": 70, "issues": []}}
    
    return {
        "seo_analysis": result,
        "content_score": result.get("score", 70),
    }


async def optimize_content_node(state: ContentState) -> Dict[str, Any]:
    """Optimize content if score is below threshold."""
    if state.get("error"):
        return {"completed": True}
    
    draft = state.get("draft", "")
    seo_analysis = state.get("seo_analysis", {})
    score = seo_analysis.get("score", 100)
    
    # If score is good, use draft as final
    if score >= 80:
        return {
            "final_content": draft,
            "completed": True,
        }
    
    # Build optimization instructions from issues
    issues = seo_analysis.get("issues", [])
    instructions = []
    
    for issue in issues:
        issue_type = issue.get("type", "")
        message = issue.get("message", "")
        
        if issue_type == "word_count":
            instructions.append("Expand the content with more detailed information and examples")
        elif issue_type == "keyword_density":
            instructions.append(f"Increase usage of the target keyword naturally: {message}")
        elif issue_type == "keyword_stuffing":
            instructions.append("Reduce keyword usage to sound more natural")
        elif issue_type == "missing_h1":
            instructions.append("Add a clear H1 heading at the beginning")
        elif issue_type == "few_headings":
            instructions.append("Add more subheadings to improve structure")
        else:
            instructions.append(message)
    
    if not instructions:
        return {
            "final_content": draft,
            "completed": True,
        }
    
    # Optimize
    result = await optimize_content.ainvoke({
        "content": draft,
        "target_keyword": state["target_keyword"],
        "instructions": "; ".join(instructions),
    })
    
    if result.get("error"):
        # Use original draft
        return {
            "final_content": draft,
            "completed": True,
        }
    
    return {
        "final_content": result.get("optimized_content", draft),
        "completed": True,
    }


async def finalize_node(state: ContentState) -> Dict[str, Any]:
    """Finalize content and build metadata."""
    final_content = state.get("final_content", state.get("draft", ""))
    brief = state.get("brief", {})
    
    # Build metadata
    metadata = {
        "target_keyword": state["target_keyword"],
        "word_count": len(final_content.split()),
        "seo_score": state.get("content_score", 70),
        "title_suggestions": brief.get("title_suggestions", []),
        "meta_description": brief.get("meta_description", ""),
        "internal_linking_suggestions": brief.get("internal_linking_suggestions", []),
        "competitors_analyzed": len(state.get("competitors", [])),
    }
    
    return {
        "metadata": metadata,
        "completed": True,
    }


def should_continue(state: ContentState) -> str:
    """Determine if workflow should continue."""
    if state.get("error"):
        return "end"
    return "continue"


def should_optimize(state: ContentState) -> str:
    """Determine if content needs optimization."""
    if state.get("error"):
        return "end"
    
    score = state.get("content_score", 0)
    if score >= 80:
        return "finalize"
    return "optimize"


class ContentWorkflow:
    """LangGraph workflow for content generation."""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the workflow graph."""
        workflow = StateGraph(ContentState)
        
        # Add nodes
        workflow.add_node("analyze_competitors", analyze_competitors_node)
        workflow.add_node("generate_brief", generate_brief_node)
        workflow.add_node("generate_draft", generate_draft_node)
        workflow.add_node("analyze_seo", analyze_seo_node)
        workflow.add_node("optimize_content", optimize_content_node)
        workflow.add_node("finalize", finalize_node)
        
        # Add edges
        workflow.set_entry_point("analyze_competitors")
        
        workflow.add_edge("analyze_competitors", "generate_brief")
        
        workflow.add_conditional_edges(
            "generate_brief",
            should_continue,
            {
                "continue": "generate_draft",
                "end": END,
            },
        )
        
        workflow.add_conditional_edges(
            "generate_draft",
            should_continue,
            {
                "continue": "analyze_seo",
                "end": END,
            },
        )
        
        workflow.add_conditional_edges(
            "analyze_seo",
            should_optimize,
            {
                "optimize": "optimize_content",
                "finalize": "finalize",
                "end": END,
            },
        )
        
        workflow.add_edge("optimize_content", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def run(
        self,
        target_keyword: str,
        location: str = "United States",
        language: str = "en",
        target_word_count: int = 1500,
    ) -> ContentState:
        """Run the content workflow."""
        initial_state: ContentState = {
            "target_keyword": target_keyword,
            "location": location,
            "language": language,
            "target_word_count": target_word_count,
            "serp_data": None,
            "competitors": None,
            "brief": None,
            "draft": None,
            "seo_analysis": None,
            "final_content": None,
            "content_score": None,
            "metadata": None,
            "error": None,
            "completed": False,
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result


async def run_content_workflow(
    target_keyword: str,
    location: str = "United States",
    language: str = "en",
    target_word_count: int = 1500,
) -> Dict[str, Any]:
    """
    Convenience function to run the content workflow.
    
    Args:
        target_keyword: The target keyword for the content
        location: Target location for SERP analysis
        language: Target language code
        target_word_count: Target word count for the content
    
    Returns:
        Generated content with metadata
    """
    workflow = ContentWorkflow()
    result = await workflow.run(target_keyword, location, language, target_word_count)
    
    if result.get("error"):
        return {
            "success": False,
            "error": result["error"],
        }
    
    return {
        "success": True,
        "target_keyword": target_keyword,
        "content": result.get("final_content", ""),
        "brief": result.get("brief", {}),
        "seo_analysis": result.get("seo_analysis", {}),
        "metadata": result.get("metadata", {}),
    }
