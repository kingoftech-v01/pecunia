"""
Comprehensive tests for apps.core.permissions.

Covers all DRF permission classes:
- BaseSubscriptionPermission
- IsSubscribed, IsPremiumUser, IsProUser, IsBusinessUser
- CanAccessBankingFeature, CanAccessAIFeatures, CanExportData, CanAccessAPIFeature
- IsOwnerOrReadOnly, IsOwner, IsOwnerOrAdmin
- WithinBankAccountLimit, WithinBudgetLimit, WithinCategoryLimit
- CanManageBankConnection
- IsEmailVerified, IsSameUser, ReadOnly
- SubscriptionPermissionMixin, OwnerPermissionMixin
"""
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.test import RequestFactory, override_settings
from rest_framework.permissions import SAFE_METHODS
from rest_framework.test import APIRequestFactory

from apps.core.permissions import (
    BaseSubscriptionPermission,
    IsSubscribed,
    IsPremiumUser,
    IsProUser,
    IsBusinessUser,
    CanAccessBankingFeature,
    CanAccessAIFeatures,
    CanExportData,
    CanAccessAPIFeature,
    IsOwnerOrReadOnly,
    IsOwner,
    IsOwnerOrAdmin,
    WithinBankAccountLimit,
    WithinBudgetLimit,
    WithinCategoryLimit,
    CanManageBankConnection,
    IsEmailVerified,
    IsSameUser,
    ReadOnly,
    SubscriptionPermissionMixin,
    OwnerPermissionMixin,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_anon_user():
    user = MagicMock()
    user.is_authenticated = False
    user.id = None
    user.is_staff = False
    user.is_superuser = False
    return user


def _make_auth_user(user_id=1, tier="free", is_staff=False, is_superuser=False,
                    is_email_verified=True):
    user = MagicMock()
    user.is_authenticated = True
    user.id = user_id
    user.subscription_tier = tier
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.is_email_verified = is_email_verified
    return user


def _make_request(method="GET", user=None, path="/api/test/", query_params=None,
                  kwargs=None):
    """Build a DRF-like request mock."""
    request = MagicMock()
    request.method = method
    request.user = user or _make_anon_user()
    request.path = path
    request.query_params = query_params or {}
    return request


def _make_view(kwargs=None):
    view = MagicMock()
    view.kwargs = kwargs or {}
    return view


def _make_obj(user=None, owner=None):
    obj = MagicMock(spec=[])
    if user is not None:
        obj.user = user
    if owner is not None:
        obj.owner = owner
    return obj


@pytest.fixture
def api_rf():
    return APIRequestFactory()


# ============================================================================
# BaseSubscriptionPermission
# ============================================================================

class TestBaseSubscriptionPermission:
    """Tests for BaseSubscriptionPermission base class."""

    def _make_perm(self):
        return BaseSubscriptionPermission()

    # --- get_subscription_info ---

    def test_anonymous_user_info(self):
        perm = self._make_perm()
        user = _make_anon_user()
        info = perm.get_subscription_info(user)
        assert info["is_active"] is False
        assert info["tier"] is None

    @patch("apps.core.permissions.cache")
    def test_cached_subscription_info(self, mock_cache):
        perm = self._make_perm()
        cached = {"is_active": True, "tier": "premium", "status": "active",
                  "is_trialing": False, "features": {}, "limits": {}}
        mock_cache.get.return_value = cached
        user = _make_auth_user()
        info = perm.get_subscription_info(user)
        assert info == cached

    @patch("apps.core.permissions.cache")
    def test_subscription_info_fallback_on_exception(self, mock_cache):
        """When Subscription model import fails, use fallback."""
        mock_cache.get.return_value = None
        perm = self._make_perm()
        user = _make_auth_user(tier="pro")
        with patch.dict("sys.modules", {"apps.subscriptions.models": None}):
            info = perm.get_subscription_info(user)
        assert info["is_active"] is True
        assert info["tier"] == "pro"
        assert info["status"] == "active"
        mock_cache.set.assert_called_once()

    @patch("apps.core.permissions.cache")
    def test_subscription_info_no_subscription(self, mock_cache):
        """User with no Subscription object gets free tier info."""
        mock_cache.get.return_value = None
        perm = self._make_perm()
        user = _make_auth_user()

        mock_subscription_module = MagicMock()
        mock_subscription_module.Subscription.objects.select_related.return_value.filter.return_value.first.return_value = None
        with patch.dict("sys.modules", {"apps.subscriptions.models": mock_subscription_module}):
            with patch("apps.core.permissions.cache", mock_cache):
                info = perm.get_subscription_info(user)
        assert info["tier"] == "free"
        assert info["is_active"] is True

    # --- invalidate_subscription_cache ---

    @patch("apps.core.permissions.cache")
    def test_invalidate_subscription_cache(self, mock_cache):
        BaseSubscriptionPermission.invalidate_subscription_cache(42)
        mock_cache.delete.assert_called_once_with("subscription_perm:42")

    # --- _extract_features ---

    def test_extract_features(self):
        perm = self._make_perm()
        plan = MagicMock()
        plan.ai_categorization = True
        plan.ai_insights = False
        plan.export_csv = True
        plan.bank_sync = False
        features = perm._extract_features(plan)
        assert features["ai_categorization"] is True
        assert features["ai_insights"] is False
        assert features["export_csv"] is True
        assert features["bank_sync"] is False

    def test_extract_features_missing_attrs(self):
        perm = self._make_perm()
        plan = MagicMock(spec=[])
        features = perm._extract_features(plan)
        # All should default to False
        for v in features.values():
            assert v is False

    # --- _extract_limits ---

    def test_extract_limits(self):
        perm = self._make_perm()
        plan = MagicMock()
        plan.max_bank_accounts = 5
        plan.max_budgets = 10
        plan.max_transactions_per_month = 1000
        plan.max_categories = 50
        plan.max_family_members = 3
        limits = perm._extract_limits(plan)
        assert limits["max_bank_accounts"] == 5
        assert limits["max_family_members"] == 3

    def test_extract_limits_missing_attrs(self):
        perm = self._make_perm()
        plan = MagicMock(spec=[])
        limits = perm._extract_limits(plan)
        for v in limits.values():
            assert v == 0

    # --- _get_free_tier_info ---

    def test_free_tier_info(self):
        perm = self._make_perm()
        info = perm._get_free_tier_info()
        assert info["tier"] == "free"
        assert info["is_active"] is True
        assert info["features"]["ai_categorization"] is False
        assert info["limits"]["max_bank_accounts"] == 1

    # --- _get_anonymous_info ---

    def test_anonymous_info(self):
        perm = self._make_perm()
        info = perm._get_anonymous_info()
        assert info["is_active"] is False
        assert info["tier"] is None

    # --- get_tier_level ---

    def test_get_tier_level_known(self):
        perm = self._make_perm()
        assert perm.get_tier_level("free") == 0
        assert perm.get_tier_level("premium") == 1
        assert perm.get_tier_level("pro") == 2
        assert perm.get_tier_level("business") == 3

    def test_get_tier_level_unknown(self):
        perm = self._make_perm()
        assert perm.get_tier_level("nonexistent") == 0

    # --- has_minimum_tier ---

    def test_has_minimum_tier_pass(self):
        perm = self._make_perm()
        user = _make_auth_user(tier="pro")
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "pro", "features": {}, "limits": {}
        }):
            assert perm.has_minimum_tier(user, "premium") is True

    def test_has_minimum_tier_fail(self):
        perm = self._make_perm()
        user = _make_auth_user(tier="free")
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "free", "features": {}, "limits": {}
        }):
            assert perm.has_minimum_tier(user, "premium") is False

    def test_has_minimum_tier_inactive(self):
        perm = self._make_perm()
        user = _make_auth_user(tier="business")
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": False, "tier": "business", "features": {}, "limits": {}
        }):
            assert perm.has_minimum_tier(user, "free") is False

    def test_has_minimum_tier_equal(self):
        perm = self._make_perm()
        user = _make_auth_user(tier="premium")
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "premium", "features": {}, "limits": {}
        }):
            assert perm.has_minimum_tier(user, "premium") is True

    # --- has_feature ---

    def test_has_feature_true(self):
        perm = self._make_perm()
        user = _make_auth_user()
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "premium",
            "features": {"bank_sync": True}, "limits": {}
        }):
            assert perm.has_feature(user, "bank_sync") is True

    def test_has_feature_false(self):
        perm = self._make_perm()
        user = _make_auth_user()
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "free",
            "features": {"bank_sync": False}, "limits": {}
        }):
            assert perm.has_feature(user, "bank_sync") is False

    def test_has_feature_inactive(self):
        perm = self._make_perm()
        user = _make_auth_user()
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": False, "tier": "premium",
            "features": {"bank_sync": True}, "limits": {}
        }):
            assert perm.has_feature(user, "bank_sync") is False

    def test_has_feature_missing(self):
        perm = self._make_perm()
        user = _make_auth_user()
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "free",
            "features": {}, "limits": {}
        }):
            assert perm.has_feature(user, "nonexistent") is False

    # --- check_limit ---

    def test_check_limit_within(self):
        perm = self._make_perm()
        user = _make_auth_user()
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "premium",
            "features": {}, "limits": {"max_budgets": 10}
        }):
            assert perm.check_limit(user, "max_budgets", 5) is True

    def test_check_limit_exceeded(self):
        perm = self._make_perm()
        user = _make_auth_user()
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "free",
            "features": {}, "limits": {"max_budgets": 3}
        }):
            assert perm.check_limit(user, "max_budgets", 3) is False

    def test_check_limit_missing_limit(self):
        perm = self._make_perm()
        user = _make_auth_user()
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "tier": "free",
            "features": {}, "limits": {}
        }):
            # Default limit is 0, current_count=0 is not < 0
            assert perm.check_limit(user, "nonexistent", 0) is False


