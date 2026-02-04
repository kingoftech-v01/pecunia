"""Tests for src/services/backup.py — BackupService and related classes."""

import json
import os
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from services.backup import (
    BackupService, BackupInfo, BackupError, RestoreError,
)


class TestBackupInfo:
    """Tests for BackupInfo data class."""

    def _make_info(self, size_bytes=1024, days_ago=0, **kwargs):
        defaults = dict(
            path=Path("/tmp/test_backup.financebackup"),
            created_at=datetime.now() - timedelta(days=days_ago),
            size_bytes=size_bytes,
            version="1.0",
            checksum="abc123",
        )
        defaults.update(kwargs)
        return BackupInfo(**defaults)

    def test_filename_property(self):
        info = self._make_info()
        assert info.filename == "test_backup.financebackup"

    def test_size_formatted_bytes(self):
        info = self._make_info(size_bytes=512)
        assert "512.0 B" == info.size_formatted

    def test_size_formatted_kb(self):
        info = self._make_info(size_bytes=2048)
        assert "KB" in info.size_formatted

    def test_size_formatted_mb(self):
        info = self._make_info(size_bytes=2 * 1024 * 1024)
        assert "MB" in info.size_formatted

    def test_size_formatted_gb(self):
        info = self._make_info(size_bytes=2 * 1024 * 1024 * 1024)
        assert "GB" in info.size_formatted

    def test_age_days(self):
        info = self._make_info(days_ago=5)
        assert info.age_days == 5

    def test_age_days_today(self):
        info = self._make_info(days_ago=0)
        assert info.age_days == 0

    def test_to_dict(self):
        info = self._make_info()
        d = info.to_dict()
        assert d["filename"] == "test_backup.financebackup"
        assert d["version"] == "1.0"
        assert d["checksum"] == "abc123"
        assert d["size_bytes"] == 1024
        assert "created_at" in d
        assert "age_days" in d
        assert "size_formatted" in d
        assert "metadata" in d

    def test_metadata_default_empty(self):
        info = self._make_info()
        assert info.metadata == {}

    def test_metadata_custom(self):
        info = self._make_info(metadata={"description": "test"})
        assert info.metadata["description"] == "test"


