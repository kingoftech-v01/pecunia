"""
Claude API Client for Pecunia.

This module provides a robust client for interacting with the Claude API,
including rate limiting, retry logic, and cost tracking.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from django.conf import settings
from django.utils import timezone

try:
    import anthropic
    from anthropic import AsyncAnthropic, RateLimitError, APIError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None
    AsyncAnthropic = None
    RateLimitError = Exception
    APIError = Exception

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResponse:
    """Response from Claude API."""
    content: str
    model: str
    tokens_input: int
    tokens_output: int
    request_id: str
    latency_ms: int
    cost_estimate: Decimal


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Implements a simple rate limiting mechanism to prevent
    exceeding API rate limits.
    """

    def __init__(self, requests_per_minute: int = 50, tokens_per_minute: int = 100000):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.request_timestamps: list[float] = []
        self.token_counts: list[tuple[float, int]] = []
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """
        Wait until rate limit allows the request.

        Args:
            estimated_tokens: Estimated tokens for this request
        """
        async with self._lock:
            now = time.time()
            minute_ago = now - 60

            # Clean old entries
            self.request_timestamps = [
                ts for ts in self.request_timestamps if ts > minute_ago
            ]
            self.token_counts = [
                (ts, count) for ts, count in self.token_counts if ts > minute_ago
            ]

            # Dual limits: requests/min prevents API abuse, tokens/min controls cost.
            while len(self.request_timestamps) >= self.requests_per_minute:
                wait_time = self.request_timestamps[0] - minute_ago
                if wait_time > 0:
                    await asyncio.sleep(wait_time + 0.1)
                now = time.time()
                minute_ago = now - 60
                self.request_timestamps = [
                    ts for ts in self.request_timestamps if ts > minute_ago
                ]

            # Check token limit
            total_tokens = sum(count for _, count in self.token_counts)
            while total_tokens + estimated_tokens > self.tokens_per_minute:
                if self.token_counts:
                    wait_time = self.token_counts[0][0] - minute_ago
                    if wait_time > 0:
                        await asyncio.sleep(wait_time + 0.1)
                now = time.time()
                minute_ago = now - 60
                self.token_counts = [
                    (ts, count) for ts, count in self.token_counts if ts > minute_ago
                ]
                total_tokens = sum(count for _, count in self.token_counts)

            # Record this request
            self.request_timestamps.append(now)
            self.token_counts.append((now, estimated_tokens))

    def record_actual_tokens(self, tokens: int) -> None:
        """Replace estimate with actual tokens after API response arrives."""
        if self.token_counts:
            timestamp, _ = self.token_counts[-1]
            self.token_counts[-1] = (timestamp, tokens)


