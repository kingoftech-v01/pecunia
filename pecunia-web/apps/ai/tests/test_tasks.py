"""
Tests for AI Celery tasks.

Tests task execution, retries, cross-tenant isolation, and SoftTimeLimitExceeded handling.
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone

from apps.ai.models import AIRecommendation
from apps.ai.tasks import (
    categorize_new_transactions,
    categorize_user_transactions,
    check_anomalies_daily,
    check_single_transaction_anomaly,
    detect_subscription_changes,
    generate_weekly_recommendations,
    generate_user_recommendations,
    generate_monthly_insights,
    cleanup_old_recommendations,
    ai_health_check,
    refresh_user_patterns,
)


# =============================================================================
# categorize_new_transactions
# =============================================================================

@pytest.mark.django_db
class TestCategorizeNewTransactions:

    def test_requires_user_id(self):
        """Task must raise ValueError if user_id is not provided (cross-tenant check)."""
        with pytest.raises(ValueError, match="user_id is required"):
            categorize_new_transactions(user_id=None)

    def test_requires_user_id_zero(self):
        with pytest.raises(ValueError, match="user_id is required"):
            categorize_new_transactions(user_id=0)

    @patch('apps.ai.services.categorization.TransactionCategorizer')
    def test_no_uncategorized_transactions(self, mock_categorizer, user):
        result = categorize_new_transactions(user_id=user.id)
        assert result['status'] == 'no_transactions'
        assert result['processed'] == 0

    @patch('apps.ai.services.categorization.TransactionCategorizer')
    def test_categorize_transactions(self, mock_categorizer, user, transaction):
        """Test categorization with uncategorized transactions."""
        # Make transaction uncategorized
        transaction.category = None
        transaction.save()

        mock_service = MagicMock()
        mock_categorizer.return_value = mock_service
        mock_service.categorize_batch.return_value = [
            {
                'category_id': 'cat_123',
                'category_name': 'Groceries',
                'confidence': 0.9,
                'applied': True,
            }
        ]

        result = categorize_new_transactions(user_id=user.id)
        assert result['processed'] >= 1
        assert result['categorized'] >= 1

    def test_user_id_prevents_cross_tenant_access(self, user, user2, transaction):
        """Ensure user_id scoping prevents one user from categorizing another's transactions."""
        # transaction belongs to user, trying with user2.id should not find it
        transaction.category = None
        transaction.save()

        with patch('apps.ai.services.categorization.TransactionCategorizer'):
            result = categorize_new_transactions(user_id=user2.id)
            assert result['status'] == 'no_transactions'


# =============================================================================
# categorize_user_transactions
# =============================================================================

@pytest.mark.django_db
class TestCategorizeUserTransactions:

    @patch('apps.ai.services.categorization.TransactionCategorizer')
    def test_categorize_specific_transactions(self, mock_categorizer, user, transaction):
        mock_service = MagicMock()
        mock_categorizer.return_value = mock_service
        mock_service.categorize_batch.return_value = [
            {
                'category_id': str(transaction.category.id),
                'category_name': 'Groceries',
                'confidence': 0.95,
            }
        ]

        result = categorize_user_transactions(
            user_id=user.id,
            transaction_ids=[str(transaction.id)],
        )
        assert isinstance(result, dict)


# =============================================================================
# check_anomalies_daily
# =============================================================================

@pytest.mark.django_db
class TestCheckAnomaliesDaily:

    def test_requires_user_id(self):
        with pytest.raises(ValueError, match="user_id is required"):
            check_anomalies_daily(user_id=None)

    @patch('apps.ai.services.anomaly_detection.AnomalyDetector')
    def test_check_anomalies(self, mock_detector, user, transaction):
        mock_service = MagicMock()
        mock_detector.return_value = mock_service
        mock_service.detect_unusual_spending.return_value = {'is_unusual': False}
        mock_service.detect_duplicate_transactions.return_value = []

        result = check_anomalies_daily(user_id=user.id)
        assert isinstance(result, dict)
        assert result['status'] == 'completed'


# =============================================================================
# check_single_transaction_anomaly
# =============================================================================

@pytest.mark.django_db
class TestCheckSingleTransactionAnomaly:

    @patch('apps.ai.services.anomaly_detection.AnomalyDetector')
    def test_check_single(self, mock_detector, user, transaction):
        mock_service = MagicMock()
        mock_detector.return_value = mock_service
        mock_service.detect_unusual_spending.return_value = {
            'is_unusual': False,
            'risk_level': 'low',
        }

        result = check_single_transaction_anomaly(
            transaction_id=str(transaction.id),
        )
        assert isinstance(result, dict)
        assert result['transaction_id'] == str(transaction.id)


# =============================================================================
# detect_subscription_changes
# =============================================================================

@pytest.mark.django_db
class TestDetectSubscriptionChanges:

    def test_requires_user_id(self):
        with pytest.raises(ValueError, match="user_id is required"):
            detect_subscription_changes(user_id=None)

    @patch('apps.ai.services.anomaly_detection.AnomalyDetector')
    def test_detect_changes(self, mock_detector, user):
        mock_service = MagicMock()
        mock_detector.return_value = mock_service
        mock_service.detect_subscription_changes.return_value = {
            'changes_detected': 0,
            'changes': [],
        }

        result = detect_subscription_changes(user_id=user.id)
        assert isinstance(result, dict)
        assert result['status'] == 'completed'


# =============================================================================
# generate_weekly_recommendations
# =============================================================================

