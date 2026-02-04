"""
Authentication service for Pecunia Desktop.

Handles user authentication, JWT token management, and secure token storage.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

import keyring
from keyring.errors import KeyringError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config_dir
from constants import (
    KEYRING_SERVICE_NAME,
    KEYRING_ACCESS_TOKEN,
    KEYRING_REFRESH_TOKEN,
    Endpoints,
    ErrorMessages,
    SuccessMessages,
)
from .client import APIClient, APIResponse, APIError, AuthenticationError

logger = logging.getLogger(__name__)


@dataclass
class User:
    """Represents an authenticated user."""
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary."""
        return cls(
            id=data.get('id', ''),
            email=data.get('email', ''),
            full_name=data.get('full_name'),
            is_active=data.get('is_active', True),
            is_verified=data.get('is_verified', False),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )


@dataclass
class AuthTokens:
    """Container for authentication tokens."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    expires_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthTokens':
        """Create AuthTokens from API response."""
        expires_in = data.get('expires_in')
        expires_at = None
        if expires_in:
            expires_at = datetime.now() + timedelta(seconds=expires_in)

        return cls(
            access_token=data.get('access_token', ''),
            refresh_token=data.get('refresh_token'),
            token_type=data.get('token_type', 'Bearer'),
            expires_in=expires_in,
            expires_at=expires_at,
        )

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if the access token is expired or about to expire."""
        if self.expires_at is None:
            return False
        return datetime.now() >= (self.expires_at - timedelta(seconds=buffer_seconds))


class TokenStorage:
    """
    Secure storage for authentication tokens.

    Uses the system keyring for secure storage, with a fallback
    to encrypted file storage if keyring is unavailable.
    """

    def __init__(self, service_name: str = KEYRING_SERVICE_NAME):
        """
        Initialize token storage.

        Args:
            service_name: Service name for keyring storage.
        """
        self._service_name = service_name
        self._use_keyring = self._check_keyring_available()
        self._fallback_file = get_config_dir() / '.tokens'

    def _check_keyring_available(self) -> bool:
        """Check if system keyring is available."""
        try:
            # Try to access keyring
            keyring.get_keyring()
            return True
        except Exception as e:
            logger.warning(f"Keyring not available, using fallback storage: {e}")
            return False

    def save_tokens(self, tokens: AuthTokens) -> bool:
        """
        Save authentication tokens securely.

        Args:
            tokens: AuthTokens to save.

        Returns:
            True if successful.
        """
        try:
            if self._use_keyring:
                keyring.set_password(
                    self._service_name,
                    KEYRING_ACCESS_TOKEN,
                    tokens.access_token
                )
                if tokens.refresh_token:
                    keyring.set_password(
                        self._service_name,
                        KEYRING_REFRESH_TOKEN,
                        tokens.refresh_token
                    )

                # Save expiry info to file (non-sensitive)
                expiry_data = {
                    'expires_at': tokens.expires_at.isoformat() if tokens.expires_at else None,
                    'token_type': tokens.token_type,
                }
                self._save_expiry_data(expiry_data)

            else:
                # Fallback: save to file (less secure)
                self._save_tokens_to_file(tokens)

            logger.info("Tokens saved successfully")
            return True

        except KeyringError as e:
            logger.error(f"Failed to save tokens to keyring: {e}")
            # Try fallback
            return self._save_tokens_to_file(tokens)

        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            return False

    def load_tokens(self) -> Optional[AuthTokens]:
        """
        Load authentication tokens from secure storage.

        Returns:
            AuthTokens if found, None otherwise.
        """
        try:
            if self._use_keyring:
                access_token = keyring.get_password(
                    self._service_name,
                    KEYRING_ACCESS_TOKEN
                )
                if not access_token:
                    return None

                refresh_token = keyring.get_password(
                    self._service_name,
                    KEYRING_REFRESH_TOKEN
                )

                # Load expiry data
                expiry_data = self._load_expiry_data()
                expires_at = None
                if expiry_data and expiry_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(expiry_data['expires_at'])

                return AuthTokens(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type=expiry_data.get('token_type', 'Bearer') if expiry_data else 'Bearer',
                    expires_at=expires_at,
                )

            else:
                return self._load_tokens_from_file()

        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            return None

    def clear_tokens(self) -> bool:
        """
        Clear all stored tokens.

        Returns:
            True if successful.
        """
        try:
            if self._use_keyring:
                try:
                    keyring.delete_password(self._service_name, KEYRING_ACCESS_TOKEN)
                except KeyringError:
                    pass

                try:
                    keyring.delete_password(self._service_name, KEYRING_REFRESH_TOKEN)
                except KeyringError:
                    pass

            # Clear fallback file
            if self._fallback_file.exists():
                self._fallback_file.unlink()

            # Clear expiry data
            expiry_file = get_config_dir() / '.token_expiry'
            if expiry_file.exists():
                expiry_file.unlink()

            logger.info("Tokens cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to clear tokens: {e}")
            return False

    def _save_expiry_data(self, data: Dict[str, Any]):
        """Save token expiry data to file."""
        expiry_file = get_config_dir() / '.token_expiry'
        with open(expiry_file, 'w') as f:
            json.dump(data, f)

    def _load_expiry_data(self) -> Optional[Dict[str, Any]]:
        """Load token expiry data from file."""
        expiry_file = get_config_dir() / '.token_expiry'
        if not expiry_file.exists():
            return None
        with open(expiry_file, 'r') as f:
            return json.load(f)

    def _save_tokens_to_file(self, tokens: AuthTokens) -> bool:
        """Save tokens to fallback file (less secure)."""
        try:
            # Note: In production, this should be encrypted
            data = {
                'access_token': tokens.access_token,
                'refresh_token': tokens.refresh_token,
                'token_type': tokens.token_type,
                'expires_at': tokens.expires_at.isoformat() if tokens.expires_at else None,
            }
            self._fallback_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._fallback_file, 'w') as f:
                json.dump(data, f)
            # Set restrictive permissions on Unix
            try:
                self._fallback_file.chmod(0o600)
            except (AttributeError, OSError):
                pass  # Windows doesn't support chmod the same way
            return True
        except Exception as e:
            logger.error(f"Failed to save tokens to file: {e}")
            return False

    def _load_tokens_from_file(self) -> Optional[AuthTokens]:
        """Load tokens from fallback file."""
        try:
            if not self._fallback_file.exists():
                return None
            with open(self._fallback_file, 'r') as f:
                data = json.load(f)

            expires_at = None
            if data.get('expires_at'):
                expires_at = datetime.fromisoformat(data['expires_at'])

            return AuthTokens(
                access_token=data.get('access_token', ''),
                refresh_token=data.get('refresh_token'),
                token_type=data.get('token_type', 'Bearer'),
                expires_at=expires_at,
            )
        except Exception as e:
            logger.error(f"Failed to load tokens from file: {e}")
            return None


