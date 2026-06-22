from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.admin.ai_connection_test import verify_anthropic_connection


@pytest.mark.asyncio
async def test_anthropic_connection_falls_back_when_primary_model_missing():
    client = MagicMock()
    client.messages.create = AsyncMock(
        side_effect=[
            Exception("Error code: 404 - model not found"),
            None,
        ]
    )

    with patch(
        "app.admin.ai_connection_test.anthropic.AsyncAnthropic",
        return_value=client,
    ):
        success, message = await verify_anthropic_connection(
            "sk-ant-test",
            "claude-sonnet-4-20250514",
        )

    assert success is True
    assert "Connection successful" in message
    assert client.messages.create.await_count == 2


@pytest.mark.asyncio
async def test_anthropic_connection_invalid_key():
    client = MagicMock()
    client.messages.create = AsyncMock(
        side_effect=Exception("Error code: 401 - authentication_error")
    )

    with patch(
        "app.admin.ai_connection_test.anthropic.AsyncAnthropic",
        return_value=client,
    ):
        success, message = await verify_anthropic_connection(
            "bad-key",
            "claude-haiku-4-5",
        )

    assert success is False
    assert message == "Invalid API key"
