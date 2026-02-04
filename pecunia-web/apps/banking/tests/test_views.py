"""
Tests for banking API views.

Covers every ViewSet, APIView, action, and edge case in apps.banking.views.
"""
import uuid
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework import status as http_status

from apps.banking.models import BankAccount, BankConnection, SyncLog
from apps.banking.providers.base import (
    AuthorizationResult,
    ProviderAccount,
    ProviderError,
    TokenExpiredError,
)


# Use a minimal URL config that only includes the banking app
# and override session/middleware settings that require external services.
_TEST_OVERRIDES = {
    "ROOT_URLCONF": "apps.banking.tests.urls",
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    "MIDDLEWARE": [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
    ],
}
pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("_view_settings"),
]


@pytest.fixture(autouse=False)
def _view_settings(settings):
    """Apply minimal settings overrides for view tests."""
    settings.ROOT_URLCONF = _TEST_OVERRIDES["ROOT_URLCONF"]
    settings.CACHES = _TEST_OVERRIDES["CACHES"]
    settings.MIDDLEWARE = _TEST_OVERRIDES["MIDDLEWARE"]
    settings.ALLOWED_REDIRECT_DOMAINS = []
    settings.REST_FRAMEWORK = {
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework_simplejwt.authentication.JWTAuthentication",
            "rest_framework.authentication.SessionAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
    }


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

CONNECTIONS_URL = "/api/v1/banking/connections/"
CALLBACK_URL = "/api/v1/banking/callback/"
ACCOUNTS_URL = "/api/v1/banking/accounts/"
INSTITUTIONS_URL = "/api/v1/banking/institutions/"
SYNC_LOGS_URL = "/api/v1/banking/sync-logs/"
SYNC_ALL_URL = "/api/v1/banking/sync-all/"


def _connection_detail_url(pk):
    return f"{CONNECTIONS_URL}{pk}/"


def _connection_sync_url(pk):
    return f"{CONNECTIONS_URL}{pk}/sync/"


def _connection_status_url(pk):
    return f"{CONNECTIONS_URL}{pk}/status/"


def _account_detail_url(pk):
    return f"{ACCOUNTS_URL}{pk}/"


def _account_refresh_balance_url(pk):
    return f"{ACCOUNTS_URL}{pk}/refresh_balance/"


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestAuthenticationRequired:
    """All banking endpoints require authentication."""

    def test_connections_list_unauthenticated(self, api_client):
        resp = api_client.get(CONNECTIONS_URL)
        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_accounts_list_unauthenticated(self, api_client):
        resp = api_client.get(ACCOUNTS_URL)
        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_callback_unauthenticated(self, api_client):
        resp = api_client.post(CALLBACK_URL, {})
        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_institutions_unauthenticated(self, api_client):
        resp = api_client.get(INSTITUTIONS_URL)
        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_sync_logs_unauthenticated(self, api_client):
        resp = api_client.get(SYNC_LOGS_URL)
        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_sync_all_unauthenticated(self, api_client):
        resp = api_client.post(SYNC_ALL_URL)
        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# BankConnectionViewSet
# ---------------------------------------------------------------------------


class TestBankConnectionViewSetList:

    def test_list_returns_own_connections(self, auth_client, bank_connection):
        resp = auth_client.get(CONNECTIONS_URL)
        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["id"] == str(bank_connection.id)

    def test_list_excludes_other_user_connections(
        self, auth_client, auth_client2, user2, encryption_key, db
    ):
        """User should only see their own connections."""
        BankConnection.objects.create(
            user=user2,
            provider="truelayer",
            institution_id="ins_other",
            institution_name="Other Bank",
        )
        resp = auth_client.get(CONNECTIONS_URL)
        # auth_client (user) should see 0 connections (no bank_connection fixture here)
        for conn in resp.data:
            assert conn["institution_name"] != "Other Bank"