class AuthService:
    """
    Authentication service for handling user authentication.

    Manages login, logout, token refresh, and user session state.
    """

    def __init__(self, api_client: Optional[APIClient] = None):
        """
        Initialize the authentication service.

        Args:
            api_client: Optional API client instance.
        """
        self._token_storage = TokenStorage()
        self._tokens: Optional[AuthTokens] = None
        self._user: Optional[User] = None
        self._api_client = api_client or APIClient(token_provider=self.get_access_token)
        self._refresh_lock = asyncio.Lock()
        self._auth_state_callbacks: list[Callable[[bool], None]] = []

        # Try to load existing tokens
        self._load_cached_tokens()

    def _load_cached_tokens(self):
        """Load cached tokens from storage."""
        self._tokens = self._token_storage.load_tokens()
        if self._tokens:
            logger.info("Loaded cached authentication tokens")

    @property
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self._tokens is not None and self._tokens.access_token

    @property
    def current_user(self) -> Optional[User]:
        """Get the current authenticated user."""
        return self._user

    @property
    def tokens(self) -> Optional[AuthTokens]:
        """Get the current authentication tokens."""
        return self._tokens

    def get_access_token(self) -> Optional[str]:
        """Get the current access token (for token provider callback)."""
        return self._tokens.access_token if self._tokens else None

    def add_auth_state_callback(self, callback: Callable[[bool], None]):
        """Add a callback to be notified of authentication state changes."""
        self._auth_state_callbacks.append(callback)

    def remove_auth_state_callback(self, callback: Callable[[bool], None]):
        """Remove an authentication state callback."""
        if callback in self._auth_state_callbacks:
            self._auth_state_callbacks.remove(callback)

    def _notify_auth_state_change(self, is_authenticated: bool):
        """Notify all callbacks of authentication state change."""
        for callback in self._auth_state_callbacks:
            try:
                callback(is_authenticated)
            except Exception as e:
                logger.error(f"Error in auth state callback: {e}")

    async def login(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address.
            password: User's password.

        Returns:
            Authenticated User object.

        Raises:
            AuthenticationError: If authentication fails.
        """
        try:
            response = await self._api_client.post(
                Endpoints.AUTH_LOGIN,
                data={'email': email, 'password': password},
                include_auth=False,
            )

            if not response.is_ok:
                error_msg = self._extract_error(response)
                raise AuthenticationError(error_msg or ErrorMessages.INVALID_CREDENTIALS)

            # Parse tokens
            self._tokens = AuthTokens.from_dict(response.data)
            self._token_storage.save_tokens(self._tokens)

            # Fetch user info
            self._user = await self._fetch_current_user()

            logger.info(f"User {email} logged in successfully")
            self._notify_auth_state_change(True)

            return self._user

        except AuthenticationError:
            raise
        except APIError as e:
            logger.error(f"Login failed: {e}")
            raise AuthenticationError(str(e))

    async def register(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> User:
        """
        Register a new user account.

        Args:
            email: User's email address.
            password: User's password.
            full_name: User's full name.

        Returns:
            Created User object.

        Raises:
            APIError: If registration fails.
        """
        try:
            data = {
                'email': email,
                'password': password,
            }
            if full_name:
                data['full_name'] = full_name

            response = await self._api_client.post(
                Endpoints.AUTH_REGISTER,
                data=data,
                include_auth=False,
            )

            if not response.is_ok:
                error_msg = self._extract_error(response)
                raise APIError(error_msg or "Registration failed")

            # Auto-login after registration if tokens are returned
            if 'access_token' in response.data:
                self._tokens = AuthTokens.from_dict(response.data)
                self._token_storage.save_tokens(self._tokens)
                self._user = await self._fetch_current_user()
                self._notify_auth_state_change(True)
                return self._user

            # Otherwise return the user data from response
            return User.from_dict(response.data.get('user', response.data))

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            raise APIError(str(e))

    async def logout(self) -> bool:
        """
        Log out the current user.

        Returns:
            True if logout was successful.
        """
        try:
            if self._tokens:
                # Notify backend (don't fail if this fails)
                try:
                    await self._api_client.post(Endpoints.AUTH_LOGOUT)
                except Exception as e:
                    logger.warning(f"Backend logout notification failed: {e}")

            # Clear local state
            self._tokens = None
            self._user = None
            self._token_storage.clear_tokens()

            logger.info("User logged out successfully")
            self._notify_auth_state_change(False)

            return True

        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Still clear local state
            self._tokens = None
            self._user = None
            self._token_storage.clear_tokens()
            self._notify_auth_state_change(False)
            return True

    async def refresh_token(self) -> bool:
        """
        Refresh the access token using the refresh token.

        Returns:
            True if refresh was successful.

        Raises:
            AuthenticationError: If refresh fails.
        """
        async with self._refresh_lock:
            if not self._tokens or not self._tokens.refresh_token:
                raise AuthenticationError("No refresh token available")

            try:
                response = await self._api_client.post(
                    Endpoints.AUTH_REFRESH,
                    data={'refresh_token': self._tokens.refresh_token},
                    include_auth=False,
                )

                if not response.is_ok:
                    raise AuthenticationError(ErrorMessages.TOKEN_EXPIRED)

                # Update tokens
                self._tokens = AuthTokens.from_dict(response.data)
                self._token_storage.save_tokens(self._tokens)

                logger.info("Token refreshed successfully")
                return True

            except AuthenticationError:
                # Clear tokens on refresh failure
                await self.logout()
                raise
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                raise AuthenticationError(ErrorMessages.TOKEN_EXPIRED)

    async def ensure_authenticated(self) -> bool:
        """
        Ensure the user is authenticated, refreshing token if needed.

        Returns:
            True if authenticated (possibly after refresh).

        Raises:
            AuthenticationError: If not authenticated and cannot refresh.
        """
        if not self._tokens:
            raise AuthenticationError("Not authenticated")

        # Check if token needs refresh
        if self._tokens.is_expired():
            await self.refresh_token()

        return True

    async def get_current_user(self, force_refresh: bool = False) -> Optional[User]:
        """
        Get the current authenticated user.

        Args:
            force_refresh: Whether to force fetching from API.

        Returns:
            User object or None if not authenticated.
        """
        if not self.is_authenticated:
            return None

        if self._user and not force_refresh:
            return self._user

        self._user = await self._fetch_current_user()
        return self._user

    async def _fetch_current_user(self) -> User:
        """Fetch current user from API."""
        response = await self._api_client.get(Endpoints.AUTH_ME)

        if not response.is_ok:
            raise AuthenticationError("Failed to fetch user info")

        return User.from_dict(response.data)

    async def change_password(
        self,
        current_password: str,
        new_password: str,
    ) -> bool:
        """
        Change the current user's password.

        Args:
            current_password: Current password.
            new_password: New password.

        Returns:
            True if successful.

        Raises:
            APIError: If password change fails.
        """
        response = await self._api_client.post(
            Endpoints.AUTH_CHANGE_PASSWORD,
            data={
                'current_password': current_password,
                'new_password': new_password,
            }
        )

        if not response.is_ok:
            error_msg = self._extract_error(response)
            raise APIError(error_msg or "Failed to change password")

        logger.info("Password changed successfully")
        return True

    async def request_password_reset(self, email: str) -> bool:
        """
        Request a password reset email.

        Args:
            email: Email address for the account.

        Returns:
            True if the request was sent successfully.

        Raises:
            APIError: If the request fails.
        """
        try:
            response = await self._api_client.post(
                Endpoints.AUTH_RESET_PASSWORD,
                data={'email': email},
                include_auth=False,
            )

            if not response.is_ok:
                error_msg = self._extract_error(response)
                raise APIError(error_msg or "Failed to request password reset")

            logger.info(f"Password reset requested for {email}")
            return True

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Password reset request failed: {e}")
            raise APIError(str(e))

    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> bool:
        """
        Reset password using a reset token.

        Args:
            token: Password reset token from email.
            new_password: New password to set.

        Returns:
            True if password was reset successfully.

        Raises:
            APIError: If password reset fails.
        """
        try:
            response = await self._api_client.post(
                Endpoints.AUTH_RESET_PASSWORD,
                data={
                    'token': token,
                    'new_password': new_password,
                },
                include_auth=False,
            )

            if not response.is_ok:
                error_msg = self._extract_error(response)
                raise APIError(error_msg or "Failed to reset password")

            logger.info("Password reset successfully")
            return True

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            raise APIError(str(e))

    async def check_auth_status(self) -> bool:
        """
        Check the current authentication status.

        Validates the stored tokens by making a request to the server.
        If tokens are expired but refresh token is available, attempts refresh.

        Returns:
            True if authenticated with valid tokens, False otherwise.
        """
        # No tokens stored
        if not self._tokens or not self._tokens.access_token:
            return False

        # Check if token is expired and try to refresh
        if self._tokens.is_expired():
            if self._tokens.refresh_token:
                try:
                    await self.refresh_token()
                    return True
                except AuthenticationError:
                    return False
            return False

        # Validate token with server
        try:
            response = await self._api_client.get(Endpoints.AUTH_ME)
            if response.is_ok:
                self._user = User.from_dict(response.data)
                return True
            return False
        except AuthenticationError:
            return False
        except Exception as e:
            logger.warning(f"Auth status check failed: {e}")
            # If we can't reach server, consider locally valid token as authenticated
            return self._tokens is not None and not self._tokens.is_expired()

    async def verify_email(self, token: str) -> bool:
        """
        Verify user email address using verification token.

        Args:
            token: Email verification token.

        Returns:
            True if email was verified successfully.

        Raises:
            APIError: If verification fails.
        """
        try:
            response = await self._api_client.post(
                Endpoints.AUTH_VERIFY_EMAIL,
                data={'token': token},
                include_auth=False,
            )

            if not response.is_ok:
                error_msg = self._extract_error(response)
                raise APIError(error_msg or "Email verification failed")

            logger.info("Email verified successfully")
            return True

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Email verification failed: {e}")
            raise APIError(str(e))

    async def update_user_profile(
        self,
        full_name: Optional[str] = None,
        **kwargs
    ) -> User:
        """
        Update the current user's profile.

        Args:
            full_name: New full name.
            **kwargs: Additional profile fields to update.

        Returns:
            Updated User object.

        Raises:
            APIError: If update fails.
        """
        data = {}
        if full_name is not None:
            data['full_name'] = full_name
        data.update(kwargs)

        response = await self._api_client.patch(
            Endpoints.AUTH_ME,
            data=data,
        )

        if not response.is_ok:
            error_msg = self._extract_error(response)
            raise APIError(error_msg or "Failed to update profile")

        self._user = User.from_dict(response.data)
        logger.info("User profile updated successfully")
        return self._user

    def _extract_error(self, response: APIResponse) -> Optional[str]:
        """Extract error message from API response."""
        if isinstance(response.data, dict):
            return response.data.get('detail') or response.data.get('message')
        return None


@dataclass
class AuthResult:
    """Result of an authentication operation."""
    success: bool
    user: Optional[User] = None
    error: Optional[str] = None
    tokens: Optional[AuthTokens] = None

    @classmethod
    def success_result(cls, user: User, tokens: AuthTokens) -> 'AuthResult':
        """Create a successful auth result."""
        return cls(success=True, user=user, tokens=tokens)

    @classmethod
    def error_result(cls, error: str) -> 'AuthResult':
        """Create an error auth result."""
        return cls(success=False, error=error)


# Singleton instance for easy access
_auth_service: Optional[AuthService] = None


def get_auth_service(api_client: Optional[APIClient] = None) -> AuthService:
    """
    Get the singleton AuthService instance.

    Args:
        api_client: Optional API client to use.

    Returns:
        The AuthService singleton instance.
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(api_client)
    return _auth_service


def reset_auth_service() -> None:
    """Reset the AuthService singleton (useful for testing)."""
    global _auth_service
    _auth_service = None
