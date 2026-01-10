"""
External service integrations for SEOman.

- seoanalyzer: Python SEO Analyzer for quick audits
- dataforseo: DataForSEO API for keyword research
- llm: LLM client for AI features (supports local/OpenAI/Anthropic)
- storage: S3-compatible storage using MinIO
- pagespeed: Google PageSpeed Insights for performance analysis
"""

from app.integrations.seoanalyzer import SEOAnalyzerClient
from app.integrations.dataforseo import DataForSEOClient
from app.integrations.pagespeed import PageSpeedClient
from app.integrations.llm import LLMClient, get_llm_client, Message, LLMResponse
from app.integrations.storage import (
    BaseStorageClient,
    LocalStorageClient,
    S3StorageClient,
    get_storage_client,
    SEOmanStoragePaths,
)

__all__ = [
    "SEOAnalyzerClient",
    "DataForSEOClient",
    "PageSpeedClient",
    "LLMClient",
    "get_llm_client",
    "Message",
    "LLMResponse",
    "BaseStorageClient",
    "LocalStorageClient",
    "S3StorageClient",
    "get_storage_client",
    "SEOmanStoragePaths",
]
