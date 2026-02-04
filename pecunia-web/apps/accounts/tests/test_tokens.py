"""
Tests for accounts.tokens module.

Covers BaseTokenGenerator, EmailVerificationTokenGenerator,
PasswordResetTokenGenerator, and TokenService with all branches.
"""
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.tokens import (
    BaseTokenGenerator,
    EmailVerificationTokenGenerator,
    PasswordResetTokenGenerator,
    TokenService,
    email_verification_token_generator,
    password_reset_token_generator,
    token_service,
)


# ---------------------------------------------------------------------------
# EmailVerificationTokenGenerator tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmailVerificationTokenGenerator:
    """Tests for email verification tokens."""

    def test_make_token_returns_string(self, user):
        token = email_verification_token_generator.make_token(user)
        assert isinstance(token, str)
        assert "-" in token

    def test_check_token_valid(self, user):
        token = email_verification_token_generator.make_token(user)
        assert email_verification_token_generator.check_token(user, token) is True

    def test_check_token_wrong_user(self, user, user2):
        token = email_verification_token_generator.make_token(user)
        assert email_verification_token_generator.check_token(user2, token) is False

    def test_check_token_invalid_format(self, user):
        assert email_verification_token_generator.check_token(user, "invalid") is False

    def test_check_token_no_dash(self, user):
        assert email_verification_token_generator.check_token(user, "nodash") is False

    def test_check_token_none_user(self):
        assert email_verification_token_generator.check_token(None, "abc-def") is False

    def test_check_token_none_token(self, user):
        assert email_verification_token_generator.check_token(user, None) is False

    def test_check_token_empty_token(self, user):
        assert email_verification_token_generator.check_token(user, "") is False

    def test_token_invalidated_when_email_verified(self, user):
        token = email_verification_token_generator.make_token(user)
        # Simulate email verification
        user.is_email_verified = True
        user.save()
        assert email_verification_token_generator.check_token(user, token) is False

    def test_token_expired_after_24_hours(self, user):
        gen = EmailVerificationTokenGenerator()
        token = gen.make_token(user)
        # Patch _now to return 25 hours in the future
        future = timezone.now() + timedelta(hours=25)
        with patch.object(gen, "_now", return_value=future):
            assert gen.check_token(user, token) is False

    def test_token_valid_within_24_hours(self, user):
        gen = EmailVerificationTokenGenerator()
        token = gen.make_token(user)
        # Patch _now to return 23 hours in the future
        future = timezone.now() + timedelta(hours=23)
        with patch.object(gen, "_now", return_value=future):
            assert gen.check_token(user, token) is True

    def test_get_expiration_time(self, user):
        token = email_verification_token_generator.make_token(user)
        expiration = email_verification_token_generator.get_expiration_time(token)
        assert expiration is not None
        assert isinstance(expiration, datetime)
        # Should be about 24 hours from now
        delta = expiration - timezone.now()
        assert timedelta(hours=23) < delta < timedelta(hours=25)

    def test_get_expiration_time_invalid_token(self):
        result = email_verification_token_generator.get_expiration_time("invalid")
        assert result is None

    def test_get_token_timestamp(self, user):
        token = email_verification_token_generator.make_token(user)
        ts = email_verification_token_generator.get_token_timestamp(token)
        assert ts is not None
        assert isinstance(ts, datetime)

    def test_get_token_timestamp_invalid(self):
        result = email_verification_token_generator.get_token_timestamp("badformat")
        assert result is None