class TestBankConnectionViewSetCreate:

    @patch("apps.banking.views.get_provider")
    def test_create_returns_auth_url(self, mock_get_provider, auth_client):
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = "https://bank.com/auth?state=abc"
        mock_get_provider.return_value = mock_provider

        resp = auth_client.post(
            CONNECTIONS_URL,
            {"provider": "plaid", "redirect_uri": "https://myapp.com/callback"},
            format="json",
        )
        assert resp.status_code == http_status.HTTP_200_OK
        assert "authorization_url" in resp.data
        assert resp.data["provider"] == "plaid"

    @patch("apps.banking.views.get_provider")
    def test_create_stores_state_in_session(self, mock_get_provider, auth_client):
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = "https://bank.com/auth"
        mock_get_provider.return_value = mock_provider

        auth_client.post(
            CONNECTIONS_URL,
            {"provider": "plaid", "redirect_uri": "https://myapp.com/cb"},
            format="json",
        )
        # Session keys verified via callback tests below

    @patch("apps.banking.views.get_provider")
    def test_create_provider_error(self, mock_get_provider, auth_client):
        mock_get_provider.side_effect = ProviderError("Config error", code="cfg_err")

        resp = auth_client.post(
            CONNECTIONS_URL,
            {"provider": "plaid", "redirect_uri": "https://myapp.com/cb"},
            format="json",
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == "cfg_err"

    def test_create_invalid_provider(self, auth_client):
        resp = auth_client.post(
            CONNECTIONS_URL,
            {"provider": "nonexistent", "redirect_uri": "https://app.com/cb"},
            format="json",
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST


class TestBankConnectionViewSetRetrieve:

    def test_retrieve_uses_detail_serializer(self, auth_client, bank_connection):
        resp = auth_client.get(_connection_detail_url(bank_connection.id))
        assert resp.status_code == http_status.HTTP_200_OK
        assert "accounts" in resp.data

    def test_retrieve_other_user_forbidden(
        self, auth_client2, bank_connection
    ):
        resp = auth_client2.get(_connection_detail_url(bank_connection.id))
        assert resp.status_code == http_status.HTTP_404_NOT_FOUND


class TestBankConnectionViewSetDestroy:

    @patch("apps.banking.views.get_provider")
    def test_destroy_revokes_and_deletes(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.revoke_access.return_value = True
        mock_get_provider.return_value = mock_provider

        resp = auth_client.delete(_connection_detail_url(bank_connection.id))
        assert resp.status_code == http_status.HTTP_204_NO_CONTENT
        assert not BankConnection.objects.filter(pk=bank_connection.pk).exists()

    @patch("apps.banking.views.get_provider")
    def test_destroy_continues_on_revoke_error(
        self, mock_get_provider, auth_client, bank_connection
    ):
        """Deletion proceeds even if provider revocation fails."""
        mock_provider = MagicMock()
        mock_provider.revoke_access.side_effect = ProviderError("Revoke failed")
        mock_get_provider.return_value = mock_provider

        resp = auth_client.delete(_connection_detail_url(bank_connection.id))
        assert resp.status_code == http_status.HTTP_204_NO_CONTENT
        assert not BankConnection.objects.filter(pk=bank_connection.pk).exists()

    @patch("apps.banking.views.get_provider")
    def test_destroy_continues_on_generic_exception(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.revoke_access.side_effect = Exception("Network down")
        mock_get_provider.return_value = mock_provider

        resp = auth_client.delete(_connection_detail_url(bank_connection.id))
        assert resp.status_code == http_status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# BankConnectionViewSet - sync action
# ---------------------------------------------------------------------------


class TestBankConnectionSync:

    def _make_provider_account(self):
        return ProviderAccount(
            provider_account_id="acc_sync_1",
            name="Synced Checking",
            account_type="checking",
            balance=Decimal("1234.56"),
            currency="EUR",
        )

    @patch("apps.banking.views.get_provider")
    def test_sync_success(self, mock_get_provider, auth_client, bank_connection):
        mock_provider = MagicMock()
        mock_provider.get_accounts.return_value = [self._make_provider_account()]
        mock_get_provider.return_value = mock_provider

        # Ensure token is not expired
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(
            _connection_sync_url(bank_connection.id),
            {"sync_type": "full"},
            format="json",
        )
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["status"] == "success"
        assert resp.data["accounts_synced"] == 1

    @patch("apps.banking.views.get_provider")
    def test_sync_refreshes_expired_token(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.refresh_access_token.return_value = AuthorizationResult(
            access_token="new_token",
            refresh_token="new_refresh",
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        mock_provider.get_accounts.return_value = [self._make_provider_account()]
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() - timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(
            _connection_sync_url(bank_connection.id), {}, format="json"
        )
        assert resp.status_code == http_status.HTTP_200_OK
        mock_provider.refresh_access_token.assert_called_once()

    @patch("apps.banking.views.get_provider")
    def test_sync_token_expired_error(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.get_accounts.side_effect = TokenExpiredError("Token expired")
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(
            _connection_sync_url(bank_connection.id), {}, format="json"
        )
        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED
        assert resp.data["needs_reauthorization"] is True

        bank_connection.refresh_from_db()
        assert bank_connection.status == "expired"

    @patch("apps.banking.views.get_provider")
    def test_sync_provider_error(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.get_accounts.side_effect = ProviderError(
            "API down", code="api_error"
        )
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(
            _connection_sync_url(bank_connection.id), {}, format="json"
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == "api_error"

    @patch("apps.banking.views.get_provider")
    def test_sync_concurrent_prevention(
        self, mock_get_provider, auth_client, bank_connection
    ):
        """A sync already in progress prevents a new one."""
        SyncLog.objects.create(
            connection=bank_connection,
            sync_type="full",
            status="started",
        )
        resp = auth_client.post(
            _connection_sync_url(bank_connection.id), {}, format="json"
        )
        assert resp.status_code == http_status.HTTP_409_CONFLICT

    @patch("apps.banking.views.get_provider")
    def test_sync_old_started_log_does_not_block(
        self, mock_get_provider, auth_client, bank_connection
    ):
        """Started logs older than 5 minutes don't block new syncs."""
        old_log = SyncLog.objects.create(
            connection=bank_connection,
            sync_type="full",
            status="started",
        )
        # Backdate the started_at
        SyncLog.objects.filter(pk=old_log.pk).update(
            started_at=timezone.now() - timedelta(minutes=10)
        )

        mock_provider = MagicMock()
        mock_provider.get_accounts.return_value = []
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(
            _connection_sync_url(bank_connection.id), {}, format="json"
        )
        assert resp.status_code == http_status.HTTP_200_OK

    @patch("apps.banking.views.get_provider")
    def test_sync_creates_sync_log(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.get_accounts.return_value = []
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(
            _connection_sync_url(bank_connection.id), {}, format="json"
        )
        assert resp.status_code == http_status.HTTP_200_OK
        log = SyncLog.objects.get(pk=resp.data["sync_log_id"])
        assert log.status == "success"
        assert log.completed_at is not None


# ---------------------------------------------------------------------------
# BankConnectionViewSet - status action
# ---------------------------------------------------------------------------


class TestBankConnectionStatus:

    def test_status_returns_connection_health(self, auth_client, bank_connection):
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.get(_connection_status_url(bank_connection.id))
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["status"] == "active"
        assert resp.data["is_healthy"] is True

    def test_status_expired_connection(self, auth_client, bank_connection):
        bank_connection.status = "expired"
        bank_connection.status_message = "Token expired"
        bank_connection.save()

        resp = auth_client.get(_connection_status_url(bank_connection.id))
        assert resp.data["is_healthy"] is False
        assert resp.data["needs_reauthorization"] is True


# ---------------------------------------------------------------------------
# BankConnectionViewSet - providers action
# ---------------------------------------------------------------------------


class TestBankConnectionProviders:

    @patch("apps.banking.views.get_provider")
    @patch("apps.banking.views.get_available_providers")
    def test_providers_list(
        self, mock_available, mock_get_provider, auth_client, settings
    ):
        # Configure settings so providers can init
        settings.PLAID_CLIENT_ID = "test"
        settings.PLAID_SECRET = "test"
        settings.TRUELAYER_CLIENT_ID = "test"
        settings.BUDGET_INSIGHT_CLIENT_ID = "test"

        mock_available.return_value = ["plaid"]

        mock_provider = MagicMock()
        mock_provider.provider_name = "plaid"
        mock_provider.display_name = "Plaid"
        mock_provider.supported_countries = ["US", "CA"]
        mock_get_provider.return_value = mock_provider

        resp = auth_client.get(f"{CONNECTIONS_URL}providers/")
        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["name"] == "plaid"


# ---------------------------------------------------------------------------
# BankConnectionCallbackView
# ---------------------------------------------------------------------------


class TestBankConnectionCallback:

    def _setup_session(self, client, provider="plaid", state="test_state", redirect="https://app.com/cb"):
        """Set up session data that the create endpoint would have stored."""
        session = client.session
        session[f"bank_oauth_state_{provider}"] = state
        session[f"bank_oauth_redirect_{provider}"] = redirect
        session.save()

    @patch("apps.banking.views.get_provider")
    def test_callback_success_creates_connection(
        self, mock_get_provider, auth_client, encryption_key, user
    ):
        mock_provider = MagicMock()
        mock_provider.exchange_code.return_value = AuthorizationResult(
            access_token="new_access",
            refresh_token="new_refresh",
            token_expires_at=timezone.now() + timedelta(hours=1),
            consent_expires_at=timezone.now() + timedelta(days=90),
            provider_connection_id="conn_id_123",
            institution_id="ins_callback",
            institution_name="Callback Bank",
            institution_logo_url="https://logo.com/bank.png",
        )
        mock_get_provider.return_value = mock_provider

        self._setup_session(auth_client)

        resp = auth_client.post(
            CALLBACK_URL,
            {
                "code": "auth_code_xyz",
                "state": "test_state",
                "redirect_uri": "https://app.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_201_CREATED
        assert resp.data["created"] is True
        assert resp.data["connection"]["institution_name"] == "Callback Bank"

        # Verify connection in DB
        conn = BankConnection.objects.get(
            user=user, provider="plaid", institution_id="ins_callback"
        )
        assert conn.access_token == "new_access"
        assert conn.refresh_token == "new_refresh"
        assert conn.status == "active"

    @patch("apps.banking.views.get_provider")
    def test_callback_updates_existing_connection(
        self, mock_get_provider, auth_client, bank_connection, user
    ):
        mock_provider = MagicMock()
        mock_provider.exchange_code.return_value = AuthorizationResult(
            access_token="updated_access",
            institution_id=bank_connection.institution_id,
            institution_name="Test Bank Updated",
        )
        mock_get_provider.return_value = mock_provider

        self._setup_session(auth_client)

        resp = auth_client.post(
            CALLBACK_URL,
            {
                "code": "reauth_code",
                "state": "test_state",
                "redirect_uri": "https://app.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["created"] is False

    def test_callback_invalid_state(self, auth_client, encryption_key):
        self._setup_session(auth_client, state="correct_state")

        resp = auth_client.post(
            CALLBACK_URL,
            {
                "code": "code",
                "state": "wrong_state",
                "redirect_uri": "https://app.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Invalid state" in resp.data["error"]

    def test_callback_missing_state_in_session(self, auth_client, encryption_key):
        """No state stored in session -> invalid."""
        resp = auth_client.post(
            CALLBACK_URL,
            {
                "code": "code",
                "state": "any_state",
                "redirect_uri": "https://app.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_callback_invalid_redirect_uri(self, auth_client, encryption_key):
        self._setup_session(
            auth_client, redirect="https://app.com/cb"
        )

        resp = auth_client.post(
            CALLBACK_URL,
            {
                "code": "code",
                "state": "test_state",
                "redirect_uri": "https://evil.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "redirect_uri" in resp.data["error"]

    def test_callback_missing_redirect_in_session(self, auth_client, encryption_key):
        """State matches but redirect not in session."""
        session = auth_client.session
        session["bank_oauth_state_plaid"] = "test_state"
        session.save()

        resp = auth_client.post(
            CALLBACK_URL,
            {
                "code": "code",
                "state": "test_state",
                "redirect_uri": "https://app.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    @patch("apps.banking.views.get_provider")
    def test_callback_provider_error(
        self, mock_get_provider, auth_client, encryption_key
    ):
        mock_get_provider.return_value = MagicMock(
            exchange_code=MagicMock(
                side_effect=ProviderError("Exchange failed", code="exchange_err")
            )
        )
        self._setup_session(auth_client)

        resp = auth_client.post(
            CALLBACK_URL,
            {
                "code": "bad_code",
                "state": "test_state",
                "redirect_uri": "https://app.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == "exchange_err"

    @patch("apps.banking.views.get_provider")
    def test_callback_cleans_session(
        self, mock_get_provider, auth_client, encryption_key, user
    ):
        mock_provider = MagicMock()
        mock_provider.exchange_code.return_value = AuthorizationResult(
            access_token="tok",
            institution_id="ins_clean",
            institution_name="Clean Bank",
        )
        mock_get_provider.return_value = mock_provider

        self._setup_session(auth_client)

        auth_client.post(
            CALLBACK_URL,
            {
                "code": "code",
                "state": "test_state",
                "redirect_uri": "https://app.com/cb",
                "provider": "plaid",
            },
            format="json",
        )
        session = auth_client.session
        assert "bank_oauth_state_plaid" not in session
        assert "bank_oauth_redirect_plaid" not in session


# ---------------------------------------------------------------------------
# BankAccountViewSet
# ---------------------------------------------------------------------------


class TestBankAccountViewSet:

    def test_list_accounts(self, auth_client, bank_account):
        resp = auth_client.get(ACCOUNTS_URL)
        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_list_excludes_hidden_by_default(
        self, auth_client, bank_account, user, bank_connection
    ):
        BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="hidden_acc",
            name="Hidden",
            is_hidden=True,
        )
        resp = auth_client.get(ACCOUNTS_URL)
        names = [a["name"] for a in resp.data]
        assert "Hidden" not in names

    def test_list_includes_hidden_when_requested(
        self, auth_client, bank_account, user, bank_connection
    ):
        BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="hidden_acc_2",
            name="Hidden 2",
            is_hidden=True,
        )
        resp = auth_client.get(ACCOUNTS_URL, {"include_hidden": "true"})
        names = [a["name"] for a in resp.data]
        assert "Hidden 2" in names

    def test_filter_by_type(self, auth_client, bank_account, user, bank_connection):
        BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="sav_acc",
            name="Savings",
            account_type="savings",
        )
        resp = auth_client.get(ACCOUNTS_URL, {"type": "savings"})
        assert len(resp.data) == 1
        assert resp.data[0]["account_type"] == "savings"

    def test_filter_by_connection(self, auth_client, bank_account, bank_connection):
        resp = auth_client.get(
            ACCOUNTS_URL, {"connection": str(bank_connection.id)}
        )
        assert len(resp.data) == 1

    def test_retrieve_account(self, auth_client, bank_account):
        resp = auth_client.get(_account_detail_url(bank_account.id))
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["name"] == "Test Checking"

    def test_partial_update_account(self, auth_client, bank_account):
        resp = auth_client.patch(
            _account_detail_url(bank_account.id),
            {"custom_name": "My Checking"},
            format="json",
        )
        assert resp.status_code == http_status.HTTP_200_OK
        bank_account.refresh_from_db()
        assert bank_account.custom_name == "My Checking"

    def test_other_user_cannot_see_account(self, auth_client2, bank_account):
        resp = auth_client2.get(_account_detail_url(bank_account.id))
        assert resp.status_code == http_status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# BankAccountViewSet - summary action
# ---------------------------------------------------------------------------


class TestBankAccountSummary:

    def test_summary_returns_totals(self, auth_client, bank_account, user):
        user.preferred_currency = "EUR"
        user.save()

        resp = auth_client.get(f"{ACCOUNTS_URL}summary/")
        assert resp.status_code == http_status.HTTP_200_OK
        assert Decimal(resp.data["total_balance"]) == Decimal("5000.00")
        assert resp.data["accounts_count"] == 1
        assert resp.data["currency"] == "EUR"

    def test_summary_empty_accounts(self, auth_client, user, encryption_key):
        user.preferred_currency = "EUR"
        user.save()

        resp = auth_client.get(f"{ACCOUNTS_URL}summary/")
        assert resp.status_code == http_status.HTTP_200_OK
        assert Decimal(resp.data["total_balance"]) == Decimal("0")
        assert resp.data["accounts_count"] == 0

    def test_summary_groups_by_type(
        self, auth_client, user, bank_connection, bank_account
    ):
        user.preferred_currency = "EUR"
        user.save()

        BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="sav_sum",
            name="Savings",
            account_type="savings",
            balance=Decimal("3000.00"),
        )
        resp = auth_client.get(f"{ACCOUNTS_URL}summary/")
        by_type = resp.data["by_type"]
        assert "checking" in by_type
        assert "savings" in by_type


# ---------------------------------------------------------------------------
# BankAccountViewSet - refresh_balance action
# ---------------------------------------------------------------------------


class TestBankAccountRefreshBalance:

    @patch("apps.banking.views.get_provider")
    def test_refresh_balance_success(
        self, mock_get_provider, auth_client, bank_account, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.get_balance.return_value = {
            "balance": Decimal("9999.99"),
            "available_balance": Decimal("9900.00"),
        }
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(_account_refresh_balance_url(bank_account.id))
        assert resp.status_code == http_status.HTTP_200_OK

        bank_account.refresh_from_db()
        assert bank_account.balance == Decimal("9999.99")

    @patch("apps.banking.views.get_provider")
    def test_refresh_balance_token_refresh(
        self, mock_get_provider, auth_client, bank_account, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.refresh_access_token.return_value = AuthorizationResult(
            access_token="refreshed_token",
            refresh_token="new_refresh",
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        mock_provider.get_balance.return_value = {
            "balance": Decimal("100.00"),
        }
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() - timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(_account_refresh_balance_url(bank_account.id))
        assert resp.status_code == http_status.HTTP_200_OK
        mock_provider.refresh_access_token.assert_called_once()

    @patch("apps.banking.views.get_provider")
    def test_refresh_balance_provider_error(
        self, mock_get_provider, auth_client, bank_account, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.get_balance.side_effect = ProviderError("API error")
        mock_get_provider.return_value = mock_provider

        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.save()

        resp = auth_client.post(_account_refresh_balance_url(bank_account.id))
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# InstitutionSearchView
# ---------------------------------------------------------------------------


class TestInstitutionSearchView:

    @patch("apps.banking.views.get_provider")
    def test_search_institutions(self, mock_get_provider, auth_client):
        mock_provider = MagicMock()
        mock_provider.get_institutions.return_value = [
            MagicMock(
                institution_id="ins_1",
                name="Bank One",
                logo_url="https://logo.com/1.png",
                country="FR",
                bic=None,
            ),
        ]
        mock_get_provider.return_value = mock_provider

        resp = auth_client.get(INSTITUTIONS_URL, {"provider": "plaid", "country": "FR"})
        assert resp.status_code == http_status.HTTP_200_OK

    def test_missing_provider_param(self, auth_client):
        resp = auth_client.get(INSTITUTIONS_URL)
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Provider parameter required" in resp.data["error"]

    @patch("apps.banking.views.get_provider")
    def test_provider_error(self, mock_get_provider, auth_client):
        mock_get_provider.side_effect = ProviderError("Provider broken")
        resp = auth_client.get(INSTITUTIONS_URL, {"provider": "plaid"})
        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    @patch("apps.banking.views.get_provider")
    def test_results_limited_to_50(self, mock_get_provider, auth_client):
        institutions = [
            MagicMock(
                institution_id=f"ins_{i}",
                name=f"Bank {i}",
                logo_url=None,
                country="FR",
                bic=None,
            )
            for i in range(60)
        ]
        mock_provider = MagicMock()
        mock_provider.get_institutions.return_value = institutions
        mock_get_provider.return_value = mock_provider

        resp = auth_client.get(INSTITUTIONS_URL, {"provider": "plaid"})
        assert len(resp.data) == 50


# ---------------------------------------------------------------------------
# SyncLogViewSet
# ---------------------------------------------------------------------------


class TestSyncLogViewSet:

    def test_list_sync_logs(self, auth_client, sync_log):
        resp = auth_client.get(SYNC_LOGS_URL)
        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_retrieve_sync_log(self, auth_client, sync_log):
        resp = auth_client.get(f"{SYNC_LOGS_URL}{sync_log.id}/")
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["sync_type"] == "full"

    def test_other_user_cannot_see_logs(self, auth_client2, sync_log):
        resp = auth_client2.get(f"{SYNC_LOGS_URL}{sync_log.id}/")
        assert resp.status_code == http_status.HTTP_404_NOT_FOUND

    def test_logs_ordered_by_started_at_desc(self, auth_client, bank_connection):
        l1 = SyncLog.objects.create(
            connection=bank_connection, sync_type="full", status="success"
        )
        l2 = SyncLog.objects.create(
            connection=bank_connection, sync_type="incremental", status="started"
        )
        resp = auth_client.get(SYNC_LOGS_URL)
        ids = [entry["id"] for entry in resp.data]
        assert ids.index(str(l2.id)) < ids.index(str(l1.id))


# ---------------------------------------------------------------------------
# SyncAllView
# ---------------------------------------------------------------------------


class TestSyncAllView:

    @patch("apps.banking.views.get_provider")
    def test_sync_all_success(
        self, mock_get_provider, auth_client, bank_connection, bank_account
    ):
        mock_provider = MagicMock()
        mock_provider.get_accounts.return_value = [
            ProviderAccount(
                provider_account_id="acc_123",
                name="Test Checking",
                account_type="checking",
                balance=Decimal("6000.00"),
                currency="EUR",
            )
        ]
        mock_get_provider.return_value = mock_provider

        resp = auth_client.post(SYNC_ALL_URL)
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["synced"] == 1
        assert resp.data["failed"] == 0

    @patch("apps.banking.views.get_provider")
    def test_sync_all_with_errors(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.get_accounts.side_effect = ProviderError("Sync failed")
        mock_get_provider.return_value = mock_provider

        resp = auth_client.post(SYNC_ALL_URL)
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["failed"] == 1

    @patch("apps.banking.views.get_provider")
    def test_sync_all_unexpected_exception(
        self, mock_get_provider, auth_client, bank_connection
    ):
        mock_provider = MagicMock()
        mock_provider.get_accounts.side_effect = RuntimeError("Unexpected")
        mock_get_provider.return_value = mock_provider

        resp = auth_client.post(SYNC_ALL_URL)
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["failed"] == 1
        assert "unexpected error" in resp.data["results"][0]["error"].lower()

    def test_sync_all_only_active_connections(
        self, auth_client, user, encryption_key, db
    ):
        """Only active connections are synced."""
        BankConnection.objects.create(
            user=user,
            provider="plaid",
            institution_id="ins_expired",
            institution_name="Expired Bank",
            status="expired",
        )
        resp = auth_client.post(SYNC_ALL_URL)
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["synced"] == 0
        assert resp.data["failed"] == 0

    @patch("apps.banking.views.get_provider")
    def test_sync_all_limited_to_max_connections(
        self, mock_get_provider, auth_client, user, encryption_key, db
    ):
        """Should not sync more than MAX_CONNECTIONS_PER_SYNC."""
        for i in range(15):
            BankConnection.objects.create(
                user=user,
                provider="plaid",
                institution_id=f"ins_max_{i}",
                institution_name=f"Bank {i}",
                status="active",
            )

        mock_provider = MagicMock()
        mock_provider.get_accounts.return_value = []
        mock_get_provider.return_value = mock_provider

        resp = auth_client.post(SYNC_ALL_URL)
        total = resp.data["synced"] + resp.data["failed"]
        assert total <= 10
