"""
Tests for AI serializers.

Tests validation, field mapping, and edge cases.
"""
import uuid
from datetime import date

import pytest
from django.utils import timezone

from apps.ai.serializers import (
    AIRecommendationSerializer,
    AIRecommendationListSerializer,
    AIRecommendationActionSerializer,
    ChatMessageSerializer,
    ChatRequestSerializer,
    CategorizeRequestSerializer,
    CategorizeResponseSerializer,
    BulkCategorizeRequestSerializer,
    InsightsSerializer,
    InsightsResponseSerializer,
)
from apps.ai.models import AIRecommendation


@pytest.mark.django_db
class TestAIRecommendationSerializer:

    def test_serialize_recommendation(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type='budget_alert',
            title="Budget Alert",
            content="Test content",
            priority=3,
        )
        serializer = AIRecommendationSerializer(rec)
        data = serializer.data
        assert data['type'] == 'budget_alert'
        assert data['title'] == "Budget Alert"
        assert data['content'] == "Test content"
        assert data['priority'] == 3
        assert data['is_read'] is False
        assert data['is_dismissed'] is False
        assert 'time_ago' in data
        assert 'type_display' in data

    def test_time_ago_field(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type='spending_insight',
            title="Test",
            content="Test",
        )
        serializer = AIRecommendationSerializer(rec)
        # time_ago should be a string like "0 minutes"
        assert isinstance(serializer.data['time_ago'], str)


@pytest.mark.django_db
class TestAIRecommendationListSerializer:

    def test_list_serializer_fields(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type='saving_tip',
            title="Save Money",
            content="Detailed content here",
            priority=2,
        )
        serializer = AIRecommendationListSerializer(rec)
        data = serializer.data
        assert 'id' in data
        assert 'type' in data
        assert 'title' in data
        assert 'priority' in data
        assert 'is_read' in data
        # List serializer should not have 'content'
        assert 'content' not in data


class TestAIRecommendationActionSerializer:

    def test_valid_mark_read(self):
        serializer = AIRecommendationActionSerializer(data={'action': 'mark_read'})
        assert serializer.is_valid()

    def test_valid_dismiss(self):
        serializer = AIRecommendationActionSerializer(data={'action': 'dismiss'})
        assert serializer.is_valid()

    def test_invalid_action(self):
        serializer = AIRecommendationActionSerializer(data={'action': 'delete'})
        assert not serializer.is_valid()

    def test_missing_action(self):
        serializer = AIRecommendationActionSerializer(data={})
        assert not serializer.is_valid()


class TestChatMessageSerializer:

    def test_valid_user_message(self):
        serializer = ChatMessageSerializer(data={'role': 'user', 'content': 'Hello'})
        assert serializer.is_valid()
        assert serializer.validated_data['content'] == 'Hello'

    def test_valid_assistant_message(self):
        serializer = ChatMessageSerializer(data={'role': 'assistant', 'content': 'Hi'})
        assert serializer.is_valid()

    def test_invalid_role(self):
        serializer = ChatMessageSerializer(data={'role': 'system', 'content': 'test'})
        assert not serializer.is_valid()
        assert 'role' in serializer.errors

    def test_empty_content(self):
        serializer = ChatMessageSerializer(data={'role': 'user', 'content': '   '})
        assert not serializer.is_valid()
        assert 'content' in serializer.errors

    def test_content_stripped(self):
        serializer = ChatMessageSerializer(data={'role': 'user', 'content': '  Hello  '})
        assert serializer.is_valid()
        assert serializer.validated_data['content'] == 'Hello'


class TestChatRequestSerializer:

    def test_valid_request(self):
        serializer = ChatRequestSerializer(data={'message': 'Hello'})
        assert serializer.is_valid()
        assert serializer.validated_data['context_type'] == 'general'
        assert serializer.validated_data['include_history'] is True

    def test_with_context_type(self):
        serializer = ChatRequestSerializer(data={
            'message': 'Analyze my spending',
            'context_type': 'transactions',
        })
        assert serializer.is_valid()
        assert serializer.validated_data['context_type'] == 'transactions'

    def test_invalid_context_type(self):
        serializer = ChatRequestSerializer(data={
            'message': 'Test',
            'context_type': 'invalid',
        })
        assert not serializer.is_valid()

    def test_empty_message(self):
        serializer = ChatRequestSerializer(data={'message': '   '})
        assert not serializer.is_valid()

    def test_with_session_id(self):
        sid = uuid.uuid4()
        serializer = ChatRequestSerializer(data={
            'message': 'Hello',
            'session_id': str(sid),
        })
        assert serializer.is_valid()
        assert serializer.validated_data['session_id'] == sid

    def test_all_context_types(self):
        for ctx_type in ['general', 'transactions', 'budgets', 'savings', 'investments']:
            serializer = ChatRequestSerializer(data={
                'message': 'Test',
                'context_type': ctx_type,
            })
            assert serializer.is_valid(), f"Should accept context_type={ctx_type}"