class TestBackupServiceInit:
    """Tests for BackupService initialization."""

    def test_init_creates_backup_dir(self, tmp_path):
        backup_dir = tmp_path / "backups"
        svc = BackupService(backup_dir=backup_dir)
        assert backup_dir.exists()

    def test_init_default_backup_dir(self, tmp_path):
        with patch("services.backup.os.name", "posix"), \
             patch("services.backup.os.environ.get", return_value=str(tmp_path)):
            svc = BackupService()
            assert svc._backup_dir is not None

    def test_set_database_path(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        db_path = tmp_path / "test.db"
        svc.set_database_path(db_path)
        assert svc._database_path == db_path

    def test_set_backup_dir(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups1")
        new_dir = tmp_path / "backups2"
        svc.set_backup_dir(new_dir)
        assert svc._backup_dir == new_dir
        assert new_dir.exists()

    def test_set_settings_path(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        svc.set_settings_path(tmp_path / "settings.json")
        assert svc._settings_path == tmp_path / "settings.json"

    def test_set_progress_callback(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        cb = MagicMock()
        svc.set_progress_callback(cb)
        svc._report_progress(1, 10, "test")
        cb.assert_called_once_with(1, 10, "test")

    def test_report_progress_no_callback(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        # Should not raise
        svc._report_progress(1, 10, "test")


class TestBackupServiceCreateBackup:
    """Tests for BackupService.create_backup."""

    def _create_db(self, path):
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        conn.close()

    def test_create_backup_success(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)

        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        result = svc.create_backup(description="test backup")

        assert isinstance(result, BackupInfo)
        assert result.path.exists()
        assert result.version == "1.0"
        assert result.size_bytes > 0
        assert result.checksum != ""
        assert result.metadata["description"] == "test backup"

    def test_create_backup_custom_path(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        custom_path = tmp_path / "custom" / "my_backup.financebackup"
        self._create_db(db_path)

        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        result = svc.create_backup(output_path=custom_path)

        assert result.path == custom_path
        assert custom_path.exists()

    def test_create_backup_with_settings(self, tmp_path):
        db_path = tmp_path / "test.db"
        settings_path = tmp_path / "settings.json"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        settings_path.write_text('{"theme": "dark"}')

        svc = BackupService(
            database_path=db_path,
            backup_dir=backup_dir,
            settings_path=settings_path,
        )
        result = svc.create_backup(include_settings=True)
        assert result.metadata["settings_included"] is True

    def test_create_backup_without_settings(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)

        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        result = svc.create_backup(include_settings=False)
        assert result.metadata["settings_included"] is False

    def test_create_backup_no_database(self, tmp_path):
        backup_dir = tmp_path / "backups"
        svc = BackupService(backup_dir=backup_dir)
        with pytest.raises(BackupError):
            svc.create_backup()

    def test_create_backup_missing_database(self, tmp_path):
        db_path = tmp_path / "nonexistent.db"
        backup_dir = tmp_path / "backups"
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        with pytest.raises(BackupError):
            svc.create_backup()

    def test_create_backup_contains_manifest(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)

        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        result = svc.create_backup()

        with zipfile.ZipFile(result.path, 'r') as zf:
            assert "manifest.json" in zf.namelist()
            assert "database.db" in zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["version"] == "1.0"
            assert "database" in manifest

    def test_create_backup_reports_progress(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)

        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        progress_calls = []
        svc.set_progress_callback(lambda c, t, m: progress_calls.append((c, t, m)))
        svc.create_backup()
        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100  # Final progress = 100


class TestBackupServiceRestore:
    """Tests for BackupService.restore_backup."""

    def _create_db(self, path):
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        conn.close()

    def _create_backup(self, tmp_path):
        db_path = tmp_path / "source.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        return svc.create_backup()

    def test_restore_backup_success(self, tmp_path):
        backup_info = self._create_backup(tmp_path)
        target_db = tmp_path / "restored.db"
        self._create_db(target_db)

        svc = BackupService(
            database_path=target_db,
            backup_dir=tmp_path / "backups",
        )
        result = svc.restore_backup(
            backup_info.path,
            create_pre_restore_backup=False,
        )
        assert result is True
        assert target_db.exists()

    def test_restore_nonexistent_backup(self, tmp_path):
        svc = BackupService(
            database_path=tmp_path / "test.db",
            backup_dir=tmp_path / "backups",
        )
        with pytest.raises(RestoreError, match="not found"):
            svc.restore_backup(tmp_path / "nonexistent.financebackup")

    def test_restore_no_database_path(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        backup_info = self._create_backup(tmp_path)
        with pytest.raises(RestoreError, match="Database path not set"):
            svc.restore_backup(backup_info.path)

    def test_restore_creates_pre_restore_backup(self, tmp_path):
        backup_info = self._create_backup(tmp_path)
        target_db = tmp_path / "restored.db"
        self._create_db(target_db)

        backup_dir = tmp_path / "restore_backups"
        svc = BackupService(
            database_path=target_db,
            backup_dir=backup_dir,
        )
        svc.restore_backup(backup_info.path, create_pre_restore_backup=True)
        # Should have created a pre_restore backup
        pre_restore = list(backup_dir.glob("pre_restore_*"))
        assert len(pre_restore) >= 1


class TestBackupServiceVerify:
    """Tests for BackupService.verify_backup."""

    def _create_db(self, path):
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

    def test_verify_valid_backup(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)

        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        info = svc.create_backup()

        is_valid, details = svc.verify_backup(info.path)
        assert is_valid is True
        assert details["valid_zip"] is True
        assert details["has_manifest"] is True
        assert details["has_database"] is True
        assert details["checksums_valid"] is True

    def test_verify_nonexistent_file(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        is_valid, details = svc.verify_backup(tmp_path / "nonexistent.zip")
        assert is_valid is False
        assert details["exists"] is False

    def test_verify_non_zip_file(self, tmp_path):
        bad_file = tmp_path / "bad.financebackup"
        bad_file.write_text("not a zip")
        svc = BackupService(backup_dir=tmp_path / "backups")
        is_valid, details = svc.verify_backup(bad_file)
        assert is_valid is False
        assert details["valid_zip"] is False

    def test_verify_zip_without_manifest(self, tmp_path):
        bad_zip = tmp_path / "bad.financebackup"
        with zipfile.ZipFile(bad_zip, 'w') as zf:
            zf.writestr("random.txt", "data")
        svc = BackupService(backup_dir=tmp_path / "backups")
        is_valid, details = svc.verify_backup(bad_zip)
        assert is_valid is False
        assert details["has_manifest"] is False


class TestBackupServiceListAndDelete:
    """Tests for BackupService list and delete operations."""

    def _create_db(self, path):
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

    def test_list_backups_empty(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        result = svc.list_backups()
        assert result == []

    def test_list_backups_with_items(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        svc.create_backup(description="backup1")
        svc.create_backup(description="backup2")
        result = svc.list_backups()
        assert len(result) >= 2

    def test_list_backups_sorted_by_date(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        svc.create_backup()
        svc.create_backup()
        result = svc.list_backups(sort_by='date', descending=True)
        if len(result) >= 2:
            assert result[0].created_at >= result[1].created_at

    def test_delete_backup(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        info = svc.create_backup()
        assert info.path.exists()
        result = svc.delete_backup(info.path)
        assert result is True
        assert not info.path.exists()

    def test_delete_backup_nonexistent(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        result = svc.delete_backup(tmp_path / "nonexistent.financebackup")
        assert result is False

    def test_delete_old_backups(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        for _ in range(5):
            svc.create_backup()
        deleted = svc.delete_old_backups(keep_count=2)
        remaining = svc.list_backups()
        assert len(remaining) <= 2

    def test_get_backup_stats_empty(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        stats = svc.get_backup_stats()
        assert stats["total_backups"] == 0
        assert stats["total_size"] == 0

    def test_get_backup_stats_with_backups(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        svc.create_backup()
        stats = svc.get_backup_stats()
        assert stats["total_backups"] >= 1
        assert stats["total_size"] > 0
        assert stats["newest_backup"] is not None


class TestBackupServiceAutoBackup:
    """Tests for BackupService auto-backup scheduling."""

    def test_is_auto_backup_running_initially_false(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        assert svc.is_auto_backup_running is False

    def test_stop_auto_backup_when_not_running(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        svc.stop_auto_backup()  # Should not raise

    def test_auto_backup_enabled_flag(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        assert svc._auto_backup_enabled is False


class TestBackupServiceQuickMethods:
    """Tests for BackupService quick backup and restore methods."""

    def _create_db(self, path):
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

    def test_quick_backup(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        result = svc.quick_backup("quick test")
        assert isinstance(result, BackupInfo)
        assert result.path.exists()

    def test_restore_latest_no_backups(self, tmp_path):
        svc = BackupService(
            database_path=tmp_path / "test.db",
            backup_dir=tmp_path / "backups",
        )
        with pytest.raises(RestoreError, match="No backups available"):
            svc.restore_latest()

    def test_export_for_migration(self, tmp_path):
        db_path = tmp_path / "test.db"
        backup_dir = tmp_path / "backups"
        export_path = tmp_path / "export.financebackup"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        result = svc.export_for_migration(export_path)
        assert result.path == export_path
        assert export_path.exists()

    def test_import_from_migration(self, tmp_path):
        db_path = tmp_path / "source.db"
        backup_dir = tmp_path / "backups"
        self._create_db(db_path)
        svc = BackupService(database_path=db_path, backup_dir=backup_dir)
        info = svc.create_backup()

        target_db = tmp_path / "target.db"
        self._create_db(target_db)
        svc2 = BackupService(database_path=target_db, backup_dir=tmp_path / "backups2")
        result = svc2.import_from_migration(info.path)
        assert result is True


class TestBackupServiceChecksums:
    """Tests for BackupService checksum and filename generation."""

    def test_calculate_checksum(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        svc = BackupService(backup_dir=tmp_path / "backups")
        checksum = svc._calculate_checksum(test_file)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex digest

    def test_generate_backup_filename(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        name = svc._generate_backup_filename("backup")
        assert name.startswith("backup_")
        assert name.endswith(svc.BACKUP_EXTENSION)

    def test_generate_backup_filename_custom_prefix(self, tmp_path):
        svc = BackupService(backup_dir=tmp_path / "backups")
        name = svc._generate_backup_filename("auto")
        assert name.startswith("auto_")
