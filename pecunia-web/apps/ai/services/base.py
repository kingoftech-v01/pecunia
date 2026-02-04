"""
Base AI Service.

Provides base functionality for all AI services using Anthropic Claude API.
"""
import logging
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

import anthropic

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class AIRateLimitError(AIServiceError):
    """Raised when API rate limit is exceeded."""
    pass


class AIResponseError(AIServiceError):
    """Raised when AI response is invalid or unexpected."""
    pass


class BaseAIService(ABC):
    """
    Base class for AI services using Claude API.

    Provides common functionality for API communication,
    error handling, caching, and response parsing.
    """

    # Default model configuration
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TEMPERATURE = 0.3

    # Cache configuration
    CACHE_PREFIX = "ai_service"
    DEFAULT_CACHE_TTL = 3600  # 1 hour

    def __init__(
        self,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the AI service.

        Args:
            model: Claude model to use (default: claude-sonnet-4-20250514)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-1)
        """
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        if not self.api_key:
            raise AIServiceError(
                "ANTHROPIC_API_KEY not configured in settings"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        self.temperature = temperature or self.DEFAULT_TEMPERATURE

    def _make_request(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Make a request to Claude API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: System prompt (optional)
            max_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            str: Claude's response text

        Raises:
            AIServiceError: On API errors
            AIRateLimitError: On rate limit errors
        """
        start_time = time.time()

        try:
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "messages": messages,
            }

            if system:
                kwargs["system"] = system

            if temperature is not None:
                kwargs["temperature"] = temperature
            else:
                kwargs["temperature"] = self.temperature

            response = self.client.messages.create(**kwargs)

            processing_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"AI request completed in {processing_time}ms, "
                f"tokens used: {response.usage.input_tokens} input, "
                f"{response.usage.output_tokens} output"
            )

            if response.content and len(response.content) > 0:
                return response.content[0].text

            raise AIResponseError("Empty response from Claude API")

        except anthropic.RateLimitError as e:
            logger.warning(f"Claude API rate limit exceeded: {e}")
            raise AIRateLimitError("API rate limit exceeded. Please try again later.")

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise AIServiceError(f"AI service error: {str(e)}")

        except Exception as e:
            logger.exception(f"Unexpected error in AI service: {e}")
            raise AIServiceError(f"Unexpected error: {str(e)}")

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from Claude's response.

        Handles cases where response contains markdown code blocks.

        Args:
            response: Raw response text from Claude

        Returns:
            dict: Parsed JSON data

        Raises:
            AIResponseError: If JSON parsing fails
        """
        # Try to extract JSON from code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            raise AIResponseError(f"Invalid JSON response: {str(e)}")

    def _get_cache_key(self, prefix: str, *args) -> str:
        """
        Generate a cache key.

        Args:
            prefix: Key prefix
            *args: Additional key components

        Returns:
            str: Cache key
        """
        key_parts = [self.CACHE_PREFIX, prefix] + [str(arg) for arg in args]
        return ":".join(key_parts)

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available.

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None
        """
        return cache.get(cache_key)

    def _set_cached_result(
        self,
        cache_key: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Cache a result.

        Args:
            cache_key: Cache key
            result: Result to cache
            ttl: Time to live in seconds
        """
        cache.set(cache_key, result, ttl or self.DEFAULT_CACHE_TTL)

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this service.

        Returns:
            str: System prompt
        """
        pass

    def format_currency(self, amount: float, currency: str = "EUR") -> str:
        """
        Format amount as currency string.

        Args:
            amount: Numeric amount
            currency: Currency code

        Returns:
            str: Formatted currency string
        """
        symbols = {
            "EUR": "\u20ac",
            "USD": "$",
            "GBP": "\u00a3",
            "CHF": "CHF",
        }
        symbol = symbols.get(currency, currency)
        return f"{symbol}{amount:,.2f}"
