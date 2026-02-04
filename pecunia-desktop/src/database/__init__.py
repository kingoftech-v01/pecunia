"""
Database module for Pecunia Desktop.

Provides async SQLite database connection management and ORM models
with offline-first architecture support.
"""

from .connection import (
    AsyncDatabaseConnection,
    DatabaseBackupError,
    DatabaseConnectionError,
    DatabaseNotInitializedError,
    close_database,
    get_db,
    get_session,
    init_database,
    session_scope,
)

__all__ = [
    # Classes
    "AsyncDatabaseConnection",
    # Exceptions
    "DatabaseConnectionError",
    "DatabaseNotInitializedError",
    "DatabaseBackupError",
    # Functions
    "get_db",
    "init_database",
    "get_session",
    "session_scope",
    "close_database",
]
