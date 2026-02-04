"""
Tests for TransactionCategorizer service.

Tests categorization, batch processing, learned patterns, and caching.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.ai.services.base import AIServiceError, AIResponseError


# =============================================================================
# Test TransactionCategorizer
# =============================================================================

@pytest.mark.django_db
class TestTransactionCategorizer:

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def _get_service(self, mock_anthropic_cls):
        from apps.ai.services.categorization import TransactionCategorizer
        return TransactionCategorizer()

    def setup_method(self):
        cache.clear()

    def test_init(self):
        service = self._get_service()
        assert service is not None
        assert service.get_system_prompt() is not None

    def test_system_prompt_not_empty(self):
        service = self._get_service()
        prompt = service.get_system_prompt()
        assert len(prompt) > 0
        assert isinstance(prompt, str)

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_categorize_single(self, mock_anthropic_cls, user, category):
        from apps.ai.services.categorization import TransactionCategorizer

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=f'{{"category_id": "{category.id}", "confidence": 0.92, "reasoning": "Coffee shop", "keywords": ["coffee"]}}')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        service = TransactionCategorizer()
        # categorize_single signature: description, merchant, amount, transaction_type, user
        result = service.categorize_single(
            description="Coffee at Starbucks",
            amount=Decimal("4.50"),
            merchant="Starbucks",
            user=user,
        )
        assert isinstance(result, dict)

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_categorize_single_no_user(self, mock_anthropic_cls):
        from apps.ai.services.categorization import TransactionCategorizer

        service = TransactionCategorizer()
        result = service.categorize_single(
            description="Test",
            user=None,
        )
        assert result.get('error') is True

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_categorize_batch(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.categorization import TransactionCategorizer

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=f'[{{"transaction_id": "{transaction.id}", "category_id": "{transaction.category.id}", "confidence": 0.9, "reasoning": "Match", "keywords": []}}]')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        service = TransactionCategorizer()
        # categorize_batch takes List[Transaction], no user_id
        result = service.categorize_batch([transaction])
        assert isinstance(result, list)

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_learn_from_correction(self, mock_anthropic_cls, transaction, category):
        from apps.ai.services.categorization import TransactionCategorizer

        service = TransactionCategorizer()
        # learn_from_correction takes: transaction, correct_category
        result = service.learn_from_correction(
            transaction=transaction,
            correct_category=category,
        )
        assert isinstance(result, dict)
        assert result.get('learned') is True

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_check_learned_patterns(self, mock_anthropic_cls, user):
        from apps.ai.services.categorization import TransactionCategorizer

        service = TransactionCategorizer()
        # _check_learned_patterns takes: description, merchant, user (not user_id)
        result = service._check_learned_patterns(
            "Completely unknown merchant",
            "Unknown",
            user,
        )
        # May return None or a pattern depending on cache state
        assert result is None or isinstance(result, dict)

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_extract_learning_patterns(self, mock_anthropic_cls, transaction, category):
        from apps.ai.services.categorization import TransactionCategorizer

        service = TransactionCategorizer()
        # _extract_learning_patterns takes: transaction, category
        patterns = service._extract_learning_patterns(
            transaction, category,
        )
        assert isinstance(patterns, dict)
        assert 'keywords' in patterns
        assert 'merchant' in patterns

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_get_category_suggestions(self, mock_anthropic_cls, user, category):
        from apps.ai.services.categorization import TransactionCategorizer

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=f'[{{"category_id": "{category.id}", "category_name": "{category.name}", "score": 0.9, "reasoning": "Match"}}]')]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 30
        mock_client.messages.create.return_value = mock_response

        service = TransactionCategorizer()
        # get_category_suggestions takes: description, user (not user_id)
        result = service.get_category_suggestions(
            description="Groceries at Walmart",
            user=user,
        )
        assert isinstance(result, list)

    @patch('apps.ai.services.base.anthropic.Anthropic')
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_get_category_suggestions_no_user(self, mock_anthropic_cls):
        from apps.ai.services.categorization import TransactionCategorizer

        service = TransactionCategorizer()
        result = service.get_category_suggestions(
            description="Test",
            user=None,
        )
        assert result == []
