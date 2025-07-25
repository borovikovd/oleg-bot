"""Webhook handler for Telegram updates."""

import logging
import traceback
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from telegram import Bot, Update, error

from ..config import settings
from .commands import command_handler
from .decision import ResponseAction, decision_engine
from .language import language_detector
from .reactions import reaction_handler
from .responder import gpt_responder
from .startup import startup_manager
from .store import StoredMessage, message_store
from .tone import tone_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

# Create rate limiter for webhook endpoints
limiter = Limiter(key_func=get_remote_address)

# Error tracking
class ErrorTracker:
    """Simple error tracking for monitoring critical issues."""

    def __init__(self) -> None:
        self.error_counts: dict[str, int] = {}
        self.recent_errors: list[dict[str, Any]] = []
        self.max_recent_errors = 50

    def track_error(self, error_type: str, error_message: str, context: dict[str, Any] | None = None) -> None:
        """Track an error occurrence."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        error_info = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_message,
            "context": context or {},
        }

        self.recent_errors.append(error_info)

        # Keep only recent errors
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[-self.max_recent_errors:]

        # Log critical errors
        if error_type in ["webhook_failure", "config_error", "gpt_api_failure"]:
            logger.error(f"CRITICAL ERROR [{error_type}]: {error_message}", extra={"context": context})

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        return {
            "error_counts": self.error_counts,
            "recent_errors": self.recent_errors[-10:],  # Last 10 errors
            "total_errors": sum(self.error_counts.values()),
        }

    def reset_stats(self) -> None:
        """Reset error statistics."""
        self.error_counts.clear()
        self.recent_errors.clear()
        logger.info("Error statistics reset")

# Global error tracker
error_tracker = ErrorTracker()

def get_bot() -> Bot:
    """Get the shared bot instance from startup manager."""
    if not startup_manager.bot:
        raise RuntimeError("Bot not initialized - startup may have failed")
    return startup_manager.bot


async def send_message(
    chat_id: int,
    text: str,
    reply_to_message_id: int | None = None,
    parse_mode: str | None = "Markdown"
) -> None:
    """Send a message via Telegram API with error handling."""
    try:
        bot = get_bot()
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=reply_to_message_id,
            parse_mode=parse_mode
        )

        # Store bot's message in the message store
        bot_message = StoredMessage(
            message_id=sent_message.message_id,
            chat_id=chat_id,
            user_id=0,  # Bot user ID
            text=text,
            timestamp=datetime.now(),
            is_bot_message=True,
            reply_to_message_id=reply_to_message_id,
        )
        message_store.add_message(bot_message)

        logger.info(f"Sent message to chat {chat_id}: {text[:50]}...")

    except error.TelegramError as e:
        error_tracker.track_error(
            "telegram_api_error",
            f"Failed to send message: {e}",
            {"chat_id": chat_id, "error_code": getattr(e, 'message', None)}
        )
        logger.error(f"Failed to send message to chat {chat_id}: {e}")
        raise
    except Exception as e:
        error_tracker.track_error(
            "message_send_error",
            str(e),
            {"chat_id": chat_id}
        )
        logger.error(f"Unexpected error sending message: {e}")
        raise


async def send_reaction(chat_id: int, message_id: int, reaction: str) -> None:
    """Send a reaction via Telegram API with error handling."""
    try:
        bot = get_bot()
        await bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[reaction]
        )

        logger.info(f"Sent reaction {reaction} to message {message_id} in chat {chat_id}")

    except error.TelegramError as e:
        # Reactions might not be supported in all chats, so log as warning instead of error
        logger.warning(f"Failed to send reaction to chat {chat_id}: {e}")
        error_tracker.track_error(
            "telegram_reaction_error",
            f"Failed to send reaction: {e}",
            {"chat_id": chat_id, "message_id": message_id, "reaction": reaction}
        )
    except Exception as e:
        logger.error(f"Unexpected error sending reaction: {e}")
        error_tracker.track_error(
            "reaction_send_error",
            str(e),
            {"chat_id": chat_id, "message_id": message_id}
        )


@router.post("/telegram")
@limiter.limit("100/minute")  # Limit to 100 webhook calls per minute per IP
async def handle_telegram_webhook(request: Request) -> dict[str, str]:
    """Handle incoming Telegram webhook updates."""
    try:
        # Verify webhook secret if configured
        if settings.telegram_webhook_secret:
            webhook_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if webhook_secret != settings.telegram_webhook_secret:
                logger.warning("Invalid webhook secret received")
                raise HTTPException(status_code=403, detail="Invalid webhook secret")

        # Parse the update
        body = await request.json()
        try:
            update = Update.de_json(body, None)
        except Exception as e:
            logger.warning(f"Failed to parse update: {e}")
            raise HTTPException(status_code=400, detail="Invalid update format") from e

        if not update:
            logger.warning("Received invalid update")
            raise HTTPException(status_code=400, detail="Invalid update")

        # Process the update
        await process_update(update)

        return {"status": "ok"}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_tracker.track_error(
            "webhook_failure",
            str(e),
            {"traceback": traceback.format_exc(), "endpoint": "telegram_webhook"}
        )
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


async def process_update(update: Update) -> None:
    """Process a Telegram update."""
    try:
        if update.message:
            await process_message(update.message)
        elif update.edited_message:
            await process_message(update.edited_message, is_edit=True)
        else:
            logger.debug(f"Ignoring update type: {type(update)}")

    except Exception as e:
        error_tracker.track_error(
            "update_processing_error",
            str(e),
            {"update_type": type(update).__name__}
        )
        logger.error(f"Error processing update: {e}")


async def process_message(message: Any, is_edit: bool = False) -> None:
    """Process a Telegram message and store it."""
    try:
        # Extract message data
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else 0
        message_id = message.message_id
        text = message.text or message.caption
        timestamp = datetime.now()

        # Check if it's a reply
        reply_to_message_id = None
        if message.reply_to_message:
            reply_to_message_id = message.reply_to_message.message_id

        # Create stored message
        stored_message = StoredMessage(
            message_id=message_id,
            chat_id=chat_id,
            user_id=user_id,
            text=text,
            timestamp=timestamp,
            is_bot_message=False,  # We'll update this when we send bot messages
            reply_to_message_id=reply_to_message_id,
        )

        # Store the message
        message_store.add_message(stored_message)

        # Log the message (without sensitive content)
        log_prefix = "Edited message" if is_edit else "Message"
        logger.info(
            f"{log_prefix} received: chat_id={chat_id}, "
            f"user_id={user_id}, message_id={message_id}, "
            f"has_text={bool(text)}"
        )

        # Process message for potential response
        await process_bot_logic(stored_message)

    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def process_bot_logic(message: StoredMessage) -> None:
    """Process bot logic for a message (commands, decisions, responses)."""
    try:
        # Skip processing for bot messages
        if message.is_bot_message:
            return

        # Skip messages without text
        if not message.text:
            logger.debug(f"Skipping message {message.message_id} without text")
            return

        # Handle commands first
        if command_handler.is_command(message.text):
            response = command_handler.handle_command(
                message.text, message.user_id, message.chat_id
            )

            # Send command response via Telegram API
            await send_message(message.chat_id, response, reply_to_message_id=message.message_id)
            return

        # Use decision engine to determine response
        decision = decision_engine.should_respond(message.chat_id, message)

        logger.debug(
            f"Decision for message {message.message_id}: "
            f"action={decision.action.value}, confidence={decision.confidence:.2f}, "
            f"reasoning='{decision.reasoning}'"
        )

        if not decision.should_process:
            return

        # Get recent messages for context
        recent_messages = message_store.get_messages(message.chat_id, limit=10)

        # Analyze language and tone
        message_texts = [msg.text for msg in recent_messages if msg.text]
        detected_language = language_detector.detect_from_messages(message_texts)
        tone_hints = tone_analyzer.analyze_tone(message_texts)

        if decision.action == ResponseAction.REACT:
            # Choose and send reaction
            if decision.reasoning.startswith("Direct mention"):
                reaction = reaction_handler.get_reaction_for_mention(tone_hints)
            elif decision.reasoning.startswith("Reply to bot"):
                reaction = reaction_handler.get_reaction_for_reply(tone_hints)
            else:
                reaction = reaction_handler.choose_reaction(
                    message.text, tone_hints, detected_language, "neutral"
                )

            # Send reaction via Telegram API
            await send_reaction(message.chat_id, message.message_id, reaction)

        elif decision.action == ResponseAction.REPLY:
            # Generate and send text response
            try:
                response_text = await gpt_responder.generate_response(
                    message=message,
                    recent_messages=recent_messages,
                    language=detected_language,
                    tone_hints=tone_hints,
                    chat_context="group chat",
                )

                # Send reply via Telegram API
                await send_message(message.chat_id, response_text, reply_to_message_id=message.message_id)

            except Exception as e:
                error_tracker.track_error(
                    "gpt_api_failure",
                    str(e),
                    {"message_id": message.message_id, "chat_id": message.chat_id}
                )
                logger.error(f"Failed to generate response: {e}")
                # Fall back to reaction
                reaction = reaction_handler.choose_reaction(
                    message.text, tone_hints, detected_language, "neutral"
                )
                await send_reaction(message.chat_id, message.message_id, reaction)

    except Exception as e:
        error_tracker.track_error(
            "bot_logic_error",
            str(e),
            {"message_id": message.message_id, "chat_id": message.chat_id}
        )
        logger.error(f"Error in bot logic processing: {e}")


@router.get("/errors")
@limiter.limit("30/minute")  # Limit error stats access
async def get_error_stats(request: Request) -> dict[str, Any]:
    """Get error statistics for monitoring."""
    return error_tracker.get_error_stats()


@router.post("/errors/reset")
@limiter.limit("10/hour")  # Strict limit for reset operations
async def reset_error_stats(request: Request) -> dict[str, str]:
    """Reset error statistics (admin endpoint)."""
    error_tracker.reset_stats()
    return {"status": "reset", "message": "Error statistics have been reset"}


@router.get("/memory")
@limiter.limit("60/minute")  # Allow frequent memory monitoring
async def get_memory_stats(request: Request) -> dict[str, Any]:
    """Get memory usage statistics."""
    return message_store.get_memory_stats()


@router.post("/memory/cleanup")
@limiter.limit("5/hour")  # Limited cleanup operations
async def force_memory_cleanup(request: Request) -> dict[str, Any]:
    """Force cleanup of inactive chats."""
    return message_store.force_cleanup()
