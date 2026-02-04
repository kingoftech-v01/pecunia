"""Tests for src/database/connection.py — Database connection manager."""

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from database.connection import (
    AsyncDatabaseConnection, DatabaseConnectionError,
    DatabaseNotInitializedError, DatabaseBackupError,
    get_db, init_database, get_session, close_database,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton between tests."""
    AsyncDatabaseConnection._instance = None
    AsyncDatabaseConnection._engine = None
    AsyncDatabaseConnection._session_factory = None
    AsyncDatabaseConnection._initialized = False
    AsyncDatabaseConnection._db_path = None
    yield
    AsyncDatabaseConnection._instance = None
    AsyncDatabaseConnection._engine = None
    AsyncDatabaseConnection._session_factory = None
    AsyncDatabaseConnection._initialized = False
    AsyncDatabaseConnection._db_path = None


class TestSingleton:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self):
        db1 = AsyncDatabaseConnection()
        db2 = AsyncDatabaseConnection()
        assert db1 is db2

    def test_get_db_returns_instance(self):
        import database.connection as mod
        mod._db_connection = None
        db = get_db()
        assert db is not None
        assert isinstance(db, AsyncDatabaseConnection)
        mod._db_connection = None


class TestProperties:
    """Tests for property accessors."""

    def test_engine_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            _ = db.engine

    def test_session_factory_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            _ = db.session_factory

    def test_db_path_none_initially(self):
        db = AsyncDatabaseConnection()
        assert db.db_path is None

    def test_is_initialized_false_initially(self):
        db = AsyncDatabaseConnection()
        assert db.is_initialized is False


class TestDefaultPaths:
    """Tests for default path generation."""

    def test_get_default_db_path_linux(self, tmp_path):
        db = AsyncDatabaseConnection()
        with patch("database.connection.os.name", "posix"), \
             patch("database.connection.os.getenv", return_value=str(tmp_path)):
            path = db._get_default_db_path()
            assert path.name == "pecunia.db"
            assert "Pecunia" in str(path)

    def test_get_default_db_path_windows(self, tmp_path):
        db = AsyncDatabaseConnection()
        with patch("database.connection.os.name", "nt"), \
             patch("database.connection.os.getenv", return_value=str(tmp_path)):
            path = db._get_default_db_path()
            assert "Pecunia" in str(path)

    def test_get_default_backup_dir_with_db_path(self, tmp_path):
        db = AsyncDatabaseConnection()
        db._db_path = tmp_path / "test.db"
        backup_dir = db._get_default_backup_dir()
        assert "backups" in str(backup_dir)

    def test_get_default_backup_dir_without_db_path(self, tmp_path):
        db = AsyncDatabaseConnection()
        db._db_path = None
        with patch("database.connection.os.name", "posix"), \
             patch("database.connection.os.getenv", return_value=str(tmp_path)):
            backup_dir = db._get_default_backup_dir()
            assert "backups" in str(backup_dir)


class TestInitialize:
    """Tests for database initialization."""

    async def test_initialize_in_memory(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        assert db.is_initialized is True
        assert db._engine is not None
        assert db._session_factory is not None
        await db.close()

    async def test_initialize_with_path(self, tmp_path):
        db = AsyncDatabaseConnection()
        db_path = str(tmp_path / "test.db")
        await db.initialize(db_path=db_path)
        assert db.is_initialized is True
        assert db._db_path == Path(db_path)
        await db.close()

    async def test_initialize_skips_if_already_initialized(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        # Second call should skip
        await db.initialize(in_memory=True)
        assert db.is_initialized is True
        await db.close()

    async def test_initialize_creates_parent_dirs(self, tmp_path):
        db = AsyncDatabaseConnection()
        db_path = str(tmp_path / "subdir" / "test.db")
        await db.initialize(db_path=db_path)
        assert (tmp_path / "subdir").exists()
        await db.close()


class TestSessionManagement:
    """Tests for session lifecycle."""

    async def test_get_session(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        session = await db.get_session()
        assert session is not None
        await session.close()
        await db.close()

    async def test_get_session_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            await db.get_session()

    async def test_session_scope_commits_on_success(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        async with db.session_scope() as session:
            assert session is not None
        await db.close()

    async def test_session_scope_rollbacks_on_error(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        with pytest.raises(ValueError):
            async with db.session_scope() as session:
                raise ValueError("test error")
        await db.close()


class TestClose:
    """Tests for closing database connection."""

    async def test_close_disposes_engine(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        assert db.is_initialized is True
        await db.close()
        assert db.is_initialized is False
        assert db._engine is None
        assert db._session_factory is None

    async def test_close_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        await db.close()  # Should not raise


class TestContextManager:
    """Tests for async context manager."""

    async def test_enter_returns_self(self):
        db = AsyncDatabaseConnection()
        result = await db.__aenter__()
        assert result is db

    async def test_exit_closes_connection(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        await db.__aexit__(None, None, None)
        assert db.is_initialized is False


class TestVacuumAnalyze:
    """Tests for maintenance operations."""

    async def test_vacuum_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            await db.vacuum()

    async def test_analyze_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            await db.analyze()

    async def test_optimize_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            await db.optimize()

    async def test_incremental_vacuum_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            await db.incremental_vacuum()


class TestHealthCheck:
    """Tests for health check."""

    async def test_health_check_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        result = await db.health_check()
        assert result["status"] == "unhealthy"
        assert result["initialized"] is False

    async def test_health_check_when_initialized(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        result = await db.health_check()
        assert result["status"] == "healthy"
        assert result["initialized"] is True
        await db.close()


class TestStatistics:
    """Tests for database statistics."""

    async def test_get_statistics_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        stats = await db.get_statistics()
        assert "error" in stats

    async def test_get_statistics_when_initialized(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        stats = await db.get_statistics()
        assert "tables" in stats
        assert "sqlite_version" in stats
        await db.close()


class TestBackup:
    """Tests for backup functionality."""

    async def test_backup_raises_when_not_initialized(self):
        db = AsyncDatabaseConnection()
        with pytest.raises(DatabaseNotInitializedError):
            await db.backup()

    async def test_backup_raises_for_in_memory(self):
        db = AsyncDatabaseConnection()
        await db.initialize(in_memory=True)
        with pytest.raises(DatabaseNotInitializedError):
            await db.backup()
        await db.close()

    async def test_backup_creates_file(self, tmp_path):
        db = AsyncDatabaseConnection()
        db_path = str(tmp_path / "test.db")
        backup_dir = str(tmp_path / "backups")
        await db.initialize(db_path=db_path, backup_dir=backup_dir)
        backup_file = await db.backup()
        assert backup_file.exists()
        await db.close()


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    async def test_init_database(self):
        import database.connection as mod
        mod._db_connection = None
        db = await init_database(in_memory=True, create_tables=False)
        assert db.is_initialized is True
        await db.close()
        mod._db_connection = None

    async def test_close_database(self):
        import database.connection as mod
        mod._db_connection = None
        await init_database(in_memory=True, create_tables=False)
        await close_database()
        assert mod._db_connection is None
