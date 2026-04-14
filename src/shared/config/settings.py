from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Baixar Videos Privados API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    public_download_failure_message: str = "Nao foi possivel baixar o video."
    api_key: str = ""
    api_key_header_name: str = "X-API-Key"
    job_repository_backend: Literal["sqlite", "in_memory"] = "sqlite"
    sqlite_db_path: str = "data/download_jobs.db"
    authorization_cache_ttl_seconds: int = 180
    authorization_cache_max_size: int = 2000
    requester_rate_limit_enabled: bool = True
    requester_rate_limit_window_seconds: int = 60
    requester_rate_limit_max_requests: int = 30
    provider_retry_max_attempts: int = 3
    provider_retry_base_delay_seconds: float = 0.1
    download_worker_concurrency: int = 2
    queue_backend: Literal["in_process", "redis"] = "in_process"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_key: str = "download_jobs_queue"
    download_output_dir: str = "downloads"
    download_http_timeout_seconds: float = 120.0
    allowed_source_hosts: str = ""
    enable_platform_extractor: bool = True
    extractor_concurrent_fragment_downloads: int = 8
    download_quality_default: Literal["best", "high", "medium", "low", "audio"] = "best"
    download_file_token_secret: str = "change-me-in-prod"
    download_file_token_ttl_seconds: int = 300
    retention_cleanup_enabled: bool = True
    retention_cleanup_interval_seconds: int = 3600
    terminal_job_retention_hours: int = 24
    metrics_enabled: bool = True
    expose_failure_diagnostic_detail: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
