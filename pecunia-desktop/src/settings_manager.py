"""
Settings Manager for Pecunia Desktop.

Provides a robust settings management system with:
- JSON file persistence with atomic writes
- Default values and validation
- Settings migration between versions
- Thread-safe operations
- Change notification callbacks
"""

import json
import logging
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from copy import deepcopy

from config import get_config_dir, get_data_dir

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# Enums and Constants
# =============================================================================

class Theme(str, Enum):
    """Application theme options."""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class Language(str, Enum):
    """Supported languages."""
    ENGLISH = "en"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"
    PORTUGUESE = "pt"
    ITALIAN = "it"


class SyncInterval(int, Enum):
    """Predefined sync intervals in minutes."""
    FIVE_MINUTES = 5
    FIFTEEN_MINUTES = 15
    THIRTY_MINUTES = 30
    ONE_HOUR = 60
    SIX_HOURS = 360
    DAILY = 1440


# Current settings version for migrations
SETTINGS_VERSION = 2


# =============================================================================
# Default Settings
# =============================================================================

@dataclass
class APISettings:
    """API connection settings."""
    api_url: str = "https://localhost:8000/api/v1"
    timeout_seconds: int = 30
    max_retries: int = 3
    verify_ssl: bool = True


@dataclass
class SyncSettings:
    """Synchronization settings."""
    sync_interval: int = 15  # minutes
    auto_sync: bool = True
    sync_on_startup: bool = True
    offline_mode: bool = False
    last_sync_timestamp: Optional[str] = None
    pending_changes_count: int = 0


@dataclass
class UISettings:
    """User interface settings."""
    theme: str = "system"
    language: str = "en"
    currency: str = "USD"
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M"
    sidebar_collapsed: bool = False
    show_balance: bool = True
    animations_enabled: bool = True
    compact_mode: bool = False


@dataclass
class NotificationSettings:
    """Notification preferences."""
    notifications_enabled: bool = True
    budget_alerts: bool = True
    transaction_alerts: bool = True
    sync_alerts: bool = False
    sound_enabled: bool = True
    budget_threshold_percent: int = 80


@dataclass
class WindowGeometry:
    """Window position and size."""
    width: int = 1280
    height: int = 800
    x: Optional[int] = None
    y: Optional[int] = None
    maximized: bool = False


@dataclass
class PrivacySettings:
    """Privacy and security settings."""
    remember_login: bool = True
    lock_on_minimize: bool = False
    lock_timeout_minutes: int = 5
    hide_amounts_in_notifications: bool = False
    analytics_enabled: bool = True
    crash_reports_enabled: bool = True


@dataclass
class ExportSettings:
    """Export preferences."""
    default_format: str = "csv"
    include_headers: bool = True
    date_range_months: int = 12
    export_directory: Optional[str] = None


