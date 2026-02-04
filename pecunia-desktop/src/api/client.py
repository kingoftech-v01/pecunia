"""
Base HTTP client for Pecunia Desktop API communication.

Provides async HTTP request handling with automatic retry logic,
request/response interceptors, automatic token refresh on 401,
error handling, connection pooling, and response parsing.

This module implements a singleton pattern for the API client,
ensuring a single shared instance across the application.
"""

import asyncio
import logging
import time
import random
from typing import Any, Optional, Dict, Callable, Awaitable, List
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

import aiohttp
from aiohttp import ClientTimeout, ClientConnectorError, TCPConnector

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from constants import (
    API_TIMEOUT_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY_SECONDS,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HEADER_ACCEPT,
    CONTENT_TYPE_JSON,
    Endpoints,
    ErrorMessages,
)

logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """HTTP request methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class APIResponse:
    """
    Represents an API response.

    Attributes:
        success: Whether the request was successful.
        status_code: HTTP status code.
        data: Response data (parsed JSON).
        error: Error message if request failed.
        headers: Response headers.
        elapsed_time: Request duration in seconds.
    """
    success: bool
    status_code: int
    data: Optional[Any] = None
    error: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    elapsed_time: float = 0.0

    @property
    def is_ok(self) -> bool:
        """Check if response indicates success (2xx status)."""
        return 200 <= self.status_code < 300


@dataclass
class RequestContext:
    """
    Context information for a request, used by interceptors.

    Attributes:
        method: HTTP method.
        url: Full request URL.
        endpoint: API endpoint path.
        headers: Request headers.
        data: Request body data.
        params: Query parameters.
        attempt: Current retry attempt number.
        start_time: Request start timestamp.
    """
    method: HTTPMethod
    url: str
    endpoint: str
    headers: Dict[str, str]
    data: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    attempt: int = 1
    start_time: float = field(default_factory=time.time)


# Type aliases for interceptors
RequestInterceptor = Callable[[RequestContext], Awaitable[RequestContext]]
ResponseInterceptor = Callable[[RequestContext, APIResponse], Awaitable[APIResponse]]
TokenRefreshCallback = Callable[[], Awaitable[bool]]


class APIError(Exception):
    """
    Exception raised for API errors.

    Attributes:
        message: Error message.
        status_code: HTTP status code.
        response: Full API response.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[APIResponse] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(APIError):
    """Raised when authentication fails or token is invalid."""
    pass


class NetworkError(APIError):
    """Raised when network connection fails."""
    pass


class ValidationError(APIError):
    """Raised when request validation fails."""
    pass


class TimeoutError(APIError):
    """Raised when request times out."""
    pass


