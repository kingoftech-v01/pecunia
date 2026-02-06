"""
OAuth Providers Configuration for Pecunia
Supports Google OAuth2 and Apple Sign-In with PKCE security.
"""

import hashlib
import secrets
import base64
import json
import time
import jwt
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone

import requests
import logging

logger = logging.getLogger(__name__)


class OAuthProvider(Enum):
    """Supported OAuth providers."""
    GOOGLE = 'google'
    APPLE = 'apple'


class OAuthError(Exception):
    """Base exception for OAuth errors."""
    pass


class OAuthStateError(OAuthError):
    """Invalid or expired state parameter."""
    pass


class OAuthTokenError(OAuthError):
    """Error obtaining or validating tokens."""
    pass


class OAuthUserInfoError(OAuthError):
    """Error fetching user information."""
    pass


@dataclass
class OAuthUserInfo:
    """Standardized user information from OAuth providers."""
    provider: str
    provider_user_id: str
    email: str
    email_verified: bool
    first_name: str
    last_name: str
    full_name: str
    picture_url: Optional[str] = None
    locale: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class PKCEManager:
    """
    PKCE (Proof Key for Code Exchange) manager for enhanced OAuth security.
    Implements RFC 7636.
    """

    @staticmethod
    def generate_code_verifier(length: int = 64) -> str:
        """
        Generate a cryptographically random code verifier.

        Args:
            length: Length of the verifier (43-128 characters)

        Returns:
            URL-safe base64 encoded random string
        """
        if not 43 <= length <= 128:
            raise ValueError("Code verifier length must be between 43 and 128")

        # PKCE requires high-entropy verifier; token_bytes provides cryptographic randomness.
        random_bytes = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')[:length]

    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """
        Generate S256 code challenge from code verifier.

        Args:
            code_verifier: The code verifier string

        Returns:
            Base64 URL-encoded SHA256 hash of the verifier
        """
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


class OAuthStateManager:
    """
    Manages OAuth state parameters for CSRF protection.
    States are stored in cache with expiration.
    """

    STATE_TIMEOUT = 600  # 10 minutes
    STATE_PREFIX = 'oauth_state_'

    @classmethod
    def generate_state(
        cls,
        provider: str,
        redirect_url: Optional[str] = None,
        link_to_user_id: Optional[int] = None,
        code_verifier: Optional[str] = None
    ) -> str:
        """
        Generate a secure state parameter and store associated data.

        Args:
            provider: OAuth provider name
            redirect_url: URL to redirect after successful auth
            link_to_user_id: User ID to link social account to
            code_verifier: PKCE code verifier for this flow

        Returns:
            The generated state token
        """
        state = secrets.token_urlsafe(32)

        state_data = {
            'provider': provider,
            'redirect_url': redirect_url,
            'link_to_user_id': link_to_user_id,
            'code_verifier': code_verifier,
            'created_at': timezone.now().isoformat(),
        }

        cache_key = f"{cls.STATE_PREFIX}{state}"
        cache.set(cache_key, state_data, cls.STATE_TIMEOUT)

        logger.debug(f"Generated OAuth state for provider {provider}")
        return state

    @classmethod
    def validate_state(cls, state: str) -> Dict[str, Any]:
        """
        Validate and consume a state parameter.

        Args:
            state: The state token to validate

        Returns:
            The stored state data

        Raises:
            OAuthStateError: If state is invalid or expired
        """
        if not state:
            raise OAuthStateError("Missing state parameter")

        cache_key = f"{cls.STATE_PREFIX}{state}"
        state_data = cache.get(cache_key)

        if state_data is None:
            raise OAuthStateError("Invalid or expired state parameter")

        # Delete immediately: single-use prevents replay attacks with stolen state.
        cache.delete(cache_key)

        logger.debug(f"Validated OAuth state for provider {state_data.get('provider')}")
        return state_data


