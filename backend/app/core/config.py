"""Application configuration utilities."""
from functools import lru_cache
from typing import Optional
import sys

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    app_name: str = Field(default="FastAPI Backend", env="APP_NAME")  # type: ignore[call-overload]
    app_env: str = Field(default="development", env="APP_ENV")  # type: ignore[call-overload]
    app_debug: bool = Field(default=False, env="APP_DEBUG")  # type: ignore[call-overload]
    database_url: str = Field(default=..., env="DATABASE_URL")  # type: ignore[call-overload]
    vector_dimension: int = Field(default=1536, env="VECTOR_DIMENSION")  # type: ignore[call-overload]
    auto_create_pgvector_extension: bool = Field(default=True, env="AUTO_CREATE_PGVECTOR_EXTENSION")  # type: ignore[call-overload]
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")  # type: ignore[call-overload]
    openai_chat_model: str = Field(default="gpt-5-nano", env="OPENAI_CHAT_MODEL")  # type: ignore[call-overload]
    openai_embedding_model: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")  # type: ignore[call-overload]
    
    # Google OAuth
    google_client_id: str = Field(default="", env="GOOGLE_CLIENT_ID")  # type: ignore[call-overload]
    google_client_secret: str = Field(default="", env="GOOGLE_CLIENT_SECRET")  # type: ignore[call-overload]
    google_redirect_uri: str = Field(default="http://localhost:8000/api/auth/google/callback", env="GOOGLE_REDIRECT_URI")  # type: ignore[call-overload]
    
    # HubSpot OAuth
    hubspot_client_id: str = Field(default="", env="HUBSPOT_CLIENT_ID")  # type: ignore[call-overload]
    hubspot_client_secret: str = Field(default="", env="HUBSPOT_CLIENT_SECRET")  # type: ignore[call-overload]
    hubspot_redirect_uri: str = Field(default="http://localhost:8000/api/auth/hubspot/callback", env="HUBSPOT_REDIRECT_URI")  # type: ignore[call-overload]

    # Application
    secret_key: str = Field(default="dev-secret-key-change-in-production-min-32-characters", env="SECRET_KEY")  # type: ignore[call-overload]
    frontend_url: str = Field(default="http://localhost:5173", env="FRONTEND_URL")  # type: ignore[call-overload]

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate that secret_key is not using default value in production."""
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and v.startswith("dev-"):
            print("ERROR: Using default SECRET_KEY in production is not allowed!")
            sys.exit(1)
        if len(v) < 32:
            print(f"ERROR: SECRET_KEY must be at least 32 characters (current: {len(v)})")
            sys.exit(1)
        return v

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