class TestCategorizeRequestSerializer:

    def test_valid_with_transaction_id(self):
        serializer = CategorizeRequestSerializer(data={
            'transaction_id': str(uuid.uuid4()),
        })
        assert serializer.is_valid()

    def test_valid_with_description(self):
        serializer = CategorizeRequestSerializer(data={
            'description': 'Coffee at Starbucks',
        })
        assert serializer.is_valid()

    def test_valid_with_both(self):
        serializer = CategorizeRequestSerializer(data={
            'transaction_id': str(uuid.uuid4()),
            'description': 'Coffee',
        })
        assert serializer.is_valid()

    def test_invalid_without_either(self):
        serializer = CategorizeRequestSerializer(data={})
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_with_optional_fields(self):
        serializer = CategorizeRequestSerializer(data={
            'description': 'Coffee',
            'amount': '4.50',
            'merchant': 'Starbucks',
            'include_confidence': True,
            'include_alternatives': True,
        })
        assert serializer.is_valid()
        assert serializer.validated_data['amount'] == pytest.approx(4.50, abs=0.01)


class TestBulkCategorizeRequestSerializer:

    def test_valid_request(self):
        ids = [str(uuid.uuid4()) for _ in range(3)]
        serializer = BulkCategorizeRequestSerializer(data={
            'transaction_ids': ids,
        })
        assert serializer.is_valid()
        assert serializer.validated_data['auto_apply'] is False
        assert serializer.validated_data['confidence_threshold'] == 0.85

    def test_empty_list(self):
        serializer = BulkCategorizeRequestSerializer(data={
            'transaction_ids': [],
        })
        assert not serializer.is_valid()

    def test_too_many_ids(self):
        ids = [str(uuid.uuid4()) for _ in range(51)]
        serializer = BulkCategorizeRequestSerializer(data={
            'transaction_ids': ids,
        })
        assert not serializer.is_valid()

    def test_with_auto_apply(self):
        serializer = BulkCategorizeRequestSerializer(data={
            'transaction_ids': [str(uuid.uuid4())],
            'auto_apply': True,
            'confidence_threshold': 0.9,
        })
        assert serializer.is_valid()
        assert serializer.validated_data['auto_apply'] is True
        assert serializer.validated_data['confidence_threshold'] == 0.9

    def test_confidence_threshold_bounds(self):
        # Below minimum
        serializer = BulkCategorizeRequestSerializer(data={
            'transaction_ids': [str(uuid.uuid4())],
            'confidence_threshold': 0.3,
        })
        assert not serializer.is_valid()

        # Above maximum
        serializer = BulkCategorizeRequestSerializer(data={
            'transaction_ids': [str(uuid.uuid4())],
            'confidence_threshold': 1.1,
        })
        assert not serializer.is_valid()


class TestInsightsSerializer:

    def test_valid_default(self):
        serializer = InsightsSerializer(data={})
        assert serializer.is_valid()
        assert serializer.validated_data['period'] == 'month'

    def test_valid_week(self):
        serializer = InsightsSerializer(data={'period': 'week'})
        assert serializer.is_valid()

    def test_custom_requires_dates(self):
        serializer = InsightsSerializer(data={'period': 'custom'})
        assert not serializer.is_valid()

    def test_custom_with_dates(self):
        serializer = InsightsSerializer(data={
            'period': 'custom',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        assert serializer.is_valid()

    def test_custom_start_after_end(self):
        serializer = InsightsSerializer(data={
            'period': 'custom',
            'start_date': '2024-02-01',
            'end_date': '2024-01-01',
        })
        assert not serializer.is_valid()

    def test_all_periods(self):
        for period in ['week', 'month', 'quarter', 'year']:
            serializer = InsightsSerializer(data={'period': period})
            assert serializer.is_valid(), f"Should accept period={period}"

    def test_with_insight_types(self):
        serializer = InsightsSerializer(data={
            'period': 'month',
            'insight_types': ['spending_summary', 'anomalies'],
        })
        assert serializer.is_valid()

    def test_invalid_insight_type(self):
        serializer = InsightsSerializer(data={
            'period': 'month',
            'insight_types': ['invalid_type'],
        })
        assert not serializer.is_valid()
