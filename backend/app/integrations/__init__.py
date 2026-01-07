"""
External service integrations for SEOman.

- seoanalyzer: Python SEO Analyzer for quick audits
- dataforseo: DataForSEO API for keyword research
- llm: LLM client for AI features (supports local/OpenAI/Anthropic)
- storage: S3-compatible storage using MinIO
"""

from app.integrations.seoanalyzer import SEOAnalyzerClient
from app.integrations.dataforseo import DataForSEOClient
from app.integrations.llm import LLMClient, get_llm_client, Message, LLMResponse
from app.integrations.storage import StorageClient, get_storage_client, SEOmanStoragePaths

__all__ = [
    # SEO Analyzer
    "SEOAnalyzerClient",
    # DataForSEO
    "DataForSEOClient",
    # LLM
    "LLMClient",
    "get_llm_client",
    "Message",
    "LLMResponse",
    # Storage
    "StorageClient",
    "get_storage_client",
    "SEOmanStoragePaths",
]
