"""
Email service for account-related emails.
Handles verification, password reset, and welcome emails.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode

from .tokens import (
    email_verification_token_generator,
    password_reset_token_generator,
)

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when email rate limit is exceeded."""
    pass


@dataclass
class EmailConfig:
    """Configuration for email sending."""
    from_email: str = None
    reply_to: List[str] = None
    verification_url_name: str = "accounts:verify_email"
    password_reset_url_name: str = "accounts:reset_password"
    site_name: str = "Pecunia"
    support_email: str = None

    def __post_init__(self):
        if self.from_email is None:
            self.from_email = getattr(
                settings, 'DEFAULT_FROM_EMAIL',
                'noreply@pecunia.com'
            )
        if self.support_email is None:
            self.support_email = getattr(
                settings, 'SUPPORT_EMAIL',
                'support@pecunia.com'
            )
        if self.reply_to is None:
            self.reply_to = [self.support_email]


class EmailService:
    """
    Service class for sending account-related emails.
    Includes rate limiting and template rendering.
    """

    # Rate limiting settings (per user)
    RATE_LIMIT_VERIFICATION = 3  # max emails per hour
    RATE_LIMIT_PASSWORD_RESET = 5  # max emails per hour
    RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds

    def __init__(self, config: EmailConfig = None):
        self.config = config or EmailConfig()

    def _get_rate_limit_key(self, user_id: int, email_type: str) -> str:
        """Generate cache key for rate limiting."""
        return f"email_rate_limit:{email_type}:{user_id}"

    def _acquire_rate_limit(self, user_id: int, email_type: str, limit: int) -> bool:
        """
        Atomically check and increment the rate limit counter.

        Uses atomic cache operations to avoid the TOCTOU race condition
        inherent in a separate check-then-increment approach.

        Returns True if within limit (slot acquired), False if exceeded.
        """
        key = self._get_rate_limit_key(user_id, email_type)
        try:
            # Try to increment atomically.  If the key already exists
            # this is an atomic read-and-increment operation.
            new_value = cache.incr(key)
        except ValueError:
            # Key does not exist yet -- initialise it to 1 with the
            # full rate-limit window as its TTL.  There is a small
            # window where two concurrent requests could both fail the
            # incr and race to set, but add() is atomic: only the first
            # caller wins; the others fall through to incr again.
            added = cache.add(key, 1, self.RATE_LIMIT_WINDOW)
            if added:
                new_value = 1
            else:
                # Another thread created the key between our incr and add.
                new_value = cache.incr(key)

        if new_value > limit:
            # We incremented past the limit -- roll back the counter
            # so it stays accurate for future checks.
            try:
                cache.decr(key)
            except ValueError:
                pass
            return False

        return True

    def _get_base_url(self) -> str:
        """Get the base URL for the application."""
        return getattr(settings, 'SITE_URL', 'http://localhost:8000')

    def _build_verification_url(self, user, token: str) -> str:
        """Build the email verification URL."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        path = reverse(
            self.config.verification_url_name,
            kwargs={'uidb64': uid, 'token': token}
        )
        return f"{self._get_base_url()}{path}"

    def _build_password_reset_url(self, user, token: str) -> str:
        """Build the password reset URL."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        path = reverse(
            self.config.password_reset_url_name,
            kwargs={'uidb64': uid, 'token': token}
        )
        return f"{self._get_base_url()}{path}"

    def _send_html_email(
        self,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        recipient_email: str,
        fail_silently: bool = False
    ) -> bool:
        """
        Send an HTML email with plain text fallback.
        Returns True if successful.
        """
        try:
            # Render HTML content
            html_content = render_to_string(template_name, context)
            # Create plain text version
            text_content = strip_tags(html_content)

            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.config.from_email,
                to=[recipient_email],
                reply_to=self.config.reply_to
            )
            email.attach_alternative(html_content, "text/html")

            # Send email
            email.send(fail_silently=fail_silently)

            logger.info(
                f"Email sent successfully: {subject} to {recipient_email}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send email: {subject} to {recipient_email}. "
                f"Error: {str(e)}"
            )
            if not fail_silently:
                raise
            return False

    def send_verification_email(
        self,
        user,
        fail_silently: bool = False
    ) -> bool:
        """
        Send email verification email to user.

        Args:
            user: User instance
            fail_silently: If True, suppress exceptions

        Returns:
            True if email sent successfully

        Raises:
            RateLimitExceeded: If user has exceeded rate limit
        """
        # Atomically acquire a rate-limit slot before doing any work.
        if not self._acquire_rate_limit(
            user.id, 'verification', self.RATE_LIMIT_VERIFICATION
        ):
            raise RateLimitExceeded(
                "Too many verification emails sent. Please try again later."
            )

        # Generate token and URL
        token = email_verification_token_generator.make_token(user)
        verification_url = self._build_verification_url(user, token)
        expiration = email_verification_token_generator.get_expiration_time(token)

        # Prepare context
        context = {
            'user': user,
            'username': getattr(user, 'username', user.email),
            'first_name': getattr(user, 'first_name', ''),
            'verification_url': verification_url,
            'expiration_hours': 24,
            'expiration_time': expiration,
            'site_name': self.config.site_name,
            'support_email': self.config.support_email,
            'current_year': __import__('datetime').datetime.now().year,
        }

        # Send email
        return self._send_html_email(
            subject=f"Verify your email - {self.config.site_name}",
            template_name='emails/verification.html',
            context=context,
            recipient_email=user.email,
            fail_silently=fail_silently
        )

    def send_password_reset_email(
        self,
        user,
        fail_silently: bool = False
    ) -> bool:
        """
        Send password reset email to user.

        Args:
            user: User instance
            fail_silently: If True, suppress exceptions

        Returns:
            True if email sent successfully

        Raises:
            RateLimitExceeded: If user has exceeded rate limit
        """
        # Atomically acquire a rate-limit slot before doing any work.
        if not self._acquire_rate_limit(
            user.id, 'password_reset', self.RATE_LIMIT_PASSWORD_RESET
        ):
            raise RateLimitExceeded(
                "Too many password reset emails sent. Please try again later."
            )

        # Generate token and URL
        token = password_reset_token_generator.make_token(user)
        reset_url = self._build_password_reset_url(user, token)
        expiration = password_reset_token_generator.get_expiration_time(token)

        # Prepare context
        context = {
            'user': user,
            'username': getattr(user, 'username', user.email),
            'first_name': getattr(user, 'first_name', ''),
            'reset_url': reset_url,
            'expiration_hours': 1,
            'expiration_time': expiration,
            'site_name': self.config.site_name,
            'support_email': self.config.support_email,
            'current_year': __import__('datetime').datetime.now().year,
        }

        # Send email
        return self._send_html_email(
            subject=f"Reset your password - {self.config.site_name}",
            template_name='emails/password_reset.html',
            context=context,
            recipient_email=user.email,
            fail_silently=fail_silently
        )

    def send_welcome_email(
        self,
        user,
        fail_silently: bool = False
    ) -> bool:
        """
        Send welcome email to newly registered user.

        Args:
            user: User instance
            fail_silently: If True, suppress exceptions

        Returns:
            True if email sent successfully
        """
        # Prepare context
        context = {
            'user': user,
            'username': getattr(user, 'username', user.email),
            'first_name': getattr(user, 'first_name', ''),
            'site_name': self.config.site_name,
            'login_url': f"{self._get_base_url()}/login/",
            'support_email': self.config.support_email,
            'current_year': __import__('datetime').datetime.now().year,
        }

        return self._send_html_email(
            subject=f"Welcome to {self.config.site_name}!",
            template_name='emails/welcome.html',
            context=context,
            recipient_email=user.email,
            fail_silently=fail_silently
        )


# Convenience functions for quick email sending
_email_service = EmailService()


def send_verification_email(user, fail_silently: bool = False) -> bool:
    """Send verification email to user."""
    return _email_service.send_verification_email(user, fail_silently)


def send_password_reset_email(user, fail_silently: bool = False) -> bool:
    """Send password reset email to user."""
    return _email_service.send_password_reset_email(user, fail_silently)


def send_welcome_email(user, fail_silently: bool = False) -> bool:
    """Send welcome email to user."""
    return _email_service.send_welcome_email(user, fail_silently)
