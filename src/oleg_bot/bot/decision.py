"""Decision engine for determining when OlegBot should respond."""

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .language import language_detector
from .store import StoredMessage, message_store
from .tone import tone_analyzer

logger = logging.getLogger(__name__)


class ResponseAction(Enum):
    """Possible actions the bot can take."""

    REPLY = "reply"
    REACT = "react"
    IGNORE = "ignore"


@dataclass
class DecisionContext:
    """Context information for making decisions."""

    chat_id: int
    message_id: int
    user_id: int
    text: str | None
    is_direct_mention: bool
    is_reply_to_bot: bool
    recent_messages: list[StoredMessage]
    topic_heat: float
    time_since_last_bot_message: float
    current_quota_usage: float
    detected_language: str
    tone_hints: Any  # ToneHints from tone module


@dataclass
class DecisionResult:
    """Result of a decision with reasoning."""

    action: ResponseAction
    confidence: float  # 0.0 to 1.0
    reasoning: str
    should_process: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "action": self.action.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "should_process": self.should_process,
        }


class DecisionEngine:
    """Core decision engine for determining bot responses."""

    def __init__(
        self,
        bot_username: str = "oleg_bot",
        reply_target_ratio: float = 0.10,
        gap_min_seconds: int = 20,
        topic_heat_threshold: float = 0.6,
        reaction_probability: float = 0.3,
    ):
        """
        Initialize decision engine.

        Args:
            bot_username: Bot's username for mention detection
            reply_target_ratio: Target percentage of messages to reply to
            gap_min_seconds: Minimum seconds between bot messages
            topic_heat_threshold: Threshold for considering a topic "hot"
            reaction_probability: Probability of reacting vs replying when appropriate
        """
        self.bot_username = bot_username.lower()
        self.reply_target_ratio = reply_target_ratio
        self.gap_min_seconds = gap_min_seconds
        self.topic_heat_threshold = topic_heat_threshold
        self.reaction_probability = reaction_probability

        # Internal state for quota tracking
        self._message_count = 0
        self._reply_count = 0
        self._last_reset_time = time.time()
        self._reset_interval = 3600  # Reset quotas every hour

        logger.info(
            f"Decision engine initialized: target_ratio={reply_target_ratio}, gap={gap_min_seconds}s"
        )

    def should_respond(self, chat_id: int, message: StoredMessage) -> DecisionResult:
        """
        Determine if and how the bot should respond to a message.

        Args:
            chat_id: Chat ID where message was sent
            message: The message to evaluate

        Returns:
            DecisionResult with action and reasoning
        """
        # Build decision context
        context = self._build_context(chat_id, message)

        # Apply decision rules in priority order
        decision = self._apply_decision_rules(context)

        # Update internal state
        self._update_state(decision)

        logger.debug(f"Decision for message {message.message_id}: {decision.to_dict()}")
        return decision

    def _build_context(self, chat_id: int, message: StoredMessage) -> DecisionContext:
        """Build decision context from message and chat state."""
        # Get recent messages for analysis
        recent_messages = message_store.get_messages(chat_id, limit=20)

        # Check for direct mentions
        is_direct_mention = self._is_direct_mention(message.text or "")

        # Check if this is a reply to bot
        is_reply_to_bot = self._is_reply_to_bot(message, recent_messages)

        # Calculate topic heat
        topic_heat = self._calculate_topic_heat(recent_messages)

        # Calculate time since last bot message
        time_since_last = self._time_since_last_bot_message(chat_id)

        # Get current quota usage
        quota_usage = self._get_current_quota_usage()

        # Analyze language and tone
        message_texts = [msg.text for msg in recent_messages if msg.text]
        detected_language = language_detector.detect_from_messages(message_texts)
        tone_hints = tone_analyzer.analyze_tone(message_texts)

        return DecisionContext(
            chat_id=chat_id,
            message_id=message.message_id,
            user_id=message.user_id,
            text=message.text,
            is_direct_mention=is_direct_mention,
            is_reply_to_bot=is_reply_to_bot,
            recent_messages=recent_messages,
            topic_heat=topic_heat,
            time_since_last_bot_message=time_since_last,
            current_quota_usage=quota_usage,
            detected_language=detected_language,
            tone_hints=tone_hints,
        )

    def _apply_decision_rules(self, context: DecisionContext) -> DecisionResult:
        """Apply decision rules to determine response action."""

        # Rule 1: Always respond to direct mentions (if rate limit allows)
        if context.is_direct_mention:
            if context.time_since_last_bot_message >= self.gap_min_seconds:
                return DecisionResult(
                    action=ResponseAction.REPLY,
                    confidence=0.95,
                    reasoning="Direct mention detected",
                    should_process=True,
                )
            else:
                return DecisionResult(
                    action=ResponseAction.REACT,
                    confidence=0.8,
                    reasoning="Direct mention but rate limited, reacting instead",
                    should_process=True,
                )

        # Rule 2: Always respond to replies to bot (if rate limit allows)
        if context.is_reply_to_bot:
            if context.time_since_last_bot_message >= self.gap_min_seconds:
                return DecisionResult(
                    action=ResponseAction.REPLY,
                    confidence=0.9,
                    reasoning="Reply to bot message",
                    should_process=True,
                )
            else:
                return DecisionResult(
                    action=ResponseAction.REACT,
                    confidence=0.7,
                    reasoning="Reply to bot but rate limited, reacting instead",
                    should_process=True,
                )

        # Rule 3: Respect rate limiting
        if context.time_since_last_bot_message < self.gap_min_seconds:
            return DecisionResult(
                action=ResponseAction.IGNORE,
                confidence=0.9,
                reasoning=f"Rate limited: {context.time_since_last_bot_message:.1f}s < {self.gap_min_seconds}s",
                should_process=False,
            )

        # Rule 4: Check quota limits
        if context.current_quota_usage >= self.reply_target_ratio:
            return DecisionResult(
                action=ResponseAction.IGNORE,
                confidence=0.8,
                reasoning=f"Quota exceeded: {context.current_quota_usage:.1%} >= {self.reply_target_ratio:.1%}",
                should_process=False,
            )

        # Rule 5: Hot topic participation
        if context.topic_heat >= self.topic_heat_threshold:
            # Decide between reply and reaction
            import random

            if random.random() < self.reaction_probability:
                return DecisionResult(
                    action=ResponseAction.REACT,
                    confidence=0.6,
                    reasoning=f"Hot topic participation (react): heat={context.topic_heat:.2f}",
                    should_process=True,
                )
            else:
                return DecisionResult(
                    action=ResponseAction.REPLY,
                    confidence=0.6,
                    reasoning=f"Hot topic participation (reply): heat={context.topic_heat:.2f}",
                    should_process=True,
                )

        # Rule 6: Random participation based on remaining quota
        remaining_quota = self.reply_target_ratio - context.current_quota_usage
        if remaining_quota > 0:
            # Scale probability based on remaining quota
            participation_probability = min(remaining_quota * 2, 0.1)  # Max 10% chance

            import random

            if random.random() < participation_probability:
                return DecisionResult(
                    action=ResponseAction.REPLY,
                    confidence=0.4,
                    reasoning=f"Random participation: prob={participation_probability:.1%}",
                    should_process=True,
                )

        # Default: ignore
        return DecisionResult(
            action=ResponseAction.IGNORE,
            confidence=0.5,
            reasoning="No compelling reason to respond",
            should_process=False,
        )

    def _is_direct_mention(self, text: str) -> bool:
        """Check if message contains a direct mention of the bot."""
        if not text:
            return False

        text_lower = text.lower()

        # Check for @username mentions
        username_pattern = rf"@{re.escape(self.bot_username)}\b"
        if re.search(username_pattern, text_lower):
            return True

        # Check for common bot invocation patterns
        bot_patterns = [
            rf"\b{re.escape(self.bot_username)}\b",
            r"\bbot\b",
            r"\boleg\b",
        ]

        for pattern in bot_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _is_reply_to_bot(
        self, message: StoredMessage, recent_messages: list[StoredMessage]
    ) -> bool:
        """Check if message is a reply to a bot message."""
        if not message.reply_to_message_id:
            return False

        # Look for the replied-to message in recent messages
        for msg in recent_messages:
            if msg.message_id == message.reply_to_message_id:
                return msg.is_bot_message

        return False

    def _calculate_topic_heat(self, recent_messages: list[StoredMessage]) -> float:
        """
        Calculate topic heat based on recent message activity.

        Higher values indicate more active discussion.
        """
        if len(recent_messages) < 2:
            return 0.0

        now = datetime.now()
        active_window = timedelta(minutes=5)  # Look at last 5 minutes

        # Count messages in active window
        active_messages = [
            msg for msg in recent_messages if (now - msg.timestamp) <= active_window
        ]

        if not active_messages:
            return 0.0

        # Calculate base activity score
        message_rate = len(active_messages) / 5.0  # messages per minute

        # Boost for multiple participants
        unique_users = len({msg.user_id for msg in active_messages})
        user_diversity_boost = min(unique_users / 3.0, 1.0)  # Up to 3 users = max boost

        # Boost for replies (indicates engagement)
        reply_count = sum(1 for msg in active_messages if msg.reply_to_message_id)
        reply_boost = min(reply_count / len(active_messages), 0.5)  # Max 50% boost

        # Calculate final heat score
        heat = message_rate * 0.4 + user_diversity_boost * 0.4 + reply_boost * 0.2

        # Normalize to 0-1 range
        normalized_heat = min(heat / 2.0, 1.0)

        logger.debug(
            f"Topic heat: {normalized_heat:.2f} (rate={message_rate:.1f}, users={unique_users}, replies={reply_count})"
        )
        return normalized_heat

    def _time_since_last_bot_message(self, chat_id: int) -> float:
        """Get seconds since last bot message in chat."""
        if message_store.has_recent_bot_message(
            chat_id, seconds=3600
        ):  # Check last hour
            # Get recent messages to find the exact timestamp
            recent_messages = message_store.get_messages(chat_id, limit=50)
            now = datetime.now()

            for message in reversed(recent_messages):
                if message.is_bot_message:
                    time_diff = (now - message.timestamp).total_seconds()
                    return time_diff

        # No recent bot message found
        return float("inf")

    def _get_current_quota_usage(self) -> float:
        """Get current quota usage ratio."""
        current_time = time.time()

        # Reset quota tracking if interval has passed
        if current_time - self._last_reset_time >= self._reset_interval:
            self._message_count = 0
            self._reply_count = 0
            self._last_reset_time = current_time

        if self._message_count == 0:
            return 0.0

        return self._reply_count / self._message_count

    def _update_state(self, decision: DecisionResult) -> None:
        """Update internal state based on decision."""
        self._message_count += 1

        if decision.action == ResponseAction.REPLY:
            self._reply_count += 1

    def update_settings(self, **kwargs: Any) -> None:
        """Update decision engine settings."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                setattr(self, key, value)
                logger.info(f"Updated {key}: {old_value} -> {value}")
            else:
                logger.warning(f"Unknown setting: {key}")

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return {
            "message_count": self._message_count,
            "reply_count": self._reply_count,
            "current_quota_usage": self._get_current_quota_usage(),
            "target_ratio": self.reply_target_ratio,
            "gap_min_seconds": self.gap_min_seconds,
            "topic_heat_threshold": self.topic_heat_threshold,
            "last_reset_time": self._last_reset_time,
        }


# Global decision engine instance
decision_engine = DecisionEngine()
