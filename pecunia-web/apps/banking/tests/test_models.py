"""
Tests for banking models.

Covers EncryptedFieldMixin, BankConnection, BankAccount, and SyncLog.
"""
import os
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet, InvalidToken
from django.utils import timezone

from apps.banking.models import BankAccount, BankConnection, EncryptedFieldMixin, SyncLog


# ---------------------------------------------------------------------------
# EncryptedFieldMixin
# ---------------------------------------------------------------------------


class TestEncryptedFieldMixin:
    """Tests for the EncryptedFieldMixin encryption helpers."""

    def test_get_encryption_key_from_settings(self, settings):
        key = Fernet.generate_key().decode()
        settings.BANK_ENCRYPTION_KEY = key
        result = EncryptedFieldMixin.get_encryption_key()
        assert result == key.encode()

    def test_get_encryption_key_from_env(self, settings):
        """Falls back to environment variable when setting is absent."""
        settings.BANK_ENCRYPTION_KEY = None
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"BANK_ENCRYPTION_KEY": key}):
            result = EncryptedFieldMixin.get_encryption_key()
            assert result == key.encode()

    def test_get_encryption_key_missing_raises(self, settings):
        settings.BANK_ENCRYPTION_KEY = None
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if present
            os.environ.pop("BANK_ENCRYPTION_KEY", None)
            with pytest.raises(ValueError, match="BANK_ENCRYPTION_KEY must be set"):
                EncryptedFieldMixin.get_encryption_key()

    def test_get_encryption_key_bytes_input(self, settings):
        """When the setting is already bytes it should be returned as-is."""
        key = Fernet.generate_key()  # bytes
        settings.BANK_ENCRYPTION_KEY = key
        result = EncryptedFieldMixin.get_encryption_key()
        assert result == key

    def test_encrypt_value_returns_ciphertext(self, encryption_key):
        ciphertext = EncryptedFieldMixin.encrypt_value("my_secret")
        assert ciphertext is not None
        assert ciphertext != "my_secret"
        # Must be a valid Fernet token string
        assert isinstance(ciphertext, str)

    def test_encrypt_value_none_returns_none(self, encryption_key):
        assert EncryptedFieldMixin.encrypt_value(None) is None

    def test_encrypt_value_empty_string_returns_none(self, encryption_key):
        assert EncryptedFieldMixin.encrypt_value("") is None

    def test_decrypt_value_round_trip(self, encryption_key):
        plaintext = "super_secret_token_xyz"
        ciphertext = EncryptedFieldMixin.encrypt_value(plaintext)
        decrypted = EncryptedFieldMixin.decrypt_value(ciphertext)
        assert decrypted == plaintext

    def test_decrypt_value_none_returns_none(self, encryption_key):
        assert EncryptedFieldMixin.decrypt_value(None) is None

    def test_decrypt_value_empty_string_returns_none(self, encryption_key):
        assert EncryptedFieldMixin.decrypt_value("") is None

    def test_decrypt_value_wrong_key_raises(self, settings):
        """Decrypting with a different key must fail."""
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        settings.BANK_ENCRYPTION_KEY = key1
        ciphertext = EncryptedFieldMixin.encrypt_value("secret")

        settings.BANK_ENCRYPTION_KEY = key2
        with pytest.raises(InvalidToken):
            EncryptedFieldMixin.decrypt_value(ciphertext)


