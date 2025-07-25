"""Main FastAPI application for OlegBot."""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .bot.startup import startup_manager
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

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

def get_client_ip(request: Request) -> str:
    """Get client IP for rate limiting, considering proxies."""
    # Check for forwarded headers (for proxy setups)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fallback to remote address
    return get_remote_address(request)


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

    # Initialize bot and register webhook
    try:
        await startup_manager.initialize_bot()
        logger.info("Bot initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        if settings.is_production():
            raise  # Fail fast in production
        else:
            logger.warning("Continuing without bot initialization (development mode)")

    logger.info("OlegBot startup complete")

    yield

    # Shutdown
    logger.info("OlegBot shutting down...")
    try:
        await startup_manager.shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    logger.info("OlegBot shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="OlegBot",
    description="Witty Telegram bot powered by GPT-4o",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

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


@app.get("/bot/status")
async def bot_status() -> dict[str, Any]:
    """Get detailed bot status information."""
    return await startup_manager.get_bot_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "oleg_bot.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