# ============================================================================
# IsSubscribed
# ============================================================================

class TestIsSubscribed:

    def test_anonymous_denied(self):
        perm = IsSubscribed()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_active_subscription_allowed(self):
        perm = IsSubscribed()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "get_subscription_info", return_value={"is_active": True}):
            assert perm.has_permission(request, _make_view()) is True

    def test_inactive_subscription_denied(self):
        perm = IsSubscribed()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "get_subscription_info", return_value={"is_active": False}):
            assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# IsPremiumUser
# ============================================================================

class TestIsPremiumUser:

    def test_anonymous_denied(self):
        perm = IsPremiumUser()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_free_denied(self):
        perm = IsPremiumUser()
        user = _make_auth_user(tier="free")
        request = _make_request(user=user)
        with patch.object(perm, "has_minimum_tier", return_value=False):
            assert perm.has_permission(request, _make_view()) is False

    def test_premium_allowed(self):
        perm = IsPremiumUser()
        user = _make_auth_user(tier="premium")
        request = _make_request(user=user)
        with patch.object(perm, "has_minimum_tier", return_value=True):
            assert perm.has_permission(request, _make_view()) is True

    def test_business_allowed(self):
        perm = IsPremiumUser()
        user = _make_auth_user(tier="business")
        request = _make_request(user=user)
        with patch.object(perm, "has_minimum_tier", return_value=True):
            assert perm.has_permission(request, _make_view()) is True


