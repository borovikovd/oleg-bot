"""GPT-4o responder for generating contextual bot responses."""

import logging
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ..config import settings
from .store import StoredMessage
from .tone import ToneHints

logger = logging.getLogger(__name__)


class GPTResponder:
    """Handles response generation using OpenAI GPT-4o."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        max_tokens: int = 150,
        temperature: float = 0.8,
    ):
        """
        Initialize GPT responder.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model to use for generation
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.0-2.0)
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Response tracking for cost management
        self._total_requests = 0
        self._total_tokens_used = 0
        self._total_cost_estimate = 0.0

        logger.info(
            f"GPT responder initialized: model={model}, max_tokens={max_tokens}, temperature={temperature}"
        )

    async def generate_response(
        self,
        message: StoredMessage,
        recent_messages: list[StoredMessage],
        language: str,
        tone_hints: ToneHints,
        chat_context: str = "group chat",
    ) -> str:
        """
        Generate a contextual response using GPT-4o.

        Args:
            message: The message to respond to
            recent_messages: Recent conversation context
            language: Detected language for response
            tone_hints: Tone analysis results
            chat_context: Type of chat (group, private, etc.)

        Returns:
            Generated response text

        Raises:
            Exception: If response generation fails
        """
        try:
            # Build conversation context
            conversation_context = self._build_conversation_context(
                recent_messages, max_messages=5
            )

            # Generate dynamic prompt
            system_prompt = self._build_system_prompt(
                language, tone_hints, chat_context
            )
            user_prompt = self._build_user_prompt(
                message, conversation_context, language
            )

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0.1,  # Slight penalty for repetition
                frequency_penalty=0.1,  # Slight penalty for overused words
            )

            # Extract response
            response_text = self._extract_response(response)

            # Update usage statistics
            self._update_usage_stats(response)

            logger.debug(
                f"Generated response: {len(response_text)} chars, "
                f"tokens_used={response.usage.total_tokens if response.usage else 0}"
            )

            return response_text

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            # Return fallback response
            return self._get_fallback_response(language, tone_hints)

    def _build_conversation_context(
        self, recent_messages: list[StoredMessage], max_messages: int = 5
    ) -> str:
        """Build conversation context from recent messages."""
        if not recent_messages:
            return "No recent conversation context."

        context_lines = []
        for msg in recent_messages[-max_messages:]:
            if msg.text:
                sender = "Bot" if msg.is_bot_message else f"User{msg.user_id}"
                context_lines.append(f"{sender}: {msg.text}")

        return "\n".join(context_lines) if context_lines else "No text messages in recent context."

    def _build_system_prompt(
        self, language: str, tone_hints: ToneHints, chat_context: str
    ) -> str:
        """Build dynamic system prompt with language and tone hints."""
        # Language-specific instructions
        language_instructions = {
            "en": "Respond in English",
            "es": "Responde en español",
            "fr": "Répondez en français",
            "de": "Antworte auf Deutsch",
            "it": "Rispondi in italiano",
            "pt": "Responda em português",
            "ru": "Отвечай на русском языке",
            "ja": "日本語で答えてください",
            "zh": "请用中文回答",
            "ko": "한국어로 대답해주세요",
            "ar": "أجب باللغة العربية",
            "hi": "हिंदी में उत्तर दें",
        }

        language_instruction = language_instructions.get(
            language, f"Respond in {language} if possible, otherwise English"
        )

        # Tone adaptation
        formality_instruction = (
            "Use formal language and avoid excessive emojis"
            if tone_hints.formality_level == "formal"
            else "Use casual, friendly language"
        )

        emoji_instruction = (
            "Feel free to use emojis to match the conversation style"
            if tone_hints.has_high_emoji
            else "Use emojis sparingly"
        )

        # Base personality
        base_prompt = f"""You are Oleg, a witty and engaging chatbot participating in a {chat_context}.

Key traits:
- Witty and sometimes sarcastic, but not mean-spirited
- Conversational and natural, like a friend in the group
- Brief responses (under 100 words, preferably 1-2 sentences)
- Contextually aware of the ongoing conversation
- Adapt to the group's communication style

Language: {language_instruction}
Tone: {formality_instruction}
Emojis: {emoji_instruction}

Remember: Be helpful when asked direct questions, but primarily focus on natural conversation flow. Don't be overly formal or robotic."""

        return base_prompt

    def _build_user_prompt(
        self, message: StoredMessage, conversation_context: str, language: str
    ) -> str:
        """Build user prompt with message and context."""
        prompt = f"""Recent conversation:
{conversation_context}

Latest message to respond to: "{message.text}"

Generate a natural, witty response that fits the conversation flow. Keep it brief and engaging."""

        return prompt

    def _extract_response(self, response: ChatCompletion) -> str:
        """Extract and clean response text from OpenAI response."""
        if not response.choices:
            raise ValueError("No response choices returned from OpenAI")

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response content from OpenAI")

        # Clean up the response
        cleaned_response = content.strip()

        # Remove quotes if the entire response is wrapped in them
        if (
            len(cleaned_response) >= 2
            and cleaned_response.startswith('"')
            and cleaned_response.endswith('"')
        ):
            cleaned_response = cleaned_response[1:-1].strip()

        # Ensure response is not too long (fallback limit)
        if len(cleaned_response) > 500:  # Character limit as final safety
            cleaned_response = cleaned_response[:497] + "..."

        return cleaned_response

    def _get_fallback_response(self, language: str, tone_hints: ToneHints) -> str:
        """Get fallback response when GPT fails."""
        fallback_responses = {
            "en": [
                "Interesting point! 🤔",
                "I see what you mean.",
                "That's worth thinking about.",
                "Fair enough!",
                "Good observation.",
            ],
            "es": [
                "¡Punto interesante! 🤔",
                "Entiendo lo que quieres decir.",
                "Eso vale la pena pensarlo.",
                "¡Justo!",
                "Buena observación.",
            ],
            "ru": [
                "Интересная мысль! 🤔",
                "Понимаю, что ты имеешь в виду.",
                "Над этим стоит подумать.",
                "Справедливо!",
                "Хорошее наблюдение.",
            ],
            "fr": [
                "Point intéressant ! 🤔",
                "Je vois ce que tu veux dire.",
                "Ça vaut la peine d'y réfléchir.",
                "C'est juste !",
                "Bonne observation.",
            ],
        }

        responses = fallback_responses.get(language, fallback_responses["en"])

        # Remove emoji from formal responses
        if tone_hints.formality_level == "formal":
            responses = [resp.replace(" 🤔", "") for resp in responses]

        import random
        return random.choice(responses)

    def _update_usage_stats(self, response: ChatCompletion) -> None:
        """Update usage statistics for cost tracking."""
        self._total_requests += 1

        if response.usage:
            tokens_used = response.usage.total_tokens
            self._total_tokens_used += tokens_used

            # Rough cost estimate for GPT-4o (as of 2024)
            # Input: $5/1M tokens, Output: $15/1M tokens
            # Using average for simplicity: $10/1M tokens
            estimated_cost = (tokens_used / 1_000_000) * 10.0
            self._total_cost_estimate += estimated_cost

    def get_usage_stats(self) -> dict[str, Any]:
        """Get current usage statistics."""
        return {
            "total_requests": self._total_requests,
            "total_tokens_used": self._total_tokens_used,
            "estimated_cost_usd": round(self._total_cost_estimate, 4),
            "avg_tokens_per_request": (
                round(self._total_tokens_used / self._total_requests, 1)
                if self._total_requests > 0
                else 0.0
            ),
        }

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self._total_requests = 0
        self._total_tokens_used = 0
        self._total_cost_estimate = 0.0
        logger.info("Usage statistics reset")


# Global responder instance
gpt_responder = GPTResponder()
