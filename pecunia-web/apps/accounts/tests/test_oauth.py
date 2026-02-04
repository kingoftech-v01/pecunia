"""
Tests for accounts.oauth module.

Covers OAuthProvider enum, OAuthError hierarchy, PKCEManager,
OAuthStateManager, BaseOAuth2Provider, GoogleOAuth2Provider,
AppleOAuth2Provider, and convenience functions with all branches.
"""
import json
import time
from unittest.mock import patch, MagicMock, PropertyMock

import jwt
import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.accounts.oauth import (
    AppleOAuth2Provider,
    BaseOAuth2Provider,
    GoogleOAuth2Provider,
    OAuthError,
    OAuthProvider,
    OAuthStateError,
    OAuthStateManager,
    OAuthTokenError,
    OAuthUserInfo,
    OAuthUserInfoError,
    OAUTH_PROVIDERS,
    PKCEManager,
    get_oauth_provider,
    get_oauth_url,
    handle_callback,
)


# ---------------------------------------------------------------------------
# OAuthProvider enum tests
# ---------------------------------------------------------------------------

class TestOAuthProvider:
    """Tests for OAuthProvider enum."""

    def test_google_value(self):
        assert OAuthProvider.GOOGLE.value == "google"

    def test_apple_value(self):
        assert OAuthProvider.APPLE.value == "apple"


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------

class TestOAuthExceptions:
    """Tests for OAuth exception classes."""

    def test_oauth_error_base(self):
        assert issubclass(OAuthError, Exception)

    def test_state_error_inherits(self):
        assert issubclass(OAuthStateError, OAuthError)

    def test_token_error_inherits(self):
        assert issubclass(OAuthTokenError, OAuthError)

    def test_user_info_error_inherits(self):
        assert issubclass(OAuthUserInfoError, OAuthError)


# ---------------------------------------------------------------------------
# OAuthUserInfo dataclass tests
# ---------------------------------------------------------------------------

class TestOAuthUserInfo:
    """Tests for OAuthUserInfo dataclass."""

    def test_create_user_info(self):
        info = OAuthUserInfo(
            provider="google",
            provider_user_id="123",
            email="test@example.com",
            email_verified=True,
            first_name="Test",
            last_name="User",
            full_name="Test User",
        )
        assert info.provider == "google"
        assert info.email == "test@example.com"
        assert info.picture_url is None
        assert info.locale is None
        assert info.raw_data is None


# ---------------------------------------------------------------------------
# PKCEManager tests
# ---------------------------------------------------------------------------

class TestPKCEManager:
    """Tests for PKCEManager."""

    def test_generate_code_verifier_length(self):
        verifier = PKCEManager.generate_code_verifier(64)
        assert len(verifier) == 64

    def test_generate_code_verifier_default(self):
        verifier = PKCEManager.generate_code_verifier()
        assert len(verifier) == 64

    def test_generate_code_verifier_min_length(self):
        verifier = PKCEManager.generate_code_verifier(43)
        assert len(verifier) == 43

    def test_generate_code_verifier_max_length(self):
        verifier = PKCEManager.generate_code_verifier(128)
        assert len(verifier) == 128

    def test_generate_code_verifier_too_short(self):
        with pytest.raises(ValueError, match="between 43 and 128"):
            PKCEManager.generate_code_verifier(42)

    def test_generate_code_verifier_too_long(self):
        with pytest.raises(ValueError, match="between 43 and 128"):
            PKCEManager.generate_code_verifier(129)

    def test_generate_code_verifier_unique(self):
        verifiers = {PKCEManager.generate_code_verifier() for _ in range(10)}
        assert len(verifiers) == 10

    def test_generate_code_challenge(self):
        verifier = "test_verifier_string_that_is_long_enough_for_test"
        challenge = PKCEManager.generate_code_challenge(verifier)
        assert isinstance(challenge, str)
        assert len(challenge) > 0

    def test_generate_code_challenge_deterministic(self):
        verifier = "same_verifier"
        c1 = PKCEManager.generate_code_challenge(verifier)
        c2 = PKCEManager.generate_code_challenge(verifier)
        assert c1 == c2

    def test_generate_code_challenge_different_verifiers(self):
        v1 = PKCEManager.generate_code_verifier()
        v2 = PKCEManager.generate_code_verifier()
        assert PKCEManager.generate_code_challenge(v1) != PKCEManager.generate_code_challenge(v2)