class APIClient:
    """
    Async HTTP client for API communication with singleton support.

    Provides methods for making HTTP requests with:
    - Automatic retry with exponential backoff
    - Request/response interceptors
    - Automatic token refresh on 401 responses
    - Connection pooling
    - Comprehensive logging
    - Error handling and parsing

    Usage:
        # Get singleton instance
        client = APIClient.get_instance()

        # Or create a new instance
        client = APIClient(base_url="http://api.example.com")

        # Make requests
        response = await client.get("/users")
        response = await client.post("/users", data={"name": "John"})
    """

    _instance: Optional['APIClient'] = None
    _lock = asyncio.Lock()

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        token_provider: Optional[Callable[[], Optional[str]]] = None,
        max_connections: int = 100,
        max_connections_per_host: int = 10,
    ):
        """
        Initialize the API client.

        Args:
            base_url: Base URL for API requests.
            timeout: Request timeout in seconds.
            token_provider: Callable that returns the current access token.
            max_connections: Maximum number of connections in the pool.
            max_connections_per_host: Maximum connections per host.
        """
        config = get_config()
        self._base_url = (base_url or config.api.base_url).rstrip('/')
        self._timeout = timeout or config.api.timeout
        self._verify_ssl = config.api.verify_ssl
        self._token_provider = token_provider
        self._max_connections = max_connections
        self._max_connections_per_host = max_connections_per_host

        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

        # Interceptors
        self._request_interceptors: List[RequestInterceptor] = []
        self._response_interceptors: List[ResponseInterceptor] = []

        # Token refresh callback
        self._token_refresh_callback: Optional[TokenRefreshCallback] = None
        self._refresh_lock = asyncio.Lock()
        self._is_refreshing = False

        # Retry configuration
        self._max_retries = API_MAX_RETRIES
        self._base_retry_delay = API_RETRY_DELAY_SECONDS
        self._max_retry_delay = 30  # Maximum delay between retries in seconds

        logger.debug(f"APIClient initialized with base_url={self._base_url}")

    @classmethod
    async def get_instance(
        cls,
        base_url: Optional[str] = None,
        token_provider: Optional[Callable[[], Optional[str]]] = None,
        **kwargs
    ) -> 'APIClient':
        """
        Get or create the singleton APIClient instance.

        This method is thread-safe and will only create one instance.

        Args:
            base_url: Base URL for API requests (only used on first call).
            token_provider: Token provider callback (only used on first call).
            **kwargs: Additional arguments passed to __init__.

        Returns:
            The singleton APIClient instance.
        """
        if cls._instance is None:
            async with cls._lock:
                # Double-check pattern
                if cls._instance is None:
                    cls._instance = cls(
                        base_url=base_url,
                        token_provider=token_provider,
                        **kwargs
                    )
                    logger.info("APIClient singleton instance created")
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> Optional['APIClient']:
        """
        Get the singleton instance synchronously.

        Returns:
            The singleton instance if it exists, None otherwise.
        """
        return cls._instance

    @classmethod
    async def reset_instance(cls):
        """
        Reset the singleton instance.

        Closes the existing instance and clears it.
        Useful for testing or reconfiguration.
        """
        async with cls._lock:
            if cls._instance is not None:
                await cls._instance.close()
                cls._instance = None
                logger.info("APIClient singleton instance reset")

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._base_url

    def set_token_provider(self, provider: Callable[[], Optional[str]]):
        """
        Set the token provider callback.

        Args:
            provider: Callable that returns the current access token.
        """
        self._token_provider = provider

    def set_token_refresh_callback(self, callback: TokenRefreshCallback):
        """
        Set the callback for refreshing expired tokens.

        This callback will be invoked when a 401 response is received,
        allowing automatic token refresh and request retry.

        Args:
            callback: Async callback that refreshes the token and returns
                     True if successful, False otherwise.
        """
        self._token_refresh_callback = callback
        logger.debug("Token refresh callback configured")

    # -------------------------------------------------------------------------
    # Interceptor Management
    # -------------------------------------------------------------------------

    def add_request_interceptor(self, interceptor: RequestInterceptor):
        """
        Add a request interceptor.

        Request interceptors are called before each request is sent,
        allowing modification of the request context.

        Args:
            interceptor: Async function that receives and returns RequestContext.
        """
        self._request_interceptors.append(interceptor)
        logger.debug(f"Request interceptor added: {interceptor.__name__}")

    def remove_request_interceptor(self, interceptor: RequestInterceptor):
        """Remove a request interceptor."""
        if interceptor in self._request_interceptors:
            self._request_interceptors.remove(interceptor)
            logger.debug(f"Request interceptor removed: {interceptor.__name__}")

    def add_response_interceptor(self, interceptor: ResponseInterceptor):
        """
        Add a response interceptor.

        Response interceptors are called after each response is received,
        allowing modification or logging of the response.

        Args:
            interceptor: Async function that receives (RequestContext, APIResponse)
                        and returns APIResponse.
        """
        self._response_interceptors.append(interceptor)
        logger.debug(f"Response interceptor added: {interceptor.__name__}")

    def remove_response_interceptor(self, interceptor: ResponseInterceptor):
        """Remove a response interceptor."""
        if interceptor in self._response_interceptors:
            self._response_interceptors.remove(interceptor)
            logger.debug(f"Response interceptor removed: {interceptor.__name__}")

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create the aiohttp session with connection pooling.

        Uses a TCPConnector for connection pooling and reuse.
        """
        async with self._session_lock:
            if self._session is None or self._session.closed:
                timeout = ClientTimeout(total=self._timeout)
                connector = TCPConnector(
                    ssl=self._verify_ssl if self._verify_ssl else False,
                    limit=self._max_connections,
                    limit_per_host=self._max_connections_per_host,
                    ttl_dns_cache=300,  # Cache DNS for 5 minutes
                    enable_cleanup_closed=True,
                )
                self._session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                )
                logger.debug(
                    f"Created new aiohttp session with pool "
                    f"(max_connections={self._max_connections}, "
                    f"per_host={self._max_connections_per_host})"
                )
        return self._session

    async def close(self):
        """
        Close the HTTP session and release resources.

        Should be called when the client is no longer needed.
        """
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
                logger.debug("APIClient session closed")

    # -------------------------------------------------------------------------
    # Request Building
    # -------------------------------------------------------------------------

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        endpoint = endpoint.lstrip('/')
        return f"{self._base_url}/{endpoint}"

    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """
        Build request headers.

        Args:
            include_auth: Whether to include authorization header.

        Returns:
            Dictionary of headers.
        """
        headers = {
            HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
            HEADER_ACCEPT: CONTENT_TYPE_JSON,
        }

        if include_auth and self._token_provider:
            token = self._token_provider()
            if token:
                headers[HEADER_AUTHORIZATION] = f"Bearer {token}"

        return headers

    # -------------------------------------------------------------------------
    # Retry Logic with Exponential Backoff
    # -------------------------------------------------------------------------

    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry using exponential backoff with jitter.

        Uses the formula: min(max_delay, base_delay * 2^attempt + random_jitter)

        Args:
            attempt: Current attempt number (0-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        # Exponential backoff
        delay = self._base_retry_delay * (2 ** attempt)

        # Add jitter (up to 25% of the delay)
        jitter = random.uniform(0, delay * 0.25)
        delay += jitter

        # Cap at maximum delay
        delay = min(delay, self._max_retry_delay)

        return delay

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if a request should be retried.

        Args:
            error: The exception that occurred.
            attempt: Current attempt number.

        Returns:
            True if the request should be retried.
        """
        if attempt >= self._max_retries:
            return False

        # Retry on network errors
        if isinstance(error, NetworkError):
            return True

        # Retry on timeout errors
        if isinstance(error, TimeoutError):
            return True

        # Retry on server errors (5xx)
        if isinstance(error, APIError) and error.status_code:
            if 500 <= error.status_code < 600:
                return True

        return False

    # -------------------------------------------------------------------------
    # Token Refresh
    # -------------------------------------------------------------------------

    async def _handle_token_refresh(self) -> bool:
        """
        Handle token refresh when a 401 is received.

        Uses a lock to prevent multiple simultaneous refresh attempts.

        Returns:
            True if token was successfully refreshed.
        """
        if not self._token_refresh_callback:
            return False

        async with self._refresh_lock:
            # Check if another coroutine already refreshed
            if self._is_refreshing:
                # Wait for the other refresh to complete
                await asyncio.sleep(0.1)
                return True

            self._is_refreshing = True
            try:
                logger.info("Attempting to refresh authentication token")
                success = await self._token_refresh_callback()
                if success:
                    logger.info("Token refresh successful")
                else:
                    logger.warning("Token refresh failed")
                return success
            except Exception as e:
                logger.error(f"Token refresh error: {e}")
                return False
            finally:
                self._is_refreshing = False

    # -------------------------------------------------------------------------
    # Core Request Method
    # -------------------------------------------------------------------------

    async def _make_request(
        self,
        context: RequestContext,
    ) -> APIResponse:
        """
        Make a single HTTP request.

        Args:
            context: Request context containing all request parameters.

        Returns:
            APIResponse object.
        """
        session = await self._get_session()

        # Log request
        logger.debug(
            f"Request: {context.method.value} {context.url} "
            f"(attempt {context.attempt})"
        )
        if context.data:
            # Log data but mask sensitive fields
            safe_data = self._mask_sensitive_data(context.data)
            logger.debug(f"Request data: {safe_data}")

        try:
            async with session.request(
                method=context.method.value,
                url=context.url,
                json=context.data if context.data else None,
                params=context.params,
                headers=context.headers,
            ) as response:
                # Calculate elapsed time
                elapsed = time.time() - context.start_time

                # Parse response
                response_headers = dict(response.headers)

                try:
                    response_data = await response.json()
                except (aiohttp.ContentTypeError, ValueError):
                    response_data = await response.text()

                api_response = APIResponse(
                    success=response.ok,
                    status_code=response.status,
                    data=response_data,
                    headers=response_headers,
                    elapsed_time=elapsed,
                )

                # Log response
                logger.debug(
                    f"Response: {response.status} "
                    f"(elapsed: {elapsed:.3f}s)"
                )

                return api_response

        except ClientConnectorError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError(ErrorMessages.NETWORK_ERROR) from e

        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout: {context.url}")
            raise TimeoutError("Request timed out. Please try again.") from e

        except Exception as e:
            logger.exception(f"Unexpected error during request: {e}")
            raise APIError(str(e)) from e

    async def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        include_auth: bool = True,
        retry: bool = True,
        max_retries: Optional[int] = None,
    ) -> APIResponse:
        """
        Make an HTTP request with retry logic and interceptors.

        Args:
            method: HTTP method.
            endpoint: API endpoint.
            data: Request body data.
            params: Query parameters.
            headers: Additional headers.
            include_auth: Whether to include authorization.
            retry: Whether to retry on failure.
            max_retries: Maximum retry attempts (uses default if not specified).

        Returns:
            APIResponse object.

        Raises:
            APIError: If request fails after all retries.
        """
        url = self._build_url(endpoint)
        request_headers = self._get_headers(include_auth)
        if headers:
            request_headers.update(headers)

        max_attempts = max_retries if max_retries is not None else self._max_retries
        if not retry:
            max_attempts = 1

        last_error: Optional[Exception] = None
        token_refresh_attempted = False

        for attempt in range(max_attempts):
            # Create request context
            context = RequestContext(
                method=method,
                url=url,
                endpoint=endpoint,
                headers=request_headers.copy(),
                data=data,
                params=params,
                attempt=attempt + 1,
                start_time=time.time(),
            )

            try:
                # Run request interceptors
                for interceptor in self._request_interceptors:
                    context = await interceptor(context)

                # Make the request
                response = await self._make_request(context)

                # Run response interceptors
                for interceptor in self._response_interceptors:
                    response = await interceptor(context, response)

                # Handle specific status codes
                if response.status_code == 401:
                    # Try to refresh token if we haven't already
                    if not token_refresh_attempted and include_auth:
                        token_refresh_attempted = True
                        if await self._handle_token_refresh():
                            # Update headers with new token and retry
                            request_headers = self._get_headers(include_auth)
                            if headers:
                                request_headers.update(headers)
                            continue

                    raise AuthenticationError(
                        ErrorMessages.AUTH_FAILED,
                        status_code=401,
                        response=response,
                    )

                if response.status_code == 403:
                    raise APIError(
                        ErrorMessages.FORBIDDEN,
                        status_code=403,
                        response=response,
                    )

                if response.status_code == 404:
                    raise APIError(
                        ErrorMessages.NOT_FOUND,
                        status_code=404,
                        response=response,
                    )

                if response.status_code == 422:
                    error_detail = self._extract_error_message(response.data)
                    raise ValidationError(
                        error_detail or ErrorMessages.VALIDATION_ERROR,
                        status_code=422,
                        response=response,
                    )

                if response.status_code >= 500:
                    error = APIError(
                        ErrorMessages.SERVER_ERROR,
                        status_code=response.status_code,
                        response=response,
                    )
                    if self._should_retry(error, attempt):
                        delay = self._calculate_retry_delay(attempt)
                        logger.warning(
                            f"Server error (attempt {attempt + 1}/{max_attempts}), "
                            f"retrying in {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise error

                return response

            except (NetworkError, TimeoutError) as e:
                last_error = e
                if self._should_retry(e, attempt):
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"{type(e).__name__} (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

            except AuthenticationError:
                raise  # Don't retry auth errors

            except APIError as e:
                if e.status_code and e.status_code < 500:
                    raise  # Don't retry client errors
                last_error = e
                if self._should_retry(e, attempt):
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"API error (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        raise last_error or APIError("Request failed after all retries")

    def _extract_error_message(self, data: Any) -> Optional[str]:
        """Extract error message from response data."""
        if isinstance(data, dict):
            # FastAPI-style error
            if 'detail' in data:
                detail = data['detail']
                if isinstance(detail, str):
                    return detail
                if isinstance(detail, list) and detail:
                    # Validation error format
                    messages = []
                    for error in detail:
                        if isinstance(error, dict):
                            loc = error.get('loc', [])
                            msg = error.get('msg', '')
                            field = '.'.join(str(l) for l in loc[1:]) if len(loc) > 1 else ''
                            messages.append(f"{field}: {msg}" if field else msg)
                    return '; '.join(messages)

            # Standard error format
            if 'message' in data:
                return data['message']

            if 'error' in data:
                return data['error']

        return None

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in data for logging."""
        sensitive_fields = {'password', 'token', 'access_token', 'refresh_token', 'secret'}
        masked = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                masked[key] = '***MASKED***'
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_data(value)
            else:
                masked[key] = value
        return masked

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Make a GET request."""
        return await self.request(HTTPMethod.GET, endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Make a POST request."""
        return await self.request(HTTPMethod.POST, endpoint, data=data, **kwargs)

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Make a PUT request."""
        return await self.request(HTTPMethod.PUT, endpoint, data=data, **kwargs)

    async def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Make a PATCH request."""
        return await self.request(HTTPMethod.PATCH, endpoint, data=data, **kwargs)

    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> APIResponse:
        """Make a DELETE request."""
        return await self.request(HTTPMethod.DELETE, endpoint, **kwargs)

    # -------------------------------------------------------------------------
    # Context Manager Support
    # -------------------------------------------------------------------------

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# -------------------------------------------------------------------------
# Module-level Singleton Access
# -------------------------------------------------------------------------

_default_client: Optional[APIClient] = None
_default_client_lock = asyncio.Lock()


async def get_api_client(
    token_provider: Optional[Callable[[], Optional[str]]] = None,
    **kwargs
) -> APIClient:
    """
    Get the default API client singleton.

    This is the recommended way to get an API client instance.

    Args:
        token_provider: Token provider callback (only used on first call).
        **kwargs: Additional arguments passed to APIClient.

    Returns:
        The singleton APIClient instance.

    Example:
        client = await get_api_client(token_provider=auth_service.get_access_token)
        response = await client.get("/users")
    """
    global _default_client
    if _default_client is None:
        async with _default_client_lock:
            if _default_client is None:
                _default_client = APIClient(
                    token_provider=token_provider,
                    **kwargs
                )
                logger.info("Default API client created")
    return _default_client


def get_api_client_sync() -> Optional[APIClient]:
    """
    Get the default API client synchronously.

    Returns:
        The singleton instance if it exists, None otherwise.
    """
    return _default_client


async def close_api_client():
    """
    Close the default API client and release resources.

    Should be called when the application is shutting down.
    """
    global _default_client
    async with _default_client_lock:
        if _default_client is not None:
            await _default_client.close()
            _default_client = None
            logger.info("Default API client closed")


# -------------------------------------------------------------------------
# Decorator for Automatic Retry
# -------------------------------------------------------------------------

def with_retry(
    max_retries: int = API_MAX_RETRIES,
    retry_on: tuple = (NetworkError, TimeoutError),
):
    """
    Decorator to add retry logic to async functions.

    Args:
        max_retries: Maximum number of retry attempts.
        retry_on: Tuple of exception types to retry on.

    Example:
        @with_retry(max_retries=3)
        async def fetch_data():
            client = await get_api_client()
            return await client.get("/data")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = API_RETRY_DELAY_SECONDS * (2 ** attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                        )
                        await asyncio.sleep(delay)
            raise last_error
        return wrapper
    return decorator
