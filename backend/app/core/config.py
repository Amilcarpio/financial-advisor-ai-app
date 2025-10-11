"""Application configuration utilities."""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    app_name: str = Field(default="FastAPI Backend", env="APP_NAME")  # type: ignore[call-overload]
    app_env: str = Field(default="development", env="APP_ENV")  # type: ignore[call-overload]
    app_debug: bool = Field(default=False, env="APP_DEBUG")  # type: ignore[call-overload]
    database_url: str = Field(default=..., env="DATABASE_URL")  # type: ignore[call-overload]
    vector_dimension: int = Field(default=1536, env="VECTOR_DIMENSION")  # type: ignore[call-overload]
    auto_create_pgvector_extension: bool = Field(default=True, env="AUTO_CREATE_PGVECTOR_EXTENSION")  # type: ignore[call-overload]
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")  # type: ignore[call-overload]
    
    # Google OAuth
    google_client_id: str = Field(default="", env="GOOGLE_CLIENT_ID")  # type: ignore[call-overload]
    google_client_secret: str = Field(default="", env="GOOGLE_CLIENT_SECRET")  # type: ignore[call-overload]
    google_redirect_uri: str = Field(default="http://localhost:8000/auth/google/callback", env="GOOGLE_REDIRECT_URI")  # type: ignore[call-overload]
    
    # HubSpot OAuth
    hubspot_client_id: str = Field(default="", env="HUBSPOT_CLIENT_ID")  # type: ignore[call-overload]
    hubspot_client_secret: str = Field(default="", env="HUBSPOT_CLIENT_SECRET")  # type: ignore[call-overload]
    hubspot_redirect_uri: str = Field(default="http://localhost:8000/auth/hubspot/callback", env="HUBSPOT_REDIRECT_URI")  # type: ignore[call-overload]
    
    # Application
    secret_key: str = Field(default="dev-secret-key-change-in-production-min-32-characters", env="SECRET_KEY")  # type: ignore[call-overload]
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")  # type: ignore[call-overload]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def log_level(self) -> str:
        return "DEBUG" if self.app_debug else "INFO"

    @property
    def debug_sql(self) -> bool:
        return self.app_debug


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of application settings."""

    return Settings()


settings = get_settings()
