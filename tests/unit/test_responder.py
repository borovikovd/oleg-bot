"""Unit tests for GPT responder module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oleg_bot.bot.responder import GPTResponder
from oleg_bot.bot.store import StoredMessage
from oleg_bot.bot.tone import ToneHints


class TestGPTResponder:
    """Test cases for GPTResponder."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.responder = GPTResponder(api_key="test_key")

    def test_initialization(self) -> None:
        """Test GPT responder initialization."""
        responder = GPTResponder(
            api_key="test_key",
            model="gpt-4o",
            max_tokens=200,
            temperature=0.7,
        )

        assert responder.model == "gpt-4o"
        assert responder.max_tokens == 200
        assert responder.temperature == 0.7
        assert responder._total_requests == 0
        assert responder._total_tokens_used == 0
        assert responder._total_cost_estimate == 0.0

    def test_initialization_defaults(self) -> None:
        """Test initialization with default values."""
        with patch("oleg_bot.bot.responder.settings") as mock_settings:
            mock_settings.openai_api_key = "default_key"
            responder = GPTResponder()

            assert responder.model == "gpt-4o"
            assert responder.max_tokens == 150
            assert responder.temperature == 0.8

    @pytest.mark.asyncio
    async def test_generate_response_success(self) -> None:
        """Test successful response generation."""
        # Create test data
        message = StoredMessage(
            message_id=123,
            chat_id=-100123456789,
            user_id=987654321,
            text="What do you think about this?",
            timestamp=datetime.now(),
            is_bot_message=False,
        )

        recent_messages = [
            StoredMessage(
                message_id=121,
                chat_id=-100123456789,
                user_id=111,
                text="This is interesting",
                timestamp=datetime.now(),
                is_bot_message=False,
            ),
            StoredMessage(
                message_id=122,
                chat_id=-100123456789,
                user_id=222,
                text="I agree",
                timestamp=datetime.now(),
                is_bot_message=False,
            ),
        ]

        tone_hints = ToneHints(
            emoji_density=0.02,
            formality_level="casual",
            avg_message_length=15.0,
            has_high_emoji=False,
        )

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "That's a great point! 👍"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 25

        with patch.object(
            self.responder.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await self.responder.generate_response(
                message=message,
                recent_messages=recent_messages,
                language="en",
                tone_hints=tone_hints,
            )

            assert result == "That's a great point! 👍"
            assert self.responder._total_requests == 1
            assert self.responder._total_tokens_used == 25

            # Verify API call
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["model"] == "gpt-4o"
            assert call_args[1]["max_tokens"] == 150
            assert call_args[1]["temperature"] == 0.8
            assert len(call_args[1]["messages"]) == 2
            assert call_args[1]["messages"][0]["role"] == "system"
            assert call_args[1]["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_response_api_failure(self) -> None:
        """Test response generation with API failure."""
        message = StoredMessage(
            message_id=123,
            chat_id=-100123456789,
            user_id=987654321,
            text="Hello",
            timestamp=datetime.now(),
            is_bot_message=False,
        )

        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="casual",
            avg_message_length=10.0,
            has_high_emoji=False,
        )

        with patch.object(
            self.responder.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("API Error")

            result = await self.responder.generate_response(
                message=message,
                recent_messages=[],
                language="en",
                tone_hints=tone_hints,
            )

            # Should return fallback response
            assert isinstance(result, str)
            assert len(result) > 0
            # Should be one of the English fallback responses
            fallback_responses = [
                "Interesting point!",
                "I see what you mean.",
                "That's worth thinking about.",
                "Fair enough!",
                "Good observation.",
            ]
            assert any(fallback in result for fallback in fallback_responses)

    def test_build_conversation_context_empty(self) -> None:
        """Test building context with no messages."""
        context = self.responder._build_conversation_context([])
        assert context == "No recent conversation context."

    def test_build_conversation_context_with_messages(self) -> None:
        """Test building context with messages."""
        messages = [
            StoredMessage(
                message_id=1,
                chat_id=-100123456789,
                user_id=111,
                text="Hello everyone",
                timestamp=datetime.now(),
                is_bot_message=False,
            ),
            StoredMessage(
                message_id=2,
                chat_id=-100123456789,
                user_id=999,  # Bot user ID
                text="Hi there!",
                timestamp=datetime.now(),
                is_bot_message=True,
            ),
            StoredMessage(
                message_id=3,
                chat_id=-100123456789,
                user_id=222,
                text="How's everyone doing?",
                timestamp=datetime.now(),
                is_bot_message=False,
            ),
        ]

        context = self.responder._build_conversation_context(messages, max_messages=3)

        assert "User111: Hello everyone" in context
        assert "Bot: Hi there!" in context
        assert "User222: How's everyone doing?" in context

    def test_build_conversation_context_no_text_messages(self) -> None:
        """Test building context with messages that have no text."""
        messages = [
            StoredMessage(
                message_id=1,
                chat_id=-100123456789,
                user_id=111,
                text=None,  # No text
                timestamp=datetime.now(),
                is_bot_message=False,
            ),
        ]

        context = self.responder._build_conversation_context(messages)
        assert context == "No text messages in recent context."

    def test_build_conversation_context_limits_messages(self) -> None:
        """Test that context building respects message limits."""
        messages = [
            StoredMessage(
                message_id=i,
                chat_id=-100123456789,
                user_id=111,
                text=f"Message {i}",
                timestamp=datetime.now(),
                is_bot_message=False,
            )
            for i in range(10)
        ]

        context = self.responder._build_conversation_context(messages, max_messages=3)
        lines = context.strip().split("\n")

        # Should only include last 3 messages
        assert len(lines) == 3
        assert "Message 7" in lines[0]
        assert "Message 8" in lines[1]
        assert "Message 9" in lines[2]

    def test_build_system_prompt_english_casual(self) -> None:
        """Test system prompt building for English casual conversation."""
        tone_hints = ToneHints(
            emoji_density=0.05,
            formality_level="casual",
            avg_message_length=12.0,
            has_high_emoji=True,
        )

        prompt = self.responder._build_system_prompt("en", tone_hints, "group chat")

        assert "Respond in English" in prompt
        assert "casual, friendly language" in prompt
        assert "Feel free to use emojis" in prompt
        assert "group chat" in prompt
        assert "Oleg" in prompt
        assert "witty" in prompt

    def test_build_system_prompt_formal_low_emoji(self) -> None:
        """Test system prompt building for formal conversation with low emoji usage."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="formal",
            avg_message_length=25.0,
            has_high_emoji=False,
        )

        prompt = self.responder._build_system_prompt("es", tone_hints, "private chat")

        assert "Responde en español" in prompt
        assert "formal language" in prompt
        assert "avoid excessive emojis" in prompt
        assert "Use emojis sparingly" in prompt
        assert "private chat" in prompt

    def test_build_system_prompt_unknown_language(self) -> None:
        """Test system prompt building for unknown language."""
        tone_hints = ToneHints(
            emoji_density=0.02,
            formality_level="casual",
            avg_message_length=15.0,
            has_high_emoji=False,
        )

        prompt = self.responder._build_system_prompt("unknown", tone_hints, "group chat")

        assert "Respond in unknown if possible, otherwise English" in prompt

    def test_build_user_prompt(self) -> None:
        """Test user prompt building."""
        message = StoredMessage(
            message_id=123,
            chat_id=-100123456789,
            user_id=987654321,
            text="What's your opinion on this?",
            timestamp=datetime.now(),
            is_bot_message=False,
        )

        conversation_context = "User111: This is interesting\nUser222: I agree"

        prompt = self.responder._build_user_prompt(message, conversation_context, "en")

        assert "Recent conversation:" in prompt
        assert conversation_context in prompt
        assert "What's your opinion on this?" in prompt
        assert "Generate a natural, witty response" in prompt

    def test_extract_response_success(self) -> None:
        """Test successful response extraction."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a great response!"

        result = self.responder._extract_response(mock_response)
        assert result == "This is a great response!"

    def test_extract_response_with_quotes(self) -> None:
        """Test response extraction with surrounding quotes."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '"This response has quotes"'

        result = self.responder._extract_response(mock_response)
        assert result == "This response has quotes"

    def test_extract_response_too_long(self) -> None:
        """Test response extraction with overly long content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "A" * 600  # Too long

        result = self.responder._extract_response(mock_response)
        assert len(result) == 500
        assert result.endswith("...")

    def test_extract_response_no_choices(self) -> None:
        """Test response extraction with no choices."""
        mock_response = MagicMock()
        mock_response.choices = []

        with pytest.raises(ValueError, match="No response choices returned"):
            self.responder._extract_response(mock_response)

    def test_extract_response_empty_content(self) -> None:
        """Test response extraction with empty content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        with pytest.raises(ValueError, match="Empty response content"):
            self.responder._extract_response(mock_response)

    def test_get_fallback_response_english(self) -> None:
        """Test fallback response in English."""
        tone_hints = ToneHints(
            emoji_density=0.02,
            formality_level="casual",
            avg_message_length=12.0,
            has_high_emoji=False,
        )

        response = self.responder._get_fallback_response("en", tone_hints)

        english_responses = [
            "Interesting point! 🤔",
            "I see what you mean.",
            "That's worth thinking about.",
            "Fair enough!",
            "Good observation.",
        ]

        assert response in english_responses

    def test_get_fallback_response_spanish(self) -> None:
        """Test fallback response in Spanish."""
        tone_hints = ToneHints(
            emoji_density=0.02,
            formality_level="casual",
            avg_message_length=12.0,
            has_high_emoji=False,
        )

        response = self.responder._get_fallback_response("es", tone_hints)

        spanish_responses = [
            "¡Punto interesante! 🤔",
            "Entiendo lo que quieres decir.",
            "Eso vale la pena pensarlo.",
            "¡Justo!",
            "Buena observación.",
        ]

        assert response in spanish_responses

    def test_get_fallback_response_formal_no_emoji(self) -> None:
        """Test fallback response for formal tone removes emojis."""
        tone_hints = ToneHints(
            emoji_density=0.01,
            formality_level="formal",
            avg_message_length=25.0,
            has_high_emoji=False,
        )

        response = self.responder._get_fallback_response("en", tone_hints)

        # Should not contain emoji for formal responses
        assert "🤔" not in response

    def test_get_fallback_response_unknown_language(self) -> None:
        """Test fallback response for unknown language defaults to English."""
        tone_hints = ToneHints(
            emoji_density=0.02,
            formality_level="casual",
            avg_message_length=12.0,
            has_high_emoji=False,
        )

        response = self.responder._get_fallback_response("unknown", tone_hints)

        english_responses = [
            "Interesting point! 🤔",
            "I see what you mean.",
            "That's worth thinking about.",
            "Fair enough!",
            "Good observation.",
        ]

        assert response in english_responses

    def test_update_usage_stats(self) -> None:
        """Test usage statistics updating."""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100

        self.responder._update_usage_stats(mock_response)

        assert self.responder._total_requests == 1
        assert self.responder._total_tokens_used == 100
        assert self.responder._total_cost_estimate > 0

        # Test second update
        self.responder._update_usage_stats(mock_response)

        assert self.responder._total_requests == 2
        assert self.responder._total_tokens_used == 200

    def test_update_usage_stats_no_usage(self) -> None:
        """Test usage statistics updating with no usage data."""
        mock_response = MagicMock()
        mock_response.usage = None

        self.responder._update_usage_stats(mock_response)

        assert self.responder._total_requests == 1
        assert self.responder._total_tokens_used == 0
        assert self.responder._total_cost_estimate == 0.0

    def test_get_usage_stats(self) -> None:
        """Test getting usage statistics."""
        # Initially empty
        stats = self.responder.get_usage_stats()

        assert stats["total_requests"] == 0
        assert stats["total_tokens_used"] == 0
        assert stats["estimated_cost_usd"] == 0.0
        assert stats["avg_tokens_per_request"] == 0.0

        # After some usage
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 150

        self.responder._update_usage_stats(mock_response)
        self.responder._update_usage_stats(mock_response)

        stats = self.responder.get_usage_stats()

        assert stats["total_requests"] == 2
        assert stats["total_tokens_used"] == 300
        assert stats["estimated_cost_usd"] > 0
        assert stats["avg_tokens_per_request"] == 150.0

    def test_reset_usage_stats(self) -> None:
        """Test resetting usage statistics."""
        # Add some usage first
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        self.responder._update_usage_stats(mock_response)

        # Verify stats exist
        assert self.responder._total_requests == 1
        assert self.responder._total_tokens_used == 50

        # Reset
        self.responder.reset_usage_stats()

        # Verify reset
        assert self.responder._total_requests == 0
        assert self.responder._total_tokens_used == 0
        assert self.responder._total_cost_estimate == 0.0

        # Check stats API also returns zeros
        stats = self.responder.get_usage_stats()
        assert all(value == 0 or value == 0.0 for value in stats.values())

    def test_language_specific_system_prompts(self) -> None:
        """Test language-specific instructions in system prompts."""
        tone_hints = ToneHints(
            emoji_density=0.02,
            formality_level="casual",
            avg_message_length=12.0,
            has_high_emoji=False,
        )

        test_cases = [
            ("fr", "Répondez en français"),
            ("de", "Antworte auf Deutsch"),
            ("it", "Rispondi in italiano"),
            ("pt", "Responda em português"),
            ("ru", "Отвечай на русском языке"),
            ("ja", "日本語で答えてください"),
            ("zh", "请用中文回答"),
            ("ko", "한국어로 대답해주세요"),
            ("ar", "أجب باللغة العربية"),
            ("hi", "हिंदी में उत्तर दें"),
        ]

        for language_code, expected_instruction in test_cases:
            prompt = self.responder._build_system_prompt(
                language_code, tone_hints, "group chat"
            )
            assert expected_instruction in prompt

    def test_model_parameters_used_correctly(self) -> None:
        """Test that model parameters are used correctly in API calls."""
        custom_responder = GPTResponder(
            api_key="test",
            model="gpt-4o-mini",
            max_tokens=75,
            temperature=0.5,
        )

        message = StoredMessage(
            message_id=123,
            chat_id=-100123456789,
            user_id=987654321,
            text="Test message",
            timestamp=datetime.now(),
            is_bot_message=False,
        )

        tone_hints = ToneHints(
            emoji_density=0.02,
            formality_level="casual",
            avg_message_length=12.0,
            has_high_emoji=False,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 20

        async def test_api_call() -> None:
            with patch.object(
                custom_responder.client.chat.completions, "create", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = mock_response

                await custom_responder.generate_response(
                    message=message,
                    recent_messages=[],
                    language="en",
                    tone_hints=tone_hints,
                )

                # Verify custom parameters were used
                call_args = mock_create.call_args[1]
                assert call_args["model"] == "gpt-4o-mini"
                assert call_args["max_tokens"] == 75
                assert call_args["temperature"] == 0.5
                assert call_args["presence_penalty"] == 0.1
                assert call_args["frequency_penalty"] == 0.1

        import asyncio
        asyncio.run(test_api_call())
