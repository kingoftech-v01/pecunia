"""
Social Authentication Adapters for Pecunia
Handles account linking, profile synchronization, and social auth customization.
"""

import logging
from typing import Optional, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.exceptions import ImmediateHttpResponse
from allauth.account.utils import perform_login

import requests

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for email/password authentication.
    Extends django-allauth's DefaultAccountAdapter.
    """

    def is_open_for_signup(self, request) -> bool:
        """
        Check if registration is allowed.
        Can be controlled via settings.
        """
        return getattr(settings, 'ACCOUNT_ALLOW_REGISTRATION', True)

    def save_user(self, request, user, form, commit=True):
        """
        Save a new user with additional fields.
        """
        user = super().save_user(request, user, form, commit=False)

        # Set additional fields from form data
        if hasattr(form, 'cleaned_data'):
            data = form.cleaned_data
            user.first_name = data.get('first_name', '')
            user.last_name = data.get('last_name', '')

        if commit:
            user.save()

        return user

    def get_login_redirect_url(self, request):
        """
        Return the URL to redirect to after login.
        """
        # Check for next parameter
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url and self.is_safe_url(next_url, request):
            return next_url

        return getattr(settings, 'LOGIN_REDIRECT_URL', '/dashboard/')

    def is_safe_url(self, url: str, request) -> bool:
        """
        Check if URL is safe for redirect.
        """
        from django.utils.http import url_has_allowed_host_and_scheme

        return url_has_allowed_host_and_scheme(
            url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        )

    def send_mail(self, template_prefix, email, context):
        """
        Send email with custom template handling.
        """
        # Add site context
        context['site_name'] = getattr(settings, 'SITE_NAME', 'Pecunia')
        context['support_email'] = getattr(settings, 'SUPPORT_EMAIL', 'support@pecunia.com')

        super().send_mail(template_prefix, email, context)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for OAuth authentication.
    Handles account linking, profile sync, and social auth customization.
    """

    def is_open_for_signup(self, request, sociallogin) -> bool:
        """
        Check if social signup is allowed.
        """
        return getattr(settings, 'SOCIALACCOUNT_ALLOW_REGISTRATION', True)

    def pre_social_login(self, request, sociallogin: SocialLogin):
        """
        Called before social login completes.
        Handles automatic account linking by email.
        """
        # If user is already logged in, we'll handle linking in connect flow
        if request.user.is_authenticated:
            return

        # Check if this social account is already connected
        if sociallogin.is_existing:
            return

        # Try to find existing user by email
        email = sociallogin.account.extra_data.get('email')
        if not email:
            # Try to get email from user object
            if sociallogin.user and sociallogin.user.email:
                email = sociallogin.user.email

        if email:
            try:
                existing_user = User.objects.get(email__iexact=email)

                # Check if email is verified by the provider
                email_verified = sociallogin.account.extra_data.get('email_verified', False)

                if email_verified:
                    # Auto-link the account
                    sociallogin.connect(request, existing_user)
                    logger.info(
                        f"Auto-linked {sociallogin.account.provider} account to user {existing_user.id}"
                    )
                else:
                    # Email not verified, require manual linking
                    logger.warning(
                        f"Cannot auto-link unverified email {email} from {sociallogin.account.provider}"
                    )

            except User.DoesNotExist:
                pass
            except User.MultipleObjectsReturned:
                logger.error(f"Multiple users found with email {email}")

    def populate_user(self, request, sociallogin: SocialLogin, data: Dict[str, Any]):
        """
        Populate user data from social account.
        """
        user = super().populate_user(request, sociallogin, data)

        # Additional data population
        extra_data = sociallogin.account.extra_data

        # Set first and last name
        if not user.first_name:
            user.first_name = (
                data.get('first_name') or
                extra_data.get('given_name') or
                extra_data.get('firstName', '')
            )

        if not user.last_name:
            user.last_name = (
                data.get('last_name') or
                extra_data.get('family_name') or
                extra_data.get('lastName', '')
            )

        # If we only have full name, split it
        if not user.first_name and not user.last_name:
            full_name = data.get('name') or extra_data.get('name', '')
            if full_name:
                parts = full_name.split(' ', 1)
                user.first_name = parts[0]
                user.last_name = parts[1] if len(parts) > 1 else ''

        return user

    def save_user(self, request, sociallogin: SocialLogin, form=None):
        """
        Save user after social signup.
        """
        user = super().save_user(request, sociallogin, form)

        # Sync profile from social account
        self.sync_profile_from_social(user, sociallogin)

        logger.info(f"Created user {user.id} via {sociallogin.account.provider}")

        return user

    def authentication_error(
        self,
        request,
        provider_id: str,
        error: Optional[str] = None,
        exception: Optional[Exception] = None,
        extra_context: Optional[Dict] = None
    ):
        """
        Handle authentication errors.
        """
        logger.error(
            f"OAuth authentication error from {provider_id}: {error}",
            exc_info=exception
        )

        # Let default handling continue
        super().authentication_error(
            request, provider_id, error, exception, extra_context
        )

    def get_connect_redirect_url(self, request, socialaccount: SocialAccount) -> str:
        """
        Return URL to redirect to after connecting a social account.
        """
        return getattr(settings, 'SOCIALACCOUNT_CONNECT_REDIRECT_URL', '/settings/accounts/')

    @transaction.atomic
    def sync_profile_from_social(
        self,
        user,
        sociallogin: SocialLogin,
        update_picture: bool = True
    ):
        """
        Synchronize user profile from social account data.

        Args:
            user: User instance
            sociallogin: Social login instance
            update_picture: Whether to download and update profile picture
        """
        extra_data = sociallogin.account.extra_data
        provider = sociallogin.account.provider

        # Update basic info if not set
        updated = False

        if not user.first_name:
            first_name = extra_data.get('given_name') or extra_data.get('firstName')
            if first_name:
                user.first_name = first_name
                updated = True

        if not user.last_name:
            last_name = extra_data.get('family_name') or extra_data.get('lastName')
            if last_name:
                user.last_name = last_name
                updated = True

        # Update profile picture
        if update_picture:
            picture_url = extra_data.get('picture')
            if picture_url:
                self._update_profile_picture(user, picture_url, provider)

        # Update locale if available
        locale = extra_data.get('locale')
        if locale and hasattr(user, 'locale'):
            user.locale = locale
            updated = True

        if updated:
            user.save()
            logger.info(f"Synced profile for user {user.id} from {provider}")

    def _update_profile_picture(self, user, picture_url: str, provider: str):
        """
        Download and save profile picture from social provider.
        """
        if not hasattr(user, 'avatar'):
            return

        try:
            response = requests.get(picture_url, timeout=10)
            response.raise_for_status()

            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            else:
                ext = 'jpg'  # Default

            filename = f"avatar_{provider}_{user.id}.{ext}"
            user.avatar.save(filename, ContentFile(response.content), save=True)

            logger.debug(f"Updated avatar for user {user.id} from {provider}")

        except requests.RequestException as e:
            logger.warning(f"Failed to download profile picture from {provider}: {e}")
        except Exception as e:
            logger.error(f"Error saving profile picture: {e}")