# ============================================================================
# IsProUser
# ============================================================================

class TestIsProUser:

    def test_anonymous_denied(self):
        perm = IsProUser()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_premium_denied(self):
        perm = IsProUser()
        user = _make_auth_user(tier="premium")
        request = _make_request(user=user)
        with patch.object(perm, "has_minimum_tier", return_value=False):
            assert perm.has_permission(request, _make_view()) is False

    def test_pro_allowed(self):
        perm = IsProUser()
        user = _make_auth_user(tier="pro")
        request = _make_request(user=user)
        with patch.object(perm, "has_minimum_tier", return_value=True):
            assert perm.has_permission(request, _make_view()) is True


# ============================================================================
# IsBusinessUser
# ============================================================================

class TestIsBusinessUser:

    def test_anonymous_denied(self):
        perm = IsBusinessUser()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_pro_denied(self):
        perm = IsBusinessUser()
        user = _make_auth_user(tier="pro")
        request = _make_request(user=user)
        with patch.object(perm, "has_minimum_tier", return_value=False):
            assert perm.has_permission(request, _make_view()) is False

    def test_business_allowed(self):
        perm = IsBusinessUser()
        user = _make_auth_user(tier="business")
        request = _make_request(user=user)
        with patch.object(perm, "has_minimum_tier", return_value=True):
            assert perm.has_permission(request, _make_view()) is True


# ============================================================================
# CanAccessBankingFeature
# ============================================================================

class TestCanAccessBankingFeature:

    def test_anonymous_denied(self):
        perm = CanAccessBankingFeature()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_with_bank_sync(self):
        perm = CanAccessBankingFeature()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "has_feature", return_value=True):
            assert perm.has_permission(request, _make_view()) is True

    def test_without_bank_sync(self):
        perm = CanAccessBankingFeature()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "has_feature", return_value=False):
            assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# CanAccessAIFeatures