@dataclass
class AppSettings:
    """Complete application settings."""
    # Settings metadata
    version: int = SETTINGS_VERSION
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Setting sections
    api: APISettings = field(default_factory=APISettings)
    sync: SyncSettings = field(default_factory=SyncSettings)
    ui: UISettings = field(default_factory=UISettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    window: WindowGeometry = field(default_factory=WindowGeometry)
    privacy: PrivacySettings = field(default_factory=PrivacySettings)
    export: ExportSettings = field(default_factory=ExportSettings)

    # First run flag
    first_run: bool = True
    onboarding_completed: bool = False


def get_default_settings() -> AppSettings:
    """Create a new AppSettings instance with all defaults."""
    return AppSettings()


# =============================================================================
# Settings Validation
# =============================================================================

class ValidationError(Exception):
    """Raised when settings validation fails."""

    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Validation error for '{field}': {message}")


class SettingsValidator:
    """Validates settings values."""

    # Validation rules
    VALID_THEMES = {"light", "dark", "system"}
    VALID_LANGUAGES = {"en", "fr", "es", "de", "pt", "it"}
    VALID_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "CNY", "INR", "BRL"}
    VALID_DATE_FORMATS = {"%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%d-%m-%Y"}
    VALID_TIME_FORMATS = {"%H:%M", "%I:%M %p", "%H:%M:%S"}
    VALID_EXPORT_FORMATS = {"csv", "json", "xlsx", "pdf"}

    MIN_SYNC_INTERVAL = 1  # minutes
    MAX_SYNC_INTERVAL = 1440  # 24 hours
    MIN_TIMEOUT = 5
    MAX_TIMEOUT = 300
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600

    @classmethod
    def validate_all(cls, settings: AppSettings) -> List[ValidationError]:
        """
        Validate all settings and return list of errors.

        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []

        # API settings
        if not settings.api.api_url:
            errors.append(ValidationError("api.api_url", "API URL cannot be empty"))
        elif not settings.api.api_url.startswith(("http://", "https://")):
            errors.append(ValidationError(
                "api.api_url",
                "API URL must start with http:// or https://",
                settings.api.api_url
            ))

        if not cls.MIN_TIMEOUT <= settings.api.timeout_seconds <= cls.MAX_TIMEOUT:
            errors.append(ValidationError(
                "api.timeout_seconds",
                f"Timeout must be between {cls.MIN_TIMEOUT} and {cls.MAX_TIMEOUT}",
                settings.api.timeout_seconds
            ))

        # Sync settings
        if not cls.MIN_SYNC_INTERVAL <= settings.sync.sync_interval <= cls.MAX_SYNC_INTERVAL:
            errors.append(ValidationError(
                "sync.sync_interval",
                f"Sync interval must be between {cls.MIN_SYNC_INTERVAL} and {cls.MAX_SYNC_INTERVAL} minutes",
                settings.sync.sync_interval
            ))

        # UI settings
        if settings.ui.theme not in cls.VALID_THEMES:
            errors.append(ValidationError(
                "ui.theme",
                f"Theme must be one of: {', '.join(cls.VALID_THEMES)}",
                settings.ui.theme
            ))

        if settings.ui.language not in cls.VALID_LANGUAGES:
            errors.append(ValidationError(
                "ui.language",
                f"Language must be one of: {', '.join(cls.VALID_LANGUAGES)}",
                settings.ui.language
            ))

        if settings.ui.currency not in cls.VALID_CURRENCIES:
            errors.append(ValidationError(
                "ui.currency",
                f"Currency must be one of: {', '.join(cls.VALID_CURRENCIES)}",
                settings.ui.currency
            ))

        if settings.ui.date_format not in cls.VALID_DATE_FORMATS:
            errors.append(ValidationError(
                "ui.date_format",
                f"Date format must be one of: {', '.join(cls.VALID_DATE_FORMATS)}",
                settings.ui.date_format
            ))

        # Window geometry
        if settings.window.width < cls.MIN_WINDOW_WIDTH:
            errors.append(ValidationError(
                "window.width",
                f"Window width must be at least {cls.MIN_WINDOW_WIDTH}",
                settings.window.width
            ))

        if settings.window.height < cls.MIN_WINDOW_HEIGHT:
            errors.append(ValidationError(
                "window.height",
                f"Window height must be at least {cls.MIN_WINDOW_HEIGHT}",
                settings.window.height
            ))

        # Notification settings
        if not 0 <= settings.notifications.budget_threshold_percent <= 100:
            errors.append(ValidationError(
                "notifications.budget_threshold_percent",
                "Budget threshold must be between 0 and 100",
                settings.notifications.budget_threshold_percent
            ))

        # Export settings
        if settings.export.default_format not in cls.VALID_EXPORT_FORMATS:
            errors.append(ValidationError(
                "export.default_format",
                f"Export format must be one of: {', '.join(cls.VALID_EXPORT_FORMATS)}",
                settings.export.default_format
            ))

        return errors

    @classmethod
    def validate_value(cls, key: str, value: Any) -> Optional[ValidationError]:
        """
        Validate a single setting value.

        Args:
            key: Setting key in dot notation (e.g., "ui.theme")
            value: Value to validate

        Returns:
            ValidationError if invalid, None if valid
        """
        validators = {
            "ui.theme": lambda v: v in cls.VALID_THEMES,
            "ui.language": lambda v: v in cls.VALID_LANGUAGES,
            "ui.currency": lambda v: v in cls.VALID_CURRENCIES,
            "ui.date_format": lambda v: v in cls.VALID_DATE_FORMATS,
            "ui.time_format": lambda v: v in cls.VALID_TIME_FORMATS,
            "api.timeout_seconds": lambda v: cls.MIN_TIMEOUT <= v <= cls.MAX_TIMEOUT,
            "api.api_url": lambda v: v and v.startswith(("http://", "https://")),
            "sync.sync_interval": lambda v: cls.MIN_SYNC_INTERVAL <= v <= cls.MAX_SYNC_INTERVAL,
            "window.width": lambda v: v >= cls.MIN_WINDOW_WIDTH,
            "window.height": lambda v: v >= cls.MIN_WINDOW_HEIGHT,
            "notifications.budget_threshold_percent": lambda v: 0 <= v <= 100,
            "export.default_format": lambda v: v in cls.VALID_EXPORT_FORMATS,
        }

        if key in validators:
            if not validators[key](value):
                return ValidationError(key, f"Invalid value: {value}", value)

        return None


# =============================================================================
# Settings Migration
# =============================================================================

class SettingsMigrator:
    """
    Handles migration of settings between versions.

    Each migration function transforms settings from version N to N+1.
    """

    @staticmethod
    def migrate(data: Dict[str, Any], from_version: int) -> Dict[str, Any]:
        """
        Migrate settings from a given version to current.

        Args:
            data: Settings dictionary
            from_version: Source version number

        Returns:
            Migrated settings dictionary
        """
        migrations = {
            1: SettingsMigrator._migrate_v1_to_v2,
            # Add more migrations as needed
        }

        current_version = from_version

        while current_version < SETTINGS_VERSION:
            if current_version in migrations:
                logger.info(f"Migrating settings from v{current_version} to v{current_version + 1}")
                data = migrations[current_version](data)
            current_version += 1

        data["version"] = SETTINGS_VERSION
        return data

    @staticmethod
    def _migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate from v1 to v2.

        Changes in v2:
        - Added privacy section
        - Added export section
        - Renamed some fields
        """
        # Ensure new sections exist with defaults
        if "privacy" not in data:
            data["privacy"] = asdict(PrivacySettings())

        if "export" not in data:
            data["export"] = asdict(ExportSettings())

        # Move deprecated fields if they exist
        if "ui" in data:
            # Move 'remember_me' to privacy section if it exists
            if "remember_me" in data["ui"]:
                data["privacy"]["remember_login"] = data["ui"].pop("remember_me")

        # Ensure notifications has new fields
        if "notifications" in data:
            if "budget_threshold_percent" not in data["notifications"]:
                data["notifications"]["budget_threshold_percent"] = 80

        return data


