from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Baixar Videos Privados API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    public_download_failure_message: str = "Nao foi possivel baixar o video."
    authorization_cache_ttl_seconds: int = 180
    authorization_cache_max_size: int = 2000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
