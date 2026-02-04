"""
Accounts App Configuration.
"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the accounts application."""
    default_auto_field = 'django.db.models.UUIDField'
    name = 'apps.accounts'
    verbose_name = 'User Accounts'

    def ready(self):
        """Import signals when app is ready."""
        import apps.accounts.signals  # noqa: F401
