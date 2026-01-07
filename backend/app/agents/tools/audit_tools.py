"""
Audit Tools for LangGraph Agents

Tools for running and analyzing SEO audits.
"""

from typing import Dict, Any, List
from langchain_core.tools import tool

from app.integrations.seoanalyzer import SEOAnalyzerClient
from app.integrations.llm import get_llm_client, analyze_seo_issues


@tool
async def run_site_audit(url: str, max_pages: int = 100) -> Dict[str, Any]:
    """
    Run an SEO audit on a website.
    
    Args:
        url: The URL of the website to audit
        max_pages: Maximum number of pages to analyze (default 100)
    
    Returns:
        Audit results including score, issues, and page data
    """
    analyzer = SEOAnalyzerClient()
    
    result = await analyzer.analyze(
        url=url,
        follow_links=True,
        max_pages=max_pages,
    )
    
    if not result.get("success"):
        return {"error": result.get("error", "Audit failed")}
    
    # Calculate score
    issues = result.get("issues", [])
    score = 100
    
    severity_deductions = {
        "critical": 15,
        "high": 10,
        "medium": 5,
        "low": 2,
    }
    
    for issue in issues:
        severity = issue.get("severity", "low").lower()
        score -= severity_deductions.get(severity, 0)
    
    score = max(0, score)
    
    return {
        "success": True,
        "url": url,
        "score": score,
        "pages_analyzed": len(result.get("pages", [])),
        "issues_found": len(issues),
        "issues": issues[:20],  # Return top 20 issues
        "summary": {
            "critical": sum(1 for i in issues if i.get("severity") == "critical"),
            "high": sum(1 for i in issues if i.get("severity") == "high"),
            "medium": sum(1 for i in issues if i.get("severity") == "medium"),
            "low": sum(1 for i in issues if i.get("severity") == "low"),
        }
    }


@tool
async def get_audit_results(audit_id: str) -> Dict[str, Any]:
    """
    Get the results of a previous audit.
    
    Args:
        audit_id: The ID of the audit to retrieve
    
    Returns:
        Audit results including score and issues
    """
    # This would normally fetch from database
    # For now, return a placeholder
    return {
        "audit_id": audit_id,
        "status": "completed",
        "message": "Use database to retrieve actual audit results",
    }


@tool
async def analyze_issues(url: str, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Use AI to analyze SEO issues and provide recommendations.
    
    Args:
        url: The URL that was audited
        issues: List of issues found during audit
    
    Returns:
        AI analysis with prioritized recommendations
    """
    llm = get_llm_client()
    
    if not await llm.health_check():
        return {"error": "LLM service unavailable"}
    
    analysis = await analyze_seo_issues(llm, url, issues)
    
    return {
        "success": True,
        "url": url,
        "analysis": analysis,
    }
