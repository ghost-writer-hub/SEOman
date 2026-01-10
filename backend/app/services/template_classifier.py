"""
Template Classification Service

Uses OpenAI to analyze crawled pages and classify them into template types.
Templates help understand site structure and identify optimization opportunities.
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any
from urllib.parse import urlparse

from app.integrations.llm import LLMClient, Message, get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class PageTemplate:
    """Represents a detected page template."""

    template_id: str
    name: str
    description: str
    url_patterns: list[str] = field(default_factory=list)
    common_elements: dict[str, Any] = field(default_factory=dict)
    page_count: int = 0
    example_urls: list[str] = field(default_factory=list)
    seo_recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TemplateClassificationResult:
    """Result of template classification for a site."""

    site_url: str
    total_pages: int
    templates: list[PageTemplate] = field(default_factory=list)
    unclassified_pages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "site_url": self.site_url,
            "total_pages": self.total_pages,
            "templates": [t.to_dict() for t in self.templates],
            "unclassified_pages": self.unclassified_pages,
        }


class TemplateClassifier:
    """Classifies pages into templates using LLM analysis."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or get_llm_client()

    async def classify_pages(
        self,
        site_url: str,
        pages: list[dict],
        use_llm: bool = True,
    ) -> TemplateClassificationResult:
        """
        Classify crawled pages into templates.

        Args:
            site_url: The base URL of the site
            pages: List of crawled page data from crawler
            use_llm: Whether to use LLM for intelligent naming (vs heuristics only)

        Returns:
            TemplateClassificationResult with detected templates
        """
        logger.info(f"Classifying {len(pages)} pages into templates for {site_url}")

        # Step 1: Group pages by structural similarity using heuristics
        page_groups = self._group_pages_by_structure(pages)
        logger.info(f"Initial grouping: {len(page_groups)} groups")

        # Step 2: Use LLM to name and describe templates
        if use_llm and page_groups:
            templates = await self._name_templates_with_llm(site_url, page_groups, pages)
        else:
            templates = self._create_basic_templates(page_groups, pages)

        # Identify unclassified pages
        classified_urls = set()
        for template in templates:
            classified_urls.update(template.example_urls)

        all_urls = {p.get("url") or p.get("final_url") for p in pages}
        unclassified = list(all_urls - classified_urls)

        result = TemplateClassificationResult(
            site_url=site_url,
            total_pages=len(pages),
            templates=templates,
            unclassified_pages=unclassified[:20],  # Limit to 20 examples
        )

        logger.info(f"Classification complete: {len(templates)} templates, {len(unclassified)} unclassified")
        return result

    def _group_pages_by_structure(self, pages: list[dict]) -> dict[str, list[dict]]:
        """Group pages by structural similarity (URL patterns, content structure)."""
        groups: dict[str, list[dict]] = defaultdict(list)

        for page in pages:
            url = page.get("url") or page.get("final_url", "")
            if not url:
                continue

            # Generate a structural signature
            signature = self._get_page_signature(page)
            groups[signature].append(page)

        # Merge small groups into "other"
        merged_groups: dict[str, list[dict]] = {}
        other_pages: list[dict] = []

        for sig, group_pages in groups.items():
            if len(group_pages) >= 2:  # At least 2 pages to be a template
                merged_groups[sig] = group_pages
            else:
                other_pages.extend(group_pages)

        if other_pages:
            merged_groups["_other_"] = other_pages

        return merged_groups

    def _get_page_signature(self, page: dict) -> str:
        """Generate a structural signature for a page."""
        url = page.get("url") or page.get("final_url", "")
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        # URL pattern analysis
        path_parts = [p for p in path.split("/") if p]
        depth = len(path_parts)

        # Detect URL patterns
        patterns = []

        # Check if homepage
        if not path_parts or path == "":
            return "homepage"

        # Language prefix detection (e.g., /en/, /es/, /de/)
        lang_prefix = ""
        if path_parts and len(path_parts[0]) == 2 and path_parts[0].isalpha():
            lang_prefix = path_parts[0]
            path_parts = path_parts[1:]
            depth -= 1

        # Check for common page types by URL
        if not path_parts:
            return f"homepage_{lang_prefix}" if lang_prefix else "homepage"

        last_part = path_parts[-1] if path_parts else ""
        first_part = path_parts[0] if path_parts else ""

        # Blog/article patterns
        if any(p in ["blog", "news", "article", "articles", "posts", "noticias"] for p in path_parts):
            if depth >= 2:
                return f"blog_post_{lang_prefix}" if lang_prefix else "blog_post"
            return f"blog_index_{lang_prefix}" if lang_prefix else "blog_index"

        # Product/service patterns
        if any(p in ["product", "products", "item", "shop", "store", "producto", "productos"] for p in path_parts):
            if depth >= 2:
                return f"product_page_{lang_prefix}" if lang_prefix else "product_page"
            return f"product_listing_{lang_prefix}" if lang_prefix else "product_listing"

        # Category patterns
        if any(p in ["category", "categories", "cat", "collection", "categoria"] for p in path_parts):
            return f"category_page_{lang_prefix}" if lang_prefix else "category_page"

        # Contact/about patterns
        if any(p in ["contact", "contacto", "about", "sobre", "about-us", "sobre-nosotros"] for p in path_parts):
            return f"info_page_{lang_prefix}" if lang_prefix else "info_page"

        # FAQ patterns
        if any(p in ["faq", "faqs", "help", "ayuda", "preguntas"] for p in path_parts):
            return f"faq_page_{lang_prefix}" if lang_prefix else "faq_page"

        # Legal patterns
        if any(p in ["privacy", "terms", "legal", "policy", "privacidad", "cookies"] for p in path_parts):
            return f"legal_page_{lang_prefix}" if lang_prefix else "legal_page"

        # Analyze content structure
        h1_count = len(page.get("h1", []))
        h2_count = len(page.get("h2", []))
        word_count = page.get("word_count", 0)
        images_count = len(page.get("images", []))

        # Content-based heuristics
        content_type = "standard"
        if word_count > 1000 and h2_count >= 3:
            content_type = "long_form"
        elif images_count > 5 and word_count < 300:
            content_type = "gallery"
        elif word_count < 100:
            content_type = "minimal"

        # Build signature from URL structure
        url_pattern = self._extract_url_pattern(path_parts, last_part)

        signature_parts = [url_pattern]
        if lang_prefix:
            signature_parts.append(lang_prefix)
        if content_type != "standard":
            signature_parts.append(content_type)

        return "_".join(signature_parts)

    def _extract_url_pattern(self, path_parts: list[str], last_part: str) -> str:
        """Extract a generalized URL pattern."""
        if not path_parts:
            return "root"

        # Check for file extension
        if "." in last_part:
            ext = last_part.split(".")[-1].lower()
            if ext == "html":
                name = last_part.rsplit(".", 1)[0]
                # Check if it looks like a slug (contains hyphens or is descriptive)
                if "-" in name or len(name) > 10:
                    return f"content_{path_parts[0]}" if len(path_parts) > 1 else "content_page"
            return f"file_{ext}"

        # Path depth analysis
        depth = len(path_parts)
        if depth == 1:
            return f"section_{path_parts[0][:20]}"
        elif depth == 2:
            return f"subsection_{path_parts[0][:15]}"
        else:
            return f"deep_content_d{depth}"

    async def _name_templates_with_llm(
        self,
        site_url: str,
        page_groups: dict[str, list[dict]],
        all_pages: list[dict],
    ) -> list[PageTemplate]:
        """Use LLM to intelligently name and describe templates."""
        templates = []

        # Prepare summary for LLM
        groups_summary = []
        for sig, group_pages in page_groups.items():
            if sig == "_other_":
                continue

            example_urls = [p.get("url") or p.get("final_url") for p in group_pages[:5]]
            example_titles = [p.get("title", "")[:60] for p in group_pages[:5]]

            groups_summary.append({
                "signature": sig,
                "count": len(group_pages),
                "example_urls": example_urls,
                "example_titles": example_titles,
            })

        if not groups_summary:
            return templates

        # Ask LLM to name templates
        prompt = f"""Analyze the following page groups from {site_url} and provide meaningful names and descriptions for each template type.

Page Groups:
{json.dumps(groups_summary, indent=2)}

For each group, provide:
1. A clear, descriptive template name (e.g., "Hotel Property Page", "Destination Guide", "Promotional Landing Page")
2. A brief description of what this template is used for
3. SEO recommendations specific to this template type

Focus on understanding the business context and purpose of each page type."""

        schema = {
            "type": "object",
            "properties": {
                "templates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "signature": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "seo_recommendations": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                        },
                    },
                },
            },
        }

        try:
            result = await self.llm.generate_json(
                prompt,
                schema,
                system_prompt="You are an expert SEO analyst specializing in website architecture and template analysis.",
            )

            llm_templates = {t["signature"]: t for t in result.get("templates", [])}

            for sig, group_pages in page_groups.items():
                if sig == "_other_":
                    continue

                llm_data = llm_templates.get(sig, {})
                example_urls = [p.get("url") or p.get("final_url") for p in group_pages[:10]]

                template = PageTemplate(
                    template_id=sig,
                    name=llm_data.get("name", self._humanize_signature(sig)),
                    description=llm_data.get("description", f"Pages matching pattern: {sig}"),
                    url_patterns=self._extract_url_patterns_from_pages(group_pages),
                    page_count=len(group_pages),
                    example_urls=example_urls,
                    seo_recommendations=llm_data.get("seo_recommendations", []),
                )
                templates.append(template)

        except Exception as e:
            logger.warning(f"LLM template naming failed, using heuristics: {e}")
            templates = self._create_basic_templates(page_groups, all_pages)

        # Handle "other" group
        if "_other_" in page_groups:
            other_pages = page_groups["_other_"]
            templates.append(PageTemplate(
                template_id="_other_",
                name="Other Pages",
                description="Pages that don't match common template patterns",
                page_count=len(other_pages),
                example_urls=[p.get("url") or p.get("final_url") for p in other_pages[:10]],
            ))

        return templates

    def _create_basic_templates(
        self,
        page_groups: dict[str, list[dict]],
        all_pages: list[dict],
    ) -> list[PageTemplate]:
        """Create templates using heuristics only (no LLM)."""
        templates = []

        for sig, group_pages in page_groups.items():
            example_urls = [p.get("url") or p.get("final_url") for p in group_pages[:10]]

            # Analyze pages to generate better name and description
            name, description, recommendations = self._analyze_template_group(sig, group_pages)

            template = PageTemplate(
                template_id=sig,
                name=name,
                description=description,
                url_patterns=self._extract_url_patterns_from_pages(group_pages),
                page_count=len(group_pages),
                example_urls=example_urls,
                seo_recommendations=recommendations,
            )
            templates.append(template)

        return templates

    def _analyze_template_group(
        self,
        sig: str,
        pages: list[dict],
    ) -> tuple[str, str, list[str]]:
        """Analyze a template group to generate name, description, and recommendations."""

        # Get common characteristics
        avg_word_count = sum(p.get("word_count", 0) for p in pages) // max(len(pages), 1)
        titles = [p.get("title", "") for p in pages if p.get("title")]
        h1s = [h1 for p in pages for h1 in (p.get("h1", []) or [])]
        urls = [p.get("url") or p.get("final_url", "") for p in pages]

        # Detect language from signature
        lang_suffix = ""
        lang_code = None
        parts = sig.split("_")
        if parts and len(parts[-1]) == 2 and parts[-1].isalpha():
            lang_code = parts[-1].upper()
            lang_suffix = f" ({lang_code})"

        # Generate name and description based on analysis
        name, description = self._humanize_signature_enhanced(sig, pages, titles, avg_word_count)
        if lang_code and not name.endswith(f"({lang_code})"):
            name = f"{name}{lang_suffix}"

        # Generate SEO recommendations based on template characteristics
        recommendations = self._generate_template_recommendations(pages, avg_word_count)

        return name, description, recommendations

    def _humanize_signature_enhanced(
        self,
        sig: str,
        pages: list[dict],
        titles: list[str],
        avg_word_count: int,
    ) -> tuple[str, str]:
        """Convert a signature to a human-readable name with context-aware description."""

        # Enhanced name map with descriptions
        template_info = {
            "homepage": ("Homepage", "Main landing page of the website"),
            "blog_post": ("Blog Article", "Individual blog posts or news articles"),
            "blog_index": ("Blog Index", "Blog listing page showing multiple posts"),
            "product_page": ("Product Page", "Individual product detail pages"),
            "product_listing": ("Product Listing", "Category or collection pages showing multiple products"),
            "category_page": ("Category Page", "Pages organizing content into categories"),
            "info_page": ("Information Page", "About, contact, and general information pages"),
            "faq_page": ("FAQ Page", "Frequently asked questions pages"),
            "legal_page": ("Legal Page", "Privacy policy, terms, and legal content"),
            "_other_": ("Miscellaneous", "Pages that don't match common patterns"),
            "content_page": ("Content Page", "Standard content pages"),
            "file_html": ("Static Page", "Static HTML pages"),
            "gallery": ("Gallery Page", "Image-heavy gallery or portfolio pages"),
            "minimal": ("Utility Page", "Pages with minimal content (redirects, confirmations)"),
            "long_form": ("Long-Form Content", "Detailed guides or comprehensive articles"),
        }

        # Remove language suffix for lookup
        base_sig = sig
        for lang in ["_en", "_es", "_de", "_fr", "_it", "_pt"]:
            if sig.endswith(lang):
                base_sig = sig[:-3]
                break

        # Remove content type suffix for lookup
        for suffix in ["_long_form", "_gallery", "_minimal"]:
            if base_sig.endswith(suffix):
                base_sig = base_sig.replace(suffix, "")
                break

        # Check for exact match first
        if base_sig in template_info:
            name, desc = template_info[base_sig]
        else:
            # Try partial matches
            found = False
            for key, (name, desc) in template_info.items():
                if key in base_sig:
                    found = True
                    break
            if not found:
                name = base_sig.replace("_", " ").title()
                desc = f"Pages with {base_sig.replace('_', ' ')} structure"

        # Enhance description with statistics
        page_count = len(pages)
        if avg_word_count > 0:
            desc = f"{desc}. Average {avg_word_count:,} words per page."

        # Try to detect content theme from titles
        if titles:
            common_words = self._find_common_title_words(titles)
            if common_words:
                theme = ", ".join(common_words[:3])
                desc = f"{desc} Common themes: {theme}."

        return name, desc

    def _find_common_title_words(self, titles: list[str]) -> list[str]:
        """Find commonly occurring words in titles."""
        from collections import Counter

        # Stopwords to ignore
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "shall", "can", "need",
            "de", "la", "el", "los", "las", "un", "una", "en", "y", "que", "del",
            "por", "con", "para", "es", "son", "o7", "hotels", "hotel", "-", "|",
        }

        words = []
        for title in titles:
            for word in title.lower().split():
                # Clean word
                word = word.strip(".,!?()[]{}:;\"'")
                if word and word not in stopwords and len(word) > 2:
                    words.append(word)

        # Get most common words
        counter = Counter(words)
        common = [word for word, count in counter.most_common(10) if count >= 2]
        return common[:3]

    def _generate_template_recommendations(
        self,
        pages: list[dict],
        avg_word_count: int,
    ) -> list[str]:
        """Generate SEO recommendations for a template type."""
        recommendations = []

        # Check for common issues
        pages_without_meta = sum(1 for p in pages if not p.get("meta_description"))
        pages_without_h1 = sum(1 for p in pages if not p.get("h1"))
        pages_with_multiple_h1 = sum(1 for p in pages if len(p.get("h1", []) or []) > 1)
        pages_low_word_count = sum(1 for p in pages if (p.get("word_count") or 0) < 300)

        total = len(pages)
        if total == 0:
            return recommendations

        # Meta description
        if pages_without_meta / total > 0.3:
            recommendations.append(
                f"Add meta descriptions: {pages_without_meta}/{total} pages missing meta descriptions"
            )

        # H1 issues
        if pages_without_h1 / total > 0.2:
            recommendations.append(
                f"Add H1 headings: {pages_without_h1}/{total} pages missing H1 tags"
            )
        if pages_with_multiple_h1 / total > 0.3:
            recommendations.append(
                f"Fix multiple H1s: {pages_with_multiple_h1}/{total} pages have more than one H1"
            )

        # Content length
        if pages_low_word_count / total > 0.5 and avg_word_count < 300:
            recommendations.append(
                f"Expand thin content: Average word count is only {avg_word_count}. Consider adding more content."
            )

        return recommendations

    def _humanize_signature(self, sig: str) -> str:
        """Convert a signature to a human-readable name (legacy compatibility)."""
        name, _ = self._humanize_signature_enhanced(sig, [], [], 0)
        return name

    def _extract_url_patterns_from_pages(self, pages: list[dict]) -> list[str]:
        """Extract common URL patterns from a group of pages."""
        patterns = set()

        for page in pages[:20]:  # Sample first 20
            url = page.get("url") or page.get("final_url", "")
            parsed = urlparse(url)
            path = parsed.path

            # Create pattern by replacing specific values with wildcards
            pattern = re.sub(r"/\d+", "/{id}", path)  # Numbers
            pattern = re.sub(r"/[a-f0-9-]{36}", "/{uuid}", pattern)  # UUIDs
            pattern = re.sub(r"/[a-z]{2}/", "/{lang}/", pattern)  # Language codes
            patterns.add(pattern)

        return list(patterns)[:5]  # Return up to 5 patterns


async def classify_site_templates(
    site_url: str,
    pages: list[dict],
    use_llm: bool = True,
) -> TemplateClassificationResult:
    """Convenience function to classify templates for a site."""
    classifier = TemplateClassifier()
    return await classifier.classify_pages(site_url, pages, use_llm=use_llm)
