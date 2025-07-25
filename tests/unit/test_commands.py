"""Unit tests for command handler module."""

from unittest.mock import patch

from oleg_bot.bot.commands import CommandHandler


class TestCommandHandler:
    """Test cases for CommandHandler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.handler = CommandHandler(admin_user_ids=[123, 456])

    def test_initialization(self) -> None:
        """Test command handler initialization."""
        handler = CommandHandler(admin_user_ids=[100, 200])

        assert 100 in handler.admin_user_ids
        assert 200 in handler.admin_user_ids
        assert len(handler.commands) > 0
        assert "/help" in handler.commands
        assert "/stats" in handler.commands
        assert "/setquota" in handler.commands
        assert "/setgap" in handler.commands

    def test_initialization_no_admins(self) -> None:
        """Test initialization with no admin users."""
        handler = CommandHandler()

        assert len(handler.admin_user_ids) == 0

    def test_is_command_true(self) -> None:
        """Test command detection for valid commands."""
        assert self.handler.is_command("/help")
        assert self.handler.is_command("/stats")
        assert self.handler.is_command("/setquota 0.15")
        assert self.handler.is_command("/setgap 30")
        assert self.handler.is_command("  /help  ")  # With whitespace

    def test_is_command_false(self) -> None:
        """Test command detection for invalid commands."""
        assert not self.handler.is_command("hello")
        assert not self.handler.is_command("not a command")
        assert not self.handler.is_command("/unknown")
        assert not self.handler.is_command("")
        assert not self.handler.is_command(None)

    def test_is_admin_true(self) -> None:
        """Test admin check for valid admin users."""
        assert self.handler._is_admin(123)
        assert self.handler._is_admin(456)

    def test_is_admin_false(self) -> None:
        """Test admin check for non-admin users."""
        assert not self.handler._is_admin(999)
        assert not self.handler._is_admin(0)

    def test_handle_help_command(self) -> None:
        """Test /help command handling."""
        response = self.handler.handle_command("/help", 789, 100)

        assert "OlegBot Commands" in response
        assert "/stats" in response
        assert "/help" in response
        # Should not show admin commands for non-admin user
        assert "/setquota" not in response
        assert "/setgap" not in response

    def test_handle_help_command_admin(self) -> None:
        """Test /help command for admin user."""
        response = self.handler.handle_command("/help", 123, 100)  # Admin user

        assert "OlegBot Commands" in response
        assert "/stats" in response
        assert "/help" in response
        # Should show admin commands for admin user
        assert "/setquota" in response
        assert "/setgap" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    @patch('oleg_bot.bot.commands.reaction_handler')
    @patch('oleg_bot.bot.commands.message_store')
    def test_handle_stats_command(self, mock_store, mock_reactions, mock_engine) -> None:
        """Test /stats command handling."""
        # Mock return values
        mock_engine.get_stats.return_value = {
            "message_count": 100,
            "reply_count": 15,
            "current_quota_usage": 0.15,
            "target_ratio": 0.10,
            "gap_min_seconds": 20,
            "topic_heat_threshold": 0.6,
        }
        mock_reactions.get_stats.return_value = {
            "total_reaction_types": 25,
            "supported_languages": 8,
        }
        mock_store.get_chat_count.return_value = 5
        mock_store.window_size = 50
        mock_store.get_messages.return_value = [
            type('obj', (object,), {'is_bot_message': True})(),
            type('obj', (object,), {'is_bot_message': False})(),
        ]

        response = self.handler.handle_command("/stats", 789, 100)

        assert "OlegBot Statistics" in response
        assert "Messages processed: 100" in response
        assert "Replies sent: 15" in response
        assert "15.0%" in response  # Current quota usage
        assert "Active chats: 5" in response
        assert "Reaction types: 25" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    def test_handle_setquota_no_args(self, mock_engine) -> None:
        """Test /setquota command with no arguments."""
        mock_engine.reply_target_ratio = 0.10

        response = self.handler.handle_command("/setquota", 123, 100)  # Admin user

        assert "Current quota: 10.0%" in response
        assert "Usage: /setquota" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    def test_handle_setquota_valid(self, mock_engine) -> None:
        """Test /setquota command with valid argument."""
        mock_engine.reply_target_ratio = 0.10
        mock_engine.update_settings = lambda **kwargs: setattr(mock_engine, 'reply_target_ratio', kwargs['reply_target_ratio'])

        response = self.handler.handle_command("/setquota 0.15", 123, 100)  # Admin user

        assert "Quota updated" in response
        assert "10.0%" in response  # Old value
        assert "15.0%" in response  # New value

    def test_handle_setquota_invalid_range(self) -> None:
        """Test /setquota command with invalid range."""
        response = self.handler.handle_command("/setquota 1.5", 123, 100)  # Admin user

        assert "Quota must be between 0.0 and 1.0" in response

    def test_handle_setquota_invalid_format(self) -> None:
        """Test /setquota command with invalid format."""
        response = self.handler.handle_command("/setquota abc", 123, 100)  # Admin user

        assert "Invalid quota value" in response

    def test_handle_setquota_non_admin(self) -> None:
        """Test /setquota command by non-admin user."""
        response = self.handler.handle_command("/setquota 0.15", 789, 100)  # Non-admin

        assert "Admin permissions required" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    def test_handle_setgap_no_args(self, mock_engine) -> None:
        """Test /setgap command with no arguments."""
        mock_engine.gap_min_seconds = 20

        response = self.handler.handle_command("/setgap", 123, 100)  # Admin user

        assert "Current gap: 20s" in response
        assert "Usage: /setgap" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    def test_handle_setgap_valid(self, mock_engine) -> None:
        """Test /setgap command with valid argument."""
        mock_engine.gap_min_seconds = 20
        mock_engine.update_settings = lambda **kwargs: setattr(mock_engine, 'gap_min_seconds', kwargs['gap_min_seconds'])

        response = self.handler.handle_command("/setgap 30", 123, 100)  # Admin user

        assert "Gap updated" in response
        assert "20s" in response  # Old value
        assert "30s" in response  # New value

    def test_handle_setgap_invalid_range(self) -> None:
        """Test /setgap command with invalid range."""
        response = self.handler.handle_command("/setgap 500", 123, 100)  # Admin user

        assert "Gap must be between 5 and 300 seconds" in response

    def test_handle_setgap_invalid_format(self) -> None:
        """Test /setgap command with invalid format."""
        response = self.handler.handle_command("/setgap abc", 123, 100)  # Admin user

        assert "Invalid gap value" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    def test_handle_status_command(self, mock_engine) -> None:
        """Test /status command handling."""
        mock_engine.get_stats.return_value = {
            "current_quota_usage": 0.3,
            "target_ratio": 0.10,
            "message_count": 50,
        }
        mock_engine._time_since_last_bot_message.return_value = 120.0  # 2 minutes

        response = self.handler.handle_command("/status", 789, 100)

        assert "Bot Status:" in response
        assert "30.0%" in response  # Quota usage
        assert "2m ago" in response  # Last activity
        assert "Messages processed: 50" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    def test_handle_status_no_recent_activity(self, mock_engine) -> None:
        """Test /status command with no recent activity."""
        mock_engine.get_stats.return_value = {
            "current_quota_usage": 0.05,
            "target_ratio": 0.10,
            "message_count": 10,
        }
        mock_engine._time_since_last_bot_message.return_value = float('inf')

        response = self.handler.handle_command("/status", 789, 100)

        assert "Bot Status:" in response
        assert "No recent activity" in response

    def test_handle_unknown_command(self) -> None:
        """Test handling unknown command."""
        response = self.handler.handle_command("/unknown", 789, 100)

        assert "Unknown command" in response
        assert "/help" in response

    def test_handle_not_command(self) -> None:
        """Test handling non-command text."""
        response = self.handler.handle_command("hello world", 789, 100)

        assert "Unknown command" in response
        assert "/help" in response

    @patch('oleg_bot.bot.commands.decision_engine')
    def test_handle_command_with_exception(self, mock_engine) -> None:
        """Test command handling when exception occurs."""
        mock_engine.get_stats.side_effect = Exception("Test error")

        response = self.handler.handle_command("/stats", 789, 100)

        assert "Command failed" in response
        assert "Test error" in response

    def test_add_admin(self) -> None:
        """Test adding admin user."""
        initial_count = len(self.handler.admin_user_ids)
        self.handler.add_admin(999)

        assert 999 in self.handler.admin_user_ids
        assert len(self.handler.admin_user_ids) == initial_count + 1

    def test_add_admin_existing(self) -> None:
        """Test adding existing admin user."""
        initial_count = len(self.handler.admin_user_ids)
        self.handler.add_admin(123)  # Already admin

        assert 123 in self.handler.admin_user_ids
        assert len(self.handler.admin_user_ids) == initial_count  # No change

    def test_remove_admin(self) -> None:
        """Test removing admin user."""
        initial_count = len(self.handler.admin_user_ids)
        self.handler.remove_admin(123)

        assert 123 not in self.handler.admin_user_ids
        assert len(self.handler.admin_user_ids) == initial_count - 1

    def test_remove_admin_non_existing(self) -> None:
        """Test removing non-existing admin user."""
        initial_count = len(self.handler.admin_user_ids)
        self.handler.remove_admin(999)  # Not admin

        assert len(self.handler.admin_user_ids) == initial_count  # No change

    def test_get_available_commands_admin(self) -> None:
        """Test getting available commands for admin user."""
        commands = self.handler.get_available_commands(123)  # Admin user

        assert "/help" in commands
        assert "/stats" in commands
        assert "/setquota" in commands
        assert "/setgap" in commands
        assert "/status" in commands

    def test_get_available_commands_non_admin(self) -> None:
        """Test getting available commands for non-admin user."""
        commands = self.handler.get_available_commands(789)  # Non-admin user

        assert "/help" in commands
        assert "/stats" in commands
        assert "/status" in commands
        # Should not include admin commands
        assert "/setquota" not in commands
        assert "/setgap" not in commands

    def test_command_parsing_with_args(self) -> None:
        """Test command parsing with arguments."""
        # This is tested implicitly in setquota/setgap tests, but let's be explicit
        response = self.handler.handle_command("/setquota 0.2 extra args", 123, 100)

        # Should handle extra arguments gracefully
        assert "Quota updated" in response or "Invalid quota" in response

    def test_command_case_sensitivity(self) -> None:
        """Test command case sensitivity."""
        response = self.handler.handle_command("/HELP", 789, 100)

        assert "OlegBot Commands" in response

    def test_command_with_whitespace(self) -> None:
        """Test command with extra whitespace."""
        response = self.handler.handle_command("  /help  ", 789, 100)

        assert "OlegBot Commands" in response