# ---------------------------------------------------------------------------
# PasswordResetTokenGenerator tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPasswordResetTokenGenerator:
    """Tests for password reset tokens."""

    def test_make_token_returns_string(self, user):
        token = password_reset_token_generator.make_token(user)
        assert isinstance(token, str)
        assert "-" in token

    def test_check_token_valid(self, user):
        token = password_reset_token_generator.make_token(user)
        assert password_reset_token_generator.check_token(user, token) is True

    def test_check_token_wrong_user(self, user, user2):
        token = password_reset_token_generator.make_token(user)
        assert password_reset_token_generator.check_token(user2, token) is False

    def test_token_invalidated_when_password_changes(self, user):
        token = password_reset_token_generator.make_token(user)
        # Change password
        user.set_password("NewlyChangedP@ss123!")
        user.save()
        assert password_reset_token_generator.check_token(user, token) is False

    def test_token_expired_after_1_hour(self, user):
        gen = PasswordResetTokenGenerator()
        token = gen.make_token(user)
        future = timezone.now() + timedelta(hours=2)
        with patch.object(gen, "_now", return_value=future):
            assert gen.check_token(user, token) is False

    def test_token_valid_within_1_hour(self, user):
        gen = PasswordResetTokenGenerator()
        token = gen.make_token(user)
        future = timezone.now() + timedelta(minutes=50)
        with patch.object(gen, "_now", return_value=future):
            assert gen.check_token(user, token) is True

    def test_get_expiration_time(self, user):
        token = password_reset_token_generator.make_token(user)
        expiration = password_reset_token_generator.get_expiration_time(token)
        assert expiration is not None
        delta = expiration - timezone.now()
        assert timedelta(minutes=50) < delta < timedelta(hours=2)

    def test_get_expiration_time_invalid_token(self):
        result = password_reset_token_generator.get_expiration_time("bad")
        assert result is None

    def test_hash_includes_last_login(self, user):
        """Token includes last_login in hash, changing it invalidates token."""
        token = password_reset_token_generator.make_token(user)
        user.last_login = timezone.now()
        user.save()
        assert password_reset_token_generator.check_token(user, token) is False

    def test_hash_works_without_last_login(self, db):
        user = User.objects.create_user(
            email="nologin@example.com",
            password="SomeP@ssw0rd12!",
        )
        token = password_reset_token_generator.make_token(user)
        assert password_reset_token_generator.check_token(user, token) is True


# ---------------------------------------------------------------------------
# BaseTokenGenerator tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBaseTokenGenerator:
    """Tests for base token generator."""

    def test_is_expired_raises_not_implemented(self, user):
        gen = BaseTokenGenerator()
        token = gen.make_token(user)
        with pytest.raises(NotImplementedError):
            gen.check_token(user, token)

    def test_secret_defaults_to_secret_key(self):
        gen = BaseTokenGenerator()
        from django.conf import settings
        assert gen.secret == settings.SECRET_KEY


# ---------------------------------------------------------------------------
# TokenService tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTokenService:
    """Tests for the TokenService convenience class."""

    def test_generate_email_verification_token(self, user):
        token = token_service.generate_email_verification_token(user)
        assert isinstance(token, str)

    def test_verify_email_token(self, user):
        token = token_service.generate_email_verification_token(user)
        assert token_service.verify_email_token(user, token) is True

    def test_verify_email_token_invalid(self, user):
        assert token_service.verify_email_token(user, "bad-token") is False

    def test_generate_password_reset_token(self, user):
        token = token_service.generate_password_reset_token(user)
        assert isinstance(token, str)

    def test_verify_password_reset_token(self, user):
        token = token_service.generate_password_reset_token(user)
        assert token_service.verify_password_reset_token(user, token) is True

    def test_verify_password_reset_token_invalid(self, user):
        assert token_service.verify_password_reset_token(user, "bad-token") is False

    def test_get_email_verification_expiration(self, user):
        token = token_service.generate_email_verification_token(user)
        exp = token_service.get_email_verification_expiration(token)
        assert exp is not None

    def test_get_password_reset_expiration(self, user):
        token = token_service.generate_password_reset_token(user)
        exp = token_service.get_password_reset_expiration(token)
        assert exp is not None

    def test_get_email_verification_expiration_invalid(self):
        exp = token_service.get_email_verification_expiration("bad")
        assert exp is None

    def test_get_password_reset_expiration_invalid(self):
        exp = token_service.get_password_reset_expiration("bad")
        assert exp is None
