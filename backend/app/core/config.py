from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AURI.AI"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-very-long-random-string"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://auri:auri_secret@localhost:5432/auri"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "auri-meetings"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None
    qdrant_collection: str = "meetings"

    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_timeout: int = 120

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepgram_api_key: str | None = None
    assemblyai_api_key: str | None = None
    google_api_key: str | None = None

    ai_mode: Literal["strict_private", "hybrid", "cloud"] = "strict_private"

    zoom_webhook_secret: str | None = None
    zoom_client_id: str | None = None
    zoom_client_secret: str | None = None

    google_oidc_client_id: str | None = None
    google_oidc_client_secret: str | None = None
    microsoft_oidc_client_id: str | None = None
    microsoft_oidc_client_secret: str | None = None
    microsoft_oidc_tenant: str | None = "common"
    oidc_redirect_base: str = "http://localhost:8000"
    okta_oidc_client_id: str | None = None
    okta_oidc_client_secret: str | None = None
    okta_domain: str | None = None

    settings_encryption_key: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_tls: bool = True
    frontend_url: str = "http://localhost:3000"

    hf_token: str | None = None

    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_enterprise: str | None = None

    rate_limit_fail_closed: bool = False
    use_redis_rate_limit: bool = True

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "auri-backend"

    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    @property
    def is_private_mode(self) -> bool:
        return self.ai_mode == "strict_private"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
