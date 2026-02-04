"""Tests for src/exceptions.py — Custom exceptions and error handling."""

import logging
from datetime import datetime
from unittest.mock import patch, MagicMock, call

import pytest

from exceptions import (
    PecuniaError, APIError, NetworkError, AuthError, TokenExpiredError,
    InvalidCredentialsError, DatabaseError, DatabaseConnectionError,
    DatabaseIntegrityError, RecordNotFoundError, SyncError, ConflictError,
    ValidationError, ConfigurationError, GlobalExceptionHandler,
    get_exception_handler, handle_exceptions, async_handle_exceptions,
    raise_api_error_for_status,
)


class TestPecuniaError:
    """Tests for the base PecuniaError."""

    def test_basic_creation(self):
        err = PecuniaError("Something failed")
        assert err.message == "Something failed"
        assert err.error_code == "PecuniaError"
        assert err.details == {}
        assert isinstance(err.timestamp, datetime)

    def test_with_error_code(self):
        err = PecuniaError("fail", error_code="CUSTOM_CODE")
        assert err.error_code == "CUSTOM_CODE"

    def test_with_details(self):
        details = {"key": "value"}
        err = PecuniaError("fail", details=details)
        assert err.details == details

    def test_with_cause(self):
        cause = ValueError("original")
        err = PecuniaError("wrapped", cause=cause)
        assert err.cause is cause

    def test_str_includes_code(self):
        err = PecuniaError("fail", error_code="ERR01")
        assert "[ERR01]" in str(err)
        assert "fail" in str(err)

    def test_to_dict(self):
        err = PecuniaError("test", error_code="EC", details={"x": 1})
        d = err.to_dict()
        assert d["error_type"] == "PecuniaError"
        assert d["message"] == "test"
        assert d["error_code"] == "EC"
        assert d["details"] == {"x": 1}
        assert d["timestamp"] is not None
        assert d["cause"] is None

    def test_to_dict_with_cause(self):
        cause = ValueError("root")
        err = PecuniaError("wrapped", cause=cause)
        d = err.to_dict()
        assert "root" in d["cause"]

    def test_log_method(self):
        err = PecuniaError("log me")
        with patch("exceptions.logger") as mock_logger:
            err.log(logging.WARNING)
            mock_logger.log.assert_called_once()


