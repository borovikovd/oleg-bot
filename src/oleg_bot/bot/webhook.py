"""Webhook handler for Telegram updates."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from telegram import Update

from ..config import settings
from .store import StoredMessage, message_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/telegram")
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

        # TODO: Process message for potential response
        # This will be implemented in the decision engine

    except Exception as e:
        logger.error(f"Error processing message: {e}")
