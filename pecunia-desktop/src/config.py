"""
Configuration management for Pecunia Desktop.

Uses pydantic-settings for type-safe configuration with support for
.env files, environment variables, and secure token storage via keyring.
"""

import os
import logging
from pathlib import Path
from typing import Literal, Optional
from functools import lru_cache

from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None

from constants import (
    APP_NAME,
    APP_VERSION,
    APP_ORGANIZATION,
    DEFAULT_API_BASE_URL,
    API_TIMEOUT_SECONDS,
    KEYRING_SERVICE_NAME,
    KEYRING_ACCESS_TOKEN,
    KEYRING_REFRESH_TOKEN,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Platform-Specific Directory Functions
# =============================================================================

def get_config_dir() -> Path:
    """Get the platform-specific configuration directory."""
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif os.name == 'posix':
        if hasattr(os, 'uname') and 'darwin' in os.uname().sysname.lower():  # macOS
            base = Path.home() / 'Library' / 'Application Support'
        else:  # Linux
            base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    else:
        base = Path.home()

    config_dir = base / APP_ORGANIZATION / APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get the platform-specific data directory."""
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif os.name == 'posix':
        if hasattr(os, 'uname') and 'darwin' in os.uname().sysname.lower():  # macOS
            base = Path.home() / 'Library' / 'Application Support'
        else:  # Linux
            base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    else:
        base = Path.home()

    data_dir = base / APP_ORGANIZATION / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    """Get the platform-specific cache directory."""
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        cache_dir = base / APP_ORGANIZATION / APP_NAME / 'Cache'
    elif os.name == 'posix':
        if hasattr(os, 'uname') and 'darwin' in os.uname().sysname.lower():  # macOS
            base = Path.home() / 'Library' / 'Caches'
            cache_dir = base / f'{APP_ORGANIZATION}.{APP_NAME}'
        else:  # Linux
            base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
            cache_dir = base / APP_NAME.lower()
    else:
        cache_dir = Path.home() / '.cache' / APP_NAME.lower()

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_default_database_path() -> Path:
    """Get the default database path."""
    return get_data_dir() / 'pecunia.db'


# =============================================================================
# Secure Token Storage
# =============================================================================

class SecureTokenStorage:
    """
    Secure storage for API tokens using the system keyring.

    Falls back to in-memory storage if keyring is not available.
    """

    def __init__(self, service_name: str = KEYRING_SERVICE_NAME):
        self._service_name = service_name
        self._fallback_storage: dict[str, str] = {}

        if not KEYRING_AVAILABLE:
            logger.warning(
                "keyring package not available. Tokens will be stored in memory only. "
                "Install keyring for secure persistent token storage: pip install keyring"
            )

    def _get_username(self, key: str) -> str:
        """Generate a username for keyring storage."""
        return f"{APP_NAME}_{key}"

    def store_token(self, key: str, token: str) -> bool:
        """
        Store a token securely.

        Args:
            key: Token identifier (e.g., 'access_token', 'refresh_token')
            token: The token value to store

        Returns:
            True if storage was successful
        """
        try:
            if KEYRING_AVAILABLE and keyring is not None:
                keyring.set_password(
                    self._service_name,
                    self._get_username(key),
                    token
                )
                logger.debug(f"Token '{key}' stored in system keyring")
            else:
                self._fallback_storage[key] = token
                logger.debug(f"Token '{key}' stored in memory (keyring unavailable)")
            return True
        except Exception as e:
            logger.error(f"Failed to store token '{key}': {e}")
            # Fall back to memory storage
            self._fallback_storage[key] = token
            return True

    def get_token(self, key: str) -> Optional[str]:
        """
        Retrieve a token from secure storage.

        Args:
            key: Token identifier

        Returns:
            The token value, or None if not found
        """
        try:
            if KEYRING_AVAILABLE and keyring is not None:
                token = keyring.get_password(
                    self._service_name,
                    self._get_username(key)
                )
                if token:
                    return token
            # Check fallback storage
            return self._fallback_storage.get(key)
        except Exception as e:
            logger.error(f"Failed to retrieve token '{key}': {e}")
            return self._fallback_storage.get(key)

    def delete_token(self, key: str) -> bool:
        """
        Delete a token from secure storage.

        Args:
            key: Token identifier

        Returns:
            True if deletion was successful
        """
        try:
            if KEYRING_AVAILABLE and keyring is not None:
                keyring.delete_password(
                    self._service_name,
                    self._get_username(key)
                )
                logger.debug(f"Token '{key}' deleted from system keyring")
        except Exception as e:
            logger.debug(f"Could not delete token '{key}' from keyring: {e}")

        # Also clear from fallback storage
        self._fallback_storage.pop(key, None)
        return True

    def store_access_token(self, token: str) -> bool:
        """Store the access token."""
        return self.store_token(KEYRING_ACCESS_TOKEN, token)

    def store_refresh_token(self, token: str) -> bool:
        """Store the refresh token."""
        return self.store_token(KEYRING_REFRESH_TOKEN, token)

    def get_access_token(self) -> Optional[str]:
        """Retrieve the access token."""
        return self.get_token(KEYRING_ACCESS_TOKEN)

    def get_refresh_token(self) -> Optional[str]:
        """Retrieve the refresh token."""
        return self.get_token(KEYRING_REFRESH_TOKEN)

    def clear_tokens(self) -> bool:
        """Clear all stored tokens."""
        self.delete_token(KEYRING_ACCESS_TOKEN)
        self.delete_token(KEYRING_REFRESH_TOKEN)
        return True


# =============================================================================
# Pydantic Settings Models
# =============================================================================

class APISettings(BaseSettings):
    """API connection configuration."""

    model_config = SettingsConfigDict(
        env_prefix='PECUNIA_API_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    base_url: str = Field(
        default=DEFAULT_API_BASE_URL,
        description="Base URL for the API server"
    )
    timeout: int = Field(
        default=API_TIMEOUT_SECONDS,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    connect_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Connection timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=30.0,
        description="Delay between retries in seconds"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates"
    )

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base URL doesn't have trailing slash."""
        return v.rstrip('/')


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(
        env_prefix='PECUNIA_DB_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    path: Path = Field(
        default_factory=get_default_database_path,
        description="Path to the SQLite database file"
    )
    echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging"
    )
    pool_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Database connection pool size"
    )

    @field_validator('path', mode='before')
    @classmethod
    def resolve_path(cls, v):
        """Resolve and expand the database path."""
        if isinstance(v, str):
            v = Path(v)
        return v.expanduser().resolve()


