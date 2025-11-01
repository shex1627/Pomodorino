"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider
    anthropic_api_key: str
    openai_api_key: Optional[str] = None

    # YouTube API
    youtube_api_key: Optional[str] = None

    # Development
    debug: bool = False
    log_level: str = "INFO"

    # LLM Configuration
    primary_llm_provider: str = "anthropic"
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    openai_model: str = "gpt-4-turbo-preview"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
