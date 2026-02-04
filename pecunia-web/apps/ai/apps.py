"""
AI App Configuration.
"""
from django.apps import AppConfig


class AIConfig(AppConfig):
    """Configuration for the AI application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai'
    verbose_name = 'AI Features'

    def ready(self):
        """Initialize AI services when app is ready."""
        pass
