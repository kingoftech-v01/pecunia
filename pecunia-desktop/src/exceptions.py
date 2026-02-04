"""
Custom exceptions for Pecunia Desktop.

Provides a hierarchy of application-specific exceptions for better error
handling and reporting throughout the application.
"""

import sys
import logging
import traceback
from typing import Optional, Any, Dict, Callable
from functools import wraps
from datetime import datetime

from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


# =============================================================================
# Base Exception Classes
# =============================================================================

class PecuniaError(Exception):
    """
    Base exception for all Pecunia errors.

    Attributes:
        message: Human-readable error message.
        error_code: Optional error code for programmatic handling.
        details: Additional error details for debugging.
        timestamp: When the error occurred.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        """Return formatted error string."""
        parts = [self.message]
        if self.error_code:
            parts.insert(0, f"[{self.error_code}]")
        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }

    def log(self, level: int = logging.ERROR) -> None:
        """Log this exception with the specified level."""
        logger.log(level, str(self), extra={"error_details": self.to_dict()})


# =============================================================================
# API and Network Errors
# =============================================================================

class APIError(PecuniaError):
    """
    Exception raised for API-related errors.

    Attributes:
        status_code: HTTP status code from the API response.
        response_body: Raw response body from the API.
        endpoint: The API endpoint that was called.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint
        self.details.update({
            "status_code": status_code,
            "endpoint": endpoint,
        })

    @classmethod
    def from_response(cls, response: Any, endpoint: str = "") -> "APIError":
        """Create APIError from an HTTP response object."""
        try:
            status_code = getattr(response, "status_code", getattr(response, "status", None))
            body = getattr(response, "text", str(response))
            message = f"API request failed with status {status_code}"
            return cls(
                message=message,
                status_code=status_code,
                response_body=body,
                endpoint=endpoint,
            )
        except Exception as e:
            return cls(
                message=f"API error: {str(e)}",
                endpoint=endpoint,
            )


