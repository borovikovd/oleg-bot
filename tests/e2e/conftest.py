"""Pytest configuration for E2E tests."""

import asyncio
from unittest.mock import patch

import pytest

from oleg_bot.bot.store import message_store


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def clean_message_store():
    """Clean message store before each test."""
    message_store._chat_windows.clear()
    message_store._chat_last_activity.clear()


@pytest.fixture(autouse=True)
def mock_startup_manager():
    """Mock startup manager to prevent actual bot initialization in tests."""
    with patch("oleg_bot.bot.startup.startup_manager.initialize_bot"):
        yield

