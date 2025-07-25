"""Reaction handler for OlegBot emoji responses."""

import logging
import random
from typing import Any

from .tone import ToneHints

logger = logging.getLogger(__name__)


class ReactionHandler:
    """Handles emoji reactions based on context and tone."""

    def __init__(self) -> None:
        """Initialize reaction handler with emoji sets."""
        # Base reaction sets by category
        self.positive_reactions = ["👍", "❤️", "😊", "🎉", "✨", "🔥", "💯"]
        self.negative_reactions = ["👎", "😔", "🤔", "😬", "😅"]
        self.neutral_reactions = ["👀", "🤷", "🙃", "😐", "🤖"]
        self.funny_reactions = ["😂", "🤣", "😄", "😆", "🤭", "😹"]
        self.thinking_reactions = ["🤔", "💭", "🧠", "💡", "🔍"]
        self.support_reactions = ["❤️", "🤗", "💪", "👏", "🙌", "✊"]

        # Language-specific reactions
        self.language_reactions = {
            "ru": ["🇷🇺", "💔", "🥃", "🐻"],
            "es": ["🇪🇸", "💃", "🌶️", "⚽"],
            "fr": ["🇫🇷", "🥖", "🍷", "🎨"],
            "de": ["🇩🇪", "🍺", "⚽", "🥨"],
            "it": ["🇮🇹", "🍕", "🍝", "🤌"],
            "ja": ["🇯🇵", "🍜", "🎌", "🌸"],
            "zh": ["🇨🇳", "🥢", "🐉", "🎋"],
        }

        # Formal vs casual reaction preferences
        self.formal_reactions = ["👍", "👌", "✅", "💼", "📊", "📈"]
        self.casual_reactions = ["😎", "🤘", "🙌", "🔥", "💯", "😂"]

    def choose_reaction(
        self,
        message_text: str | None,
        tone_hints: ToneHints,
        language: str = "en",
        context: str = "neutral",
    ) -> str:
        """
        Choose an appropriate emoji reaction.

        Args:
            message_text: The message text to react to
            tone_hints: Tone analysis results
            language: Detected language
            context: Context hint ("positive", "negative", "funny", etc.)

        Returns:
            Emoji string for reaction
        """
        # Determine base reaction pool
        reaction_pool = self._get_base_reactions(message_text, context)

        # Adjust for tone and formality
        reaction_pool = self._adjust_for_tone(reaction_pool, tone_hints)

        # Add language-specific reactions if available
        if language in self.language_reactions:
            # 20% chance to use language-specific reaction
            if random.random() < 0.2:
                reaction_pool.extend(self.language_reactions[language])

        # Choose random reaction from pool
        chosen_reaction = random.choice(reaction_pool)

        logger.debug(
            f"Chose reaction '{chosen_reaction}' for context='{context}', "
            f"language='{language}', formality='{tone_hints.formality_level}'"
        )

        return chosen_reaction

    def _get_base_reactions(self, message_text: str | None, context: str) -> list[str]:
        """Get base reaction pool based on message content and context."""
        if not message_text:
            return self.neutral_reactions.copy()

        text_lower = message_text.lower()

        # Detect sentiment from message content
        positive_keywords = [
            "good",
            "great",
            "awesome",
            "amazing",
            "perfect",
            "love",
            "happy",
            "thanks",
            "thank",
            "excellent",
            "wonderful",
            "fantastic",
            "brilliant",
        ]

        negative_keywords = [
            "bad",
            "terrible",
            "awful",
            "hate",
            "sad",
            "angry",
            "frustrated",
            "disappointed",
            "wrong",
            "problem",
            "issue",
            "error",
            "fail",
        ]

        funny_keywords = [
            "lol",
            "haha",
            "funny",
            "joke",
            "laugh",
            "humor",
            "hilarious",
            "comedy",
            "meme",
            "rofl",
            "lmao",
            "😂",
            "🤣",
        ]

        thinking_keywords = [
            "think",
            "wonder",
            "question",
            "why",
            "how",
            "what",
            "hmm",
            "curious",
            "consider",
            "analyze",
            "understand",
            "explain",
        ]

        # Override context based on message content
        if any(keyword in text_lower for keyword in funny_keywords):
            context = "funny"
        elif any(keyword in text_lower for keyword in positive_keywords):
            context = "positive"
        elif any(keyword in text_lower for keyword in negative_keywords):
            context = "negative"
        elif any(keyword in text_lower for keyword in thinking_keywords):
            context = "thinking"

        # Return appropriate reaction pool
        if context == "positive":
            return self.positive_reactions.copy()
        elif context == "negative":
            return self.negative_reactions.copy()
        elif context == "funny":
            return self.funny_reactions.copy()
        elif context == "thinking":
            return self.thinking_reactions.copy()
        elif context == "support":
            return self.support_reactions.copy()
        else:
            return self.neutral_reactions.copy()

    def _adjust_for_tone(
        self, reactions: list[str], tone_hints: ToneHints
    ) -> list[str]:
        """Adjust reaction pool based on tone analysis."""
        # Adjust for formality
        if tone_hints.formality_level == "formal":
            # Add formal reactions and remove very casual ones
            reactions.extend(self.formal_reactions)
            # Remove overly casual reactions
            casual_to_remove = ["🤘", "🔥", "💯", "😂", "🤣"]
            reactions = [r for r in reactions if r not in casual_to_remove]
        else:
            # Add casual reactions for informal tone
            reactions.extend(self.casual_reactions)

        # Adjust for emoji usage in conversation
        if tone_hints.has_high_emoji:
            # Use more expressive reactions in emoji-heavy conversations
            expressive_reactions = ["🎉", "✨", "🔥", "💯", "🙌", "🤘", "😎"]
            reactions.extend(expressive_reactions)
        else:
            # Use more restrained reactions in low-emoji conversations
            restrained_reactions = ["👍", "👌", "✅", "💼"]
            reactions.extend(restrained_reactions)

        # Remove duplicates while preserving order
        seen = set()
        unique_reactions = []
        for reaction in reactions:
            if reaction not in seen:
                seen.add(reaction)
                unique_reactions.append(reaction)

        return unique_reactions

    def get_reaction_for_mention(self, tone_hints: ToneHints) -> str:
        """Get a reaction specifically for when bot is mentioned but rate-limited."""
        # Use acknowledgment reactions for mentions
        mention_reactions = ["👋", "👀", "🤖", "✋", "👍", "🙋"]

        if tone_hints.formality_level == "formal":
            return random.choice(["👍", "✅", "👌"])
        else:
            return random.choice(mention_reactions)

    def get_reaction_for_reply(self, tone_hints: ToneHints) -> str:
        """Get a reaction specifically for replies to bot when rate-limited."""
        # Use engagement reactions for replies
        reply_reactions = ["👀", "🤔", "💭", "👍", "🙂"]

        if tone_hints.has_high_emoji:
            reply_reactions.extend(["😊", "😉", "🤗"])

        return random.choice(reply_reactions)

    def get_stats(self) -> dict[str, Any]:
        """Get reaction handler statistics."""
        return {
            "total_reaction_types": len(
                set(
                    self.positive_reactions
                    + self.negative_reactions
                    + self.neutral_reactions
                    + self.funny_reactions
                    + self.thinking_reactions
                    + self.support_reactions
                )
            ),
            "supported_languages": len(self.language_reactions),
            "language_codes": list(self.language_reactions.keys()),
        }


# Global reaction handler instance
reaction_handler = ReactionHandler()
