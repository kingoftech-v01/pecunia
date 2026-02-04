"""
Django AppConfig for the core application.

This configuration handles app initialization and Celery integration.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    """
    Configuration class for the core Django application.

    This app serves as the central hub for:
    - Celery task management
    - Background job processing
    - Scheduled tasks (via Celery Beat)
    - System-wide utilities
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core Application'

    def ready(self):
        """
        Initialize the core application.

        This method is called when Django starts and is responsible for:
        - Loading Celery configuration
        - Registering signal handlers
        - Importing task modules to ensure they're registered
        """
        self._setup_celery()
        self._register_signals()
        self._import_tasks()
        logger.info("Core application initialized successfully")

    def _setup_celery(self):
        """
        Initialize Celery integration with Django.

        Ensures the Celery app is properly configured and ready to use.
        """
        try:
            # Import celery app to ensure it's initialized
            from config.celery import app as celery_app

            # Log Celery configuration status
            logger.debug(
                f"Celery app configured: broker={celery_app.conf.broker_url}"
            )
        except ImportError as e:
            logger.warning(
                f"Celery not configured: {e}. "
                "Background tasks will not be available."
            )
        except Exception as e:
            logger.error(f"Error initializing Celery: {e}")

    def _register_signals(self):
        """
        Register Django signal handlers for the core app.

        Signal handlers are used for:
        - Triggering background tasks on model changes
        - Logging important events
        - Cache invalidation
        """
        try:
            # Import signal handlers
            # from apps.core import signals  # noqa: F401
            logger.debug("Core signal handlers registered")
        except ImportError:
            logger.debug("No signal handlers to register")

    def _import_tasks(self):
        """
        Import Celery tasks to ensure they're registered.

        This ensures all tasks are discoverable by Celery workers.
        """
        try:
            # Import tasks module to register all tasks
            from apps.core import tasks  # noqa: F401

            logger.debug("Celery tasks imported and registered")
        except ImportError as e:
            logger.warning(f"Could not import tasks: {e}")
        except Exception as e:
            logger.error(f"Error importing tasks: {e}")
