"""Integration tests for webhook handling."""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from oleg_bot.bot.store import message_store
from oleg_bot.main import app


class TestWebhookIntegration:
    """Integration tests for webhook endpoints."""

    def setup_method(self) -> None:
        """Set up test client and clear message store."""
        self.client = TestClient(app)
        # Clear any existing messages
        message_store._chat_windows.clear()

    def test_health_check(self) -> None:
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "oleg-bot"}

    def test_root_endpoint(self) -> None:
        """Test root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["message"] == "OlegBot is running"
        assert json_response["version"] == "0.1.0"
        assert "environment" in json_response
        assert "status" in json_response

    def test_error_stats_endpoint(self) -> None:
        """Test error statistics endpoint."""
        response = self.client.get("/webhook/errors")
        assert response.status_code == 200
        json_response = response.json()
        assert "error_counts" in json_response
        assert "recent_errors" in json_response
        assert "total_errors" in json_response

    @patch("oleg_bot.bot.webhook.gpt_responder.generate_response")
    @patch("oleg_bot.config.settings.telegram_webhook_secret", None)
    def test_telegram_webhook_valid_message(self, mock_gpt_response) -> None:
        """Test processing valid Telegram message."""
        # Mock GPT response to avoid API calls
        mock_gpt_response.return_value = "Test response"

        # Sample Telegram update payload
        update_payload = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "date": int(datetime.now().timestamp()),
                "chat": {
                    "id": -100123456789,
                    "type": "group",
                    "title": "Test Group"
                },
                "from": {
                    "id": 987654321,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "text": "Hello, world!"
            }
        }

        response = self.client.post("/webhook/telegram", json=update_payload)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify user message was stored
        chat_id = -100123456789
        messages = message_store.get_messages(chat_id)
        user_messages = [msg for msg in messages if not msg.is_bot_message]
        assert len(user_messages) == 1
        assert user_messages[0].text == "Hello, world!"
        assert user_messages[0].user_id == 987654321

    @patch("oleg_bot.config.settings.telegram_webhook_secret", "test_secret")
    def test_telegram_webhook_with_secret_valid(self) -> None:
        """Test webhook with valid secret."""
        update_payload = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "date": int(datetime.now().timestamp()),
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 456, "is_bot": False, "first_name": "Test"},
                "text": "Test message"
            }
        }

        headers = {"X-Telegram-Bot-Api-Secret-Token": "test_secret"}
        response = self.client.post("/webhook/telegram", json=update_payload, headers=headers)
        assert response.status_code == 200

    @patch("oleg_bot.config.settings.telegram_webhook_secret", "test_secret")
    def test_telegram_webhook_with_secret_invalid(self) -> None:
        """Test webhook with invalid secret."""
        update_payload = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "date": int(datetime.now().timestamp()),
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 456, "is_bot": False, "first_name": "Test"},
                "text": "Test message"
            }
        }

        headers = {"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"}
        response = self.client.post("/webhook/telegram", json=update_payload, headers=headers)
        assert response.status_code == 403

    def test_telegram_webhook_invalid_payload(self) -> None:
        """Test webhook with invalid payload."""
        invalid_payload = {"invalid": "data"}

        response = self.client.post("/webhook/telegram", json=invalid_payload)
        assert response.status_code == 400

    def test_telegram_webhook_reply_message(self) -> None:
        """Test processing message that is a reply."""
        update_payload = {
            "update_id": 123456,
            "message": {
                "message_id": 2,
                "date": int(datetime.now().timestamp()),
                "chat": {"id": 123, "type": "group"},
                "from": {"id": 456, "is_bot": False, "first_name": "Test"},
                "text": "This is a reply",
                "reply_to_message": {
                    "message_id": 1,
                    "date": int(datetime.now().timestamp()),
                    "chat": {"id": 123, "type": "group"},
                    "from": {"id": 789, "is_bot": False, "first_name": "Other"},
                    "text": "Original message"
                }
            }
        }

        response = self.client.post("/webhook/telegram", json=update_payload)
        assert response.status_code == 200

        # Verify reply information was stored
        messages = message_store.get_messages(123)
        assert len(messages) == 1
        assert messages[0].reply_to_message_id == 1

    def test_telegram_webhook_edited_message(self) -> None:
        """Test processing edited message."""
        update_payload = {
            "update_id": 123456,
            "edited_message": {
                "message_id": 1,
                "date": int(datetime.now().timestamp()),
                "edit_date": int(datetime.now().timestamp()),
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 456, "is_bot": False, "first_name": "Test"},
                "text": "Edited message"
            }
        }

        response = self.client.post("/webhook/telegram", json=update_payload)
        assert response.status_code == 200

        # Verify edited message was stored
        messages = message_store.get_messages(123)
        assert len(messages) == 1
        assert messages[0].text == "Edited message"
