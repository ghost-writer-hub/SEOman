"""
Plan Workflow

LangGraph workflow for generating comprehensive SEO improvement plans.

Flow:
1. Run site audit (or use provided audit)
2. Run keyword research (or use provided keywords)
3. Analyze opportunities
4. Generate prioritized action plan
5. Create content calendar
"""

from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END

from app.agents.tools import (
    run_site_audit,
    analyze_issues,
    discover_keywords,
    cluster_keywords,
    get_site_info,
)
from app.integrations.llm import get_llm_client, Message


class PlanState(TypedDict):
    """State for plan workflow."""
    # Input
    url: str
    seed_keywords: List[str]
    location: str
    language: str
    plan_duration_weeks: int
    # Provided data (optional - skip fetch if provided)
    provided_audit: Optional[Dict[str, Any]]
    provided_keywords: Optional[List[Dict[str, Any]]]
    # Process state
    site_info: Optional[Dict[str, Any]]
    audit_results: Optional[Dict[str, Any]]
    keyword_data: Optional[List[Dict[str, Any]]]
    keyword_clusters: Optional[List[Dict[str, Any]]]
    opportunities: Optional[List[Dict[str, Any]]]
    # Output
    action_plan: Optional[List[Dict[str, Any]]]
    content_calendar: Optional[List[Dict[str, Any]]]
    summary: Optional[Dict[str, Any]]
    error: Optional[str]
    completed: bool


async def get_site_info_node(state: PlanState) -> Dict[str, Any]:
    """Get basic site information."""
    result = await get_site_info.ainvoke({"url": state["url"]})
    
    if result.get("error"):
        # Non-fatal: continue without site info
        return {"site_info": {}}
    
    return {"site_info": result}


async def run_audit_node(state: PlanState) -> Dict[str, Any]:
    """Run or use provided audit."""
    # Use provided audit if available
    if state.get("provided_audit"):
        return {"audit_results": state["provided_audit"]}
    
    result = await run_site_audit.ainvoke({
        "url": state["url"],
        "max_pages": 50,  # Lighter audit for planning
    })
    
    if result.get("error"):
        # Non-fatal: continue without audit
        return {"audit_results": {"score": 70, "issues": []}}
    
    return {"audit_results": result}


async def gather_keywords_node(state: PlanState) -> Dict[str, Any]:
    """Gather keywords from seeds or use provided."""
    # Use provided keywords if available
    if state.get("provided_keywords"):
        return {"keyword_data": state["provided_keywords"]}
    
    seed_keywords = state.get("seed_keywords", [])
    if not seed_keywords:
        return {"keyword_data": []}
    
    all_keywords = []
    
    # Discover keywords for first 3 seeds
    for seed in seed_keywords[:3]:
        result = await discover_keywords.ainvoke({
            "seed_keyword": seed,
            "location": state.get("location", "United States"),
            "language": state.get("language", "en"),
            "limit": 20,
        })
        
        if result.get("keywords"):
            all_keywords.extend(result["keywords"])
    
    return {"keyword_data": all_keywords}


async def cluster_keywords_node(state: PlanState) -> Dict[str, Any]:
    """Cluster keywords by topic and intent."""
    keywords = state.get("keyword_data", [])
    
    if len(keywords) < 3:
        return {"keyword_clusters": []}
    
    # Extract keyword strings
    keyword_strings = []
    for kw in keywords:
        if isinstance(kw, dict):
            keyword_strings.append(kw.get("keyword", ""))
        else:
            keyword_strings.append(str(kw))
    
    keyword_strings = [k for k in keyword_strings if k][:50]  # Limit
    
    if len(keyword_strings) < 3:
        return {"keyword_clusters": []}
    
    result = await cluster_keywords.ainvoke({"keywords": keyword_strings})
    
    if result.get("error"):
        return {"keyword_clusters": []}
    
    return {"keyword_clusters": result.get("clusters", [])}


