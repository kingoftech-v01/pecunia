"""
Dashboard Application Configuration.
"""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Configuration for the Dashboard app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = 'Dashboard'

    def ready(self):
        """Initialize app when Django starts."""
        pass
