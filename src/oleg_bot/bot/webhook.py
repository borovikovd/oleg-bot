"""Webhook handler for Telegram updates."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from telegram import Update

from ..config import settings
from .commands import command_handler
from .decision import ResponseAction, decision_engine
from .language import language_detector
from .reactions import reaction_handler
from .responder import gpt_responder
from .store import StoredMessage, message_store
from .tone import tone_analyzer

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

            # Send command response (in a real implementation, this would use the Telegram API)
            logger.info(f"Command response: {response}")

            # Store bot's command response
            bot_message = StoredMessage(
                message_id=message.message_id + 10000,  # Fake message ID
                chat_id=message.chat_id,
                user_id=0,  # Bot user ID
                text=response,
                timestamp=datetime.now(),
                is_bot_message=True,
            )
            message_store.add_message(bot_message)
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

            # In a real implementation, this would use the Telegram API to add reaction
            logger.info(
                f"Bot reaction to message {message.message_id}: {reaction}"
            )

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

                # In a real implementation, this would use the Telegram API to send message
                logger.info(
                    f"Bot reply to message {message.message_id}: {response_text}"
                )

                # Store bot's response
                bot_message = StoredMessage(
                    message_id=message.message_id + 10000,  # Fake message ID
                    chat_id=message.chat_id,
                    user_id=0,  # Bot user ID
                    text=response_text,
                    timestamp=datetime.now(),
                    is_bot_message=True,
                )
                message_store.add_message(bot_message)

            except Exception as e:
                logger.error(f"Failed to generate response: {e}")
                # Fall back to reaction
                reaction = reaction_handler.choose_reaction(
                    message.text, tone_hints, detected_language, "neutral"
                )
                logger.info(
                    f"Bot fallback reaction to message {message.message_id}: {reaction}"
                )

    except Exception as e:
        logger.error(f"Error in bot logic processing: {e}")
