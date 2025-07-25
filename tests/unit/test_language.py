"""Unit tests for language detection module."""

from unittest.mock import MagicMock, patch

from oleg_bot.bot.language import LanguageDetector


class TestLanguageDetector:
    """Test cases for LanguageDetector."""

    def test_initialization(self) -> None:
        """Test language detector initialization."""
        detector = LanguageDetector()
        assert detector.fallback_language == "en"

        detector_custom = LanguageDetector(fallback_language="es")
        assert detector_custom.fallback_language == "es"

    def test_detect_language_english(self) -> None:
        """Test detecting English text."""
        detector = LanguageDetector()

        english_text = "Hello world, this is a test message in English."
        result = detector.detect_language(english_text)
        assert result == "en"

    def test_detect_language_spanish(self) -> None:
        """Test detecting Spanish text."""
        detector = LanguageDetector()

        spanish_text = "Hola mundo, este es un mensaje de prueba en español."
        result = detector.detect_language(spanish_text)
        assert result == "es"

    def test_detect_language_russian(self) -> None:
        """Test detecting Russian text."""
        detector = LanguageDetector()

        russian_text = "Привет мир, это тестовое сообщение на русском языке."
        result = detector.detect_language(russian_text)
        assert result == "ru"

    def test_detect_language_empty_text(self) -> None:
        """Test with empty text returns fallback."""
        detector = LanguageDetector()

        assert detector.detect_language("") == "en"
        assert detector.detect_language("   ") == "en"
        assert detector.detect_language("\n\t") == "en"

    def test_detect_language_short_text(self) -> None:
        """Test with very short text returns fallback."""
        detector = LanguageDetector()

        assert detector.detect_language("hi") == "en"
        assert detector.detect_language("ok") == "en"
        assert detector.detect_language("no") == "en"

    def test_detect_language_fallback_on_error(self) -> None:
        """Test fallback when language detection fails."""
        detector = LanguageDetector(fallback_language="fr")

        # Text with only symbols/numbers that might cause detection to fail
        problematic_text = "123 !@# $%^ &*()"
        result = detector.detect_language(problematic_text)
        assert result == "fr"  # Should use fallback

    @patch('oleg_bot.bot.language.detect')
    def test_detect_language_handles_langdetect_error(self, mock_detect: MagicMock) -> None:
        """Test handling of LangDetectException."""
        from langdetect import LangDetectException

        mock_detect.side_effect = LangDetectException("No features in text", "")
        detector = LanguageDetector()

        result = detector.detect_language("some text")
        assert result == "en"

    @patch('oleg_bot.bot.language.detect')
    def test_detect_language_handles_unexpected_error(self, mock_detect: MagicMock) -> None:
        """Test handling of unexpected errors."""
        mock_detect.side_effect = ValueError("Unexpected error")
        detector = LanguageDetector()

        result = detector.detect_language("some text")
        assert result == "en"

    def test_detect_from_messages_single_language(self) -> None:
        """Test detecting language from multiple messages in same language."""
        detector = LanguageDetector()

        english_messages = [
            "Hello, how are you today?",
            "I'm doing well, thank you for asking.",
            "Would you like to have lunch together?",
        ]

        result = detector.detect_from_messages(english_messages)
        assert result == "en"

    def test_detect_from_messages_mixed_languages(self) -> None:
        """Test with mixed languages - should detect dominant one."""
        detector = LanguageDetector()

        mixed_messages = [
            "Hello there",  # English
            "Hola amigo, como estas hoy? Espero que todo este bien contigo.",  # Spanish (longer)
            "Hi again",  # English
        ]

        result = detector.detect_from_messages(mixed_messages)
        # Should detect Spanish as it has more content
        assert result == "es"

    def test_detect_from_messages_empty_list(self) -> None:
        """Test with empty message list."""
        detector = LanguageDetector()

        assert detector.detect_from_messages([]) == "en"

    def test_detect_from_messages_all_empty(self) -> None:
        """Test with list of empty messages."""
        detector = LanguageDetector()

        empty_messages = ["", "   ", "\n", None]
        result = detector.detect_from_messages(empty_messages)
        assert result == "en"

    def test_clean_text_removes_urls(self) -> None:
        """Test that URLs are removed from text."""
        detector = LanguageDetector()

        text_with_url = "Check this out https://example.com/path?param=value it's cool"
        cleaned = detector._clean_text(text_with_url)
        assert "https://example.com" not in cleaned
        assert "Check this out" in cleaned
        assert "it's cool" in cleaned

    def test_clean_text_removes_mentions(self) -> None:
        """Test that mentions are removed from text."""
        detector = LanguageDetector()

        text_with_mentions = "Hey @username and @another_user, what do you think?"
        cleaned = detector._clean_text(text_with_mentions)
        assert "@username" not in cleaned
        assert "@another_user" not in cleaned
        assert "Hey" in cleaned
        assert "what do you think?" in cleaned

    def test_clean_text_removes_hashtags(self) -> None:
        """Test that hashtags are removed from text."""
        detector = LanguageDetector()

        text_with_hashtags = "This is #awesome and #cool stuff"
        cleaned = detector._clean_text(text_with_hashtags)
        assert "#awesome" not in cleaned
        assert "#cool" not in cleaned
        assert "This is" in cleaned
        assert "stuff" in cleaned

    def test_clean_text_normalizes_whitespace(self) -> None:
        """Test that excessive whitespace is normalized."""
        detector = LanguageDetector()

        text_with_spaces = "This   has    too     many      spaces"
        cleaned = detector._clean_text(text_with_spaces)
        assert "This has too many spaces" == cleaned

    def test_clean_text_removes_emoji_only_messages(self) -> None:
        """Test that emoji-only messages are filtered out."""
        detector = LanguageDetector()

        emoji_only = "😀😂🎉"
        cleaned = detector._clean_text(emoji_only)
        assert cleaned == ""

        text_with_emoji = "Hello 😀 world"
        cleaned_mixed = detector._clean_text(text_with_emoji)
        assert "Hello" in cleaned_mixed
        assert "world" in cleaned_mixed

    def test_get_language_name_known_languages(self) -> None:
        """Test getting human-readable names for known languages."""
        detector = LanguageDetector()

        assert detector.get_language_name("en") == "English"
        assert detector.get_language_name("es") == "Spanish"
        assert detector.get_language_name("fr") == "French"
        assert detector.get_language_name("de") == "German"
        assert detector.get_language_name("ru") == "Russian"
        assert detector.get_language_name("zh") == "Chinese"
        assert detector.get_language_name("ja") == "Japanese"

    def test_get_language_name_unknown_language(self) -> None:
        """Test getting name for unknown language code."""
        detector = LanguageDetector()

        assert detector.get_language_name("xyz") == "XYZ"
        assert detector.get_language_name("unknown") == "UNKNOWN"

    def test_detect_language_with_numbers_and_symbols(self) -> None:
        """Test detection with text containing numbers and symbols."""
        detector = LanguageDetector()

        # Text with mix of English words and symbols
        mixed_text = "The price is $29.99 (including 15% tax) for version 2.0!"
        result = detector.detect_language(mixed_text)
        assert result == "en"

    def test_detect_language_preserves_case(self) -> None:
        """Test that detection works with various cases."""
        detector = LanguageDetector()

        uppercase_text = "HELLO WORLD THIS IS AN ENGLISH MESSAGE"
        lowercase_text = "hello world this is an english message"
        mixed_case = "Hello World This Is An English Message"

        assert detector.detect_language(uppercase_text) == "en"
        assert detector.detect_language(lowercase_text) == "en"
        assert detector.detect_language(mixed_case) == "en"