class SyncSettings(BaseSettings):
    """Synchronization configuration."""

    model_config = SettingsConfigDict(
        env_prefix='PECUNIA_SYNC_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    enabled: bool = Field(
        default=True,
        description="Enable automatic synchronization"
    )
    interval_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,
        description="Sync interval in minutes"
    )
    on_startup: bool = Field(
        default=True,
        description="Sync on application startup"
    )
    on_network_change: bool = Field(
        default=True,
        description="Sync when network connectivity changes"
    )
    batch_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Number of records to sync per batch"
    )


class UISettings(BaseSettings):
    """User interface configuration."""

    model_config = SettingsConfigDict(
        env_prefix='PECUNIA_UI_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    theme: Literal['light', 'dark', 'system'] = Field(
        default='system',
        description="Application color theme"
    )
    accent_color: str = Field(
        default='#007AFF',
        description="Primary accent color (hex)"
    )
    language: str = Field(
        default='en',
        description="UI language code"
    )
    currency: str = Field(
        default='USD',
        description="Default currency code"
    )
    date_format: str = Field(
        default='%m/%d/%Y',
        description="Date display format"
    )
    time_format: str = Field(
        default='%I:%M %p',
        description="Time display format"
    )
    sidebar_collapsed: bool = Field(
        default=False,
        description="Whether sidebar is collapsed"
    )
    show_balance: bool = Field(
        default=True,
        description="Show account balances in UI"
    )
    animations_enabled: bool = Field(
        default=True,
        description="Enable UI animations"
    )

    # Window geometry (persisted separately)
    window_width: int = Field(default=1280, ge=800)
    window_height: int = Field(default=800, ge=600)
    window_x: Optional[int] = Field(default=None)
    window_y: Optional[int] = Field(default=None)
    window_maximized: bool = Field(default=False)

    @field_validator('accent_color')
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """Validate hex color format."""
        v = v.strip()
        if not v.startswith('#'):
            v = f'#{v}'
        if len(v) not in (4, 7):
            raise ValueError('Accent color must be a valid hex color (e.g., #007AFF)')
        return v