class NetworkError(PecuniaError):
    """
    Exception raised for network connectivity issues.

    Attributes:
        url: The URL that failed to connect.
        timeout: Whether the error was a timeout.
    """

    def __init__(
        self,
        message: str = "Network connection failed",
        url: Optional[str] = None,
        timeout: bool = False,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.url = url
        self.timeout = timeout
        self.details.update({
            "url": url,
            "timeout": timeout,
        })


class AuthError(PecuniaError):
    """
    Exception raised for authentication/authorization errors.

    Attributes:
        token_expired: Whether the auth token has expired.
        requires_reauth: Whether user must re-authenticate.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        token_expired: bool = False,
        requires_reauth: bool = False,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.token_expired = token_expired
        self.requires_reauth = requires_reauth
        self.details.update({
            "token_expired": token_expired,
            "requires_reauth": requires_reauth,
        })


class TokenExpiredError(AuthError):
    """Exception raised when the authentication token has expired."""

    def __init__(self, message: str = "Authentication token has expired", **kwargs):
        super().__init__(message, token_expired=True, requires_reauth=True, **kwargs)


class InvalidCredentialsError(AuthError):
    """Exception raised when login credentials are invalid."""

    def __init__(self, message: str = "Invalid credentials provided", **kwargs):
        super().__init__(message, **kwargs)


# =============================================================================
# Database Errors
# =============================================================================

class DatabaseError(PecuniaError):
    """
    Exception raised for database-related errors.

    Attributes:
        query: The query that failed (sanitized).
        table: The table involved in the error.
    """

    def __init__(
        self,
        message: str = "Database operation failed",
        query: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.query = query
        self.table = table
        self.details.update({
            "table": table,
        })


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""

    def __init__(self, message: str = "Failed to connect to database", **kwargs):
        super().__init__(message, **kwargs)


class DatabaseIntegrityError(DatabaseError):
    """Exception raised for database integrity constraint violations."""

    def __init__(self, message: str = "Database integrity constraint violated", **kwargs):
        super().__init__(message, **kwargs)


class RecordNotFoundError(DatabaseError):
    """Exception raised when a database record is not found."""

    def __init__(
        self,
        message: str = "Record not found",
        record_id: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.record_id = record_id
        self.details["record_id"] = record_id


# =============================================================================
# Sync Errors
# =============================================================================

class SyncError(PecuniaError):
    """
    Exception raised for synchronization-related errors.

    Attributes:
        sync_type: Type of sync that failed (e.g., 'transactions', 'accounts').
        partial_success: Whether some items were synced successfully.
        failed_items: Number of items that failed to sync.
    """

    def __init__(
        self,
        message: str = "Synchronization failed",
        sync_type: Optional[str] = None,
        partial_success: bool = False,
        failed_items: int = 0,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.sync_type = sync_type
        self.partial_success = partial_success
        self.failed_items = failed_items
        self.details.update({
            "sync_type": sync_type,
            "partial_success": partial_success,
            "failed_items": failed_items,
        })


class ConflictError(SyncError):
    """Exception raised when there's a sync conflict."""

    def __init__(
        self,
        message: str = "Sync conflict detected",
        local_version: Optional[Any] = None,
        remote_version: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.local_version = local_version
        self.remote_version = remote_version


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(PecuniaError):
    """
    Exception raised for data validation errors.

    Attributes:
        field: The field that failed validation.
        value: The invalid value.
        constraints: Validation constraints that were violated.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.constraints = constraints or {}
        self.details.update({
            "field": field,
            "constraints": constraints,
        })


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(PecuniaError):
    """Exception raised for configuration-related errors."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.details["config_key"] = config_key


# =============================================================================
# Global Exception Handler
# =============================================================================

class GlobalExceptionHandler(QObject):
    """
    Global exception handler for the application.

    Captures unhandled exceptions and provides appropriate error reporting
    and recovery mechanisms.

    Signals:
        exception_caught: Emitted when an exception is caught.
        critical_error: Emitted for critical errors requiring immediate attention.
    """

    exception_caught = pyqtSignal(Exception, str)  # (exception, traceback_str)
    critical_error = pyqtSignal(str)  # error message

    _instance: Optional["GlobalExceptionHandler"] = None

    def __new__(cls):
        """Singleton pattern for global exception handler."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            super().__init__()
            self._initialized = True
            self._error_callbacks: list[Callable[[Exception], None]] = []
            self._show_dialogs = True
            self._log_errors = True

    def install(self) -> None:
        """Install the global exception handler."""
        sys.excepthook = self._handle_exception
        logger.info("Global exception handler installed")

    def uninstall(self) -> None:
        """Uninstall the global exception handler."""
        sys.excepthook = sys.__excepthook__
        logger.info("Global exception handler uninstalled")

    def set_show_dialogs(self, show: bool) -> None:
        """Enable or disable error dialogs."""
        self._show_dialogs = show

    def set_log_errors(self, log: bool) -> None:
        """Enable or disable error logging."""
        self._log_errors = log

    def add_callback(self, callback: Callable[[Exception], None]) -> None:
        """Add a callback to be called when an exception is caught."""
        self._error_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Exception], None]) -> None:
        """Remove an exception callback."""
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)

    def _handle_exception(
        self,
        exc_type: type,
        exc_value: Exception,
        exc_traceback
    ) -> None:
        """
        Handle an uncaught exception.

        Args:
            exc_type: Exception type.
            exc_value: Exception instance.
            exc_traceback: Traceback object.
        """
        # Format traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_str = "".join(tb_lines)

        # Log the error
        if self._log_errors:
            logger.critical(
                f"Unhandled exception: {exc_type.__name__}: {exc_value}",
                exc_info=(exc_type, exc_value, exc_traceback),
            )

        # Emit signal
        self.exception_caught.emit(exc_value, tb_str)

        # Call registered callbacks
        for callback in self._error_callbacks:
            try:
                callback(exc_value)
            except Exception as e:
                logger.error(f"Error in exception callback: {e}")

        # Show error dialog if enabled
        if self._show_dialogs:
            self._show_error_dialog(exc_type, exc_value, tb_str)

        # Check if this is a critical error
        if self._is_critical(exc_value):
            self.critical_error.emit(str(exc_value))

    def _is_critical(self, exc: Exception) -> bool:
        """Determine if an exception is critical."""
        critical_types = (
            MemoryError,
            SystemError,
            KeyboardInterrupt,
            DatabaseConnectionError,
        )
        return isinstance(exc, critical_types)

    def _show_error_dialog(
        self,
        exc_type: type,
        exc_value: Exception,
        tb_str: str
    ) -> None:
        """Show an error dialog to the user."""
        app = QApplication.instance()
        if app is None:
            return

        # Determine message based on exception type
        if isinstance(exc_value, PecuniaError):
            title = "Application Error"
            message = exc_value.message
        else:
            title = "Unexpected Error"
            message = str(exc_value) or "An unexpected error occurred."

        # Create detailed text with traceback
        detailed_text = f"Error Type: {exc_type.__name__}\n\n{tb_str}"

        # Show the dialog
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setDetailedText(detailed_text)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()

    def handle_exception(self, exc: Exception) -> None:
        """
        Manually handle an exception.

        Use this to handle caught exceptions consistently with
        the global handler.

        Args:
            exc: The exception to handle.
        """
        self._handle_exception(type(exc), exc, exc.__traceback__)


def get_exception_handler() -> GlobalExceptionHandler:
    """Get the global exception handler instance."""
    return GlobalExceptionHandler()


# =============================================================================
# Decorators
# =============================================================================

def handle_exceptions(
    *exception_types: type,
    default_return: Any = None,
    log_level: int = logging.ERROR,
    reraise: bool = False
):
    """
    Decorator to handle exceptions in a function.

    Args:
        exception_types: Exception types to catch (defaults to Exception).
        default_return: Value to return if an exception is caught.
        log_level: Logging level for caught exceptions.
        reraise: Whether to re-raise the exception after handling.

    Returns:
        Decorated function.
    """
    if not exception_types:
        exception_types = (Exception,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                logger.log(
                    log_level,
                    f"Exception in {func.__name__}: {e}",
                    exc_info=True,
                )
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def async_handle_exceptions(
    *exception_types: type,
    default_return: Any = None,
    log_level: int = logging.ERROR,
    reraise: bool = False
):
    """
    Async decorator to handle exceptions in an async function.

    Args:
        exception_types: Exception types to catch (defaults to Exception).
        default_return: Value to return if an exception is caught.
        log_level: Logging level for caught exceptions.
        reraise: Whether to re-raise the exception after handling.

    Returns:
        Decorated async function.
    """
    if not exception_types:
        exception_types = (Exception,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exception_types as e:
                logger.log(
                    log_level,
                    f"Exception in {func.__name__}: {e}",
                    exc_info=True,
                )
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


# =============================================================================
# Utility Functions
# =============================================================================

def raise_api_error_for_status(response: Any, endpoint: str = "") -> None:
    """
    Raise an appropriate API error based on HTTP status code.

    Args:
        response: HTTP response object with status_code attribute.
        endpoint: The API endpoint for context.

    Raises:
        APIError: For 4xx/5xx status codes.
        AuthError: For 401/403 status codes.
    """
    status_code = getattr(response, "status_code", getattr(response, "status", 200))

    if status_code < 400:
        return

    if status_code == 401:
        raise TokenExpiredError(endpoint=endpoint)
    elif status_code == 403:
        raise AuthError(
            message="Access forbidden",
            error_code="FORBIDDEN",
            details={"endpoint": endpoint},
        )
    elif status_code == 404:
        raise APIError(
            message="Resource not found",
            status_code=status_code,
            endpoint=endpoint,
            error_code="NOT_FOUND",
        )
    elif status_code == 422:
        raise ValidationError(
            message="Validation failed",
            details={"endpoint": endpoint, "status_code": status_code},
        )
    elif status_code >= 500:
        raise APIError(
            message="Server error",
            status_code=status_code,
            endpoint=endpoint,
            error_code="SERVER_ERROR",
        )
    else:
        raise APIError.from_response(response, endpoint)
