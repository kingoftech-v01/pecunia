"""Tests for src/api/client.py — Base HTTP client with retry and interceptors."""

import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from api.client import (
    APIClient, APIResponse, APIError, AuthenticationError, NetworkError,
    ValidationError, APITimeoutError, HTTPMethod, RequestContext,
    get_api_client, get_api_client_sync, close_api_client, with_retry,
)


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.api.base_url = "https://api.example.com"
    config.api.timeout = 30
    config.api.verify_ssl = True
    config.environment = "development"
    return config


@pytest.fixture
def client(mock_config):
    with patch("api.client.get_config", return_value=mock_config):
        c = APIClient(
            base_url="https://api.example.com",
            token_provider=lambda: "test_token",
        )
    return c


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_is_ok_200(self):
        resp = APIResponse(success=True, status_code=200)
        assert resp.is_ok is True

    def test_is_ok_201(self):
        resp = APIResponse(success=True, status_code=201)
        assert resp.is_ok is True

    def test_is_ok_false_400(self):
        resp = APIResponse(success=False, status_code=400)
        assert resp.is_ok is False

    def test_is_ok_false_500(self):
        resp = APIResponse(success=False, status_code=500)
        assert resp.is_ok is False

    def test_data_default_none(self):
        resp = APIResponse(success=True, status_code=200)
        assert resp.data is None


class TestRequestContext:
    """Tests for RequestContext dataclass."""

    def test_default_values(self):
        ctx = RequestContext(
            method=HTTPMethod.GET,
            url="https://api.test.com/foo",
            endpoint="/foo",
            headers={},
        )
        assert ctx.attempt == 1
        assert ctx.data is None
        assert ctx.params is None

    def test_method_enum(self):
        for method in HTTPMethod:
            ctx = RequestContext(
                method=method, url="", endpoint="", headers={}
            )
            assert ctx.method == method


class TestAPIError:
    """Tests for error classes."""

    def test_api_error_str_with_status(self):
        err = APIError("fail", status_code=500)
        assert "[500]" in str(err)

    def test_api_error_str_without_status(self):
        err = APIError("fail")
        assert str(err) == "fail"

    def test_authentication_error_inherits(self):
        err = AuthenticationError("auth fail", status_code=401)
        assert isinstance(err, APIError)
        assert err.status_code == 401

    def test_network_error_inherits(self):
        err = NetworkError("net fail")
        assert isinstance(err, APIError)

    def test_validation_error_inherits(self):
        err = ValidationError("bad input", status_code=422)
        assert isinstance(err, APIError)

    def test_timeout_error_inherits(self):
        err = APITimeoutError("timed out")
        assert isinstance(err, APIError)


class TestAPIClientInit:
    """Tests for APIClient initialization."""

    def test_base_url_set(self, client):
        assert client.base_url == "https://api.example.com"

    def test_base_url_strips_trailing_slash(self, mock_config):
        with patch("api.client.get_config", return_value=mock_config):
            c = APIClient(base_url="https://api.example.com/")
        assert not c.base_url.endswith("/")

    def test_token_provider_set(self, client):
        assert client._token_provider is not None
        assert client._token_provider() == "test_token"


class TestBuildURL:
    """Tests for URL building."""

    def test_simple_endpoint(self, client):
        url = client._build_url("/users")
        assert url == "https://api.example.com/users"

    def test_endpoint_without_leading_slash(self, client):
        url = client._build_url("users")
        assert url == "https://api.example.com/users"


class TestGetHeaders:
    """Tests for header building."""

    def test_includes_auth_header(self, client):
        headers = client._get_headers(include_auth=True)
        assert "Authorization" in headers or "authorization" in headers

    def test_auth_header_bearer_format(self, client):
        headers = client._get_headers(include_auth=True)
        auth = headers.get("Authorization") or headers.get("authorization")
        assert auth == "Bearer test_token"

    def test_no_auth_when_disabled(self, client):
        headers = client._get_headers(include_auth=False)
        assert "Authorization" not in headers

    def test_content_type_json(self, client):
        headers = client._get_headers()
        ct = headers.get("Content-Type") or headers.get("content-type")
        assert "json" in ct


class TestMaskSensitiveData:
    """Tests for data masking."""

    def test_masks_password(self, client):
        data = {"email": "test@test.com", "password": "secret"}
        masked = client._mask_sensitive_data(data)
        assert masked["email"] == "test@test.com"
        assert masked["password"] == "***MASKED***"

    def test_masks_token(self, client):
        data = {"token": "abc123"}
        masked = client._mask_sensitive_data(data)
        assert masked["token"] == "***MASKED***"

    def test_masks_nested(self, client):
        data = {"user": {"password": "secret", "name": "test"}}
        masked = client._mask_sensitive_data(data)
        assert masked["user"]["password"] == "***MASKED***"
        assert masked["user"]["name"] == "test"


class TestExtractErrorMessage:
    """Tests for error message extraction."""

    def test_extracts_detail_string(self, client):
        data = {"detail": "Not found"}
        assert client._extract_error_message(data) == "Not found"

    def test_extracts_detail_list(self, client):
        data = {"detail": [{"loc": ["body", "email"], "msg": "invalid"}]}
        result = client._extract_error_message(data)
        assert "email" in result
        assert "invalid" in result

    def test_extracts_message(self, client):
        data = {"message": "Bad request"}
        assert client._extract_error_message(data) == "Bad request"

    def test_extracts_error(self, client):
        data = {"error": "Server down"}
        assert client._extract_error_message(data) == "Server down"

    def test_returns_none_for_non_dict(self, client):
        assert client._extract_error_message("string") is None

    def test_returns_none_for_empty_dict(self, client):
        assert client._extract_error_message({}) is None


