"""
Budgets App Configuration.
"""
from django.apps import AppConfig


class BudgetsConfig(AppConfig):
    """Configuration for the budgets application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.budgets'
    verbose_name = 'Budget Management'