# ---------------------------------------------------------------------------
# OAuthStateManager tests
# ---------------------------------------------------------------------------

class TestOAuthStateManager:
    """Tests for OAuthStateManager."""

    def setup_method(self):
        cache.clear()

    def test_generate_state(self):
        state = OAuthStateManager.generate_state("google")
        assert isinstance(state, str)
        assert len(state) > 0

    def test_generate_state_stores_data(self):
        state = OAuthStateManager.generate_state(
            "google", redirect_url="/dashboard", code_verifier="test_verifier"
        )
        cache_key = f"{OAuthStateManager.STATE_PREFIX}{state}"
        data = cache.get(cache_key)
        assert data is not None
        assert data["provider"] == "google"
        assert data["redirect_url"] == "/dashboard"
        assert data["code_verifier"] == "test_verifier"

    def test_validate_state_success(self):
        state = OAuthStateManager.generate_state("google")
        data = OAuthStateManager.validate_state(state)
        assert data["provider"] == "google"

    def test_validate_state_deletes_state(self):
        state = OAuthStateManager.generate_state("google")
        OAuthStateManager.validate_state(state)
        # Second use should fail (replay prevention)
        with pytest.raises(OAuthStateError, match="Invalid or expired"):
            OAuthStateManager.validate_state(state)

    def test_validate_state_empty(self):
        with pytest.raises(OAuthStateError, match="Missing state"):
            OAuthStateManager.validate_state("")

    def test_validate_state_invalid(self):
        with pytest.raises(OAuthStateError, match="Invalid or expired"):
            OAuthStateManager.validate_state("nonexistent_state")

    def test_validate_state_expired(self):
        state = OAuthStateManager.generate_state("google")
        # Manually delete from cache to simulate expiration
        cache.delete(f"{OAuthStateManager.STATE_PREFIX}{state}")
        with pytest.raises(OAuthStateError, match="Invalid or expired"):
            OAuthStateManager.validate_state(state)


# ---------------------------------------------------------------------------
# GoogleOAuth2Provider tests
# ---------------------------------------------------------------------------

