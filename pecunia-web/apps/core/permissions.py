"""
Core Permissions.

Custom DRF permission classes for subscription-based access control.
Implements fine-grained authorization for SaaS features.
"""
import logging
from typing import Any, List, Optional

from django.conf import settings
from django.core.cache import cache
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


# =============================================================================
# Base Permission Classes
# =============================================================================

class BaseSubscriptionPermission(permissions.BasePermission):
    """
    Base class for subscription-based permissions.

    Provides common functionality for checking subscription status,
    tier levels, and feature access.
    """

    # Tier hierarchy (higher number = higher tier)
    TIER_LEVELS = {
        'free': 0,
        'premium': 1,
        'pro': 2,
        'business': 3,
    }

    # Cache timeout for subscription checks (30 seconds)
    CACHE_TIMEOUT = 30

    def get_subscription_info(self, user) -> dict:
        """
        Get user's subscription information with caching.

        Returns:
            dict: Subscription details including tier, status, features, limits
        """
        if not user.is_authenticated:
            return self._get_anonymous_info()

        cache_key = f"subscription_perm:{user.id}"
        cached_info = cache.get(cache_key)

        if cached_info:
            return cached_info

        try:
            from apps.subscriptions.models import Subscription

            subscription = Subscription.objects.select_related('plan').filter(
                user=user
            ).first()

            if subscription:
                info = {
                    'is_active': subscription.is_active,
                    'tier': subscription.tier,
                    'status': subscription.status,
                    'is_trialing': subscription.is_on_trial,
                    'features': self._extract_features(subscription.plan),
                    'limits': self._extract_limits(subscription.plan),
                }
            else:
                info = self._get_free_tier_info()
        except Exception as e:
            logger.warning(f"Error fetching subscription: {e}")
            # Fallback to user's tier field
            info = {
                'is_active': True,
                'tier': getattr(user, 'subscription_tier', 'free'),
                'status': 'active',
                'is_trialing': False,
                'features': {},
                'limits': {},
            }

        cache.set(cache_key, info, self.CACHE_TIMEOUT)
        return info

    @staticmethod
    def invalidate_subscription_cache(user_id):
        """Invalidate cached subscription info when subscription changes.

        Call this from subscription update/cancel/renew signal handlers
        or views to ensure permission checks reflect the latest state.
        """
        cache.delete(f"subscription_perm:{user_id}")

    def _extract_features(self, plan) -> dict:
        """Extract feature flags from subscription plan."""
        feature_fields = [
            'ai_categorization', 'ai_insights', 'export_csv', 'export_pdf',
            'bank_sync', 'recurring_transactions', 'custom_categories',
            'budget_alerts', 'multi_currency', 'priority_support', 'api_access',
        ]
        return {field: getattr(plan, field, False) for field in feature_fields}

    def _extract_limits(self, plan) -> dict:
        """Extract limits from subscription plan."""
        limit_fields = [
            'max_bank_accounts', 'max_budgets', 'max_transactions_per_month',
            'max_categories', 'max_family_members',
        ]
        return {field: getattr(plan, field, 0) for field in limit_fields}

    def _get_free_tier_info(self) -> dict:
        """Get default free tier info."""
        return {
            'is_active': True,
            'tier': 'free',
            'status': 'active',
            'is_trialing': False,
            'features': {
                'ai_categorization': False,
                'ai_insights': False,
                'export_csv': False,
                'export_pdf': False,
                'bank_sync': False,
                'recurring_transactions': True,
                'custom_categories': True,
                'budget_alerts': True,
                'multi_currency': False,
                'priority_support': False,
                'api_access': False,
            },
            'limits': {
                'max_bank_accounts': 1,
                'max_budgets': 3,
                'max_transactions_per_month': 100,
                'max_categories': 10,
                'max_family_members': 0,
            },
        }

    def _get_anonymous_info(self) -> dict:
        """Get info for anonymous users."""
        return {
            'is_active': False,
            'tier': None,
            'status': None,
            'is_trialing': False,
            'features': {},
            'limits': {},
        }

    def get_tier_level(self, tier: str) -> int:
        """Get numeric level for tier."""
        return self.TIER_LEVELS.get(tier, 0)

    def has_minimum_tier(self, user, required_tier: str) -> bool:
        """
        Check if user has at least the required tier.

        Uses numeric levels (free=0, basic=1, premium=2, business=3) to enable
        "X or higher" checks. For example, a premium feature (level 2) is
        accessible to premium (2) and business (3) users, but not basic (1).
        """
        subscription = self.get_subscription_info(user)

        if not subscription['is_active']:
            return False

        user_level = self.get_tier_level(subscription['tier'])
        required_level = self.get_tier_level(required_tier)

        return user_level >= required_level

    def has_feature(self, user, feature_name: str) -> bool:
        """Check if user's subscription includes a feature."""
        subscription = self.get_subscription_info(user)

        if not subscription['is_active']:
            return False

        return subscription.get('features', {}).get(feature_name, False)

    def check_limit(self, user, limit_name: str, current_count: int) -> bool:
        """Check if user is within a subscription limit."""
        subscription = self.get_subscription_info(user)
        max_allowed = subscription.get('limits', {}).get(limit_name, 0)
        return current_count < max_allowed


