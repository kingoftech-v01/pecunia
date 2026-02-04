"""
Tests for accounts.views module.

Covers RegisterAPIView, LoginAPIView, LogoutAPIView, UserViewSet,
and UserProfileViewSet with all branches and edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserProfile


# ---------------------------------------------------------------------------
# We define a minimal URL config to avoid importing the broken ROOT_URLCONF.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _use_accounts_urls(settings):
    """Override ROOT_URLCONF with a minimal config for view tests."""
    settings.ROOT_URLCONF = "apps.accounts.tests._test_urls"
    # The security settings reference a 'sessions' cache alias that does not
    # exist in development CACHES.  Fall back to database sessions so the
    # tests do not break.
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.db"


# URL constants relative to the minimal URL config above.
REGISTER_URL = "/api/v1/accounts/register/"
LOGIN_URL = "/api/v1/accounts/login/"
LOGOUT_URL = "/api/v1/accounts/logout/"
USER_ME_URL = "/api/v1/accounts/users/me/"
CHANGE_PASSWORD_URL = "/api/v1/accounts/users/me/change-password/"
PROFILE_LIST_URL = "/api/v1/accounts/profile/"


# ---------------------------------------------------------------------------
# RegisterAPIView tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRegisterAPIView:
    """Tests for user registration endpoint."""

    VALID_PAYLOAD = {
        "email": "register@example.com",
        "password": "Str0ngP@ssw0rd!",
        "password_confirm": "Str0ngP@ssw0rd!",
        "first_name": "Reg",
        "last_name": "User",
    }

    def test_register_success(self, api_client):
        response = api_client.post(REGISTER_URL, self.VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert response.data["user"]["email"] == "register@example.com"
        assert "detail" in response.data
        assert User.objects.filter(email="register@example.com").exists()

    def test_register_creates_profile(self, api_client):
        api_client.post(REGISTER_URL, self.VALID_PAYLOAD, format="json")
        user = User.objects.get(email="register@example.com")
        assert hasattr(user, "profile")
        assert user.profile is not None

    def test_register_no_tokens_returned(self, api_client):
        response = api_client.post(REGISTER_URL, self.VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" not in response.data

    def test_register_password_mismatch(self, api_client):
        data = {**self.VALID_PAYLOAD, "password_confirm": "Mismatch123!!"}
        response = api_client.post(REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, user):
        data = {**self.VALID_PAYLOAD, "email": user.email}
        response = api_client.post(REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        data = {**self.VALID_PAYLOAD, "password": "123", "password_confirm": "123"}
        response = api_client.post(REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_email(self, api_client):
        data = {**self.VALID_PAYLOAD}
        del data["email"]
        response = api_client.post(REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_allows_any(self, api_client):
        """Endpoint should be accessible without authentication."""
        response = api_client.post(REGISTER_URL, self.VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# LoginAPIView tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLoginAPIView:
    """Tests for user login endpoint."""

    def test_login_success(self, api_client, user, user_password):
        data = {"email": user.email, "password": user_password}
        with patch("apps.accounts.views.TOTPService") as MockTOTP:
            mock_svc = MockTOTP.return_value
            mock_svc.is_2fa_enabled.return_value = False
            response = api_client.post(LOGIN_URL, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        assert "user" in response.data
        assert response.data["user"]["email"] == user.email

    def test_login_invalid_credentials(self, api_client, user):
        data = {"email": user.email, "password": "WrongPass123!!"}
        response = api_client.post(LOGIN_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_nonexistent_user(self, api_client):
        data = {"email": "none@example.com", "password": "DoesNotMatter1!"}
        response = api_client.post(LOGIN_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_missing_fields(self, api_client):
        response = api_client.post(LOGIN_URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_2fa_required_no_code(self, api_client, user, user_password):
        """When 2FA is enabled and no code provided, return requires_2fa."""
        data = {"email": user.email, "password": user_password}
        with patch("apps.accounts.views.TOTPService") as MockTOTP:
            mock_svc = MockTOTP.return_value
            mock_svc.is_2fa_enabled.return_value = True
            response = api_client.post(LOGIN_URL, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["requires_2fa"] is True

    def test_login_2fa_invalid_code(self, api_client, user, user_password):
        """When 2FA code is provided but invalid, return 401."""
        data = {"email": user.email, "password": user_password, "totp_code": "000000"}
        with patch("apps.accounts.views.TOTPService") as MockTOTP:
            mock_svc = MockTOTP.return_value
            mock_svc.is_2fa_enabled.return_value = True
            mock_svc.verify_token.return_value = False
            response = api_client.post(LOGIN_URL, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid two-factor" in response.data["detail"]

    def test_login_2fa_valid_code(self, api_client, user, user_password):
        """When 2FA code is valid, login succeeds with tokens."""
        data = {"email": user.email, "password": user_password, "totp_code": "123456"}
        with patch("apps.accounts.views.TOTPService") as MockTOTP:
            mock_svc = MockTOTP.return_value
            mock_svc.is_2fa_enabled.return_value = True
            mock_svc.verify_token.return_value = True
            response = api_client.post(LOGIN_URL, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data

    def test_login_allows_any(self, api_client, user, user_password):
        """Endpoint should be accessible without authentication."""
        data = {"email": user.email, "password": user_password}
        with patch("apps.accounts.views.TOTPService") as MockTOTP:
            mock_svc = MockTOTP.return_value
            mock_svc.is_2fa_enabled.return_value = False
            response = api_client.post(LOGIN_URL, data, format="json")
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# LogoutAPIView tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogoutAPIView:
    """Tests for user logout endpoint."""

    def test_logout_success(self, auth_client, user):
        refresh = RefreshToken.for_user(user)
        response = auth_client.post(
            LOGOUT_URL, {"refresh": str(refresh)}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "Successfully logged out" in response.data["detail"]

    def test_logout_without_refresh_token(self, auth_client):
        response = auth_client.post(LOGOUT_URL, {}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_logout_invalid_token(self, auth_client):
        response = auth_client.post(
            LOGOUT_URL, {"refresh": "invalidtoken"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid token" in response.data["detail"]

    def test_logout_requires_authentication(self, api_client):
        response = api_client.post(LOGOUT_URL, {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_other_users_token(self, auth_client, user2):
        """Cannot blacklist another user's refresh token."""
        other_refresh = RefreshToken.for_user(user2)
        response = auth_client.post(
            LOGOUT_URL, {"refresh": str(other_refresh)}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "does not belong" in response.data["detail"]


# ---------------------------------------------------------------------------
# UserViewSet tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserViewSet:
    """Tests for user viewset (me endpoint)."""

    def test_get_me(self, auth_client, user):
        response = auth_client.get(USER_ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["first_name"] == "Test"
        assert response.data["last_name"] == "User"

    def test_get_me_unauthenticated(self, api_client):
        response = api_client.get(USER_ME_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_me(self, auth_client, user):
        response = auth_client.patch(
            USER_ME_URL,
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"
        assert response.data["last_name"] == "Name"
        user.refresh_from_db()
        assert user.first_name == "Updated"

    def test_patch_me_read_only_fields_ignored(self, auth_client, user):
        response = auth_client.patch(
            USER_ME_URL,
            {"email": "hacked@evil.com", "subscription_tier": "premium"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.email == "testuser@example.com"
        assert user.subscription_tier == "free"

    def test_user2_cannot_see_user1_data(self, auth_client2, user):
        """User2's auth client should return user2's data, not user1."""
        response = auth_client2.get(USER_ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "otheruser@example.com"


# ---------------------------------------------------------------------------
# Change password tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChangePassword:
    """Tests for the change-password endpoint."""

    def test_change_password_success(self, auth_client, user, user_password):
        data = {
            "current_password": user_password,
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        response = auth_client.post(CHANGE_PASSWORD_URL, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "Password changed successfully" in response.data["detail"]
        user.refresh_from_db()
        assert user.check_password("N3wStr0ngP@ss!")

    def test_change_password_wrong_current(self, auth_client, user):
        data = {
            "current_password": "WrongOldPass123!!",
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        response = auth_client.post(CHANGE_PASSWORD_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(self, auth_client, user, user_password):
        data = {
            "current_password": user_password,
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "Mismatch123!!",
        }
        response = auth_client.post(CHANGE_PASSWORD_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_weak_new(self, auth_client, user, user_password):
        data = {
            "current_password": user_password,
            "new_password": "123",
            "new_password_confirm": "123",
        }
        response = auth_client.post(CHANGE_PASSWORD_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthenticated(self, api_client):
        data = {
            "current_password": "whatever",
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        response = api_client.post(CHANGE_PASSWORD_URL, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password_returns_new_tokens(self, auth_client, user, user_password):
        data = {
            "current_password": user_password,
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        response = auth_client.post(CHANGE_PASSWORD_URL, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]


# ---------------------------------------------------------------------------
# UserProfileViewSet tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserProfileViewSet:
    """Tests for the profile endpoint."""

    def test_get_profile(self, auth_client, user):
        response = auth_client.get(PROFILE_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["theme"] == "system"
        assert response.data["language"] == "fr"

    def test_get_profile_unauthenticated(self, api_client):
        response = api_client.get(PROFILE_LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user2_gets_own_profile(self, auth_client2, user2):
        response = auth_client2.get(PROFILE_LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_patch_profile(self, auth_client, user):
        """Test updating user profile settings via PATCH."""
        # The profile endpoint uses the router, so the detail URL is /profile/{pk}/
        # But the list endpoint overrides to show current user's profile.
        # We need to test the update path which requires a detail URL.
        profile = user.profile
        detail_url = f"{PROFILE_LIST_URL}{profile.pk}/"
        response = auth_client.patch(
            detail_url,
            {"theme": "dark", "language": "en"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["theme"] == "dark"
        assert response.data["language"] == "en"
        profile.refresh_from_db()
        assert profile.theme == "dark"
        assert profile.language == "en"

    def test_put_profile(self, auth_client, user):
        """Test full update of user profile via PUT."""
        profile = user.profile
        detail_url = f"{PROFILE_LIST_URL}{profile.pk}/"
        response = auth_client.put(
            detail_url,
            {
                "email_notifications": False,
                "push_notifications": False,
                "weekly_summary": False,
                "budget_alerts": False,
                "theme": "light",
                "language": "de",
                "date_format": "YYYY-MM-DD",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        profile.refresh_from_db()
        assert profile.theme == "light"
        assert profile.language == "de"
        assert profile.email_notifications is False
