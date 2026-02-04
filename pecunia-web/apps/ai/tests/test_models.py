"""
Tests for AI models.

Tests all model methods, properties, and edge cases.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.ai.models import (
    AIRecommendation,
    AICategorizationLog,
    AIAnalysisCache,
    AIConversation,
    AIUsageLog,
    ChatSession,
    ChatMessage,
)


# =============================================================================
# AIRecommendation Tests
# =============================================================================

@pytest.mark.django_db
class TestAIRecommendation:

    def test_create_recommendation(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type=AIRecommendation.RecommendationType.BUDGET_ALERT,
            title="Budget Alert",
            content="You are over budget.",
            priority=3,
        )
        assert rec.pk is not None
        assert rec.type == 'budget_alert'
        assert rec.is_read is False
        assert rec.is_dismissed is False
        assert rec.is_actionable is True
        assert str(rec) == "Budget Alert (budget_alert)"

    def test_recommendation_types(self, user):
        for choice_val, _ in AIRecommendation.RecommendationType.choices:
            rec = AIRecommendation.objects.create(
                user=user,
                type=choice_val,
                title=f"Test {choice_val}",
                content="Test content",
            )
            assert rec.type == choice_val

    def test_mark_as_read(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type='budget_alert',
            title="Test",
            content="Test",
        )
        assert rec.is_read is False
        rec.mark_as_read()
        rec.refresh_from_db()
        assert rec.is_read is True

    def test_mark_as_read_idempotent(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type='budget_alert',
            title="Test",
            content="Test",
            is_read=True,
        )
        # Should not error when already read
        rec.mark_as_read()
        rec.refresh_from_db()
        assert rec.is_read is True

    def test_dismiss(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type='spending_insight',
            title="Test",
            content="Test",
        )
        assert rec.is_dismissed is False
        rec.dismiss()
        rec.refresh_from_db()
        assert rec.is_dismissed is True

    def test_normalize_priority_string(self):
        assert AIRecommendation.normalize_priority('low') == 1
        assert AIRecommendation.normalize_priority('medium') == 2
        assert AIRecommendation.normalize_priority('high') == 3
        assert AIRecommendation.normalize_priority('urgent') == 4
        assert AIRecommendation.normalize_priority('critical') == 5

    def test_normalize_priority_string_case_insensitive(self):
        assert AIRecommendation.normalize_priority('LOW') == 1
        assert AIRecommendation.normalize_priority('High') == 3

    def test_normalize_priority_integer(self):
        assert AIRecommendation.normalize_priority(1) == 1
        assert AIRecommendation.normalize_priority(5) == 5

    def test_normalize_priority_invalid_string(self):
        assert AIRecommendation.normalize_priority('unknown') == 3

    def test_normalize_priority_out_of_range_int(self):
        assert AIRecommendation.normalize_priority(0) == 3
        assert AIRecommendation.normalize_priority(6) == 3

    def test_normalize_priority_non_string_non_int(self):
        assert AIRecommendation.normalize_priority(3.5) == 3
        assert AIRecommendation.normalize_priority(None) == 3

    def test_priority_map(self):
        assert AIRecommendation.PRIORITY_MAP == {
            'low': 1,
            'medium': 2,
            'high': 3,
            'urgent': 4,
            'critical': 5,
        }

    def test_recommendation_with_metadata(self, user):
        rec = AIRecommendation.objects.create(
            user=user,
            type='anomaly',
            title="Anomaly Detected",
            content="Unusual spending pattern",
            metadata={'category': 'groceries', 'amount': 500},
            confidence_score=0.95,
        )
        assert rec.metadata == {'category': 'groceries', 'amount': 500}
        assert rec.confidence_score == 0.95

    def test_recommendation_with_related_entities(self, user, transaction, category):
        rec = AIRecommendation.objects.create(
            user=user,
            type='spending_insight',
            title="Test",
            content="Test",
            related_transaction=transaction,
            related_category=category,
        )
        assert rec.related_transaction == transaction
        assert rec.related_category == category

    def test_recommendation_ordering(self, user):
        rec1 = AIRecommendation.objects.create(
            user=user, type='budget_alert', title="First", content="A"
        )
        rec2 = AIRecommendation.objects.create(
            user=user, type='budget_alert', title="Second", content="B"
        )
        recs = list(AIRecommendation.objects.filter(user=user))
        # Ordering is -created_at, so newest first
        assert recs[0] == rec2
        assert recs[1] == rec1

    def test_recommendation_with_expires_at(self, user):
        expires = timezone.now() + timedelta(days=7)
        rec = AIRecommendation.objects.create(
            user=user,
            type='saving_tip',
            title="Test",
            content="Test",
            expires_at=expires,
        )
        assert rec.expires_at is not None


# =============================================================================
# AICategorizationLog Tests
# =============================================================================

@pytest.mark.django_db
class TestAICategorizationLog:

    def test_create_log(self, user, transaction, category):
        log = AICategorizationLog.objects.create(
            user=user,
            transaction=transaction,
            suggested_category=category,
            confidence_score=0.92,
            reasoning="Grocery merchant detected",
        )
        assert log.pk is not None
        assert log.confidence_score == 0.92
        assert log.was_accepted is None
        assert "0.92" in str(log)

    def test_log_with_feedback(self, user, transaction, category):
        log = AICategorizationLog.objects.create(
            user=user,
            transaction=transaction,
            suggested_category=category,
            confidence_score=0.85,
            was_accepted=True,
            actual_category=category,
        )
        assert log.was_accepted is True
        assert log.actual_category == category

    def test_log_rejected(self, user, transaction, category):
        other_cat = category  # Simplified for test
        log = AICategorizationLog.objects.create(
            user=user,
            transaction=transaction,
            suggested_category=category,
            confidence_score=0.60,
            was_accepted=False,
            actual_category=other_cat,
        )
        assert log.was_accepted is False

    def test_log_with_raw_response(self, user, transaction, category):
        log = AICategorizationLog.objects.create(
            user=user,
            transaction=transaction,
            suggested_category=category,
            confidence_score=0.88,
            raw_response={'model': 'claude', 'tokens': 150},
            processing_time_ms=250,
        )
        assert log.raw_response == {'model': 'claude', 'tokens': 150}
        assert log.processing_time_ms == 250


# =============================================================================
# AIAnalysisCache Tests
# =============================================================================

@pytest.mark.django_db
class TestAIAnalysisCache:

    def test_create_cache_entry(self, user):
        cache = AIAnalysisCache.objects.create(
            user=user,
            analysis_type='spending',
            cache_key='2024-01',
            result={'total': 1500},
            expires_at=timezone.now() + timedelta(hours=24),
        )
        assert cache.pk is not None
        assert cache.result == {'total': 1500}
        assert str(cache) == "spending: 2024-01"

    def test_is_expired_false(self, user):
        cache = AIAnalysisCache.objects.create(
            user=user,
            analysis_type='spending',
            cache_key='test',
            result={},
            expires_at=timezone.now() + timedelta(hours=1),
        )
        assert cache.is_expired is False

    def test_is_expired_true(self, user):
        cache = AIAnalysisCache.objects.create(
            user=user,
            analysis_type='spending',
            cache_key='test',
            result={},
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert cache.is_expired is True

    def test_unique_together(self, user):
        AIAnalysisCache.objects.create(
            user=user,
            analysis_type='spending',
            cache_key='2024-01',
            result={'a': 1},
            expires_at=timezone.now() + timedelta(hours=1),
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            AIAnalysisCache.objects.create(
                user=user,
                analysis_type='spending',
                cache_key='2024-01',
                result={'b': 2},
                expires_at=timezone.now() + timedelta(hours=1),
            )


# =============================================================================
# AIConversation Tests
# =============================================================================

@pytest.mark.django_db
class TestAIConversation:

    def test_create_conversation(self, user):
        conv = AIConversation.objects.create(
            user=user,
            title="Test Chat",
        )
        assert conv.pk is not None
        assert conv.messages == []
        assert conv.context == {}
        assert conv.is_active is True
        assert "Conversation" in str(conv)

    def test_add_message(self, user):
        conv = AIConversation.objects.create(user=user)
        conv.add_message('user', 'Hello')
        conv.refresh_from_db()
        assert len(conv.messages) == 1
        assert conv.messages[0]['role'] == 'user'
        assert conv.messages[0]['content'] == 'Hello'
        assert 'timestamp' in conv.messages[0]

    def test_add_multiple_messages(self, user):
        conv = AIConversation.objects.create(user=user)
        conv.add_message('user', 'Hello')
        conv.add_message('assistant', 'Hi there!')
        conv.add_message('user', 'How are you?')
        conv.refresh_from_db()
        assert len(conv.messages) == 3
        assert conv.messages[0]['role'] == 'user'
        assert conv.messages[1]['role'] == 'assistant'
        assert conv.messages[2]['role'] == 'user'

    def test_get_messages_for_api(self, user):
        conv = AIConversation.objects.create(user=user)
        conv.add_message('user', 'Hello')
        conv.add_message('assistant', 'Hi!')
        api_msgs = conv.get_messages_for_api()
        assert len(api_msgs) == 2
        # Should not include timestamp
        assert set(api_msgs[0].keys()) == {'role', 'content'}
        assert api_msgs[0] == {'role': 'user', 'content': 'Hello'}

    def test_clear_messages(self, user):
        conv = AIConversation.objects.create(user=user)
        conv.add_message('user', 'Hello')
        conv.add_message('assistant', 'Hi!')
        assert len(conv.messages) == 2
        conv.clear_messages()
        conv.refresh_from_db()
        assert conv.messages == []

    def test_conversation_ordering(self, user):
        conv1 = AIConversation.objects.create(user=user, title="First")
        conv2 = AIConversation.objects.create(user=user, title="Second")
        convs = list(AIConversation.objects.filter(user=user))
        # Ordering is -updated_at, newest first
        assert convs[0] == conv2


# =============================================================================
# AIUsageLog Tests
# =============================================================================

@pytest.mark.django_db
class TestAIUsageLog:

    def test_create_usage_log(self, user):
        log = AIUsageLog.objects.create(
            user=user,
            model='claude-3-5-sonnet-20241022',
            tokens_input=100,
            tokens_output=200,
            endpoint='chat',
        )
        assert log.pk is not None
        assert log.success is True
        assert log.cost_estimate > 0

    def test_cost_calculation_sonnet(self, user):
        log = AIUsageLog.objects.create(
            user=user,
            model='claude-3-5-sonnet-20241022',
            tokens_input=1_000_000,
            tokens_output=1_000_000,
            endpoint='chat',
        )
        # Sonnet: $3/M input + $15/M output = $18
        assert log.cost_estimate == Decimal('18.0')

    def test_cost_calculation_haiku(self, user):
        log = AIUsageLog.objects.create(
            user=user,
            model='claude-3-haiku-20240307',
            tokens_input=1_000_000,
            tokens_output=1_000_000,
            endpoint='categorize',
        )
        # Haiku: $0.25/M input + $1.25/M output = $1.50
        assert log.cost_estimate == Decimal('1.5')

    def test_cost_calculation_opus(self, user):
        log = AIUsageLog.objects.create(
            user=user,
            model='claude-3-opus-20240229',
            tokens_input=1_000_000,
            tokens_output=1_000_000,
            endpoint='analyze',
        )
        # Opus: $15/M input + $75/M output = $90
        assert log.cost_estimate == Decimal('90.0')

    def test_cost_calculation_unknown_model(self, user):
        log = AIUsageLog(
            user=user,
            model='unknown-model',
            tokens_input=100,
            tokens_output=200,
            endpoint='chat',
        )
        log.save()
        assert log.cost_estimate == 0

    def test_str_representation(self, user):
        log = AIUsageLog.objects.create(
            user=user,
            model='claude-3-5-sonnet-20241022',
            tokens_input=100,
            tokens_output=200,
            endpoint='chat',
        )
        assert "chat" in str(log)
        assert "300 tokens" in str(log)

    def test_get_user_usage_stats(self, user):
        for i in range(5):
            AIUsageLog.objects.create(
                user=user,
                model='claude-3-5-sonnet-20241022',
                tokens_input=100,
                tokens_output=50,
                endpoint='chat',
                latency_ms=200,
            )
        stats = AIUsageLog.get_user_usage_stats(user, days=30)
        assert stats['total_calls'] == 5
        assert stats['total_input_tokens'] == 500
        assert stats['total_output_tokens'] == 250
        assert stats['total_tokens'] == 750
        assert stats['total_cost'] > 0
        assert stats['avg_latency_ms'] == 200
        assert stats['period_days'] == 30

    def test_get_user_usage_stats_empty(self, user):
        stats = AIUsageLog.get_user_usage_stats(user, days=30)
        assert stats['total_calls'] == 0
        assert stats['total_input_tokens'] == 0
        assert stats['total_output_tokens'] == 0
        assert stats['total_tokens'] == 0
        assert stats['total_cost'] == 0

    def test_get_user_usage_stats_excludes_failed(self, user):
        AIUsageLog.objects.create(
            user=user,
            model='claude-3-5-sonnet-20241022',
            tokens_input=100,
            tokens_output=50,
            endpoint='chat',
            success=True,
        )
        AIUsageLog.objects.create(
            user=user,
            model='claude-3-5-sonnet-20241022',
            tokens_input=100,
            tokens_output=50,
            endpoint='chat',
            success=False,
        )
        stats = AIUsageLog.get_user_usage_stats(user, days=30)
        assert stats['total_calls'] == 1

    def test_usage_log_with_error(self, user):
        log = AIUsageLog.objects.create(
            user=user,
            model='claude-3-5-sonnet-20241022',
            tokens_input=0,
            tokens_output=0,
            endpoint='chat',
            success=False,
            error_message="Rate limit exceeded",
        )
        assert log.success is False
        assert log.error_message == "Rate limit exceeded"


# =============================================================================
# ChatSession Tests
# =============================================================================

@pytest.mark.django_db
class TestChatSession:

    def test_create_session(self, user):
        session = ChatSession.objects.create(user=user, title="Test Session")
        assert session.pk is not None
        assert session.is_active is True
        assert "Chat Session" in str(session)

    def test_session_ordering(self, user):
        s1 = ChatSession.objects.create(user=user, title="Old")
        s2 = ChatSession.objects.create(user=user, title="New")
        sessions = list(ChatSession.objects.filter(user=user))
        assert sessions[0] == s2  # newest first


# =============================================================================
# ChatMessage Tests
# =============================================================================

@pytest.mark.django_db
class TestChatMessage:

    def test_create_message(self, user):
        session = ChatSession.objects.create(user=user)
        msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content='Hello, AI!',
        )
        assert msg.pk is not None
        assert msg.role == 'user'
        assert str(msg).startswith('user:')

    def test_message_ordering(self, user):
        session = ChatSession.objects.create(user=user)
        m1 = ChatMessage.objects.create(session=session, role='user', content='Hi')
        m2 = ChatMessage.objects.create(session=session, role='assistant', content='Hello')
        msgs = list(ChatMessage.objects.filter(session=session))
        assert msgs[0] == m1  # oldest first (ordering by created_at)
