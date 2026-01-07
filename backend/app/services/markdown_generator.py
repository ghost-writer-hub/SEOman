"""
Markdown Report Generator Service

Generates structured markdown reports for SEO audits, plans, and content briefs.
These reports are designed to be stored in S3-compatible storage (MinIO/Backblaze B2).
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import re


class MarkdownGenerator:
    """Generates markdown reports from SEO data."""
    
    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text[:50]
    
    @classmethod
    def generate_audit_report(
        cls,
        site_url: str,
        score: int,
        issues: List[Dict[str, Any]],
        summary: Optional[str] = None,
        recommendations: Optional[List[Dict[str, Any]]] = None,
        generated_at: Optional[datetime] = None,
    ) -> str:
        """
        Generate a comprehensive SEO audit report in markdown format.
        
        Args:
            site_url: The audited website URL
            score: Overall SEO score (0-100)
            issues: List of SEO issues found
            summary: Executive summary text
            recommendations: AI-generated recommendations
            generated_at: Report generation timestamp
        
        Returns:
            Markdown formatted audit report
        """
        generated_at = generated_at or datetime.utcnow()
        
        # Calculate severity counts
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.get("severity", "low").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Build the report
        lines = [
            f"# SEO Audit Report",
            f"",
            f"**Site:** {site_url}  ",
            f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
            f"**Overall Score:** {score}/100",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
        ]
        
        if summary:
            # Handle both string and dict summary
            if isinstance(summary, str):
                lines.append(summary)
            elif isinstance(summary, dict):
                # Extract meaningful summary from dict
                total_checks = summary.get("total_checks", 0)
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                lines.append(
                    f"Ran {total_checks} SEO checks. {passed} passed, {failed} failed."
                )
            else:
                lines.append(str(summary))
        else:
            # Generate default summary
            if score >= 80:
                status = "good"
                action = "Minor optimizations recommended."
            elif score >= 60:
                status = "fair"
                action = "Several improvements needed to boost rankings."
            elif score >= 40:
                status = "needs work"
                action = "Significant issues require attention."
            else:
                status = "poor"
                action = "Critical issues must be addressed immediately."
            
            lines.append(
                f"This site's SEO health is **{status}** with a score of {score}/100. "
                f"{action}"
            )
        
        lines.extend([
            f"",
            f"### Issues Overview",
            f"",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| Critical | {severity_counts['critical']} |",
            f"| High | {severity_counts['high']} |",
            f"| Medium | {severity_counts['medium']} |",
            f"| Low | {severity_counts['low']} |",
            f"| **Total** | **{len(issues)}** |",
            f"",
            f"---",
            f"",
        ])
        
        # Group issues by severity
        for severity in ["critical", "high", "medium", "low"]:
            severity_issues = [i for i in issues if i.get("severity", "").lower() == severity]
            if severity_issues:
                lines.extend([
                    f"## {severity.capitalize()} Priority Issues",
                    f"",
                ])
                
                for idx, issue in enumerate(severity_issues, 1):
                    title = issue.get("title", "Unknown Issue")
                    description = issue.get("description", "")
                    suggested_fix = issue.get("suggested_fix", issue.get("recommendation", ""))
                    affected_urls = issue.get("affected_urls", [])
                    category = issue.get("category", "General")
                    
                    lines.extend([
                        f"### {idx}. {title}",
                        f"",
                        f"**Category:** {category}  ",
                        f"**Severity:** {severity.capitalize()}",
                        f"",
                    ])
                    
                    if description:
                        lines.extend([description, ""])
                    
                    if suggested_fix:
                        lines.extend([
                            f"**Recommended Fix:**",
                            f"> {suggested_fix}",
                            f"",
                        ])
                    
                    if affected_urls:
                        lines.extend([
                            f"**Affected Pages:**",
                            f"",
                        ])
                        for url in affected_urls[:10]:  # Limit to 10
                            lines.append(f"- {url}")
                        if len(affected_urls) > 10:
                            lines.append(f"- ... and {len(affected_urls) - 10} more")
                        lines.append("")
                
                lines.append("")
        
        # AI Recommendations section
        if recommendations:
            lines.extend([
                f"---",
                f"",
                f"## AI-Powered Recommendations",
                f"",
            ])
            
            # Priority issues from AI
            priority_issues = recommendations.get("priority_issues", [])
            if priority_issues:
                lines.extend([
                    f"### Priority Actions",
                    f"",
                ])
                for idx, rec in enumerate(priority_issues, 1):
                    issue = rec.get("issue", "")
                    recommendation = rec.get("recommendation", "")
                    impact = rec.get("estimated_impact", "")
                    
                    lines.extend([
                        f"{idx}. **{issue}**",
                        f"   - Action: {recommendation}",
                    ])
                    if impact:
                        lines.append(f"   - Expected Impact: {impact}")
                    lines.append("")
            
            # Quick wins
            quick_wins = recommendations.get("quick_wins", [])
            if quick_wins:
                lines.extend([
                    f"### Quick Wins",
                    f"",
                    f"These can be implemented quickly for immediate improvement:",
                    f"",
                ])
                for win in quick_wins:
                    lines.append(f"- {win}")
                lines.append("")
        
        lines.extend([
            f"---",
            f"",
            f"*Report generated by SEOman*",
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def generate_seo_plan(
        cls,
        site_url: str,
        summary: Dict[str, Any],
        action_plan: List[Dict[str, Any]],
        content_calendar: List[Dict[str, Any]],
        generated_at: Optional[datetime] = None,
    ) -> str:
        """
        Generate an SEO improvement plan in markdown format.
        
        Args:
            site_url: The website URL
            summary: Plan summary with stats
            action_plan: List of action items
            content_calendar: Content publishing schedule
            generated_at: Report generation timestamp
        
        Returns:
            Markdown formatted SEO plan
        """
        generated_at = generated_at or datetime.utcnow()
        
        duration_weeks = summary.get("plan_duration_weeks", 12)
        current_score = summary.get("current_score", 0)
        
        lines = [
            f"# SEO Improvement Plan",
            f"",
            f"**Site:** {site_url}  ",
            f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
            f"**Plan Duration:** {duration_weeks} weeks",
            f"",
            f"---",
            f"",
            f"## Overview",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Current SEO Score | {current_score}/100 |",
            f"| Target Score | 85+/100 |",
            f"| Total Action Items | {summary.get('total_action_items', len(action_plan))} |",
            f"| Technical Tasks | {summary.get('technical_tasks', 0)} |",
            f"| Content Tasks | {summary.get('content_tasks', 0)} |",
            f"| Content Pieces Planned | {summary.get('content_pieces_planned', len(content_calendar))} |",
            f"",
            f"---",
            f"",
            f"## Phase Breakdown",
            f"",
        ]
        
        # Phases
        phases = summary.get("phases", [])
        if phases:
            for phase in phases:
                lines.extend([
                    f"### Phase {phase.get('number', '?')}: {phase.get('name', 'Unknown')}",
                    f"",
                    f"**Weeks:** {phase.get('weeks', 'TBD')}  ",
                    f"**Focus:** {phase.get('focus', '')}  ",
                    f"**Tasks:** {phase.get('tasks', 0)}",
                    f"",
                ])
        else:
            # Generate default phases from action plan
            phases_data = {}
            for item in action_plan:
                phase_name = item.get("phase_name", "General")
                if phase_name not in phases_data:
                    phases_data[phase_name] = []
                phases_data[phase_name].append(item)
            
            for phase_name, items in phases_data.items():
                lines.extend([
                    f"### {phase_name}",
                    f"",
                    f"**Tasks:** {len(items)}",
                    f"",
                ])
        
        lines.extend([
            f"---",
            f"",
            f"## Action Plan",
            f"",
        ])
        
        # Group by phase
        current_phase = None
        for item in action_plan:
            phase_name = item.get("phase_name", "General")
            if phase_name != current_phase:
                current_phase = phase_name
                lines.extend([
                    f"### {phase_name}",
                    f"",
                ])
            
            task = item.get("task", "Unknown Task")
            description = item.get("description", "")
            effort = item.get("effort", "medium")
            impact = item.get("expected_impact", "medium")
            week_start = item.get("week_start", "?")
            week_end = item.get("week_end", "?")
            
            lines.extend([
                f"#### [ ] {task}",
                f"",
                f"- **Timeline:** Week {week_start}-{week_end}",
                f"- **Effort:** {effort.capitalize()}",
                f"- **Impact:** {impact.capitalize()}",
            ])
            
            if description:
                lines.append(f"- **Details:** {description}")
            
            # Add keywords if content task
            keywords = item.get("target_keywords", [])
            if keywords:
                lines.append(f"- **Target Keywords:** {', '.join(keywords[:5])}")
            
            lines.append("")
        
        # Content Calendar
        if content_calendar:
            lines.extend([
                f"---",
                f"",
                f"## Content Calendar",
                f"",
                f"| Week | Publish Date | Title | Type | Target Keywords |",
                f"|------|--------------|-------|------|-----------------|",
            ])
            
            for item in content_calendar:
                week = item.get("week", "?")
                date = item.get("publish_date", "TBD")
                title = item.get("title", "Untitled")[:40]
                content_type = item.get("content_type", "Article")
                keywords = ", ".join(item.get("target_keywords", [])[:3])
                
                lines.append(f"| {week} | {date} | {title} | {content_type} | {keywords} |")
            
            lines.append("")
        
        # Expected Outcomes
        outcomes = summary.get("expected_outcomes", [])
        if outcomes:
            lines.extend([
                f"---",
                f"",
                f"## Expected Outcomes",
                f"",
            ])
            for outcome in outcomes:
                lines.append(f"- {outcome}")
            lines.append("")
        
        lines.extend([
            f"---",
            f"",
            f"*Plan generated by SEOman*",
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def generate_page_fixes(
        cls,
        site_url: str,
        issues: List[Dict[str, Any]],
        generated_at: Optional[datetime] = None,
    ) -> str:
        """
        Generate a page-by-page modification guide in markdown format.
        
        Args:
            site_url: The website URL
            issues: List of SEO issues with affected URLs
            generated_at: Report generation timestamp
        
        Returns:
            Markdown formatted page fixes guide
        """
        generated_at = generated_at or datetime.utcnow()
        
        # Group issues by affected URL
        pages: Dict[str, List[Dict]] = {}
        for issue in issues:
            affected_urls = issue.get("affected_urls", [])
            if not affected_urls:
                # Use site root as fallback
                affected_urls = [site_url]
            
            for url in affected_urls:
                if url not in pages:
                    pages[url] = []
                pages[url].append(issue)
        
        lines = [
            f"# Page Modification Guide",
            f"",
            f"**Site:** {site_url}  ",
            f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
            f"**Pages with Issues:** {len(pages)}",
            f"",
            f"---",
            f"",
            f"## Quick Reference",
            f"",
            f"| Page | Critical | High | Medium | Low | Total |",
            f"|------|----------|------|--------|-----|-------|",
        ]
        
        # Build quick reference table
        for url, page_issues in sorted(pages.items()):
            counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for issue in page_issues:
                severity = issue.get("severity", "low").lower()
                if severity in counts:
                    counts[severity] += 1
            total = sum(counts.values())
            
            # Truncate long URLs
            display_url = url if len(url) <= 50 else url[:47] + "..."
            lines.append(
                f"| {display_url} | {counts['critical']} | {counts['high']} | "
                f"{counts['medium']} | {counts['low']} | {total} |"
            )
        
        lines.extend([
            f"",
            f"---",
            f"",
            f"## Detailed Fixes by Page",
            f"",
        ])
        
        # Sort pages by severity (most critical first)
        def page_priority(item):
            url, page_issues = item
            score = 0
            for issue in page_issues:
                severity = issue.get("severity", "low").lower()
                if severity == "critical":
                    score += 100
                elif severity == "high":
                    score += 10
                elif severity == "medium":
                    score += 1
            return -score
        
        sorted_pages = sorted(pages.items(), key=page_priority)
        
        for url, page_issues in sorted_pages:
            lines.extend([
                f"### {url}",
                f"",
            ])
            
            # Sort issues by severity
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_issues = sorted(
                page_issues,
                key=lambda x: severity_order.get(x.get("severity", "low").lower(), 4)
            )
            
            for issue in sorted_issues:
                title = issue.get("title", "Unknown Issue")
                severity = issue.get("severity", "low").capitalize()
                suggested_fix = issue.get("suggested_fix", issue.get("recommendation", ""))
                
                lines.extend([
                    f"#### [{severity}] {title}",
                    f"",
                ])
                
                if suggested_fix:
                    lines.extend([
                        f"**Fix:** {suggested_fix}",
                        f"",
                    ])
            
            lines.append("")
        
        lines.extend([
            f"---",
            f"",
            f"*Guide generated by SEOman*",
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def generate_article_brief(
        cls,
        keyword: str,
        brief_data: Dict[str, Any],
        brief_number: int = 1,
        generated_at: Optional[datetime] = None,
    ) -> str:
        """
        Generate an article content brief in markdown format.
        
        Args:
            keyword: Target keyword for the article
            brief_data: Brief data including outline, suggestions, etc.
            brief_number: Brief sequence number
            generated_at: Report generation timestamp
        
        Returns:
            Markdown formatted article brief
        """
        generated_at = generated_at or datetime.utcnow()
        
        title_suggestions = brief_data.get("title_suggestions", [f"Article about {keyword}"])
        meta_description = brief_data.get("meta_description", "")
        target_word_count = brief_data.get("target_word_count", 1500)
        content_outline = brief_data.get("content_outline", [])
        keywords_to_include = brief_data.get("keywords_to_include", [keyword])
        differentiation_angle = brief_data.get("differentiation_angle", "")
        search_intent = brief_data.get("intent", "informational")
        
        lines = [
            f"# Article Brief #{brief_number:02d}",
            f"",
            f"**Target Keyword:** {keyword}  ",
            f"**Search Intent:** {search_intent.capitalize()}  ",
            f"**Target Word Count:** {target_word_count} words  ",
            f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"",
            f"---",
            f"",
            f"## Title Suggestions",
            f"",
        ]
        
        for idx, title in enumerate(title_suggestions[:5], 1):
            lines.append(f"{idx}. {title}")
        
        lines.extend([
            f"",
            f"## Meta Description",
            f"",
            f"> {meta_description or 'Write a compelling 150-160 character description including the target keyword.'}",
            f"",
        ])
        
        if differentiation_angle:
            lines.extend([
                f"## Unique Angle",
                f"",
                f"{differentiation_angle}",
                f"",
            ])
        
        lines.extend([
            f"---",
            f"",
            f"## Content Outline",
            f"",
        ])
        
        if content_outline:
            for section in content_outline:
                heading = section.get("heading", "Section")
                key_points = section.get("key_points", [])
                
                lines.extend([
                    f"### {heading}",
                    f"",
                ])
                
                for point in key_points:
                    lines.append(f"- {point}")
                
                lines.append("")
        else:
            lines.extend([
                f"### Introduction",
                f"- Hook the reader with a compelling opening",
                f"- Introduce the topic and why it matters",
                f"- Preview what the article will cover",
                f"",
                f"### Main Content",
                f"- Cover the topic comprehensively",
                f"- Use subheadings for organization",
                f"- Include examples and data",
                f"",
                f"### Conclusion",
                f"- Summarize key takeaways",
                f"- Include a call to action",
                f"",
            ])
        
        lines.extend([
            f"---",
            f"",
            f"## Keywords to Include",
            f"",
        ])
        
        for kw in keywords_to_include[:15]:
            lines.append(f"- {kw}")
        
        lines.extend([
            f"",
            f"---",
            f"",
            f"## Writing Guidelines",
            f"",
            f"- Write for humans first, search engines second",
            f"- Use the target keyword naturally in the first 100 words",
            f"- Include the keyword in at least one H2 heading",
            f"- Use related keywords throughout the content",
            f"- Break up text with subheadings every 300-400 words",
            f"- Include internal links to related content",
            f"- Add external links to authoritative sources",
            f"",
            f"---",
            f"",
            f"*Brief generated by SEOman*",
        ])
        
        return "\n".join(lines)


# Convenience functions

def generate_full_report_package(
    site_url: str,
    audit_data: Dict[str, Any],
    plan_data: Dict[str, Any],
    briefs_data: List[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Generate a complete package of markdown reports.
    
    Args:
        site_url: The website URL
        audit_data: Audit results including score, issues, recommendations
        plan_data: Plan data including summary, action_plan, content_calendar
        briefs_data: List of content briefs (optional)
    
    Returns:
        Dictionary with report type as key and markdown content as value
    """
    generator = MarkdownGenerator
    reports = {}
    
    # Audit Report
    reports["audit_report"] = generator.generate_audit_report(
        site_url=site_url,
        score=audit_data.get("score", 0),
        issues=audit_data.get("issues", []),
        summary=audit_data.get("summary"),
        recommendations=audit_data.get("recommendations"),
    )
    
    # SEO Plan
    reports["seo_plan"] = generator.generate_seo_plan(
        site_url=site_url,
        summary=plan_data.get("summary", {}),
        action_plan=plan_data.get("action_plan", []),
        content_calendar=plan_data.get("content_calendar", []),
    )
    
    # Page Fixes Guide
    reports["page_fixes"] = generator.generate_page_fixes(
        site_url=site_url,
        issues=audit_data.get("issues", []),
    )
    
    # Article Briefs
    if briefs_data:
        reports["briefs"] = []
        for idx, brief in enumerate(briefs_data, 1):
            keyword = brief.get("keyword", f"topic-{idx}")
            content = generator.generate_article_brief(
                keyword=keyword,
                brief_data=brief,
                brief_number=idx,
            )
            reports["briefs"].append({
                "keyword": keyword,
                "slug": generator.slugify(keyword),
                "content": content,
            })
    
    return reports
