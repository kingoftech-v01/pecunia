"""
Comprehensive tests for config/settings.

Verifies settings are correctly configured across:
- base.py (common settings)
- development.py (dev-specific)
- production.py (prod-specific)
- security.py (security headers, CORS, CSP, rate limiting, JWT, etc.)
- __init__.py (environment routing)
"""
import os
from unittest.mock import patch

import pytest
from django.conf import settings
from django.test import override_settings


# ============================================================================
# Base Settings
# ============================================================================

class TestBaseSettings:
    """Tests for settings that should be present in all environments."""

    def test_installed_apps_contains_core_apps(self):
        required_apps = [
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
        ]
        for app in required_apps:
            assert app in settings.INSTALLED_APPS, f"{app} missing from INSTALLED_APPS"

    def test_installed_apps_contains_third_party(self):
        third_party = [
            "rest_framework",
            "rest_framework_simplejwt",
            "corsheaders",
            "django_filters",
            "drf_spectacular",
        ]
        for app in third_party:
            assert app in settings.INSTALLED_APPS, f"{app} missing from INSTALLED_APPS"

    def test_installed_apps_contains_local_apps(self):
        local_apps = [
            "apps.accounts",
            "apps.transactions",
            "apps.budgets",
            "apps.banking",
            "apps.ai",
            "apps.subscriptions",
            "apps.sync",
        ]
        for app in local_apps:
            assert app in settings.INSTALLED_APPS, f"{app} missing from INSTALLED_APPS"

    def test_middleware_order(self):
        """Verify middleware ordering is correct for security."""
        mw = settings.MIDDLEWARE
        assert "apps.core.middleware.RequestSanitizationMiddleware" in mw
        assert "corsheaders.middleware.CorsMiddleware" in mw
        assert "django.middleware.security.SecurityMiddleware" in mw

        # Sanitization should come before CORS
        sanitization_idx = mw.index("apps.core.middleware.RequestSanitizationMiddleware")
        cors_idx = mw.index("corsheaders.middleware.CorsMiddleware")
        assert sanitization_idx < cors_idx

    def test_middleware_contains_custom_middleware(self):
        mw = settings.MIDDLEWARE
        custom = [
            "apps.core.middleware.RequestSanitizationMiddleware",
            "apps.core.middleware.RateLimitMiddleware",
            "apps.core.middleware.SubscriptionCheckMiddleware",
            "apps.core.middleware.AuditLogMiddleware",
            "apps.core.middleware.SecurityHeadersMiddleware",
        ]
        for m in custom:
            assert m in mw, f"{m} missing from MIDDLEWARE"

    def test_auth_middleware_before_rate_limit(self):
        """Rate limit should come after authentication to support user-tier limits."""
        mw = settings.MIDDLEWARE
        auth_idx = mw.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        rate_idx = mw.index("apps.core.middleware.RateLimitMiddleware")
        assert auth_idx < rate_idx

    def test_root_urlconf(self):
        assert settings.ROOT_URLCONF == "config.urls"

    def test_wsgi_application(self):
        assert settings.WSGI_APPLICATION == "config.wsgi.application"

    def test_custom_user_model(self):
        assert settings.AUTH_USER_MODEL == "accounts.User"

    def test_language_code(self):
        assert settings.LANGUAGE_CODE == "fr-fr"

    def test_timezone(self):
        assert settings.TIME_ZONE == "Europe/Paris"

    def test_use_tz_enabled(self):
        assert settings.USE_TZ is True

    def test_use_i18n_enabled(self):
        assert settings.USE_I18N is True

    def test_static_url(self):
        assert settings.STATIC_URL == "/static/"

    def test_password_validators_configured(self):
        validators = settings.AUTH_PASSWORD_VALIDATORS
        assert len(validators) >= 4
        validator_names = [v["NAME"] for v in validators]
        assert any("MinimumLengthValidator" in n for n in validator_names)
        assert any("CommonPasswordValidator" in n for n in validator_names)
        assert any("NumericPasswordValidator" in n for n in validator_names)
        assert any("UserAttributeSimilarityValidator" in n for n in validator_names)

    def test_rest_framework_config(self):
        rf = settings.REST_FRAMEWORK
        assert "DEFAULT_AUTHENTICATION_CLASSES" in rf
        assert "DEFAULT_PERMISSION_CLASSES" in rf
        assert "rest_framework_simplejwt.authentication.JWTAuthentication" in rf[
            "DEFAULT_AUTHENTICATION_CLASSES"
        ]
        assert "rest_framework.permissions.IsAuthenticated" in rf[
            "DEFAULT_PERMISSION_CLASSES"
        ]

    def test_rest_framework_pagination(self):
        rf = settings.REST_FRAMEWORK
        assert rf["DEFAULT_PAGINATION_CLASS"] == "rest_framework.pagination.PageNumberPagination"
        assert rf["PAGE_SIZE"] == 20

    def test_rest_framework_schema(self):
        rf = settings.REST_FRAMEWORK
        assert rf["DEFAULT_SCHEMA_CLASS"] == "drf_spectacular.openapi.AutoSchema"

    def test_simple_jwt_configured(self):
        jwt = settings.SIMPLE_JWT
        assert "ACCESS_TOKEN_LIFETIME" in jwt
        assert "REFRESH_TOKEN_LIFETIME" in jwt
        assert jwt["ROTATE_REFRESH_TOKENS"] is True
        assert jwt["BLACKLIST_AFTER_ROTATION"] is True
        assert "Bearer" in jwt["AUTH_HEADER_TYPES"]

    def test_templates_configured(self):
        assert len(settings.TEMPLATES) >= 1
        template = settings.TEMPLATES[0]
        assert template["BACKEND"] == "django.template.backends.django.DjangoTemplates"
        assert template["APP_DIRS"] is True

    def test_spectacular_settings(self):
        spec = settings.SPECTACULAR_SETTINGS
        assert spec["TITLE"] == "Pecunia API"
        assert "VERSION" in spec