# =============================================================================
# Subscription Permissions
# =============================================================================

class IsSubscribed(BaseSubscriptionPermission):
    """
    Permission class to verify user has an active subscription.

    Usage:
        permission_classes = [IsAuthenticated, IsSubscribed]

    Allows:
        - Users with active subscription (any tier)
        - Users in trial period

    Denies:
        - Anonymous users
        - Users with expired/canceled subscriptions
    """

    message = "Un abonnement actif est requis pour acceder a cette ressource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user has active subscription."""
        if not request.user.is_authenticated:
            return False

        subscription = self.get_subscription_info(request.user)
        return subscription['is_active']


class IsPremiumUser(BaseSubscriptionPermission):
    """
    Permission class to verify user has Premium tier or higher.

    Usage:
        permission_classes = [IsAuthenticated, IsPremiumUser]

    Allows:
        - Premium tier users
        - Pro tier users
        - Business tier users

    Denies:
        - Free tier users
        - Inactive subscriptions
    """

    message = "Cette fonctionnalite necessite un abonnement Premium ou superieur."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user has premium tier or higher."""
        if not request.user.is_authenticated:
            return False

        return self.has_minimum_tier(request.user, 'premium')


class IsProUser(BaseSubscriptionPermission):
    """
    Permission class to verify user has Pro tier or higher.

    Usage:
        permission_classes = [IsAuthenticated, IsProUser]

    Allows:
        - Pro tier users
        - Business tier users

    Denies:
        - Free tier users
        - Premium tier users
        - Inactive subscriptions
    """

    message = "Cette fonctionnalite necessite un abonnement Pro ou superieur."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user has pro tier or higher."""
        if not request.user.is_authenticated:
            return False

        return self.has_minimum_tier(request.user, 'pro')


class IsBusinessUser(BaseSubscriptionPermission):
    """
    Permission class to verify user has Business tier.

    Usage:
        permission_classes = [IsAuthenticated, IsBusinessUser]

    Allows:
        - Business tier users only

    Denies:
        - All other tiers
        - Inactive subscriptions
    """

    message = "Cette fonctionnalite necessite un abonnement Business."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user has business tier."""
        if not request.user.is_authenticated:
            return False

        return self.has_minimum_tier(request.user, 'business')


# =============================================================================
# Feature-based Permissions
# =============================================================================

class CanAccessBankingFeature(BaseSubscriptionPermission):
    """
    Permission class for banking synchronization features.

    Usage:
        permission_classes = [IsAuthenticated, CanAccessBankingFeature]

    Allows:
        - Users with bank_sync feature enabled (Premium+)

    Denies:
        - Free tier users
        - Users without active subscription
    """

    message = "La synchronisation bancaire necessite un abonnement Premium ou superieur."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user can access banking features."""
        if not request.user.is_authenticated:
            return False

        return self.has_feature(request.user, 'bank_sync')


class CanAccessAIFeatures(BaseSubscriptionPermission):
    """
    Permission class for AI-powered features.

    Usage:
        permission_classes = [IsAuthenticated, CanAccessAIFeatures]

    Allows:
        - Users with ai_categorization or ai_insights features

    Denies:
        - Free tier users without AI access
    """

    message = "Les fonctionnalites IA necessitent un abonnement Premium ou superieur."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user can access AI features."""
        if not request.user.is_authenticated:
            return False

        subscription = self.get_subscription_info(request.user)

        if not subscription['is_active']:
            return False

        features = subscription.get('features', {})
        return features.get('ai_categorization', False) or features.get('ai_insights', False)


class CanExportData(BaseSubscriptionPermission):
    """
    Permission class for data export features.

    Usage:
        permission_classes = [IsAuthenticated, CanExportData]

    Allows:
        - Users with export_csv or export_pdf features
    """

    message = "L'export de donnees necessite un abonnement Premium ou superieur."

    # Mapping of export types to required features
    EXPORT_FEATURES = {
        'csv': 'export_csv',
        'pdf': 'export_pdf',
        'excel': 'export_csv',  # Excel uses same feature as CSV
    }

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user can export data."""
        if not request.user.is_authenticated:
            return False

        # Get export type from request
        export_type = request.query_params.get('format', 'csv').lower()
        required_feature = self.EXPORT_FEATURES.get(export_type, 'export_csv')

        return self.has_feature(request.user, required_feature)