class ClaudeClient:
    """
    Async client for Claude API with rate limiting and retry logic.

    Provides methods for chat, transaction categorization,
    and spending analysis.
    """

    # Model configurations
    DEFAULT_MODEL = 'claude-3-5-haiku-20241022'  # Fast and cost-effective for most tasks
    ANALYSIS_MODEL = 'claude-3-5-sonnet-20241022'  # More capable for complex analysis

    # Pricing per 1M tokens
    PRICING = {
        'claude-3-opus-20240229': {'input': 15.00, 'output': 75.00},
        'claude-3-sonnet-20240229': {'input': 3.00, 'output': 15.00},
        'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25},
        'claude-3-5-sonnet-20241022': {'input': 3.00, 'output': 15.00},
        'claude-3-5-haiku-20241022': {'input': 0.80, 'output': 4.00},
    }

    # Retry configuration
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Claude client.

        Args:
            api_key: Anthropic API key. If not provided, uses settings.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is not installed. "
                "Install it with: pip install anthropic"
            )

        self.api_key = api_key or getattr(settings, 'ANTHROPIC_API_KEY', None)
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY in settings or pass it directly."
            )

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.rate_limiter = RateLimiter()

        # System prompts
        self.base_system_prompt = """You are a helpful financial assistant for a personal finance management application.
You help users understand their spending patterns, manage budgets, and make better financial decisions.
Always be concise, practical, and focused on actionable advice.
Never provide specific investment advice or recommend specific financial products.
Respect user privacy and never ask for sensitive personal information."""

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate cost estimate for API call."""
        if model in self.PRICING:
            pricing = self.PRICING[model]
            input_cost = (input_tokens / 1_000_000) * pricing['input']
            output_cost = (output_tokens / 1_000_000) * pricing['output']
            return Decimal(str(input_cost + output_cost))
        return Decimal('0')

    async def _call_api(
        self,
        messages: list[dict],
        system_prompt: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> ClaudeResponse:
        """
        Make an API call with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt for the conversation
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            ClaudeResponse with the API response

        Raises:
            anthropic.APIError: If all retries fail
        """
        # Rough estimate: ~2 tokens per character; refined after response.
        estimated_tokens = sum(len(m.get('content', '')) for m in messages) * 2
        await self.rate_limiter.acquire(estimated_tokens)

        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()

                response = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=messages,
                    temperature=temperature
                )

                latency_ms = int((time.time() - start_time) * 1000)

                # Extract content
                content = ''
                if response.content:
                    content = response.content[0].text

                # Update rate limiter with actual tokens
                total_tokens = response.usage.input_tokens + response.usage.output_tokens
                self.rate_limiter.record_actual_tokens(total_tokens)

                return ClaudeResponse(
                    content=content,
                    model=model,
                    tokens_input=response.usage.input_tokens,
                    tokens_output=response.usage.output_tokens,
                    request_id=response.id,
                    latency_ms=latency_ms,
                    cost_estimate=self._calculate_cost(
                        model,
                        response.usage.input_tokens,
                        response.usage.output_tokens
                    )
                )

            except RateLimitError as e:
                last_error = e
                wait_time = self.BASE_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(wait_time)

            except APIError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"API error: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise last_error

    async def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        user: Optional[Any] = None
    ) -> ClaudeResponse:
        """
        Have a conversation with Claude.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional custom system prompt
            user: Optional user for logging

        Returns:
            ClaudeResponse with the assistant's reply
        """
        prompt = system_prompt or self.base_system_prompt

        response = await self._call_api(
            messages=messages,
            system_prompt=prompt,
            model=self.DEFAULT_MODEL,
            max_tokens=2048,
            temperature=0.7
        )

        # Log usage if user provided
        if user:
            await self._log_usage(user, response, 'chat')

        return response

    async def categorize(
        self,
        description: str,
        categories: Optional[list[str]] = None,
        user: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Categorize a transaction based on its description.

        Args:
            description: Transaction description
            categories: List of valid categories (optional)
            user: Optional user for logging

        Returns:
            Dict with 'category', 'confidence', and 'reasoning'
        """
        default_categories = [
            'Food & Dining', 'Transportation', 'Shopping', 'Entertainment',
            'Bills & Utilities', 'Healthcare', 'Travel', 'Income',
            'Transfer', 'Fees & Charges', 'Other'
        ]

        category_list = categories or default_categories

        system_prompt = f"""You are a transaction categorization assistant.
Categorize the given transaction into one of these categories: {', '.join(category_list)}

Respond in JSON format with:
- "category": the best matching category (must be from the list above)
- "confidence": confidence level (high, medium, low)
- "reasoning": brief explanation of why this category was chosen

Only respond with valid JSON, no additional text."""

        messages = [
            {'role': 'user', 'content': f'Categorize this transaction: "{description}"'}
        ]

        response = await self._call_api(
            messages=messages,
            system_prompt=system_prompt,
            model=self.DEFAULT_MODEL,
            max_tokens=256,
            temperature=0.3  # Lower temperature for more consistent categorization
        )

        # Log usage if user provided
        if user:
            await self._log_usage(user, response, 'categorize')

        # Parse JSON response
        try:
            result = json.loads(response.content)
            # Validate category
            if result.get('category') not in category_list:
                result['category'] = 'Other'
            return result
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse categorization response: {response.content}")
            return {
                'category': 'Other',
                'confidence': 'low',
                'reasoning': 'Could not parse AI response'
            }

    async def analyze_spending(
        self,
        transactions: list[dict],
        period: str = 'month',
        user: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Analyze spending patterns from transactions.

        Args:
            transactions: List of transaction dicts with 'description', 'amount', 'category', 'date'
            period: Analysis period ('week', 'month', 'quarter', 'year')
            user: Optional user for logging

        Returns:
            Dict with analysis results including insights, anomalies, and recommendations
        """
        # Prepare transaction summary for analysis
        if not transactions:
            return {
                'insights': [],
                'anomalies': [],
                'recommendations': [],
                'summary': 'No transactions to analyze.'
            }

        # Aggregate by category
        category_totals: dict[str, float] = {}
        for t in transactions:
            category = t.get('category', 'Other')
            amount = abs(float(t.get('amount', 0)))
            category_totals[category] = category_totals.get(category, 0) + amount

        total_spending = sum(category_totals.values())

        # Format for AI
        spending_summary = '\n'.join([
            f"- {cat}: ${amount:.2f} ({(amount/total_spending*100):.1f}%)"
            for cat, amount in sorted(category_totals.items(), key=lambda x: -x[1])
        ])

        system_prompt = """You are a financial analysis assistant.
Analyze the user's spending data and provide actionable insights.

Respond in JSON format with:
- "summary": A brief 1-2 sentence summary of overall spending
- "insights": Array of 2-4 key insights about spending patterns
- "anomalies": Array of any unusual spending patterns detected (can be empty)
- "recommendations": Array of 2-3 actionable recommendations to improve finances

Be specific and reference actual numbers when possible.
Only respond with valid JSON, no additional text."""

        messages = [
            {
                'role': 'user',
                'content': f"""Analyze this {period}ly spending breakdown:

Total Spending: ${total_spending:.2f}
Number of Transactions: {len(transactions)}

Spending by Category:
{spending_summary}

Provide insights and recommendations."""
            }
        ]

        response = await self._call_api(
            messages=messages,
            system_prompt=system_prompt,
            model=self.ANALYSIS_MODEL,  # Use more capable model for analysis
            max_tokens=1024,
            temperature=0.5
        )

        # Log usage if user provided
        if user:
            await self._log_usage(user, response, 'analyze')

        # Parse JSON response
        try:
            result = json.loads(response.content)
            # Ensure all expected fields exist
            result.setdefault('summary', '')
            result.setdefault('insights', [])
            result.setdefault('anomalies', [])
            result.setdefault('recommendations', [])
            return result
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis response: {response.content}")
            return {
                'summary': response.content[:200],
                'insights': [],
                'anomalies': [],
                'recommendations': []
            }

    async def generate_recommendations(
        self,
        user_context: dict[str, Any],
        user: Optional[Any] = None
    ) -> list[dict[str, Any]]:
        """
        Generate personalized financial recommendations.

        Args:
            user_context: Dict with user's financial context
                - budget_status: Dict with budget category and percentage used
                - recent_transactions: Recent transaction patterns
                - savings_goal: Optional savings goal info
            user: Optional user for logging

        Returns:
            List of recommendation dicts with 'type', 'title', 'content', 'priority'
        """
        system_prompt = """You are a personal finance advisor assistant.
Generate helpful, actionable recommendations based on the user's financial situation.

Respond in JSON format with an array of recommendations, each having:
- "type": one of "budget_alert", "spending_insight", "saving_tip", "anomaly"
- "title": brief title (max 100 chars)
- "content": detailed recommendation (max 500 chars)
- "priority": 1-5 (5 being most urgent)

Generate 2-5 relevant recommendations.
Only respond with valid JSON array, no additional text."""

        context_str = json.dumps(user_context, indent=2, default=str)

        messages = [
            {
                'role': 'user',
                'content': f"""Based on this financial context, generate personalized recommendations:

{context_str}

Generate relevant and actionable recommendations."""
            }
        ]

        response = await self._call_api(
            messages=messages,
            system_prompt=system_prompt,
            model=self.DEFAULT_MODEL,
            max_tokens=1024,
            temperature=0.6
        )

        # Log usage if user provided
        if user:
            await self._log_usage(user, response, 'recommend')

        # Parse JSON response
        try:
            recommendations = json.loads(response.content)
            if not isinstance(recommendations, list):
                recommendations = [recommendations]

            # Validate each recommendation
            valid_types = ['budget_alert', 'spending_insight', 'saving_tip', 'anomaly']
            validated = []
            for rec in recommendations:
                if isinstance(rec, dict):
                    rec['type'] = rec.get('type', 'spending_insight')
                    if rec['type'] not in valid_types:
                        rec['type'] = 'spending_insight'
                    rec['priority'] = max(1, min(5, int(rec.get('priority', 3))))
                    validated.append(rec)

            return validated

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse recommendations response: {response.content}")
            return []

    async def _log_usage(
        self,
        user: Any,
        response: ClaudeResponse,
        endpoint: str
    ) -> None:
        """
        Log API usage to database.

        Args:
            user: User who made the request
            response: ClaudeResponse from the API
            endpoint: Endpoint type for logging
        """
        try:
            from apps.ai.models import AIUsageLog

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: AIUsageLog.objects.create(
                    user=user,
                    model=response.model,
                    tokens_input=response.tokens_input,
                    tokens_output=response.tokens_output,
                    cost_estimate=response.cost_estimate,
                    endpoint=endpoint,
                    request_id=response.request_id,
                    latency_ms=response.latency_ms,
                    success=True
                )
            )
        except Exception as e:
            logger.error(f"Failed to log AI usage: {e}")


# Synchronous wrapper for non-async contexts
class SyncClaudeClient:
    """
    Synchronous wrapper for ClaudeClient.

    Use this when you need to call Claude from synchronous code
    (e.g., Django views without async support).
    """

    def __init__(self, api_key: Optional[str] = None):
        self._async_client = ClaudeClient(api_key)

    def _run_async(self, coro):
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def chat(self, messages: list[dict], system_prompt: Optional[str] = None, user: Optional[Any] = None) -> ClaudeResponse:
        """Synchronous chat method."""
        return self._run_async(self._async_client.chat(messages, system_prompt, user))

    def categorize(self, description: str, categories: Optional[list[str]] = None, user: Optional[Any] = None) -> dict[str, Any]:
        """Synchronous categorize method."""
        return self._run_async(self._async_client.categorize(description, categories, user))

    def analyze_spending(self, transactions: list[dict], period: str = 'month', user: Optional[Any] = None) -> dict[str, Any]:
        """Synchronous analyze_spending method."""
        return self._run_async(self._async_client.analyze_spending(transactions, period, user))

    def generate_recommendations(self, user_context: dict[str, Any], user: Optional[Any] = None) -> list[dict[str, Any]]:
        """Synchronous generate_recommendations method."""
        return self._run_async(self._async_client.generate_recommendations(user_context, user))
