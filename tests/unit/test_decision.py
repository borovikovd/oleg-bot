"""Unit tests for decision engine module."""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from oleg_bot.bot.decision import (
    DecisionEngine,
    DecisionResult,
    ResponseAction,
)
from oleg_bot.bot.store import StoredMessage


class TestDecisionEngine:
    """Test cases for DecisionEngine."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = DecisionEngine(
            bot_username="test_bot",
            reply_target_ratio=0.1,
            gap_min_seconds=20,
            topic_heat_threshold=0.6,
        )
        # Reset internal state
        self.engine._message_count = 0
        self.engine._reply_count = 0
        self.engine._last_reset_time = time.time()

    def test_initialization(self) -> None:
        """Test decision engine initialization."""
        engine = DecisionEngine(
            bot_username="my_bot",
            reply_target_ratio=0.15,
            gap_min_seconds=30,
        )

        assert engine.bot_username == "my_bot"
        assert engine.reply_target_ratio == 0.15
        assert engine.gap_min_seconds == 30
        assert engine.topic_heat_threshold == 0.6  # default
        assert engine._message_count == 0
        assert engine._reply_count == 0

    def test_is_direct_mention_username(self) -> None:
        """Test direct mention detection with username."""
        # Username mentions
        assert self.engine._is_direct_mention("@test_bot hello")
        assert self.engine._is_direct_mention("Hello @test_bot!")
        assert self.engine._is_direct_mention("@TEST_BOT how are you?")  # case insensitive

        # Not mentions
        assert not self.engine._is_direct_mention("@other_bot hello")
        assert not self.engine._is_direct_mention("test_bot_other hello")
        assert not self.engine._is_direct_mention("hello world")

    def test_is_direct_mention_patterns(self) -> None:
        """Test direct mention detection with common patterns."""
        # Bot keyword
        assert self.engine._is_direct_mention("bot help me")
        assert self.engine._is_direct_mention("Hey bot!")

        # Bot name
        assert self.engine._is_direct_mention("oleg what do you think?")
        assert self.engine._is_direct_mention("OLEG are you there?")

        # Username without @
        assert self.engine._is_direct_mention("test_bot please help")
        assert self.engine._is_direct_mention("Hey test_bot!")

        # Not mentions
        assert not self.engine._is_direct_mention("testing robots")
        assert not self.engine._is_direct_mention("telegram")

    def test_is_reply_to_bot_true(self) -> None:
        """Test reply to bot detection when true."""
        bot_message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=999,
            text="Hello",
            timestamp=datetime.now(),
            is_bot_message=True,
        )

        reply_message = StoredMessage(
            message_id=2,
            chat_id=100,
            user_id=200,
            text="Hi back",
            timestamp=datetime.now(),
            reply_to_message_id=1,
        )

        recent_messages = [bot_message]

        result = self.engine._is_reply_to_bot(reply_message, recent_messages)
        assert result is True

    def test_is_reply_to_bot_false(self) -> None:
        """Test reply to bot detection when false."""
        user_message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=200,
            text="Hello",
            timestamp=datetime.now(),
            is_bot_message=False,
        )

        reply_message = StoredMessage(
            message_id=2,
            chat_id=100,
            user_id=201,
            text="Hi back",
            timestamp=datetime.now(),
            reply_to_message_id=1,
        )

        recent_messages = [user_message]

        result = self.engine._is_reply_to_bot(reply_message, recent_messages)
        assert result is False

    def test_is_reply_to_bot_no_reply(self) -> None:
        """Test reply to bot detection with no reply."""
        message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=200,
            text="Hello",
            timestamp=datetime.now(),
            reply_to_message_id=None,
        )

        result = self.engine._is_reply_to_bot(message, [])
        assert result is False

    def test_calculate_topic_heat_no_messages(self) -> None:
        """Test topic heat calculation with no messages."""
        heat = self.engine._calculate_topic_heat([])
        assert heat == 0.0

    def test_calculate_topic_heat_low_activity(self) -> None:
        """Test topic heat calculation with low activity."""
        now = datetime.now()
        messages = [
            StoredMessage(1, 100, 200, "hello", now - timedelta(minutes=10), False),
        ]

        heat = self.engine._calculate_topic_heat(messages)
        assert heat == 0.0  # Outside active window

    def test_calculate_topic_heat_high_activity(self) -> None:
        """Test topic heat calculation with high activity."""
        now = datetime.now()
        messages = [
            StoredMessage(1, 100, 200, "hello", now - timedelta(minutes=1), False),
            StoredMessage(2, 100, 201, "hi there", now - timedelta(minutes=2), False),
            StoredMessage(3, 100, 202, "how's everyone?", now - timedelta(minutes=3), False),
            StoredMessage(4, 100, 200, "good thanks", now - timedelta(minutes=1), False, 3),
        ]

        heat = self.engine._calculate_topic_heat(messages)
        assert heat > 0.0  # Should be positive with recent activity

    def test_time_since_last_bot_message_none(self) -> None:
        """Test time calculation when no bot messages."""
        with patch('oleg_bot.bot.decision.message_store') as mock_store:
            mock_store.has_recent_bot_message.return_value = False

            time_since = self.engine._time_since_last_bot_message(100)
            assert time_since == float('inf')

    def test_time_since_last_bot_message_recent(self) -> None:
        """Test time calculation with recent bot message."""
        now = datetime.now()
        bot_message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=999,
            text="Hello",
            timestamp=now - timedelta(seconds=30),
            is_bot_message=True,
        )

        with patch('oleg_bot.bot.decision.message_store') as mock_store:
            mock_store.has_recent_bot_message.return_value = True
            mock_store.get_messages.return_value = [bot_message]

            time_since = self.engine._time_since_last_bot_message(100)
            assert 25 <= time_since <= 35  # Approximately 30 seconds

    def test_get_current_quota_usage_empty(self) -> None:
        """Test quota usage calculation when empty."""
        usage = self.engine._get_current_quota_usage()
        assert usage == 0.0

    def test_get_current_quota_usage_with_data(self) -> None:
        """Test quota usage calculation with data."""
        self.engine._message_count = 10
        self.engine._reply_count = 3

        usage = self.engine._get_current_quota_usage()
        assert usage == 0.3  # 3/10 = 30%

    def test_get_current_quota_usage_reset(self) -> None:
        """Test quota usage reset after interval."""
        self.engine._message_count = 10
        self.engine._reply_count = 5
        self.engine._last_reset_time = time.time() - 3700  # Over an hour ago

        usage = self.engine._get_current_quota_usage()
        assert usage == 0.0  # Should be reset
        assert self.engine._message_count == 0
        assert self.engine._reply_count == 0

    @patch('oleg_bot.bot.decision.message_store')
    @patch('oleg_bot.bot.decision.language_detector')
    @patch('oleg_bot.bot.decision.tone_analyzer')
    def test_decision_direct_mention_reply(self, mock_tone, mock_lang, mock_store) -> None:
        """Test decision for direct mention - should reply."""
        # Setup mocks
        mock_store.get_messages.return_value = []
        mock_lang.detect_from_messages.return_value = "en"
        mock_tone.analyze_tone.return_value = MagicMock(formality_level="casual")

        message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=200,
            text="@test_bot hello",
            timestamp=datetime.now(),
        )

        result = self.engine.should_respond(100, message)

        assert result.action == ResponseAction.REPLY
        assert result.confidence >= 0.9
        assert "mention" in result.reasoning.lower()
        assert result.should_process is True

    @patch('oleg_bot.bot.decision.message_store')
    @patch('oleg_bot.bot.decision.language_detector')
    @patch('oleg_bot.bot.decision.tone_analyzer')
    def test_decision_direct_mention_rate_limited(self, mock_tone, mock_lang, mock_store) -> None:
        """Test decision for direct mention when rate limited - should react."""
        # Setup recent bot message
        now = datetime.now()
        bot_message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=999,
            text="Previous response",
            timestamp=now - timedelta(seconds=10),  # Recent
            is_bot_message=True,
        )

        mock_store.get_messages.return_value = [bot_message]
        mock_store.has_recent_bot_message.return_value = True
        mock_lang.detect_from_messages.return_value = "en"
        mock_tone.analyze_tone.return_value = MagicMock(formality_level="casual")

        message = StoredMessage(
            message_id=2,
            chat_id=100,
            user_id=200,
            text="@test_bot hello",
            timestamp=now,
        )

        result = self.engine.should_respond(100, message)

        assert result.action == ResponseAction.REACT
        assert "rate limited" in result.reasoning.lower()
        assert result.should_process is True

    @patch('oleg_bot.bot.decision.message_store')
    @patch('oleg_bot.bot.decision.language_detector')
    @patch('oleg_bot.bot.decision.tone_analyzer')
    def test_decision_quota_exceeded(self, mock_tone, mock_lang, mock_store) -> None:
        """Test decision when quota is exceeded - should ignore."""
        mock_store.get_messages.return_value = []
        mock_store.has_recent_bot_message.return_value = False
        mock_lang.detect_from_messages.return_value = "en"
        mock_tone.analyze_tone.return_value = MagicMock(formality_level="casual")

        # Set quota exceeded
        self.engine._message_count = 10
        self.engine._reply_count = 2  # 20% > 10% target

        message = StoredMessage(
            message_id=1,
            chat_id=100,
            user_id=200,
            text="regular message",
            timestamp=datetime.now(),
        )

        result = self.engine.should_respond(100, message)

        assert result.action == ResponseAction.IGNORE
        assert "quota" in result.reasoning.lower()
        assert result.should_process is False

    @patch('oleg_bot.bot.decision.message_store')
    @patch('oleg_bot.bot.decision.language_detector')
    @patch('oleg_bot.bot.decision.tone_analyzer')
    def test_decision_hot_topic(self, mock_tone, mock_lang, mock_store) -> None:
        """Test decision for hot topic - should participate."""
        # Create high activity messages
        now = datetime.now()
        messages = [
            StoredMessage(i, 100, 200 + i, f"Message {i}", now - timedelta(minutes=i), False)
            for i in range(5)
        ]

        mock_store.get_messages.return_value = messages
        mock_store.has_recent_bot_message.return_value = False
        mock_lang.detect_from_messages.return_value = "en"
        mock_tone.analyze_tone.return_value = MagicMock(formality_level="casual")

        # Mock high topic heat
        with patch.object(self.engine, '_calculate_topic_heat', return_value=0.8):
            message = StoredMessage(
                message_id=6,
                chat_id=100,
                user_id=200,
                text="interesting discussion",
                timestamp=now,
            )

            result = self.engine.should_respond(100, message)

            assert result.action in [ResponseAction.REPLY, ResponseAction.REACT]
            assert "hot topic" in result.reasoning.lower()
            assert result.should_process is True

    def test_update_settings(self) -> None:
        """Test updating engine settings."""
        old_ratio = self.engine.reply_target_ratio
        old_gap = self.engine.gap_min_seconds

        self.engine.update_settings(
            reply_target_ratio=0.2,
            gap_min_seconds=30,
            unknown_setting=42  # Should be ignored
        )

        assert self.engine.reply_target_ratio == 0.2
        assert self.engine.gap_min_seconds == 30
        assert old_ratio != self.engine.reply_target_ratio
        assert old_gap != self.engine.gap_min_seconds

    def test_get_stats(self) -> None:
        """Test getting engine statistics."""
        self.engine._message_count = 15
        self.engine._reply_count = 3

        stats = self.engine.get_stats()

        assert stats["message_count"] == 15
        assert stats["reply_count"] == 3
        assert stats["current_quota_usage"] == 0.2  # 3/15
        assert stats["target_ratio"] == 0.1
        assert stats["gap_min_seconds"] == 20
        assert "last_reset_time" in stats

    def test_update_state_reply(self) -> None:
        """Test state update for reply decision."""
        initial_messages = self.engine._message_count
        initial_replies = self.engine._reply_count

        decision = DecisionResult(
            action=ResponseAction.REPLY,
            confidence=0.8,
            reasoning="Test",
            should_process=True,
        )

        self.engine._update_state(decision)

        assert self.engine._message_count == initial_messages + 1
        assert self.engine._reply_count == initial_replies + 1

    def test_update_state_ignore(self) -> None:
        """Test state update for ignore decision."""
        initial_messages = self.engine._message_count
        initial_replies = self.engine._reply_count

        decision = DecisionResult(
            action=ResponseAction.IGNORE,
            confidence=0.5,
            reasoning="Test",
            should_process=False,
        )

        self.engine._update_state(decision)

        assert self.engine._message_count == initial_messages + 1
        assert self.engine._reply_count == initial_replies  # No change


class TestDecisionResult:
    """Test cases for DecisionResult."""

    def test_decision_result_creation(self) -> None:
        """Test creating DecisionResult."""
        result = DecisionResult(
            action=ResponseAction.REPLY,
            confidence=0.85,
            reasoning="Direct mention",
            should_process=True,
        )

        assert result.action == ResponseAction.REPLY
        assert result.confidence == 0.85
        assert result.reasoning == "Direct mention"
        assert result.should_process is True

    def test_decision_result_to_dict(self) -> None:
        """Test converting DecisionResult to dictionary."""
        result = DecisionResult(
            action=ResponseAction.REACT,
            confidence=0.6,
            reasoning="Rate limited",
            should_process=True,
        )

        result_dict = result.to_dict()
        expected = {
            "action": "react",
            "confidence": 0.6,
            "reasoning": "Rate limited",
            "should_process": True,
        }

        assert result_dict == expected


class TestResponseAction:
    """Test cases for ResponseAction enum."""

    def test_response_action_values(self) -> None:
        """Test ResponseAction enum values."""
        assert ResponseAction.REPLY.value == "reply"
        assert ResponseAction.REACT.value == "react"
        assert ResponseAction.IGNORE.value == "ignore"

    def test_response_action_enum_members(self) -> None:
        """Test ResponseAction enum has expected members."""
        actions = list(ResponseAction)
        assert len(actions) == 3
        assert ResponseAction.REPLY in actions
        assert ResponseAction.REACT in actions
        assert ResponseAction.IGNORE in actions
