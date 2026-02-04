"""
Tests for accounts.emails module.

Covers EmailService, EmailConfig, RateLimitExceeded, and convenience
functions with rate limiting, template rendering, and error handling.
"""
from unittest.mock import patch, MagicMock

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.accounts.emails import (
    EmailConfig,
    EmailService,
    RateLimitExceeded,
    send_verification_email,
    send_password_reset_email,
    send_welcome_email,
)
from apps.accounts.models import User


# ---------------------------------------------------------------------------
# EmailConfig tests
# ---------------------------------------------------------------------------

class TestEmailConfig:
    """Tests for EmailConfig dataclass."""

    def test_default_from_email(self):
        config = EmailConfig()
        expected = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pecunia.com')
        assert config.from_email == expected

    def test_default_support_email(self):
        config = EmailConfig()
        expected = getattr(settings, 'SUPPORT_EMAIL', 'support@pecunia.com')
        assert config.support_email == expected

    def test_default_reply_to(self):
        config = EmailConfig()
        assert config.reply_to == [config.support_email]

    def test_custom_from_email(self):
        config = EmailConfig(from_email="custom@example.com")
        assert config.from_email == "custom@example.com"

    def test_custom_reply_to(self):
        config = EmailConfig(reply_to=["reply@example.com"])
        assert config.reply_to == ["reply@example.com"]

    def test_site_name_default(self):
        config = EmailConfig()
        assert config.site_name == "Pecunia"

    def test_custom_site_name(self):
        config = EmailConfig(site_name="TestSite")
        assert config.site_name == "TestSite"


# ---------------------------------------------------------------------------
# RateLimitExceeded tests
# ---------------------------------------------------------------------------

class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_is_exception(self):
        assert issubclass(RateLimitExceeded, Exception)

    def test_message(self):
        exc = RateLimitExceeded("Too many emails")
        assert str(exc) == "Too many emails"


# ---------------------------------------------------------------------------
# EmailService tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmailService:
    """Tests for EmailService."""

    def setup_method(self):
        self.service = EmailService()
        cache.clear()

    def test_init_default_config(self):
        svc = EmailService()
        assert isinstance(svc.config, EmailConfig)

    def test_init_custom_config(self):
        config = EmailConfig(site_name="Custom")
        svc = EmailService(config=config)
        assert svc.config.site_name == "Custom"

    def test_get_rate_limit_key(self):
        key = self.service._get_rate_limit_key(123, "verification")
        assert key == "email_rate_limit:verification:123"

    def test_acquire_rate_limit_first_request(self, user):
        result = self.service._acquire_rate_limit(user.id, "test", 5)
        assert result is True

    def test_acquire_rate_limit_within_limit(self, user):
        for _ in range(3):
            result = self.service._acquire_rate_limit(user.id, "test", 5)
        assert result is True

    def test_acquire_rate_limit_exceeded(self, user):
        for _ in range(5):
            self.service._acquire_rate_limit(user.id, "test", 5)
        result = self.service._acquire_rate_limit(user.id, "test", 5)
        assert result is False

    def test_acquire_rate_limit_rollback_on_exceed(self, user):
        """Counter should be rolled back when limit is exceeded."""
        for _ in range(5):
            self.service._acquire_rate_limit(user.id, "test", 5)
        # This should fail but roll back
        self.service._acquire_rate_limit(user.id, "test", 5)
        # The counter should still be at 5, not 6
        key = self.service._get_rate_limit_key(user.id, "test")
        counter = cache.get(key)
        assert counter == 5

    def test_get_base_url(self):
        url = self.service._get_base_url()
        assert isinstance(url, str)

    @patch("apps.accounts.emails.render_to_string")
    @patch("apps.accounts.emails.EmailMultiAlternatives")
    def test_send_html_email_success(self, mock_email_cls, mock_render, user):
        mock_render.return_value = "<html><body>Test</body></html>"
        mock_email_instance = MagicMock()
        mock_email_cls.return_value = mock_email_instance

        result = self.service._send_html_email(
            subject="Test",
            template_name="test.html",
            context={"user": user},
            recipient_email=user.email,
        )
        assert result is True
        mock_email_instance.send.assert_called_once()

    @patch("apps.accounts.emails.render_to_string")
    def test_send_html_email_fail_silently(self, mock_render, user):
        mock_render.side_effect = Exception("Template error")
        result = self.service._send_html_email(
            subject="Test",
            template_name="nonexistent.html",
            context={},
            recipient_email=user.email,
            fail_silently=True,
        )
        assert result is False

    @patch("apps.accounts.emails.render_to_string")
    def test_send_html_email_raises_on_error(self, mock_render, user):
        mock_render.side_effect = Exception("Template error")
        with pytest.raises(Exception, match="Template error"):
            self.service._send_html_email(
                subject="Test",
                template_name="nonexistent.html",
                context={},
                recipient_email=user.email,
                fail_silently=False,
            )

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_verification_url", return_value="http://test/verify")
    def test_send_verification_email(self, mock_url, mock_send, user):
        result = self.service.send_verification_email(user)
        assert result is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "Verify your email" in call_kwargs["subject"]
        assert call_kwargs["recipient_email"] == user.email

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_verification_url", return_value="http://test/verify")
    def test_send_verification_email_rate_limited(self, mock_url, mock_send, user):
        """After RATE_LIMIT_VERIFICATION emails, should raise."""
        for _ in range(self.service.RATE_LIMIT_VERIFICATION):
            self.service.send_verification_email(user)
        with pytest.raises(RateLimitExceeded):
            self.service.send_verification_email(user)

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_password_reset_url", return_value="http://test/reset")
    def test_send_password_reset_email(self, mock_url, mock_send, user):
        result = self.service.send_password_reset_email(user)
        assert result is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "Reset your password" in call_kwargs["subject"]

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_password_reset_url", return_value="http://test/reset")
    def test_send_password_reset_email_rate_limited(self, mock_url, mock_send, user):
        for _ in range(self.service.RATE_LIMIT_PASSWORD_RESET):
            self.service.send_password_reset_email(user)
        with pytest.raises(RateLimitExceeded):
            self.service.send_password_reset_email(user)

    @patch.object(EmailService, "_send_html_email", return_value=True)
    def test_send_welcome_email(self, mock_send, user):
        result = self.service.send_welcome_email(user)
        assert result is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "Welcome" in call_kwargs["subject"]

    @patch.object(EmailService, "_send_html_email", return_value=True)
    def test_send_welcome_email_fail_silently(self, mock_send, user):
        result = self.service.send_welcome_email(user, fail_silently=True)
        assert result is True

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_verification_url", return_value="http://test/verify")
    def test_send_verification_email_context(self, mock_url, mock_send, user):
        self.service.send_verification_email(user)
        call_kwargs = mock_send.call_args[1]
        context = call_kwargs.get("context", {})
        assert "user" in context
        assert "verification_url" in context
        assert "site_name" in context

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_password_reset_url", return_value="http://test/reset")
    def test_send_password_reset_email_context(self, mock_url, mock_send, user):
        self.service.send_password_reset_email(user)
        call_kwargs = mock_send.call_args[1]
        context = call_kwargs.get("context", {})
        assert "user" in context
        assert "reset_url" in context
        assert "site_name" in context


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def setup_method(self):
        cache.clear()

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_verification_url", return_value="http://test/verify")
    def test_send_verification_email(self, mock_url, mock_send, user):
        result = send_verification_email(user)
        assert result is True

    @patch.object(EmailService, "_send_html_email", return_value=True)
    @patch.object(EmailService, "_build_password_reset_url", return_value="http://test/reset")
    def test_send_password_reset_email(self, mock_url, mock_send, user):
        result = send_password_reset_email(user)
        assert result is True

    @patch.object(EmailService, "_send_html_email", return_value=True)
    def test_send_welcome_email(self, mock_send, user):
        result = send_welcome_email(user)
        assert result is True


