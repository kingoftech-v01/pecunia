"""Tests for src/config.py — Configuration management."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestGetConfigDir:
    """Tests for get_config_dir()."""

    def test_linux_config_dir_uses_xdg(self, tmp_path):
        with patch("config.os.name", "posix"), \
             patch("config.os.environ", {"XDG_CONFIG_HOME": str(tmp_path)}), \
             patch("config.os.uname") as mock_uname:
            mock_uname.return_value = MagicMock(sysname="Linux")
            from config import get_config_dir, APP_ORGANIZATION, APP_NAME
            result = get_config_dir()
            assert str(tmp_path) in str(result)

    def test_windows_config_dir_uses_appdata(self, tmp_path):
        with patch("config.os.name", "nt"), \
             patch("config.os.environ", {"APPDATA": str(tmp_path)}):
            from config import get_config_dir, APP_ORGANIZATION, APP_NAME
            result = get_config_dir()
            assert str(tmp_path) in str(result)

    def test_fallback_config_dir_uses_home(self):
        with patch("config.os.name", "other"):
            from config import get_config_dir
            result = get_config_dir()
            assert result.exists()


class TestGetDataDir:
    """Tests for get_data_dir()."""

    def test_linux_data_dir_uses_xdg(self, tmp_path):
        with patch("config.os.name", "posix"), \
             patch("config.os.environ", {"XDG_DATA_HOME": str(tmp_path)}), \
             patch("config.os.uname") as mock_uname:
            mock_uname.return_value = MagicMock(sysname="Linux")
            from config import get_data_dir
            result = get_data_dir()
            assert str(tmp_path) in str(result)

    def test_windows_data_dir_uses_localappdata(self, tmp_path):
        with patch("config.os.name", "nt"), \
             patch("config.os.environ", {"LOCALAPPDATA": str(tmp_path)}):
            from config import get_data_dir
            result = get_data_dir()
            assert str(tmp_path) in str(result)


class TestGetCacheDir:
    """Tests for get_cache_dir()."""

    def test_linux_cache_dir_uses_xdg(self, tmp_path):
        with patch("config.os.name", "posix"), \
             patch("config.os.environ", {"XDG_CACHE_HOME": str(tmp_path)}), \
             patch("config.os.uname") as mock_uname:
            mock_uname.return_value = MagicMock(sysname="Linux")
            from config import get_cache_dir
            result = get_cache_dir()
            assert str(tmp_path) in str(result)


class TestSecureTokenStorage:
    """Tests for SecureTokenStorage."""

    def test_store_token_fallback_when_keyring_unavailable(self):
        with patch("config.KEYRING_AVAILABLE", False):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            result = storage.store_token("test_key", "test_value")
            assert result is True
            assert storage.get_token("test_key") == "test_value"

    def test_get_token_returns_none_when_not_stored(self):
        with patch("config.KEYRING_AVAILABLE", False):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            assert storage.get_token("nonexistent") is None

    def test_delete_token_clears_fallback(self):
        with patch("config.KEYRING_AVAILABLE", False):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            storage.store_token("key1", "val1")
            storage.delete_token("key1")
            assert storage.get_token("key1") is None

    def test_store_access_token(self):
        with patch("config.KEYRING_AVAILABLE", False):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            assert storage.store_access_token("access123") is True
            assert storage.get_access_token() == "access123"

    def test_store_refresh_token(self):
        with patch("config.KEYRING_AVAILABLE", False):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            assert storage.store_refresh_token("refresh456") is True
            assert storage.get_refresh_token() == "refresh456"

    def test_clear_tokens(self):
        with patch("config.KEYRING_AVAILABLE", False):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            storage.store_access_token("a")
            storage.store_refresh_token("r")
            assert storage.clear_tokens() is True
            assert storage.get_access_token() is None
            assert storage.get_refresh_token() is None

    def test_store_token_with_keyring(self):
        mock_keyring = MagicMock()
        with patch("config.KEYRING_AVAILABLE", True), \
             patch("config.keyring", mock_keyring):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            result = storage.store_token("key", "value")
            assert result is True
            mock_keyring.set_password.assert_called_once()

    def test_get_token_with_keyring(self):
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "stored_val"
        with patch("config.KEYRING_AVAILABLE", True), \
             patch("config.keyring", mock_keyring):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            result = storage.get_token("key")
            assert result == "stored_val"

    def test_store_token_keyring_exception_falls_back(self):
        mock_keyring = MagicMock()
        mock_keyring.set_password.side_effect = Exception("keyring error")
        with patch("config.KEYRING_AVAILABLE", True), \
             patch("config.keyring", mock_keyring):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            result = storage.store_token("key", "value")
            assert result is True
            assert storage._fallback_storage["key"] == "value"

    def test_get_token_keyring_exception_returns_fallback(self):
        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = Exception("err")
        with patch("config.KEYRING_AVAILABLE", True), \
             patch("config.keyring", mock_keyring):
            from config import SecureTokenStorage
            storage = SecureTokenStorage()
            storage._fallback_storage["key"] = "fallback_val"
            assert storage.get_token("key") == "fallback_val"


class TestAPISettings:
    """Tests for APISettings model."""

    def test_default_values(self):
        from config import APISettings
        settings = APISettings()
        assert settings.timeout == 30
        assert settings.max_retries == 3
        assert settings.verify_ssl is True

    def test_base_url_strips_trailing_slash(self):
        from config import APISettings
        settings = APISettings(base_url="https://api.example.com/")
        assert not settings.base_url.endswith("/")


class TestUISettings:
    """Tests for UISettings model."""

    def test_default_theme(self):
        from config import UISettings
        settings = UISettings()
        assert settings.theme == "system"

    def test_valid_hex_color(self):
        from config import UISettings
        settings = UISettings(accent_color="#FF0000")
        assert settings.accent_color == "#FF0000"

    def test_hex_color_adds_hash(self):
        from config import UISettings
        settings = UISettings(accent_color="007AFF")
        assert settings.accent_color == "#007AFF"

    def test_invalid_hex_color_raises(self):
        from config import UISettings
        with pytest.raises(Exception):
            UISettings(accent_color="#ZZZZZZ")


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_load_creates_defaults_when_no_file(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        settings = mgr.load()
        assert settings is not None
        assert settings.app_name == "Pecunia Desktop"

    def test_save_and_load_round_trip(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        mgr.load()
        mgr.settings.ui.theme = "dark"
        mgr.save()

        mgr2 = ConfigManager(config_dir=tmp_path)
        settings = mgr2.load()
        assert settings.ui.theme == "dark"

    def test_save_returns_false_when_no_settings(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        assert mgr.save() is False

    def test_reset_returns_defaults(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        mgr.load()
        mgr.settings.ui.theme = "dark"
        mgr.reset()
        assert mgr.settings.ui.theme == "system"

    def test_update_window_geometry(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        mgr.load()
        mgr.update_window_geometry(100, 200, 1000, 700, True)
        assert mgr.settings.ui.window_x == 100
        assert mgr.settings.ui.window_y == 200
        assert mgr.settings.ui.window_width == 1000
        assert mgr.settings.ui.window_height == 700
        assert mgr.settings.ui.window_maximized is True

    def test_set_theme(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        mgr.load()
        mgr.set_theme("dark")
        assert mgr.settings.ui.theme == "dark"

    def test_set_sync_interval_valid(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        mgr.load()
        mgr.set_sync_interval(30)
        assert mgr.settings.sync.interval_minutes == 30

    def test_set_sync_interval_out_of_range_ignored(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        mgr.load()
        original = mgr.settings.sync.interval_minutes
        mgr.set_sync_interval(9999)
        assert mgr.settings.sync.interval_minutes == original

    def test_properties_trigger_load(self, tmp_path):
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        assert mgr.api is not None
        assert mgr.database is not None
        assert mgr.sync is not None
        assert mgr.ui is not None
        assert mgr.notifications is not None
        assert mgr.tokens is not None

    def test_load_handles_corrupt_json(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json {{{")
        from config import ConfigManager
        mgr = ConfigManager(config_dir=tmp_path)
        settings = mgr.load()
        assert settings is not None
        assert settings.app_name == "Pecunia Desktop"


class TestGlobalAccessors:
    """Tests for module-level singleton accessors."""

    def test_get_config_manager_returns_instance(self):
        import config
        config._config_manager = None
        mgr = config.get_config_manager()
        assert mgr is not None
        config._config_manager = None

    def test_get_settings_returns_settings(self):
        import config
        config._config_manager = None
        settings = config.get_settings()
        assert settings is not None
        config._config_manager = None

    def test_get_token_storage_returns_instance(self):
        import config
        config._token_storage = None
        storage = config.get_token_storage()
        assert storage is not None
        config._token_storage = None

    def test_get_cached_settings_caches(self):
        import config
        config._config_manager = None
        config.get_cached_settings.cache_clear()
        s1 = config.get_cached_settings()
        s2 = config.get_cached_settings()
        assert s1 is s2
        config.get_cached_settings.cache_clear()
        config._config_manager = None

    def test_get_config_alias(self):
        import config
        config._config_manager = None
        result = config.get_config()
        assert result is not None
        config._config_manager = None
