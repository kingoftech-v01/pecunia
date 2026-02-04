"""
Transactions App Configuration.
"""
from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    """Configuration for the transactions application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.transactions'
    verbose_name = 'Transactions'
