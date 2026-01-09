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
