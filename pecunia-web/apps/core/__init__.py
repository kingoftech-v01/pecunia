"""
Core application for pecunia-web.

This module initializes the core app and ensures Celery is loaded
when Django starts.
"""

# Import Celery app to ensure it's loaded when Django starts
# This will make sure that shared_task decorator uses this app
default_app_config = 'apps.core.apps.CoreConfig'


def get_celery_app():
    """
    Get the Celery application instance.

    Returns:
        Celery: The configured Celery application.
    """
    from config.celery import app as celery_app
    return celery_app


# Expose celery_app at module level for convenience
# This allows: from apps.core import celery_app
try:
    from config.celery import app as celery_app
    __all__ = ('celery_app', 'get_celery_app')
except ImportError:
    # During initial setup, celery might not be configured yet
    __all__ = ('get_celery_app',)
