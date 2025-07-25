"""Tone analysis for OlegBot message context."""

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToneHints:
    """Tone analysis results for message context."""

    emoji_density: float  # Ratio of emoji characters to total characters
    formality_level: str  # 'formal', 'casual'
    avg_message_length: float  # Average words per message
    has_high_emoji: bool  # True if emoji ratio > 2%

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "emoji_density": self.emoji_density,
            "formality_level": self.formality_level,
            "avg_message_length": self.avg_message_length,
            "has_high_emoji": self.has_high_emoji,
        }


class ToneAnalyzer:
    """Analyzes tone characteristics from message context."""

    def __init__(
        self,
        high_emoji_threshold: float = 0.02,  # 2%
        formal_length_threshold: float = 18.0,  # words
    ):
        """
        Initialize tone analyzer with thresholds.

        Args:
            high_emoji_threshold: Emoji ratio above which is considered "high emoji"
            formal_length_threshold: Average words above which is considered "formal"
        """
        self.high_emoji_threshold = high_emoji_threshold
        self.formal_length_threshold = formal_length_threshold

    def analyze_tone(self, messages: list[str]) -> ToneHints:
        """
        Analyze tone from a list of messages.

        Args:
            messages: List of message texts to analyze

        Returns:
            ToneHints with analyzed characteristics
        """
        if not messages:
            return ToneHints(
                emoji_density=0.0,
                formality_level="casual",
                avg_message_length=0.0,
                has_high_emoji=False,
            )

        # Filter out empty messages
        valid_messages = [msg for msg in messages if msg and msg.strip()]
        if not valid_messages:
            return ToneHints(
                emoji_density=0.0,
                formality_level="casual",
                avg_message_length=0.0,
                has_high_emoji=False,
            )

        # Calculate emoji density
        emoji_density = self._calculate_emoji_density(valid_messages)

        # Calculate average message length
        avg_length = self._calculate_avg_message_length(valid_messages)

        # Determine formality level
        formality_level = (
            "formal" if avg_length > self.formal_length_threshold else "casual"
        )

        # Determine if high emoji usage
        has_high_emoji = emoji_density > self.high_emoji_threshold

        tone_hints = ToneHints(
            emoji_density=emoji_density,
            formality_level=formality_level,
            avg_message_length=avg_length,
            has_high_emoji=has_high_emoji,
        )

        logger.debug(f"Tone analysis: {tone_hints.to_dict()}")
        return tone_hints

    def _calculate_emoji_density(self, messages: list[str]) -> float:
        """
        Calculate the ratio of emoji characters to total characters.

        Args:
            messages: List of message texts

        Returns:
            Emoji density ratio (0.0 to 1.0)
        """
        total_chars = 0
        emoji_chars = 0

        # Unicode ranges for common emoji
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U00002702-\U000027b0"  # dingbats
            "\U000024c2-\U0001f251"  # enclosed characters
            "]+",
            flags=re.UNICODE,
        )

        for message in messages:
            total_chars += len(message)
            emoji_matches = emoji_pattern.findall(message)
            emoji_chars += sum(len(match) for match in emoji_matches)

        if total_chars == 0:
            return 0.0

        density = emoji_chars / total_chars
        logger.debug(f"Emoji density: {emoji_chars}/{total_chars} = {density:.4f}")
        return density

    def _calculate_avg_message_length(self, messages: list[str]) -> float:
        """
        Calculate average words per message.

        Args:
            messages: List of message texts

        Returns:
            Average words per message
        """
        if not messages:
            return 0.0

        total_words = 0
        for message in messages:
            # Simple word count - split by whitespace and filter empty strings
            words = [word for word in message.split() if word.strip()]
            total_words += len(words)

        avg_length = total_words / len(messages)
        logger.debug(
            f"Average message length: {total_words}/{len(messages)} = {avg_length:.2f} words"
        )
        return avg_length

    def get_tone_description(self, tone_hints: ToneHints) -> str:
        """
        Get human-readable description of tone characteristics.

        Args:
            tone_hints: Analyzed tone hints

        Returns:
            Descriptive string
        """
        emoji_desc = "high emoji" if tone_hints.has_high_emoji else "low emoji"
        return f"{tone_hints.formality_level}, {emoji_desc} ({tone_hints.emoji_density:.1%})"


# Global tone analyzer instance
tone_analyzer = ToneAnalyzer()
