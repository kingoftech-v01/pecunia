"""
Security Settings.

Comprehensive security configuration following OWASP Top 10 guidelines.
This file contains settings for CORS, CSP, rate limiting, JWT, and other security measures.
"""
import os
from datetime import timedelta


# =============================================================================
# Environment Detection
# =============================================================================

ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_STAGING = ENVIRONMENT == 'staging'
IS_DEVELOPMENT = ENVIRONMENT == 'development'


# =============================================================================
# CORS Configuration
# =============================================================================
# OWASP A01:2021 - Broken Access Control

# Allowed origins for CORS requests
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
] or [
    'https://pecunia.fr',
    'https://www.pecunia.fr',
    'https://app.pecunia.fr',
]

# Additional origins for development
if IS_DEVELOPMENT:
    CORS_ALLOWED_ORIGINS.extend([
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
    ])

# Allowed origin regex patterns (for subdomains)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://.*\.pecunia\.fr$',
]

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Allowed HTTP methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Allowed request headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-correlation-id',
]

# Headers exposed to the browser
CORS_EXPOSE_HEADERS = [
    'content-disposition',
    'x-correlation-id',
    'x-ratelimit-remaining',
    'x-ratelimit-reset',
]

# Preflight cache duration (1 hour)
CORS_PREFLIGHT_MAX_AGE = 3600

# Restrict CORS to API paths only
CORS_URLS_REGEX = r'^/api/.*$'


# =============================================================================
# Content Security Policy (CSP)
# =============================================================================
# OWASP A03:2021 - Injection (XSS protection)

# CSP Directives
CSP_DEFAULT_SRC = ("'self'",)

CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'" if IS_DEVELOPMENT else "",  # Only for dev
    "https://js.stripe.com",
    "https://cdn.jsdelivr.net",
)

CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",  # Required for many CSS frameworks
    "https://fonts.googleapis.com",
    "https://cdn.jsdelivr.net",
)

CSP_FONT_SRC = (
    "'self'",
    "https://fonts.gstatic.com",
    "data:",
)

CSP_IMG_SRC = (
    "'self'",
    "data:",
    "blob:",
    "https:",  # Allow images from HTTPS sources
)

CSP_CONNECT_SRC = (
    "'self'",
    "https://api.stripe.com",
    "https://api.openai.com",
    "https://*.pecunia.fr",
    "wss://*.pecunia.fr",  # WebSocket connections
)

CSP_FRAME_SRC = (
    "'self'",
    "https://js.stripe.com",
    "https://hooks.stripe.com",
)

CSP_OBJECT_SRC = ("'none'",)

CSP_BASE_URI = ("'self'",)

CSP_FORM_ACTION = ("'self'",)

CSP_FRAME_ANCESTORS = ("'self'",)

# Report URI for CSP violations
CSP_REPORT_URI = os.environ.get('CSP_REPORT_URI', '/api/security/csp-report/')

# Build CSP header string
def build_csp_header():
    """Build Content-Security-Policy header string."""
    directives = {
        'default-src': CSP_DEFAULT_SRC,
        'script-src': CSP_SCRIPT_SRC,
        'style-src': CSP_STYLE_SRC,
        'font-src': CSP_FONT_SRC,
        'img-src': CSP_IMG_SRC,
        'connect-src': CSP_CONNECT_SRC,
        'frame-src': CSP_FRAME_SRC,
        'object-src': CSP_OBJECT_SRC,
        'base-uri': CSP_BASE_URI,
        'form-action': CSP_FORM_ACTION,
        'frame-ancestors': CSP_FRAME_ANCESTORS,
    }

    if CSP_REPORT_URI:
        directives['report-uri'] = (CSP_REPORT_URI,)

    parts = []
    for directive, values in directives.items():
        filtered_values = [v for v in values if v]
        if filtered_values:
            parts.append(f"{directive} {' '.join(filtered_values)}")

    return '; '.join(parts)

CONTENT_SECURITY_POLICY = build_csp_header()

# Report-only mode for testing (doesn't block, only reports)
CSP_REPORT_ONLY = IS_DEVELOPMENT


