"""Tests for src/api/auth.py — Authentication service."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock

import pytest

from api.client import APIResponse, APIError, AuthenticationError
from api.auth import (
    User, AuthTokens, TokenStorage, AuthService, AuthResult,
    get_auth_service, reset_auth_service,
)


@pytest.fixture
def mock_api_client():
    client = MagicMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    client.patch = AsyncMock()
    return client


@pytest.fixture
def auth_service(mock_api_client):
    with patch("api.auth.TokenStorage") as mock_ts:
        mock_ts.return_value.load_tokens.return_value = None
        service = AuthService(api_client=mock_api_client)
    return service


class TestUser:
    """Tests for User dataclass."""

    def test_from_dict_full(self):
        data = {
            "id": "u1", "email": "test@test.com", "full_name": "Test User",
            "is_active": True, "is_verified": True,
            "created_at": "2024-01-01", "updated_at": "2024-06-01",
        }
        user = User.from_dict(data)
        assert user.id == "u1"
        assert user.email == "test@test.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_verified is True

    def test_from_dict_minimal(self):
        user = User.from_dict({})
        assert user.id == ""
        assert user.email == ""
        assert user.full_name is None
        assert user.is_active is True
        assert user.is_verified is False

    def test_from_dict_defaults(self):
        data = {"id": "x", "email": "a@b.com"}
        user = User.from_dict(data)
        assert user.is_active is True
        assert user.is_verified is False


class TestAuthTokens:
    """Tests for AuthTokens dataclass."""

    def test_from_dict_full(self):
        data = {
            "access_token": "at", "refresh_token": "rt",
            "token_type": "Bearer", "expires_in": 3600,
        }
        tokens = AuthTokens.from_dict(data)
        assert tokens.access_token == "at"
        assert tokens.refresh_token == "rt"
        assert tokens.expires_at is not None

    def test_from_dict_no_expiry(self):
        data = {"access_token": "at"}
        tokens = AuthTokens.from_dict(data)
        assert tokens.expires_at is None

    def test_is_expired_false_when_no_expiry(self):
        tokens = AuthTokens(access_token="at")
        assert tokens.is_expired() is False

    def test_is_expired_true_when_past(self):
        tokens = AuthTokens(
            access_token="at",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert tokens.is_expired() is True

    def test_is_expired_false_when_future(self):
        tokens = AuthTokens(
            access_token="at",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert tokens.is_expired() is False

    def test_is_expired_buffer(self):
        tokens = AuthTokens(
            access_token="at",
            expires_at=datetime.now() + timedelta(seconds=30),
        )
        # With default 60s buffer, should be considered expired
        assert tokens.is_expired(buffer_seconds=60) is True


class TestTokenStorage:
    """Tests for TokenStorage."""

    def test_init_checks_keyring(self):
        with patch("api.auth.keyring.get_keyring"):
            storage = TokenStorage()
            assert storage._use_keyring is True

    def test_init_fallback_when_keyring_unavailable(self):
        with patch("api.auth.keyring.get_keyring", side_effect=Exception("no")):
            storage = TokenStorage()
            assert storage._use_keyring is False

    def test_save_tokens_to_keyring(self):
        mock_keyring = MagicMock()
        tokens = AuthTokens(access_token="at", refresh_token="rt")
        with patch("api.auth.keyring", mock_keyring):
            storage = TokenStorage()
            storage._use_keyring = True
            storage._save_expiry_data = MagicMock()
            result = storage.save_tokens(tokens)
            assert result is True
            assert mock_keyring.set_password.call_count == 2

    def test_save_tokens_no_refresh_token(self):
        mock_keyring = MagicMock()
        tokens = AuthTokens(access_token="at")
        with patch("api.auth.keyring", mock_keyring):
            storage = TokenStorage()
            storage._use_keyring = True
            storage._save_expiry_data = MagicMock()
            result = storage.save_tokens(tokens)
            assert result is True
            assert mock_keyring.set_password.call_count == 1

    def test_load_tokens_from_keyring(self):
        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = lambda svc, key: {
            "pecunia_access_token": "at",
            "pecunia_refresh_token": "rt",
        }.get(key)
        with patch("api.auth.keyring", mock_keyring):
            storage = TokenStorage()
            storage._use_keyring = True
            storage._load_expiry_data = MagicMock(return_value=None)
            tokens = storage.load_tokens()
            assert tokens is not None
            assert tokens.access_token == "at"

    def test_load_tokens_returns_none_when_empty(self):
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = None
        with patch("api.auth.keyring", mock_keyring):
            storage = TokenStorage()
            storage._use_keyring = True
            tokens = storage.load_tokens()
            assert tokens is None

    def test_clear_tokens(self):
        mock_keyring = MagicMock()
        with patch("api.auth.keyring", mock_keyring), \
             patch("api.auth.get_config_dir") as mock_dir:
            mock_dir.return_value = MagicMock()
            mock_dir.return_value.__truediv__ = lambda s, x: MagicMock(exists=lambda: False)
            storage = TokenStorage()
            storage._use_keyring = True
            storage._fallback_file = MagicMock(exists=lambda: False)
            result = storage.clear_tokens()
            assert result is True

    def test_save_tokens_fallback(self, tmp_path):
        with patch("api.auth.keyring.get_keyring", side_effect=Exception("no")), \
             patch("api.auth.get_config_dir", return_value=tmp_path):
            storage = TokenStorage()
            tokens = AuthTokens(access_token="at", refresh_token="rt")
            result = storage.save_tokens(tokens)
            assert result is True

    def test_load_exception_returns_none(self):
        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = Exception("fail")
        with patch("api.auth.keyring", mock_keyring):
            storage = TokenStorage()
            storage._use_keyring = True
            assert storage.load_tokens() is None


class TestAuthService:
    """Tests for AuthService."""

    def test_not_authenticated_initially(self, auth_service):
        assert auth_service.is_authenticated is False

    def test_current_user_initially_none(self, auth_service):
        assert auth_service.current_user is None

    def test_get_access_token_none_initially(self, auth_service):
        assert auth_service.get_access_token() is None

    async def test_login_success(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"access_token": "at", "refresh_token": "rt", "expires_in": 3600},
        )
        mock_api_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "u1", "email": "test@test.com"},
        )
        auth_service._token_storage = MagicMock()

        user = await auth_service.login("test@test.com", "password")
        assert user.email == "test@test.com"
        assert auth_service._tokens is not None

    async def test_login_failure(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=False, status_code=401,
            data={"detail": "Invalid credentials"},
        )
        with pytest.raises(AuthenticationError):
            await auth_service.login("bad@test.com", "wrong")

    async def test_register_success_with_tokens(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"access_token": "at", "refresh_token": "rt", "expires_in": 3600},
        )
        mock_api_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "u1", "email": "new@test.com"},
        )
        auth_service._token_storage = MagicMock()

        user = await auth_service.register("new@test.com", "pass", "New User")
        assert user.email == "new@test.com"

    async def test_register_success_without_tokens(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"user": {"id": "u1", "email": "new@test.com"}},
        )
        user = await auth_service.register("new@test.com", "pass")
        assert user.email == "new@test.com"

    async def test_register_failure(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=False, status_code=400,
            data={"detail": "Email already exists"},
        )
        with pytest.raises(APIError):
            await auth_service.register("existing@test.com", "pass")

    async def test_logout(self, auth_service, mock_api_client):
        auth_service._tokens = AuthTokens(access_token="at")
        auth_service._token_storage = MagicMock()
        mock_api_client.post.return_value = APIResponse(success=True, status_code=200, data={})

        result = await auth_service.logout()
        assert result is True
        assert auth_service._tokens is None
        assert auth_service._user is None

    async def test_logout_handles_backend_failure(self, auth_service, mock_api_client):
        auth_service._tokens = AuthTokens(access_token="at")
        auth_service._token_storage = MagicMock()
        mock_api_client.post.side_effect = Exception("server down")

        result = await auth_service.logout()
        assert result is True  # Should still succeed locally

    async def test_refresh_token_success(self, auth_service, mock_api_client):
        auth_service._tokens = AuthTokens(access_token="old", refresh_token="rt")
        auth_service._token_storage = MagicMock()
        mock_api_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"access_token": "new", "refresh_token": "rt2"},
        )
        result = await auth_service.refresh_token()
        assert result is True
        assert auth_service._tokens.access_token == "new"

    async def test_refresh_token_no_refresh_token(self, auth_service):
        auth_service._tokens = AuthTokens(access_token="at")
        with pytest.raises(AuthenticationError):
            await auth_service.refresh_token()

    async def test_refresh_token_failure(self, auth_service, mock_api_client):
        auth_service._tokens = AuthTokens(access_token="at", refresh_token="rt")
        auth_service._token_storage = MagicMock()
        mock_api_client.post.return_value = APIResponse(
            success=False, status_code=401, data={},
        )
        with pytest.raises(AuthenticationError):
            await auth_service.refresh_token()

    async def test_ensure_authenticated_no_tokens(self, auth_service):
        with pytest.raises(AuthenticationError):
            await auth_service.ensure_authenticated()

    async def test_change_password_success(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=True, status_code=200, data={},
        )
        result = await auth_service.change_password("old", "new")
        assert result is True

    async def test_change_password_failure(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=False, status_code=400,
            data={"detail": "Wrong password"},
        )
        with pytest.raises(APIError):
            await auth_service.change_password("wrong", "new")

    async def test_request_password_reset(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=True, status_code=200, data={},
        )
        result = await auth_service.request_password_reset("test@test.com")
        assert result is True

    async def test_verify_email(self, auth_service, mock_api_client):
        mock_api_client.post.return_value = APIResponse(
            success=True, status_code=200, data={},
        )
        result = await auth_service.verify_email("token123")
        assert result is True

    async def test_update_user_profile(self, auth_service, mock_api_client):
        mock_api_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "u1", "email": "a@b.com", "full_name": "Updated"},
        )
        user = await auth_service.update_user_profile(full_name="Updated")
        assert user.full_name == "Updated"

    def test_add_remove_auth_state_callback(self, auth_service):
        cb = MagicMock()
        auth_service.add_auth_state_callback(cb)
        assert cb in auth_service._auth_state_callbacks
        auth_service.remove_auth_state_callback(cb)
        assert cb not in auth_service._auth_state_callbacks

    def test_notify_auth_state_change(self, auth_service):
        cb = MagicMock()
        auth_service.add_auth_state_callback(cb)
        auth_service._notify_auth_state_change(True)
        cb.assert_called_once_with(True)

    def test_extract_error_detail(self, auth_service):
        resp = APIResponse(success=False, status_code=400, data={"detail": "msg"})
        assert auth_service._extract_error(resp) == "msg"

    def test_extract_error_message(self, auth_service):
        resp = APIResponse(success=False, status_code=400, data={"message": "msg2"})
        assert auth_service._extract_error(resp) == "msg2"

    def test_extract_error_none(self, auth_service):
        resp = APIResponse(success=False, status_code=400, data="not a dict")
        assert auth_service._extract_error(resp) is None


class TestAuthResult:
    """Tests for AuthResult dataclass."""

    def test_success_result(self):
        user = User(id="u1", email="a@b.com")
        tokens = AuthTokens(access_token="at")
        result = AuthResult.success_result(user, tokens)
        assert result.success is True
        assert result.user.id == "u1"
        assert result.tokens.access_token == "at"

    def test_error_result(self):
        result = AuthResult.error_result("Something broke")
        assert result.success is False
        assert result.error == "Something broke"
        assert result.user is None


class TestSingleton:
    """Tests for singleton accessors."""

    def test_get_auth_service(self):
        import api.auth
        api.auth._auth_service = None
        with patch("api.auth.TokenStorage") as mock_ts:
            mock_ts.return_value.load_tokens.return_value = None
            svc = get_auth_service()
            assert isinstance(svc, AuthService)
        api.auth._auth_service = None

    def test_reset_auth_service(self):
        import api.auth
        api.auth._auth_service = MagicMock()
        reset_auth_service()
        assert api.auth._auth_service is None
