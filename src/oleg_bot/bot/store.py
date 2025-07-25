"""Message storage using sliding window for OlegBot."""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StoredMessage:
    """A message stored in the sliding window."""

    message_id: int
    chat_id: int
    user_id: int
    text: str | None
    timestamp: datetime
    is_bot_message: bool = False
    reply_to_message_id: int | None = None


class SlidingWindowStore:
    """Stores messages in a sliding window per chat."""

    def __init__(self, window_size: int = 50):
        """Initialize the store with a given window size."""
        self.window_size = window_size
        self._chat_windows: dict[int, deque[StoredMessage]] = {}
        logger.info(f"Initialized sliding window store with size {window_size}")

    def add_message(self, message: StoredMessage) -> None:
        """Add a message to the appropriate chat window."""
        chat_id = message.chat_id

        if chat_id not in self._chat_windows:
            self._chat_windows[chat_id] = deque(maxlen=self.window_size)

        self._chat_windows[chat_id].append(message)
        logger.debug(f"Added message {message.message_id} to chat {chat_id}")

    def get_messages(
        self, chat_id: int, limit: int | None = None
    ) -> list[StoredMessage]:
        """Get messages for a specific chat."""
        if chat_id not in self._chat_windows:
            return []

        messages = list(self._chat_windows[chat_id])
        if limit:
            messages = messages[-limit:]

        return messages

    def get_recent_text(self, chat_id: int, limit: int = 10) -> str:
        """Get concatenated text from recent messages for analysis."""
        messages = self.get_messages(chat_id, limit)
        text_messages = [msg.text for msg in messages if msg.text]
        return " ".join(text_messages)

    def has_recent_bot_message(self, chat_id: int, seconds: int = 20) -> bool:
        """Check if bot has sent a message recently in this chat."""
        messages = self.get_messages(chat_id)
        now = datetime.now()

        for message in reversed(messages):
            if message.is_bot_message:
                time_diff = (now - message.timestamp).total_seconds()
                if time_diff <= seconds:
                    return True
                break  # Only check the most recent bot message

        return False

    def get_chat_count(self) -> int:
        """Get the number of active chats."""
        return len(self._chat_windows)

    def clear_chat(self, chat_id: int) -> None:
        """Clear messages for a specific chat."""
        if chat_id in self._chat_windows:
            del self._chat_windows[chat_id]
            logger.info(f"Cleared messages for chat {chat_id}")


# Global store instance
message_store = SlidingWindowStore()
