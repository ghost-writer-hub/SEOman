"""
SEOman v2.0 Report Generator

Generates comprehensive SEO reports using Jinja2 templates.
Produces:
- Executive Summary (for stakeholders)
- Technical Audit Report (for developers)
- Action Plan (for implementation)
- Content Briefs (for content team)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


def get_jinja_env() -> Environment:
    """Get configured Jinja2 environment."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    # Custom filters
    env.filters["severity_emoji"] = lambda s: {
        "critical": "🔴",
        "high": "🟠", 
        "medium": "🟡",
        "low": "🟢",
    }.get(s.lower(), "⚪")
    
    env.filters["score_grade"] = lambda s: (
        "A+" if s >= 95 else
        "A" if s >= 90 else
        "B+" if s >= 85 else
        "B" if s >= 80 else
        "C+" if s >= 75 else
        "C" if s >= 70 else
        "D" if s >= 60 else
        "F"
    )
    
    env.filters["truncate_url"] = lambda url, length=50: (
        url if len(url) <= length else url[:length-3] + "..."
    )
    
    return env


class ReportGenerator:
    """SEOman v2.0 Report Generator using Jinja2 templates."""
    
    def __init__(self):
        self.env = get_jinja_env()
    
    def generate_executive_summary(
        self,
        site_url: str,
        audit_data: dict[str, Any],
        plan_data: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate executive summary for non-technical stakeholders.
        
        Focus: High-level metrics, business impact, ROI potential.
        """
        template = self.env.get_template("executive_summary.md.j2")
        
        # Calculate key metrics
        score = audit_data.get("score", 0)
        issues = audit_data.get("issues", [])
        audit_results = audit_data.get("audit_results", [])
        summary = audit_data.get("summary", {})
        
        # Severity breakdown
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            sev = issue.get("severity", "low").lower()
            if sev in severity_counts:
                severity_counts[sev] += 1
        
        # Category breakdown
        category_scores = self._calculate_category_scores(audit_results)
        
        # Estimated impact
        estimated_traffic_impact = self._estimate_traffic_impact(score, severity_counts)
        
        return template.render(
            site_url=site_url,
            score=score,
            grade=self._score_to_grade(score),
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            total_checks=len(audit_results),
            passed_checks=sum(1 for r in audit_results if r.get("passed", False)),
            failed_checks=sum(1 for r in audit_results if not r.get("passed", True)),
            severity_counts=severity_counts,
            category_scores=category_scores,
            top_issues=issues[:5],
            estimated_traffic_impact=estimated_traffic_impact,
            plan_summary=plan_data.get("summary", {}) if plan_data else {},
        )
    
    def generate_technical_audit(
        self,
        site_url: str,
        audit_data: dict[str, Any],
        pages_crawled: int = 0,
    ) -> str:
        """
        Generate detailed technical audit for developers.
        
        Focus: All 100 checks, technical details, code-level fixes.
        """
        template = self.env.get_template("technical_audit.md.j2")
        
        score = audit_data.get("score", 0)
        issues = audit_data.get("issues", [])
        audit_results = audit_data.get("audit_results", [])
        summary = audit_data.get("summary", {})
        
        # Group checks by category
        checks_by_category = self._group_by_category(audit_results)
        
        # Group issues by category
        issues_by_category = {}
        for issue in issues:
            cat = issue.get("category", "General")
            if cat not in issues_by_category:
                issues_by_category[cat] = []
            issues_by_category[cat].append(issue)
        
        return template.render(
            site_url=site_url,
            score=score,
            grade=self._score_to_grade(score),
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            pages_crawled=pages_crawled,
            total_checks=len(audit_results),
            passed_checks=sum(1 for r in audit_results if r.get("passed", False)),
            failed_checks=sum(1 for r in audit_results if not r.get("passed", True)),
            checks_by_category=checks_by_category,
            issues_by_category=issues_by_category,
            audit_summary=summary,
        )
    
    def generate_action_plan(
        self,
        site_url: str,
        audit_data: dict[str, Any],
        plan_data: dict[str, Any],
    ) -> str:
        """
        Generate prioritized action plan for implementation.
        
        Focus: Prioritized tasks, timelines, effort estimates.
        """
        template = self.env.get_template("action_plan.md.j2")
        
        issues = audit_data.get("issues", [])
        action_plan = plan_data.get("action_plan", [])
        content_calendar = plan_data.get("content_calendar", [])
        plan_summary = plan_data.get("summary", {})
        
        # Prioritize issues
        prioritized_issues = self._prioritize_issues(issues)
        
        # Group actions by phase
        actions_by_phase = {}
        for action in action_plan:
            phase = action.get("phase_name", "General")
            if phase not in actions_by_phase:
                actions_by_phase[phase] = []
            actions_by_phase[phase].append(action)
        
        return template.render(
            site_url=site_url,
            score=audit_data.get("score", 0),
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            plan_summary=plan_summary,
            prioritized_issues=prioritized_issues,
            actions_by_phase=actions_by_phase,
            content_calendar=content_calendar,
            quick_wins=self._get_quick_wins(issues),
        )
    
    def generate_content_brief(
        self,
        keyword: str,
        brief_data: dict[str, Any],
        brief_number: int = 1,
    ) -> str:
        """Generate individual content brief."""
        template = self.env.get_template("content_brief.md.j2")
        
        return template.render(
            keyword=keyword,
            brief_number=brief_number,
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            **brief_data,
        )
    
    def generate_full_report_package(
        self,
        site_url: str,
        audit_data: dict[str, Any],
        plan_data: dict[str, Any],
        briefs_data: list[dict[str, Any]] | None = None,
        pages_crawled: int = 0,
    ) -> dict[str, Any]:
        """
        Generate complete report package.
        
        Returns dict with all reports and metadata.
        """
        reports: dict[str, Any] = {}
        
        # Executive Summary
        reports["executive_summary"] = self.generate_executive_summary(
            site_url=site_url,
            audit_data=audit_data,
            plan_data=plan_data,
        )
        
        # Technical Audit
        reports["technical_audit"] = self.generate_technical_audit(
            site_url=site_url,
            audit_data=audit_data,
            pages_crawled=pages_crawled,
        )
        
        # Action Plan
        reports["action_plan"] = self.generate_action_plan(
            site_url=site_url,
            audit_data=audit_data,
            plan_data=plan_data,
        )
        
        # Content Briefs
        if briefs_data:
            reports["briefs"] = []
            for idx, brief in enumerate(briefs_data, 1):
                keyword = brief.get("keyword", f"topic-{idx}")
                content = self.generate_content_brief(
                    keyword=keyword,
                    brief_data=brief,
                    brief_number=idx,
                )
                reports["briefs"].append({
                    "keyword": keyword,
                    "slug": self._slugify(keyword),
                    "content": content,
                })
        
        return reports
    
    # Helper methods
    
    def _score_to_grade(self, score: int) -> str:
        if score >= 95: return "A+"
        if score >= 90: return "A"
        if score >= 85: return "B+"
        if score >= 80: return "B"
        if score >= 75: return "C+"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"
    
    def _calculate_category_scores(self, audit_results: list) -> dict[str, dict]:
        """Calculate scores per category."""
        categories: dict[str, dict] = {}
        
        for result in audit_results:
            cat = result.get("category", "General")
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "failed": 0}
            
            categories[cat]["total"] += 1
            if result.get("passed", False):
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        # Calculate percentage
        for cat, data in categories.items():
            if data["total"] > 0:
                data["score"] = int((data["passed"] / data["total"]) * 100)
            else:
                data["score"] = 0
        
        return categories
    
    def _group_by_category(self, audit_results: list) -> dict[str, list]:
        """Group audit results by category."""
        grouped: dict[str, list] = {}
        
        for result in audit_results:
            cat = result.get("category", "General")
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(result)
        
        return grouped
    
    def _prioritize_issues(self, issues: list) -> list:
        """Sort issues by priority (severity + impact)."""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        return sorted(
            issues,
            key=lambda x: (
                severity_order.get(x.get("severity", "low").lower(), 4),
                -x.get("affected_count", 0),
            )
        )
    
    def _get_quick_wins(self, issues: list) -> list:
        """Get quick wins (low effort, high impact issues)."""
        quick_wins = []
        
        for issue in issues:
            severity = issue.get("severity", "low").lower()
            # Quick wins: high/critical severity but typically easy fixes
            if severity in ["critical", "high"]:
                title = issue.get("title", "").lower()
                # These are typically quick fixes
                quick_fix_keywords = [
                    "missing", "empty", "duplicate", "too short", "too long",
                    "alt text", "meta description", "title tag", "canonical"
                ]
                if any(kw in title for kw in quick_fix_keywords):
                    quick_wins.append(issue)
        
        return quick_wins[:10]
    
    def _estimate_traffic_impact(
        self,
        score: int,
        severity_counts: dict,
    ) -> dict[str, Any]:
        """Estimate potential traffic impact from fixes."""
        # Rough estimates based on severity
        critical_impact = severity_counts.get("critical", 0) * 5
        high_impact = severity_counts.get("high", 0) * 2
        medium_impact = severity_counts.get("medium", 0) * 0.5
        
        total_potential = critical_impact + high_impact + medium_impact
        
        return {
            "current_score": score,
            "potential_score": min(95, score + int(total_potential)),
            "potential_traffic_increase": f"{min(50, int(total_potential * 2))}%",
            "confidence": "medium" if severity_counts.get("critical", 0) > 0 else "low",
        }
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text[:50]


# Fallback to string templates if Jinja templates don't exist
def generate_fallback_report(
    report_type: str,
    site_url: str,
    audit_data: dict[str, Any],
    plan_data: dict[str, Any] | None = None,
    **kwargs,
) -> str:
    """Generate report using string templates as fallback."""
    
    if report_type == "executive_summary":
        return _generate_executive_summary_fallback(site_url, audit_data, plan_data)
    elif report_type == "technical_audit":
        return _generate_technical_audit_fallback(site_url, audit_data, kwargs.get("pages_crawled", 0))
    elif report_type == "action_plan":
        return _generate_action_plan_fallback(site_url, audit_data, plan_data or {})
    else:
        return f"# {report_type}\n\nReport generation not implemented."


def _generate_executive_summary_fallback(
    site_url: str,
    audit_data: dict[str, Any],
    plan_data: dict[str, Any] | None,
) -> str:
    """Fallback executive summary generator."""
    score = audit_data.get("score", 0)
    issues = audit_data.get("issues", [])
    audit_results = audit_data.get("audit_results", [])
    
    # Count severities
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for issue in issues:
        sev = issue.get("severity", "low").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
    
    grade = (
        "A+" if score >= 95 else
        "A" if score >= 90 else
        "B" if score >= 80 else
        "C" if score >= 70 else
        "D" if score >= 60 else "F"
    )
    
    # Build report
    lines = [
        "# SEO Audit Executive Summary",
        "",
        f"**Site:** {site_url}",
        f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## Overall Score",
        "",
        f"# {score}/100 (Grade: {grade})",
        "",
        "---",
        "",
        "## Key Findings",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Checks | {len(audit_results)} |",
        f"| Passed | {sum(1 for r in audit_results if r.get('passed', False))} |",
        f"| Failed | {sum(1 for r in audit_results if not r.get('passed', True))} |",
        f"| Critical Issues | {severity_counts['critical']} |",
        f"| High Priority | {severity_counts['high']} |",
        "",
        "---",
        "",
        "## Top Issues to Address",
        "",
    ]
    
    for idx, issue in enumerate(issues[:5], 1):
        severity = issue.get("severity", "low").upper()
        title = issue.get("title", "Unknown")
        lines.append(f"{idx}. **[{severity}]** {title}")
    
    lines.extend([
        "",
        "---",
        "",
        "## Recommended Next Steps",
        "",
        "1. Address all critical issues immediately",
        "2. Fix high-priority technical issues within 1-2 weeks",
        "3. Implement content improvements based on the action plan",
        "4. Schedule monthly audits to track progress",
        "",
        "---",
        "",
        "*Report generated by SEOman v2.0*",
    ])
    
    return "\n".join(lines)


def _generate_technical_audit_fallback(
    site_url: str,
    audit_data: dict[str, Any],
    pages_crawled: int,
) -> str:
    """Fallback technical audit generator."""
    score = audit_data.get("score", 0)
    issues = audit_data.get("issues", [])
    audit_results = audit_data.get("audit_results", [])
    
    lines = [
        "# Technical SEO Audit Report",
        "",
        f"**Site:** {site_url}",
        f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}",
        f"**Pages Crawled:** {pages_crawled}",
        f"**Score:** {score}/100",
        "",
        "---",
        "",
        "## Audit Summary",
        "",
        f"| Category | Checks | Passed | Failed |",
        f"|----------|--------|--------|--------|",
    ]
    
    # Group by category
    categories: dict[str, dict] = {}
    for result in audit_results:
        cat = result.get("category", "General")
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "failed": 0}
        categories[cat]["total"] += 1
        if result.get("passed", False):
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
    
    for cat, data in categories.items():
        lines.append(f"| {cat} | {data['total']} | {data['passed']} | {data['failed']} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## All Checks",
        "",
    ])
    
    current_cat = None
    for result in audit_results:
        cat = result.get("category", "General")
        if cat != current_cat:
            current_cat = cat
            lines.extend(["", f"### {cat}", ""])
        
        status = "✅" if result.get("passed", False) else "❌"
        name = result.get("check_name", "Unknown")
        severity = result.get("severity", "low")
        
        lines.append(f"- {status} **{name}** [{severity}]")
        
        if not result.get("passed", False) and result.get("recommendation"):
            lines.append(f"  - Fix: {result['recommendation']}")
    
    lines.extend([
        "",
        "---",
        "",
        "## Issues Detail",
        "",
    ])
    
    for issue in issues:
        severity = issue.get("severity", "low").upper()
        title = issue.get("title", "Unknown")
        desc = issue.get("description", "")
        fix = issue.get("suggested_fix", "")
        urls = issue.get("affected_urls", [])
        
        lines.extend([
            f"### [{severity}] {title}",
            "",
        ])
        
        if desc:
            lines.append(desc)
            lines.append("")
        
        if fix:
            lines.append(f"**Fix:** {fix}")
            lines.append("")
        
        if urls:
            lines.append("**Affected URLs:**")
            for url in urls[:5]:
                lines.append(f"- {url}")
            if len(urls) > 5:
                lines.append(f"- ... and {len(urls) - 5} more")
            lines.append("")
    
    lines.extend([
        "---",
        "",
        "*Report generated by SEOman v2.0*",
    ])
    
    return "\n".join(lines)


def _generate_action_plan_fallback(
    site_url: str,
    audit_data: dict[str, Any],
    plan_data: dict[str, Any],
) -> str:
    """Fallback action plan generator."""
    score = audit_data.get("score", 0)
    issues = audit_data.get("issues", [])
    action_plan = plan_data.get("action_plan", [])
    content_calendar = plan_data.get("content_calendar", [])
    summary = plan_data.get("summary", {})
    
    lines = [
        "# SEO Action Plan",
        "",
        f"**Site:** {site_url}",
        f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}",
        f"**Current Score:** {score}/100",
        f"**Target Score:** 85+/100",
        "",
        "---",
        "",
        "## Plan Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Duration | {summary.get('plan_duration_weeks', 12)} weeks |",
        f"| Total Tasks | {summary.get('total_action_items', len(action_plan))} |",
        f"| Technical Tasks | {summary.get('technical_tasks', 0)} |",
        f"| Content Tasks | {summary.get('content_tasks', 0)} |",
        "",
        "---",
        "",
        "## Phase Breakdown",
        "",
    ]
    
    # Group by phase
    phases: dict[str, list] = {}
    for action in action_plan:
        phase = action.get("phase_name", "General")
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(action)
    
    for phase_name, actions in phases.items():
        lines.extend([
            f"### {phase_name}",
            "",
        ])
        
        for action in actions:
            task = action.get("task", "Unknown")
            effort = action.get("effort", "medium")
            impact = action.get("expected_impact", "medium")
            week_start = action.get("week_start", "?")
            week_end = action.get("week_end", "?")
            
            lines.extend([
                f"- [ ] **{task}**",
                f"  - Timeline: Week {week_start}-{week_end}",
                f"  - Effort: {effort} | Impact: {impact}",
                "",
            ])
    
    if content_calendar:
        lines.extend([
            "---",
            "",
            "## Content Calendar",
            "",
            "| Week | Title | Type | Keywords |",
            "|------|-------|------|----------|",
        ])
        
        for item in content_calendar:
            week = item.get("week", "?")
            title = item.get("title", "Untitled")[:30]
            ctype = item.get("content_type", "Article")
            keywords = ", ".join(item.get("target_keywords", [])[:2])
            lines.append(f"| {week} | {title} | {ctype} | {keywords} |")
    
    lines.extend([
        "",
        "---",
        "",
        "*Plan generated by SEOman v2.0*",
    ])
    
    return "\n".join(lines)
