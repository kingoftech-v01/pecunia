"""
Subscriptions App Configuration.
"""
from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    """Configuration for the subscriptions application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.subscriptions'
    verbose_name = 'Subscriptions & Billing'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.subscriptions.signals  # noqa: F401
        except ImportError:
            pass
