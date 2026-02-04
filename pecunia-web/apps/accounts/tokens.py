"""
Token generators for email verification and password reset.
Implements secure, time-limited tokens with cryptographic signing.
"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator as DjangoPasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36
from django.utils import timezone

User = get_user_model()


class BaseTokenGenerator:
    """
    Base class for generating and validating secure tokens.
    Tokens include timestamp for expiration checking.
    """

    key_salt = "accounts.tokens.BaseTokenGenerator"
    secret = None

    def __init__(self):
        self.secret = self.secret or settings.SECRET_KEY

    def make_token(self, user) -> str:
        """
        Generate a token for the given user.
        Returns a token string that includes timestamp.
        """
        return self._make_token_with_timestamp(
            user,
            self._num_seconds(self._now())
        )

    def check_token(self, user, token: str) -> bool:
        """
        Validate the token for the given user.
        Returns True if valid and not expired.
        """
        if not (user and token):
            return False

        try:
            ts_b36, _ = token.split("-", 1)
            ts = base36_to_int(ts_b36)
        except (ValueError, TypeError):
            return False

        # Check token validity
        if not constant_time_compare(
            self._make_token_with_timestamp(user, ts),
            token
        ):
            return False

        # Check expiration
        if self._is_expired(ts):
            return False

        return True

    def get_token_timestamp(self, token: str) -> Optional[datetime]:
        """
        Extract the timestamp from a token.
        Returns None if token format is invalid.
        """
        try:
            ts_b36, _ = token.split("-", 1)
            ts = base36_to_int(ts_b36)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, TypeError):
            return None

    def _make_token_with_timestamp(self, user, timestamp: int) -> str:
        """
        Generate the actual token with timestamp.
        """
        ts_b36 = int_to_base36(timestamp)
        hash_value = self._make_hash_value(user, timestamp)

        hash_string = salted_hmac(
            self.key_salt,
            hash_value,
            secret=self.secret,
            algorithm='sha256'
        ).hexdigest()[::2]  # Use every other character for shorter token

        return f"{ts_b36}-{hash_string}"

    def _make_hash_value(self, user, timestamp: int) -> str:
        """
        Create the hash value for the token.
        Subclasses should override to include relevant user state.
        """
        return f"{user.pk}{timestamp}{user.is_active}"

    def _is_expired(self, timestamp: int) -> bool:
        """
        Check if the token timestamp has expired.
        Subclasses should override to define expiration period.
        """
        raise NotImplementedError("Subclasses must implement _is_expired")

    def _num_seconds(self, dt: datetime) -> int:
        """Convert datetime to timestamp."""
        return int(dt.timestamp())

    def _now(self) -> datetime:
        """Get current datetime (timezone-aware)."""
        return timezone.now()


class EmailVerificationTokenGenerator(BaseTokenGenerator):
    """
    Token generator for email verification.
    Tokens expire after 24 hours.
    """

    key_salt = "accounts.tokens.EmailVerificationTokenGenerator"
    EXPIRATION_HOURS = 24

    def _make_hash_value(self, user, timestamp: int) -> str:
        """
        Include email verification status in hash.
        Token becomes invalid when email is verified.
        """
        email_verified = getattr(user, 'is_email_verified', getattr(user, 'email_verified', False))
        return (
            f"{user.pk}"
            f"{timestamp}"
            f"{user.is_active}"
            f"{user.email}"
            f"{email_verified}"
        )

    def _is_expired(self, timestamp: int) -> bool:
        """
        Check if token is older than 24 hours.
        """
        now = self._num_seconds(self._now())
        expiration_seconds = self.EXPIRATION_HOURS * 60 * 60
        return (now - timestamp) > expiration_seconds

    def get_expiration_time(self, token: str) -> Optional[datetime]:
        """
        Get the expiration datetime for a token.
        """
        created = self.get_token_timestamp(token)
        if created:
            return created + timedelta(hours=self.EXPIRATION_HOURS)
        return None


class PasswordResetTokenGenerator(BaseTokenGenerator):
    """
    Token generator for password reset.
    Tokens expire after 1 hour for security.
    """

    key_salt = "accounts.tokens.PasswordResetTokenGenerator"
    EXPIRATION_HOURS = 1

    def _make_hash_value(self, user, timestamp: int) -> str:
        """
        Include password hash in token hash.
        Token becomes invalid when password is changed.
        """
        # Get login timestamp if available
        login_timestamp = ""
        if hasattr(user, 'last_login') and user.last_login:
            login_timestamp = user.last_login.replace(
                microsecond=0, tzinfo=None
            ).isoformat()

        return (
            f"{user.pk}"
            f"{user.password}"  # Invalidates token when password changes
            f"{timestamp}"
            f"{login_timestamp}"
            f"{user.email}"
        )

    def _is_expired(self, timestamp: int) -> bool:
        """
        Check if token is older than 1 hour.
        """
        now = self._num_seconds(self._now())
        expiration_seconds = self.EXPIRATION_HOURS * 60 * 60
        return (now - timestamp) > expiration_seconds

    def get_expiration_time(self, token: str) -> Optional[datetime]:
        """
        Get the expiration datetime for a token.
        """
        created = self.get_token_timestamp(token)
        if created:
            return created + timedelta(hours=self.EXPIRATION_HOURS)
        return None


class TokenService:
    """
    Service class for token operations.
    Provides a unified interface for token generation and validation.
    """

    def __init__(self):
        self.email_verification_generator = EmailVerificationTokenGenerator()
        self.password_reset_generator = PasswordResetTokenGenerator()

    def generate_email_verification_token(self, user) -> str:
        """Generate an email verification token."""
        return self.email_verification_generator.make_token(user)

    def verify_email_token(self, user, token: str) -> bool:
        """Verify an email verification token."""
        return self.email_verification_generator.check_token(user, token)

    def generate_password_reset_token(self, user) -> str:
        """Generate a password reset token."""
        return self.password_reset_generator.make_token(user)

    def verify_password_reset_token(self, user, token: str) -> bool:
        """Verify a password reset token."""
        return self.password_reset_generator.check_token(user, token)

    def get_email_verification_expiration(self, token: str) -> Optional[datetime]:
        """Get expiration time for email verification token."""
        return self.email_verification_generator.get_expiration_time(token)

    def get_password_reset_expiration(self, token: str) -> Optional[datetime]:
        """Get expiration time for password reset token."""
        return self.password_reset_generator.get_expiration_time(token)


# Default instances for convenience
email_verification_token_generator = EmailVerificationTokenGenerator()
password_reset_token_generator = PasswordResetTokenGenerator()
token_service = TokenService()
