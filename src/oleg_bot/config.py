"""Configuration management for OlegBot."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Telegram Bot Configuration
    telegram_bot_token: str = ""
    telegram_webhook_secret: str | None = None
    telegram_webhook_url: str = ""

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Bot Behavior Settings
    window_size: int = 50
    reply_target_ratio: float = 0.10
    gap_min_seconds: int = 20
    max_response_words: int = 100

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


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
            openai_api_key="test_key",
        )


# Global settings instance
settings = get_settings()