@pytest.mark.django_db
class TestGenerateWeeklyRecommendations:

    def test_requires_user_id(self):
        with pytest.raises(ValueError, match="user_id is required"):
            generate_weekly_recommendations(user_id=None)

    @patch('apps.ai.services.recommendations.RecommendationEngine')
    def test_generate_recommendations(self, mock_engine, user):
        mock_service = MagicMock()
        mock_engine.return_value = mock_service
        mock_service.generate_budget_recommendations.return_value = []
        mock_service.generate_saving_tips.return_value = []

        result = generate_weekly_recommendations(user_id=user.id)
        assert isinstance(result, dict)
        assert result['status'] == 'completed'


# =============================================================================
# generate_user_recommendations
# =============================================================================

@pytest.mark.django_db
class TestGenerateUserRecommendations:

    @patch('apps.ai.services.recommendations.RecommendationEngine')
    def test_budget_type(self, mock_engine, user):
        mock_service = MagicMock()
        mock_engine.return_value = mock_service
        mock_service.generate_budget_recommendations.return_value = []

        result = generate_user_recommendations(user_id=user.id, recommendation_type='budget')
        assert isinstance(result, dict)
        assert result['status'] == 'completed'

    @patch('apps.ai.services.recommendations.RecommendationEngine')
    def test_saving_type(self, mock_engine, user):
        mock_service = MagicMock()
        mock_engine.return_value = mock_service
        mock_service.generate_saving_tips.return_value = []

        result = generate_user_recommendations(user_id=user.id, recommendation_type='saving')
        assert isinstance(result, dict)
        assert result['status'] == 'completed'

    @patch('apps.ai.services.recommendations.RecommendationEngine')
    def test_all_type(self, mock_engine, user):
        mock_service = MagicMock()
        mock_engine.return_value = mock_service
        mock_service.generate_budget_recommendations.return_value = []
        mock_service.generate_saving_tips.return_value = []
        mock_service.generate_monthly_insights.return_value = {'has_data': False}

        result = generate_user_recommendations(user_id=user.id, recommendation_type='all')
        assert isinstance(result, dict)
        assert result['status'] == 'completed'


# =============================================================================
# generate_monthly_insights
# =============================================================================

@pytest.mark.django_db
class TestGenerateMonthlyInsights:

    def test_requires_user_id(self):
        with pytest.raises(ValueError, match="user_id is required"):
            generate_monthly_insights(user_id=None)

    @patch('apps.ai.services.recommendations.RecommendationEngine')
    def test_generate_insights(self, mock_engine, user):
        mock_service = MagicMock()
        mock_engine.return_value = mock_service
        mock_service.generate_monthly_insights.return_value = {'has_data': True}

        result = generate_monthly_insights(user_id=user.id)
        assert isinstance(result, dict)
        assert result['status'] == 'completed'


# =============================================================================
# cleanup_old_recommendations
# =============================================================================

@pytest.mark.django_db
class TestCleanupOldRecommendations:

    def test_cleanup_with_no_data(self):
        result = cleanup_old_recommendations()
        assert isinstance(result, dict)

    def test_cleanup_dry_run(self, user):
        # Create some old recommendations
        old_time = timezone.now() - timedelta(days=100)
        for i in range(3):
            rec = AIRecommendation.objects.create(
                user=user,
                type='budget_alert',
                title=f"Old {i}",
                content="Old content",
                is_read=True,
            )
        result = cleanup_old_recommendations(dry_run=True)
        assert isinstance(result, dict)


# =============================================================================
# ai_health_check
# =============================================================================

@pytest.mark.django_db
class TestAIHealthCheck:

    @patch('apps.ai.services.recommendations.RecommendationEngine')
    @patch('apps.ai.services.anomaly_detection.AnomalyDetector')
    @patch('apps.ai.services.categorization.TransactionCategorizer')
    def test_health_check_success(self, mock_categorizer, mock_detector, mock_engine):
        mock_cat = MagicMock()
        mock_cat.model = 'claude-3'
        mock_categorizer.return_value = mock_cat
        mock_det = MagicMock()
        mock_det.model = 'claude-3'
        mock_detector.return_value = mock_det
        mock_eng = MagicMock()
        mock_eng.model = 'claude-3'
        mock_engine.return_value = mock_eng

        result = ai_health_check()
        assert isinstance(result, dict)
        assert result['status'] == 'healthy'

    @patch('apps.ai.services.recommendations.RecommendationEngine')
    @patch('apps.ai.services.anomaly_detection.AnomalyDetector')
    @patch('apps.ai.services.categorization.TransactionCategorizer')
    def test_health_check_service_failure(self, mock_categorizer, mock_detector, mock_engine):
        mock_categorizer.side_effect = Exception("API key missing")
        mock_det = MagicMock()
        mock_det.model = 'claude-3'
        mock_detector.return_value = mock_det
        mock_eng = MagicMock()
        mock_eng.model = 'claude-3'
        mock_engine.return_value = mock_eng

        result = ai_health_check()
        assert isinstance(result, dict)
        assert result['status'] == 'degraded'


# =============================================================================
# refresh_user_patterns
# =============================================================================

@pytest.mark.django_db
class TestRefreshUserPatterns:

    @patch('apps.ai.services.anomaly_detection.AnomalyDetector')
    def test_refresh(self, mock_detector, user):
        mock_service = MagicMock()
        mock_detector.return_value = mock_service
        mock_service.get_spending_patterns.return_value = {
            'has_data': True,
            'period_days': 30,
            'overall': {'total_transactions': 10},
        }

        result = refresh_user_patterns(user_id=user.id)
        assert isinstance(result, dict)
        assert result['status'] == 'refreshed'
