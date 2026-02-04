"""
Banking App Configuration.
"""
from django.apps import AppConfig


class BankingConfig(AppConfig):
    """Configuration for the banking application."""
    default_auto_field = 'django.db.models.UUIDField'
    name = 'apps.banking'
    verbose_name = 'Banking Connections'

    def ready(self):
        """Import signals when app is ready."""
        pass  # Signals will be added as needed