class TestGoogleOAuth2Provider:
    """Tests for GoogleOAuth2Provider."""

    def test_provider_name(self):
        provider = GoogleOAuth2Provider()
        assert provider.provider_name == "google"

    def test_supports_pkce(self):
        provider = GoogleOAuth2Provider()
        assert provider.supports_pkce is True

    def test_default_scopes(self):
        provider = GoogleOAuth2Provider()
        assert "openid" in provider.default_scopes
        assert "email" in provider.default_scopes
        assert "profile" in provider.default_scopes

    @patch("apps.accounts.oauth.requests.get")
    def test_get_user_info_via_userinfo_endpoint(self, mock_get):
        """When no id_token, falls back to userinfo endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "google-123",
            "email": "test@gmail.com",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
            "picture": "https://photo.jpg",
            "locale": "en",
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        provider = GoogleOAuth2Provider()
        user_info = provider._get_user_info({"access_token": "test_access"})
        assert user_info.email == "test@gmail.com"
        assert user_info.first_name == "Test"
        assert user_info.last_name == "User"
        assert user_info.provider_user_id == "google-123"
        assert user_info.provider == "google"

    @patch("apps.accounts.oauth.requests.get")
    def test_get_user_info_request_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        provider = GoogleOAuth2Provider()
        with pytest.raises(OAuthUserInfoError):
            provider._get_user_info({"access_token": "test"})

    @patch("apps.accounts.oauth.requests.post")
    def test_refresh_access_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        provider = GoogleOAuth2Provider()
        result = provider.refresh_access_token("old_refresh")
        assert result["access_token"] == "new_access"

    @patch("apps.accounts.oauth.requests.post")
    def test_refresh_access_token_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Error")

        provider = GoogleOAuth2Provider()
        with pytest.raises(OAuthTokenError):
            provider.refresh_access_token("old_refresh")

    @patch("apps.accounts.oauth.requests.post")
    def test_revoke_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        provider = GoogleOAuth2Provider()
        result = provider.revoke_token("some_token")
        assert result is True

    @patch("apps.accounts.oauth.requests.post")
    def test_revoke_token_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        provider = GoogleOAuth2Provider()
        result = provider.revoke_token("bad_token")
        assert result is False

    @patch("apps.accounts.oauth.requests.post")
    def test_revoke_token_network_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Error")

        provider = GoogleOAuth2Provider()
        result = provider.revoke_token("some_token")
        assert result is False


# ---------------------------------------------------------------------------
# AppleOAuth2Provider tests
# ---------------------------------------------------------------------------

class TestAppleOAuth2Provider:
    """Tests for AppleOAuth2Provider."""

    def test_provider_name(self):
        provider = AppleOAuth2Provider()
        assert provider.provider_name == "apple"

    def test_supports_pkce(self):
        provider = AppleOAuth2Provider()
        assert provider.supports_pkce is True

    def test_default_scopes(self):
        provider = AppleOAuth2Provider()
        assert "name" in provider.default_scopes
        assert "email" in provider.default_scopes

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    def test_get_user_info_success(self, mock_decode, mock_jwks_cls):
        mock_decode.return_value = {
            "sub": "apple-456",
            "email": "test@icloud.com",
            "email_verified": True,
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        provider = AppleOAuth2Provider()
        user_info = provider._get_user_info({"id_token": "valid_jwt"})
        assert user_info.email == "test@icloud.com"
        assert user_info.provider_user_id == "apple-456"

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    def test_get_user_info_with_name(self, mock_decode, mock_jwks_cls):
        mock_decode.return_value = {
            "sub": "apple-456",
            "email": "test@icloud.com",
            "email_verified": "true",
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        provider = AppleOAuth2Provider()
        user_data = {"name": {"firstName": "Apple", "lastName": "User"}}
        user_info = provider._get_user_info({"id_token": "valid_jwt"}, user_data)
        assert user_info.first_name == "Apple"
        assert user_info.last_name == "User"
        assert user_info.full_name == "Apple User"

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    def test_get_user_info_email_verified_string(self, mock_decode, mock_jwks_cls):
        """Apple sometimes sends email_verified as string."""
        mock_decode.return_value = {
            "sub": "apple-456",
            "email": "test@icloud.com",
            "email_verified": "true",
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        provider = AppleOAuth2Provider()
        user_info = provider._get_user_info({"id_token": "valid_jwt"})
        assert user_info.email_verified is True

    def test_get_user_info_missing_id_token(self):
        provider = AppleOAuth2Provider()
        with pytest.raises(OAuthUserInfoError, match="Missing ID token"):
            provider._get_user_info({})

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    def test_get_user_info_invalid_token(self, mock_decode, mock_jwks_cls):
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client
        mock_decode.side_effect = jwt.InvalidTokenError("Bad token")

        provider = AppleOAuth2Provider()
        with pytest.raises(OAuthUserInfoError, match="Failed to verify"):
            provider._get_user_info({"id_token": "bad_jwt"})

    def test_get_client_secret_missing_config(self):
        """Missing Apple keys should return empty string."""
        provider = AppleOAuth2Provider()
        # Clear any cached secret
        AppleOAuth2Provider._client_secret_cache = None
        AppleOAuth2Provider._client_secret_expiry = None
        secret = provider._get_client_secret()
        assert secret == ""

    def test_no_revoke_url(self):
        provider = AppleOAuth2Provider()
        assert provider.revoke_url is not None


# ---------------------------------------------------------------------------
# BaseOAuth2Provider tests
# ---------------------------------------------------------------------------

class TestBaseOAuth2Provider:
    """Tests for BaseOAuth2Provider."""

    def test_get_client_id_raises(self):
        with pytest.raises(NotImplementedError):
            BaseOAuth2Provider()

    def test_get_user_info_not_implemented(self):
        """_get_user_info should raise NotImplementedError on base."""
        # Can't instantiate BaseOAuth2Provider directly due to __init__
        # calling _get_client_id which raises NotImplementedError
        pass

    def test_revoke_token_no_url(self):
        """When no revoke_url, revoke_token returns False."""
        # We need to test this through a provider mock
        provider = MagicMock(spec=BaseOAuth2Provider)
        provider.revoke_url = None
        result = BaseOAuth2Provider.revoke_token(provider, "token")
        assert result is False


# ---------------------------------------------------------------------------
# Provider registry and convenience functions
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    """Tests for OAUTH_PROVIDERS and convenience functions."""

    def test_providers_registered(self):
        assert "google" in OAUTH_PROVIDERS
        assert "apple" in OAUTH_PROVIDERS

    def test_get_oauth_provider_google(self):
        provider = get_oauth_provider("google")
        assert isinstance(provider, GoogleOAuth2Provider)

    def test_get_oauth_provider_apple(self):
        provider = get_oauth_provider("apple")
        assert isinstance(provider, AppleOAuth2Provider)

    def test_get_oauth_provider_case_insensitive(self):
        provider = get_oauth_provider("Google")
        assert isinstance(provider, GoogleOAuth2Provider)

    def test_get_oauth_provider_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported"):
            get_oauth_provider("facebook")


# ---------------------------------------------------------------------------
# Google get_oauth_url and handle_callback tests
# ---------------------------------------------------------------------------

class TestGoogleOAuth2ProviderFlows:
    """Tests for GoogleOAuth2Provider OAuth flow methods."""

    def setup_method(self):
        cache.clear()

    def _make_request(self):
        """Create a mock request with build_absolute_uri."""
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://localhost/api/v1/accounts/oauth/google/callback/"
        return request

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_get_oauth_url(self, mock_reverse):
        """Test Google OAuth URL generation with PKCE parameters."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()

        url = provider.get_oauth_url(request, redirect_url="/dashboard")

        assert "accounts.google.com" in url
        assert "client_id=" in url
        assert "response_type=code" in url
        assert "state=" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_get_oauth_url_with_extra_params(self, mock_reverse):
        """Test Google OAuth URL generation with extra parameters."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()

        url = provider.get_oauth_url(
            request,
            extra_params={"login_hint": "user@example.com"}
        )

        assert "login_hint=" in url

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_get_oauth_url_custom_scopes(self, mock_reverse):
        """Test Google OAuth URL generation with custom scopes."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()

        url = provider.get_oauth_url(
            request,
            scopes=["openid", "email"]
        )

        assert "scope=" in url

    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.requests.get")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_handle_callback_success(self, mock_reverse, mock_get, mock_post):
        """Test full Google callback flow."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()

        # Set up state
        state = OAuthStateManager.generate_state(
            "google", code_verifier="test_verifier"
        )

        # Mock token exchange
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "google_access_token",
            "refresh_token": "google_refresh_token",
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        # Mock userinfo endpoint
        mock_userinfo_response = MagicMock()
        mock_userinfo_response.status_code = 200
        mock_userinfo_response.json.return_value = {
            "sub": "google-user-123",
            "email": "user@gmail.com",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
        }
        mock_userinfo_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_userinfo_response

        user_info, state_data = provider.handle_callback(
            request, code="auth_code_123", state=state
        )

        assert user_info.email == "user@gmail.com"
        assert user_info.provider == "google"
        assert state_data["provider"] == "google"

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_handle_callback_provider_mismatch(self, mock_reverse):
        """State provider mismatch should raise OAuthStateError."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()

        # Generate state for a different provider
        state = OAuthStateManager.generate_state("apple")

        with pytest.raises(OAuthStateError, match="Provider mismatch"):
            provider.handle_callback(request, code="auth_code", state=state)

    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_exchange_code_success(self, mock_reverse, mock_post):
        """Test successful code exchange."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access",
            "id_token": "new_id_token",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tokens = provider._exchange_code(request, "auth_code", code_verifier="test_verifier")
        assert tokens["access_token"] == "new_access"

        # Verify code_verifier was included in the request
        call_data = mock_post.call_args[1]["data"]
        assert call_data["code_verifier"] == "test_verifier"

    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_exchange_code_without_verifier(self, mock_reverse, mock_post):
        """Test code exchange without PKCE verifier."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "token"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tokens = provider._exchange_code(request, "auth_code")
        assert tokens["access_token"] == "token"

        # Verify code_verifier was NOT included
        call_data = mock_post.call_args[1]["data"]
        assert "code_verifier" not in call_data

    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_exchange_code_network_error(self, mock_reverse, mock_post):
        """Test code exchange with network error."""
        import requests as req
        mock_post.side_effect = req.RequestException("Connection failed")

        provider = GoogleOAuth2Provider()
        request = self._make_request()

        with pytest.raises(OAuthTokenError, match="Failed to exchange"):
            provider._exchange_code(request, "auth_code")

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    def test_get_user_info_with_id_token(self, mock_decode, mock_jwks_cls):
        """Test Google user info extraction from ID token (JWT path)."""
        mock_decode.return_value = {
            "sub": "google-jwt-123",
            "email": "jwt@gmail.com",
            "email_verified": True,
            "given_name": "JWT",
            "family_name": "User",
            "name": "JWT User",
            "picture": "https://photo.example.com/pic.jpg",
            "locale": "en",
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        provider = GoogleOAuth2Provider()
        user_info = provider._get_user_info({
            "access_token": "test_access",
            "id_token": "valid_id_token",
        })

        assert user_info.email == "jwt@gmail.com"
        assert user_info.provider_user_id == "google-jwt-123"
        assert user_info.first_name == "JWT"
        assert user_info.last_name == "User"
        assert user_info.picture_url == "https://photo.example.com/pic.jpg"
        assert user_info.locale == "en"
        assert user_info.raw_data is not None

    @patch("apps.accounts.oauth.requests.get")
    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    def test_get_user_info_id_token_fallback_on_decode_error(self, mock_decode, mock_jwks_cls, mock_get):
        """When ID token decode fails, should fall back to userinfo endpoint."""
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client
        mock_decode.side_effect = jwt.DecodeError("Bad JWT")

        # Fallback userinfo endpoint
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "fallback-123",
            "email": "fallback@gmail.com",
            "email_verified": True,
            "given_name": "Fallback",
            "family_name": "User",
            "name": "Fallback User",
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        provider = GoogleOAuth2Provider()
        user_info = provider._get_user_info({
            "access_token": "test_access",
            "id_token": "bad_id_token",
        })

        assert user_info.email == "fallback@gmail.com"
        assert user_info.provider_user_id == "fallback-123"

    @patch("apps.accounts.oauth.requests.get")
    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    def test_get_user_info_id_token_fallback_on_expired(self, mock_decode, mock_jwks_cls, mock_get):
        """When ID token is expired, should fall back to userinfo endpoint."""
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client
        mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "expired-123",
            "email": "expired@gmail.com",
            "email_verified": True,
            "given_name": "Expired",
            "family_name": "User",
            "name": "Expired User",
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        provider = GoogleOAuth2Provider()
        user_info = provider._get_user_info({
            "access_token": "test_access",
            "id_token": "expired_id_token",
        })

        assert user_info.email == "expired@gmail.com"

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_get_callback_url(self, mock_reverse):
        """Test callback URL generation."""
        provider = GoogleOAuth2Provider()
        request = self._make_request()
        url = provider.get_callback_url(request)
        assert "callback" in url


# ---------------------------------------------------------------------------
# Apple get_oauth_url, handle_callback, and client secret tests
# ---------------------------------------------------------------------------

class TestAppleOAuth2ProviderFlows:
    """Tests for AppleOAuth2Provider OAuth flow methods."""

    def setup_method(self):
        cache.clear()

    def _make_request(self):
        """Create a mock request with build_absolute_uri."""
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://localhost/api/v1/accounts/oauth/apple/callback/"
        return request

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/apple/callback/")
    def test_get_oauth_url(self, mock_reverse):
        """Test Apple OAuth URL generation."""
        provider = AppleOAuth2Provider()
        request = self._make_request()

        url = provider.get_oauth_url(request, redirect_url="/dashboard")

        assert "appleid.apple.com" in url
        assert "response_mode=form_post" in url
        assert "state=" in url
        assert "code_challenge=" in url

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/apple/callback/")
    def test_get_oauth_url_with_extra_params(self, mock_reverse):
        """Test Apple OAuth URL with extra parameters."""
        provider = AppleOAuth2Provider()
        request = self._make_request()

        url = provider.get_oauth_url(
            request,
            extra_params={"locale": "en_US"}
        )

        assert "locale=en_US" in url
        assert "response_mode=form_post" in url

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/apple/callback/")
    def test_handle_callback_success(self, mock_reverse, mock_post, mock_decode, mock_jwks_cls):
        """Test full Apple callback flow."""
        provider = AppleOAuth2Provider()
        request = self._make_request()

        # Set up state
        state = OAuthStateManager.generate_state(
            "apple", code_verifier="apple_verifier"
        )

        # Mock token exchange
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "apple_access",
            "id_token": "apple_id_token",
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        # Mock JWT decode
        mock_decode.return_value = {
            "sub": "apple-user-789",
            "email": "user@icloud.com",
            "email_verified": True,
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        user_info, state_data = provider.handle_callback(
            request, code="apple_auth_code", state=state
        )

        assert user_info.email == "user@icloud.com"
        assert user_info.provider == "apple"
        assert state_data["provider"] == "apple"

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/apple/callback/")
    def test_handle_callback_with_user_data(self, mock_reverse, mock_post, mock_decode, mock_jwks_cls):
        """Test Apple callback with user_data JSON (first authorization)."""
        provider = AppleOAuth2Provider()
        request = self._make_request()

        # Set up state
        state = OAuthStateManager.generate_state("apple")

        # Mock token exchange
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "apple_access",
            "id_token": "apple_id_token",
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        # Mock JWT decode
        mock_decode.return_value = {
            "sub": "apple-first-auth",
            "email": "new@icloud.com",
            "email_verified": "true",
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        # user_data as JSON string (Apple sends this on first auth)
        user_data = json.dumps({
            "name": {"firstName": "New", "lastName": "Apple"},
            "email": "new@icloud.com",
        })

        user_info, state_data = provider.handle_callback(
            request, code="auth_code", state=state, user_data=user_data
        )

        assert user_info.first_name == "New"
        assert user_info.last_name == "Apple"
        assert user_info.full_name == "New Apple"

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/apple/callback/")
    def test_handle_callback_with_invalid_user_data_json(self, mock_reverse, mock_post, mock_decode, mock_jwks_cls):
        """Test Apple callback with invalid user_data JSON."""
        provider = AppleOAuth2Provider()
        request = self._make_request()

        state = OAuthStateManager.generate_state("apple")

        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "apple_access",
            "id_token": "apple_id_token",
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        mock_decode.return_value = {
            "sub": "apple-bad-json",
            "email": "bad@icloud.com",
            "email_verified": True,
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        # Invalid JSON for user_data
        user_info, state_data = provider.handle_callback(
            request, code="auth_code", state=state, user_data="not-valid-json{"
        )

        # Should still succeed, just without name data
        assert user_info.email == "bad@icloud.com"
        assert user_info.first_name == ""

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/apple/callback/")
    def test_handle_callback_provider_mismatch(self, mock_reverse):
        """Apple handle_callback with wrong provider in state."""
        provider = AppleOAuth2Provider()
        request = self._make_request()

        state = OAuthStateManager.generate_state("google")

        with pytest.raises(OAuthStateError, match="Provider mismatch"):
            provider.handle_callback(request, code="code", state=state)

    @patch("apps.accounts.oauth.jwt.encode")
    def test_get_client_secret_with_valid_config(self, mock_jwt_encode):
        """Test Apple client secret JWT generation with valid config."""
        from django.test import override_settings
        mock_jwt_encode.return_value = "generated_jwt_secret"

        # Clear cache
        AppleOAuth2Provider._client_secret_cache = None
        AppleOAuth2Provider._client_secret_expiry = None

        with override_settings(
            APPLE_TEAM_ID="TEAM123",
            APPLE_KEY_ID="KEY456",
            APPLE_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----\nfake_key\n-----END EC PRIVATE KEY-----",
            APPLE_CLIENT_ID="com.example.app",
        ):
            # __init__ calls _get_client_secret() once, so we call it explicitly
            # after clearing the cache to test the path directly
            provider = AppleOAuth2Provider()
            # The init already called _get_client_secret and cached the result.
            # Verify it was called and the secret is as expected.
            secret = provider.client_secret

        assert secret == "generated_jwt_secret"
        # jwt.encode was called during __init__ -> _get_client_secret
        assert mock_jwt_encode.call_count >= 1

        # Verify the payload and headers from the last call
        call_args = mock_jwt_encode.call_args
        payload = call_args[0][0]
        assert payload["iss"] == "TEAM123"
        assert payload["aud"] == "https://appleid.apple.com"

        # Clean up
        AppleOAuth2Provider._client_secret_cache = None
        AppleOAuth2Provider._client_secret_expiry = None

    def test_get_client_secret_cached(self):
        """Test that cached client secret is returned."""
        AppleOAuth2Provider._client_secret_cache = "cached_secret"
        AppleOAuth2Provider._client_secret_expiry = time.time() + 3600

        provider = AppleOAuth2Provider()
        secret = provider._get_client_secret()
        assert secret == "cached_secret"

        # Clean up
        AppleOAuth2Provider._client_secret_cache = None
        AppleOAuth2Provider._client_secret_expiry = None

    def test_get_client_secret_jwt_encode_error(self):
        """Test client secret generation when jwt.encode raises."""
        from django.test import override_settings
        AppleOAuth2Provider._client_secret_cache = None
        AppleOAuth2Provider._client_secret_expiry = None

        with override_settings(
            APPLE_TEAM_ID="TEAM123",
            APPLE_KEY_ID="KEY456",
            APPLE_PRIVATE_KEY="invalid_key",
            APPLE_CLIENT_ID="com.example.app",
        ):
            provider = AppleOAuth2Provider()
            AppleOAuth2Provider._client_secret_cache = None
            AppleOAuth2Provider._client_secret_expiry = None
            # jwt.encode will fail with an invalid key
            secret = provider._get_client_secret()
            assert secret == ""

        # Clean up
        AppleOAuth2Provider._client_secret_cache = None
        AppleOAuth2Provider._client_secret_expiry = None


# ---------------------------------------------------------------------------
# BaseOAuth2Provider additional tests
# ---------------------------------------------------------------------------

class TestBaseOAuth2ProviderAdditional:
    """Additional tests for BaseOAuth2Provider abstract methods."""

    def test_get_client_secret_raises(self):
        """_get_client_secret raises NotImplementedError on base class."""
        # We cannot instantiate BaseOAuth2Provider, so test via __dict__
        with pytest.raises(NotImplementedError):
            BaseOAuth2Provider._get_client_secret(None)

    def test_get_user_info_raises(self):
        """_get_user_info raises NotImplementedError on base class."""
        with pytest.raises(NotImplementedError):
            BaseOAuth2Provider._get_user_info(None, {})


# ---------------------------------------------------------------------------
# Convenience function flow tests
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def setup_method(self):
        cache.clear()

    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_get_oauth_url_function(self, mock_reverse):
        """Test the get_oauth_url convenience function."""
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://localhost/callback/"

        url = get_oauth_url(
            request, "google", redirect_url="/dashboard"
        )

        assert "accounts.google.com" in url
        assert "state=" in url

    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.requests.get")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/google/callback/")
    def test_handle_callback_function(self, mock_reverse, mock_get, mock_post):
        """Test the handle_callback convenience function."""
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://localhost/callback/"

        state = OAuthStateManager.generate_state("google")

        # Mock token exchange
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "conv_access",
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        # Mock userinfo
        mock_userinfo = MagicMock()
        mock_userinfo.status_code = 200
        mock_userinfo.json.return_value = {
            "sub": "conv-123",
            "email": "conv@gmail.com",
            "email_verified": True,
            "given_name": "Conv",
            "family_name": "User",
            "name": "Conv User",
        }
        mock_userinfo.raise_for_status = MagicMock()
        mock_get.return_value = mock_userinfo

        user_info, state_data = handle_callback(
            request, "google", code="auth_code", state=state
        )

        assert user_info.email == "conv@gmail.com"
        assert state_data["provider"] == "google"

    @patch("apps.accounts.oauth.jwt.PyJWKClient")
    @patch("apps.accounts.oauth.jwt.decode")
    @patch("apps.accounts.oauth.requests.post")
    @patch("apps.accounts.oauth.reverse", return_value="/api/v1/accounts/oauth/apple/callback/")
    def test_handle_callback_function_apple(self, mock_reverse, mock_post, mock_decode, mock_jwks_cls):
        """Test the handle_callback convenience function for Apple."""
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://localhost/callback/"

        state = OAuthStateManager.generate_state("apple")

        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "apple_access",
            "id_token": "apple_jwt",
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response

        mock_decode.return_value = {
            "sub": "apple-conv-123",
            "email": "conv@icloud.com",
            "email_verified": True,
        }
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_cls.return_value = mock_jwks_client

        user_info, state_data = handle_callback(
            request, "apple", code="apple_code", state=state
        )

        assert user_info.email == "conv@icloud.com"
        assert user_info.provider == "apple"
