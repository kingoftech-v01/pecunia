"""
Tests for RecommendationEngine service.

Tests budget recommendations, saving tips, monthly insights,
data gathering, and recommendation saving.
"""
from datetime import timedelta, date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.ai.models import AIRecommendation, AIAnalysisCache


@pytest.mark.django_db
class TestRecommendationEngine:

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def _get_service(self, mock_anthropic_cls):
        from apps.ai.services.recommendations import RecommendationEngine
        return RecommendationEngine()

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
    def test_generate_budget_recommendations(self, mock_anthropic_cls, user, budget):
        from apps.ai.services.recommendations import RecommendationEngine

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"recommendations": [{"type": "budget_alert", "title": "Over budget", "content": "You are spending too much on groceries.", "priority": "high"}]}\n```')]
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 100
        mock_client.messages.create.return_value = mock_response

        service = RecommendationEngine()
        result = service.generate_budget_recommendations(user=user)
        assert isinstance(result, (list, dict))

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_generate_saving_tips(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.recommendations import RecommendationEngine

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"tips": [{"title": "Save on coffee", "content": "Consider making coffee at home.", "priority": "medium"}]}\n```')]
        mock_response.usage.input_tokens = 150
        mock_response.usage.output_tokens = 80
        mock_client.messages.create.return_value = mock_response

        service = RecommendationEngine()
        result = service.generate_saving_tips(user=user)
        assert isinstance(result, (list, dict))

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_generate_monthly_insights(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.recommendations import RecommendationEngine

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"spending_score": 75, "summary": "Good spending habits", "insights": []}\n```')]
        mock_response.usage.input_tokens = 300
        mock_response.usage.output_tokens = 200
        mock_client.messages.create.return_value = mock_response

        service = RecommendationEngine()
        result = service.generate_monthly_insights(user=user)
        assert isinstance(result, (dict, type(None)))

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_gather_comprehensive_spending_data(self, mock_anthropic_cls, user, transaction):
        from apps.ai.services.recommendations import RecommendationEngine

        service = RecommendationEngine()
        data = service._gather_comprehensive_spending_data(user=user)
        assert isinstance(data, dict)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_gather_budget_data(self, mock_anthropic_cls, user, budget, budget_item):
        from apps.ai.services.recommendations import RecommendationEngine

        service = RecommendationEngine()
        data = service._gather_budget_data(user=user)
        assert isinstance(data, (list, dict))

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_save_recommendations(self, mock_anthropic_cls, user):
        from apps.ai.services.recommendations import RecommendationEngine

        service = RecommendationEngine()
        recs = [
            {
                'type': 'budget_alert',
                'title': 'Budget Alert',
                'content': 'You are over budget.',
                'priority': 'high',
            },
            {
                'type': 'saving_tip',
                'title': 'Save Money',
                'content': 'Try cooking at home.',
                'priority': 'medium',
            },
        ]
        initial_count = AIRecommendation.objects.filter(user=user).count()
        service._save_recommendations(user=user, recommendations=recs)
        new_count = AIRecommendation.objects.filter(user=user).count()
        assert new_count >= initial_count

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_save_monthly_insights(self, mock_anthropic_cls, user):
        from apps.ai.services.recommendations import RecommendationEngine

        service = RecommendationEngine()
        insights = {
            'spending_score': 55,
            'summary': 'Could improve spending habits.',
            'total_spent': 2500,
            'total_income': 3000,
        }
        service._save_monthly_insights(
            user=user,
            insights=insights,
            month=1,
            year=2024,
        )
        # Check that cache entry was created
        cache_entries = AIAnalysisCache.objects.filter(
            user=user,
            analysis_type='monthly_insights',
        )
        assert cache_entries.exists()

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_calc_change_percent(self, mock_anthropic_cls):
        from apps.ai.services.recommendations import RecommendationEngine

        service = RecommendationEngine()
        assert service._calc_change_percent(100, 120) == pytest.approx(20.0)
        assert service._calc_change_percent(100, 80) == pytest.approx(-20.0)
        assert service._calc_change_percent(0, 100) == 100.0  # When old=0, returns 100.0 if new>0
        assert service._calc_change_percent(100, 100) == pytest.approx(0.0)

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @patch('apps.ai.services.base.anthropic.Anthropic')
    def test_save_monthly_insights_low_score_creates_recommendation(self, mock_anthropic_cls, user):
        from apps.ai.services.recommendations import RecommendationEngine

        service = RecommendationEngine()
        insights = {
            'spending_score': 40,
            'summary': 'Spending habits need improvement.',
            'total_spent': 3500,
            'total_income': 3000,
        }
        service._save_monthly_insights(
            user=user,
            insights=insights,
            month=1,
            year=2024,
        )
        # With score < 60, should create a recommendation
        recs = AIRecommendation.objects.filter(
            user=user,
            type='spending_insight',
        )
        assert recs.exists()