class TestAPIError:
    """Tests for APIError."""

    def test_creation_with_status_code(self):
        err = APIError("api fail", status_code=500)
        assert err.status_code == 500
        assert err.details["status_code"] == 500

    def test_from_response(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        err = APIError.from_response(mock_resp, "/test")
        assert err.status_code == 404
        assert err.endpoint == "/test"

    def test_from_response_handles_exception(self):
        err = APIError.from_response(None, "/test")
        assert isinstance(err, APIError)


class TestNetworkError:
    """Tests for NetworkError."""

    def test_default_message(self):
        err = NetworkError()
        assert "Network" in err.message or "connection" in err.message

    def test_with_url_and_timeout(self):
        err = NetworkError(url="https://api.test.com", timeout=True)
        assert err.url == "https://api.test.com"
        assert err.timeout is True
        assert err.details["url"] == "https://api.test.com"


class TestAuthError:
    """Tests for AuthError and subclasses."""

    def test_default_message(self):
        err = AuthError()
        assert "Authentication" in err.message or "auth" in err.message.lower()

    def test_token_expired_flags(self):
        err = TokenExpiredError()
        assert err.token_expired is True
        assert err.requires_reauth is True

    def test_invalid_credentials(self):
        err = InvalidCredentialsError()
        assert isinstance(err, AuthError)


class TestDatabaseErrors:
    """Tests for database-related errors."""

    def test_database_error_with_table(self):
        err = DatabaseError(table="users")
        assert err.table == "users"
        assert err.details["table"] == "users"

    def test_connection_error(self):
        err = DatabaseConnectionError()
        assert isinstance(err, DatabaseError)

    def test_integrity_error(self):
        err = DatabaseIntegrityError()
        assert isinstance(err, DatabaseError)

    def test_record_not_found(self):
        err = RecordNotFoundError(record_id="abc123")
        assert err.record_id == "abc123"
        assert err.details["record_id"] == "abc123"


class TestSyncErrors:
    """Tests for sync-related errors."""

    def test_sync_error_attributes(self):
        err = SyncError(sync_type="transactions", partial_success=True, failed_items=5)
        assert err.sync_type == "transactions"
        assert err.partial_success is True
        assert err.failed_items == 5

    def test_conflict_error(self):
        err = ConflictError(local_version=1, remote_version=2)
        assert err.local_version == 1
        assert err.remote_version == 2
        assert isinstance(err, SyncError)


class TestValidationError:
    """Tests for ValidationError."""

    def test_with_field_and_value(self):
        err = ValidationError(field="email", value="bad", constraints={"format": "email"})
        assert err.field == "email"
        assert err.value == "bad"
        assert err.constraints == {"format": "email"}


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_with_config_key(self):
        err = ConfigurationError(config_key="db.path")
        assert err.config_key == "db.path"
        assert err.details["config_key"] == "db.path"


class TestGlobalExceptionHandler:
    """Tests for GlobalExceptionHandler."""

    def test_singleton_pattern(self):
        GlobalExceptionHandler._instance = None
        h1 = GlobalExceptionHandler()
        h2 = GlobalExceptionHandler()
        assert h1 is h2
        GlobalExceptionHandler._instance = None

    def test_install_sets_excepthook(self):
        import sys
        GlobalExceptionHandler._instance = None
        handler = GlobalExceptionHandler()
        original = sys.excepthook
        handler.install()
        assert sys.excepthook == handler._handle_exception
        handler.uninstall()
        GlobalExceptionHandler._instance = None

    def test_set_show_dialogs(self):
        GlobalExceptionHandler._instance = None
        handler = GlobalExceptionHandler()
        handler.set_show_dialogs(False)
        assert handler._show_dialogs is False
        GlobalExceptionHandler._instance = None

    def test_add_remove_callback(self):
        GlobalExceptionHandler._instance = None
        handler = GlobalExceptionHandler()
        cb = MagicMock()
        handler.add_callback(cb)
        assert cb in handler._error_callbacks
        handler.remove_callback(cb)
        assert cb not in handler._error_callbacks
        GlobalExceptionHandler._instance = None

    def test_is_critical_memory_error(self):
        GlobalExceptionHandler._instance = None
        handler = GlobalExceptionHandler()
        assert handler._is_critical(MemoryError()) is True
        assert handler._is_critical(ValueError()) is False
        GlobalExceptionHandler._instance = None

    def test_is_critical_db_connection_error(self):
        GlobalExceptionHandler._instance = None
        handler = GlobalExceptionHandler()
        assert handler._is_critical(DatabaseConnectionError()) is True
        GlobalExceptionHandler._instance = None


class TestHandleExceptionsDecorator:
    """Tests for handle_exceptions decorator."""

    def test_catches_exception_returns_default(self):
        @handle_exceptions(ValueError, default_return=-1)
        def bad_func():
            raise ValueError("oops")
        assert bad_func() == -1

    def test_passes_through_on_success(self):
        @handle_exceptions(ValueError, default_return=-1)
        def good_func():
            return 42
        assert good_func() == 42

    def test_reraise_option(self):
        @handle_exceptions(ValueError, reraise=True)
        def bad_func():
            raise ValueError("re")
        with pytest.raises(ValueError):
            bad_func()

    def test_no_exception_types_catches_all(self):
        @handle_exceptions(default_return="caught")
        def bad():
            raise RuntimeError("x")
        assert bad() == "caught"


class TestAsyncHandleExceptionsDecorator:
    """Tests for async_handle_exceptions decorator."""

    async def test_catches_exception_returns_default(self):
        @async_handle_exceptions(ValueError, default_return=-1)
        async def bad_func():
            raise ValueError("oops")
        result = await bad_func()
        assert result == -1

    async def test_passes_through_on_success(self):
        @async_handle_exceptions(ValueError, default_return=-1)
        async def good_func():
            return 42
        result = await good_func()
        assert result == 42

    async def test_reraise_option(self):
        @async_handle_exceptions(ValueError, reraise=True)
        async def bad_func():
            raise ValueError("re")
        with pytest.raises(ValueError):
            await bad_func()


class TestRaiseAPIErrorForStatus:
    """Tests for raise_api_error_for_status."""

    def test_success_status_does_nothing(self):
        resp = MagicMock(status_code=200)
        raise_api_error_for_status(resp)  # should not raise

    def test_401_raises_token_expired(self):
        resp = MagicMock(status_code=401)
        with pytest.raises(TokenExpiredError):
            raise_api_error_for_status(resp, "/test")

    def test_403_raises_auth_error(self):
        resp = MagicMock(status_code=403)
        with pytest.raises(AuthError):
            raise_api_error_for_status(resp, "/test")

    def test_404_raises_api_error(self):
        resp = MagicMock(status_code=404)
        with pytest.raises(APIError):
            raise_api_error_for_status(resp, "/test")

    def test_422_raises_validation_error(self):
        resp = MagicMock(status_code=422)
        with pytest.raises(ValidationError):
            raise_api_error_for_status(resp, "/test")

    def test_500_raises_api_error(self):
        resp = MagicMock(status_code=500)
        with pytest.raises(APIError):
            raise_api_error_for_status(resp, "/test")

    def test_other_4xx_raises_api_error(self):
        resp = MagicMock(status_code=429)
        resp.status = 429
        resp.text = "Too many requests"
        with pytest.raises(APIError):
            raise_api_error_for_status(resp, "/test")
