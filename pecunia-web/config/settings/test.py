"""
Django Test Settings.
Settings specific to running tests with SQLite.
"""
from .base import *
from .security import *  # noqa: F401, F403

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-test-key-for-testing-only'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Database - Use SQLite for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Cache (local memory for testing)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'sessions-cache',
    },
}

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Password hashers - use faster hasher for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable rate limiting in tests
RATE_LIMIT_ENABLED = False

# Stripe test settings
STRIPE_SECRET_KEY = 'sk_test_fake_key'
STRIPE_WEBHOOK_SECRET = 'whsec_test_fake_secret'
STRIPE_SUCCESS_URL = '/subscriptions/success/'
STRIPE_CANCEL_URL = '/subscriptions/cancel/'
STRIPE_PORTAL_RETURN_URL = '/account/billing/'
SITE_URL = 'http://testserver'

# Bank encryption key for testing
BANK_ENCRYPTION_KEY = 'test-encryption-key-32-bytes-xx'

# AI settings for testing
ANTHROPIC_API_KEY = 'test-api-key'
AI_MODEL = 'claude-3-sonnet-20240229'
AI_MAX_TOKENS = 1024

# Celery settings for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Logging - reduce noise in tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'apps': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
    },
}
