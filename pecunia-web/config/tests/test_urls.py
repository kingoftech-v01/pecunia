"""
Comprehensive tests for config/urls.py.

Verifies:
- All URL patterns resolve correctly
- API v1 namespace and routes
- Admin URLs
- API documentation URLs (require admin auth)
- Landing and frontend patterns
- AuthenticatedSchemaView / AuthenticatedSwaggerView permission classes
"""
from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings
from django.urls import resolve, reverse, NoReverseMatch
from rest_framework.permissions import IsAdminUser

from config.urls import AuthenticatedSchemaView, AuthenticatedSwaggerView


# ============================================================================
# URL Pattern Resolution
# ============================================================================

class TestURLResolution:
    """Test that key URL patterns exist and resolve."""

    def test_admin_url_resolves(self):
        """Admin URL should resolve."""
        match = resolve("/admin/")
        assert match is not None

    def test_api_schema_url_resolves(self):
        """API schema URL should resolve."""
        match = resolve("/api/schema/")
        assert match is not None

    def test_api_docs_url_resolves(self):
        """API docs URL should resolve."""
        match = resolve("/api/docs/")
        assert match is not None

    def test_api_v1_accounts_resolves(self):
        """API v1 accounts URL should resolve."""
        match = resolve("/api/v1/accounts/")
        assert match is not None

    def test_api_v1_transactions_resolves(self):
        """API v1 transactions URL should resolve."""
        match = resolve("/api/v1/transactions/")
        assert match is not None

    def test_api_v1_budgets_resolves(self):
        """API v1 budgets URL should resolve."""
        match = resolve("/api/v1/budgets/")
        assert match is not None

    def test_api_v1_banking_resolves(self):
        """API v1 banking URL should resolve."""
        match = resolve("/api/v1/banking/")
        assert match is not None

    def test_api_v1_ai_resolves(self):
        """API v1 AI sub-pattern should resolve (no root pattern)."""
        match = resolve("/api/v1/ai/recommendations/")
        assert match is not None

    def test_api_v1_subscriptions_resolves(self):
        """API v1 subscriptions URL should resolve."""
        match = resolve("/api/v1/subscriptions/")
        assert match is not None

    def test_api_v1_sync_resolves(self):
        """API v1 sync URL should resolve."""
        match = resolve("/api/v1/sync/")
        assert match is not None

    def test_api_v1_dashboard_resolves(self):
        """API v1 dashboard sub-pattern should resolve (no root pattern)."""
        match = resolve("/api/v1/dashboard/summary/")
        assert match is not None


# ============================================================================
# Namespace Tests
# ============================================================================

class TestURLNamespaces:
    """Test URL namespaces are correctly configured."""

    def test_api_v1_namespace(self):
        """API v1 patterns should have the api-v1 namespace."""
        match = resolve("/api/v1/accounts/")
        assert match.namespace.startswith("api-v1")

    def test_schema_url_name(self):
        """Schema URL should have the name 'schema'."""
        url = reverse("schema")
        assert "/api/schema/" in url

    def test_swagger_ui_name(self):
        """Swagger UI URL should have the name 'swagger-ui'."""
        url = reverse("swagger-ui")
        assert "/api/docs/" in url

    def test_accounts_namespace(self):
        match = resolve("/api/v1/accounts/")
        assert "accounts" in match.namespace

    def test_transactions_namespace(self):
        match = resolve("/api/v1/transactions/")
        assert "transactions" in match.namespace

    def test_budgets_namespace(self):
        match = resolve("/api/v1/budgets/")
        assert "budgets" in match.namespace

    def test_banking_namespace(self):
        match = resolve("/api/v1/banking/")
        assert "banking" in match.namespace

    def test_ai_namespace(self):
        match = resolve("/api/v1/ai/recommendations/")
        assert "ai" in match.namespace

    def test_subscriptions_namespace(self):
        match = resolve("/api/v1/subscriptions/")
        assert "subscriptions" in match.namespace

    def test_sync_namespace(self):
        match = resolve("/api/v1/sync/")
        assert "sync" in match.namespace

    def test_dashboard_namespace(self):
        match = resolve("/api/v1/dashboard/summary/")
        assert "dashboard" in match.namespace


# ============================================================================
# Authenticated Views
# ============================================================================

class TestAuthenticatedViews:
    """Test that schema/docs views require admin authentication."""

    def test_schema_view_requires_admin(self):
        assert IsAdminUser in AuthenticatedSchemaView.permission_classes

    def test_swagger_view_requires_admin(self):
        assert IsAdminUser in AuthenticatedSwaggerView.permission_classes

    def test_schema_view_is_subclass_of_spectacular(self):
        from drf_spectacular.views import SpectacularAPIView
        assert issubclass(AuthenticatedSchemaView, SpectacularAPIView)

    def test_swagger_view_is_subclass_of_spectacular(self):
        from drf_spectacular.views import SpectacularSwaggerView
        assert issubclass(AuthenticatedSwaggerView, SpectacularSwaggerView)


# ============================================================================
# API v1 pattern contents
# ============================================================================

class TestAPIV1Patterns:
    """Test that all expected API v1 sub-patterns are present."""

    def test_all_api_apps_included(self):
        """All expected app URLs should be included under api/v1/.

        Some apps (ai, dashboard) do not have a root pattern, so we test
        a known sub-path instead.
        """
        # Apps with a root list URL
        root_prefixes = [
            "accounts",
            "transactions",
            "budgets",
            "banking",
            "subscriptions",
            "sync",
        ]
        for prefix in root_prefixes:
            match = resolve(f"/api/v1/{prefix}/")
            assert match is not None, f"/api/v1/{prefix}/ did not resolve"

        # Apps with only sub-path URLs
        match = resolve("/api/v1/ai/recommendations/")
        assert match is not None, "/api/v1/ai/recommendations/ did not resolve"
        match = resolve("/api/v1/dashboard/summary/")
        assert match is not None, "/api/v1/dashboard/summary/ did not resolve"


# ============================================================================
# Landing / Frontend patterns
# ============================================================================

class TestLandingAndFrontendPatterns:
    """Test landing page (root) and frontend (app/) patterns."""

    def test_root_url_resolves(self):
        """Root URL should resolve to landing page."""
        match = resolve("/")
        assert match is not None

    def test_frontend_accounts_resolves(self):
        match = resolve("/app/accounts/")
        assert match is not None

    def test_frontend_transactions_resolves(self):
        match = resolve("/app/transactions/")
        assert match is not None

    def test_frontend_subscriptions_resolves(self):
        match = resolve("/app/subscriptions/")
        assert match is not None

    def test_frontend_dashboard_resolves(self):
        match = resolve("/app/dashboard/")
        assert match is not None

    def test_landing_features_resolves(self):
        match = resolve("/features/")
        assert match is not None

    def test_landing_pricing_resolves(self):
        match = resolve("/pricing/")
        assert match is not None

    def test_landing_about_resolves(self):
        match = resolve("/about/")
        assert match is not None

    def test_landing_contact_resolves(self):
        match = resolve("/contact/")
        assert match is not None

    def test_landing_privacy_resolves(self):
        match = resolve("/privacy/")
        assert match is not None

    def test_landing_terms_resolves(self):
        match = resolve("/terms/")
        assert match is not None

    def test_frontend_patterns_are_namespaced(self):
        """Frontend patterns should be under the 'frontend' namespace."""
        match = resolve("/app/accounts/")
        assert "frontend" in match.namespace

    def test_landing_namespace(self):
        """Landing pages should be under the 'landing' namespace."""
        match = resolve("/")
        assert "landing" in match.namespace
