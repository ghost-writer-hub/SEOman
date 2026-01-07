"""
Audit Workflow

LangGraph workflow for running comprehensive SEO audits with AI analysis.

Flow:
1. Get site info
2. Run SEO audit
3. Analyze issues with AI
4. Generate recommendations
"""

from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from app.agents.tools import (
    run_site_audit,
    get_audit_results,
    analyze_issues,
    get_site_info,
)
from app.integrations.llm import get_llm_client, Message


class AuditState(TypedDict):
    """State for audit workflow."""
    # Input
    url: str
    max_pages: int
    # Process state
    site_info: Optional[Dict[str, Any]]
    audit_results: Optional[Dict[str, Any]]
    issues: Optional[List[Dict[str, Any]]]
    ai_analysis: Optional[Dict[str, Any]]
    # Output
    recommendations: Optional[List[Dict[str, Any]]]
    score: Optional[int]
    error: Optional[str]
    completed: bool


async def get_site_info_node(state: AuditState) -> Dict[str, Any]:
    """Get basic site information."""
    result = await get_site_info.ainvoke({"url": state["url"]})
    
    if result.get("error"):
        return {"error": result["error"], "completed": True}
    
    return {"site_info": result}


async def run_audit_node(state: AuditState) -> Dict[str, Any]:
    """Run the SEO audit."""
    if state.get("error"):
        return {}
    
    result = await run_site_audit.ainvoke({
        "url": state["url"],
        "max_pages": state.get("max_pages", 100),
    })
    
    if result.get("error"):
        return {"error": result["error"], "completed": True}
    
    return {
        "audit_results": result,
        "issues": result.get("issues", []),
        "score": result.get("score", 0),
    }


async def analyze_issues_node(state: AuditState) -> Dict[str, Any]:
    """Analyze issues with AI."""
    if state.get("error"):
        return {}
    
    issues = state.get("issues", [])
    if not issues:
        return {"ai_analysis": {"summary": "No issues found", "priority_issues": []}}
    
    result = await analyze_issues.ainvoke({
        "url": state["url"],
        "issues": issues,
    })
    
    if result.get("error"):
        # Non-fatal: continue without AI analysis
        return {"ai_analysis": {"error": result["error"]}}
    
    return {"ai_analysis": result.get("analysis", {})}


async def generate_recommendations_node(state: AuditState) -> Dict[str, Any]:
    """Generate actionable recommendations."""
    if state.get("error"):
        return {"completed": True}
    
    ai_analysis = state.get("ai_analysis", {})
    audit_results = state.get("audit_results", {})
    site_info = state.get("site_info", {})
    
    # Build recommendations from AI analysis and audit results
    recommendations = []
    
    # Add priority issues from AI analysis
    priority_issues = ai_analysis.get("priority_issues", [])
    for idx, issue in enumerate(priority_issues[:10]):
        recommendations.append({
            "priority": idx + 1,
            "category": "ai_recommendation",
            "issue": issue.get("issue", ""),
            "severity": issue.get("severity", "medium"),
            "recommendation": issue.get("recommendation", ""),
            "estimated_impact": issue.get("estimated_impact", "unknown"),
        })
    
    # Add quick wins
    quick_wins = ai_analysis.get("quick_wins", [])
    for idx, win in enumerate(quick_wins[:5]):
        recommendations.append({
            "priority": len(recommendations) + 1,
            "category": "quick_win",
            "issue": win,
            "severity": "low",
            "recommendation": win,
            "estimated_impact": "quick implementation",
        })
    
    # Add technical issues from audit
    for issue in audit_results.get("issues", [])[:10]:
        if not any(r.get("issue") == issue.get("message") for r in recommendations):
            recommendations.append({
                "priority": len(recommendations) + 1,
                "category": "technical",
                "issue": issue.get("message", ""),
                "severity": issue.get("severity", "medium"),
                "recommendation": f"Fix: {issue.get('message', '')}",
                "page": issue.get("page", ""),
            })
    
    return {
        "recommendations": recommendations[:20],  # Top 20 recommendations
        "completed": True,
    }


def should_continue(state: AuditState) -> str:
    """Determine if workflow should continue or end."""
    if state.get("error"):
        return "end"
    return "continue"


class AuditWorkflow:
    """LangGraph workflow for SEO audits."""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the workflow graph."""
        workflow = StateGraph(AuditState)
        
        # Add nodes
        workflow.add_node("get_site_info", get_site_info_node)
        workflow.add_node("run_audit", run_audit_node)
        workflow.add_node("analyze_issues", analyze_issues_node)
        workflow.add_node("generate_recommendations", generate_recommendations_node)
        
        # Add edges
        workflow.set_entry_point("get_site_info")
        
        workflow.add_conditional_edges(
            "get_site_info",
            should_continue,
            {
                "continue": "run_audit",
                "end": END,
            },
        )
        
        workflow.add_conditional_edges(
            "run_audit",
            should_continue,
            {
                "continue": "analyze_issues",
                "end": END,
            },
        )
        
        workflow.add_edge("analyze_issues", "generate_recommendations")
        workflow.add_edge("generate_recommendations", END)
        
        return workflow.compile()
    
    async def run(self, url: str, max_pages: int = 100) -> AuditState:
        """Run the audit workflow."""
        initial_state: AuditState = {
            "url": url,
            "max_pages": max_pages,
            "site_info": None,
            "audit_results": None,
            "issues": None,
            "ai_analysis": None,
            "recommendations": None,
            "score": None,
            "error": None,
            "completed": False,
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result


async def run_audit_workflow(url: str, max_pages: int = 100) -> Dict[str, Any]:
    """
    Convenience function to run the audit workflow.
    
    Args:
        url: The URL to audit
        max_pages: Maximum pages to analyze
    
    Returns:
        Audit results with recommendations
    """
    workflow = AuditWorkflow()
    result = await workflow.run(url, max_pages)
    
    if result.get("error"):
        return {
            "success": False,
            "error": result["error"],
        }
    
    return {
        "success": True,
        "url": url,
        "score": result.get("score"),
        "site_info": result.get("site_info"),
        "issues_found": len(result.get("issues", [])),
        "ai_analysis": result.get("ai_analysis"),
        "recommendations": result.get("recommendations", []),
    }