class CanAccessAPIFeature(BaseSubscriptionPermission):
    """
    Permission class for API access (programmatic access).

    Usage:
        permission_classes = [IsAuthenticated, CanAccessAPIFeature]

    Allows:
        - Business tier users with API access enabled

    Denies:
        - All other tiers
    """

    message = "L'acces API necessite un abonnement Business."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user can access API features."""
        if not request.user.is_authenticated:
            return False

        return self.has_feature(request.user, 'api_access')


# =============================================================================
# Object-level Permissions
# =============================================================================

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission class allowing owners full access, others read-only.

    Usage:
        permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    Requires:
        - Object must have 'user' or 'owner' attribute

    Allows:
        - Owners: full CRUD access
        - Others: GET, HEAD, OPTIONS only

    OWASP Protection:
        - A01:2021 - Broken Access Control
    """

    message = "Vous n'avez pas la permission de modifier cette ressource."

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any
    ) -> bool:
        """Check object-level permission."""
        # Read permissions for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)

        if owner is None:
            logger.warning(
                f"Object {type(obj).__name__} has no user/owner attribute"
            )
            return False

        return owner == request.user


class IsOwner(permissions.BasePermission):
    """
    Permission class allowing only owners full access.

    Usage:
        permission_classes = [IsAuthenticated, IsOwner]

    Requires:
        - Object must have 'user' or 'owner' attribute

    Allows:
        - Owners only (all methods)

    Denies:
        - Non-owners (all methods including read)

    OWASP Protection:
        - A01:2021 - Broken Access Control
    """

    message = "Vous n'avez pas acces a cette ressource."

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any
    ) -> bool:
        """Check object-level permission."""
        owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)

        if owner is None:
            return False

        return owner == request.user


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class allowing owners and admins full access.

    Usage:
        permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    Allows:
        - Object owners: full access
        - Staff/Admin users: full access
    """

    message = "Vous n'avez pas la permission d'acceder a cette ressource."

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any
    ) -> bool:
        """Check object-level permission."""
        # Admin/staff always allowed
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check ownership
        owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)
        return owner == request.user


# =============================================================================
# Limit-based Permissions
# =============================================================================

class WithinBankAccountLimit(BaseSubscriptionPermission):
    """
    Permission class to check bank account creation limit.

    Usage:
        permission_classes = [IsAuthenticated, WithinBankAccountLimit]

    Checks subscription limit before allowing creation of new bank accounts.
    """

    message = "Vous avez atteint la limite de comptes bancaires pour votre abonnement."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user can create more bank accounts."""
        if not request.user.is_authenticated:
            return False

        # Only check on POST (creation)
        if request.method != 'POST':
            return True

        try:
            from apps.banking.models import BankAccount
            current_count = BankAccount.objects.filter(user=request.user).count()
        except Exception:
            current_count = 0

        return self.check_limit(request.user, 'max_bank_accounts', current_count)


class WithinBudgetLimit(BaseSubscriptionPermission):
    """
    Permission class to check budget creation limit.

    Usage:
        permission_classes = [IsAuthenticated, WithinBudgetLimit]

    Checks subscription limit before allowing creation of new budgets.
    """

    message = "Vous avez atteint la limite de budgets pour votre abonnement."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user can create more budgets."""
        if not request.user.is_authenticated:
            return False

        # Only check on POST (creation)
        if request.method != 'POST':
            return True

        try:
            from apps.budgets.models import Budget
            current_count = Budget.objects.filter(user=request.user).count()
        except Exception:
            current_count = 0

        return self.check_limit(request.user, 'max_budgets', current_count)


class WithinCategoryLimit(BaseSubscriptionPermission):
    """
    Permission class to check category creation limit.

    Usage:
        permission_classes = [IsAuthenticated, WithinCategoryLimit]

    Checks subscription limit before allowing creation of new categories.
    """

    message = "Vous avez atteint la limite de categories pour votre abonnement."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user can create more categories."""
        if not request.user.is_authenticated:
            return False

        # Only check on POST (creation)
        if request.method != 'POST':
            return True

        try:
            from apps.transactions.models import Category
            current_count = Category.objects.filter(user=request.user).count()
        except Exception:
            current_count = 0

        return self.check_limit(request.user, 'max_categories', current_count)


