"""
SQLite database connection manager with async support.

Provides async connection pooling, session management, database initialization,
migrations, backup functionality, and optional encryption for the offline-first
desktop application.
"""

import asyncio
import logging
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass


class DatabaseNotInitializedError(DatabaseConnectionError):
    """Exception raised when database operations are attempted before initialization."""
    pass


class DatabaseBackupError(DatabaseConnectionError):
    """Exception raised when backup operations fail."""
    pass


class AsyncDatabaseConnection:
    """
    Async SQLite database connection manager.

    Manages async database connections with proper configuration for desktop
    application use, including WAL mode for better concurrency, foreign key
    enforcement, connection pooling, backup functionality, and optional encryption.

    This class implements the singleton pattern to ensure a single database
    connection throughout the application lifecycle.

    Attributes:
        _instance: Singleton instance of the connection manager.
        _engine: SQLAlchemy async engine instance.
        _session_factory: Async session factory for creating sessions.
        _db_path: Path to the SQLite database file.
        _encryption_key: Optional encryption key for database encryption.
    """

    _instance: Optional['AsyncDatabaseConnection'] = None
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    _db_path: Optional[Path] = None
    _backup_dir: Optional[Path] = None
    _encryption_key: Optional[str] = None
    _initialized: bool = False
    _lock: asyncio.Lock = None

    def __new__(cls) -> 'AsyncDatabaseConnection':
        """Singleton pattern to ensure single database connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    def __init__(self):
        """Initialize the database connection manager."""
        # Initialization is handled in __new__ for singleton
        pass

    @property
    def engine(self) -> AsyncEngine:
        """
        Get the SQLAlchemy async engine.

        Returns:
            The async engine instance.

        Raises:
            DatabaseNotInitializedError: If database not initialized.
        """
        if self._engine is None:
            raise DatabaseNotInitializedError(
                "Database not initialized. Call initialize() first."
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Get the async session factory.

        Returns:
            The async session factory instance.

        Raises:
            DatabaseNotInitializedError: If database not initialized.
        """
        if self._session_factory is None:
            raise DatabaseNotInitializedError(
                "Database not initialized. Call initialize() first."
            )
        return self._session_factory

    @property
    def db_path(self) -> Optional[Path]:
        """Get the path to the database file."""
        return self._db_path

    @property
    def is_initialized(self) -> bool:
        """Check if the database is initialized."""
        return self._initialized

    def _get_default_db_path(self) -> Path:
        """
        Get the default database path based on the operating system.

        Returns:
            Path to the default database location.
        """
        if os.name == 'nt':  # Windows
            app_data = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        else:  # Unix-like (macOS, Linux)
            app_data = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

        app_dir = app_data / 'Pecunia'
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / 'pecunia.db'

    def _get_default_backup_dir(self) -> Path:
        """
        Get the default backup directory path.

        Returns:
            Path to the default backup directory.
        """
        if self._db_path:
            backup_dir = self._db_path.parent / 'backups'
        else:
            if os.name == 'nt':
                app_data = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
            else:
                app_data = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
            backup_dir = app_data / 'Pecunia' / 'backups'

        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    async def initialize(
        self,
        db_path: Optional[str] = None,
        echo: bool = False,
        in_memory: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        encryption_key: Optional[str] = None,
        backup_dir: Optional[str] = None,
    ) -> None:
        """
        Initialize the async database connection.

        Args:
            db_path: Path to the SQLite database file. If None, uses default location.
            echo: Whether to echo SQL statements (for debugging).
            in_memory: Whether to use an in-memory database (for testing).
            pool_size: Number of connections to keep in the pool.
            max_overflow: Maximum overflow connections beyond pool_size.
            pool_timeout: Timeout for getting a connection from the pool.
            encryption_key: Optional key for database encryption (requires sqlcipher).
            backup_dir: Directory for storing backups. If None, uses default.

        Raises:
            DatabaseConnectionError: If initialization fails.
        """
        async with self._lock:
            if self._initialized:
                logger.warning("Database already initialized. Skipping re-initialization.")
                return

            try:
                # Store encryption key
                self._encryption_key = encryption_key

                # Determine database path
                if in_memory:
                    db_url = "sqlite+aiosqlite:///:memory:"
                    self._db_path = None
                else:
                    if db_path is None:
                        self._db_path = self._get_default_db_path()
                    else:
                        self._db_path = Path(db_path)
                        self._db_path.parent.mkdir(parents=True, exist_ok=True)

                    # Handle encryption if key provided
                    if encryption_key:
                        # Use sqlcipher for encryption
                        db_url = f"sqlite+aiosqlite:///{self._db_path}?cipher=aes-256-cbc"
                    else:
                        db_url = f"sqlite+aiosqlite:///{self._db_path}"

                # Set backup directory
                if backup_dir:
                    self._backup_dir = Path(backup_dir)
                    self._backup_dir.mkdir(parents=True, exist_ok=True)
                else:
                    self._backup_dir = self._get_default_backup_dir()

                # Mask the database URL to avoid leaking path info in logs
                masked_url = db_url.split("///")[0] + "///***" if "///" in db_url else db_url
                logger.info(f"Initializing async database at: {masked_url}")

                # Connection arguments for SQLite
                connect_args = {"check_same_thread": False}

                # Add encryption key to connection args if provided
                if encryption_key:
                    connect_args["encryption_key"] = encryption_key

                # Create async engine with appropriate settings
                if in_memory:
                    # For in-memory databases, use StaticPool to maintain connection
                    self._engine = create_async_engine(
                        db_url,
                        echo=echo,
                        connect_args=connect_args,
                        poolclass=StaticPool,
                    )
                else:
                    # For file-based databases, use connection pooling
                    # Note: aiosqlite doesn't support traditional pooling well,
                    # so we use NullPool and let aiosqlite manage connections
                    self._engine = create_async_engine(
                        db_url,
                        echo=echo,
                        connect_args=connect_args,
                        poolclass=NullPool,
                        # Pool settings are ignored with NullPool but kept for reference
                        pool_pre_ping=True,
                    )

                # Configure SQLite pragmas on connection
                await self._configure_sqlite_pragmas()

                # Create async session factory
                self._session_factory = async_sessionmaker(
                    bind=self._engine,
                    class_=AsyncSession,
                    autocommit=False,
                    autoflush=False,
                    expire_on_commit=False,
                )

                self._initialized = True
                logger.info("Async database connection initialized successfully.")

            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise DatabaseConnectionError(f"Failed to initialize database: {e}") from e

    async def _configure_sqlite_pragmas(self) -> None:
        """Configure SQLite connection with optimal settings using pragmas."""

        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas on each new connection."""
            cursor = dbapi_connection.cursor()
            try:
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys = ON")
                # Use WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode = WAL")
                # Synchronous mode for durability with good performance
                cursor.execute("PRAGMA synchronous = NORMAL")
                # Increase cache size (negative = KB, 64MB cache)
                cursor.execute("PRAGMA cache_size = -65536")
                # Enable memory-mapped I/O (256MB)
                cursor.execute("PRAGMA mmap_size = 268435456")
                # Temporary tables in memory
                cursor.execute("PRAGMA temp_store = MEMORY")
                # Busy timeout (5 seconds)
                cursor.execute("PRAGMA busy_timeout = 5000")
                # Auto-vacuum incremental for gradual space reclamation
                cursor.execute("PRAGMA auto_vacuum = INCREMENTAL")
            finally:
                cursor.close()

    async def create_tables(self, base=None) -> None:
        """
        Create all database tables.

        Args:
            base: SQLAlchemy declarative base. If None, imports from models.
        """
        if base is None:
            from .models import Base
            base = Base

        async with self._engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)
        logger.info("Database tables created successfully.")

    async def drop_tables(self, base=None) -> None:
        """
        Drop all database tables.

        WARNING: This will delete all data! Use with caution.

        Args:
            base: SQLAlchemy declarative base. If None, imports from models.
        """
        if base is None:
            from .models import Base
            base = Base

        async with self._engine.begin() as conn:
            await conn.run_sync(base.metadata.drop_all)
        logger.warning("All database tables dropped.")

    async def get_session(self) -> AsyncSession:
        """
        Get a new async database session.

        Returns:
            A new AsyncSession instance.

        Raises:
            DatabaseNotInitializedError: If database not initialized.
        """
        if not self._initialized:
            raise DatabaseNotInitializedError(
                "Database not initialized. Call initialize() first."
            )
        return self._session_factory()

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope around a series of operations.

        This context manager handles session lifecycle, committing on success
        and rolling back on failure.

        Yields:
            An async database session with automatic commit/rollback.

        Example:
            async with db.session_scope() as session:
                user = User(name="John")
                session.add(user)
                # Automatically committed on exit
        """
        session = await self.get_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

    async def execute_raw(self, sql: str, params: Optional[dict] = None) -> any:
        """
        Execute raw SQL statement.

        Args:
            sql: SQL statement to execute.
            params: Optional parameters for the SQL statement.

        Returns:
            The result of the execution.
        """
        async with self._engine.begin() as conn:
            if params:
                result = await conn.execute(text(sql), params)
            else:
                result = await conn.execute(text(sql))
            return result

    async def run_migrations(
        self,
        migrations_path: Optional[str] = None,
        migration_callback: Optional[Callable] = None,
    ) -> None:
        """
        Run database migrations.

        This method supports two approaches:
        1. SQL file-based migrations from a directory
        2. Custom migration callback function

        Args:
            migrations_path: Path to directory containing migration SQL files.
            migration_callback: Custom async callback for migrations.

        Example:
            # Using SQL files
            await db.run_migrations(migrations_path="./migrations")

            # Using custom callback
            async def my_migrations(engine):
                async with engine.begin() as conn:
                    await conn.execute(text("ALTER TABLE ..."))
            await db.run_migrations(migration_callback=my_migrations)
        """
        logger.info("Running database migrations...")

        try:
            # Create migrations tracking table if it doesn't exist
            async with self._engine.begin() as conn:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS _migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

            # Run custom migration callback if provided
            if migration_callback:
                await migration_callback(self._engine)

            # Run SQL file migrations if path provided
            if migrations_path:
                migrations_dir = Path(migrations_path)
                if migrations_dir.exists():
                    # Get list of applied migrations
                    async with self._engine.begin() as conn:
                        result = await conn.execute(
                            text("SELECT name FROM _migrations")
                        )
                        applied = {row[0] for row in result.fetchall()}

                    # Get migration files sorted by name
                    migration_files = sorted(migrations_dir.glob("*.sql"))

                    for migration_file in migration_files:
                        if migration_file.name not in applied:
                            logger.info(f"Applying migration: {migration_file.name}")
                            sql_content = migration_file.read_text()

                            async with self._engine.begin() as conn:
                                # Execute migration statements
                                # Note: naive split on ';' may break if SQL
                                # contains semicolons inside string literals.
                                # For production use, consider a proper SQL parser.
                                import re
                                statements = re.split(r';(?=(?:[^\']*\'[^\']*\')*[^\']*$)', sql_content)
                                for statement in statements:
                                    statement = statement.strip()
                                    if statement:
                                        await conn.execute(text(statement))

                                # Record migration
                                await conn.execute(
                                    text("INSERT INTO _migrations (name) VALUES (:name)"),
                                    {"name": migration_file.name}
                                )
                            logger.info(f"Migration applied: {migration_file.name}")

            logger.info("Database migrations completed.")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise DatabaseConnectionError(f"Migration failed: {e}") from e

    async def backup(
        self,
        backup_path: Optional[str] = None,
        max_backups: int = 5,
    ) -> Path:
        """
        Create a backup of the database.

        Args:
            backup_path: Custom path for the backup file. If None, uses default
                        naming with timestamp in the backup directory.
            max_backups: Maximum number of backups to keep. Oldest are deleted.

        Returns:
            Path to the created backup file.

        Raises:
            DatabaseBackupError: If backup fails.
            DatabaseNotInitializedError: If database not initialized.
        """
        if not self._initialized or self._db_path is None:
            raise DatabaseNotInitializedError(
                "Cannot backup: database not initialized or using in-memory database."
            )

        try:
            # Determine backup path
            if backup_path:
                backup_file = Path(backup_path)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self._backup_dir / f"pecunia_backup_{timestamp}.db"

            backup_file.parent.mkdir(parents=True, exist_ok=True)

            # Checkpoint WAL to ensure all data is in main database file
            async with self._engine.begin() as conn:
                await conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))

            # Copy database file
            await asyncio.to_thread(shutil.copy2, self._db_path, backup_file)

            logger.info(f"Database backup created: {backup_file}")

            # Clean up old backups if max_backups is set
            if max_backups > 0 and not backup_path:
                await self._cleanup_old_backups(max_backups)

            return backup_file

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise DatabaseBackupError(f"Backup failed: {e}") from e

    async def _cleanup_old_backups(self, max_backups: int) -> None:
        """
        Remove old backups exceeding the maximum count.

        Args:
            max_backups: Maximum number of backups to keep.
        """
        backup_files = sorted(
            self._backup_dir.glob("pecunia_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for old_backup in backup_files[max_backups:]:
            try:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")
            except OSError as e:
                logger.warning(f"Failed to remove old backup {old_backup}: {e}")

    async def restore(self, backup_path: str) -> None:
        """
        Restore the database from a backup.

        WARNING: This will replace the current database!

        Args:
            backup_path: Path to the backup file to restore.

        Raises:
            DatabaseBackupError: If restore fails.
            FileNotFoundError: If backup file doesn't exist.
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        if self._db_path is None:
            raise DatabaseBackupError("Cannot restore: using in-memory database.")

        try:
            # Close current connections
            await self.close()

            # Copy backup to database path
            await asyncio.to_thread(shutil.copy2, backup_file, self._db_path)

            logger.info(f"Database restored from: {backup_file}")

            # Re-initialize the database
            self._initialized = False
            await self.initialize(db_path=str(self._db_path))

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise DatabaseBackupError(f"Restore failed: {e}") from e

    async def vacuum(self) -> None:
        """
        Optimize the database file size by running VACUUM.

        This reclaims unused space and defragments the database file.
        Note: VACUUM requires exclusive access and may take time for large databases.
        """
        if not self._initialized:
            raise DatabaseNotInitializedError("Database not initialized.")

        logger.info("Starting database vacuum...")
        async with self._engine.begin() as conn:
            await conn.execute(text("VACUUM"))
        logger.info("Database vacuum completed.")

    async def analyze(self) -> None:
        """
        Analyze the database to update query planner statistics.

        This helps SQLite make better query optimization decisions.
        """
        if not self._initialized:
            raise DatabaseNotInitializedError("Database not initialized.")

        logger.info("Analyzing database...")
        async with self._engine.begin() as conn:
            await conn.execute(text("ANALYZE"))
        logger.info("Database analysis completed.")

    async def optimize(self) -> None:
        """
        Run optimization pragma for better performance.

        This runs PRAGMA optimize which performs various optimizations
        based on query patterns.
        """
        if not self._initialized:
            raise DatabaseNotInitializedError("Database not initialized.")

        async with self._engine.begin() as conn:
            await conn.execute(text("PRAGMA optimize"))
        logger.info("Database optimization completed.")

    async def incremental_vacuum(self, pages: int = 100) -> None:
        """
        Perform incremental vacuum to gradually reclaim space.

        Args:
            pages: Number of pages to vacuum (0 = all free pages).
        """
        if not self._initialized:
            raise DatabaseNotInitializedError("Database not initialized.")

        async with self._engine.begin() as conn:
            await conn.execute(text(f"PRAGMA incremental_vacuum({pages})"))
        logger.debug(f"Incremental vacuum completed ({pages} pages).")

    async def health_check(self) -> dict:
        """
        Perform a health check on the database connection.

        Returns:
            Dictionary containing health check results including:
            - status: 'healthy' or 'unhealthy'
            - initialized: Whether database is initialized
            - db_path: Path to database file
            - db_size_bytes: Size of database file
            - integrity_check: Result of integrity check
            - wal_mode: Whether WAL mode is enabled
            - foreign_keys: Whether foreign keys are enabled
            - page_count: Number of pages in database
            - page_size: Size of each page
            - freelist_count: Number of free pages

        Example:
            health = await db.health_check()
            if health['status'] == 'healthy':
                print("Database is healthy!")
        """
        health_result = {
            "status": "unhealthy",
            "initialized": self._initialized,
            "db_path": str(self._db_path) if self._db_path else None,
            "db_size_bytes": None,
            "integrity_check": None,
            "wal_mode": None,
            "foreign_keys": None,
            "page_count": None,
            "page_size": None,
            "freelist_count": None,
            "error": None,
        }

        if not self._initialized:
            health_result["error"] = "Database not initialized"
            return health_result

        try:
            # Check database file size
            if self._db_path and self._db_path.exists():
                health_result["db_size_bytes"] = self._db_path.stat().st_size

            async with self._engine.begin() as conn:
                # Quick integrity check
                result = await conn.execute(text("PRAGMA quick_check"))
                integrity = result.scalar()
                health_result["integrity_check"] = integrity

                # Check journal mode
                result = await conn.execute(text("PRAGMA journal_mode"))
                health_result["wal_mode"] = result.scalar() == "wal"

                # Check foreign keys
                result = await conn.execute(text("PRAGMA foreign_keys"))
                health_result["foreign_keys"] = bool(result.scalar())

                # Get page statistics
                result = await conn.execute(text("PRAGMA page_count"))
                health_result["page_count"] = result.scalar()

                result = await conn.execute(text("PRAGMA page_size"))
                health_result["page_size"] = result.scalar()

                result = await conn.execute(text("PRAGMA freelist_count"))
                health_result["freelist_count"] = result.scalar()

            # Determine overall health status
            if health_result["integrity_check"] == "ok":
                health_result["status"] = "healthy"

            logger.debug(f"Health check completed: {health_result['status']}")

        except Exception as e:
            health_result["error"] = str(e)
            logger.error(f"Health check failed: {e}")

        return health_result

    async def get_statistics(self) -> dict:
        """
        Get database statistics and metrics.

        Returns:
            Dictionary containing various database statistics.
        """
        stats = {}

        if not self._initialized:
            return {"error": "Database not initialized"}

        try:
            async with self._engine.begin() as conn:
                # Get table information
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ))
                tables = [row[0] for row in result.fetchall()]
                stats["tables"] = tables
                stats["table_count"] = len(tables)

                # Get row counts for each table
                # Validate table names to prevent SQL injection
                import re
                valid_table_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
                table_stats = {}
                for table in tables:
                    if not valid_table_pattern.match(table):
                        logger.warning(f"Skipping invalid table name: {table}")
                        continue
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    table_stats[table] = {"row_count": result.scalar()}
                stats["table_statistics"] = table_stats

                # Get index information
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
                ))
                stats["index_count"] = len(result.fetchall())

                # Database version
                result = await conn.execute(text("SELECT sqlite_version()"))
                stats["sqlite_version"] = result.scalar()

        except Exception as e:
            stats["error"] = str(e)
            logger.error(f"Failed to get statistics: {e}")

        return stats

    async def close(self) -> None:
        """
        Close the database connection and cleanup resources.

        This should be called when shutting down the application.
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
        self._session_factory = None
        self._initialized = False
        logger.info("Async database connection closed.")

    async def __aenter__(self) -> 'AsyncDatabaseConnection':
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Module-level singleton instance
_db_connection: Optional[AsyncDatabaseConnection] = None


def get_db() -> AsyncDatabaseConnection:
    """
    Get the global database connection instance.

    Returns:
        The AsyncDatabaseConnection singleton instance.
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = AsyncDatabaseConnection()
    return _db_connection


async def init_database(
    db_path: Optional[str] = None,
    echo: bool = False,
    in_memory: bool = False,
    create_tables: bool = True,
    encryption_key: Optional[str] = None,
    **kwargs,
) -> AsyncDatabaseConnection:
    """
    Initialize the database connection.

    Convenience function for initializing the global database connection.

    Args:
        db_path: Path to the SQLite database file.
        echo: Whether to echo SQL statements.
        in_memory: Whether to use an in-memory database.
        create_tables: Whether to create tables after initialization.
        encryption_key: Optional key for database encryption.
        **kwargs: Additional arguments passed to initialize().

    Returns:
        The AsyncDatabaseConnection instance.

    Example:
        db = await init_database(
            db_path="./data/app.db",
            echo=True,
            create_tables=True
        )
    """
    db = get_db()
    await db.initialize(
        db_path=db_path,
        echo=echo,
        in_memory=in_memory,
        encryption_key=encryption_key,
        **kwargs,
    )
    if create_tables:
        await db.create_tables()
    return db


async def get_session() -> AsyncSession:
    """
    Get a new async database session.

    Convenience function for getting a session from the global connection.

    Returns:
        A new AsyncSession instance.
    """
    return await get_db().get_session()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.

    Convenience function providing a transactional scope.

    Yields:
        An async database session with automatic commit/rollback.

    Example:
        async with session_scope() as session:
            user = User(name="John")
            session.add(user)
    """
    async with get_db().session_scope() as session:
        yield session


async def close_database() -> None:
    """
    Close the global database connection.

    Should be called during application shutdown.
    """
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