# =============================================================================
# Permissions Policy (formerly Feature-Policy)
# =============================================================================
# OWASP A05:2021 - Security Misconfiguration

PERMISSIONS_POLICY = (
    "accelerometer=(), "
    "ambient-light-sensor=(), "
    "autoplay=(), "
    "battery=(), "
    "camera=(), "
    "cross-origin-isolated=(), "
    "display-capture=(), "
    "document-domain=(), "
    "encrypted-media=(), "
    "execution-while-not-rendered=(), "
    "execution-while-out-of-viewport=(), "
    "fullscreen=(self), "
    "geolocation=(), "
    "gyroscope=(), "
    "keyboard-map=(), "
    "magnetometer=(), "
    "microphone=(), "
    "midi=(), "
    "navigation-override=(), "
    "payment=(self 'https://js.stripe.com'), "
    "picture-in-picture=(), "
    "publickey-credentials-get=(), "
    "screen-wake-lock=(), "
    "sync-xhr=(), "
    "usb=(), "
    "web-share=(), "
    "xr-spatial-tracking=()"
)


# =============================================================================
# Rate Limiting Configuration
# =============================================================================
# OWASP A04:2021 - Insecure Design

# Default rate limits by tier (requests per window)
RATE_LIMIT_CONFIG = {
    'anonymous': {'requests': 60, 'window': 60},      # 60 req/min
    'free': {'requests': 120, 'window': 60},          # 120 req/min
    'premium': {'requests': 300, 'window': 60},       # 300 req/min
    'pro': {'requests': 600, 'window': 60},           # 600 req/min
    'business': {'requests': 1200, 'window': 60},     # 1200 req/min
}

# Stricter limits for sensitive endpoints
RATE_LIMIT_SENSITIVE_ENDPOINTS = {
    '/api/auth/login/': {'requests': 5, 'window': 60},
    '/api/auth/register/': {'requests': 3, 'window': 60},
    '/api/auth/password-reset/': {'requests': 3, 'window': 300},
    '/api/auth/password-reset/confirm/': {'requests': 5, 'window': 300},
    '/api/auth/verify-email/': {'requests': 5, 'window': 60},
    '/api/auth/resend-verification/': {'requests': 3, 'window': 300},
    '/api/banking/connect/': {'requests': 10, 'window': 300},
    '/api/subscriptions/webhook/': {'requests': 100, 'window': 60},
}

# Whitelisted IPs (internal services, health checks)
RATE_LIMIT_WHITELIST_IPS = [
    ip.strip()
    for ip in os.environ.get('RATE_LIMIT_WHITELIST_IPS', '').split(',')
    if ip.strip()
] or [
    '127.0.0.1',
    '::1',
]

# Add load balancer/proxy IPs in production
if IS_PRODUCTION:
    RATE_LIMIT_WHITELIST_IPS.extend([
        # Add your load balancer IPs here
    ])

# Enable/disable rate limiting
RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true'


# =============================================================================
# JWT Settings (Extended)
# =============================================================================
# OWASP A02:2021 - Cryptographic Failures
# OWASP A07:2021 - Identification and Authentication Failures

SIMPLE_JWT = {
    # Token lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.environ.get('JWT_ACCESS_TOKEN_MINUTES', '60'))
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.environ.get('JWT_REFRESH_TOKEN_DAYS', '7'))
    ),

    # Token rotation and blacklisting
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    # Signing algorithm
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.environ.get('JWT_SIGNING_KEY', os.environ.get('SECRET_KEY', '')),
    'VERIFYING_KEY': None,

    # Token validation
    'AUDIENCE': os.environ.get('JWT_AUDIENCE', 'pecunia-api'),
    'ISSUER': os.environ.get('JWT_ISSUER', 'pecunia'),
    'JWK_URL': None,
    'LEEWAY': timedelta(seconds=30),  # Clock skew tolerance

    # Header configuration
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # Authentication rule
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    # Token types
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    # JTI (JWT ID) claim
    'JTI_CLAIM': 'jti',

    # Sliding token configuration (if using sliding tokens)
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

# Shorter token lifetime in production for security
if IS_PRODUCTION:
    SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(minutes=30)
    SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(days=1)


