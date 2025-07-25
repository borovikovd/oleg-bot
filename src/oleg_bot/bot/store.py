"""Message storage using sliding window for OlegBot."""

import logging
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

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
    """Stores messages in a sliding window per chat with memory management."""

    def __init__(self, window_size: int = 50, max_chats: int = 1000, cleanup_interval_hours: int = 24):
        """
        Initialize the store with memory management.

        Args:
            window_size: Number of messages to keep per chat
            max_chats: Maximum number of chats to track (LRU eviction)
            cleanup_interval_hours: Hours before inactive chats are cleaned up
        """
        self.window_size = window_size
        self.max_chats = max_chats
        self.cleanup_interval = timedelta(hours=cleanup_interval_hours)

        # Use OrderedDict for LRU behavior
        self._chat_windows: OrderedDict[int, deque[StoredMessage]] = OrderedDict()
        self._chat_last_activity: dict[int, datetime] = {}

        logger.info(
            f"Initialized sliding window store: window_size={window_size}, "
            f"max_chats={max_chats}, cleanup_interval={cleanup_interval_hours}h"
        )

    def add_message(self, message: StoredMessage) -> None:
        """Add a message to the appropriate chat window with memory management."""
        chat_id = message.chat_id
        now = datetime.now()

        # Update last activity time
        self._chat_last_activity[chat_id] = now

        # Create chat window if needed
        if chat_id not in self._chat_windows:
            # Check if we need to evict old chats (LRU)
            if len(self._chat_windows) >= self.max_chats:
                self._evict_least_recently_used()

            self._chat_windows[chat_id] = deque(maxlen=self.window_size)

        # Move chat to end (most recently used)
        self._chat_windows.move_to_end(chat_id)

        # Add message to chat window
        self._chat_windows[chat_id].append(message)

        # Trigger cleanup occasionally (every 100 messages roughly)
        if len(self._chat_windows) % 100 == 0:
            self._cleanup_inactive_chats()

        logger.debug(f"Added message {message.message_id} to chat {chat_id}")

    def get_messages(
        self, chat_id: int, limit: int | None = None
    ) -> list[StoredMessage]:
        """Get messages for a specific chat."""
        if chat_id not in self._chat_windows:
            return []

        # Update access time (LRU)
        self._chat_windows.move_to_end(chat_id)
        self._chat_last_activity[chat_id] = datetime.now()

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
            self._chat_last_activity.pop(chat_id, None)
            logger.info(f"Cleared messages for chat {chat_id}")

    def _evict_least_recently_used(self) -> None:
        """Evict the least recently used chat to make space."""
        if not self._chat_windows:
            return

        # OrderedDict keeps insertion order, first item is least recently used
        lru_chat_id = next(iter(self._chat_windows))
        self.clear_chat(lru_chat_id)
        logger.info(f"Evicted LRU chat {lru_chat_id} due to memory limit")

    def _cleanup_inactive_chats(self) -> None:
        """Remove chats that haven't been active recently."""
        now = datetime.now()
        inactive_chats = []

        for chat_id, last_activity in self._chat_last_activity.items():
            if now - last_activity > self.cleanup_interval:
                inactive_chats.append(chat_id)

        for chat_id in inactive_chats:
            self.clear_chat(chat_id)

        if inactive_chats:
            logger.info(f"Cleaned up {len(inactive_chats)} inactive chats")

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory usage statistics."""
        total_messages = sum(len(window) for window in self._chat_windows.values())

        return {
            "active_chats": len(self._chat_windows),
            "max_chats": self.max_chats,
            "total_messages": total_messages,
            "window_size": self.window_size,
            "memory_usage_percent": (len(self._chat_windows) / self.max_chats) * 100,
            "cleanup_interval_hours": self.cleanup_interval.total_seconds() / 3600,
        }

    def force_cleanup(self) -> dict[str, int]:
        """Force cleanup of inactive chats and return statistics."""
        initial_count = len(self._chat_windows)
        self._cleanup_inactive_chats()
        cleaned_count = initial_count - len(self._chat_windows)

        return {
            "initial_chats": initial_count,
            "cleaned_chats": cleaned_count,
            "remaining_chats": len(self._chat_windows),
        }


# Global store instance
message_store = SlidingWindowStore()