# ---------------------------------------------------------------------------
# BankConnection model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBankConnection:
    """Tests for the BankConnection model."""

    def test_str_representation(self, bank_connection):
        assert str(bank_connection) == "Test Bank (plaid)"

    def test_access_token_encryption_round_trip(self, bank_connection):
        """Setting access_token encrypts; reading decrypts."""
        bank_connection.access_token = "new_access_token"
        bank_connection.save()
        bank_connection.refresh_from_db()
        assert bank_connection.access_token == "new_access_token"
        # The raw DB field should differ
        assert bank_connection._access_token_encrypted != "new_access_token"

    def test_refresh_token_encryption_round_trip(self, bank_connection):
        bank_connection.refresh_token = "new_refresh_token"
        bank_connection.save()
        bank_connection.refresh_from_db()
        assert bank_connection.refresh_token == "new_refresh_token"
        assert bank_connection._refresh_token_encrypted != "new_refresh_token"

    def test_access_token_none_when_not_set(self, user, encryption_key, db):
        conn = BankConnection.objects.create(
            user=user,
            provider="plaid",
            institution_id="ins_new",
            institution_name="No Token Bank",
        )
        assert conn.access_token is None

    def test_refresh_token_none_when_not_set(self, user, encryption_key, db):
        conn = BankConnection.objects.create(
            user=user,
            provider="plaid",
            institution_id="ins_no_refresh",
            institution_name="No Refresh Bank",
        )
        assert conn.refresh_token is None

    # -- is_token_expired -----------------------------------------------------

    def test_is_token_expired_when_not_set(self, bank_connection):
        """Defaults to True (safe default) when token_expires_at is None."""
        bank_connection.token_expires_at = None
        assert bank_connection.is_token_expired is True

    def test_is_token_expired_when_future(self, bank_connection):
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        assert bank_connection.is_token_expired is False

    def test_is_token_expired_when_past(self, bank_connection):
        bank_connection.token_expires_at = timezone.now() - timedelta(hours=1)
        assert bank_connection.is_token_expired is True

    def test_is_token_expired_at_exact_now(self, bank_connection):
        """Edge case: token_expires_at == now should be expired (>= comparison)."""
        now = timezone.now()
        bank_connection.token_expires_at = now
        with patch("apps.banking.models.timezone.now", return_value=now):
            assert bank_connection.is_token_expired is True

    # -- is_consent_expired ---------------------------------------------------

    def test_is_consent_expired_when_not_set(self, bank_connection):
        """Defaults to False when consent_expires_at is None."""
        bank_connection.consent_expires_at = None
        assert bank_connection.is_consent_expired is False

    def test_is_consent_expired_when_future(self, bank_connection):
        bank_connection.consent_expires_at = timezone.now() + timedelta(days=90)
        assert bank_connection.is_consent_expired is False

    def test_is_consent_expired_when_past(self, bank_connection):
        bank_connection.consent_expires_at = timezone.now() - timedelta(days=1)
        assert bank_connection.is_consent_expired is True

    # -- needs_reauthorization ------------------------------------------------

    def test_needs_reauthorization_active_valid_token(self, bank_connection):
        bank_connection.status = "active"
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.consent_expires_at = None
        assert bank_connection.needs_reauthorization is False

    def test_needs_reauthorization_expired_status(self, bank_connection):
        bank_connection.status = "expired"
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        assert bank_connection.needs_reauthorization is True

    def test_needs_reauthorization_error_status(self, bank_connection):
        bank_connection.status = "error"
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        assert bank_connection.needs_reauthorization is True

    def test_needs_reauthorization_revoked_status(self, bank_connection):
        bank_connection.status = "revoked"
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        assert bank_connection.needs_reauthorization is True

    def test_needs_reauthorization_token_expired(self, bank_connection):
        bank_connection.status = "active"
        bank_connection.token_expires_at = timezone.now() - timedelta(hours=1)
        assert bank_connection.needs_reauthorization is True

    def test_needs_reauthorization_consent_expired(self, bank_connection):
        bank_connection.status = "active"
        bank_connection.token_expires_at = timezone.now() + timedelta(hours=1)
        bank_connection.consent_expires_at = timezone.now() - timedelta(days=1)
        assert bank_connection.needs_reauthorization is True

    def test_needs_reauthorization_token_not_set(self, bank_connection):
        """token_expires_at=None -> is_token_expired=True -> needs_reauth."""
        bank_connection.status = "active"
        bank_connection.token_expires_at = None
        assert bank_connection.needs_reauthorization is True

    # -- mark_sync_success ----------------------------------------------------

    def test_mark_sync_success(self, bank_connection):
        bank_connection.sync_error_count = 2
        bank_connection.status = "error"
        bank_connection.mark_sync_success()
        bank_connection.refresh_from_db()

        assert bank_connection.status == "active"
        assert bank_connection.last_sync_status == "success"
        assert bank_connection.sync_error_count == 0
        assert bank_connection.last_sync_at is not None

    # -- mark_sync_error ------------------------------------------------------

    def test_mark_sync_error_increments_count(self, bank_connection):
        bank_connection.sync_error_count = 0
        bank_connection.status = "active"
        bank_connection.save()

        bank_connection.mark_sync_error("connection timeout")
        bank_connection.refresh_from_db()

        assert bank_connection.sync_error_count == 1
        assert bank_connection.last_sync_status == "error"
        assert bank_connection.status_message == "connection timeout"
        # status should still be active (< 3 errors)
        assert bank_connection.status == "active"

    def test_mark_sync_error_sets_error_status_at_threshold(self, bank_connection):
        """After 3 consecutive errors, status flips to 'error'."""
        bank_connection.sync_error_count = 2
        bank_connection.status = "active"
        bank_connection.save()

        bank_connection.mark_sync_error("third failure")
        bank_connection.refresh_from_db()

        assert bank_connection.sync_error_count == 3
        assert bank_connection.status == "error"

    def test_mark_sync_error_above_threshold(self, bank_connection):
        bank_connection.sync_error_count = 5
        bank_connection.status = "error"
        bank_connection.save()

        bank_connection.mark_sync_error("another failure")
        bank_connection.refresh_from_db()

        assert bank_connection.sync_error_count == 6
        assert bank_connection.status == "error"

    # -- Meta / constraints ---------------------------------------------------

    def test_unique_together_constraint(self, user, encryption_key, db):
        BankConnection.objects.create(
            user=user,
            provider="truelayer",
            institution_id="inst_abc",
            institution_name="Bank A",
        )
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            BankConnection.objects.create(
                user=user,
                provider="truelayer",
                institution_id="inst_abc",
                institution_name="Bank A duplicate",
            )

    def test_ordering_by_created_at_desc(self, user, encryption_key, db):
        c1 = BankConnection.objects.create(
            user=user,
            provider="plaid",
            institution_id="ins_first",
            institution_name="First",
        )
        c2 = BankConnection.objects.create(
            user=user,
            provider="plaid",
            institution_id="ins_second",
            institution_name="Second",
        )
        conns = list(BankConnection.objects.filter(user=user))
        # Most recent first
        assert conns[0].pk == c2.pk
        assert conns[1].pk == c1.pk


