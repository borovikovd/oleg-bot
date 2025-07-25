"""Unit tests for the sliding window message store."""

from datetime import datetime, timedelta

from oleg_bot.bot.store import SlidingWindowStore, StoredMessage


class TestSlidingWindowStore:
    """Test cases for SlidingWindowStore."""

    def test_initialization(self) -> None:
        """Test store initialization."""
        store = SlidingWindowStore(window_size=10)
        assert store.window_size == 10
        assert store.get_chat_count() == 0

    def test_add_message(self) -> None:
        """Test adding a message to the store."""
        store = SlidingWindowStore(window_size=5)
        message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=200,
            text="Hello world",
            timestamp=datetime.now(),
        )

        store.add_message(message)
        messages = store.get_messages(100)

        assert len(messages) == 1
        assert messages[0] == message
        assert store.get_chat_count() == 1

    def test_window_size_limit(self) -> None:
        """Test that window size is respected."""
        store = SlidingWindowStore(window_size=3)
        chat_id = 100

        # Add 5 messages
        for i in range(5):
            message = StoredMessage(
                message_id=i,
                chat_id=chat_id,
                user_id=200,
                text=f"Message {i}",
                timestamp=datetime.now(),
            )
            store.add_message(message)

        messages = store.get_messages(chat_id)

        # Should only have the last 3 messages
        assert len(messages) == 3
        assert messages[0].message_id == 2
        assert messages[1].message_id == 3
        assert messages[2].message_id == 4

    def test_multiple_chats(self) -> None:
        """Test handling multiple chats."""
        store = SlidingWindowStore(window_size=5)

        # Add messages to different chats
        message1 = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=200,
            text="Chat 1 message",
            timestamp=datetime.now(),
        )
        message2 = StoredMessage(
            message_id=2,
            chat_id=101,
            user_id=201,
            text="Chat 2 message",
            timestamp=datetime.now(),
        )

        store.add_message(message1)
        store.add_message(message2)

        assert len(store.get_messages(100)) == 1
        assert len(store.get_messages(101)) == 1
        assert store.get_chat_count() == 2

    def test_get_recent_text(self) -> None:
        """Test getting recent text for analysis."""
        store = SlidingWindowStore(window_size=5)
        chat_id = 100

        messages = [
            StoredMessage(1, chat_id, 200, "Hello", datetime.now()),
            StoredMessage(2, chat_id, 201, "How are you?", datetime.now()),
            StoredMessage(3, chat_id, 200, None, datetime.now()),  # No text
            StoredMessage(4, chat_id, 202, "Good!", datetime.now()),
        ]

        for msg in messages:
            store.add_message(msg)

        recent_text = store.get_recent_text(chat_id, limit=4)
        assert recent_text == "Hello How are you? Good!"

    def test_has_recent_bot_message(self) -> None:
        """Test checking for recent bot messages."""
        store = SlidingWindowStore(window_size=5)
        chat_id = 100
        now = datetime.now()

        # Add old bot message
        old_bot_message = StoredMessage(
            message_id=1,
            chat_id=chat_id,
            user_id=999,  # Bot user ID
            text="Bot response",
            timestamp=now - timedelta(seconds=30),
            is_bot_message=True,
        )

        # Add recent user message
        user_message = StoredMessage(
            message_id=2,
            chat_id=chat_id,
            user_id=200,
            text="User message",
            timestamp=now - timedelta(seconds=5),
        )

        store.add_message(old_bot_message)
        store.add_message(user_message)

        # Should not find recent bot message (>20s ago)
        assert not store.has_recent_bot_message(chat_id, seconds=20)

        # Should find recent bot message with longer threshold
        assert store.has_recent_bot_message(chat_id, seconds=40)

        # Add recent bot message
        recent_bot_message = StoredMessage(
            message_id=3,
            chat_id=chat_id,
            user_id=999,
            text="Recent bot response",
            timestamp=now - timedelta(seconds=10),
            is_bot_message=True,
        )
        store.add_message(recent_bot_message)

        # Should find recent bot message
        assert store.has_recent_bot_message(chat_id, seconds=20)

    def test_clear_chat(self) -> None:
        """Test clearing messages for a specific chat."""
        store = SlidingWindowStore(window_size=5)

        # Add messages to two chats
        for chat_id in [100, 101]:
            message = StoredMessage(
                message_id=1,
                chat_id=chat_id,
                user_id=200,
                text="Test message",
                timestamp=datetime.now(),
            )
            store.add_message(message)

        assert store.get_chat_count() == 2

        # Clear one chat
        store.clear_chat(100)

        assert store.get_chat_count() == 1
        assert len(store.get_messages(100)) == 0
        assert len(store.get_messages(101)) == 1

    def test_empty_chat_messages(self) -> None:
        """Test getting messages from non-existent chat."""
        store = SlidingWindowStore(window_size=5)

        messages = store.get_messages(999)  # Non-existent chat
        assert messages == []

        recent_text = store.get_recent_text(999)
        assert recent_text == ""

        assert not store.has_recent_bot_message(999)
