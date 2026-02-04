"""
Services package for Pecunia Desktop.

Provides centralized services for:
- Notifications (system tray, in-app toasts, notification center)
- Data export (CSV, Excel, PDF)
- Report generation (monthly, yearly, custom PDF reports)
- Backup and restore (database, settings, scheduled backups)
- Data import (CSV, OFX, QFX, QIF)
- System tray integration
- Background services
"""

from services.notifications import (
    # Enums
    NotificationType,
    NotificationPriority,
    NotificationCategory,

    # Data classes
    Notification,
    NotificationPreferences,

    # Widgets
    ToastNotification,

    # Service
    NotificationService,
    get_notification_service,

    # Convenience functions
    notify,
    notify_info,
    notify_success,
    notify_warning,
    notify_error,
    show_notification,
    show_system_notification,

    # Availability flags
    QT_AVAILABLE,
    PLYER_AVAILABLE,
)

from services.system_tray import (
    SystemTrayIcon,
    SystemTrayService,
    get_system_tray_service,
    TRAY_ICON_AVAILABLE,
)

from services.notification_center import (
    NotificationCenter,
    NotificationItem,
    NotificationFilter,
    get_notification_center,
)

from services.export import (
    ExportService,
    ExportError,
)

from services.reports import (
    ReportGenerator,
    ReportError,
)

from services.backup import (
    BackupService,
    BackupError,
    RestoreError,
    BackupInfo,
)

from services.import_service import (
    ImportService,
    ImportError as DataImportError,  # Renamed to avoid conflict with builtin
    ValidationError,
    ImportRecord,
    ImportResult,
)

__all__ = [
    # Notification types and enums
    "NotificationType",
    "NotificationPriority",
    "NotificationCategory",

    # Notification data classes
    "Notification",
    "NotificationPreferences",

    # Notification widgets
    "ToastNotification",

    # Notification service
    "NotificationService",
    "get_notification_service",

    # Notification convenience functions
    "notify",
    "notify_info",
    "notify_success",
    "notify_warning",
    "notify_error",
    "show_notification",
    "show_system_notification",

    # System tray
    "SystemTrayIcon",
    "SystemTrayService",
    "get_system_tray_service",
    "TRAY_ICON_AVAILABLE",

    # Notification center
    "NotificationCenter",
    "NotificationItem",
    "NotificationFilter",
    "get_notification_center",

    # Export
    "ExportService",
    "ExportError",

    # Report Generator
    "ReportGenerator",
    "ReportError",

    # Backup Service
    "BackupService",
    "BackupError",
    "RestoreError",
    "BackupInfo",

    # Import Service
    "ImportService",
    "DataImportError",
    "ValidationError",
    "ImportRecord",
    "ImportResult",

    # Availability flags
    "QT_AVAILABLE",
    "PLYER_AVAILABLE",
]


# =============================================================================
# Service Factory Functions
# =============================================================================

def get_export_service() -> ExportService:
    """Get a new ExportService instance."""
    return ExportService()


def get_report_generator() -> ReportGenerator:
    """Get a new ReportGenerator instance."""
    return ReportGenerator()


def get_backup_service(
    database_path=None,
    backup_dir=None,
    settings_path=None
) -> BackupService:
    """
    Get a new BackupService instance.

    Args:
        database_path: Path to the SQLite database file
        backup_dir: Directory for storing backups
        settings_path: Path to settings JSON file

    Returns:
        Configured BackupService instance
    """
    return BackupService(
        database_path=database_path,
        backup_dir=backup_dir,
        settings_path=settings_path
    )


def get_import_service() -> ImportService:
    """Get a new ImportService instance."""
    return ImportService()
