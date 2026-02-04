"""
Sync App Configuration.
"""
from django.apps import AppConfig


class SyncConfig(AppConfig):
    """Configuration for the sync application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sync'
    verbose_name = 'Data Synchronization'

    def ready(self):
        """Initialize app when ready."""
        pass
