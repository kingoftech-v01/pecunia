"""
Tests for AI API views.

Tests all ViewSet actions, permissions, and filtering.
"""
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ai.models import AIRecommendation, AICategorizationLog, AIConversation, ChatSession, ChatMessage
from apps.ai.views import IsPremiumUser


# =============================================================================
# Permission Tests
# =============================================================================

@pytest.mark.django_db
class TestIsPremiumUser:

    def test_unauthenticated_denied(self, api_client):
        """Unauthenticated users should be denied."""
        perm = IsPremiumUser()
        request = MagicMock()
        request.user.is_authenticated = False
        assert perm.has_permission(request, None) is False

    def test_free_user_denied(self, user):
        perm = IsPremiumUser()
        request = MagicMock()
        request.user = user
        # Free user should not have access - is_authenticated is already True for real User
        assert user.subscription_tier == 'free'
        assert perm.has_permission(request, None) is False

    def test_premium_user_allowed(self, premium_user):
        perm = IsPremiumUser()
        request = MagicMock()
        request.user = premium_user
        assert perm.has_permission(request, None) is True

    def test_pro_user_allowed(self, db, user_password):
        from apps.accounts.models import User
        pro_user = User.objects.create_user(
            email="pro@example.com",
            password=user_password,
            subscription_tier="pro",
        )
        perm = IsPremiumUser()
        request = MagicMock()
        request.user = pro_user
        assert perm.has_permission(request, None) is True

    def test_enterprise_user_allowed(self, db, user_password):
        from apps.accounts.models import User
        ent_user = User.objects.create_user(
            email="ent@example.com",
            password=user_password,
            subscription_tier="enterprise",
        )
        perm = IsPremiumUser()
        request = MagicMock()
        request.user = ent_user
        assert perm.has_permission(request, None) is True


# =============================================================================
# Helper to create authenticated premium client
# =============================================================================

@pytest.fixture
def premium_client(premium_user):
    client = APIClient()
    refresh = RefreshToken.for_user(premium_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# =============================================================================
# AIRecommendationViewSet Tests
# =============================================================================

@pytest.mark.django_db
class TestAIRecommendationViewSet:

    def test_list_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/ai/api/recommendations/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_requires_premium(self, auth_client):
        resp = auth_client.get('/api/v1/ai/api/recommendations/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_recommendations(self, premium_user, premium_client):
        AIRecommendation.objects.create(
            user=premium_user,
            type='budget_alert',
            title="Test",
            content="Content",
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) >= 1

    def test_list_excludes_dismissed(self, premium_user, premium_client):
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert',
            title="Active", content="Test",
        )
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert',
            title="Dismissed", content="Test", is_dismissed=True,
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert all(r['title'] != 'Dismissed' for r in data)

    def test_filter_by_type(self, premium_user, premium_client):
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="BA", content="T",
        )
        AIRecommendation.objects.create(
            user=premium_user, type='saving_tip', title="ST", content="T",
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/?type=budget_alert')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert all(r['type'] == 'budget_alert' for r in data)

    def test_filter_by_read_status(self, premium_user, premium_client):
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Unread", content="T",
        )
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Read", content="T", is_read=True,
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/?is_read=false')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert all(r['is_read'] is False for r in data)

    def test_excludes_expired_by_default(self, premium_user, premium_client):
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Active", content="T",
        )
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Expired", content="T",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        titles = [r['title'] for r in data]
        assert "Expired" not in titles

    def test_include_expired(self, premium_user, premium_client):
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Expired", content="T",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/?include_expired=true')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        titles = [r['title'] for r in data]
        assert "Expired" in titles

    def test_mark_read_action(self, premium_user, premium_client):
        rec = AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Test", content="T",
        )
        resp = premium_client.post(f'/api/v1/ai/api/recommendations/{rec.id}/mark_read/', {}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        rec.refresh_from_db()
        assert rec.is_read is True

    def test_dismiss_action(self, premium_user, premium_client):
        rec = AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Test", content="T",
        )
        resp = premium_client.post(f'/api/v1/ai/api/recommendations/{rec.id}/dismiss/', {}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        rec.refresh_from_db()
        assert rec.is_dismissed is True

    def test_mark_all_read(self, premium_user, premium_client):
        for i in range(3):
            AIRecommendation.objects.create(
                user=premium_user, type='budget_alert', title=f"T{i}", content="T",
            )
        resp = premium_client.post('/api/v1/ai/api/recommendations/mark_all_read/', {}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert '3' in resp.data['status']

    def test_unread_count(self, premium_user, premium_client):
        for i in range(5):
            AIRecommendation.objects.create(
                user=premium_user, type='budget_alert', title=f"T{i}", content="T",
            )
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="Read", content="T", is_read=True,
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/unread_count/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['unread_count'] == 5

    def test_cross_tenant_isolation(self, premium_user, premium_client, user2):
        """Other user's recommendations should not be visible."""
        AIRecommendation.objects.create(
            user=user2, type='budget_alert', title="Other User Rec", content="T",
        )
        AIRecommendation.objects.create(
            user=premium_user, type='budget_alert', title="My Rec", content="T",
        )
        resp = premium_client.get('/api/v1/ai/api/recommendations/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        titles = [r['title'] for r in data]
        assert "My Rec" in titles
        assert "Other User Rec" not in titles


# =============================================================================
# CategorizeView Tests
# =============================================================================

@pytest.mark.django_db
class TestCategorizeView:

    def test_categorize_requires_auth(self, api_client):
        resp = api_client.post('/api/v1/ai/api/categorize/', {}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_categorize_requires_premium(self, auth_client):
        resp = auth_client.post('/api/v1/ai/api/categorize/', {'description': 'Test'}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_categorize_with_description(self, premium_user, premium_client):
        from apps.transactions.models import TransactionCategory
        cat = TransactionCategory.objects.create(
            user=premium_user, name="Food", type="expense",
            icon="utensils", color="#ff0000",
        )
        resp = premium_client.post('/api/v1/ai/api/categorize/', {
            'description': 'Coffee at Starbucks',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert 'category_name' in resp.data

    def test_categorize_validation_error(self, premium_client):
        resp = premium_client.post('/api/v1/ai/api/categorize/', {}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# BulkCategorizeView Tests
# =============================================================================

@pytest.mark.django_db
class TestBulkCategorizeView:

    def test_bulk_requires_auth(self, api_client):
        resp = api_client.post('/api/v1/ai/api/categorize/bulk/', {}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_bulk_requires_premium(self, auth_client):
        resp = auth_client.post('/api/v1/ai/api/categorize/bulk/', {
            'transaction_ids': [str(uuid.uuid4())],
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# ChatView Tests
# =============================================================================

@pytest.mark.django_db
class TestChatView:

    def test_chat_requires_auth(self, api_client):
        resp = api_client.post('/api/v1/ai/api/chat/', {'message': 'Hi'}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# ChatHistoryView Tests
# =============================================================================

@pytest.mark.django_db
class TestChatHistoryView:

    def test_chat_history_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/ai/api/chat/history/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# InsightsView Tests
# =============================================================================

@pytest.mark.django_db
class TestInsightsView:

    def test_insights_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/ai/api/insights/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
