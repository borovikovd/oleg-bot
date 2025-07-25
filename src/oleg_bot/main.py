"""Main FastAPI application for OlegBot."""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from .bot.webhook import router as webhook_router
from .config import settings

# Configure logging with production settings
log_level = getattr(logging, settings.log_level, logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def validate_startup_config() -> None:
    """Validate configuration at startup."""
    logger.info(f"Starting OlegBot in {settings.environment} environment")

    # Validate production configuration
    if settings.is_production():
        logger.info("Running production configuration validation...")
        errors = settings.validate_production_config()
        if errors:
            logger.error("Production configuration errors:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)
        logger.info("Production configuration validation passed")
    else:
        logger.warning(f"Running in {settings.environment} mode - not for production use")

    # Log configuration (without sensitive data)
    logger.info(f"Server configuration: {settings.host}:{settings.port}")
    logger.info(f"Bot window size: {settings.window_size} messages")
    logger.info(f"Target reply ratio: {settings.reply_target_ratio:.1%}")
    logger.info(f"Minimum gap between replies: {settings.gap_min_seconds}s")
    logger.info(f"Max response words: {settings.max_response_words}")
    logger.info(f"OpenAI model: {settings.openai_model}")
    logger.info(f"Debug mode: {settings.debug}")

    # Validate required settings without exposing values
    if settings.telegram_bot_token:
        logger.info("✅ Telegram bot token configured")
    else:
        logger.warning("⚠️ Telegram bot token not configured")

    if settings.openai_api_key:
        logger.info("✅ OpenAI API key configured")
    else:
        logger.warning("⚠️ OpenAI API key not configured")

    if settings.telegram_webhook_url:
        logger.info("✅ Webhook URL configured")
    else:
        logger.warning("⚠️ Webhook URL not configured")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan management."""
    # Startup
    logger.info("OlegBot starting up...")
    validate_startup_config()
    logger.info("OlegBot startup complete")

    yield

    # Shutdown
    logger.info("OlegBot shutting down...")


# Create FastAPI app
app = FastAPI(
    title="OlegBot",
    description="Witty Telegram bot powered by GPT-4o",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# Include routers
app.include_router(webhook_router)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with basic bot information."""
    return {
        "message": "OlegBot is running",
        "version": "0.1.0",
        "environment": settings.environment,
        "status": "healthy",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "oleg-bot"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "oleg_bot.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
