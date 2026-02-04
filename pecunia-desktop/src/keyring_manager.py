"""
Keyring Manager for Pecunia Desktop.

Provides secure credential storage with:
- System keyring integration (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- JWT token management with expiry tracking
- Local encrypted file fallback when keyring unavailable
- Cross-platform support
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config import get_config_dir, get_credentials_path

# Optional imports with fallbacks
try:
    import keyring
    from keyring.errors import KeyringError, PasswordDeleteError
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None  # type: ignore
    KeyringError = Exception  # type: ignore
    PasswordDeleteError = Exception  # type: ignore

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore

from constants import (
    APP_NAME,
    KEYRING_SERVICE_NAME,
    KEYRING_ACCESS_TOKEN,
    KEYRING_REFRESH_TOKEN,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Keyring keys
KEY_ACCESS_TOKEN = "access_token"
KEY_REFRESH_TOKEN = "refresh_token"
KEY_TOKEN_EXPIRY = "token_expiry"
KEY_USER_ID = "user_id"
KEY_USER_EMAIL = "user_email"
KEY_ENCRYPTION_KEY = "encryption_key"

# Encryption settings
ENCRYPTION_SALT_SIZE = 16
ENCRYPTION_KEY_SIZE = 32
ENCRYPTION_ITERATIONS = 480000  # OWASP recommended


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TokenInfo:
    """Information about a stored token."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at is None:
            return False
        # Add 30 second buffer
        return datetime.now() >= (self.expires_at - timedelta(seconds=30))

    @property
    def is_valid(self) -> bool:
        """Check if we have a valid access token."""
        return bool(self.access_token) and not self.is_expired

    @property
    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time remaining until token expires."""
        if self.expires_at is None:
            return None
        return self.expires_at - datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "user_id": self.user_id,
            "user_email": self.user_email,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenInfo":
        """Create from dictionary."""
        expires_at = None
        if data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(data["expires_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            user_id=data.get("user_id"),
            user_email=data.get("user_email"),
        )


# =============================================================================
# Abstract Backend
# =============================================================================

class CredentialBackend(ABC):
    """Abstract base class for credential storage backends."""

    @abstractmethod
    def store(self, key: str, value: str) -> bool:
        """Store a credential."""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve a credential."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a credential."""
        pass

    @abstractmethod
    def clear_all(self) -> bool:
        """Clear all credentials."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available."""
        pass


# =============================================================================
# Keyring Backend
# =============================================================================

