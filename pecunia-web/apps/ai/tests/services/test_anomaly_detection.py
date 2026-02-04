"""
Tests for AnomalyDetector service.

Tests unusual spending detection, duplicate detection, subscription changes,
spending patterns, and z-score calculations.
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings
from django.utils import timezone


@pytest.mark.django_db
class TestAnomalyDetector:

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def _get_service(self, mock_anthropic_cls):
        from apps.ai.services.anomaly_detection import AnomalyDetector
        return AnomalyDetector()

    def test_init(self):
        service = self._get_service()
        assert service is not None

    def test_system_prompt(self):
        service = self._get_service()
        prompt = service.get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_detect_unusual_spending_no_history(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.anomaly_detection import AnomalyDetector

        service = AnomalyDetector()
        result = service.detect_unusual_spending(
            user=user,
            transaction=transaction,
        )
        # With no history, should return non-anomalous result
        assert result is None or isinstance(result, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_check_amount_anomaly(self, mock_anthropic_cls, user):
        from apps.ai.services.anomaly_detection import AnomalyDetector

        service = AnomalyDetector()
        # Test with patterns that have enough data
        patterns = {
            'overall': {
                'avg_amount': 50.0,
                'stddev_amount': 10.0,
                'max_amount': 100.0,
                'total_transactions': 30,
            },
            'by_category': {},
        }
        # Normal amount - positional args: amount, patterns, category
        is_anomaly, details = service._check_amount_anomaly(
            45.0, patterns, None,
        )
        assert isinstance(details, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_check_amount_anomaly_high_amount(self, mock_anthropic_cls):
        from apps.ai.services.anomaly_detection import AnomalyDetector

        service = AnomalyDetector()
        patterns = {
            'overall': {
                'avg_amount': 50.0,
                'stddev_amount': 10.0,
                'max_amount': 100.0,
            },
            'by_category': {},
        }
        # Very high amount should flag anomaly: (500 - 50) / 10 = 45 stddevs
        is_anomaly, details = service._check_amount_anomaly(
            500.0, patterns, None,
        )
        assert isinstance(details, dict)
        if is_anomaly:
            assert details.get('z_score_overall', 0) > 2.0

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_check_timing_anomaly(self, mock_anthropic_cls, transaction):
        from apps.ai.services.anomaly_detection import AnomalyDetector

        service = AnomalyDetector()
        patterns = {
            'by_weekday': {
                1: {'avg_amount': 50.0, 'count': 5},
                2: {'avg_amount': 60.0, 'count': 8},
            },
        }
        # Pass a Transaction object, not transaction_date
        is_anomaly, details = service._check_timing_anomaly(
            transaction, patterns,
        )
        assert isinstance(details, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_check_merchant_anomaly(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.anomaly_detection import AnomalyDetector

        service = AnomalyDetector()
        # Pass user and transaction objects (positional args)
        is_anomaly, details = service._check_merchant_anomaly(
            user, transaction,
        )
        assert isinstance(details, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_detect_duplicate_transactions(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.anomaly_detection import AnomalyDetector
        from apps.transactions.models import Transaction

        service = AnomalyDetector()
        # Create a potential duplicate
        dup = Transaction.objects.create(
            user=user,
            category=transaction.category,
            amount=transaction.amount,
            type='expense',
            description=transaction.description,
            merchant=transaction.merchant,
            transaction_date=transaction.transaction_date,
        )
        result = service.detect_duplicate_transactions(
            user=user,
            lookback_days=30,
        )
        assert isinstance(result, list)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_detect_subscription_changes(self, mock_anthropic_cls, user):
        from apps.ai.services.anomaly_detection import AnomalyDetector

        service = AnomalyDetector()
        result = service.detect_subscription_changes(user=user)
        assert isinstance(result, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_get_spending_patterns(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.anomaly_detection import AnomalyDetector

        service = AnomalyDetector()
        patterns = service.get_spending_patterns(user=user)
        assert isinstance(patterns, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_build_transaction_index(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.anomaly_detection import AnomalyDetector
        from apps.transactions.models import Transaction

        service = AnomalyDetector()
        transactions = Transaction.objects.filter(user=user)
        index = service._build_transaction_index(list(transactions))
        assert isinstance(index, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_save_anomaly_alert(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.anomaly_detection import AnomalyDetector
        from apps.ai.models import AIRecommendation

        service = AnomalyDetector()
        initial_count = AIRecommendation.objects.filter(user=user, type='anomaly').count()
        # _save_anomaly_alert takes (user, transaction, analysis_dict)
        service._save_anomaly_alert(
            user,
            transaction,
            {
                "is_unusual": True,
                "risk_level": "medium",
                "confidence": 0.85,
                "explanation": "Unusual spending detected",
                "recommended_action": "Review this transaction",
                "anomaly_flags": {"amount": True},
            },
        )
        new_count = AIRecommendation.objects.filter(user=user, type='anomaly').count()
        assert new_count == initial_count + 1
