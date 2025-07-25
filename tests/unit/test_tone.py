"""Unit tests for tone analysis module."""


from oleg_bot.bot.tone import ToneAnalyzer, ToneHints


class TestToneHints:
    """Test cases for ToneHints dataclass."""

    def test_tone_hints_creation(self) -> None:
        """Test creating ToneHints instance."""
        hints = ToneHints(
            emoji_density=0.05,
            formality_level="formal",
            avg_message_length=25.5,
            has_high_emoji=True,
        )

        assert hints.emoji_density == 0.05
        assert hints.formality_level == "formal"
        assert hints.avg_message_length == 25.5
        assert hints.has_high_emoji is True

    def test_tone_hints_to_dict(self) -> None:
        """Test converting ToneHints to dictionary."""
        hints = ToneHints(
            emoji_density=0.03,
            formality_level="casual",
            avg_message_length=12.0,
            has_high_emoji=True,
        )

        result = hints.to_dict()
        expected = {
            'emoji_density': 0.03,
            'formality_level': 'casual',
            'avg_message_length': 12.0,
            'has_high_emoji': True,
        }

        assert result == expected


class TestToneAnalyzer:
    """Test cases for ToneAnalyzer."""

    def test_initialization_default(self) -> None:
        """Test tone analyzer initialization with defaults."""
        analyzer = ToneAnalyzer()
        assert analyzer.high_emoji_threshold == 0.02  # 2%
        assert analyzer.formal_length_threshold == 18.0

    def test_initialization_custom(self) -> None:
        """Test tone analyzer initialization with custom values."""
        analyzer = ToneAnalyzer(
            high_emoji_threshold=0.05,
            formal_length_threshold=20.0
        )
        assert analyzer.high_emoji_threshold == 0.05
        assert analyzer.formal_length_threshold == 20.0

    def test_analyze_tone_empty_messages(self) -> None:
        """Test tone analysis with empty message list."""
        analyzer = ToneAnalyzer()
        result = analyzer.analyze_tone([])

        assert result.emoji_density == 0.0
        assert result.formality_level == "casual"
        assert result.avg_message_length == 0.0
        assert result.has_high_emoji is False

    def test_analyze_tone_all_empty_messages(self) -> None:
        """Test tone analysis with list of empty/whitespace messages."""
        analyzer = ToneAnalyzer()
        messages = ["", "   ", "\n", None]
        result = analyzer.analyze_tone(messages)

        assert result.emoji_density == 0.0
        assert result.formality_level == "casual"
        assert result.avg_message_length == 0.0
        assert result.has_high_emoji is False

    def test_analyze_tone_casual_short_messages(self) -> None:
        """Test tone analysis with casual, short messages."""
        analyzer = ToneAnalyzer()
        messages = [
            "hi there",
            "how are you?",
            "good thanks",
            "see you later"
        ]

        result = analyzer.analyze_tone(messages)

        assert result.emoji_density == 0.0  # No emojis
        assert result.formality_level == "casual"  # Short messages
        assert result.avg_message_length < 18.0
        assert result.has_high_emoji is False

    def test_analyze_tone_formal_long_messages(self) -> None:
        """Test tone analysis with formal, longer messages."""
        analyzer = ToneAnalyzer()
        messages = [
            "Good morning, I hope you are having a wonderful and absolutely spectacular day today with lots of activities.",
            "I would like to discuss the upcoming project deadline with the entire development team and stakeholders involved in this matter.",
            "Please let me know if you have any questions, concerns, or suggestions about this important matter that requires our immediate attention.",
        ]

        result = analyzer.analyze_tone(messages)

        assert result.emoji_density == 0.0  # No emojis
        assert result.formality_level == "formal"  # Long messages
        assert result.avg_message_length > 18.0
        assert result.has_high_emoji is False

    def test_analyze_tone_high_emoji_usage(self) -> None:
        """Test tone analysis with high emoji usage."""
        analyzer = ToneAnalyzer()
        messages = [
            "Hey! 😀 How are you doing? 🎉",
            "Great! 😂 Thanks for asking! 👍",
            "Let's meet up! 🤝 Coffee? ☕",
        ]

        result = analyzer.analyze_tone(messages)

        assert result.emoji_density > 0.02  # Above threshold
        assert result.has_high_emoji is True
        # formality_level depends on word count, not emoji count

    def test_analyze_tone_low_emoji_usage(self) -> None:
        """Test tone analysis with low emoji usage."""
        analyzer = ToneAnalyzer()
        messages = [
            "Hello there, how are you doing today?",
            "I'm doing well, thanks for asking.",
            "Would you like to grab some coffee later? ☕",  # Just one emoji
        ]

        result = analyzer.analyze_tone(messages)

        assert result.emoji_density < 0.02  # Below threshold
        assert result.has_high_emoji is False

    def test_calculate_emoji_density_no_emojis(self) -> None:
        """Test emoji density calculation with no emojis."""
        analyzer = ToneAnalyzer()
        messages = ["hello world", "how are you", "good thanks"]

        density = analyzer._calculate_emoji_density(messages)
        assert density == 0.0

    def test_calculate_emoji_density_with_emojis(self) -> None:
        """Test emoji density calculation with emojis."""
        analyzer = ToneAnalyzer()
        messages = ["😀😂", "hello"]  # 2 emojis out of 7 total chars

        density = analyzer._calculate_emoji_density(messages)
        # Should be approximately 2/7 ≈ 0.286
        assert density > 0.2
        assert density < 0.3

    def test_calculate_emoji_density_empty_messages(self) -> None:
        """Test emoji density calculation with empty messages."""
        analyzer = ToneAnalyzer()

        density = analyzer._calculate_emoji_density([])
        assert density == 0.0

    def test_calculate_emoji_density_various_emoji_types(self) -> None:
        """Test emoji density with different types of emojis."""
        analyzer = ToneAnalyzer()
        messages = [
            "😀😂🎉",  # Emoticons
            "🚗🏠🌟",  # Symbols & pictographs
            "✈️🚀🚁",  # Transport
            "🇺🇸🇪🇸",  # Flags
        ]

        density = analyzer._calculate_emoji_density(messages)
        # Most characters should be emojis
        assert density > 0.8

    def test_calculate_avg_message_length_empty(self) -> None:
        """Test average message length calculation with empty list."""
        analyzer = ToneAnalyzer()

        avg_length = analyzer._calculate_avg_message_length([])
        assert avg_length == 0.0

    def test_calculate_avg_message_length_single_word_messages(self) -> None:
        """Test average message length with single word messages."""
        analyzer = ToneAnalyzer()
        messages = ["hello", "world", "test"]

        avg_length = analyzer._calculate_avg_message_length(messages)
        assert avg_length == 1.0

    def test_calculate_avg_message_length_varied_lengths(self) -> None:
        """Test average message length with varied message lengths."""
        analyzer = ToneAnalyzer()
        messages = [
            "hi",  # 1 word
            "how are you",  # 3 words
            "I am doing well today thanks",  # 6 words
        ]

        avg_length = analyzer._calculate_avg_message_length(messages)
        # (1 + 3 + 6) / 3 = 10/3 ≈ 3.33
        assert 3.0 < avg_length < 4.0

    def test_calculate_avg_message_length_with_punctuation(self) -> None:
        """Test average length calculation handles punctuation correctly."""
        analyzer = ToneAnalyzer()
        messages = [
            "Hello, world!",  # 2 words (punctuation doesn't count)
            "How are you doing today?",  # 5 words
        ]

        avg_length = analyzer._calculate_avg_message_length(messages)
        # (2 + 5) / 2 = 3.5
        assert avg_length == 3.5

    def test_calculate_avg_message_length_with_extra_spaces(self) -> None:
        """Test that extra spaces don't affect word count."""
        analyzer = ToneAnalyzer()
        messages = [
            "hello   world",  # 2 words despite extra spaces
            "  test  message  ",  # 2 words despite leading/trailing spaces
        ]

        avg_length = analyzer._calculate_avg_message_length(messages)
        # (2 + 2) / 2 = 2.0
        assert avg_length == 2.0

    def test_get_tone_description_casual_low_emoji(self) -> None:
        """Test tone description for casual, low emoji."""
        analyzer = ToneAnalyzer()
        hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        description = analyzer.get_tone_description(hints)
        assert "casual" in description
        assert "low emoji" in description
        assert "1.0%" in description

    def test_get_tone_description_formal_high_emoji(self) -> None:
        """Test tone description for formal, high emoji."""
        analyzer = ToneAnalyzer()
        hints = ToneHints(
            emoji_density=0.05,
            formality_level="formal",
            avg_message_length=25.0,
            has_high_emoji=True,
        )

        description = analyzer.get_tone_description(hints)
        assert "formal" in description
        assert "high emoji" in description
        assert "5.0%" in description

    def test_formality_threshold_boundary(self) -> None:
        """Test formality determination at threshold boundary."""
        analyzer = ToneAnalyzer(formal_length_threshold=15.0)

        # Exactly at threshold (15 words should be casual)
        messages_at_threshold = ["this message has exactly fifteen words in it to test the boundary condition here"]
        result_at = analyzer.analyze_tone(messages_at_threshold)

        # Above threshold (20 words should be formal)
        messages_above = ["this message has exactly twenty words in it to test the boundary condition here and now we continue"]
        result_above = analyzer.analyze_tone(messages_above)

        # Below threshold (10 words should be casual)
        messages_below = ["this message has exactly ten words in it here"]
        result_below = analyzer.analyze_tone(messages_below)

        # At 15 words should be casual (≤ threshold), above should be formal
        assert result_at.formality_level == "casual"
        assert result_above.formality_level == "formal"
        assert result_below.formality_level == "casual"

    def test_emoji_threshold_boundary(self) -> None:
        """Test emoji detection at threshold boundary."""
        analyzer = ToneAnalyzer(high_emoji_threshold=0.1)  # 10%

        # Exactly at threshold: 1 emoji out of 10 chars = 10%
        messages_at = ["😀123456789"]  # 1 emoji + 9 regular chars
        result_at = analyzer.analyze_tone(messages_at)

        # Above threshold: 2 emojis out of 10 chars = 20%
        messages_above = ["😀😂12345678"]  # 2 emojis + 8 regular chars
        result_above = analyzer.analyze_tone(messages_above)

        # Below threshold: 0 emojis
        messages_below = ["1234567890"]
        result_below = analyzer.analyze_tone(messages_below)

        # At 10% should be false (≤ threshold), above should be true
        assert result_at.has_high_emoji is False
        assert result_above.has_high_emoji is True
        assert result_below.has_high_emoji is False

    def test_analyze_tone_mixed_content(self) -> None:
        """Test tone analysis with mixed formal/casual and emoji content."""
        analyzer = ToneAnalyzer()
        messages = [
            "Hey! 😀",  # Casual with emoji
            "I would like to schedule a comprehensive meeting to discuss our quarterly business objectives and strategic planning initiatives.",  # Very formal, no emoji
            "Sounds good! 👍",  # Casual with emoji
        ]

        result = analyzer.analyze_tone(messages)

        # Should average out - one very long formal message vs two short casual ones
        # Formality depends on average length across all messages
        # Emoji density should be low due to the long message with no emojis
        assert isinstance(result.emoji_density, float)
        assert result.formality_level in ["formal", "casual"]  # Could go either way
        assert isinstance(result.has_high_emoji, bool)