# =============================================================================
# Django Security Settings
# =============================================================================
# OWASP A05:2021 - Security Misconfiguration

# HTTPS settings
SECURE_SSL_REDIRECT = IS_PRODUCTION
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000 if IS_PRODUCTION else 0  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = IS_PRODUCTION
SECURE_HSTS_PRELOAD = IS_PRODUCTION

# Cookie settings
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_NAME = '__Secure-sessionid' if IS_PRODUCTION else 'sessionid'

CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = '__Secure-csrftoken' if IS_PRODUCTION else 'csrftoken'

# Trusted origins for CSRF
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
] or [
    'https://pecunia.fr',
    'https://www.pecunia.fr',
    'https://app.pecunia.fr',
]

if IS_DEVELOPMENT:
    CSRF_TRUSTED_ORIGINS.extend([
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
    ])

# Content type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# XSS Filter (legacy browsers)
SECURE_BROWSER_XSS_FILTER = True

# Clickjacking protection
X_FRAME_OPTIONS = 'DENY'

# Referrer policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# =============================================================================
# Password Security
# =============================================================================
# OWASP A07:2021 - Identification and Authentication Failures

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # NIST recommends 8+, we use 12 for better security
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # Most secure
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]


# =============================================================================
# Session Security
# =============================================================================
# OWASP A07:2021 - Identification and Authentication Failures

# Session engine (use cache for performance, db for persistence)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# Session expiry
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # Extend session on each request

# Maximum sessions per user (requires custom middleware)
MAX_SESSIONS_PER_USER = int(os.environ.get('MAX_SESSIONS_PER_USER', '5'))


# =============================================================================
# Logging Configuration (Security-focused)
# =============================================================================
# OWASP A09:2021 - Security Logging and Monitoring Failures

SECURITY_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'security': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.environ.get('SECURITY_LOG_FILE', '/var/log/pecunia/security.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.environ.get('AUDIT_LOG_FILE', '/var/log/pecunia/audit.log'),
            'maxBytes': 52428800,  # 50MB
            'backupCount': 30,
            'formatter': 'json',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'security',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}


# =============================================================================
# Encryption Keys
# =============================================================================
# OWASP A02:2021 - Cryptographic Failures

# Bank data encryption key (Fernet)
BANK_ENCRYPTION_KEY = os.environ.get('BANK_ENCRYPTION_KEY')
if not BANK_ENCRYPTION_KEY and IS_PRODUCTION:
    raise ValueError("BANK_ENCRYPTION_KEY must be set in production")

# API key encryption
API_KEY_ENCRYPTION_KEY = os.environ.get('API_KEY_ENCRYPTION_KEY')


# =============================================================================
# IP and Geolocation Security
# =============================================================================

# Trusted proxy headers
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Number of proxies in front of the app
TRUSTED_PROXY_COUNT = int(os.environ.get('TRUSTED_PROXY_COUNT', '1'))

# Block known malicious IPs (updated regularly)
BLOCKED_IPS = [
    ip.strip()
    for ip in os.environ.get('BLOCKED_IPS', '').split(',')
    if ip.strip()
]


# =============================================================================
# API Security
# =============================================================================

# Allowed API versions
ALLOWED_API_VERSIONS = ['v1']

# API request size limits
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Throttle classes for DRF
REST_FRAMEWORK_THROTTLE_RATES = {
    'anon': '60/minute',
    'user': '120/minute',
    'premium': '300/minute',
    'burst': '10/second',
}


# =============================================================================
# Third-party Service Security
# =============================================================================

# Stripe webhook secret
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Banking providers timeout
BANKING_PROVIDER_TIMEOUT = int(os.environ.get('BANKING_PROVIDER_TIMEOUT', '30'))

# OpenAI API timeout
OPENAI_API_TIMEOUT = int(os.environ.get('OPENAI_API_TIMEOUT', '60'))


# =============================================================================
# Security Headers Summary
# =============================================================================
# These headers are added by SecurityHeadersMiddleware

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': CONTENT_SECURITY_POLICY,
    'Permissions-Policy': PERMISSIONS_POLICY,
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload' if IS_PRODUCTION else '',
}