# ============================================================================

class TestCanAccessAIFeatures:

    def test_anonymous_denied(self):
        perm = CanAccessAIFeatures()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_inactive_denied(self):
        perm = CanAccessAIFeatures()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": False, "features": {"ai_categorization": True}
        }):
            assert perm.has_permission(request, _make_view()) is False

    def test_with_ai_categorization(self):
        perm = CanAccessAIFeatures()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True,
            "features": {"ai_categorization": True, "ai_insights": False}
        }):
            assert perm.has_permission(request, _make_view()) is True

    def test_with_ai_insights(self):
        perm = CanAccessAIFeatures()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True,
            "features": {"ai_categorization": False, "ai_insights": True}
        }):
            assert perm.has_permission(request, _make_view()) is True

    def test_without_ai_features(self):
        perm = CanAccessAIFeatures()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True,
            "features": {"ai_categorization": False, "ai_insights": False}
        }):
            assert perm.has_permission(request, _make_view()) is False

    def test_empty_features(self):
        perm = CanAccessAIFeatures()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "get_subscription_info", return_value={
            "is_active": True, "features": {}
        }):
            assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# CanExportData
# ============================================================================

class TestCanExportData:

    def test_anonymous_denied(self):
        perm = CanExportData()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_csv_export_with_feature(self):
        perm = CanExportData()
        user = _make_auth_user()
        request = _make_request(user=user, query_params={"format": "csv"})
        with patch.object(perm, "has_feature", return_value=True) as mock_hf:
            assert perm.has_permission(request, _make_view()) is True
            mock_hf.assert_called_with(user, "export_csv")

    def test_pdf_export_with_feature(self):
        perm = CanExportData()
        user = _make_auth_user()
        request = _make_request(user=user, query_params={"format": "pdf"})
        with patch.object(perm, "has_feature", return_value=True) as mock_hf:
            assert perm.has_permission(request, _make_view()) is True
            mock_hf.assert_called_with(user, "export_pdf")

    def test_excel_uses_csv_feature(self):
        perm = CanExportData()
        user = _make_auth_user()
        request = _make_request(user=user, query_params={"format": "excel"})
        with patch.object(perm, "has_feature", return_value=True) as mock_hf:
            perm.has_permission(request, _make_view())
            mock_hf.assert_called_with(user, "export_csv")

    def test_default_format_csv(self):
        perm = CanExportData()
        user = _make_auth_user()
        request = _make_request(user=user, query_params={})
        with patch.object(perm, "has_feature", return_value=True) as mock_hf:
            perm.has_permission(request, _make_view())
            mock_hf.assert_called_with(user, "export_csv")

    def test_unknown_format_defaults_csv(self):
        perm = CanExportData()
        user = _make_auth_user()
        request = _make_request(user=user, query_params={"format": "unknown"})
        with patch.object(perm, "has_feature", return_value=True) as mock_hf:
            perm.has_permission(request, _make_view())
            mock_hf.assert_called_with(user, "export_csv")

    def test_without_feature(self):
        perm = CanExportData()
        user = _make_auth_user()
        request = _make_request(user=user, query_params={"format": "csv"})
        with patch.object(perm, "has_feature", return_value=False):
            assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# CanAccessAPIFeature
# ============================================================================

class TestCanAccessAPIFeature:

    def test_anonymous_denied(self):
        perm = CanAccessAPIFeature()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_with_api_access(self):
        perm = CanAccessAPIFeature()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "has_feature", return_value=True) as mock_hf:
            assert perm.has_permission(request, _make_view()) is True
            mock_hf.assert_called_with(user, "api_access")

    def test_without_api_access(self):
        perm = CanAccessAPIFeature()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "has_feature", return_value=False):
            assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# IsOwnerOrReadOnly
# ============================================================================

