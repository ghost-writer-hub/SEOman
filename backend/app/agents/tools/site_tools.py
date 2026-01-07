"""
Site Tools for LangGraph Agents

Tools for site analysis and crawling.
"""

from typing import Dict, Any
import httpx
from langchain_core.tools import tool


@tool
async def get_site_info(url: str) -> Dict[str, Any]:
    """
    Get basic information about a website.
    
    Args:
        url: The URL of the website
    
    Returns:
        Site information including title, meta tags, and status
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            
            content = response.text
            
            # Extract title
            title = None
            if "<title>" in content and "</title>" in content:
                start = content.find("<title>") + 7
                end = content.find("</title>")
                title = content[start:end].strip()
            
            # Extract meta description
            meta_description = None
            if 'name="description"' in content:
                start = content.find('name="description"')
                content_attr = content.find('content="', start)
                if content_attr != -1:
                    end = content.find('"', content_attr + 9)
                    meta_description = content[content_attr + 9:end]
            
            # Count headings
            h1_count = content.lower().count("<h1")
            h2_count = content.lower().count("<h2")
            
            return {
                "success": True,
                "url": str(response.url),
                "status_code": response.status_code,
                "title": title,
                "meta_description": meta_description,
                "h1_count": h1_count,
                "h2_count": h2_count,
                "content_length": len(content),
                "redirected": str(response.url) != url,
            }
            
    except httpx.TimeoutException:
        return {"error": "Request timed out", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


@tool
async def crawl_page(url: str) -> Dict[str, Any]:
    """
    Crawl a single page and extract SEO-relevant data.
    
    Args:
        url: The URL to crawl
    
    Returns:
        Page data including content, links, and meta information
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            
            content = response.text
            content_lower = content.lower()
            
            # Extract links
            internal_links = []
            external_links = []
            
            # Simple link extraction (production would use proper HTML parsing)
            import re
            from urllib.parse import urljoin, urlparse
            
            base_domain = urlparse(url).netloc
            
            href_pattern = re.compile(r'href=["\']([^"\']+)["\']')
            for match in href_pattern.finditer(content):
                href = match.group(1)
                if href.startswith('#') or href.startswith('javascript:'):
                    continue
                
                full_url = urljoin(url, href)
                link_domain = urlparse(full_url).netloc
                
                if link_domain == base_domain:
                    internal_links.append(full_url)
                elif link_domain:
                    external_links.append(full_url)
            
            # Extract images without alt
            img_pattern = re.compile(r'<img[^>]+>')
            images = img_pattern.findall(content)
            images_without_alt = [img for img in images if 'alt=' not in img.lower() or 'alt=""' in img.lower()]
            
            # Word count (rough estimate)
            text_content = re.sub(r'<[^>]+>', ' ', content)
            word_count = len(text_content.split())
            
            return {
                "success": True,
                "url": str(response.url),
                "status_code": response.status_code,
                "word_count": word_count,
                "internal_links": len(internal_links),
                "external_links": len(external_links),
                "images_total": len(images),
                "images_without_alt": len(images_without_alt),
                "has_canonical": 'rel="canonical"' in content_lower,
                "has_robots_meta": 'name="robots"' in content_lower,
            }
            
    except httpx.TimeoutException:
        return {"error": "Request timed out", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


@tool
async def check_page_status(urls: list[str]) -> Dict[str, Any]:
    """
    Check the HTTP status of multiple URLs.
    
    Args:
        urls: List of URLs to check
    
    Returns:
        Status results for each URL
    """
    results = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in urls[:50]:  # Limit to 50 URLs
            try:
                response = await client.head(url, follow_redirects=True)
                results.append({
                    "url": url,
                    "status_code": response.status_code,
                    "final_url": str(response.url),
                    "is_redirect": str(response.url) != url,
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "error": str(e),
                })
    
    # Summary
    status_200 = sum(1 for r in results if r.get("status_code") == 200)
    status_301_302 = sum(1 for r in results if r.get("status_code") in [301, 302])
    status_404 = sum(1 for r in results if r.get("status_code") == 404)
    errors = sum(1 for r in results if "error" in r)
    
    return {
        "success": True,
        "urls_checked": len(results),
        "summary": {
            "status_200": status_200,
            "redirects": status_301_302,
            "status_404": status_404,
            "errors": errors,
        },
        "results": results,
    }
