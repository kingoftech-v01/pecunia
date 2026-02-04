"""
Backup Service for Finance Desktop Application.

Provides comprehensive backup and restore functionality including
database backups, scheduled auto-backups, and backup management.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread, Event
from typing import List, Dict, Any, Optional, Callable, Tuple
import logging

logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Exception raised for backup-related errors."""
    pass


class RestoreError(Exception):
    """Exception raised for restore-related errors."""
    pass


class BackupInfo:
    """Information about a backup file."""

    def __init__(
        self,
        path: Path,
        created_at: datetime,
        size_bytes: int,
        version: str,
        checksum: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.path = path
        self.created_at = created_at
        self.size_bytes = size_bytes
        self.version = version
        self.checksum = checksum
        self.metadata = metadata or {}

    @property
    def filename(self) -> str:
        """Get the backup filename."""
        return self.path.name

    @property
    def size_formatted(self) -> str:
        """Get human-readable file size."""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def age_days(self) -> int:
        """Get the age of the backup in days."""
        return (datetime.now() - self.created_at).days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'path': str(self.path),
            'filename': self.filename,
            'created_at': self.created_at.isoformat(),
            'size_bytes': self.size_bytes,
            'size_formatted': self.size_formatted,
            'version': self.version,
            'checksum': self.checksum,
            'age_days': self.age_days,
            'metadata': self.metadata
        }


