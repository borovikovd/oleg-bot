"""Main FastAPI application for OlegBot."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from .bot.webhook import router as webhook_router
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage application lifespan."""
    logger.info("Starting OlegBot...")
    yield
    logger.info("Shutting down OlegBot...")


# Create FastAPI application
app = FastAPI(
    title="OlegBot",
    description="Witty, stateless GPT-4o-powered Telegram bot",
    version="0.1.0",
    lifespan=lifespan,
)

# Add routers
app.include_router(webhook_router)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "oleg-bot"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "OlegBot is running", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "oleg_bot.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