class NotificationSettings(BaseSettings):
    """Notification configuration."""

    model_config = SettingsConfigDict(
        env_prefix='PECUNIA_NOTIFY_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    enabled: bool = Field(
        default=True,
        description="Enable notifications"
    )
    budget_alerts: bool = Field(
        default=True,
        description="Show budget threshold alerts"
    )
    transaction_alerts: bool = Field(
        default=True,
        description="Show new transaction notifications"
    )
    sync_alerts: bool = Field(
        default=False,
        description="Show sync status notifications"
    )
    sound_enabled: bool = Field(
        default=True,
        description="Enable notification sounds"
    )
    budget_threshold_percent: int = Field(
        default=80,
        ge=1,
        le=100,
        description="Budget alert threshold percentage"
    )


class AppSettings(BaseSettings):
    """
    Main application configuration.

    Combines all configuration sections and provides centralized
    access to settings with environment variable and .env file support.
    """

    model_config = SettingsConfigDict(
        env_prefix='PECUNIA_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    # App metadata
    app_name: str = Field(default=APP_NAME)
    app_version: str = Field(default=APP_VERSION)
    app_organization: str = Field(default=APP_ORGANIZATION)

    # Update configuration
    update_url: str = Field(
        default='https://api.pecunia.com/updates',
        description="URL for checking application updates"
    )
    check_updates_on_startup: bool = Field(
        default=True,
        description="Check for updates when app starts"
    )
    auto_install_updates: bool = Field(
        default=False,
        description="Automatically install updates"
    )

    # Debug and logging
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = Field(
        default='INFO',
        description="Logging level"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Path to log file (None for stdout only)"
    )

    # Feature flags
    enable_plaid_integration: bool = Field(
        default=True,
        description="Enable Plaid bank integration"
    )
    enable_export: bool = Field(
        default=True,
        description="Enable data export features"
    )

    # Nested settings
    api: APISettings = Field(default_factory=APISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    sync: SyncSettings = Field(default_factory=SyncSettings)
    ui: UISettings = Field(default_factory=UISettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)

    # Runtime state (not persisted)
    first_run: bool = Field(default=True, exclude=True)

    @field_validator('log_file', mode='before')
    @classmethod
    def resolve_log_path(cls, v):
        """Resolve log file path."""
        if v is None:
            return None
        if isinstance(v, str):
            v = Path(v)
        return v.expanduser().resolve()


# =============================================================================
# Configuration Manager
# =============================================================================

class ConfigManager:
    """
    Manages application configuration with persistence.

    Provides a unified interface for accessing and modifying settings,
    with automatic persistence to JSON and secure token storage.
    """

    CONFIG_FILENAME = 'config.json'

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Optional custom configuration directory.
        """
        self._config_dir = config_dir or get_config_dir()
        self._config_path = self._config_dir / self.CONFIG_FILENAME
        self._settings: Optional[AppSettings] = None
        self._token_storage = SecureTokenStorage()
        self._loaded = False

    @property
    def settings(self) -> AppSettings:
        """Get the current settings."""
        if self._settings is None:
            self.load()
        return self._settings  # type: ignore

    @property
    def api(self) -> APISettings:
        """Get API settings."""
        return self.settings.api

    @property
    def database(self) -> DatabaseSettings:
        """Get database settings."""
        return self.settings.database

    @property
    def sync(self) -> SyncSettings:
        """Get sync settings."""
        return self.settings.sync

    @property
    def ui(self) -> UISettings:
        """Get UI settings."""
        return self.settings.ui

    @property
    def notifications(self) -> NotificationSettings:
        """Get notification settings."""
        return self.settings.notifications

    @property
    def tokens(self) -> SecureTokenStorage:
        """Get the token storage interface."""
        return self._token_storage

    def load(self) -> AppSettings:
        """
        Load configuration from file and environment.

        Environment variables take precedence over file settings.

        Returns:
            The loaded settings.
        """
        import json

        try:
            if self._config_path.exists():
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)

                # Create settings with file data as defaults, env vars override
                self._settings = AppSettings(
                    api=APISettings(**file_data.get('api', {})),
                    database=DatabaseSettings(**file_data.get('database', {})),
                    sync=SyncSettings(**file_data.get('sync', {})),
                    ui=UISettings(**file_data.get('ui', {})),
                    notifications=NotificationSettings(**file_data.get('notifications', {})),
                    **{k: v for k, v in file_data.items()
                       if k not in ('api', 'database', 'sync', 'ui', 'notifications')}
                )
                logger.info(f"Configuration loaded from {self._config_path}")
            else:
                # Create with defaults and env vars
                self._settings = AppSettings()
                logger.info("Using default configuration with environment overrides")

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._settings = AppSettings()

        self._loaded = True
        return self._settings

    def save(self) -> bool:
        """
        Save current configuration to file.

        Returns:
            True if save was successful.
        """
        import json

        if self._settings is None:
            return False

        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)

            # Convert to dict, excluding sensitive and transient fields
            data = self._settings.model_dump(
                exclude={'first_run'},
                exclude_none=True,
            )

            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Configuration saved to {self._config_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def reset(self) -> AppSettings:
        """
        Reset configuration to defaults.

        Returns:
            The default settings.
        """
        self._settings = AppSettings()
        self._loaded = True
        return self._settings

    def update_window_geometry(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        maximized: bool
    ) -> None:
        """Update window geometry in settings."""
        self.settings.ui.window_x = x
        self.settings.ui.window_y = y
        self.settings.ui.window_width = width
        self.settings.ui.window_height = height
        self.settings.ui.window_maximized = maximized

    def set_theme(self, theme: Literal['light', 'dark', 'system']) -> None:
        """Set the UI theme."""
        self.settings.ui.theme = theme

    def set_sync_interval(self, minutes: int) -> None:
        """Set the sync interval in minutes."""
        if 1 <= minutes <= 1440:
            self.settings.sync.interval_minutes = minutes


# =============================================================================
# Global Instance Access
# =============================================================================

_config_manager: Optional[ConfigManager] = None
_token_storage: Optional[SecureTokenStorage] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_settings() -> AppSettings:
    """Get the current application settings."""
    return get_config_manager().settings


def get_token_storage() -> SecureTokenStorage:
    """Get the global token storage instance."""
    global _token_storage
    if _token_storage is None:
        _token_storage = SecureTokenStorage()
    return _token_storage


@lru_cache()
def get_cached_settings() -> AppSettings:
    """
    Get cached settings for performance-critical code.

    Note: Changes to settings won't be reflected until cache is cleared.
    Call get_cached_settings.cache_clear() after modifying settings.
    """
    return get_settings()


# Backward compatibility alias
def get_config() -> AppSettings:
    """Get the current application configuration (alias for get_settings)."""
    return get_settings()