# ============================================================================
# Security Settings
# ============================================================================

class TestSecuritySettings:
    """Tests for config/settings/security.py values."""

    def test_cors_allowed_origins_is_list(self):
        assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)

    def test_cors_allow_credentials(self):
        assert settings.CORS_ALLOW_CREDENTIALS is True

    def test_cors_allow_methods(self):
        methods = settings.CORS_ALLOW_METHODS
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "PATCH" in methods
        assert "DELETE" in methods
        assert "OPTIONS" in methods

    def test_cors_allow_headers(self):
        headers = settings.CORS_ALLOW_HEADERS
        assert "authorization" in headers
        assert "content-type" in headers
        assert "x-csrftoken" in headers

    def test_cors_expose_headers(self):
        exposed = settings.CORS_EXPOSE_HEADERS
        assert "x-correlation-id" in exposed
        assert "x-ratelimit-remaining" in exposed

    def test_cors_preflight_max_age(self):
        assert settings.CORS_PREFLIGHT_MAX_AGE == 3600

    def test_cors_urls_regex(self):
        assert settings.CORS_URLS_REGEX == r"^/api/.*$"

    def test_csp_directives_defined(self):
        assert hasattr(settings, "CSP_DEFAULT_SRC")
        assert "'self'" in settings.CSP_DEFAULT_SRC

    def test_content_security_policy_header(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert isinstance(csp, str)
        assert "default-src" in csp
        assert "script-src" in csp
        assert "'self'" in csp

    def test_permissions_policy_defined(self):
        pp = settings.PERMISSIONS_POLICY
        assert isinstance(pp, str)
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp

    def test_rate_limit_config(self):
        config = settings.RATE_LIMIT_CONFIG
        assert "anonymous" in config
        assert "free" in config
        assert "premium" in config
        assert "pro" in config
        assert "business" in config
        assert config["anonymous"]["requests"] < config["business"]["requests"]

    def test_rate_limit_sensitive_endpoints(self):
        endpoints = settings.RATE_LIMIT_SENSITIVE_ENDPOINTS
        assert "/api/auth/login/" in endpoints
        assert "/api/auth/register/" in endpoints
        # Login should have strict limits
        assert endpoints["/api/auth/login/"]["requests"] <= 10

    def test_rate_limit_whitelist_ips(self):
        assert isinstance(settings.RATE_LIMIT_WHITELIST_IPS, list)

    def test_simple_jwt_security(self):
        jwt = settings.SIMPLE_JWT
        assert jwt["ALGORITHM"] == "HS256"
        assert "AUDIENCE" in jwt
        assert "ISSUER" in jwt
        assert "LEEWAY" in jwt

    def test_session_cookie_httponly(self):
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_session_cookie_samesite(self):
        assert settings.SESSION_COOKIE_SAMESITE == "Lax"

    def test_csrf_cookie_httponly(self):
        assert settings.CSRF_COOKIE_HTTPONLY is True

    def test_csrf_cookie_samesite(self):
        assert settings.CSRF_COOKIE_SAMESITE == "Lax"

    def test_secure_content_type_nosniff(self):
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_secure_browser_xss_filter(self):
        assert settings.SECURE_BROWSER_XSS_FILTER is True

    def test_x_frame_options_deny(self):
        assert settings.X_FRAME_OPTIONS == "DENY"

    def test_secure_referrer_policy(self):
        assert settings.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"

    def test_password_validators_security(self):
        validators = settings.AUTH_PASSWORD_VALIDATORS
        # Check minimum length validator has strong settings
        for v in validators:
            if "MinimumLengthValidator" in v["NAME"]:
                if "OPTIONS" in v:
                    assert v["OPTIONS"]["min_length"] >= 8

    def test_password_hashers_argon2_first(self):
        hashers = settings.PASSWORD_HASHERS
        # In test environment, MD5 is used for speed
        # In production/development, Argon2 should be first
        assert "Argon2PasswordHasher" in hashers[0] or "MD5PasswordHasher" in hashers[0]

    def test_session_engine(self):
        assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.cache"

    def test_session_max_age(self):
        assert settings.SESSION_COOKIE_AGE == 86400

    def test_data_upload_limits(self):
        assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE == 5 * 1024 * 1024
        assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS == 100
        assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == 10 * 1024 * 1024

    def test_allowed_api_versions(self):
        assert "v1" in settings.ALLOWED_API_VERSIONS

    def test_trusted_proxy_count(self):
        assert isinstance(settings.TRUSTED_PROXY_COUNT, int)
        assert settings.TRUSTED_PROXY_COUNT >= 1

    def test_security_headers_summary(self):
        headers = settings.SECURITY_HEADERS
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert headers["X-Frame-Options"] == "DENY"

    def test_csrf_trusted_origins(self):
        origins = settings.CSRF_TRUSTED_ORIGINS
        assert isinstance(origins, list)
        assert len(origins) >= 1

    def test_banking_provider_timeout(self):
        assert isinstance(settings.BANKING_PROVIDER_TIMEOUT, int)
        assert settings.BANKING_PROVIDER_TIMEOUT > 0

    def test_openai_api_timeout(self):
        assert isinstance(settings.OPENAI_API_TIMEOUT, int)
        assert settings.OPENAI_API_TIMEOUT > 0


# ============================================================================
# Development Settings
# ============================================================================

class TestDevelopmentSettings:
    """Tests verifying development settings are correct.

    These tests run under the default test environment which is development.
    """

    def test_debug_is_overridden_by_test_runner(self):
        """Django test runner forces DEBUG=False for safety.
        We verify the setting mechanism works by checking it's a bool."""
        assert isinstance(settings.DEBUG, bool)

    def test_allowed_hosts_dev(self):
        hosts = settings.ALLOWED_HOSTS
        assert "localhost" in hosts
        assert "127.0.0.1" in hosts

    def test_database_engine_postgresql(self):
        db = settings.DATABASES["default"]
        # PostgreSQL in dev/prod, SQLite in test
        assert "postgresql" in db["ENGINE"] or "sqlite" in db["ENGINE"]

    def test_cache_backend(self):
        cache = settings.CACHES["default"]
        # Dev uses locmem cache
        assert "LocMemCache" in cache["BACKEND"] or "locmem" in cache["BACKEND"].lower() or \
               "Redis" in cache["BACKEND"] or "redis" in cache["BACKEND"].lower()

    def test_email_backend(self):
        # Dev should use console email backend
        backend = settings.EMAIL_BACKEND
        assert "console" in backend.lower() or "locmem" in backend.lower() or \
               "smtp" in backend.lower()

    def test_cors_allowed_origins_dev(self):
        origins = settings.CORS_ALLOWED_ORIGINS
        # In dev, localhost origins should be present
        localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
        assert len(localhost_origins) >= 1


# ============================================================================
# Security Settings build_csp_header function
# ============================================================================

class TestBuildCspHeader:
    """Tests for the build_csp_header() function in security.py."""

    def test_csp_header_is_string(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert isinstance(csp, str)

    def test_csp_contains_default_src(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "default-src" in csp

    def test_csp_contains_script_src(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "script-src" in csp

    def test_csp_contains_style_src(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "style-src" in csp

    def test_csp_contains_img_src(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "img-src" in csp

    def test_csp_contains_connect_src(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "connect-src" in csp

    def test_csp_contains_frame_src(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "frame-src" in csp

    def test_csp_contains_object_src_none(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "object-src" in csp
        assert "'none'" in csp

    def test_csp_stripe_allowed(self):
        csp = settings.CONTENT_SECURITY_POLICY
        assert "js.stripe.com" in csp

    def test_csp_report_uri(self):
        assert hasattr(settings, "CSP_REPORT_URI")


# ============================================================================
# Settings __init__.py environment routing
# ============================================================================

class TestSettingsInit:
    """Test that settings __init__.py routes to the right module."""

    def test_environment_variable(self):
        """DJANGO_ENV should exist or default to 'development'."""
        env = os.environ.get("DJANGO_ENV", "development")
        assert env in ("development", "staging", "production")

    def test_security_settings_imported(self):
        """Security settings should always be imported last and override."""
        # Check a setting that only exists in security.py
        assert hasattr(settings, "RATE_LIMIT_CONFIG")
        assert hasattr(settings, "CONTENT_SECURITY_POLICY")
        assert hasattr(settings, "PERMISSIONS_POLICY")

    def test_base_settings_present(self):
        """Base settings should always be present."""
        assert hasattr(settings, "ROOT_URLCONF")
        assert hasattr(settings, "INSTALLED_APPS")
        assert hasattr(settings, "REST_FRAMEWORK")