# ---------------------------------------------------------------------------
# URL builder tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestURLBuilders:
    """Tests for _build_verification_url and _build_password_reset_url."""

    def setup_method(self):
        self.service = EmailService()

    @patch("apps.accounts.emails.reverse")
    def test_build_verification_url(self, mock_reverse, user):
        """Test verification URL is built correctly with uidb64 and token."""
        mock_reverse.return_value = "/verify/uid123/token456/"
        url = self.service._build_verification_url(user, "test-token-123")
        assert url.endswith("/verify/uid123/token456/")
        assert url.startswith("http")
        # Verify reverse was called with correct kwargs
        call_kwargs = mock_reverse.call_args[1]
        assert "uidb64" in call_kwargs["kwargs"]
        assert call_kwargs["kwargs"]["token"] == "test-token-123"

    @patch("apps.accounts.emails.reverse")
    def test_build_password_reset_url(self, mock_reverse, user):
        """Test password reset URL is built correctly with uidb64 and token."""
        mock_reverse.return_value = "/reset/uid789/tokenABC/"
        url = self.service._build_password_reset_url(user, "reset-token-789")
        assert url.endswith("/reset/uid789/tokenABC/")
        assert url.startswith("http")
        call_kwargs = mock_reverse.call_args[1]
        assert "uidb64" in call_kwargs["kwargs"]
        assert call_kwargs["kwargs"]["token"] == "reset-token-789"


# ---------------------------------------------------------------------------
# Rate limit race condition tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRateLimitRaceCondition:
    """Tests for the race condition branch in _acquire_rate_limit."""

    def setup_method(self):
        self.service = EmailService()
        cache.clear()

    def test_acquire_rate_limit_add_fails_race_condition(self, user):
        """When cache.add fails (another thread created the key), should retry incr."""
        key = self.service._get_rate_limit_key(user.id, "race_test")

        with patch.object(cache, "incr") as mock_incr, \
             patch.object(cache, "add") as mock_add:
            # First incr raises ValueError (key doesn't exist)
            # Then add returns False (another thread created it)
            # Then second incr succeeds with value 2
            mock_incr.side_effect = [ValueError("Key not found"), 2]
            mock_add.return_value = False

            result = self.service._acquire_rate_limit(user.id, "race_test", 5)

            assert result is True
            assert mock_incr.call_count == 2
            mock_add.assert_called_once()

    def test_acquire_rate_limit_decr_value_error(self, user):
        """When over limit, decr might raise ValueError if key was deleted."""
        key = self.service._get_rate_limit_key(user.id, "decr_test")

        with patch.object(cache, "incr") as mock_incr, \
             patch.object(cache, "decr") as mock_decr:
            # incr returns value over the limit
            mock_incr.return_value = 6
            # decr raises ValueError (key was deleted between operations)
            mock_decr.side_effect = ValueError("Key not found")

            result = self.service._acquire_rate_limit(user.id, "decr_test", 5)

            assert result is False
            mock_decr.assert_called_once()
