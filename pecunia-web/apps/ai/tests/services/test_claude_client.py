"""
Tests for ClaudeClient and SyncClaudeClient.

Tests async client, rate limiting, retry logic, and sync wrapper.
"""
import asyncio
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from django.test import override_settings

from apps.ai.services.claude_client import (
    ClaudeClient,
    SyncClaudeClient,
    ClaudeResponse,
    RateLimiter,
    ANTHROPIC_AVAILABLE,
)


# =============================================================================
# ClaudeResponse Tests
# =============================================================================

class TestClaudeResponse:

    def test_create_response(self):
        resp = ClaudeResponse(
            content="Hello",
            model="claude-3",
            tokens_input=10,
            tokens_output=5,
            request_id="req_123",
            latency_ms=100,
            cost_estimate=Decimal("0.001"),
        )
        assert resp.content == "Hello"
        assert resp.model == "claude-3"
        assert resp.tokens_input == 10
        assert resp.tokens_output == 5
        assert resp.request_id == "req_123"
        assert resp.latency_ms == 100
        assert resp.cost_estimate == Decimal("0.001")


# =============================================================================
# RateLimiter Tests
# =============================================================================

class TestRateLimiter:

    def test_create_rate_limiter(self):
        rl = RateLimiter(tokens_per_minute=100000)
        assert rl.tokens_per_minute == 100000

    def test_acquire_token(self):
        import asyncio
        rl = RateLimiter(tokens_per_minute=100000)
        # Should not raise
        asyncio.run(rl.acquire(100))

    def test_record_actual_tokens(self):
        import asyncio
        rl = RateLimiter(tokens_per_minute=100000)
        asyncio.run(rl.acquire(100))
        rl.record_actual_tokens(50)  # Actual was less than estimated


# =============================================================================
# ClaudeClient Tests
# =============================================================================

class TestClaudeClient:

    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_init(self):
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic not available")
        client = ClaudeClient()
        assert client is not None

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.claude_client.anthropic.AsyncAnthropic')
    def test_chat(self, mock_async_anthropic):
        import asyncio
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic not available")
        mock_client = MagicMock()
        mock_async_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello!")]
        mock_response.model = "claude-3-5-sonnet"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.id = "msg_123"

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        client = ClaudeClient()
        client.client = mock_client
        result = asyncio.run(client.chat(
            messages=[{'role': 'user', 'content': 'Hello'}],
        ))
        assert isinstance(result, ClaudeResponse)
        assert result.content == "Hello!"

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.claude_client.anthropic.AsyncAnthropic')
    def test_categorize(self, mock_async_anthropic):
        import asyncio
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic not available")
        mock_client = MagicMock()
        mock_async_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"category": "Food", "confidence": "high", "reasoning": "Coffee shop"}')]
        mock_response.model = "claude-3-5-sonnet"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_response.id = "msg_456"

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        client = ClaudeClient()
        client.client = mock_client
        result = asyncio.run(client.categorize(
            description="Coffee at Starbucks",
        ))
        assert isinstance(result, dict)


# =============================================================================
# SyncClaudeClient Tests
# =============================================================================

class TestSyncClaudeClient:

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.claude_client.anthropic.AsyncAnthropic')
    @patch('apps.ai.services.claude_client.anthropic.Anthropic')
    def test_init(self, mock_sync, mock_async):
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic not available")
        client = SyncClaudeClient()
        assert client is not None

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.claude_client.anthropic.AsyncAnthropic')
    @patch('apps.ai.services.claude_client.anthropic.Anthropic')
    def test_sync_chat(self, mock_anthropic_cls, mock_async_cls):
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic not available")
        mock_async_client = MagicMock()
        mock_async_cls.return_value = mock_async_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello sync!")]
        mock_response.model = "claude-3-5-sonnet"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.id = "msg_789"

        mock_async_client.messages.create = AsyncMock(return_value=mock_response)

        client = SyncClaudeClient()
        client._async_client.client = mock_async_client
        result = client.chat(
            messages=[{'role': 'user', 'content': 'Hello'}],
        )
        assert isinstance(result, ClaudeResponse)
        assert result.content == "Hello sync!"