async def analyze_opportunities_node(state: PlanState) -> Dict[str, Any]:
    """Analyze opportunities from audit and keywords."""
    audit = state.get("audit_results", {})
    clusters = state.get("keyword_clusters", [])
    site_info = state.get("site_info", {})
    
    opportunities = []
    
    # Technical opportunities from audit
    issues = audit.get("issues", [])
    severity_priority = {"critical": 1, "high": 2, "medium": 3, "low": 4}
    
    # Group issues by type
    issue_groups: Dict[str, List[Dict]] = {}
    for issue in issues:
        issue_type = issue.get("type", "other")
        if issue_type not in issue_groups:
            issue_groups[issue_type] = []
        issue_groups[issue_type].append(issue)
    
    # Add technical opportunities
    for issue_type, type_issues in issue_groups.items():
        if type_issues:
            worst_severity = min(
                severity_priority.get(i.get("severity", "low"), 4)
                for i in type_issues
            )
            opportunities.append({
                "type": "technical",
                "category": issue_type,
                "title": f"Fix {issue_type.replace('_', ' ').title()} Issues",
                "description": f"Found {len(type_issues)} {issue_type} issues to fix",
                "priority": worst_severity,
                "effort": "medium" if len(type_issues) > 3 else "low",
                "impact": "high" if worst_severity <= 2 else "medium",
                "affected_pages": len(type_issues),
            })
    
    # Content opportunities from keyword clusters
    for cluster in clusters:
        cluster_name = cluster.get("name", "")
        intent = cluster.get("intent", "")
        keywords = cluster.get("keywords", [])
        
        if keywords:
            opportunities.append({
                "type": "content",
                "category": "new_content",
                "title": f"Create Content for: {cluster_name}",
                "description": f"Target {len(keywords)} keywords with {intent} intent",
                "priority": 2 if intent == "transactional" else 3,
                "effort": "high",
                "impact": "high" if len(keywords) > 5 else "medium",
                "target_keywords": keywords[:5],
                "recommended_content_type": cluster.get("recommended_content_type", "Blog post"),
            })
    
    # Site structure opportunities
    if site_info:
        if site_info.get("h1_count", 0) == 0:
            opportunities.append({
                "type": "technical",
                "category": "on_page",
                "title": "Add Missing H1 Tag",
                "description": "Homepage is missing H1 heading",
                "priority": 2,
                "effort": "low",
                "impact": "medium",
            })
    
    # Sort by priority
    opportunities.sort(key=lambda x: x.get("priority", 5))
    
    return {"opportunities": opportunities}


