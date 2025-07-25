"""Startup tasks for OlegBot, including webhook registration."""

import logging
from typing import Any

from telegram import Bot, error

from ..config import settings

logger = logging.getLogger(__name__)


class StartupManager:
    """Handles bot startup tasks."""

    def __init__(self) -> None:
        self.bot: Bot | None = None
        self._webhook_registered = False

    async def initialize_bot(self) -> None:
        """Initialize the bot and perform startup tasks."""
        try:
            # Create bot instance
            self.bot = Bot(token=settings.telegram_bot_token)
            
            # Test bot connection
            bot_info = await self.bot.get_me()
            logger.info(f"Bot initialized: @{bot_info.username} ({bot_info.first_name})")
            
            # Register webhook if configured
            if settings.telegram_webhook_url:
                await self.register_webhook()
            else:
                logger.warning("No webhook URL configured - bot will not receive updates")
                
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

    async def register_webhook(self) -> None:
        """Register webhook with Telegram."""
        if not self.bot:
            raise RuntimeError("Bot not initialized")
            
        try:
            webhook_url = f"{settings.telegram_webhook_url}/webhook/telegram"
            
            # Set webhook
            await self.bot.set_webhook(
                url=webhook_url,
                secret_token=settings.telegram_webhook_secret,
                drop_pending_updates=True,  # Clear any pending updates
                allowed_updates=["message", "edited_message"]  # Only handle messages
            )
            
            # Verify webhook was set
            webhook_info = await self.bot.get_webhook_info()
            
            if webhook_info.url == webhook_url:
                self._webhook_registered = True
                logger.info(f"Webhook registered successfully: {webhook_url}")
                logger.info(f"Pending updates: {webhook_info.pending_update_count}")
            else:
                logger.error(f"Webhook registration failed - expected {webhook_url}, got {webhook_info.url}")
                
        except error.TelegramError as e:
            logger.error(f"Failed to register webhook: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error registering webhook: {e}")
            raise

    async def unregister_webhook(self) -> None:
        """Unregister webhook (for shutdown)."""
        if not self.bot:
            return
            
        try:
            await self.bot.delete_webhook(drop_pending_updates=False)
            self._webhook_registered = False
            logger.info("Webhook unregistered successfully")
        except Exception as e:
            logger.warning(f"Failed to unregister webhook: {e}")

    async def get_bot_status(self) -> dict[str, Any]:
        """Get bot status information."""
        if not self.bot:
            return {"status": "not_initialized"}
            
        try:
            bot_info = await self.bot.get_me()
            webhook_info = await self.bot.get_webhook_info()
            
            return {
                "status": "active",
                "bot_username": bot_info.username,
                "bot_name": bot_info.first_name,
                "webhook_url": webhook_info.url,
                "webhook_registered": self._webhook_registered,
                "pending_updates": webhook_info.pending_update_count,
                "last_error": webhook_info.last_error_message,
                "last_error_date": webhook_info.last_error_date.isoformat() if webhook_info.last_error_date else None,
            }
        except Exception as e:
            logger.error(f"Failed to get bot status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def shutdown(self) -> None:
        """Shutdown the bot and cleanup resources."""
        try:
            if self._webhook_registered:
                await self.unregister_webhook()
                
            if self.bot:
                # Close the bot session
                await self.bot.close()
                self.bot = None
                
            logger.info("Bot shutdown completed")
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")


# Global startup manager instance
startup_manager = StartupManager()