class TestRetryLogic:
    """Tests for retry calculation and decisions."""

    def test_calculate_retry_delay_exponential(self, client):
        d0 = client._calculate_retry_delay(0)
        d1 = client._calculate_retry_delay(1)
        assert d1 > d0  # Should increase exponentially

    def test_retry_delay_capped(self, client):
        delay = client._calculate_retry_delay(100)
        assert delay <= client._max_retry_delay

    def test_should_retry_network_error(self, client):
        err = NetworkError("net")
        assert client._should_retry(err, 0) is True

    def test_should_retry_timeout_error(self, client):
        err = APITimeoutError("timeout")
        assert client._should_retry(err, 0) is True

    def test_should_not_retry_auth_error(self, client):
        err = AuthenticationError("auth", status_code=401)
        assert client._should_retry(err, 0) is False

    def test_should_retry_500_error(self, client):
        err = APIError("server error", status_code=500)
        assert client._should_retry(err, 0) is True

    def test_should_not_retry_400_error(self, client):
        err = APIError("bad request", status_code=400)
        assert client._should_retry(err, 0) is False

    def test_should_not_retry_max_attempts(self, client):
        err = NetworkError("net")
        assert client._should_retry(err, client._max_retries) is False


class TestTokenRefresh:
    """Tests for token refresh logic."""

    async def test_handle_token_refresh_no_callback(self, client):
        client._token_refresh_callback = None
        result = await client._handle_token_refresh()
        assert result is False

    async def test_handle_token_refresh_success(self, client):
        client._token_refresh_callback = AsyncMock(return_value=True)
        result = await client._handle_token_refresh()
        assert result is True

    async def test_handle_token_refresh_failure(self, client):
        client._token_refresh_callback = AsyncMock(return_value=False)
        result = await client._handle_token_refresh()
        assert result is False

    async def test_handle_token_refresh_exception(self, client):
        client._token_refresh_callback = AsyncMock(side_effect=Exception("fail"))
        result = await client._handle_token_refresh()
        assert result is False


class TestInterceptors:
    """Tests for request/response interceptors."""

    def test_add_request_interceptor(self, client):
        async def my_interceptor(ctx):
            return ctx
        client.add_request_interceptor(my_interceptor)
        assert my_interceptor in client._request_interceptors

    def test_remove_request_interceptor(self, client):
        async def my_interceptor(ctx):
            return ctx
        client.add_request_interceptor(my_interceptor)
        client.remove_request_interceptor(my_interceptor)
        assert my_interceptor not in client._request_interceptors

    def test_add_response_interceptor(self, client):
        async def my_interceptor(ctx, resp):
            return resp
        client.add_response_interceptor(my_interceptor)
        assert my_interceptor in client._response_interceptors

    def test_remove_response_interceptor(self, client):
        async def my_interceptor(ctx, resp):
            return resp
        client.add_response_interceptor(my_interceptor)
        client.remove_response_interceptor(my_interceptor)
        assert my_interceptor not in client._response_interceptors


class TestSetters:
    """Tests for setter methods."""

    def test_set_token_provider(self, client):
        new_provider = lambda: "new_token"
        client.set_token_provider(new_provider)
        assert client._token_provider() == "new_token"

    def test_set_token_refresh_callback(self, client):
        callback = AsyncMock()
        client.set_token_refresh_callback(callback)
        assert client._token_refresh_callback is callback


class TestContextManager:
    """Tests for async context manager."""

    async def test_enter_returns_self(self, client):
        result = await client.__aenter__()
        assert result is client

    async def test_exit_closes_session(self, client):
        client._session = MagicMock()
        client._session.closed = False
        client._session.close = AsyncMock()
        await client.__aexit__(None, None, None)
        client._session.close.assert_called_once()


class TestSingletonAccess:
    """Tests for module-level singleton access."""

    async def test_get_api_client_creates_instance(self, mock_config):
        import api.client as mod
        mod._default_client = None
        with patch("api.client.get_config", return_value=mock_config):
            c = await get_api_client()
            assert c is not None
        mod._default_client = None

    def test_get_api_client_sync_returns_none_initially(self):
        import api.client as mod
        mod._default_client = None
        assert get_api_client_sync() is None

    async def test_close_api_client(self, mock_config):
        import api.client as mod
        mod._default_client = None
        with patch("api.client.get_config", return_value=mock_config):
            await get_api_client()
            await close_api_client()
            assert mod._default_client is None


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""

    async def test_success_no_retry(self):
        call_count = 0

        @with_retry(max_retries=3, retry_on=(NetworkError,))
        async def good_func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await good_func()
        assert result == "ok"
        assert call_count == 1

    async def test_retries_on_network_error(self):
        call_count = 0

        @with_retry(max_retries=3, retry_on=(NetworkError,))
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("fail")
            return "ok"

        with patch("api.client.asyncio.sleep", new_callable=AsyncMock):
            result = await flaky_func()
        assert result == "ok"
        assert call_count == 3

    async def test_raises_after_max_retries(self):
        @with_retry(max_retries=2, retry_on=(NetworkError,))
        async def always_fail():
            raise NetworkError("fail")

        with patch("api.client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(NetworkError):
                await always_fail()
