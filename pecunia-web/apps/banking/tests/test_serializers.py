"""
Tests for banking serializers.

Covers every serializer class in apps.banking.serializers.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.banking.models import BankAccount, BankConnection, SyncLog
from apps.banking.serializers import (
    BalanceAggregateSerializer,
    BankAccountSerializer,
    BankAccountSummarySerializer,
    BankAccountUpdateSerializer,
    BankConnectionCallbackSerializer,
    BankConnectionCreateSerializer,
    BankConnectionDetailSerializer,
    BankConnectionSerializer,
    ConnectionStatusSerializer,
    InstitutionSerializer,
    SyncLogSerializer,
    SyncRequestSerializer,
)


# ---------------------------------------------------------------------------
# BankConnectionSerializer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBankConnectionSerializer:

    def test_serializes_expected_fields(self, bank_connection):
        serializer = BankConnectionSerializer(bank_connection)
        data = serializer.data
        assert "id" in data
        assert "provider" in data
        assert "institution_name" in data
        assert "status" in data
        assert "is_token_expired" in data
        assert "is_consent_expired" in data
        assert "needs_reauthorization" in data
        assert "accounts_count" in data

    def test_accounts_count_zero(self, bank_connection):
        serializer = BankConnectionSerializer(bank_connection)
        assert serializer.data["accounts_count"] == 0

    def test_accounts_count_with_accounts(self, bank_connection, bank_account):
        serializer = BankConnectionSerializer(bank_connection)
        assert serializer.data["accounts_count"] == 1

    def test_sensitive_fields_excluded(self, bank_connection):
        """access_token and refresh_token must never appear in output."""
        serializer = BankConnectionSerializer(bank_connection)
        data = serializer.data
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert "_access_token_encrypted" not in data
        assert "_refresh_token_encrypted" not in data

    def test_read_only_fields(self):
        """Read-only fields cannot be set via input."""
        ser = BankConnectionSerializer(
            data={
                "provider": "plaid",
                "status": "revoked",
                "institution_name": "Hacker Bank",
            }
        )
        # We only check the meta
        assert "status" in BankConnectionSerializer.Meta.read_only_fields
        assert "institution_name" in BankConnectionSerializer.Meta.read_only_fields


# ---------------------------------------------------------------------------
# BankConnectionDetailSerializer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBankConnectionDetailSerializer:

    def test_includes_accounts_field(self, bank_connection, bank_account):
        serializer = BankConnectionDetailSerializer(bank_connection)
        data = serializer.data
        assert "accounts" in data
        assert len(data["accounts"]) == 1

    def test_filters_hidden_accounts(self, bank_connection, bank_account, user, db):
        # Create a hidden account
        BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="hidden_acc",
            name="Hidden Savings",
            is_hidden=True,
        )
        serializer = BankConnectionDetailSerializer(bank_connection)
        accounts = serializer.data["accounts"]
        # Only the non-hidden one should appear
        assert len(accounts) == 1
        assert accounts[0]["name"] == "Test Checking"


# ---------------------------------------------------------------------------
# BankConnectionCreateSerializer
# ---------------------------------------------------------------------------


class TestBankConnectionCreateSerializer:

    def test_valid_data(self):
        data = {
            "provider": "plaid",
            "redirect_uri": "https://example.com/callback",
        }
        serializer = BankConnectionCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_valid_with_institution_id(self):
        data = {
            "provider": "truelayer",
            "redirect_uri": "https://example.com/callback",
            "institution_id": "ob-hsbc",
        }
        serializer = BankConnectionCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_provider(self):
        data = {
            "provider": "nonexistent",
            "redirect_uri": "https://example.com/callback",
        }
        serializer = BankConnectionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "provider" in serializer.errors

    def test_missing_redirect_uri(self):
        data = {"provider": "plaid"}
        serializer = BankConnectionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "redirect_uri" in serializer.errors

    def test_invalid_redirect_uri(self):
        data = {
            "provider": "plaid",
            "redirect_uri": "not-a-url",
        }
        serializer = BankConnectionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "redirect_uri" in serializer.errors

    def test_redirect_uri_allowed_domain(self, settings):
        settings.ALLOWED_REDIRECT_DOMAINS = ["myapp.com"]
        data = {
            "provider": "plaid",
            "redirect_uri": "https://myapp.com/callback",
        }
        serializer = BankConnectionCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_redirect_uri_disallowed_domain(self, settings):
        settings.ALLOWED_REDIRECT_DOMAINS = ["myapp.com"]
        data = {
            "provider": "plaid",
            "redirect_uri": "https://evil.com/callback",
        }
        serializer = BankConnectionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "redirect_uri" in serializer.errors

    def test_redirect_uri_no_restriction_when_empty(self, settings):
        settings.ALLOWED_REDIRECT_DOMAINS = []
        data = {
            "provider": "plaid",
            "redirect_uri": "https://anything.com/callback",
        }
        serializer = BankConnectionCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_validate_provider_returns_value(self):
        serializer = BankConnectionCreateSerializer()
        assert serializer.validate_provider("plaid") == "plaid"

    def test_validate_provider_invalid_raises(self):
        from rest_framework import serializers as drf_serializers

        serializer = BankConnectionCreateSerializer()
        with pytest.raises(drf_serializers.ValidationError):
            serializer.validate_provider("invalid_provider")


# ---------------------------------------------------------------------------
# BankConnectionCallbackSerializer
# ---------------------------------------------------------------------------


class TestBankConnectionCallbackSerializer:

    def test_valid_data(self):
        data = {
            "code": "auth_code_123",
            "state": "state_abc",
            "redirect_uri": "https://example.com/callback",
            "provider": "plaid",
        }
        serializer = BankConnectionCallbackSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_missing_code(self):
        data = {
            "state": "state_abc",
            "redirect_uri": "https://example.com/callback",
            "provider": "plaid",
        }
        serializer = BankConnectionCallbackSerializer(data=data)
        assert not serializer.is_valid()
        assert "code" in serializer.errors

    def test_missing_state(self):
        data = {
            "code": "auth_code",
            "redirect_uri": "https://example.com/callback",
            "provider": "plaid",
        }
        serializer = BankConnectionCallbackSerializer(data=data)
        assert not serializer.is_valid()
        assert "state" in serializer.errors

    def test_redirect_uri_allowed_domain(self, settings):
        settings.ALLOWED_REDIRECT_DOMAINS = ["safe.com"]
        data = {
            "code": "code",
            "state": "state",
            "redirect_uri": "https://safe.com/cb",
            "provider": "plaid",
        }
        serializer = BankConnectionCallbackSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_redirect_uri_disallowed_domain(self, settings):
        settings.ALLOWED_REDIRECT_DOMAINS = ["safe.com"]
        data = {
            "code": "code",
            "state": "state",
            "redirect_uri": "https://evil.com/cb",
            "provider": "plaid",
        }
        serializer = BankConnectionCallbackSerializer(data=data)
        assert not serializer.is_valid()
        assert "redirect_uri" in serializer.errors

    def test_redirect_uri_no_restriction_when_empty(self, settings):
        settings.ALLOWED_REDIRECT_DOMAINS = []
        data = {
            "code": "code",
            "state": "state",
            "redirect_uri": "https://any.com/cb",
            "provider": "truelayer",
        }
        serializer = BankConnectionCallbackSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


# ---------------------------------------------------------------------------
# BankAccountSerializer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBankAccountSerializer:

    def test_serializes_expected_fields(self, bank_account):
        serializer = BankAccountSerializer(bank_account)
        data = serializer.data
        assert data["name"] == "Test Checking"
        assert data["display_name"] == "Test Checking"
        assert data["institution_name"] == "Test Bank"
        assert data["provider"] == "plaid"
        assert "connection_status" in data

    def test_connection_status_reflects_connection(self, bank_account):
        serializer = BankAccountSerializer(bank_account)
        assert serializer.data["connection_status"] == "active"

    def test_read_only_fields_enforced(self):
        ro = BankAccountSerializer.Meta.read_only_fields
        assert "balance" in ro
        assert "currency" in ro
        assert "name" in ro


# ---------------------------------------------------------------------------
# BankAccountUpdateSerializer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBankAccountUpdateSerializer:

    def test_allowed_fields(self):
        assert set(BankAccountUpdateSerializer.Meta.fields) == {
            "is_hidden",
            "custom_name",
            "color",
        }

    def test_valid_update(self, bank_account):
        serializer = BankAccountUpdateSerializer(
            bank_account,
            data={"is_hidden": True, "custom_name": "Savings", "color": "#ff0000"},
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.is_hidden is True
        assert updated.custom_name == "Savings"
        assert updated.color == "#ff0000"

    def test_partial_update(self, bank_account):
        serializer = BankAccountUpdateSerializer(
            bank_account,
            data={"custom_name": "New Name"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors


# ---------------------------------------------------------------------------
# BankAccountSummarySerializer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBankAccountSummarySerializer:

    def test_fields(self, bank_account):
        serializer = BankAccountSummarySerializer(bank_account)
        data = serializer.data
        assert "display_name" in data
        assert "institution_name" in data
        assert "balance" in data
        assert "currency" in data
        assert "color" in data


# ---------------------------------------------------------------------------
# SyncLogSerializer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncLogSerializer:

    def test_serializes_fields(self, sync_log):
        serializer = SyncLogSerializer(sync_log)
        data = serializer.data
        assert data["sync_type"] == "full"
        assert data["status"] == "success"
        assert data["accounts_synced"] == 2
        assert data["transactions_synced"] == 50

    def test_connection_name(self, sync_log):
        serializer = SyncLogSerializer(sync_log)
        assert serializer.data["connection_name"] == "Test Bank"

    def test_duration_seconds_none_when_not_completed(self, sync_log):
        sync_log.completed_at = None
        sync_log.save()
        serializer = SyncLogSerializer(sync_log)
        assert serializer.data["duration_seconds"] is None

    def test_duration_seconds_present_when_completed(self, sync_log):
        sync_log.completed_at = sync_log.started_at + timedelta(seconds=5)
        sync_log.save()
        serializer = SyncLogSerializer(sync_log)
        assert serializer.data["duration_seconds"] == pytest.approx(5.0, abs=0.5)

    def test_all_fields_read_only(self):
        assert SyncLogSerializer.Meta.read_only_fields == SyncLogSerializer.Meta.fields


# ---------------------------------------------------------------------------
# InstitutionSerializer
# ---------------------------------------------------------------------------


class TestInstitutionSerializer:

    def test_valid_data(self):
        data = {
            "institution_id": "ins_123",
            "name": "Test Bank",
            "logo_url": "https://example.com/logo.png",
            "country": "FR",
        }
        serializer = InstitutionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_null_optional_fields(self):
        data = {
            "institution_id": "ins_456",
            "name": "Null Bank",
            "logo_url": None,
            "country": None,
        }
        serializer = InstitutionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_with_bic(self):
        data = {
            "institution_id": "ins_789",
            "name": "BIC Bank",
            "logo_url": None,
            "country": "DE",
            "bic": "DEUTDEFF",
        }
        serializer = InstitutionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


# ---------------------------------------------------------------------------
# SyncRequestSerializer
# ---------------------------------------------------------------------------


class TestSyncRequestSerializer:

    def test_defaults(self):
        serializer = SyncRequestSerializer(data={})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["sync_type"] == "incremental"
        assert serializer.validated_data["force"] is False

    def test_full_sync_type(self):
        serializer = SyncRequestSerializer(data={"sync_type": "full"})
        assert serializer.is_valid(), serializer.errors

    def test_balance_sync_type(self):
        serializer = SyncRequestSerializer(data={"sync_type": "balance"})
        assert serializer.is_valid(), serializer.errors

    def test_invalid_sync_type(self):
        serializer = SyncRequestSerializer(data={"sync_type": "invalid"})
        assert not serializer.is_valid()
        assert "sync_type" in serializer.errors

    def test_force_flag(self):
        serializer = SyncRequestSerializer(data={"force": True})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["force"] is True


# ---------------------------------------------------------------------------
# BalanceAggregateSerializer
# ---------------------------------------------------------------------------


class TestBalanceAggregateSerializer:

    def test_valid_data(self):
        data = {
            "total_balance": Decimal("10000.00"),
            "total_available": Decimal("9500.00"),
            "currency": "EUR",
            "accounts_count": 3,
            "by_type": {"checking": Decimal("5000.00"), "savings": Decimal("5000.00")},
            "by_institution": {"Bank A": Decimal("10000.00")},
        }
        serializer = BalanceAggregateSerializer(data)
        assert serializer.data["total_balance"] == "10000.00"
        assert serializer.data["accounts_count"] == 3

    def test_null_available(self):
        data = {
            "total_balance": Decimal("500.00"),
            "total_available": None,
            "currency": "USD",
            "accounts_count": 1,
            "by_type": {},
            "by_institution": {},
        }
        serializer = BalanceAggregateSerializer(data)
        assert serializer.data["total_available"] is None


# ---------------------------------------------------------------------------
# ConnectionStatusSerializer
# ---------------------------------------------------------------------------


class TestConnectionStatusSerializer:

    def test_valid_data(self):
        import uuid

        data = {
            "connection_id": uuid.uuid4(),
            "status": "active",
            "is_healthy": True,
            "needs_reauthorization": False,
            "last_sync_at": timezone.now(),
            "error_message": "",
        }
        serializer = ConnectionStatusSerializer(data)
        result = serializer.data
        assert result["status"] == "active"
        assert result["is_healthy"] is True
        assert result["needs_reauthorization"] is False

    def test_error_state(self):
        import uuid

        data = {
            "connection_id": uuid.uuid4(),
            "status": "error",
            "is_healthy": False,
            "needs_reauthorization": True,
            "last_sync_at": None,
            "error_message": "Connection failed",
        }
        serializer = ConnectionStatusSerializer(data)
        assert serializer.data["is_healthy"] is False
        assert serializer.data["error_message"] == "Connection failed"
