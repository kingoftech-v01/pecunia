"""
Tests for accounts.totp module.

Covers TOTPDevice model, TOTPService class, and convenience functions
with all branches including replay protection, QR codes, and setup flow.
"""
import base64
from unittest.mock import patch, MagicMock

import pyotp
import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.totp import (
    TOTPDevice,
    TOTPService,
    generate_secret,
    get_qr_code,
    verify_totp,
)


# ---------------------------------------------------------------------------
# TOTPDevice model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTOTPDevice:
    """Tests for the TOTPDevice model."""

    def test_create_device(self, user):
        device = TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=False,
        )
        assert device.pk is not None
        assert device.confirmed is False
        assert device.last_used_counter == -1

    def test_str_representation(self, user):
        device = TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
        )
        assert str(device) == f"TOTP Device for {user.email}"

    def test_default_name(self, user):
        device = TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
        )
        assert device.name == "Authenticator App"

    def test_one_to_one_constraint(self, user):
        TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
        )
        with pytest.raises(IntegrityError):
            TOTPDevice.objects.create(
                user=user,
                secret=TOTPService.generate_secret(),
            )

    def test_verify_delegates_to_service(self, user):
        secret = TOTPService.generate_secret()
        device = TOTPDevice.objects.create(
            user=user,
            secret=secret,
            confirmed=True,
        )
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        code = totp.now()
        result = device.verify(code)
        assert result is True

    def test_verbose_name(self):
        assert TOTPDevice._meta.verbose_name == "TOTP Device"
        assert TOTPDevice._meta.verbose_name_plural == "TOTP Devices"