class BackupService:
    """
    Service for managing database backups with scheduled auto-backup support.

    Provides backup creation, restoration, verification, and cleanup
    with progress tracking for large operations.
    """

    BACKUP_EXTENSION = '.financebackup'
    MANIFEST_FILENAME = 'manifest.json'
    DATABASE_FILENAME = 'database.db'
    SETTINGS_FILENAME = 'settings.json'
    CURRENT_VERSION = '1.0'

    def __init__(
        self,
        database_path: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
        settings_path: Optional[Path] = None
    ):
        """
        Initialize the backup service.

        Args:
            database_path: Path to the SQLite database file
            backup_dir: Directory for storing backups
            settings_path: Path to settings JSON file
        """
        self._database_path = database_path
        self._backup_dir = backup_dir or self._get_default_backup_dir()
        self._settings_path = settings_path
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

        # Auto-backup scheduling
        self._auto_backup_enabled = False
        self._auto_backup_interval_hours = 24
        self._auto_backup_thread: Optional[Thread] = None
        self._auto_backup_stop_event = Event()

        # Ensure backup directory exists
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_backup_dir(self) -> Path:
        """Get the default backup directory based on platform."""
        if os.name == 'nt':  # Windows
            base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        else:  # Linux/Mac
            base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

        backup_dir = base / 'Pecunia' / 'backups'
        return backup_dir

    def set_database_path(self, path: Path) -> None:
        """Set the database path."""
        self._database_path = path

    def set_backup_dir(self, path: Path) -> None:
        """Set the backup directory."""
        self._backup_dir = path
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def set_settings_path(self, path: Path) -> None:
        """Set the settings file path."""
        self._settings_path = path

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """
        Set a callback function for progress updates.

        Args:
            callback: Function that receives (current, total, message) parameters
        """
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str = "") -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _generate_backup_filename(self, prefix: str = "backup") -> str:
        """Generate a unique backup filename with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}{self.BACKUP_EXTENSION}"

    # =========================================================================
    # Backup Creation
    # =========================================================================

    def create_backup(
        self,
        output_path: Optional[Path] = None,
        include_settings: bool = True,
        description: str = "",
        compression_level: int = 6
    ) -> BackupInfo:
        """
        Create a complete backup of the database and optionally settings.

        Args:
            output_path: Custom path for the backup file (uses default dir if None)
            include_settings: Whether to include settings in the backup
            description: Optional description for the backup
            compression_level: ZIP compression level (0-9)

        Returns:
            BackupInfo object with details about the created backup

        Raises:
            BackupError: If backup creation fails
        """
        if not self._database_path or not self._database_path.exists():
            raise BackupError("Database path not set or file does not exist")

        try:
            self._report_progress(0, 100, "Starting backup...")

            # Generate output path if not provided
            if output_path is None:
                output_path = self._backup_dir / self._generate_backup_filename()
            else:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup in a temporary directory first
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Step 1: Create a safe copy of the database
                self._report_progress(10, 100, "Copying database...")
                temp_db_path = temp_path / self.DATABASE_FILENAME

                # Use SQLite backup API for safe copy
                source_conn = sqlite3.connect(str(self._database_path))
                dest_conn = sqlite3.connect(str(temp_db_path))

                try:
                    source_conn.backup(dest_conn)
                finally:
                    source_conn.close()
                    dest_conn.close()

                self._report_progress(40, 100, "Database copied...")

                # Step 2: Copy settings if requested
                settings_included = False
                if include_settings and self._settings_path and self._settings_path.exists():
                    self._report_progress(50, 100, "Copying settings...")
                    temp_settings_path = temp_path / self.SETTINGS_FILENAME
                    shutil.copy2(self._settings_path, temp_settings_path)
                    settings_included = True

                self._report_progress(60, 100, "Creating manifest...")

                # Step 3: Create manifest
                db_checksum = self._calculate_checksum(temp_db_path)
                settings_checksum = None
                if settings_included:
                    settings_checksum = self._calculate_checksum(temp_path / self.SETTINGS_FILENAME)

                manifest = {
                    'version': self.CURRENT_VERSION,
                    'created_at': datetime.now().isoformat(),
                    'description': description,
                    'database': {
                        'filename': self.DATABASE_FILENAME,
                        'checksum': db_checksum,
                        'size': temp_db_path.stat().st_size
                    },
                    'settings_included': settings_included,
                    'metadata': {
                        'app_version': '1.0.0',  # Would be imported from config
                        'platform': os.name
                    }
                }

                if settings_included and settings_checksum:
                    manifest['settings'] = {
                        'filename': self.SETTINGS_FILENAME,
                        'checksum': settings_checksum
                    }

                manifest_path = temp_path / self.MANIFEST_FILENAME
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2)

                self._report_progress(70, 100, "Compressing backup...")

                # Step 4: Create ZIP archive
                with zipfile.ZipFile(
                    output_path, 'w',
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=compression_level
                ) as zf:
                    zf.write(manifest_path, self.MANIFEST_FILENAME)
                    zf.write(temp_db_path, self.DATABASE_FILENAME)

                    if settings_included:
                        zf.write(temp_path / self.SETTINGS_FILENAME, self.SETTINGS_FILENAME)

            self._report_progress(90, 100, "Finalizing...")

            # Calculate final checksum
            backup_checksum = self._calculate_checksum(output_path)
            backup_size = output_path.stat().st_size

            self._report_progress(100, 100, "Backup complete!")

            logger.info(f"Backup created: {output_path}")

            return BackupInfo(
                path=output_path,
                created_at=datetime.now(),
                size_bytes=backup_size,
                version=self.CURRENT_VERSION,
                checksum=backup_checksum,
                metadata={
                    'description': description,
                    'settings_included': settings_included,
                    'database_checksum': db_checksum
                }
            )

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup if it exists
            if output_path and output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise BackupError(f"Failed to create backup: {str(e)}") from e

    # =========================================================================
    # Backup Restoration
    # =========================================================================

    def restore_backup(
        self,
        backup_path: Path,
        restore_settings: bool = True,
        verify_checksum: bool = True,
        create_pre_restore_backup: bool = True
    ) -> bool:
        """
        Restore from a backup file.

        Args:
            backup_path: Path to the backup file
            restore_settings: Whether to restore settings
            verify_checksum: Whether to verify file checksums
            create_pre_restore_backup: Create a backup before restoring

        Returns:
            True if restore was successful

        Raises:
            RestoreError: If restore fails
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise RestoreError(f"Backup file not found: {backup_path}")

        if not self._database_path:
            raise RestoreError("Database path not set")

        try:
            self._report_progress(0, 100, "Starting restore...")

            # Step 1: Verify backup integrity
            self._report_progress(5, 100, "Verifying backup...")
            manifest = self._read_backup_manifest(backup_path)

            if manifest is None:
                raise RestoreError("Invalid backup file: missing manifest")

            # Step 2: Create pre-restore backup if requested
            if create_pre_restore_backup and self._database_path.exists():
                self._report_progress(10, 100, "Creating pre-restore backup...")
                try:
                    pre_restore_path = self._backup_dir / self._generate_backup_filename("pre_restore")
                    self.create_backup(pre_restore_path, include_settings=True, description="Pre-restore backup")
                except Exception as e:
                    logger.warning(f"Could not create pre-restore backup: {e}")

            self._report_progress(20, 100, "Extracting backup...")

            # Step 3: Extract and restore
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                with zipfile.ZipFile(backup_path, 'r') as zf:
                    # Validate entries to prevent Zip Slip (path traversal)
                    for member in zf.namelist():
                        member_path = (temp_path / member).resolve()
                        if not str(member_path).startswith(str(temp_path.resolve())):
                            raise RestoreError(
                                f"Zip Slip detected: '{member}' would extract outside target directory"
                            )
                    zf.extractall(temp_path)

                # Verify checksums if requested
                if verify_checksum:
                    self._report_progress(40, 100, "Verifying checksums...")

                    db_checksum = self._calculate_checksum(temp_path / self.DATABASE_FILENAME)
                    expected_checksum = manifest.get('database', {}).get('checksum')

                    if expected_checksum and db_checksum != expected_checksum:
                        raise RestoreError("Database checksum verification failed")

                    if manifest.get('settings_included') and restore_settings:
                        settings_checksum = self._calculate_checksum(temp_path / self.SETTINGS_FILENAME)
                        expected_settings_checksum = manifest.get('settings', {}).get('checksum')

                        if expected_settings_checksum and settings_checksum != expected_settings_checksum:
                            raise RestoreError("Settings checksum verification failed")

                self._report_progress(60, 100, "Restoring database...")

                # Close any existing connections (caller should handle this)
                # Restore database
                source_db = temp_path / self.DATABASE_FILENAME
                if source_db.exists():
                    # Create backup of current database
                    backup_current = None
                    if self._database_path.exists():
                        backup_current = self._database_path.with_suffix('.db.old')
                        shutil.copy2(self._database_path, backup_current)

                    # Copy restored database
                    shutil.copy2(source_db, self._database_path)

                    # Remove old backup
                    if backup_current is not None and backup_current.exists():
                        backup_current.unlink()

                self._report_progress(80, 100, "Restoring settings...")

                # Restore settings if requested
                if restore_settings and manifest.get('settings_included') and self._settings_path:
                    settings_file = temp_path / self.SETTINGS_FILENAME
                    if settings_file.exists():
                        shutil.copy2(settings_file, self._settings_path)

            self._report_progress(100, 100, "Restore complete!")

            logger.info(f"Backup restored from: {backup_path}")
            return True

        except RestoreError:
            raise
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise RestoreError(f"Failed to restore backup: {str(e)}") from e

    def _read_backup_manifest(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """Read and parse the manifest from a backup file."""
        try:
            with zipfile.ZipFile(backup_path, 'r') as zf:
                with zf.open(self.MANIFEST_FILENAME) as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read backup manifest: {e}")
            return None

    def verify_backup(self, backup_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify backup integrity without restoring.

        Args:
            backup_path: Path to the backup file

        Returns:
            Tuple of (is_valid, verification_details)
        """
        backup_path = Path(backup_path)
        details = {
            'path': str(backup_path),
            'exists': backup_path.exists(),
            'valid_zip': False,
            'has_manifest': False,
            'has_database': False,
            'checksums_valid': False,
            'version': None,
            'created_at': None,
            'errors': []
        }

        if not details['exists']:
            details['errors'].append("Backup file not found")
            return False, details

        try:
            # Check if valid ZIP
            if not zipfile.is_zipfile(backup_path):
                details['errors'].append("File is not a valid ZIP archive")
                return False, details

            details['valid_zip'] = True

            with zipfile.ZipFile(backup_path, 'r') as zf:
                # Check for required files
                namelist = zf.namelist()

                if self.MANIFEST_FILENAME in namelist:
                    details['has_manifest'] = True
                else:
                    details['errors'].append("Missing manifest file")

                if self.DATABASE_FILENAME in namelist:
                    details['has_database'] = True
                else:
                    details['errors'].append("Missing database file")

                if not details['has_manifest'] or not details['has_database']:
                    return False, details

                # Read manifest
                with zf.open(self.MANIFEST_FILENAME) as f:
                    manifest = json.load(f)

                details['version'] = manifest.get('version')
                details['created_at'] = manifest.get('created_at')

                # Extract to temp and verify checksums
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Validate entries to prevent Zip Slip (path traversal)
                    temp_dir_resolved = Path(temp_dir).resolve()
                    for member in zf.namelist():
                        member_path = (Path(temp_dir) / member).resolve()
                        if not str(member_path).startswith(str(temp_dir_resolved)):
                            return False, {**details, 'errors': details['errors'] + [
                                f"Zip Slip detected: '{member}' would extract outside target directory"
                            ]}
                    zf.extractall(temp_dir)
                    temp_path = Path(temp_dir)

                    # Verify database checksum
                    db_checksum = self._calculate_checksum(temp_path / self.DATABASE_FILENAME)
                    expected_checksum = manifest.get('database', {}).get('checksum')

                    if expected_checksum:
                        if db_checksum == expected_checksum:
                            details['checksums_valid'] = True
                        else:
                            details['errors'].append("Database checksum mismatch")
                    else:
                        details['checksums_valid'] = True  # No checksum to verify

            return len(details['errors']) == 0, details

        except Exception as e:
            details['errors'].append(str(e))
            return False, details

    # =========================================================================
    # Backup Management
    # =========================================================================

    def list_backups(
        self,
        sort_by: str = 'date',
        descending: bool = True
    ) -> List[BackupInfo]:
        """
        List all available backups.

        Args:
            sort_by: Sort field ('date', 'size', 'name')
            descending: Sort in descending order

        Returns:
            List of BackupInfo objects
        """
        backups = []

        if not self._backup_dir.exists():
            return backups

        for file_path in self._backup_dir.glob(f'*{self.BACKUP_EXTENSION}'):
            try:
                manifest = self._read_backup_manifest(file_path)
                if manifest:
                    created_at = datetime.fromisoformat(manifest.get('created_at', ''))
                    backup_info = BackupInfo(
                        path=file_path,
                        created_at=created_at,
                        size_bytes=file_path.stat().st_size,
                        version=manifest.get('version', 'unknown'),
                        checksum=self._calculate_checksum(file_path),
                        metadata={
                            'description': manifest.get('description', ''),
                            'settings_included': manifest.get('settings_included', False)
                        }
                    )
                    backups.append(backup_info)
            except Exception as e:
                logger.warning(f"Could not read backup {file_path}: {e}")
                continue

        # Sort backups
        if sort_by == 'date':
            backups.sort(key=lambda x: x.created_at, reverse=descending)
        elif sort_by == 'size':
            backups.sort(key=lambda x: x.size_bytes, reverse=descending)
        elif sort_by == 'name':
            backups.sort(key=lambda x: x.filename, reverse=descending)

        return backups

    def delete_backup(self, backup_path: Path) -> bool:
        """
        Delete a specific backup file.

        Args:
            backup_path: Path to the backup file

        Returns:
            True if deletion was successful
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            logger.warning(f"Backup not found: {backup_path}")
            return False

        try:
            backup_path.unlink()
            logger.info(f"Deleted backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    def delete_old_backups(
        self,
        keep_count: int = 5,
        keep_days: Optional[int] = None
    ) -> int:
        """
        Delete old backups, keeping the most recent ones.

        Args:
            keep_count: Number of recent backups to keep
            keep_days: Optional: Also keep backups from the last N days

        Returns:
            Number of backups deleted
        """
        backups = self.list_backups(sort_by='date', descending=True)

        if len(backups) <= keep_count:
            return 0

        deleted_count = 0
        cutoff_date = None
        if keep_days:
            cutoff_date = datetime.now() - timedelta(days=keep_days)

        for i, backup in enumerate(backups):
            # Always keep the first keep_count backups
            if i < keep_count:
                continue

            # If keep_days is set, also keep backups within that period
            if cutoff_date and backup.created_at >= cutoff_date:
                continue

            # Delete the backup
            if self.delete_backup(backup.path):
                deleted_count += 1

        logger.info(f"Deleted {deleted_count} old backups")
        return deleted_count

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about backups.

        Returns:
            Dictionary with backup statistics
        """
        backups = self.list_backups()

        if not backups:
            return {
                'total_backups': 0,
                'total_size': 0,
                'total_size_formatted': '0 B',
                'oldest_backup': None,
                'newest_backup': None,
                'average_size': 0
            }

        total_size = sum(b.size_bytes for b in backups)
        oldest = min(backups, key=lambda x: x.created_at)
        newest = max(backups, key=lambda x: x.created_at)

        return {
            'total_backups': len(backups),
            'total_size': total_size,
            'total_size_formatted': BackupInfo(
                Path(), datetime.now(), total_size, '', ''
            ).size_formatted,
            'oldest_backup': oldest.to_dict(),
            'newest_backup': newest.to_dict(),
            'average_size': total_size // len(backups) if backups else 0
        }

    # =========================================================================
    # Auto-Backup Scheduling
    # =========================================================================

    def start_auto_backup(
        self,
        interval_hours: int = 24,
        keep_count: int = 7
    ) -> None:
        """
        Start automatic scheduled backups.

        Args:
            interval_hours: Hours between backups
            keep_count: Number of auto-backups to keep
        """
        if self._auto_backup_thread and self._auto_backup_thread.is_alive():
            logger.warning("Auto-backup already running")
            return

        self._auto_backup_enabled = True
        self._auto_backup_interval_hours = interval_hours
        self._auto_backup_stop_event.clear()

        def auto_backup_worker():
            logger.info(f"Auto-backup started (interval: {interval_hours} hours)")

            while not self._auto_backup_stop_event.is_set():
                try:
                    # Create backup
                    backup_path = self._backup_dir / self._generate_backup_filename("auto")
                    self.create_backup(
                        output_path=backup_path,
                        include_settings=True,
                        description="Automatic backup"
                    )

                    # Clean up old auto-backups
                    auto_backups = [
                        b for b in self.list_backups()
                        if b.filename.startswith('auto_')
                    ]

                    if len(auto_backups) > keep_count:
                        for backup in auto_backups[keep_count:]:
                            self.delete_backup(backup.path)

                except Exception as e:
                    logger.error(f"Auto-backup failed: {e}")

                # Wait for next backup interval or stop event
                self._auto_backup_stop_event.wait(interval_hours * 3600)

        self._auto_backup_thread = Thread(target=auto_backup_worker, daemon=True)
        self._auto_backup_thread.start()

    def stop_auto_backup(self) -> None:
        """Stop automatic scheduled backups."""
        if not self._auto_backup_enabled:
            return

        self._auto_backup_enabled = False
        self._auto_backup_stop_event.set()

        if self._auto_backup_thread:
            self._auto_backup_thread.join(timeout=5)
            self._auto_backup_thread = None

        logger.info("Auto-backup stopped")

    @property
    def is_auto_backup_running(self) -> bool:
        """Check if auto-backup is currently running."""
        return (
            self._auto_backup_enabled and
            self._auto_backup_thread is not None and
            self._auto_backup_thread.is_alive()
        )

    # =========================================================================
    # Quick Backup Methods
    # =========================================================================

    def quick_backup(self, description: str = "Quick backup") -> BackupInfo:
        """
        Create a quick backup with default settings.

        Args:
            description: Backup description

        Returns:
            BackupInfo for the created backup
        """
        return self.create_backup(
            include_settings=True,
            description=description
        )

    def restore_latest(
        self,
        restore_settings: bool = True
    ) -> bool:
        """
        Restore from the most recent backup.

        Args:
            restore_settings: Whether to restore settings

        Returns:
            True if restore was successful
        """
        backups = self.list_backups(sort_by='date', descending=True)

        if not backups:
            raise RestoreError("No backups available")

        return self.restore_backup(
            backups[0].path,
            restore_settings=restore_settings
        )

    # =========================================================================
    # Export/Import for Migration
    # =========================================================================

    def export_for_migration(self, output_path: Path) -> BackupInfo:
        """
        Export backup in a portable format for migrating to another machine.

        Args:
            output_path: Path for the export file

        Returns:
            BackupInfo for the created export
        """
        return self.create_backup(
            output_path=output_path,
            include_settings=True,
            description="Migration export",
            compression_level=9  # Maximum compression for transfer
        )

    def import_from_migration(self, import_path: Path) -> bool:
        """
        Import backup from another machine.

        Args:
            import_path: Path to the import file

        Returns:
            True if import was successful
        """
        # Verify the backup first
        is_valid, details = self.verify_backup(import_path)

        if not is_valid:
            raise RestoreError(f"Invalid migration backup: {', '.join(details['errors'])}")

        return self.restore_backup(
            import_path,
            restore_settings=True,
            verify_checksum=True,
            create_pre_restore_backup=True
        )