# ---------------------------------------------------------------------------
# BankAccount model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBankAccount:
    """Tests for the BankAccount model."""

    def test_str_with_default_name(self, bank_account):
        assert str(bank_account) == "Test Checking (checking)"

    def test_str_with_custom_name(self, bank_account):
        bank_account.custom_name = "My Main"
        assert str(bank_account) == "My Main (checking)"

    def test_display_name_without_custom(self, bank_account):
        bank_account.custom_name = ""
        assert bank_account.display_name == "Test Checking"

    def test_display_name_with_custom(self, bank_account):
        bank_account.custom_name = "Custom Label"
        assert bank_account.display_name == "Custom Label"

    def test_institution_name_from_connection(self, bank_account):
        assert bank_account.institution_name == "Test Bank"

    def test_provider_from_connection(self, bank_account):
        assert bank_account.provider == "plaid"

    def test_update_balance_with_available(self, bank_account):
        bank_account.update_balance(
            balance=Decimal("6000.00"),
            available_balance=Decimal("5900.00"),
        )
        bank_account.refresh_from_db()
        assert bank_account.balance == Decimal("6000.00")
        assert bank_account.available_balance == Decimal("5900.00")
        assert bank_account.balance_updated_at is not None
        assert bank_account.last_sync_at is not None

    def test_update_balance_without_available(self, bank_account):
        original_available = bank_account.available_balance
        bank_account.update_balance(balance=Decimal("7000.00"))
        bank_account.refresh_from_db()
        assert bank_account.balance == Decimal("7000.00")
        # available_balance should stay the same (None passed -> unchanged)
        assert bank_account.available_balance == original_available

    def test_unique_together_connection_provider_account(
        self, user, bank_connection, db
    ):
        from django.db import IntegrityError

        BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="unique_acc_id",
            name="Account 1",
        )
        with pytest.raises(IntegrityError):
            BankAccount.objects.create(
                user=user,
                connection=bank_connection,
                provider_account_id="unique_acc_id",
                name="Account 2",
            )

    def test_ordering_by_name(self, user, bank_connection, db):
        BankAccount.objects.all().delete()
        a = BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="z_acc",
            name="Zeta Account",
        )
        b = BankAccount.objects.create(
            user=user,
            connection=bank_connection,
            provider_account_id="a_acc",
            name="Alpha Account",
        )
        accs = list(BankAccount.objects.filter(user=user))
        assert accs[0].pk == b.pk
        assert accs[1].pk == a.pk


# ---------------------------------------------------------------------------
# SyncLog model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncLog:
    """Tests for the SyncLog model."""

    def test_str_representation(self, sync_log):
        s = str(sync_log)
        assert "full" in s
        assert "success" in s

    def test_duration_seconds_completed(self, sync_log):
        sync_log.completed_at = sync_log.started_at + timedelta(seconds=12.5)
        sync_log.save()
        assert sync_log.duration_seconds == pytest.approx(12.5, abs=0.1)

    def test_duration_seconds_not_completed(self, sync_log):
        sync_log.completed_at = None
        assert sync_log.duration_seconds is None

    def test_ordering_by_started_at_desc(self, bank_connection, db):
        s1 = SyncLog.objects.create(
            connection=bank_connection,
            sync_type="full",
            status="success",
        )
        s2 = SyncLog.objects.create(
            connection=bank_connection,
            sync_type="incremental",
            status="started",
        )
        logs = list(SyncLog.objects.filter(connection=bank_connection))
        assert logs[0].pk == s2.pk
        assert logs[1].pk == s1.pk

    def test_default_fields(self, bank_connection, db):
        log = SyncLog.objects.create(
            connection=bank_connection,
            sync_type="balance",
            status="started",
        )
        assert log.accounts_synced == 0
        assert log.transactions_synced == 0
        assert log.error_message == ""
        assert log.completed_at is None