class TestIsOwnerOrReadOnly:

    def test_safe_methods_allowed(self):
        perm = IsOwnerOrReadOnly()
        user = _make_auth_user(user_id=1)
        other_user = _make_auth_user(user_id=2)
        request = _make_request(method="GET", user=user)
        obj = _make_obj(user=other_user)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_head_allowed(self):
        perm = IsOwnerOrReadOnly()
        request = _make_request(method="HEAD", user=_make_auth_user())
        obj = _make_obj(user=_make_auth_user(user_id=999))
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_options_allowed(self):
        perm = IsOwnerOrReadOnly()
        request = _make_request(method="OPTIONS", user=_make_auth_user())
        obj = _make_obj(user=_make_auth_user(user_id=999))
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_owner_can_write(self):
        perm = IsOwnerOrReadOnly()
        user = _make_auth_user(user_id=1)
        request = _make_request(method="PUT", user=user)
        obj = _make_obj(user=user)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_non_owner_cannot_write(self):
        perm = IsOwnerOrReadOnly()
        user = _make_auth_user(user_id=1)
        other = _make_auth_user(user_id=2)
        request = _make_request(method="PUT", user=user)
        obj = _make_obj(user=other)
        assert perm.has_object_permission(request, _make_view(), obj) is False

    def test_owner_via_owner_field(self):
        perm = IsOwnerOrReadOnly()
        user = _make_auth_user(user_id=1)
        request = _make_request(method="DELETE", user=user)
        obj = _make_obj(owner=user)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_no_owner_field_denied(self):
        perm = IsOwnerOrReadOnly()
        user = _make_auth_user(user_id=1)
        request = _make_request(method="PATCH", user=user)
        obj = MagicMock(spec=[])  # No user or owner attribute
        assert perm.has_object_permission(request, _make_view(), obj) is False


# ============================================================================
# IsOwner
# ============================================================================

class TestIsOwner:

    def test_owner_allowed(self):
        perm = IsOwner()
        user = _make_auth_user(user_id=1)
        request = _make_request(method="GET", user=user)
        obj = _make_obj(user=user)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_non_owner_denied_even_read(self):
        perm = IsOwner()
        user = _make_auth_user(user_id=1)
        other = _make_auth_user(user_id=2)
        request = _make_request(method="GET", user=user)
        obj = _make_obj(user=other)
        assert perm.has_object_permission(request, _make_view(), obj) is False

    def test_owner_via_owner_field(self):
        perm = IsOwner()
        user = _make_auth_user(user_id=1)
        request = _make_request(method="DELETE", user=user)
        obj = _make_obj(owner=user)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_no_owner_field_denied(self):
        perm = IsOwner()
        user = _make_auth_user(user_id=1)
        request = _make_request(method="GET", user=user)
        obj = MagicMock(spec=[])
        assert perm.has_object_permission(request, _make_view(), obj) is False


# ============================================================================
# IsOwnerOrAdmin
# ============================================================================

class TestIsOwnerOrAdmin:

    def test_owner_allowed(self):
        perm = IsOwnerOrAdmin()
        user = _make_auth_user(user_id=1)
        request = _make_request(user=user)
        obj = _make_obj(user=user)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_admin_allowed(self):
        perm = IsOwnerOrAdmin()
        admin = _make_auth_user(user_id=99, is_superuser=True)
        request = _make_request(user=admin)
        other = _make_auth_user(user_id=1)
        obj = _make_obj(user=other)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_staff_allowed(self):
        perm = IsOwnerOrAdmin()
        staff = _make_auth_user(user_id=99, is_staff=True)
        request = _make_request(user=staff)
        other = _make_auth_user(user_id=1)
        obj = _make_obj(user=other)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_non_owner_non_admin_denied(self):
        perm = IsOwnerOrAdmin()
        user = _make_auth_user(user_id=1)
        other = _make_auth_user(user_id=2)
        request = _make_request(user=user)
        obj = _make_obj(user=other)
        assert perm.has_object_permission(request, _make_view(), obj) is False

    def test_owner_via_owner_field(self):
        perm = IsOwnerOrAdmin()
        user = _make_auth_user(user_id=1)
        request = _make_request(user=user)
        obj = _make_obj(owner=user)
        assert perm.has_object_permission(request, _make_view(), obj) is True


# ============================================================================
# WithinBankAccountLimit
# ============================================================================

