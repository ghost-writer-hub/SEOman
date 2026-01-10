from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "SEOman"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    REDIS_URL: str
    
    # Storage Configuration
    # Provider: "local" for filesystem, "minio" for MinIO, "b2" for Backblaze B2
    STORAGE_PROVIDER: str = "local"
    
    # Local Filesystem Storage (for development without S3)
    LOCAL_STORAGE_PATH: str = "/app/storage"
    LOCAL_STORAGE_BASE_URL: str = "http://localhost:8000/files"
    
    # MinIO Configuration (local S3-compatible)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_USE_SSL: bool = False
    MINIO_BUCKET: str = "seoman-files"
    
    # Backblaze B2 Configuration (production)
    B2_ENDPOINT: str = ""
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET: str = ""
    B2_REGION: str = "us-west-004"
    
    # LLM Configuration
    # Provider: "openai", "anthropic", or "local" (LM Studio)
    LLM_PROVIDER: str = "openai"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""  # Set OPENAI_API_KEY in env
    LLM_MODEL: str = "gpt-4o-mini"

    # OpenAI-specific (alias for LLM_API_KEY)
    OPENAI_API_KEY: str = ""
    
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    
    CASDOOR_ENDPOINT: str = "http://localhost:8080"
    CASDOOR_CLIENT_ID: str
    CASDOOR_CLIENT_SECRET: str
    CASDOOR_ORGANIZATION: str = "seoman"
    CASDOOR_APPLICATION: str = "seoman-app"
    
    DEEPCRAWL_API_URL: str
    DATAFORSEO_API_URL: str
    DATAFORSEO_API_LOGIN: str = ""
    DATAFORSEO_API_PASSWORD: str = ""
    
    CORS_ORIGINS: str = "http://localhost:3011,http://seoman.yourdomain.com"
    
    LOG_LEVEL: str = "DEBUG"
    SENTRY_DSN: str = ""
    
    MAX_PAGES_PER_CRAWL: int = 20000
    MAX_KEYWORD_QUERIES_PER_MONTH: int = 1000

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST_MULTIPLIER: float = 1.5

    # Default Plan Quotas (monthly)
    QUOTA_FREE_API_CALLS: int = 1000
    QUOTA_FREE_CRAWL_PAGES: int = 5000
    QUOTA_FREE_KEYWORD_LOOKUPS: int = 100
    QUOTA_FREE_AUDITS: int = 10
    QUOTA_FREE_CONTENT_GENERATIONS: int = 20
    QUOTA_FREE_JS_RENDERS: int = 500

    QUOTA_PRO_API_CALLS: int = 50000
    QUOTA_PRO_CRAWL_PAGES: int = 100000
    QUOTA_PRO_KEYWORD_LOOKUPS: int = 5000
    QUOTA_PRO_AUDITS: int = 100
    QUOTA_PRO_CONTENT_GENERATIONS: int = 500
    QUOTA_PRO_JS_RENDERS: int = 10000

    QUOTA_ENTERPRISE_API_CALLS: int = 0  # 0 = unlimited
    QUOTA_ENTERPRISE_CRAWL_PAGES: int = 0
    QUOTA_ENTERPRISE_KEYWORD_LOOKUPS: int = 0
    QUOTA_ENTERPRISE_AUDITS: int = 0
    QUOTA_ENTERPRISE_CONTENT_GENERATIONS: int = 0
    QUOTA_ENTERPRISE_JS_RENDERS: int = 0
    
    # Quick SEO Analyzer Configuration
    PYTHON_SEOANALYZER_URL: str = os.getenv("PYTHON_SEOANALYZER_URL", "http://quick-analyzer:8080")
    PYTHON_SEOANALYZER_TIMEOUT: int = int(os.getenv("PYTHON_SEOANALYZER_TIMEOUT", "30"))
    
    # Analyzer Selection
    DEFAULT_AUDIT_THRESHOLD_PAGES: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [o.strip() for o in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS


settings = Settings()
