"""
Django Settings Package.
Import from environment-specific settings module.
"""
import os

environment = os.environ.get('DJANGO_ENV', 'development')

if environment == 'production':
    from .production import *
elif environment == 'staging':
    from .staging import *
else:
    from .development import *

# Import security settings (must come after environment settings to override)
from .security import *  # noqa: F401, F403