# =============================================================================
# Settings Manager
# =============================================================================

class SettingsManager:
    """
    Manages application settings with persistence.

    Features:
    - JSON file storage with atomic writes
    - Automatic backups before saves
    - Settings validation
    - Migration support
    - Thread-safe operations
    - Change notification callbacks
    """

    SETTINGS_FILENAME = "settings.json"
    BACKUP_SUFFIX = ".backup"
    MAX_BACKUPS = 5

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        auto_save: bool = True,
        validate_on_load: bool = True
    ):
        """
        Initialize the settings manager.

        Args:
            config_dir: Directory for settings file (uses default if None)
            auto_save: Automatically save after changes
            validate_on_load: Validate settings when loading
        """
        self._config_dir = Path(config_dir) if config_dir else get_config_dir()
        self._settings_path = self._config_dir / self.SETTINGS_FILENAME
        self._auto_save = auto_save
        self._validate_on_load = validate_on_load

        self._settings: Optional[AppSettings] = None
        self._lock = threading.RLock()
        self._change_callbacks: List[Callable[[str, Any, Any], None]] = []
        self._loaded = False

        # Ensure directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)

    @property
    def settings(self) -> AppSettings:
        """Get current settings, loading if necessary."""
        if not self._loaded:
            self.load()
        return self._settings  # type: ignore

    @property
    def settings_path(self) -> Path:
        """Get the settings file path."""
        return self._settings_path

    def load(self) -> AppSettings:
        """
        Load settings from file.

        If file doesn't exist or is invalid, uses defaults.
        Performs migration if settings version is older.

        Returns:
            Loaded or default settings
        """
        with self._lock:
            try:
                if self._settings_path.exists():
                    with open(self._settings_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Check version and migrate if needed
                    file_version = data.get("version", 1)
                    if file_version < SETTINGS_VERSION:
                        logger.info(f"Settings file is version {file_version}, migrating to {SETTINGS_VERSION}")
                        data = SettingsMigrator.migrate(data, file_version)
                        # Save migrated settings
                        self._save_dict(data)

                    # Convert to AppSettings
                    self._settings = self._dict_to_settings(data)
                    logger.info(f"Settings loaded from {self._settings_path}")
                else:
                    logger.info("No settings file found, using defaults")
                    self._settings = get_default_settings()

                # Validate if enabled
                if self._validate_on_load:
                    errors = SettingsValidator.validate_all(self._settings)
                    if errors:
                        logger.warning(f"Settings validation found {len(errors)} issues:")
                        for error in errors:
                            logger.warning(f"  - {error.field}: {error.message}")

                self._loaded = True
                return self._settings

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in settings file: {e}")
                self._restore_from_backup()
                return self.load() if self._settings_path.exists() else self._use_defaults()
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
                return self._use_defaults()

    def _use_defaults(self) -> AppSettings:
        """Use default settings."""
        self._settings = get_default_settings()
        self._loaded = True
        return self._settings

    def save(self) -> bool:
        """
        Save settings to file atomically.

        Creates a backup of existing file before saving.
        Uses atomic write (write to temp, then rename).

        Returns:
            True if successful
        """
        with self._lock:
            if self._settings is None:
                return False

            try:
                # Update timestamp
                self._settings.updated_at = datetime.now().isoformat()

                # Create backup
                if self._settings_path.exists():
                    self._create_backup()

                # Convert to dict
                data = self._settings_to_dict(self._settings)

                return self._save_dict(data)

            except Exception as e:
                logger.error(f"Error saving settings: {e}")
                return False

    def _save_dict(self, data: Dict[str, Any]) -> bool:
        """Save dictionary to settings file atomically."""
        temp_path = self._settings_path.with_suffix('.tmp')

        try:
            # Write to temp file
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            # Atomic rename using os.replace (works cross-platform)
            import os as _os
            _os.replace(str(temp_path), str(self._settings_path))

            logger.info(f"Settings saved to {self._settings_path}")
            return True

        except Exception as e:
            logger.error(f"Error during atomic save: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            return False

    def _create_backup(self) -> None:
        """Create a backup of the current settings file."""
        try:
            backup_dir = self._config_dir / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"settings_{timestamp}.json"

            shutil.copy2(self._settings_path, backup_path)
            logger.debug(f"Created settings backup: {backup_path}")

            # Clean up old backups
            self._cleanup_old_backups(backup_dir)

        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")

    def _cleanup_old_backups(self, backup_dir: Path) -> None:
        """Remove old backup files, keeping only MAX_BACKUPS."""
        try:
            backups = sorted(backup_dir.glob("settings_*.json"), reverse=True)
            for old_backup in backups[self.MAX_BACKUPS:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Error cleaning up backups: {e}")

    def _restore_from_backup(self) -> bool:
        """Attempt to restore settings from the most recent backup."""
        try:
            backup_dir = self._config_dir / "backups"
            if not backup_dir.exists():
                return False

            backups = sorted(backup_dir.glob("settings_*.json"), reverse=True)
            if not backups:
                return False

            latest_backup = backups[0]
            shutil.copy2(latest_backup, self._settings_path)
            logger.info(f"Restored settings from backup: {latest_backup}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def _settings_to_dict(self, settings: AppSettings) -> Dict[str, Any]:
        """Convert AppSettings to dictionary."""
        return {
            "version": settings.version,
            "created_at": settings.created_at,
            "updated_at": settings.updated_at,
            "first_run": settings.first_run,
            "onboarding_completed": settings.onboarding_completed,
            "api": asdict(settings.api),
            "sync": asdict(settings.sync),
            "ui": asdict(settings.ui),
            "notifications": asdict(settings.notifications),
            "window": asdict(settings.window),
            "privacy": asdict(settings.privacy),
            "export": asdict(settings.export),
        }

    def _dict_to_settings(self, data: Dict[str, Any]) -> AppSettings:
        """Convert dictionary to AppSettings."""
        return AppSettings(
            version=data.get("version", SETTINGS_VERSION),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            first_run=data.get("first_run", True),
            onboarding_completed=data.get("onboarding_completed", False),
            api=APISettings(**data.get("api", {})),
            sync=SyncSettings(**data.get("sync", {})),
            ui=UISettings(**data.get("ui", {})),
            notifications=NotificationSettings(**data.get("notifications", {})),
            window=WindowGeometry(**data.get("window", {})),
            privacy=PrivacySettings(**data.get("privacy", {})),
            export=ExportSettings(**data.get("export", {})),
        )

    def get(self, key: str, default: T = None) -> Union[Any, T]:
        """
        Get a setting value by dot notation key.

        Args:
            key: Setting path (e.g., "ui.theme", "sync.sync_interval")
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        parts = key.split('.')
        obj: Any = self.settings

        try:
            for part in parts:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict):
                    obj = obj.get(part, default)
                else:
                    return default
            return obj
        except (AttributeError, KeyError):
            return default

    def set(self, key: str, value: Any, validate: bool = True) -> bool:
        """
        Set a setting value by dot notation key.

        Args:
            key: Setting path (e.g., "ui.theme", "sync.sync_interval")
            value: New value
            validate: Whether to validate the value

        Returns:
            True if successful
        """
        # Validate if requested
        if validate:
            error = SettingsValidator.validate_value(key, value)
            if error:
                logger.warning(f"Validation failed: {error.message}")
                return False

        parts = key.split('.')
        if len(parts) < 1:
            return False

        with self._lock:
            try:
                # Navigate to parent
                obj: Any = self.settings
                for part in parts[:-1]:
                    if hasattr(obj, part):
                        obj = getattr(obj, part)
                    else:
                        return False

                # Get old value for callback
                final_key = parts[-1]
                old_value = getattr(obj, final_key, None)

                # Set new value
                if hasattr(obj, final_key):
                    setattr(obj, final_key, value)
                else:
                    return False

                # Notify callbacks
                self._notify_change(key, old_value, value)

                # Auto-save if enabled
                if self._auto_save:
                    self.save()

                return True

            except Exception as e:
                logger.error(f"Error setting {key}: {e}")
                return False

    def reset(self, key: Optional[str] = None) -> bool:
        """
        Reset settings to defaults.

        Args:
            key: If provided, reset only this key. Otherwise reset all.

        Returns:
            True if successful
        """
        with self._lock:
            defaults = get_default_settings()

            if key is None:
                # Reset all
                self._settings = defaults
                logger.info("All settings reset to defaults")
            else:
                # Reset specific key
                default_value = self.get(key)
                # Get default value from fresh defaults
                parts = key.split('.')
                obj: Any = defaults
                try:
                    for part in parts:
                        obj = getattr(obj, part)
                    self.set(key, obj, validate=False)
                    logger.info(f"Setting '{key}' reset to default: {obj}")
                except AttributeError:
                    return False

            if self._auto_save:
                self.save()

            return True

    def register_callback(self, callback: Callable[[str, Any, Any], None]) -> None:
        """
        Register a callback for settings changes.

        Callback receives: (key, old_value, new_value)
        """
        self._change_callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Unregister a change callback."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def _notify_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all registered callbacks of a change."""
        for callback in self._change_callbacks:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Error in settings change callback: {e}")

    # ==========================================================================
    # Convenience Methods
    # ==========================================================================

    def get_theme(self) -> str:
        """Get current theme."""
        return self.settings.ui.theme

    def set_theme(self, theme: str) -> bool:
        """Set theme (light/dark/system)."""
        return self.set("ui.theme", theme)

    def get_language(self) -> str:
        """Get current language."""
        return self.settings.ui.language

    def set_language(self, language: str) -> bool:
        """Set language."""
        return self.set("ui.language", language)

    def get_sync_interval(self) -> int:
        """Get sync interval in minutes."""
        return self.settings.sync.sync_interval

    def set_sync_interval(self, minutes: int) -> bool:
        """Set sync interval."""
        return self.set("sync.sync_interval", minutes)

    def is_auto_sync_enabled(self) -> bool:
        """Check if auto-sync is enabled."""
        return self.settings.sync.auto_sync

    def set_auto_sync(self, enabled: bool) -> bool:
        """Enable or disable auto-sync."""
        return self.set("sync.auto_sync", enabled)

    def is_offline_mode(self) -> bool:
        """Check if offline mode is active."""
        return self.settings.sync.offline_mode

    def set_offline_mode(self, enabled: bool) -> bool:
        """Enable or disable offline mode."""
        return self.set("sync.offline_mode", enabled)

    def are_notifications_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.settings.notifications.notifications_enabled

    def set_notifications_enabled(self, enabled: bool) -> bool:
        """Enable or disable notifications."""
        return self.set("notifications.notifications_enabled", enabled)

    def update_window_geometry(
        self,
        width: int,
        height: int,
        x: Optional[int] = None,
        y: Optional[int] = None,
        maximized: bool = False
    ) -> None:
        """Update window geometry settings."""
        self.settings.window.width = max(width, SettingsValidator.MIN_WINDOW_WIDTH)
        self.settings.window.height = max(height, SettingsValidator.MIN_WINDOW_HEIGHT)
        self.settings.window.x = x
        self.settings.window.y = y
        self.settings.window.maximized = maximized

        if self._auto_save:
            self.save()

    def update_last_sync(self, timestamp: Optional[datetime] = None) -> None:
        """Update the last sync timestamp."""
        if timestamp is None:
            timestamp = datetime.now()
        self.settings.sync.last_sync_timestamp = timestamp.isoformat()

        if self._auto_save:
            self.save()

    def mark_onboarding_complete(self) -> None:
        """Mark onboarding as completed."""
        self.settings.first_run = False
        self.settings.onboarding_completed = True

        if self._auto_save:
            self.save()

    def export_settings(self) -> Dict[str, Any]:
        """Export settings as dictionary (for backup/transfer)."""
        return deepcopy(self._settings_to_dict(self.settings))

    def import_settings(self, data: Dict[str, Any], merge: bool = False) -> bool:
        """
        Import settings from dictionary.

        Args:
            data: Settings dictionary
            merge: If True, merge with existing. If False, replace.

        Returns:
            True if successful
        """
        try:
            with self._lock:
                if merge:
                    # Merge with existing settings
                    current = self._settings_to_dict(self.settings)
                    self._deep_merge(current, data)
                    data = current

                self._settings = self._dict_to_settings(data)

                if self._auto_save:
                    self.save()

                logger.info("Settings imported successfully")
                return True

        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge override into base dictionary."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


# =============================================================================
# Global Instance
# =============================================================================

_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def get_setting(key: str, default: Any = None) -> Any:
    """Convenience function to get a setting value."""
    return get_settings_manager().get(key, default)


def set_setting(key: str, value: Any) -> bool:
    """Convenience function to set a setting value."""
    return get_settings_manager().set(key, value)


__all__ = [
    # Enums
    "Theme",
    "Language",
    "SyncInterval",

    # Settings classes
    "APISettings",
    "SyncSettings",
    "UISettings",
    "NotificationSettings",
    "WindowGeometry",
    "PrivacySettings",
    "ExportSettings",
    "AppSettings",

    # Validation
    "ValidationError",
    "SettingsValidator",

    # Migration
    "SettingsMigrator",
    "SETTINGS_VERSION",

    # Manager
    "SettingsManager",
    "get_settings_manager",
    "get_setting",
    "set_setting",
    "get_default_settings",
]
