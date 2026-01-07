"""
Content Tools for LangGraph Agents

Tools for content generation and optimization.
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

from app.integrations.llm import get_llm_client, generate_content_brief, Message


@tool
async def generate_brief(
    keyword: str,
    competitors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate a content brief for a target keyword.
    
    Args:
        keyword: The target keyword
        competitors: Optional list of competitor content for analysis
    
    Returns:
        Content brief with outline, word count, and keywords
    """
    llm = get_llm_client()
    
    if not await llm.health_check():
        return {"error": "LLM service unavailable"}
    
    brief = await generate_content_brief(
        llm,
        keyword=keyword,
        competitors=competitors or [],
    )
    
    return {
        "success": True,
        "keyword": keyword,
        "brief": brief,
    }


@tool
async def generate_draft(
    keyword: str,
    outline: List[Dict[str, Any]],
    target_word_count: int = 1500,
    keywords_to_include: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a content draft based on a brief.
    
    Args:
        keyword: The target keyword
        outline: Content outline with headings and key points
        target_word_count: Target word count (default: 1500)
        keywords_to_include: Additional keywords to include
    
    Returns:
        Generated content draft
    """
    llm = get_llm_client()
    
    if not await llm.health_check():
        return {"error": "LLM service unavailable"}
    
    # Build outline text
    outline_text = ""
    for section in outline:
        outline_text += f"\n## {section.get('heading', 'Section')}\n"
        for point in section.get("key_points", []):
            outline_text += f"- {point}\n"
    
    keywords_text = ", ".join(keywords_to_include or [])
    
    prompt = f"""Write a comprehensive, SEO-optimized article based on this brief:

Target Keyword: {keyword}
Target Word Count: {target_word_count} words
Additional Keywords: {keywords_text}

Content Outline:
{outline_text}

Requirements:
1. Write in a professional but engaging tone
2. Include the target keyword naturally throughout
3. Use the provided outline as structure
4. Include an introduction and conclusion
5. Make it informative and valuable to readers
6. Format with markdown headings and lists

Write the full article:"""

    messages = [
        Message(
            role="system",
            content="You are an expert content writer specializing in SEO-optimized articles.",
        ),
        Message(role="user", content=prompt),
    ]
    
    response = await llm.chat(messages, max_tokens=4000)
    
    content = response.content
    word_count = len(content.split())
    
    return {
        "success": True,
        "keyword": keyword,
        "content": content,
        "word_count": word_count,
    }


@tool
async def analyze_content(content: str, target_keyword: str) -> Dict[str, Any]:
    """
    Analyze content for SEO optimization.
    
    Args:
        content: The content to analyze
        target_keyword: The target keyword
    
    Returns:
        SEO analysis with score and recommendations
    """
    word_count = len(content.split())
    keyword_lower = target_keyword.lower()
    content_lower = content.lower()
    
    # Count keyword occurrences
    keyword_count = content_lower.count(keyword_lower)
    keyword_density = (keyword_count / word_count * 100) if word_count > 0 else 0
    
    # Check for headings
    has_h1 = "# " in content
    heading_count = content.count("\n#")
    
    # Build analysis
    issues = []
    score = 100
    
    # Word count check
    if word_count < 300:
        issues.append({
            "type": "word_count",
            "severity": "high",
            "message": f"Content is too short ({word_count} words). Aim for at least 1000 words.",
        })
        score -= 20
    elif word_count < 1000:
        issues.append({
            "type": "word_count",
            "severity": "medium",
            "message": f"Content could be longer ({word_count} words). Consider expanding to 1500+ words.",
        })
        score -= 10
    
    # Keyword density check
    if keyword_density < 0.5:
        issues.append({
            "type": "keyword_density",
            "severity": "medium",
            "message": f"Keyword density is low ({keyword_density:.2f}%). Use the keyword more often.",
        })
        score -= 10
    elif keyword_density > 3:
        issues.append({
            "type": "keyword_stuffing",
            "severity": "high",
            "message": f"Keyword density is too high ({keyword_density:.2f}%). This may appear as keyword stuffing.",
        })
        score -= 15
    
    # Heading checks
    if not has_h1:
        issues.append({
            "type": "missing_h1",
            "severity": "high",
            "message": "Content is missing an H1 heading.",
        })
        score -= 15
    
    if heading_count < 3:
        issues.append({
            "type": "few_headings",
            "severity": "low",
            "message": "Add more subheadings to improve content structure.",
        })
        score -= 5
    
    return {
        "success": True,
        "score": max(0, score),
        "word_count": word_count,
        "keyword_count": keyword_count,
        "keyword_density": round(keyword_density, 2),
        "heading_count": heading_count,
        "issues": issues,
    }


@tool
async def optimize_content(
    content: str,
    target_keyword: str,
    instructions: str,
) -> Dict[str, Any]:
    """
    Optimize content based on SEO recommendations.
    
    Args:
        content: The content to optimize
        target_keyword: The target keyword
        instructions: Specific optimization instructions
    
    Returns:
        Optimized content
    """
    llm = get_llm_client()
    
    if not await llm.health_check():
        return {"error": "LLM service unavailable"}
    
    prompt = f"""Optimize the following content for the keyword "{target_keyword}".

Instructions: {instructions}

Content:
{content}

Provide the optimized content:"""

    messages = [
        Message(
            role="system",
            content="You are an SEO content optimization expert. Improve content while maintaining quality and readability.",
        ),
        Message(role="user", content=prompt),
    ]
    
    response = await llm.chat(messages, max_tokens=4000)
    
    return {
        "success": True,
        "optimized_content": response.content,
        "word_count": len(response.content.split()),
    }
