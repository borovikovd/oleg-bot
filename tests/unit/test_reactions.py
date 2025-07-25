"""Unit tests for reaction handler module."""

from unittest.mock import patch

from oleg_bot.bot.reactions import ReactionHandler
from oleg_bot.bot.tone import ToneHints


class TestReactionHandler:
    """Test cases for ReactionHandler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.handler = ReactionHandler()

    def test_initialization(self) -> None:
        """Test reaction handler initialization."""
        assert len(self.handler.positive_reactions) > 0
        assert len(self.handler.negative_reactions) > 0
        assert len(self.handler.neutral_reactions) > 0
        assert len(self.handler.funny_reactions) > 0
        assert len(self.handler.thinking_reactions) > 0
        assert len(self.handler.support_reactions) > 0
        assert len(self.handler.language_reactions) > 0
        assert len(self.handler.formal_reactions) > 0
        assert len(self.handler.casual_reactions) > 0

    def test_choose_reaction_positive_context(self) -> None:
        """Test choosing reaction for positive context."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        reaction = self.handler.choose_reaction(
            message_text="Great job everyone!",
            tone_hints=tone_hints,
            context="positive"
        )

        assert isinstance(reaction, str)
        assert len(reaction) > 0
        # Should be from positive reactions or related sets
        all_possible = (
            self.handler.positive_reactions +
            self.handler.casual_reactions +
            self.handler.formal_reactions
        )
        assert reaction in all_possible

    def test_choose_reaction_negative_context(self) -> None:
        """Test choosing reaction for negative context."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        reaction = self.handler.choose_reaction(
            message_text="This is terrible",
            tone_hints=tone_hints,
            context="negative"
        )

        assert isinstance(reaction, str)
        assert len(reaction) > 0

    def test_choose_reaction_funny_context(self) -> None:
        """Test choosing reaction for funny context."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        reaction = self.handler.choose_reaction(
            message_text="haha that's hilarious!",
            tone_hints=tone_hints,
            context="funny"
        )

        assert isinstance(reaction, str)
        assert len(reaction) > 0

    def test_choose_reaction_auto_detect_positive(self) -> None:
        """Test automatic context detection for positive messages."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "👍"  # Predictable reaction

            self.handler.choose_reaction(
                message_text="This is amazing and wonderful!",
                tone_hints=tone_hints,
                context="neutral"  # Will be overridden by auto-detection
            )

            # Should have been called with positive reactions
            call_args = mock_choice.call_args[0][0]
            assert "👍" in call_args or any(pos in call_args for pos in self.handler.positive_reactions)

    def test_choose_reaction_auto_detect_funny(self) -> None:
        """Test automatic context detection for funny messages."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "😂"

            self.handler.choose_reaction(
                message_text="lol that's so funny haha!",
                tone_hints=tone_hints,
                context="neutral"
            )

            call_args = mock_choice.call_args[0][0]
            assert any(funny in call_args for funny in self.handler.funny_reactions)

    def test_choose_reaction_formal_tone(self) -> None:
        """Test reaction choice for formal tone."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="formal",
            avg_message_length=25.0,
            has_high_emoji=False,
        )

        reaction = self.handler.choose_reaction(
            message_text="Thank you for your professional assistance.",
            tone_hints=tone_hints,
        )

        assert isinstance(reaction, str)
        assert len(reaction) > 0

    def test_choose_reaction_high_emoji_tone(self) -> None:
        """Test reaction choice for high emoji conversations."""
        tone_hints = ToneHints(
            emoji_density=0.05,  # High emoji
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=True,
        )

        reaction = self.handler.choose_reaction(
            message_text="Hey there! 😊🎉",
            tone_hints=tone_hints,
        )

        assert isinstance(reaction, str)
        assert len(reaction) > 0

    def test_choose_reaction_language_specific(self) -> None:
        """Test language-specific reaction selection."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        # Test with supported language
        with patch('random.random', return_value=0.1):  # Force language reaction
            with patch('random.choice') as mock_choice:
                mock_choice.return_value = "🇷🇺"

                self.handler.choose_reaction(
                    message_text="Hello",
                    tone_hints=tone_hints,
                    language="ru"
                )

                # Should include Russian reactions
                call_args = mock_choice.call_args[0][0]
                assert any(ru_emoji in call_args for ru_emoji in self.handler.language_reactions["ru"])

    def test_choose_reaction_empty_message(self) -> None:
        """Test reaction choice for empty message."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        reaction = self.handler.choose_reaction(
            message_text=None,
            tone_hints=tone_hints,
        )

        assert isinstance(reaction, str)
        assert len(reaction) > 0
        # Should use neutral reactions for empty messages

    def test_get_reaction_for_mention_formal(self) -> None:
        """Test mention reaction for formal tone."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="formal",
            avg_message_length=25.0,
            has_high_emoji=False,
        )

        reaction = self.handler.get_reaction_for_mention(tone_hints)

        assert reaction in ["👍", "✅", "👌"]

    def test_get_reaction_for_mention_casual(self) -> None:
        """Test mention reaction for casual tone."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        reaction = self.handler.get_reaction_for_mention(tone_hints)

        mention_reactions = ["👋", "👀", "🤖", "✋", "👍", "🙋"]
        assert reaction in mention_reactions

    def test_get_reaction_for_reply_low_emoji(self) -> None:
        """Test reply reaction for low emoji conversation."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        reaction = self.handler.get_reaction_for_reply(tone_hints)

        expected_reactions = ["👀", "🤔", "💭", "👍", "🙂"]
        assert reaction in expected_reactions

    def test_get_reaction_for_reply_high_emoji(self) -> None:
        """Test reply reaction for high emoji conversation."""
        tone_hints = ToneHints(
            emoji_density=0.05,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=True,
        )

        reaction = self.handler.get_reaction_for_reply(tone_hints)

        all_possible = ["👀", "🤔", "💭", "👍", "🙂", "😊", "😉", "🤗"]
        assert reaction in all_possible

    def test_get_base_reactions_positive_keywords(self) -> None:
        """Test base reaction detection for positive keywords."""
        reactions = self.handler._get_base_reactions("This is great and awesome!", "neutral")

        # Should detect positive and return positive reactions
        assert any(pos in reactions for pos in self.handler.positive_reactions)

    def test_get_base_reactions_negative_keywords(self) -> None:
        """Test base reaction detection for negative keywords."""
        reactions = self.handler._get_base_reactions("This is terrible and awful", "neutral")

        # Should detect negative and return negative reactions
        assert any(neg in reactions for neg in self.handler.negative_reactions)

    def test_get_base_reactions_funny_keywords(self) -> None:
        """Test base reaction detection for funny keywords."""
        reactions = self.handler._get_base_reactions("lol that's hilarious and funny", "neutral")

        # Should detect funny and return funny reactions
        assert any(funny in reactions for funny in self.handler.funny_reactions)

    def test_get_base_reactions_thinking_keywords(self) -> None:
        """Test base reaction detection for thinking keywords."""
        reactions = self.handler._get_base_reactions("I wonder why this happens", "neutral")

        # Should detect thinking and return thinking reactions
        assert any(think in reactions for think in self.handler.thinking_reactions)

    def test_adjust_for_tone_formal(self) -> None:
        """Test tone adjustment for formal conversation."""
        base_reactions = ["😂", "🤘", "🔥"]  # Casual reactions
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="formal",
            avg_message_length=25.0,
            has_high_emoji=False,
        )

        adjusted = self.handler._adjust_for_tone(base_reactions, tone_hints)

        # Should add formal reactions and remove very casual ones
        assert any(formal in adjusted for formal in self.handler.formal_reactions)
        # Should remove overly casual reactions
        assert "🤘" not in adjusted or "🔥" not in adjusted

    def test_adjust_for_tone_casual(self) -> None:
        """Test tone adjustment for casual conversation."""
        base_reactions = ["👍", "👌"]
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        adjusted = self.handler._adjust_for_tone(base_reactions, tone_hints)

        # Should add casual reactions
        assert any(casual in adjusted for casual in self.handler.casual_reactions)

    def test_adjust_for_tone_high_emoji(self) -> None:
        """Test tone adjustment for high emoji conversation."""
        base_reactions = ["👍"]
        tone_hints = ToneHints(
            emoji_density=0.05,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=True,
        )

        adjusted = self.handler._adjust_for_tone(base_reactions, tone_hints)

        # Should add expressive reactions
        expressive = ["🎉", "✨", "🔥", "💯", "🙌", "🤘", "😎"]
        assert any(expr in adjusted for expr in expressive)

    def test_adjust_for_tone_removes_duplicates(self) -> None:
        """Test that tone adjustment removes duplicates."""
        base_reactions = ["👍", "👍", "😊", "😊"]
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        adjusted = self.handler._adjust_for_tone(base_reactions, tone_hints)

        # Should have unique reactions only
        assert len(adjusted) == len(set(adjusted))
        assert adjusted.count("👍") == 1
        assert adjusted.count("😊") == 1

    def test_get_stats(self) -> None:
        """Test getting reaction handler statistics."""
        stats = self.handler.get_stats()

        assert "total_reaction_types" in stats
        assert "supported_languages" in stats
        assert "language_codes" in stats

        assert stats["total_reaction_types"] > 0
        assert stats["supported_languages"] == len(self.handler.language_reactions)
        assert set(stats["language_codes"]) == set(self.handler.language_reactions.keys())

    def test_reaction_sets_not_empty(self) -> None:
        """Test that all reaction sets contain emojis."""
        reaction_sets = [
            self.handler.positive_reactions,
            self.handler.negative_reactions,
            self.handler.neutral_reactions,
            self.handler.funny_reactions,
            self.handler.thinking_reactions,
            self.handler.support_reactions,
            self.handler.formal_reactions,
            self.handler.casual_reactions,
        ]

        for reaction_set in reaction_sets:
            assert len(reaction_set) > 0
            for reaction in reaction_set:
                assert isinstance(reaction, str)
                assert len(reaction) > 0

    def test_language_reactions_valid(self) -> None:
        """Test that language reactions are valid."""
        for lang_code, reactions in self.handler.language_reactions.items():
            assert isinstance(lang_code, str)
            assert len(lang_code) == 2  # ISO 639-1 code
            assert len(reactions) > 0
            for reaction in reactions:
                assert isinstance(reaction, str)
                assert len(reaction) > 0