class TestWithinBankAccountLimit:

    def test_anonymous_denied(self):
        perm = WithinBankAccountLimit()
        request = _make_request(method="POST", user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_get_always_allowed(self):
        perm = WithinBankAccountLimit()
        user = _make_auth_user()
        request = _make_request(method="GET", user=user)
        assert perm.has_permission(request, _make_view()) is True

    def test_post_within_limit(self):
        perm = WithinBankAccountLimit()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "check_limit", return_value=True), \
             patch("apps.core.permissions.cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch.dict("sys.modules", {"apps.banking.models": MagicMock()}):
                # Mock BankAccount.objects.filter().count()
                mock_ba = MagicMock()
                mock_ba.objects.filter.return_value.count.return_value = 1
                with patch.dict("sys.modules", {"apps.banking.models": MagicMock(BankAccount=mock_ba)}):
                    # Use direct mock for simpler test
                    with patch.object(perm, "check_limit", return_value=True):
                        assert perm.has_permission(request, _make_view()) is True

    def test_post_over_limit(self):
        perm = WithinBankAccountLimit()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "check_limit", return_value=False):
            # Simulate BankAccount import error -> count = 0
            with patch.dict("sys.modules", {"apps.banking.models": None}):
                result = perm.has_permission(request, _make_view())
                # count=0, check_limit returns False
                assert result is False

    def test_post_import_error_defaults_zero(self):
        perm = WithinBankAccountLimit()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "check_limit", return_value=True):
            # Simulate import failure
            with patch.dict("sys.modules", {"apps.banking.models": None}):
                assert perm.has_permission(request, _make_view()) is True


# ============================================================================
# WithinBudgetLimit
# ============================================================================

class TestWithinBudgetLimit:

    def test_anonymous_denied(self):
        perm = WithinBudgetLimit()
        request = _make_request(method="POST", user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_get_always_allowed(self):
        perm = WithinBudgetLimit()
        user = _make_auth_user()
        request = _make_request(method="GET", user=user)
        assert perm.has_permission(request, _make_view()) is True

    def test_post_within_limit(self):
        perm = WithinBudgetLimit()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "check_limit", return_value=True), \
             patch.dict("sys.modules", {"apps.budgets.models": None}):
            assert perm.has_permission(request, _make_view()) is True

    def test_post_over_limit(self):
        perm = WithinBudgetLimit()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "check_limit", return_value=False), \
             patch.dict("sys.modules", {"apps.budgets.models": None}):
            assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# WithinCategoryLimit
# ============================================================================

class TestWithinCategoryLimit:

    def test_anonymous_denied(self):
        perm = WithinCategoryLimit()
        request = _make_request(method="POST", user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_get_always_allowed(self):
        perm = WithinCategoryLimit()
        user = _make_auth_user()
        request = _make_request(method="GET", user=user)
        assert perm.has_permission(request, _make_view()) is True

    def test_post_within_limit(self):
        perm = WithinCategoryLimit()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "check_limit", return_value=True), \
             patch.dict("sys.modules", {"apps.transactions.models": None}):
            assert perm.has_permission(request, _make_view()) is True

    def test_post_over_limit(self):
        perm = WithinCategoryLimit()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "check_limit", return_value=False), \
             patch.dict("sys.modules", {"apps.transactions.models": None}):
            assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# CanManageBankConnection
# ============================================================================

class TestCanManageBankConnection:

    def test_anonymous_denied(self):
        perm = CanManageBankConnection()
        request = _make_request(user=_make_anon_user())
        result = perm.has_permission(request, _make_view())
        assert result is False
        assert "Authentification" in perm.message

    def test_no_bank_sync_feature(self):
        perm = CanManageBankConnection()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(perm, "has_feature", return_value=False):
            result = perm.has_permission(request, _make_view())
        assert result is False
        assert "Premium" in perm.message

    def test_with_bank_sync_get(self):
        perm = CanManageBankConnection()
        user = _make_auth_user()
        request = _make_request(method="GET", user=user)
        with patch.object(perm, "has_feature", return_value=True):
            assert perm.has_permission(request, _make_view()) is True

    def test_post_over_limit(self):
        perm = CanManageBankConnection()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "has_feature", return_value=True), \
             patch.object(perm, "check_limit", return_value=False), \
             patch.dict("sys.modules", {"apps.banking.models": None}):
            result = perm.has_permission(request, _make_view())
        assert result is False
        assert "Limite" in perm.message

    def test_post_within_limit(self):
        perm = CanManageBankConnection()
        user = _make_auth_user()
        request = _make_request(method="POST", user=user)
        with patch.object(perm, "has_feature", return_value=True), \
             patch.object(perm, "check_limit", return_value=True), \
             patch.dict("sys.modules", {"apps.banking.models": None}):
            assert perm.has_permission(request, _make_view()) is True

    # --- Object-level permissions ---

    def test_object_permission_owner(self):
        perm = CanManageBankConnection()
        user = _make_auth_user(user_id=1)
        request = _make_request(user=user)
        obj = _make_obj(user=user)
        assert perm.has_object_permission(request, _make_view(), obj) is True

    def test_object_permission_non_owner(self):
        perm = CanManageBankConnection()
        user = _make_auth_user(user_id=1)
        other = _make_auth_user(user_id=2)
        request = _make_request(user=user)
        obj = _make_obj(user=other)
        result = perm.has_object_permission(request, _make_view(), obj)
        assert result is False
        assert "proprietaire" in perm.message


