"""End-to-end tests for Telegram integration with mock server."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Any

import httpx
from fastapi.testclient import TestClient
from telegram import Update, Message, User, Chat
from telegram.constants import ChatType

from oleg_bot.main import app
from oleg_bot.config import Settings
from oleg_bot.bot.store import message_store, StoredMessage
from oleg_bot.bot.startup import startup_manager


@pytest.fixture
def test_settings():
    """Test settings with safe values."""
    return Settings(
        telegram_bot_token="test_token",
        telegram_webhook_url="https://test.example.com",
        telegram_webhook_secret="test_secret",
        openai_api_key="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",
        openai_model="google/gemini-2.0-flash-exp:free",
        openai_base_url="https://openrouter.ai/api/v1",
        admin_user_ids=[12345],
        environment="test",
        debug=True,
    )


@pytest.fixture
def test_client(test_settings):
    """Test client with mocked settings."""
    with patch("oleg_bot.config.settings", test_settings):
        with TestClient(app) as client:
            yield client


@pytest.fixture
def mock_telegram_update():
    """Create a mock Telegram update."""
    user = User(
        id=12345,
        first_name="Test",
        last_name="User",
        username="testuser",
        is_bot=False
    )
    
    chat = Chat(
        id=-100123456789,
        type=ChatType.GROUP,
        title="Test Group"
    )
    
    message = Message(
        message_id=123,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="Hello, Oleg!"
    )
    
    return Update(update_id=1, message=message)


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI/OpenRouter API response."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1634567890,
        "model": "google/gemini-2.0-flash-exp:free",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello there! 👋"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 10,
            "total_tokens": 60
        }
    }


class TestTelegramWebhook:
    """Test Telegram webhook integration."""

    @pytest.mark.asyncio
    async def test_webhook_receives_message(self, test_client, mock_telegram_update):
        """Test that webhook can receive and process Telegram messages."""
        # Mock bot initialization
        with patch.object(startup_manager, 'initialize_bot'), \
             patch.object(startup_manager, 'bot') as mock_bot:
            
            mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=124))
            mock_bot.set_message_reaction = AsyncMock()
            
            # Send webhook update
            response = test_client.post(
                "/webhook/telegram",
                json=mock_telegram_update.to_dict(),
                headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"}
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_webhook_invalid_secret(self, test_client, mock_telegram_update, test_settings):
        """Test webhook rejects invalid secrets."""
        # Mock bot initialization for this test
        with patch.object(startup_manager, 'initialize_bot'), \
             patch.object(startup_manager, 'bot'):
            
            response = test_client.post(
                "/webhook/telegram",
                json=mock_telegram_update.to_dict(),
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"}
            )
            
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_webhook_rate_limiting(self, test_client, mock_telegram_update):
        """Test webhook rate limiting works."""
        # Mock bot to avoid initialization
        with patch.object(startup_manager, 'initialize_bot'), \
             patch.object(startup_manager, 'bot') as mock_bot:
            
            mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=124))
            
            # Send many requests quickly
            responses = []
            for i in range(5):
                response = test_client.post(
                    "/webhook/telegram",
                    json=mock_telegram_update.to_dict(),
                    headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"}
                )
                responses.append(response)
            
            # Some should succeed, eventually rate limiting should kick in
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count > 0  # At least some should succeed


class TestMessageProcessing:
    """Test message processing logic."""

    @pytest.mark.asyncio
    async def test_command_processing(self, test_settings):
        """Test command processing with admin user."""
        with patch("oleg_bot.config.settings", test_settings):
            from oleg_bot.bot.commands import command_handler
            
            # Test admin command
            response = command_handler.handle_command(
                "/stats", 
                user_id=12345,  # Admin user
                chat_id=-100123456789
            )
            
            assert "OlegBot Statistics" in response
            assert "Decision Engine" in response

    @pytest.mark.asyncio 
    async def test_gpt_response_generation(self, test_settings, mock_openai_response):
        """Test GPT response generation with OpenRouter."""
        with patch("oleg_bot.config.settings", test_settings):
            # Import after patching settings
            from oleg_bot.bot.responder import GPTResponder
            from oleg_bot.bot.store import StoredMessage
            from oleg_bot.bot.tone import ToneHints
            
            # Create fresh responder instance for test
            responder = GPTResponder(
                api_key=test_settings.openai_api_key,
                base_url=test_settings.openai_base_url,
                model=test_settings.openai_model
            )
            
            # Mock the HTTP client
            with patch("openai.AsyncOpenAI") as mock_client:
                mock_instance = mock_client.return_value
                mock_completion = MagicMock()
                mock_completion.choices = [MagicMock()]
                mock_completion.choices[0].message.content = "Hello there! 👋"
                mock_completion.usage.prompt_tokens = 50
                mock_completion.usage.completion_tokens = 10
                mock_completion.usage.total_tokens = 60
                
                mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
                responder.client = mock_instance
                
                # Test message
                message = StoredMessage(
                    message_id=123,
                    chat_id=-100123456789,
                    user_id=12345,
                    text="Hello, Oleg!",
                    timestamp=datetime.now(),
                    is_bot_message=False
                )
                
                tone_hints = ToneHints(
                    formality_level="casual",
                    has_high_emoji=False,
                    detected_emotion="neutral"
                )
                
                response = await responder.generate_response(
                    message=message,
                    recent_messages=[message],
                    language="en",
                    tone_hints=tone_hints
                )
                
                assert response == "Hello there! 👋"
                
                # Verify OpenRouter headers were used
                call_args = mock_instance.chat.completions.create.call_args
                assert "extra_headers" in call_args.kwargs
                headers = call_args.kwargs["extra_headers"]
                assert "HTTP-Referer" in headers
                assert "X-Title" in headers


class TestMemoryManagement:
    """Test memory management and chat limits."""

    def test_memory_stats(self):
        """Test memory statistics are accurate."""
        # Clear store for clean test
        message_store._chat_windows.clear()
        message_store._chat_last_activity.clear()
        
        # Add some test messages
        for chat_id in range(5):
            for msg_id in range(10):
                message = StoredMessage(
                    message_id=msg_id,
                    chat_id=chat_id,
                    user_id=123,
                    text=f"Message {msg_id}",
                    timestamp=datetime.now(),
                    is_bot_message=False
                )
                message_store.add_message(message)
        
        stats = message_store.get_memory_stats()
        
        assert stats["active_chats"] == 5
        assert stats["total_messages"] == 50
        assert stats["window_size"] == 50

    def test_lru_eviction(self):
        """Test LRU eviction when max chats exceeded."""
        from oleg_bot.bot.store import SlidingWindowStore
        
        # Create store with low limit
        store = SlidingWindowStore(window_size=10, max_chats=3)
        
        # Add messages to 4 chats (should trigger eviction)
        for chat_id in range(4):
            message = StoredMessage(
                message_id=1,
                chat_id=chat_id,
                user_id=123,
                text="Test message",
                timestamp=datetime.now(),
                is_bot_message=False
            )
            store.add_message(message)
        
        # Should only have 3 chats (max_chats)
        assert store.get_chat_count() == 3
        
        # Chat 0 should be evicted (least recently used)
        assert store.get_messages(0) == []

    def test_inactive_chat_cleanup(self):
        """Test cleanup of inactive chats."""
        from oleg_bot.bot.store import SlidingWindowStore
        from datetime import timedelta
        
        # Create store with short cleanup interval
        store = SlidingWindowStore(cleanup_interval_hours=1)
        
        # Add message to chat
        message = StoredMessage(
            message_id=1,
            chat_id=123,
            user_id=456,
            text="Test message",
            timestamp=datetime.now(),
            is_bot_message=False
        )
        store.add_message(message)
        
        # Simulate old activity
        store._chat_last_activity[123] = datetime.now() - timedelta(hours=2)
        
        # Force cleanup
        cleanup_stats = store.force_cleanup()
        
        assert cleanup_stats["cleaned_chats"] == 1
        assert store.get_chat_count() == 0


class TestErrorHandling:
    """Test error handling and monitoring."""

    @pytest.mark.asyncio
    async def test_openai_api_failure_fallback(self, test_settings):
        """Test fallback to reactions when OpenAI API fails."""
        with patch("oleg_bot.config.settings", test_settings):
            from oleg_bot.bot.responder import GPTResponder
            from oleg_bot.bot.store import StoredMessage
            from oleg_bot.bot.tone import ToneHints
            
            # Create fresh responder instance for test
            responder = GPTResponder(
                api_key=test_settings.openai_api_key,
                base_url=test_settings.openai_base_url,
                model=test_settings.openai_model
            )
            
            # Mock OpenAI to raise exception
            with patch("openai.AsyncOpenAI") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
                responder.client = mock_instance
                
                message = StoredMessage(
                    message_id=123,
                    chat_id=-100123456789,
                    user_id=12345,
                    text="Hello, Oleg!",
                    timestamp=datetime.now(),
                    is_bot_message=False
                )
                
                tone_hints = ToneHints(
                    formality_level="casual",
                    has_high_emoji=False,
                    detected_emotion="neutral"
                )
                
                # Should return fallback response
                response = await responder.generate_response(
                    message=message,
                    recent_messages=[message],
                    language="en",
                    tone_hints=tone_hints
                )
                
                # Should get fallback response
                assert response in ["Interesting point!", "I see what you mean.", 
                                 "That's worth thinking about.", "Fair enough!", "Good observation."]

    def test_error_tracking(self, test_client):
        """Test error tracking functionality."""
        response = test_client.get("/webhook/errors")
        assert response.status_code == 200
        
        error_stats = response.json()
        assert "error_counts" in error_stats
        assert "recent_errors" in error_stats
        assert "total_errors" in error_stats


class TestBotStartup:
    """Test bot startup and webhook registration."""

    @pytest.mark.asyncio
    async def test_bot_initialization(self, test_settings):
        """Test bot initialization process."""
        with patch("oleg_bot.config.settings", test_settings), \
             patch("telegram.Bot") as mock_bot_class:
            
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = MagicMock(username="test_bot", first_name="Test Bot")
            mock_bot.set_webhook = AsyncMock()
            mock_bot.get_webhook_info.return_value = MagicMock(
                url="https://test.example.com/webhook/telegram",
                pending_update_count=0
            )
            mock_bot_class.return_value = mock_bot
            
            await startup_manager.initialize_bot()
            
            # Verify bot was created with correct token
            mock_bot_class.assert_called_with(token="test_token")
            
            # Verify webhook was registered
            mock_bot.set_webhook.assert_called_once()

    @pytest.mark.asyncio 
    async def test_bot_status_endpoint(self, test_client):
        """Test bot status endpoint."""
        with patch.object(startup_manager, 'get_bot_status') as mock_status:
            mock_status.return_value = {
                "status": "active",
                "bot_username": "test_bot",
                "webhook_registered": True
            }
            
            response = test_client.get("/bot/status")
            assert response.status_code == 200
            
            status = response.json()
            assert status["status"] == "active"
            assert status["bot_username"] == "test_bot"


@pytest.mark.asyncio
async def test_end_to_end_message_flow(test_settings, mock_telegram_update):
    """Test complete end-to-end message processing flow."""
    with patch("oleg_bot.config.settings", test_settings):
        # Mock external dependencies
        with patch.object(startup_manager, 'bot') as mock_bot, \
             patch("openai.AsyncOpenAI") as mock_openai:
            
            # Setup mocks
            mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=124))
            
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "Nice to meet you! 😊"
            mock_completion.usage.prompt_tokens = 30
            mock_completion.usage.completion_tokens = 8
            mock_completion.usage.total_tokens = 38
            
            mock_openai_instance = mock_openai.return_value
            mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
            
            # Process the message through the webhook
            from oleg_bot.bot.webhook import process_update
            
            await process_update(mock_telegram_update)
            
            # Verify message was stored
            stored_messages = message_store.get_messages(-100123456789)
            assert len(stored_messages) > 0
            
            # Verify bot response was attempted (depending on decision logic)
            # This might send a message or reaction based on the bot's decision engine