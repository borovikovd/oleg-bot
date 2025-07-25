"""Admin commands for OlegBot management."""

import logging

from .decision import decision_engine
from .reactions import reaction_handler
from .store import message_store
from ..config import settings

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles admin commands for bot management."""

    def __init__(self, admin_user_ids: list[int] | None = None):
        """
        Initialize command handler.

        Args:
            admin_user_ids: List of user IDs that can use admin commands
        """
        self.admin_user_ids = set(admin_user_ids or [])
        self.commands = {
            "/setquota": self._handle_setquota,
            "/setgap": self._handle_setgap,
            "/stats": self._handle_stats,
            "/help": self._handle_help,
            "/status": self._handle_status,
        }
        logger.info(
            f"Command handler initialized with {len(self.admin_user_ids)} admin users"
        )

    def is_command(self, text: str | None) -> bool:
        """Check if text is a bot command."""
        if not text:
            return False

        text = text.strip().lower()
        return any(text.startswith(cmd) for cmd in self.commands.keys())

    def handle_command(self, text: str, user_id: int, chat_id: int) -> str:
        """
        Handle a bot command.

        Args:
            text: Command text
            user_id: User who sent the command
            chat_id: Chat where command was sent

        Returns:
            Response message
        """
        if not self.is_command(text):
            return "Unknown command. Use /help to see available commands."

        # Parse command and arguments
        parts = text.strip().split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Check admin permissions for admin commands
        admin_commands = ["/setquota", "/setgap"]
        if command in admin_commands and not self._is_admin(user_id):
            return "❌ Admin permissions required for this command."

        # Execute command
        if command in self.commands:
            try:
                response = self.commands[command](args, user_id, chat_id)
                logger.info(
                    f"Command executed: {command} by user {user_id} in chat {chat_id}"
                )
                return response
            except Exception as e:
                logger.error(f"Command execution failed: {command}, error: {e}")
                return f"❌ Command failed: {str(e)}"
        else:
            return "Unknown command. Use /help to see available commands."

    def _is_admin(self, user_id: int) -> bool:
        """Check if user has admin permissions."""
        return user_id in self.admin_user_ids

    def _handle_setquota(self, args: list[str], user_id: int, chat_id: int) -> str:
        """Handle /setquota command."""
        if not args:
            current_quota = decision_engine.reply_target_ratio
            return f"📊 Current quota: {current_quota:.1%}\nUsage: /setquota <ratio> (e.g., /setquota 0.15 for 15%)"

        try:
            new_quota = float(args[0])
            if not 0.0 <= new_quota <= 1.0:
                return "❌ Quota must be between 0.0 and 1.0 (0% to 100%)"

            old_quota = decision_engine.reply_target_ratio
            decision_engine.update_settings(reply_target_ratio=new_quota)

            return f"✅ Quota updated: {old_quota:.1%} → {new_quota:.1%}"

        except ValueError:
            return "❌ Invalid quota value. Use a decimal between 0.0 and 1.0"

    def _handle_setgap(self, args: list[str], user_id: int, chat_id: int) -> str:
        """Handle /setgap command."""
        if not args:
            current_gap = decision_engine.gap_min_seconds
            return f"⏱️ Current gap: {current_gap}s\nUsage: /setgap <seconds> (e.g., /setgap 30)"

        try:
            new_gap = int(args[0])
            if not 5 <= new_gap <= 300:  # 5 seconds to 5 minutes
                return "❌ Gap must be between 5 and 300 seconds"

            old_gap = decision_engine.gap_min_seconds
            decision_engine.update_settings(gap_min_seconds=new_gap)

            return f"✅ Gap updated: {old_gap}s → {new_gap}s"

        except ValueError:
            return "❌ Invalid gap value. Use an integer between 5 and 300"

    def _handle_stats(self, args: list[str], user_id: int, chat_id: int) -> str:
        """Handle /stats command."""
        # Get stats from all components
        decision_stats = decision_engine.get_stats()
        reaction_stats = reaction_handler.get_stats()

        # Format comprehensive stats
        stats_text = "📊 **OlegBot Statistics**\n\n"

        # Decision engine stats
        stats_text += "🧠 **Decision Engine:**\n"
        stats_text += f"• Messages processed: {decision_stats['message_count']}\n"
        stats_text += f"• Replies sent: {decision_stats['reply_count']}\n"
        stats_text += (
            f"• Current quota usage: {decision_stats['current_quota_usage']:.1%}\n"
        )
        stats_text += f"• Target ratio: {decision_stats['target_ratio']:.1%}\n"
        stats_text += f"• Minimum gap: {decision_stats['gap_min_seconds']}s\n"
        stats_text += (
            f"• Heat threshold: {decision_stats['topic_heat_threshold']:.1f}\n\n"
        )

        # Message store stats
        stats_text += "💾 **Message Store:**\n"
        stats_text += f"• Active chats: {message_store.get_chat_count()}\n"
        stats_text += f"• Window size: {message_store.window_size} messages\n\n"

        # Reaction handler stats
        stats_text += "😊 **Reaction Handler:**\n"
        stats_text += f"• Reaction types: {reaction_stats['total_reaction_types']}\n"
        stats_text += (
            f"• Supported languages: {reaction_stats['supported_languages']}\n"
        )

        # Chat-specific stats if available
        chat_messages = message_store.get_messages(chat_id)
        if chat_messages:
            stats_text += "\n💬 **This Chat:**\n"
            stats_text += f"• Messages in window: {len(chat_messages)}\n"

            # Recent bot activity
            recent_bot_msgs = [msg for msg in chat_messages if msg.is_bot_message]
            stats_text += f"• Bot messages: {len(recent_bot_msgs)}\n"

        return stats_text

    def _handle_help(self, args: list[str], user_id: int, chat_id: int) -> str:
        """Handle /help command."""
        help_text = "🤖 **OlegBot Commands**\n\n"

        help_text += "📊 **General Commands:**\n"
        help_text += "• `/stats` - Show bot statistics\n"
        help_text += "• `/status` - Show bot status\n"
        help_text += "• `/help` - Show this help message\n\n"

        if self._is_admin(user_id):
            help_text += "⚙️ **Admin Commands:**\n"
            help_text += "• `/setquota <ratio>` - Set reply quota (0.0-1.0)\n"
            help_text += (
                "• `/setgap <seconds>` - Set minimum gap between replies (5-300)\n\n"
            )

        help_text += "💡 **Tips:**\n"
        help_text += "• Mention @olegbot to get a guaranteed response\n"
        help_text += "• Bot participates in hot topics automatically\n"
        help_text += "• Reactions are used when rate-limited\n"

        return help_text

    def _handle_status(self, args: list[str], user_id: int, chat_id: int) -> str:
        """Handle /status command."""
        stats = decision_engine.get_stats()

        # Determine bot status
        quota_usage = stats["current_quota_usage"]
        if quota_usage < 0.5:
            status_emoji = "🟢"
            status_text = "Active"
        elif quota_usage < 0.8:
            status_emoji = "🟡"
            status_text = "Moderate"
        else:
            status_emoji = "🔴"
            status_text = "Rate Limited"

        # Check if bot has recent activity in this chat
        time_since_last = decision_engine._time_since_last_bot_message(chat_id)
        if time_since_last == float("inf"):
            last_activity = "No recent activity"
        elif time_since_last < 60:
            last_activity = f"{time_since_last:.0f}s ago"
        elif time_since_last < 3600:
            last_activity = f"{time_since_last / 60:.0f}m ago"
        else:
            last_activity = f"{time_since_last / 3600:.0f}h ago"

        status_text_full = f"{status_emoji} **Bot Status: {status_text}**\n\n"
        status_text_full += (
            f"📈 Quota usage: {quota_usage:.1%} / {stats['target_ratio']:.1%}\n"
        )
        status_text_full += f"⏱️ Last activity: {last_activity}\n"
        status_text_full += f"💬 Messages processed: {stats['message_count']}\n"

        return status_text_full

    def add_admin(self, user_id: int) -> None:
        """Add a user as admin."""
        self.admin_user_ids.add(user_id)
        logger.info(f"Added admin user: {user_id}")

    def remove_admin(self, user_id: int) -> None:
        """Remove admin permissions from user."""
        self.admin_user_ids.discard(user_id)
        logger.info(f"Removed admin user: {user_id}")

    def get_available_commands(self, user_id: int) -> list[str]:
        """Get list of available commands for user."""
        all_commands = list(self.commands.keys())

        if not self._is_admin(user_id):
            # Filter out admin commands
            admin_commands = ["/setquota", "/setgap"]
            all_commands = [cmd for cmd in all_commands if cmd not in admin_commands]

        return all_commands


# Global command handler instance with admin users from config
command_handler = CommandHandler(admin_user_ids=settings.admin_user_ids)