# ============================================================================
# IsEmailVerified
# ============================================================================

class TestIsEmailVerified:

    def test_anonymous_denied(self):
        perm = IsEmailVerified()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_verified_allowed(self):
        perm = IsEmailVerified()
        user = _make_auth_user(is_email_verified=True)
        request = _make_request(user=user)
        assert perm.has_permission(request, _make_view()) is True

    def test_unverified_denied(self):
        perm = IsEmailVerified()
        user = _make_auth_user(is_email_verified=False)
        request = _make_request(user=user)
        assert perm.has_permission(request, _make_view()) is False

    def test_no_email_verified_attr_denied(self):
        perm = IsEmailVerified()
        user = MagicMock()
        user.is_authenticated = True
        # Use spec=[] so hasattr returns False for is_email_verified
        del user.is_email_verified
        request = _make_request(user=user)
        # getattr with default False should return False
        assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# IsSameUser
# ============================================================================

class TestIsSameUser:

    def test_anonymous_denied(self):
        perm = IsSameUser()
        request = _make_request(user=_make_anon_user())
        assert perm.has_permission(request, _make_view()) is False

    def test_staff_can_access_any(self):
        perm = IsSameUser()
        staff = _make_auth_user(user_id=1, is_staff=True)
        request = _make_request(user=staff)
        view = _make_view(kwargs={"user_id": "999"})
        assert perm.has_permission(request, view) is True

    def test_same_user_allowed(self):
        perm = IsSameUser()
        user = _make_auth_user(user_id=42)
        request = _make_request(user=user)
        view = _make_view(kwargs={"user_id": "42"})
        assert perm.has_permission(request, view) is True

    def test_different_user_denied(self):
        perm = IsSameUser()
        user = _make_auth_user(user_id=42)
        request = _make_request(user=user)
        view = _make_view(kwargs={"user_id": "99"})
        assert perm.has_permission(request, view) is False

    def test_pk_kwarg_used(self):
        perm = IsSameUser()
        user = _make_auth_user(user_id=42)
        request = _make_request(user=user)
        view = _make_view(kwargs={"pk": "42"})
        assert perm.has_permission(request, view) is True

    def test_no_url_kwargs_allowed(self):
        perm = IsSameUser()
        user = _make_auth_user(user_id=42)
        request = _make_request(user=user)
        view = _make_view(kwargs={})
        assert perm.has_permission(request, view) is True


# ============================================================================
# ReadOnly
# ============================================================================

class TestReadOnly:

    def test_get_allowed(self):
        perm = ReadOnly()
        request = _make_request(method="GET")
        assert perm.has_permission(request, _make_view()) is True

    def test_head_allowed(self):
        perm = ReadOnly()
        request = _make_request(method="HEAD")
        assert perm.has_permission(request, _make_view()) is True

    def test_options_allowed(self):
        perm = ReadOnly()
        request = _make_request(method="OPTIONS")
        assert perm.has_permission(request, _make_view()) is True

    def test_post_denied(self):
        perm = ReadOnly()
        request = _make_request(method="POST")
        assert perm.has_permission(request, _make_view()) is False

    def test_put_denied(self):
        perm = ReadOnly()
        request = _make_request(method="PUT")
        assert perm.has_permission(request, _make_view()) is False

    def test_patch_denied(self):
        perm = ReadOnly()
        request = _make_request(method="PATCH")
        assert perm.has_permission(request, _make_view()) is False

    def test_delete_denied(self):
        perm = ReadOnly()
        request = _make_request(method="DELETE")
        assert perm.has_permission(request, _make_view()) is False


# ============================================================================
# SubscriptionPermissionMixin
# ============================================================================