async def generate_action_plan_node(state: PlanState) -> Dict[str, Any]:
    """Generate prioritized action plan."""
    opportunities = state.get("opportunities", [])
    duration_weeks = state.get("plan_duration_weeks", 12)
    
    llm = get_llm_client()
    
    # Build action items from opportunities
    action_plan = []
    
    # Phase 1: Quick Wins (Week 1-2)
    quick_wins = [o for o in opportunities if o.get("effort") == "low"]
    for idx, opp in enumerate(quick_wins[:5]):
        action_plan.append({
            "phase": 1,
            "phase_name": "Quick Wins",
            "week_start": 1,
            "week_end": 2,
            "priority": idx + 1,
            "task": opp["title"],
            "description": opp.get("description", ""),
            "type": opp["type"],
            "effort": opp["effort"],
            "expected_impact": opp.get("impact", "medium"),
        })
    
    # Phase 2: Technical Fixes (Week 2-4)
    technical = [o for o in opportunities if o["type"] == "technical" and o.get("effort") != "low"]
    for idx, opp in enumerate(technical[:5]):
        action_plan.append({
            "phase": 2,
            "phase_name": "Technical Optimization",
            "week_start": 2,
            "week_end": 4,
            "priority": len(action_plan) + 1,
            "task": opp["title"],
            "description": opp.get("description", ""),
            "type": opp["type"],
            "effort": opp["effort"],
            "expected_impact": opp.get("impact", "medium"),
        })
    
    # Phase 3: Content Creation (Week 4-duration)
    content = [o for o in opportunities if o["type"] == "content"]
    weeks_for_content = max(4, duration_weeks - 4)
    content_per_two_weeks = max(1, len(content) // (weeks_for_content // 2))
    
    current_week = 4
    for idx, opp in enumerate(content[:10]):
        action_plan.append({
            "phase": 3,
            "phase_name": "Content Strategy",
            "week_start": current_week,
            "week_end": min(current_week + 2, duration_weeks),
            "priority": len(action_plan) + 1,
            "task": opp["title"],
            "description": opp.get("description", ""),
            "type": opp["type"],
            "effort": opp["effort"],
            "expected_impact": opp.get("impact", "medium"),
            "target_keywords": opp.get("target_keywords", []),
            "content_type": opp.get("recommended_content_type", ""),
        })
        
        if (idx + 1) % content_per_two_weeks == 0:
            current_week = min(current_week + 2, duration_weeks - 2)
    
    return {"action_plan": action_plan}


async def generate_content_calendar_node(state: PlanState) -> Dict[str, Any]:
    """Generate content calendar from action plan."""
    action_plan = state.get("action_plan", [])
    duration_weeks = state.get("plan_duration_weeks", 12)
    
    # Filter content tasks
    content_tasks = [a for a in action_plan if a["type"] == "content"]
    
    calendar = []
    start_date = datetime.now()
    
    for task in content_tasks:
        week_start = task.get("week_start", 1)
        publish_date = start_date + timedelta(weeks=week_start)
        
        calendar.append({
            "week": week_start,
            "publish_date": publish_date.strftime("%Y-%m-%d"),
            "title": task["task"],
            "content_type": task.get("content_type", "Blog post"),
            "target_keywords": task.get("target_keywords", []),
            "status": "planned",
            "notes": task.get("description", ""),
        })
    
    # Sort by week
    calendar.sort(key=lambda x: x["week"])
    
    return {"content_calendar": calendar}


async def generate_summary_node(state: PlanState) -> Dict[str, Any]:
    """Generate plan summary."""
    audit = state.get("audit_results", {})
    opportunities = state.get("opportunities", [])
    action_plan = state.get("action_plan", [])
    content_calendar = state.get("content_calendar", [])
    clusters = state.get("keyword_clusters", [])
    duration_weeks = state.get("plan_duration_weeks", 12)
    
    # Calculate stats
    technical_tasks = len([a for a in action_plan if a["type"] == "technical"])
    content_tasks = len([a for a in action_plan if a["type"] == "content"])
    total_keywords = sum(len(c.get("keywords", [])) for c in clusters)
    
    summary = {
        "url": state["url"],
        "current_score": audit.get("score", 0),
        "plan_duration_weeks": duration_weeks,
        "total_opportunities": len(opportunities),
        "total_action_items": len(action_plan),
        "technical_tasks": technical_tasks,
        "content_tasks": content_tasks,
        "keyword_clusters": len(clusters),
        "total_keywords": total_keywords,
        "content_pieces_planned": len(content_calendar),
        "phases": [
            {
                "number": 1,
                "name": "Quick Wins",
                "weeks": "1-2",
                "focus": "Low-effort, high-impact fixes",
                "tasks": len([a for a in action_plan if a.get("phase") == 1]),
            },
            {
                "number": 2,
                "name": "Technical Optimization",
                "weeks": "2-4",
                "focus": "Technical SEO improvements",
                "tasks": len([a for a in action_plan if a.get("phase") == 2]),
            },
            {
                "number": 3,
                "name": "Content Strategy",
                "weeks": f"4-{duration_weeks}",
                "focus": "Content creation and optimization",
                "tasks": len([a for a in action_plan if a.get("phase") == 3]),
            },
        ],
        "expected_outcomes": [
            f"Fix {technical_tasks} technical issues",
            f"Create {content_tasks} new content pieces",
            f"Target {total_keywords} keywords across {len(clusters)} topic clusters",
            f"Improve SEO score from {audit.get('score', 0)} to 85+",
        ],
    }
    
    return {
        "summary": summary,
        "completed": True,
    }


def should_continue(state: PlanState) -> str:
    """Determine if workflow should continue."""
    if state.get("error"):
        return "end"
    return "continue"


class PlanWorkflow:
    """LangGraph workflow for SEO plan generation."""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the workflow graph."""
        workflow = StateGraph(PlanState)
        
        # Add nodes
        workflow.add_node("get_site_info", get_site_info_node)
        workflow.add_node("run_audit", run_audit_node)
        workflow.add_node("gather_keywords", gather_keywords_node)
        workflow.add_node("cluster_keywords", cluster_keywords_node)
        workflow.add_node("analyze_opportunities", analyze_opportunities_node)
        workflow.add_node("generate_action_plan", generate_action_plan_node)
        workflow.add_node("generate_content_calendar", generate_content_calendar_node)
        workflow.add_node("generate_summary", generate_summary_node)
        
        # Add edges - mostly sequential flow
        workflow.set_entry_point("get_site_info")
        
        workflow.add_edge("get_site_info", "run_audit")
        workflow.add_edge("run_audit", "gather_keywords")
        workflow.add_edge("gather_keywords", "cluster_keywords")
        workflow.add_edge("cluster_keywords", "analyze_opportunities")
        workflow.add_edge("analyze_opportunities", "generate_action_plan")
        workflow.add_edge("generate_action_plan", "generate_content_calendar")
        workflow.add_edge("generate_content_calendar", "generate_summary")
        workflow.add_edge("generate_summary", END)
        
        return workflow.compile()
    
    async def run(
        self,
        url: str,
        seed_keywords: List[str],
        location: str = "United States",
        language: str = "en",
        plan_duration_weeks: int = 12,
        provided_audit: Optional[Dict[str, Any]] = None,
        provided_keywords: Optional[List[Dict[str, Any]]] = None,
    ) -> PlanState:
        """Run the plan workflow."""
        initial_state: PlanState = {
            "url": url,
            "seed_keywords": seed_keywords,
            "location": location,
            "language": language,
            "plan_duration_weeks": plan_duration_weeks,
            "provided_audit": provided_audit,
            "provided_keywords": provided_keywords,
            "site_info": None,
            "audit_results": None,
            "keyword_data": None,
            "keyword_clusters": None,
            "opportunities": None,
            "action_plan": None,
            "content_calendar": None,
            "summary": None,
            "error": None,
            "completed": False,
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result


async def run_plan_workflow(
    url: str,
    seed_keywords: List[str],
    location: str = "United States",
    language: str = "en",
    plan_duration_weeks: int = 12,
    provided_audit: Optional[Dict[str, Any]] = None,
    provided_keywords: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run the plan workflow.
    
    Args:
        url: The URL to plan for
        seed_keywords: List of seed keywords
        location: Target location
        language: Target language
        plan_duration_weeks: Plan duration in weeks
        provided_audit: Pre-existing audit results (optional)
        provided_keywords: Pre-existing keyword data (optional)
    
    Returns:
        SEO improvement plan with action items and calendar
    """
    workflow = PlanWorkflow()
    result = await workflow.run(
        url=url,
        seed_keywords=seed_keywords,
        location=location,
        language=language,
        plan_duration_weeks=plan_duration_weeks,
        provided_audit=provided_audit,
        provided_keywords=provided_keywords,
    )
    
    if result.get("error"):
        return {
            "success": False,
            "error": result["error"],
        }
    
    return {
        "success": True,
        "url": url,
        "summary": result.get("summary", {}),
        "action_plan": result.get("action_plan", []),
        "content_calendar": result.get("content_calendar", []),
        "opportunities": result.get("opportunities", []),
        "keyword_clusters": result.get("keyword_clusters", []),
    }