class AccountLinkingService:
    """
    Service for managing social account linking operations.
    """

    @staticmethod
    def get_linked_accounts(user) -> Dict[str, Optional[SocialAccount]]:
        """
        Get all linked social accounts for a user.

        Returns:
            Dict mapping provider name to SocialAccount or None
        """
        linked = {}

        for provider in ['google', 'apple']:
            try:
                account = SocialAccount.objects.get(
                    user=user,
                    provider=provider
                )
                linked[provider] = account
            except SocialAccount.DoesNotExist:
                linked[provider] = None

        return linked

    @staticmethod
    def can_disconnect(user, provider: str) -> tuple[bool, str]:
        """
        Check if a social account can be disconnected.

        User must have either:
        - Another social account linked, OR
        - A usable password set

        Returns:
            Tuple of (can_disconnect, reason_if_not)
        """
        social_accounts = SocialAccount.objects.filter(user=user)

        # Check if user has password
        has_password = user.has_usable_password()

        # Check if user has other social accounts
        other_accounts = social_accounts.exclude(provider=provider).exists()

        if has_password or other_accounts:
            return True, ""

        return False, (
            "Cannot disconnect this account. You must either set a password "
            "or link another social account first."
        )

    @staticmethod
    @transaction.atomic
    def disconnect_account(user, provider: str) -> tuple[bool, str]:
        """
        Disconnect a social account from user.

        Returns:
            Tuple of (success, message)
        """
        can_disconnect, reason = AccountLinkingService.can_disconnect(user, provider)

        if not can_disconnect:
            return False, reason

        try:
            account = SocialAccount.objects.get(user=user, provider=provider)
            account.delete()

            logger.info(f"Disconnected {provider} from user {user.id}")
            return True, f"Successfully disconnected {provider.title()} account"

        except SocialAccount.DoesNotExist:
            return False, f"No {provider.title()} account connected"

    @staticmethod
    @transaction.atomic
    def link_account_from_oauth(
        user,
        provider: str,
        provider_user_id: str,
        extra_data: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Link a social account from OAuth callback data.

        Returns:
            Tuple of (success, message)
        """
        # Check if this social account is already linked to another user
        existing = SocialAccount.objects.filter(
            provider=provider,
            uid=provider_user_id
        ).first()

        if existing:
            if existing.user == user:
                return False, f"{provider.title()} account is already linked"
            else:
                return False, f"This {provider.title()} account is already linked to another user"

        # Check if user already has this provider linked
        user_existing = SocialAccount.objects.filter(
            user=user,
            provider=provider
        ).first()

        if user_existing:
            return False, f"You already have a {provider.title()} account linked"

        # Create the social account
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            uid=provider_user_id,
            extra_data=extra_data,
            last_login=timezone.now()
        )

        logger.info(f"Linked {provider} account to user {user.id}")
        return True, f"Successfully linked {provider.title()} account"


class ProfileSyncService:
    """
    Service for synchronizing user profile data from social accounts.
    """

    @staticmethod
    def sync_from_provider(user, provider: str) -> bool:
        """
        Sync user profile from a specific social provider.

        Returns:
            True if sync was successful
        """
        try:
            social_account = SocialAccount.objects.get(
                user=user,
                provider=provider
            )
        except SocialAccount.DoesNotExist:
            logger.warning(f"No {provider} account for user {user.id}")
            return False

        adapter = CustomSocialAccountAdapter()

        # Create a minimal sociallogin object
        from allauth.socialaccount.models import SocialLogin
        sociallogin = SocialLogin(account=social_account, user=user)

        adapter.sync_profile_from_social(user, sociallogin)
        return True

    @staticmethod
    def get_profile_data_from_social(user, provider: str) -> Optional[Dict[str, Any]]:
        """
        Get stored profile data from a social account.
        """
        try:
            social_account = SocialAccount.objects.get(
                user=user,
                provider=provider
            )
            return social_account.extra_data
        except SocialAccount.DoesNotExist:
            return None

    @staticmethod
    def update_social_extra_data(user, provider: str, extra_data: Dict[str, Any]):
        """
        Update the extra_data stored for a social account.
        """
        try:
            social_account = SocialAccount.objects.get(
                user=user,
                provider=provider
            )
            social_account.extra_data = extra_data
            social_account.save()
        except SocialAccount.DoesNotExist:
            pass