# =============================================================================
# Composite Permissions
# =============================================================================

class CanManageBankConnection(BaseSubscriptionPermission):
    """
    Composite permission for bank connection management.

    Combines:
        - IsAuthenticated
        - CanAccessBankingFeature
        - WithinBankAccountLimit
        - IsOwner (for object-level)
    """

    message = "Vous ne pouvez pas gerer cette connexion bancaire."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check combined permissions."""
        if not request.user.is_authenticated:
            self.message = "Authentification requise."
            return False

        # Check banking feature access
        if not self.has_feature(request.user, 'bank_sync'):
            self.message = "La synchronisation bancaire necessite un abonnement Premium."
            return False

        # Check account limit for POST
        if request.method == 'POST':
            try:
                from apps.banking.models import BankAccount
                current_count = BankAccount.objects.filter(user=request.user).count()
            except Exception:
                current_count = 0

            if not self.check_limit(request.user, 'max_bank_accounts', current_count):
                self.message = "Limite de comptes bancaires atteinte."
                return False

        return True

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any
    ) -> bool:
        """Check object ownership."""
        owner = getattr(obj, 'user', None)
        if owner != request.user:
            self.message = "Vous n'etes pas proprietaire de cette connexion."
            return False
        return True


# =============================================================================
# Utility Permissions
# =============================================================================

class IsEmailVerified(permissions.BasePermission):
    """
    Permission requiring email verification.

    Usage:
        permission_classes = [IsAuthenticated, IsEmailVerified]

    Allows:
        - Users with verified email addresses

    Denies:
        - Users with unverified emails
    """

    message = "Veuillez verifier votre adresse email pour acceder a cette fonctionnalite."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user's email is verified."""
        if not request.user.is_authenticated:
            return False

        return getattr(request.user, 'is_email_verified', False)


class IsSameUser(permissions.BasePermission):
    """
    Permission ensuring user can only access their own resources.

    Usage:
        Used in user profile views where URL contains user ID.

    Allows:
        - Access to own resources only
        - Staff/admin access to any resource
    """

    message = "Vous ne pouvez acceder qu'a vos propres informations."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user is accessing own resource."""
        if not request.user.is_authenticated:
            return False

        # Staff can access any user
        if request.user.is_staff:
            return True

        # Get user ID from URL kwargs
        user_id = view.kwargs.get('user_id') or view.kwargs.get('pk')

        if user_id:
            return str(request.user.id) == str(user_id)

        return True


class ReadOnly(permissions.BasePermission):
    """
    Permission allowing only read operations.

    Usage:
        permission_classes = [IsAuthenticated, ReadOnly]

    Allows:
        - GET, HEAD, OPTIONS methods

    Denies:
        - POST, PUT, PATCH, DELETE methods
    """

    message = "Cette ressource est en lecture seule."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if request method is safe."""
        return request.method in permissions.SAFE_METHODS


# =============================================================================
# Permission Mixins for Views
# =============================================================================

class SubscriptionPermissionMixin:
    """
    Mixin providing subscription-aware permission checking in views.

    Usage:
        class MyView(SubscriptionPermissionMixin, APIView):
            required_tier = 'premium'
            required_features = ['ai_insights']
    """

    required_tier: Optional[str] = None
    required_features: List[str] = []

    def check_subscription_permissions(self, request: Request) -> bool:
        """Check subscription-based permissions."""
        if not request.user.is_authenticated:
            return False

        permission = BaseSubscriptionPermission()
        subscription = permission.get_subscription_info(request.user)

        if not subscription['is_active']:
            return False

        # Check tier
        if self.required_tier:
            if not permission.has_minimum_tier(request.user, self.required_tier):
                return False

        # Check features
        for feature in self.required_features:
            if not permission.has_feature(request.user, feature):
                return False

        return True


class OwnerPermissionMixin:
    """
    Mixin providing owner-based permission checking in views.

    Usage:
        class MyView(OwnerPermissionMixin, RetrieveUpdateDestroyAPIView):
            owner_field = 'user'  # Field name on model
    """

    owner_field: str = 'user'

    def check_owner_permission(self, request: Request, obj: Any) -> bool:
        """Check if request user is the owner."""
        owner = getattr(obj, self.owner_field, None)

        if owner is None:
            return False

        # Staff can access anything
        if request.user.is_staff:
            return True

        return owner == request.user