class KeyringBackend(CredentialBackend):
    """
    System keyring backend.

    Uses the system's native credential storage:
    - Windows: Credential Manager
    - macOS: Keychain
    - Linux: Secret Service (GNOME Keyring, KWallet)
    """

    def __init__(self, service_name: str = KEYRING_SERVICE_NAME):
        self._service_name = service_name
        self._available: Optional[bool] = None

    def _get_username(self, key: str) -> str:
        """Generate username for keyring entry."""
        return f"{APP_NAME}_{key}"

    def is_available(self) -> bool:
        """Check if keyring is available and functional."""
        if self._available is not None:
            return self._available

        if not KEYRING_AVAILABLE:
            self._available = False
            return False

        try:
            # Test keyring functionality
            test_key = f"_test_{secrets.token_hex(8)}"
            keyring.set_password(self._service_name, test_key, "test")
            result = keyring.get_password(self._service_name, test_key)
            keyring.delete_password(self._service_name, test_key)
            self._available = result == "test"
        except Exception as e:
            logger.warning(f"Keyring not available: {e}")
            self._available = False

        return self._available

    def store(self, key: str, value: str) -> bool:
        """Store a credential in the system keyring."""
        if not self.is_available():
            return False

        try:
            keyring.set_password(
                self._service_name,
                self._get_username(key),
                value
            )
            logger.debug(f"Stored '{key}' in system keyring")
            return True
        except Exception as e:
            logger.error(f"Failed to store '{key}' in keyring: {e}")
            return False

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve a credential from the system keyring."""
        if not self.is_available():
            return None

        try:
            value = keyring.get_password(
                self._service_name,
                self._get_username(key)
            )
            return value
        except Exception as e:
            logger.error(f"Failed to retrieve '{key}' from keyring: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a credential from the system keyring."""
        if not self.is_available():
            return False

        try:
            keyring.delete_password(
                self._service_name,
                self._get_username(key)
            )
            logger.debug(f"Deleted '{key}' from system keyring")
            return True
        except PasswordDeleteError:
            # Key didn't exist, consider this success
            return True
        except Exception as e:
            logger.error(f"Failed to delete '{key}' from keyring: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all stored credentials."""
        keys_to_clear = [
            KEY_ACCESS_TOKEN,
            KEY_REFRESH_TOKEN,
            KEY_TOKEN_EXPIRY,
            KEY_USER_ID,
            KEY_USER_EMAIL,
            KEY_ENCRYPTION_KEY,
        ]

        success = True
        for key in keys_to_clear:
            if not self.delete(key):
                success = False

        return success


# =============================================================================
# Encrypted File Backend
# =============================================================================

class EncryptedFileBackend(CredentialBackend):
    """
    Encrypted file backend as fallback when keyring is unavailable.

    Uses AES-256 encryption via Fernet (if cryptography is available)
    or falls back to basic obfuscation.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self._file_path = file_path or get_credentials_path()
        self._data: Dict[str, str] = {}
        self._loaded = False
        self._lock = threading.RLock()
        self._encryption_key: Optional[bytes] = None

    def _get_machine_key(self) -> bytes:
        """
        Generate a machine-specific key for encryption.

        This provides basic protection but is not as secure as a user password.
        """
        # Combine various machine identifiers
        identifiers = [
            os.environ.get("COMPUTERNAME", ""),
            os.environ.get("USERNAME", ""),
            os.environ.get("USERDOMAIN", ""),
            str(Path.home()),
        ]

        combined = "|".join(identifiers).encode('utf-8')
        return hashlib.sha256(combined).digest()

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from machine key."""
        if CRYPTOGRAPHY_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=ENCRYPTION_KEY_SIZE,
                salt=salt,
                iterations=ENCRYPTION_ITERATIONS,
            )
            return base64.urlsafe_b64encode(kdf.derive(self._get_machine_key()))
        else:
            # Simple fallback using HMAC
            return base64.urlsafe_b64encode(
                hmac.new(self._get_machine_key(), salt, hashlib.sha256).digest()
            )

    def _get_fernet(self, salt: Optional[bytes] = None) -> Tuple[Any, bytes]:
        """Get Fernet instance for encryption/decryption."""
        if salt is None:
            salt = secrets.token_bytes(ENCRYPTION_SALT_SIZE)

        key = self._derive_key(salt)

        if CRYPTOGRAPHY_AVAILABLE:
            return Fernet(key), salt
        else:
            # Return a simple wrapper for non-cryptography fallback
            return _SimpleCipher(key), salt

    def is_available(self) -> bool:
        """File backend is always available."""
        return True

    def _load(self) -> None:
        """Load and decrypt data from file."""
        with self._lock:
            if self._loaded:
                return

            self._data = {}

            if not self._file_path.exists():
                self._loaded = True
                return

            try:
                with open(self._file_path, 'rb') as f:
                    encrypted_data = f.read()

                if len(encrypted_data) < ENCRYPTION_SALT_SIZE:
                    logger.warning("Credentials file too small, resetting")
                    self._loaded = True
                    return

                # Extract salt and ciphertext
                salt = encrypted_data[:ENCRYPTION_SALT_SIZE]
                ciphertext = encrypted_data[ENCRYPTION_SALT_SIZE:]

                # Decrypt
                fernet, _ = self._get_fernet(salt)

                if CRYPTOGRAPHY_AVAILABLE:
                    plaintext = fernet.decrypt(ciphertext)
                else:
                    plaintext = fernet.decrypt(ciphertext)

                self._data = json.loads(plaintext.decode('utf-8'))
                self._loaded = True
                logger.debug("Loaded credentials from encrypted file")

            except (InvalidToken, json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load credentials file: {e}")
                self._data = {}
                self._loaded = True

    def _save(self) -> bool:
        """Encrypt and save data to file."""
        with self._lock:
            try:
                # Ensure parent directory exists
                self._file_path.parent.mkdir(parents=True, exist_ok=True)

                # Serialize and encrypt
                plaintext = json.dumps(self._data).encode('utf-8')
                fernet, salt = self._get_fernet()

                if CRYPTOGRAPHY_AVAILABLE:
                    ciphertext = fernet.encrypt(plaintext)
                else:
                    ciphertext = fernet.encrypt(plaintext)

                # Write salt + ciphertext
                with open(self._file_path, 'wb') as f:
                    f.write(salt + ciphertext)

                # Set restrictive permissions on Unix
                if os.name == 'posix':
                    os.chmod(self._file_path, 0o600)

                logger.debug("Saved credentials to encrypted file")
                return True

            except Exception as e:
                logger.error(f"Failed to save credentials file: {e}")
                return False

    def store(self, key: str, value: str) -> bool:
        """Store an encrypted credential."""
        self._load()
        with self._lock:
            self._data[key] = value
            return self._save()

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve a decrypted credential."""
        self._load()
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Delete a credential."""
        self._load()
        with self._lock:
            if key in self._data:
                del self._data[key]
                return self._save()
            return True

    def clear_all(self) -> bool:
        """Clear all credentials and remove file."""
        with self._lock:
            self._data = {}
            self._loaded = True

            try:
                if self._file_path.exists():
                    self._file_path.unlink()
                return True
            except Exception as e:
                logger.error(f"Failed to delete credentials file: {e}")
                return False


class _SimpleCipher:
    """
    Simple cipher for when cryptography library is not available.

    WARNING: This is NOT cryptographically secure. It only provides
    basic obfuscation to prevent casual inspection.
    """

    def __init__(self, key: bytes):
        self._key = key

    def encrypt(self, data: bytes) -> bytes:
        """XOR-based obfuscation (NOT secure encryption)."""
        key_len = len(self._key)
        return bytes(d ^ self._key[i % key_len] for i, d in enumerate(data))

    def decrypt(self, data: bytes) -> bytes:
        """XOR decryption."""
        return self.encrypt(data)  # XOR is symmetric


# =============================================================================
# Keyring Manager
# =============================================================================

class KeyringManager:
    """
    Manages secure credential storage for the application.

    Features:
    - System keyring integration with encrypted file fallback
    - JWT token management
    - Token expiry tracking
    - Thread-safe operations
    """

    def __init__(
        self,
        service_name: str = KEYRING_SERVICE_NAME,
        fallback_path: Optional[Path] = None
    ):
        """
        Initialize the keyring manager.

        Args:
            service_name: Name for keyring service
            fallback_path: Path for fallback encrypted file
        """
        self._service_name = service_name
        self._lock = threading.RLock()

        # Initialize backends
        self._keyring_backend = KeyringBackend(service_name)
        self._file_backend = EncryptedFileBackend(fallback_path)

        # Determine active backend
        if self._keyring_backend.is_available():
            self._backend = self._keyring_backend
            logger.info("Using system keyring for credential storage")
        else:
            self._backend = self._file_backend
            logger.info("Using encrypted file for credential storage (keyring unavailable)")

        # Cache for token info
        self._token_cache: Optional[TokenInfo] = None
        self._cache_valid = False

    @property
    def is_using_keyring(self) -> bool:
        """Check if using system keyring (vs file fallback)."""
        return isinstance(self._backend, KeyringBackend)

    @property
    def backend_name(self) -> str:
        """Get the name of the active backend."""
        return "system_keyring" if self.is_using_keyring else "encrypted_file"

    # =========================================================================
    # Token Storage
    # =========================================================================

    def store_tokens(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """
        Store authentication tokens securely.

        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token (optional)
            expires_in: Token lifetime in seconds (optional)
            user_id: User identifier (optional)
            user_email: User email (optional)

        Returns:
            True if successful
        """
        with self._lock:
            success = True

            # Store access token
            if not self._backend.store(KEY_ACCESS_TOKEN, access_token):
                success = False

            # Store refresh token
            if refresh_token:
                if not self._backend.store(KEY_REFRESH_TOKEN, refresh_token):
                    success = False

            # Store expiry time
            if expires_in:
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                if not self._backend.store(KEY_TOKEN_EXPIRY, expires_at.isoformat()):
                    success = False

            # Store user info
            if user_id:
                if not self._backend.store(KEY_USER_ID, user_id):
                    success = False

            if user_email:
                if not self._backend.store(KEY_USER_EMAIL, user_email):
                    success = False

            # Invalidate cache
            self._cache_valid = False

            if success:
                logger.info("Tokens stored successfully")
            else:
                logger.warning("Some tokens failed to store")

            return success

    def get_tokens(self) -> TokenInfo:
        """
        Retrieve stored tokens.

        Returns:
            TokenInfo with stored credentials
        """
        with self._lock:
            # Return cached if valid
            if self._cache_valid and self._token_cache is not None:
                return self._token_cache

            # Retrieve from backend
            access_token = self._backend.retrieve(KEY_ACCESS_TOKEN)
            refresh_token = self._backend.retrieve(KEY_REFRESH_TOKEN)
            expiry_str = self._backend.retrieve(KEY_TOKEN_EXPIRY)
            user_id = self._backend.retrieve(KEY_USER_ID)
            user_email = self._backend.retrieve(KEY_USER_EMAIL)

            # Parse expiry
            expires_at = None
            if expiry_str:
                try:
                    expires_at = datetime.fromisoformat(expiry_str)
                except ValueError:
                    pass

            # Create token info
            self._token_cache = TokenInfo(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                user_id=user_id,
                user_email=user_email,
            )
            self._cache_valid = True

            return self._token_cache

    def get_access_token(self) -> Optional[str]:
        """Get the access token."""
        return self.get_tokens().access_token

    def get_refresh_token(self) -> Optional[str]:
        """Get the refresh token."""
        return self.get_tokens().refresh_token

    def get_authorization_header(self) -> Optional[str]:
        """Get the Authorization header value."""
        tokens = self.get_tokens()
        if tokens.access_token:
            return f"{tokens.token_type} {tokens.access_token}"
        return None

    def is_authenticated(self) -> bool:
        """Check if user has valid stored credentials."""
        tokens = self.get_tokens()
        return tokens.is_valid

    def needs_refresh(self) -> bool:
        """Check if the access token needs refreshing."""
        tokens = self.get_tokens()
        return tokens.is_expired and bool(tokens.refresh_token)

    def update_access_token(
        self,
        access_token: str,
        expires_in: Optional[int] = None
    ) -> bool:
        """
        Update just the access token (e.g., after refresh).

        Args:
            access_token: New access token
            expires_in: New expiry time in seconds

        Returns:
            True if successful
        """
        with self._lock:
            success = self._backend.store(KEY_ACCESS_TOKEN, access_token)

            if expires_in:
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                self._backend.store(KEY_TOKEN_EXPIRY, expires_at.isoformat())

            self._cache_valid = False
            return success

    def clear_tokens(self) -> bool:
        """
        Clear all stored tokens (logout).

        Returns:
            True if successful
        """
        with self._lock:
            success = True

            for key in [KEY_ACCESS_TOKEN, KEY_REFRESH_TOKEN, KEY_TOKEN_EXPIRY,
                        KEY_USER_ID, KEY_USER_EMAIL]:
                if not self._backend.delete(key):
                    success = False

            self._token_cache = None
            self._cache_valid = False

            logger.info("Tokens cleared")
            return success

    # =========================================================================
    # Generic Credential Storage
    # =========================================================================

    def store_credential(self, key: str, value: str) -> bool:
        """
        Store an arbitrary credential.

        Args:
            key: Credential key
            value: Credential value

        Returns:
            True if successful
        """
        return self._backend.store(key, value)

    def get_credential(self, key: str) -> Optional[str]:
        """
        Retrieve an arbitrary credential.

        Args:
            key: Credential key

        Returns:
            Credential value or None
        """
        return self._backend.retrieve(key)

    def delete_credential(self, key: str) -> bool:
        """
        Delete an arbitrary credential.

        Args:
            key: Credential key

        Returns:
            True if successful
        """
        return self._backend.delete(key)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def clear_all(self) -> bool:
        """Clear all stored credentials."""
        with self._lock:
            success = self._backend.clear_all()
            self._token_cache = None
            self._cache_valid = False
            logger.info("All credentials cleared")
            return success

    def migrate_to_keyring(self) -> bool:
        """
        Attempt to migrate credentials from file to keyring.

        Useful if keyring becomes available after initial setup.

        Returns:
            True if migration successful or not needed
        """
        if not self._keyring_backend.is_available():
            logger.info("Keyring not available, cannot migrate")
            return False

        if self.is_using_keyring:
            logger.info("Already using keyring, no migration needed")
            return True

        with self._lock:
            try:
                # Get all credentials from file backend
                tokens = self.get_tokens()

                if not tokens.access_token:
                    logger.info("No credentials to migrate")
                    return True

                # Switch to keyring backend
                old_backend = self._backend
                self._backend = self._keyring_backend

                # Store tokens in keyring
                success = self.store_tokens(
                    access_token=tokens.access_token or "",
                    refresh_token=tokens.refresh_token,
                    user_id=tokens.user_id,
                    user_email=tokens.user_email,
                )

                if success:
                    # Clear file backend
                    old_backend.clear_all()
                    logger.info("Successfully migrated credentials to keyring")
                    return True
                else:
                    # Rollback
                    self._backend = old_backend
                    logger.warning("Failed to migrate credentials")
                    return False

            except Exception as e:
                logger.error(f"Error during migration: {e}")
                return False

    def export_for_backup(self) -> Optional[Dict[str, Any]]:
        """
        Export tokens for backup purposes.

        WARNING: Returns sensitive data. Handle with care.

        Returns:
            Dictionary with token info, or None if not authenticated
        """
        tokens = self.get_tokens()
        if not tokens.access_token:
            return None

        return tokens.to_dict()

    def import_from_backup(self, data: Dict[str, Any]) -> bool:
        """
        Import tokens from backup.

        Args:
            data: Dictionary from export_for_backup()

        Returns:
            True if successful
        """
        try:
            token_info = TokenInfo.from_dict(data)

            if not token_info.access_token:
                logger.warning("No access token in backup data")
                return False

            return self.store_tokens(
                access_token=token_info.access_token,
                refresh_token=token_info.refresh_token,
                user_id=token_info.user_id,
                user_email=token_info.user_email,
            )

        except Exception as e:
            logger.error(f"Error importing backup: {e}")
            return False


# =============================================================================
# Global Instance
# =============================================================================

_keyring_manager: Optional[KeyringManager] = None


def get_keyring_manager() -> KeyringManager:
    """Get the global keyring manager instance."""
    global _keyring_manager
    if _keyring_manager is None:
        _keyring_manager = KeyringManager()
    return _keyring_manager


def get_access_token() -> Optional[str]:
    """Convenience function to get the access token."""
    return get_keyring_manager().get_access_token()


def get_refresh_token() -> Optional[str]:
    """Convenience function to get the refresh token."""
    return get_keyring_manager().get_refresh_token()


def is_authenticated() -> bool:
    """Convenience function to check authentication status."""
    return get_keyring_manager().is_authenticated()


def store_tokens(
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in: Optional[int] = None
) -> bool:
    """Convenience function to store tokens."""
    return get_keyring_manager().store_tokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def clear_tokens() -> bool:
    """Convenience function to clear tokens."""
    return get_keyring_manager().clear_tokens()


__all__ = [
    # Data classes
    "TokenInfo",

    # Backends
    "CredentialBackend",
    "KeyringBackend",
    "EncryptedFileBackend",

    # Manager
    "KeyringManager",
    "get_keyring_manager",

    # Convenience functions
    "get_access_token",
    "get_refresh_token",
    "is_authenticated",
    "store_tokens",
    "clear_tokens",

    # Constants
    "KEY_ACCESS_TOKEN",
    "KEY_REFRESH_TOKEN",
    "KEY_TOKEN_EXPIRY",
    "KEY_USER_ID",
    "KEY_USER_EMAIL",
]
