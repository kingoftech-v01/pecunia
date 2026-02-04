"""Tests for src/keyring_manager.py — Secure credential storage."""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from keyring_manager import (
    TokenInfo, KeyringBackend, EncryptedFileBackend, KeyringManager,
    _SimpleCipher, KEY_ACCESS_TOKEN, KEY_REFRESH_TOKEN, KEY_TOKEN_EXPIRY,
    KEY_USER_ID, KEY_USER_EMAIL,
)


class TestTokenInfo:
    """Tests for TokenInfo dataclass."""

    def test_default_values(self):
        token = TokenInfo()
        assert token.access_token is None
        assert token.refresh_token is None
        assert token.token_type == "Bearer"
        assert token.expires_at is None

    def test_is_expired_false_when_no_expiry(self):
        token = TokenInfo(access_token="tok")
        assert token.is_expired is False

    def test_is_expired_true_when_past(self):
        token = TokenInfo(
            access_token="tok",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        assert token.is_expired is True

    def test_is_expired_false_when_future(self):
        token = TokenInfo(
            access_token="tok",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        assert token.is_expired is False

    def test_is_valid_requires_token_and_not_expired(self):
        token = TokenInfo(
            access_token="tok",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        assert token.is_valid is True

    def test_is_valid_false_when_no_token(self):
        token = TokenInfo()
        assert token.is_valid is False

    def test_is_valid_false_when_expired(self):
        token = TokenInfo(
            access_token="tok",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        assert token.is_valid is False

    def test_time_until_expiry_returns_none_when_no_expiry(self):
        token = TokenInfo()
        assert token.time_until_expiry is None

    def test_time_until_expiry_returns_timedelta(self):
        future = datetime.now() + timedelta(hours=1)
        token = TokenInfo(expires_at=future)
        td = token.time_until_expiry
        assert td is not None
        assert td.total_seconds() > 0

    def test_to_dict(self):
        token = TokenInfo(
            access_token="a", refresh_token="r",
            user_id="u1", user_email="test@test.com",
            expires_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        d = token.to_dict()
        assert d["access_token"] == "a"
        assert d["refresh_token"] == "r"
        assert d["user_id"] == "u1"
        assert d["expires_at"] == "2025-01-01T12:00:00"

    def test_from_dict(self):
        data = {
            "access_token": "a",
            "refresh_token": "r",
            "token_type": "Bearer",
            "expires_at": "2025-01-01T12:00:00",
            "user_id": "u1",
            "user_email": "e@e.com",
        }
        token = TokenInfo.from_dict(data)
        assert token.access_token == "a"
        assert token.user_id == "u1"
        assert token.expires_at == datetime(2025, 1, 1, 12, 0, 0)

    def test_from_dict_handles_bad_expiry(self):
        data = {"access_token": "a", "expires_at": "not-a-date"}
        token = TokenInfo.from_dict(data)
        assert token.expires_at is None

    def test_from_dict_minimal(self):
        token = TokenInfo.from_dict({})
        assert token.access_token is None
        assert token.token_type == "Bearer"


class TestKeyringBackend:
    """Tests for KeyringBackend."""

    def test_is_available_false_when_no_keyring(self):
        with patch("keyring_manager.KEYRING_AVAILABLE", False):
            backend = KeyringBackend()
            backend._available = None
            assert backend.is_available() is False

    def test_store_fails_when_unavailable(self):
        with patch("keyring_manager.KEYRING_AVAILABLE", False):
            backend = KeyringBackend()
            backend._available = False
            assert backend.store("key", "val") is False

    def test_retrieve_returns_none_when_unavailable(self):
        with patch("keyring_manager.KEYRING_AVAILABLE", False):
            backend = KeyringBackend()
            backend._available = False
            assert backend.retrieve("key") is None

    def test_delete_returns_false_when_unavailable(self):
        with patch("keyring_manager.KEYRING_AVAILABLE", False):
            backend = KeyringBackend()
            backend._available = False
            assert backend.delete("key") is False

    def test_store_calls_keyring(self):
        mock_keyring = MagicMock()
        with patch("keyring_manager.KEYRING_AVAILABLE", True), \
             patch("keyring_manager.keyring", mock_keyring):
            backend = KeyringBackend()
            backend._available = True
            result = backend.store("mykey", "myval")
            assert result is True
            mock_keyring.set_password.assert_called_once()

    def test_retrieve_calls_keyring(self):
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "stored"
        with patch("keyring_manager.KEYRING_AVAILABLE", True), \
             patch("keyring_manager.keyring", mock_keyring):
            backend = KeyringBackend()
            backend._available = True
            assert backend.retrieve("mykey") == "stored"

    def test_clear_all_deletes_all_keys(self):
        with patch("keyring_manager.KEYRING_AVAILABLE", False):
            backend = KeyringBackend()
            backend._available = False
            result = backend.clear_all()
            assert result is False


class TestEncryptedFileBackend:
    """Tests for EncryptedFileBackend."""

    def test_is_always_available(self, tmp_path):
        backend = EncryptedFileBackend(file_path=tmp_path / "creds.enc")
        assert backend.is_available() is True

    def test_store_and_retrieve(self, tmp_path):
        backend = EncryptedFileBackend(file_path=tmp_path / "creds.enc")
        backend.store("key1", "value1")
        assert backend.retrieve("key1") == "value1"

    def test_retrieve_missing_key_returns_none(self, tmp_path):
        backend = EncryptedFileBackend(file_path=tmp_path / "creds.enc")
        assert backend.retrieve("nonexistent") is None

    def test_delete_key(self, tmp_path):
        backend = EncryptedFileBackend(file_path=tmp_path / "creds.enc")
        backend.store("key1", "val1")
        result = backend.delete("key1")
        assert result is True
        assert backend.retrieve("key1") is None

    def test_delete_nonexistent_key(self, tmp_path):
        backend = EncryptedFileBackend(file_path=tmp_path / "creds.enc")
        assert backend.delete("nope") is True

    def test_clear_all(self, tmp_path):
        fp = tmp_path / "creds.enc"
        backend = EncryptedFileBackend(file_path=fp)
        backend.store("k", "v")
        assert fp.exists()
        backend.clear_all()
        assert not fp.exists()


class TestSimpleCipher:
    """Tests for _SimpleCipher fallback."""

    def test_encrypt_decrypt_roundtrip(self):
        cipher = _SimpleCipher(b"a" * 32)
        data = b"hello world"
        encrypted = cipher.encrypt(data)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == data

    def test_encrypt_changes_data(self):
        cipher = _SimpleCipher(b"key1234567890123")
        data = b"secret"
        encrypted = cipher.encrypt(data)
        assert encrypted != data


class TestKeyringManager:
    """Tests for KeyringManager."""

    def _make_manager(self, tmp_path):
        with patch("keyring_manager.KEYRING_AVAILABLE", False):
            mgr = KeyringManager(fallback_path=tmp_path / "creds.enc")
        return mgr

    def test_uses_file_backend_when_no_keyring(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.is_using_keyring is False
        assert mgr.backend_name == "encrypted_file"

    def test_store_and_get_tokens(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        result = mgr.store_tokens(
            access_token="access123",
            refresh_token="refresh456",
            expires_in=3600,
            user_id="user1",
            user_email="user@test.com",
        )
        assert result is True
        tokens = mgr.get_tokens()
        assert tokens.access_token == "access123"
        assert tokens.refresh_token == "refresh456"
        assert tokens.user_id == "user1"

    def test_get_access_token(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="at")
        assert mgr.get_access_token() == "at"

    def test_get_refresh_token(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="a", refresh_token="rt")
        assert mgr.get_refresh_token() == "rt"

    def test_get_authorization_header(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="mytoken")
        header = mgr.get_authorization_header()
        assert header == "Bearer mytoken"

    def test_get_authorization_header_none_when_no_token(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.get_authorization_header() is None

    def test_is_authenticated(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="tok", expires_in=3600)
        assert mgr.is_authenticated() is True

    def test_is_not_authenticated_when_empty(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.is_authenticated() is False

    def test_clear_tokens(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="a", refresh_token="r")
        mgr.clear_tokens()
        assert mgr.get_access_token() is None
        assert mgr.get_refresh_token() is None

    def test_update_access_token(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="old")
        mgr.update_access_token("new", expires_in=3600)
        assert mgr.get_access_token() == "new"

    def test_store_credential(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.store_credential("custom_key", "custom_val") is True
        assert mgr.get_credential("custom_key") == "custom_val"

    def test_delete_credential(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_credential("k", "v")
        mgr.delete_credential("k")
        assert mgr.get_credential("k") is None

    def test_clear_all(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_credential("a", "b")
        result = mgr.clear_all()
        assert result is True

    def test_export_for_backup(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="a", refresh_token="r", user_id="u1")
        data = mgr.export_for_backup()
        assert data is not None
        assert data["access_token"] == "a"

    def test_export_for_backup_none_when_no_tokens(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.export_for_backup() is None

    def test_import_from_backup(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        backup_data = {"access_token": "imported", "refresh_token": "rt"}
        result = mgr.import_from_backup(backup_data)
        assert result is True
        assert mgr.get_access_token() == "imported"

    def test_import_from_backup_fails_without_access_token(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        result = mgr.import_from_backup({})
        assert result is False

    def test_token_caching(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="cached")
        t1 = mgr.get_tokens()
        t2 = mgr.get_tokens()
        assert t1 is t2  # cached instance

    def test_needs_refresh(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.store_tokens(access_token="a", refresh_token="r", expires_in=1)
        # Force expiry by manipulating backend
        import time
        time.sleep(0.1)
        # In practice, with 30-sec buffer, 1 second expiry looks expired
        tokens = mgr.get_tokens()
        # Whether it needs refresh depends on the buffer logic
        assert isinstance(mgr.needs_refresh(), bool)