class TestSubscriptionPermissionMixin:

    def _make_mixin_instance(self, required_tier=None, required_features=None):
        instance = SubscriptionPermissionMixin()
        instance.required_tier = required_tier
        instance.required_features = required_features or []
        return instance

    def test_anonymous_denied(self):
        mixin = self._make_mixin_instance()
        request = _make_request(user=_make_anon_user())
        assert mixin.check_subscription_permissions(request) is False

    def test_inactive_denied(self):
        mixin = self._make_mixin_instance()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(BaseSubscriptionPermission, "get_subscription_info",
                          return_value={"is_active": False, "tier": "free",
                                        "features": {}, "limits": {}}):
            assert mixin.check_subscription_permissions(request) is False

    def test_active_no_requirements(self):
        mixin = self._make_mixin_instance()
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(BaseSubscriptionPermission, "get_subscription_info",
                          return_value={"is_active": True, "tier": "free",
                                        "features": {}, "limits": {}}):
            assert mixin.check_subscription_permissions(request) is True

    def test_tier_requirement_met(self):
        mixin = self._make_mixin_instance(required_tier="premium")
        user = _make_auth_user(tier="premium")
        request = _make_request(user=user)
        with patch.object(BaseSubscriptionPermission, "get_subscription_info",
                          return_value={"is_active": True, "tier": "premium",
                                        "features": {}, "limits": {}}):
            with patch.object(BaseSubscriptionPermission, "has_minimum_tier",
                              return_value=True):
                assert mixin.check_subscription_permissions(request) is True

    def test_tier_requirement_not_met(self):
        mixin = self._make_mixin_instance(required_tier="pro")
        user = _make_auth_user(tier="free")
        request = _make_request(user=user)
        with patch.object(BaseSubscriptionPermission, "get_subscription_info",
                          return_value={"is_active": True, "tier": "free",
                                        "features": {}, "limits": {}}):
            with patch.object(BaseSubscriptionPermission, "has_minimum_tier",
                              return_value=False):
                assert mixin.check_subscription_permissions(request) is False

    def test_feature_requirement_met(self):
        mixin = self._make_mixin_instance(required_features=["bank_sync"])
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(BaseSubscriptionPermission, "get_subscription_info",
                          return_value={"is_active": True, "tier": "premium",
                                        "features": {"bank_sync": True}, "limits": {}}):
            with patch.object(BaseSubscriptionPermission, "has_feature",
                              return_value=True):
                assert mixin.check_subscription_permissions(request) is True

    def test_feature_requirement_not_met(self):
        mixin = self._make_mixin_instance(required_features=["bank_sync"])
        user = _make_auth_user()
        request = _make_request(user=user)
        with patch.object(BaseSubscriptionPermission, "get_subscription_info",
                          return_value={"is_active": True, "tier": "free",
                                        "features": {}, "limits": {}}):
            with patch.object(BaseSubscriptionPermission, "has_feature",
                              return_value=False):
                assert mixin.check_subscription_permissions(request) is False


# ============================================================================
# OwnerPermissionMixin
# ============================================================================

class TestOwnerPermissionMixin:

    def _make_mixin_instance(self, owner_field="user"):
        instance = OwnerPermissionMixin()
        instance.owner_field = owner_field
        return instance

    def test_owner_allowed(self):
        mixin = self._make_mixin_instance()
        user = _make_auth_user(user_id=1)
        request = _make_request(user=user)
        obj = _make_obj(user=user)
        assert mixin.check_owner_permission(request, obj) is True

    def test_staff_allowed(self):
        mixin = self._make_mixin_instance()
        staff = _make_auth_user(user_id=99, is_staff=True)
        request = _make_request(user=staff)
        other = _make_auth_user(user_id=1)
        obj = _make_obj(user=other)
        assert mixin.check_owner_permission(request, obj) is True

    def test_non_owner_denied(self):
        mixin = self._make_mixin_instance()
        user = _make_auth_user(user_id=1)
        other = _make_auth_user(user_id=2)
        request = _make_request(user=user)
        obj = _make_obj(user=other)
        assert mixin.check_owner_permission(request, obj) is False

    def test_custom_owner_field(self):
        mixin = self._make_mixin_instance(owner_field="owner")
        user = _make_auth_user(user_id=1)
        request = _make_request(user=user)
        obj = _make_obj(owner=user)
        assert mixin.check_owner_permission(request, obj) is True

    def test_no_owner_field_denied(self):
        mixin = self._make_mixin_instance(owner_field="nonexistent")
        user = _make_auth_user(user_id=1)
        request = _make_request(user=user)
        obj = MagicMock(spec=[])
        assert mixin.check_owner_permission(request, obj) is False
