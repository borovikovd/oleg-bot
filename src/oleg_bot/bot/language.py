"""Language detection for OlegBot messages."""

import logging

from langdetect import LangDetectException, detect

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detects the dominant language from message text."""

    def __init__(self, fallback_language: str = "en"):
        """Initialize with fallback language."""
        self.fallback_language = fallback_language

    def detect_language(self, text: str) -> str:
        """
        Detect language from text.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code (e.g., 'en', 'es', 'ru')
        """
        if not text or not text.strip():
            return self.fallback_language

        # Clean text for better detection
        cleaned_text = self._clean_text(text)

        if len(cleaned_text) < 3:  # Too short for reliable detection
            return self.fallback_language

        try:
            detected_lang: str = detect(cleaned_text)
            logger.debug(
                f"Detected language '{detected_lang}' from text: {text[:50]}..."
            )
            return detected_lang
        except LangDetectException as e:
            logger.debug(
                f"Language detection failed: {e}. Using fallback: {self.fallback_language}"
            )
            return self.fallback_language
        except Exception as e:
            logger.warning(f"Unexpected error in language detection: {e}")
            return self.fallback_language

    def detect_from_messages(self, messages: list[str]) -> str:
        """
        Detect dominant language from a list of messages.

        Args:
            messages: List of message texts

        Returns:
            Dominant language code
        """
        if not messages:
            return self.fallback_language

        # Combine all messages for analysis
        combined_text = " ".join(msg for msg in messages if msg and msg.strip())
        return self.detect_language(combined_text)

    def _clean_text(self, text: str) -> str:
        """
        Clean text for better language detection.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove common noise that affects detection
        import re

        # Remove URLs
        text = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            text,
        )

        # Remove mentions and hashtags
        text = re.sub(r"@\w+|#\w+", "", text)

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove standalone emojis and symbols (keep text with mixed content)
        # This is a simple approach - more sophisticated emoji handling could be added
        text = re.sub(r"^\s*[^\w\s]+\s*$", "", text)

        return text.strip()

    def get_language_name(self, lang_code: str) -> str:
        """
        Get human-readable language name from code.

        Args:
            lang_code: ISO 639-1 language code

        Returns:
            Human-readable language name
        """
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "tr": "Turkish",
            "pl": "Polish",
            "nl": "Dutch",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "uk": "Ukrainian",
            "cs": "Czech",
            "hu": "Hungarian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
        }
        return language_names.get(lang_code, lang_code.upper())


# Global language detector instance
language_detector = LanguageDetector()
