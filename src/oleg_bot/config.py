"""Configuration management for OlegBot."""

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with production validation."""

    # Telegram Bot Configuration
    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token from @BotFather",
        min_length=1,
    )
    telegram_webhook_secret: str | None = Field(
        default=None,
        description="Optional webhook secret for security",
        min_length=8,
    )
    telegram_webhook_url: str = Field(
        default="",
        description="Public HTTPS URL for webhook endpoint",
        min_length=1,
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for GPT-4o",
        min_length=1,
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use for responses",
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL (for OpenRouter or other providers)",
    )

    # Admin Configuration
    admin_user_ids: list[int] = Field(
        default_factory=list,
        description="Telegram user IDs with admin privileges",
    )

    # Bot Behavior Settings
    window_size: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Number of messages to keep in sliding window",
    )
    reply_target_ratio: float = Field(
        default=0.10,
        ge=0.01,
        le=0.50,
        description="Target ratio of messages to reply to (1-50%)",
    )
    gap_min_seconds: int = Field(
        default=20,
        ge=5,
        le=300,
        description="Minimum seconds between bot replies",
    )
    max_response_words: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum words in bot responses",
    )

    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to",
    )
    port: int = Field(
        default=8000,
        ge=1000,
        le=65535,
        description="Port to bind the server to",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (not for production)",
    )

    # Production Settings
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @field_validator("telegram_webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        """Validate webhook URL is HTTPS in production."""
        if v and not v.startswith("https://"):
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError("Webhook URL must use HTTPS in production")
        return v

    @field_validator("telegram_bot_token")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Validate bot token format."""
        # Skip validation for test environments
        if v in ["test_token", ""]:
            return v
        if v and not v.count(":") == 1:
            raise ValueError("Invalid bot token format")
        return v

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """Validate OpenAI API key format."""
        # Skip validation for test environments
        if v in ["test_key", ""]:
            return v
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def validate_production_config(self) -> list[str]:
        """Validate configuration for production deployment."""
        errors = []

        if self.is_production():
            # Required fields for production
            if not self.telegram_bot_token:
                errors.append("TELEGRAM_BOT_TOKEN is required in production")
            if not self.telegram_webhook_url:
                errors.append("TELEGRAM_WEBHOOK_URL is required in production")
            if not self.openai_api_key:
                errors.append("OPENAI_API_KEY is required in production")

            # Security requirements
            if not self.telegram_webhook_secret:
                errors.append("TELEGRAM_WEBHOOK_SECRET is recommended in production")
            if self.debug:
                errors.append("DEBUG should be False in production")
            if not self.telegram_webhook_url.startswith("https://"):
                errors.append("Webhook URL must use HTTPS in production")

        return errors


def get_settings() -> Settings:
    """Get settings instance with proper error handling."""
    try:
        return Settings()
    except Exception as e:
        # In test/dev environments, provide defaults
        import warnings

        warnings.warn(f"Could not load settings from environment: {e}", stacklevel=2)
        return Settings(
            telegram_bot_token="test_token",
            telegram_webhook_url="http://localhost:8000/webhook/telegram",
            openai_api_key="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",
            openai_model="google/gemini-2.0-flash-exp:free",
            openai_base_url="https://openrouter.ai/api/v1",
            admin_user_ids=[],
        )


# Global settings instance
settings = get_settings()
