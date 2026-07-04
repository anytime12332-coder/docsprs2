"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "DocuMind IDP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/documind"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/documind"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    ADMIN_EMAIL: str = "admin@documind.io"
    ADMIN_PASSWORD: str = "admin123456"
    ADMIN_FULL_NAME: str = "System Administrator"

    # Storage
    STORAGE_BACKEND: str = "local"  # local | s3
    LOCAL_STORAGE_PATH: str = "./storage"
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT_URL: str = ""

    # OCR
    OCR_ENGINE: str = "tesseract"  # tesseract | paddleocr
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_LANGUAGES: str = "en"
    OCR_DPI: int = 300

    # AI/LLM
    LLM_PROVIDER: str = "openai"  # openai | anthropic | local
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Processing
    MAX_FILE_SIZE_MB: int = 100
    MAX_PAGES_PER_DOCUMENT: int = 500
    PROCESSING_TIMEOUT_SECONDS: int = 600
    MAX_CONCURRENT_JOBS: int = 10
    SUPPORTED_FORMATS: str = "pdf,docx,xlsx,csv,png,jpg,jpeg,tiff,bmp,webp,html"

    # Webhooks
    WEBHOOK_TIMEOUT_SECONDS: int = 30
    WEBHOOK_MAX_RETRIES: int = 3

    # Monitoring
    SENTRY_DSN: str = ""
    ENABLE_METRICS: bool = True

    def normalize_database_urls(self) -> None:
        """Coerce DB URLs to the correct drivers.

        Railway (and most managed Postgres) expose a single DATABASE_URL like
        'postgresql://...' or 'postgres://...'. The async engine needs
        'postgresql+asyncpg://...' and Alembic needs a sync driver. This makes
        the app tolerant of whatever form the platform injects.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            self.DATABASE_SYNC_URL = url
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        self.DATABASE_URL = url

        sync = self.DATABASE_SYNC_URL
        if sync.startswith("postgres://"):
            sync = "postgresql://" + sync[len("postgres://"):]
        if sync.startswith("postgresql+asyncpg://"):
            sync = "postgresql://" + sync[len("postgresql+asyncpg://"):]
        self.DATABASE_SYNC_URL = sync

    def validate_production_security(self) -> None:
        """Warn on insecure defaults when not in DEBUG mode."""
        if self.DEBUG:
            return
        import sys
        insecure = []
        if self.SECRET_KEY == "change-me-in-production-use-openssl-rand-hex-32":
            insecure.append("SECRET_KEY")
        if self.ADMIN_PASSWORD == "admin123456":
            insecure.append("ADMIN_PASSWORD")
        if insecure:
            msg = (
                f"WARNING: Insecure default value(s) detected for "
                f"{', '.join(insecure)}. Set secure values via environment "
                f"variables before running in production."
            )
            print(f"\n{'='*60}\n{msg}\n{'='*60}\n", file=sys.stderr, flush=True)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def supported_formats_list(self) -> list[str]:
        return [f.strip() for f in self.SUPPORTED_FORMATS.split(",")]

    @property
    def storage_path(self) -> Path:
        path = Path(self.LOCAL_STORAGE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
settings.normalize_database_urls()
settings.validate_production_security()