class BaseOAuth2Provider:
    """
    Base class for OAuth2 providers.
    Implements common OAuth2 flow with PKCE support.
    """

    provider_name: str = ''
    authorization_url: str = ''
    token_url: str = ''
    userinfo_url: str = ''
    revoke_url: Optional[str] = None

    # Default scopes
    default_scopes: list = []

    # Whether this provider supports PKCE
    supports_pkce: bool = True

    def __init__(self):
        self.client_id = self._get_client_id()
        self.client_secret = self._get_client_secret()

    def _get_client_id(self) -> str:
        """Get client ID from settings."""
        raise NotImplementedError

    def _get_client_secret(self) -> str:
        """Get client secret from settings."""
        raise NotImplementedError

    def get_callback_url(self, request) -> str:
        """Get the OAuth callback URL."""
        callback_path = reverse('accounts:oauth_callback', kwargs={'provider': self.provider_name})
        return request.build_absolute_uri(callback_path)

    def get_oauth_url(
        self,
        request,
        redirect_url: Optional[str] = None,
        link_to_user_id: Optional[int] = None,
        scopes: Optional[list] = None,
        extra_params: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate the OAuth authorization URL.

        Args:
            request: Django request object
            redirect_url: URL to redirect after auth
            link_to_user_id: User ID to link account to
            scopes: OAuth scopes to request
            extra_params: Additional URL parameters

        Returns:
            The authorization URL
        """
        # Generate PKCE parameters if supported
        code_verifier = None
        code_challenge = None

        if self.supports_pkce:
            code_verifier = PKCEManager.generate_code_verifier()
            code_challenge = PKCEManager.generate_code_challenge(code_verifier)

        # Generate state
        state = OAuthStateManager.generate_state(
            provider=self.provider_name,
            redirect_url=redirect_url,
            link_to_user_id=link_to_user_id,
            code_verifier=code_verifier
        )

        # Build authorization URL
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.get_callback_url(request),
            'response_type': 'code',
            'scope': ' '.join(scopes or self.default_scopes),
            'state': state,
        }

        if self.supports_pkce and code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = 'S256'

        if extra_params:
            params.update(extra_params)

        return f"{self.authorization_url}?{urlencode(params)}"

    def handle_callback(
        self,
        request,
        code: str,
        state: str
    ) -> Tuple[OAuthUserInfo, Dict[str, Any]]:
        """
        Handle the OAuth callback.

        Args:
            request: Django request object
            code: Authorization code from provider
            state: State parameter for validation

        Returns:
            Tuple of (user_info, state_data)

        Raises:
            OAuthError: On any OAuth error
        """
        # Validate state
        state_data = OAuthStateManager.validate_state(state)

        if state_data['provider'] != self.provider_name:
            raise OAuthStateError("Provider mismatch in state parameter")

        # Exchange code for tokens
        tokens = self._exchange_code(
            request=request,
            code=code,
            code_verifier=state_data.get('code_verifier')
        )

        # Get user info
        user_info = self._get_user_info(tokens)

        return user_info, state_data

    def _exchange_code(
        self,
        request,
        code: str,
        code_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            request: Django request object
            code: Authorization code
            code_verifier: PKCE code verifier

        Returns:
            Token response data

        Raises:
            OAuthTokenError: On token exchange failure
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.get_callback_url(request),
        }

        if code_verifier:
            data['code_verifier'] = code_verifier

        try:
            response = requests.post(
                self.token_url,
                data=data,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token exchange failed for {self.provider_name}: {e}")
            raise OAuthTokenError(f"Failed to exchange authorization code: {e}")

    def _get_user_info(self, tokens: Dict[str, Any]) -> OAuthUserInfo:
        """
        Get user information from the provider.

        Args:
            tokens: Token response data

        Returns:
            Standardized user information

        Raises:
            OAuthUserInfoError: On user info fetch failure
        """
        raise NotImplementedError

    def revoke_token(self, token: str) -> bool:
        """
        Revoke an OAuth token.

        Args:
            token: Token to revoke

        Returns:
            True if revocation was successful
        """
        if not self.revoke_url:
            return False

        try:
            response = requests.post(
                self.revoke_url,
                data={'token': token},
                timeout=30
            )
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Token revocation failed for {self.provider_name}: {e}")
            return False


class GoogleOAuth2Provider(BaseOAuth2Provider):
    """
    Google OAuth2 Provider implementation.

    Supports:
    - Standard OAuth2 flow with PKCE
    - OpenID Connect for user info
    - Token refresh
    """

    provider_name = 'google'
    authorization_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    token_url = 'https://oauth2.googleapis.com/token'
    userinfo_url = 'https://openidconnect.googleapis.com/v1/userinfo'
    revoke_url = 'https://oauth2.googleapis.com/revoke'

    default_scopes = [
        'openid',
        'email',
        'profile',
    ]

    supports_pkce = True

    def _get_client_id(self) -> str:
        return getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')

    def _get_client_secret(self) -> str:
        return getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')

    def get_oauth_url(
        self,
        request,
        redirect_url: Optional[str] = None,
        link_to_user_id: Optional[int] = None,
        scopes: Optional[list] = None,
        extra_params: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate Google OAuth URL with additional parameters.
        """
        google_params = {
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent',  # Always show consent screen for refresh token
        }

        if extra_params:
            google_params.update(extra_params)

        return super().get_oauth_url(
            request=request,
            redirect_url=redirect_url,
            link_to_user_id=link_to_user_id,
            scopes=scopes,
            extra_params=google_params
        )

    def _get_user_info(self, tokens: Dict[str, Any]) -> OAuthUserInfo:
        """
        Get user info from Google.
        Uses the ID token if available, otherwise calls userinfo endpoint.
        """
        access_token = tokens.get('access_token')
        id_token = tokens.get('id_token')

        # ID token contains claims locally; avoids extra API call to userinfo.
        if id_token:
            try:
                # Fetch Google's public keys for JWT verification
                jwks_client = jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")
                signing_key = jwks_client.get_signing_key_from_jwt(id_token)
                payload = jwt.decode(
                    id_token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=self.client_id,
                    issuer=["https://accounts.google.com", "accounts.google.com"],
                )

                return OAuthUserInfo(
                    provider=self.provider_name,
                    provider_user_id=payload.get('sub', ''),
                    email=payload.get('email', ''),
                    email_verified=payload.get('email_verified', False),
                    first_name=payload.get('given_name', ''),
                    last_name=payload.get('family_name', ''),
                    full_name=payload.get('name', ''),
                    picture_url=payload.get('picture'),
                    locale=payload.get('locale'),
                    raw_data=payload
                )
            except (jwt.DecodeError, jwt.InvalidTokenError, jwt.ExpiredSignatureError) as e:
                logger.warning("Failed to verify Google ID token (%s), falling back to userinfo", e)

        # Fall back to userinfo endpoint
        try:
            response = requests.get(
                self.userinfo_url,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return OAuthUserInfo(
                provider=self.provider_name,
                provider_user_id=data.get('sub', ''),
                email=data.get('email', ''),
                email_verified=data.get('email_verified', False),
                first_name=data.get('given_name', ''),
                last_name=data.get('family_name', ''),
                full_name=data.get('name', ''),
                picture_url=data.get('picture'),
                locale=data.get('locale'),
                raw_data=data
            )
        except requests.RequestException as e:
            logger.error(f"Failed to get Google user info: {e}")
            raise OAuthUserInfoError(f"Failed to get user information from Google: {e}")

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token

        Returns:
            New token data

        Raises:
            OAuthTokenError: On refresh failure
        """
        try:
            response = requests.post(
                self.token_url,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                },
                headers={'Accept': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token refresh failed: {e}")
            raise OAuthTokenError(f"Failed to refresh access token: {e}")


class AppleOAuth2Provider(BaseOAuth2Provider):
    """
    Apple Sign-In Provider implementation.

    Supports:
    - Sign in with Apple OAuth2 flow
    - PKCE for enhanced security
    - JWT client secret generation

    Note: Apple requires JWT-based client authentication and provides
    user info only on first authorization.
    """

    provider_name = 'apple'
    authorization_url = 'https://appleid.apple.com/auth/authorize'
    token_url = 'https://appleid.apple.com/auth/token'
    revoke_url = 'https://appleid.apple.com/auth/revoke'

    default_scopes = [
        'name',
        'email',
    ]

    supports_pkce = True

    # Cache for client secret JWT
    _client_secret_cache = None
    _client_secret_expiry = None

    def _get_client_id(self) -> str:
        return getattr(settings, 'APPLE_CLIENT_ID', '')  # Services ID

    def _get_client_secret(self) -> str:
        """
        Generate JWT client secret for Apple.
        Apple requires a JWT signed with your private key instead of a static secret.
        """
        # Check cache
        if (
            self._client_secret_cache and
            self._client_secret_expiry and
            time.time() < self._client_secret_expiry - 60
        ):
            return self._client_secret_cache

        team_id = getattr(settings, 'APPLE_TEAM_ID', '')
        key_id = getattr(settings, 'APPLE_KEY_ID', '')
        private_key = getattr(settings, 'APPLE_PRIVATE_KEY', '')

        if not all([team_id, key_id, private_key]):
            logger.error("Missing Apple OAuth configuration")
            return ''

        now = int(time.time())
        expiry = now + (86400 * 180)  # 6 months max

        headers = {
            'alg': 'ES256',
            'kid': key_id,
        }

        payload = {
            'iss': team_id,
            'iat': now,
            'exp': expiry,
            'aud': 'https://appleid.apple.com',
            'sub': self.client_id,
        }

        try:
            client_secret = jwt.encode(
                payload,
                private_key,
                algorithm='ES256',
                headers=headers
            )

            # Cache to avoid regenerating JWT for every request; 6-month max per Apple.
            AppleOAuth2Provider._client_secret_cache = client_secret
            AppleOAuth2Provider._client_secret_expiry = expiry

            return client_secret
        except Exception as e:
            logger.error(f"Failed to generate Apple client secret: {e}")
            return ''

    def get_oauth_url(
        self,
        request,
        redirect_url: Optional[str] = None,
        link_to_user_id: Optional[int] = None,
        scopes: Optional[list] = None,
        extra_params: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate Apple Sign-In URL.
        """
        apple_params = {
            'response_mode': 'form_post',  # Apple uses form_post
        }

        if extra_params:
            apple_params.update(extra_params)

        return super().get_oauth_url(
            request=request,
            redirect_url=redirect_url,
            link_to_user_id=link_to_user_id,
            scopes=scopes,
            extra_params=apple_params
        )

    def handle_callback(
        self,
        request,
        code: str,
        state: str,
        user_data: Optional[str] = None
    ) -> Tuple[OAuthUserInfo, Dict[str, Any]]:
        """
        Handle Apple Sign-In callback.

        Apple sends user info only on first authorization via POST body.

        Args:
            request: Django request
            code: Authorization code
            state: State parameter
            user_data: JSON string with user info (first auth only)

        Returns:
            Tuple of (user_info, state_data)
        """
        # Validate state
        state_data = OAuthStateManager.validate_state(state)

        if state_data['provider'] != self.provider_name:
            raise OAuthStateError("Provider mismatch in state parameter")

        # Parse user data if provided (first authorization only)
        parsed_user_data = None
        if user_data:
            try:
                parsed_user_data = json.loads(user_data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse Apple user data")

        # Exchange code for tokens
        tokens = self._exchange_code(
            request=request,
            code=code,
            code_verifier=state_data.get('code_verifier')
        )

        # Get user info
        user_info = self._get_user_info(tokens, parsed_user_data)

        return user_info, state_data

    def _get_user_info(
        self,
        tokens: Dict[str, Any],
        user_data: Optional[Dict[str, Any]] = None
    ) -> OAuthUserInfo:
        """
        Get user info from Apple ID token and optional user data.

        Apple provides user name only on first authorization.
        We get email from the ID token.
        """
        id_token = tokens.get('id_token')

        if not id_token:
            raise OAuthUserInfoError("Missing ID token from Apple")

        try:
            # Verify and decode Apple ID token using Apple's public keys
            jwks_client = jwt.PyJWKClient("https://appleid.apple.com/auth/keys")
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            payload = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer="https://appleid.apple.com",
            )

            # Extract email
            email = payload.get('email', '')
            email_verified = payload.get('email_verified', 'false')
            if isinstance(email_verified, str):
                email_verified = email_verified.lower() == 'true'

            # Extract name from user_data if available
            first_name = ''
            last_name = ''
            full_name = ''

            if user_data and 'name' in user_data:
                name_data = user_data['name']
                first_name = name_data.get('firstName', '')
                last_name = name_data.get('lastName', '')
                full_name = f"{first_name} {last_name}".strip()

            return OAuthUserInfo(
                provider=self.provider_name,
                provider_user_id=payload.get('sub', ''),
                email=email,
                email_verified=email_verified,
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                picture_url=None,  # Apple doesn't provide profile picture
                locale=None,
                raw_data={
                    'id_token_payload': payload,
                    'user_data': user_data
                }
            )
        except (jwt.DecodeError, jwt.InvalidTokenError, jwt.ExpiredSignatureError) as e:
            logger.error("Failed to verify Apple ID token: %s", e)
            raise OAuthUserInfoError(f"Failed to verify Apple ID token: {e}")


# Provider registry
OAUTH_PROVIDERS: Dict[str, type] = {
    'google': GoogleOAuth2Provider,
    'apple': AppleOAuth2Provider,
}


def get_oauth_provider(provider_name: str) -> BaseOAuth2Provider:
    """
    Get an OAuth provider instance by name.

    Args:
        provider_name: Name of the provider ('google', 'apple')

    Returns:
        Provider instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_class = OAUTH_PROVIDERS.get(provider_name.lower())

    if not provider_class:
        raise ValueError(f"Unsupported OAuth provider: {provider_name}")

    return provider_class()


def get_oauth_url(
    request,
    provider_name: str,
    redirect_url: Optional[str] = None,
    link_to_user_id: Optional[int] = None
) -> str:
    """
    Convenience function to get OAuth URL for a provider.

    Args:
        request: Django request
        provider_name: Provider name
        redirect_url: URL to redirect after auth
        link_to_user_id: User ID to link account to

    Returns:
        OAuth authorization URL
    """
    provider = get_oauth_provider(provider_name)
    return provider.get_oauth_url(
        request=request,
        redirect_url=redirect_url,
        link_to_user_id=link_to_user_id
    )


def handle_callback(
    request,
    provider_name: str,
    code: str,
    state: str,
    **kwargs
) -> Tuple[OAuthUserInfo, Dict[str, Any]]:
    """
    Convenience function to handle OAuth callback.

    Args:
        request: Django request
        provider_name: Provider name
        code: Authorization code
        state: State parameter
        **kwargs: Additional provider-specific parameters

    Returns:
        Tuple of (user_info, state_data)
    """
    provider = get_oauth_provider(provider_name)
    return provider.handle_callback(request, code, state, **kwargs)
