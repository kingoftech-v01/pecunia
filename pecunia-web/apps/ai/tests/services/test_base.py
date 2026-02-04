"""
Tests for BaseAIService.

Tests initialization, API request handling, JSON parsing, caching, and error handling.
"""
import json
from unittest.mock import patch, MagicMock

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.ai.services.base import (
    BaseAIService,
    AIServiceError,
    AIRateLimitError,
    AIResponseError,
)


class ConcreteAIService(BaseAIService):
    """Concrete implementation for testing."""

    def get_system_prompt(self):
        return "You are a test assistant."


# =============================================================================
# Initialization Tests
# =============================================================================

class TestBaseAIServiceInit:

    @override_settings(ANTHROPIC_API_KEY='test-key-123')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_init_with_api_key(self, mock_anthropic):
        service = ConcreteAIService()
        assert service.api_key == 'test-key-123'
        assert service.model == BaseAIService.DEFAULT_MODEL
        assert service.max_tokens == BaseAIService.DEFAULT_MAX_TOKENS
        assert service.temperature == BaseAIService.DEFAULT_TEMPERATURE
        mock_anthropic.assert_called_once_with(api_key='test-key-123')

    @override_settings(ANTHROPIC_API_KEY=None)
    def test_init_without_api_key(self):
        with pytest.raises(AIServiceError, match="ANTHROPIC_API_KEY not configured"):
            ConcreteAIService()

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_init_custom_params(self, mock_anthropic):
        service = ConcreteAIService(
            model='claude-3-opus-20240229',
            max_tokens=2048,
            temperature=0.7,
        )
        assert service.model == 'claude-3-opus-20240229'
        assert service.max_tokens == 2048
        assert service.temperature == 0.7


# =============================================================================
# _make_request Tests
# =============================================================================

class TestMakeRequest:

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_successful_request(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello!")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_response

        service = ConcreteAIService()
        result = service._make_request([{'role': 'user', 'content': 'Hi'}])
        assert result == "Hello!"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_request_with_system_prompt(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="OK")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_response

        service = ConcreteAIService()
        service._make_request(
            [{'role': 'user', 'content': 'Hi'}],
            system="Be helpful",
        )
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['system'] == "Be helpful"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_empty_response_raises(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        service = ConcreteAIService()
        # AIResponseError is caught by the broad except clause and re-raised as AIServiceError
        with pytest.raises(AIServiceError):
            service._make_request([{'role': 'user', 'content': 'Hi'}])

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_rate_limit_error(self, mock_anthropic_cls):
        import anthropic as real_anthropic
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = real_anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Rate limited"}},
        )

        service = ConcreteAIService()
        with pytest.raises(AIRateLimitError):
            service._make_request([{'role': 'user', 'content': 'Hi'}])

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_api_error(self, mock_anthropic_cls):
        import anthropic as real_anthropic
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = real_anthropic.APIError(
            message="Server error",
            request=MagicMock(),
            body={"error": {"message": "Server error"}},
        )

        service = ConcreteAIService()
        with pytest.raises(AIServiceError):
            service._make_request([{'role': 'user', 'content': 'Hi'}])

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_unexpected_error(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("Unexpected")

        service = ConcreteAIService()
        with pytest.raises(AIServiceError, match="Unexpected"):
            service._make_request([{'role': 'user', 'content': 'Hi'}])


# =============================================================================
# _parse_json_response Tests
# =============================================================================

class TestParseJsonResponse:

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def _get_service(self, mock_anthropic_cls):
        return ConcreteAIService()

    def test_parse_plain_json(self):
        service = self._get_service()
        result = service._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_code_block(self):
        service = self._get_service()
        response = '```json\n{"key": "value"}\n```'
        result = service._parse_json_response(response)
        assert result == {"key": "value"}

    def test_parse_generic_code_block(self):
        service = self._get_service()
        response = '```\n{"key": "value"}\n```'
        result = service._parse_json_response(response)
        assert result == {"key": "value"}

    def test_parse_json_with_surrounding_text(self):
        service = self._get_service()
        response = 'Here is the result:\n```json\n{"key": "value"}\n```\nDone.'
        result = service._parse_json_response(response)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        service = self._get_service()
        with pytest.raises(AIResponseError, match="Invalid JSON"):
            service._parse_json_response("not json at all")


# =============================================================================
# Cache Tests
# =============================================================================

class TestCacheHelpers:

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_get_cache_key(self, mock_anthropic_cls):
        service = ConcreteAIService()
        key = service._get_cache_key("test", "user123", "v1")
        assert key == "ai_service:test:user123:v1"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_set_and_get_cached_result(self, mock_anthropic_cls):
        service = ConcreteAIService()
        cache_key = "test:cache:key"
        data = {"result": "cached"}
        service._set_cached_result(cache_key, data)
        result = service._get_cached_result(cache_key)
        assert result == data

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_get_cached_result_miss(self, mock_anthropic_cls):
        service = ConcreteAIService()
        result = service._get_cached_result("nonexistent:key")
        assert result is None

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_set_cached_with_custom_ttl(self, mock_anthropic_cls):
        service = ConcreteAIService()
        with patch.object(cache, 'set') as mock_set:
            service._set_cached_result("key", {"data": 1}, ttl=300)
            mock_set.assert_called_once_with("key", {"data": 1}, 300)


# =============================================================================
# format_currency Tests
# =============================================================================

class TestFormatCurrency:

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_format_eur(self, mock_anthropic_cls):
        service = ConcreteAIService()
        assert service.format_currency(1234.56, "EUR") == "\u20ac1,234.56"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_format_usd(self, mock_anthropic_cls):
        service = ConcreteAIService()
        assert service.format_currency(1234.56, "USD") == "$1,234.56"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_format_gbp(self, mock_anthropic_cls):
        service = ConcreteAIService()
        assert service.format_currency(50.00, "GBP") == "\u00a350.00"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_format_chf(self, mock_anthropic_cls):
        service = ConcreteAIService()
        assert service.format_currency(100.00, "CHF") == "CHF100.00"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_format_unknown_currency(self, mock_anthropic_cls):
        service = ConcreteAIService()
        assert service.format_currency(100.00, "JPY") == "JPY100.00"

    @override_settings(ANTHROPIC_API_KEY='key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_get_system_prompt(self, mock_anthropic_cls):
        service = ConcreteAIService()
        assert service.get_system_prompt() == "You are a test assistant."