# ---------------------------------------------------------------------------
# TOTPService tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTOTPService:
    """Tests for the TOTPService class."""

    def test_generate_secret_returns_base32(self):
        secret = TOTPService.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) == 32
        # Should be valid base32
        base64.b32decode(secret)

    def test_generate_secret_unique(self):
        secrets = {TOTPService.generate_secret() for _ in range(10)}
        assert len(secrets) == 10

    def test_get_totp_returns_pyotp_instance(self):
        secret = TOTPService.generate_secret()
        totp = TOTPService.get_totp(secret)
        assert isinstance(totp, pyotp.TOTP)
        assert totp.digits == TOTPService.DIGITS
        assert totp.interval == TOTPService.INTERVAL

    def test_verify_totp_valid_code(self):
        secret = TOTPService.generate_secret()
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        code = totp.now()
        assert TOTPService.verify_totp(secret, code) is True

    def test_verify_totp_invalid_code(self):
        secret = TOTPService.generate_secret()
        assert TOTPService.verify_totp(secret, "000000") is False

    def test_verify_totp_empty_code(self):
        secret = TOTPService.generate_secret()
        assert TOTPService.verify_totp(secret, "") is False

    def test_verify_totp_none_code(self):
        secret = TOTPService.generate_secret()
        assert TOTPService.verify_totp(secret, None) is False

    def test_verify_totp_empty_secret(self):
        assert TOTPService.verify_totp("", "123456") is False

    def test_verify_totp_none_secret(self):
        assert TOTPService.verify_totp(None, "123456") is False

    def test_verify_totp_non_digit_code(self):
        secret = TOTPService.generate_secret()
        assert TOTPService.verify_totp(secret, "abcdef") is False

    def test_verify_totp_wrong_length(self):
        secret = TOTPService.generate_secret()
        assert TOTPService.verify_totp(secret, "12345") is False
        assert TOTPService.verify_totp(secret, "1234567") is False

    def test_verify_totp_strips_spaces(self):
        secret = TOTPService.generate_secret()
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        code = totp.now()
        # Add spaces - should still work
        spaced = f"{code[:3]} {code[3:]}"
        assert TOTPService.verify_totp(secret, spaced) is True

    def test_verify_totp_with_device_replay_protection(self, user):
        secret = TOTPService.generate_secret()
        device = TOTPDevice.objects.create(
            user=user,
            secret=secret,
            confirmed=True,
        )
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        code = totp.now()

        # First use should succeed
        assert TOTPService.verify_totp(secret, code, device) is True

        # Replay should fail (same counter)
        assert TOTPService.verify_totp(secret, code, device) is False

    def test_verify_totp_with_device_updates_last_used(self, user):
        secret = TOTPService.generate_secret()
        device = TOTPDevice.objects.create(
            user=user,
            secret=secret,
            confirmed=True,
        )
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        code = totp.now()

        TOTPService.verify_totp(secret, code, device)
        device.refresh_from_db()
        assert device.last_used_at is not None
        assert device.last_used_counter > -1

    def test_get_provisioning_uri(self):
        secret = TOTPService.generate_secret()
        uri = TOTPService.get_provisioning_uri(secret, "test@example.com")
        assert uri.startswith("otpauth://totp/")
        # Email may be URL-encoded (@ -> %40)
        assert "test" in uri and "example.com" in uri
        assert "Pecunia" in uri

    def test_get_qr_code_base64(self):
        secret = TOTPService.generate_secret()
        qr = TOTPService.get_qr_code(secret, "test@example.com")
        assert qr.startswith("data:image/png;base64,")

    def test_get_qr_code_svg(self):
        secret = TOTPService.generate_secret()
        qr = TOTPService.get_qr_code(secret, "test@example.com", format="svg")
        assert "<svg" in qr.lower() or "<?xml" in qr.lower()

    def test_setup_device(self, user):
        device, qr_code = TOTPService.setup_device(user)
        assert device is not None
        assert device.user == user
        assert device.confirmed is False
        assert qr_code.startswith("data:image/png;base64,")

    def test_setup_device_removes_unconfirmed(self, user):
        # Create an unconfirmed device first
        TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=False,
        )
        device, _ = TOTPService.setup_device(user)
        # Only one device should exist
        assert TOTPDevice.objects.filter(user=user).count() == 1
        assert device.confirmed is False

    def test_setup_device_raises_if_confirmed_exists(self, user):
        TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=True,
        )
        with pytest.raises(IntegrityError, match="already has 2FA enabled"):
            TOTPService.setup_device(user)

    def test_confirm_device(self, user):
        secret = TOTPService.generate_secret()
        device = TOTPDevice.objects.create(
            user=user,
            secret=secret,
            confirmed=False,
        )
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        code = totp.now()

        result = TOTPService.confirm_device(device, code)
        assert result is True
        device.refresh_from_db()
        assert device.confirmed is True

    def test_confirm_device_invalid_code(self, user):
        secret = TOTPService.generate_secret()
        device = TOTPDevice.objects.create(
            user=user,
            secret=secret,
            confirmed=False,
        )
        result = TOTPService.confirm_device(device, "000000")
        assert result is False
        device.refresh_from_db()
        assert device.confirmed is False

    def test_confirm_device_already_confirmed(self, user):
        device = TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=True,
        )
        result = TOTPService.confirm_device(device, "anything")
        assert result is True

    def test_get_user_device_found(self, user):
        device = TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=True,
        )
        result = TOTPService.get_user_device(user)
        assert result == device

    def test_get_user_device_not_found(self, user):
        result = TOTPService.get_user_device(user)
        assert result is None

    def test_get_user_device_unconfirmed_not_returned(self, user):
        TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=False,
        )
        result = TOTPService.get_user_device(user)
        assert result is None

    def test_is_2fa_enabled_true(self, user):
        TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=True,
        )
        assert TOTPService.is_2fa_enabled(user) is True

    def test_is_2fa_enabled_false(self, user):
        assert TOTPService.is_2fa_enabled(user) is False

    def test_disable_2fa(self, user):
        TOTPDevice.objects.create(
            user=user,
            secret=TOTPService.generate_secret(),
            confirmed=True,
        )
        result = TOTPService.disable_2fa(user)
        assert result is True
        assert not TOTPDevice.objects.filter(user=user).exists()

    def test_disable_2fa_no_device(self, user):
        result = TOTPService.disable_2fa(user)
        assert result is False

    def test_setup_device_integrity_error_reraise(self, user):
        """When create raises IntegrityError (not from confirmed check), it re-raises."""
        # Simulate: no confirmed device exists, unconfirmed was deleted,
        # but the create itself fails (e.g. race condition).
        with patch.object(
            TOTPDevice.objects, "filter"
        ) as mock_filter:
            # First call (confirmed=True check) returns queryset with exists() -> False
            # Second call (confirmed=False delete) returns queryset
            mock_qs_confirmed = MagicMock()
            mock_qs_confirmed.exists.return_value = False
            mock_qs_unconfirmed = MagicMock()
            mock_qs_unconfirmed.delete.return_value = (0, {})
            mock_filter.side_effect = [mock_qs_confirmed, mock_qs_unconfirmed]

            with patch.object(
                TOTPDevice.objects, "create",
                side_effect=IntegrityError("Duplicate key")
            ):
                with pytest.raises(IntegrityError, match="Duplicate key"):
                    TOTPService.setup_device(user)

    def test_verify_totp_with_device_invalid_code(self, user):
        """Verify with device but invalid code should return False."""
        secret = TOTPService.generate_secret()
        device = TOTPDevice.objects.create(
            user=user,
            secret=secret,
            confirmed=True,
        )
        result = TOTPService.verify_totp(secret, "000000", device)
        assert result is False


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_secret(self):
        secret = generate_secret()
        assert isinstance(secret, str)
        assert len(secret) == 32

    @pytest.mark.django_db
    def test_verify_totp_function(self):
        secret = generate_secret()
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        code = totp.now()
        assert verify_totp(secret, code) is True
        assert verify_totp(secret, "000000") is False

    def test_get_qr_code_function(self):
        secret = generate_secret()
        qr = get_qr_code(secret, "test@example.com")
        assert qr.startswith("data:image/png;base64,")
