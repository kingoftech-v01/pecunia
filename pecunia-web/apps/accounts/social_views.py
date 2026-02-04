"""
OAuth Social Authentication Views for Pecunia
Handles OAuth redirects, callbacks, and account linking.
"""

import logging
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from allauth.socialaccount.models import SocialAccount

from .oauth import (
    get_oauth_provider,
    get_oauth_url,
    handle_callback,
    OAuthError,
    OAuthStateError,
    OAuthTokenError,
    OAuthUserInfoError,
    OAuthUserInfo,
    OAUTH_PROVIDERS,
)
from .adapters import AccountLinkingService, ProfileSyncService

logger = logging.getLogger(__name__)
User = get_user_model()


class OAuthRedirectView(View):
    """
    Initiates OAuth flow by redirecting to the provider.

    URL: /auth/oauth/<provider>/
    """

    def get(self, request: HttpRequest, provider: str) -> HttpResponse:
        """
        Redirect user to OAuth provider for authentication.
        """
        # Validate provider
        if provider not in OAUTH_PROVIDERS:
            messages.error(request, f"Unsupported authentication provider: {provider}")
            return redirect('accounts:login')

        # Get redirect URL from query params
        redirect_url = request.GET.get('next', '')

        # Check if this is an account linking request
        link_to_user_id = None
        if request.user.is_authenticated:
            link_to_user_id = request.user.id

        try:
            # Generate OAuth URL
            oauth_url = get_oauth_url(
                request=request,
                provider_name=provider,
                redirect_url=redirect_url,
                link_to_user_id=link_to_user_id
            )

            logger.info(f"Redirecting to {provider} OAuth")
            return HttpResponseRedirect(oauth_url)

        except Exception as e:
            logger.error(f"Failed to generate OAuth URL for {provider}: {e}")
            messages.error(request, "Failed to initiate authentication. Please try again.")
            return redirect('accounts:login')


class OAuthCallbackView(View):
    """
    Handles OAuth callback from providers.

    URL: /auth/oauth/<provider>/callback/
    """

    def get(self, request: HttpRequest, provider: str) -> HttpResponse:
        """
        Handle GET callback (used by Google).
        """
        return self._handle_callback(request, provider)

    def post(self, request: HttpRequest, provider: str) -> HttpResponse:
        """
        Handle POST callback (used by Apple Sign-In).
        """
        return self._handle_callback(request, provider)

    def _handle_callback(self, request: HttpRequest, provider: str) -> HttpResponse:
        """
        Process OAuth callback.
        """
        # Validate provider
        if provider not in OAUTH_PROVIDERS:
            messages.error(request, f"Unsupported authentication provider: {provider}")
            return redirect('accounts:login')

        # Get callback parameters
        code = request.GET.get('code') or request.POST.get('code')
        state = request.GET.get('state') or request.POST.get('state')
        error = request.GET.get('error') or request.POST.get('error')
        error_description = (
            request.GET.get('error_description') or
            request.POST.get('error_description')
        )

        # Handle provider errors
        if error:
            logger.warning(f"OAuth error from {provider}: {error} - {error_description}")

            if error == 'access_denied':
                messages.info(request, "Authentication was cancelled.")
            else:
                messages.error(
                    request,
                    f"Authentication failed: {error_description or error}"
                )

            return redirect('accounts:login')

        # Validate required parameters
        if not code or not state:
            messages.error(request, "Invalid authentication response.")
            return redirect('accounts:login')

        try:
            # Handle provider-specific callback
            kwargs = {}
            if provider == 'apple':
                # Apple sends user data in POST body on first auth
                user_data = request.POST.get('user')
                if user_data:
                    kwargs['user_data'] = user_data

            # Process callback
            user_info, state_data = handle_callback(
                request=request,
                provider_name=provider,
                code=code,
                state=state,
                **kwargs
            )

            # Check if this is an account linking request
            if state_data.get('link_to_user_id'):
                return self._handle_account_linking(
                    request,
                    user_info,
                    state_data
                )

            # Handle login/signup
            return self._handle_login_or_signup(
                request,
                user_info,
                state_data
            )

        except OAuthStateError as e:
            logger.warning(f"OAuth state error: {e}")
            messages.error(
                request,
                "Authentication session expired. Please try again."
            )
            return redirect('accounts:login')

        except OAuthTokenError as e:
            logger.error(f"OAuth token error: {e}")
            messages.error(
                request,
                "Failed to complete authentication. Please try again."
            )
            return redirect('accounts:login')

        except OAuthUserInfoError as e:
            logger.error(f"OAuth user info error: {e}")
            messages.error(
                request,
                "Failed to retrieve account information. Please try again."
            )
            return redirect('accounts:login')

        except Exception as e:
            logger.exception(f"Unexpected OAuth error: {e}")
            messages.error(
                request,
                "An unexpected error occurred. Please try again."
            )
            return redirect('accounts:login')

    def _handle_login_or_signup(
        self,
        request: HttpRequest,
        user_info: OAuthUserInfo,
        state_data: dict
    ) -> HttpResponse:
        """
        Handle login for existing user or create new account.
        """
        provider = user_info.provider

        # Check if social account exists
        try:
            social_account = SocialAccount.objects.get(
                provider=provider,
                uid=user_info.provider_user_id
            )
            user = social_account.user

            # Update extra data
            social_account.extra_data = user_info.raw_data or {}
            social_account.save()

            # Log user in
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            logger.info(f"User {user.id} logged in via {provider}")
            messages.success(request, f"Welcome back!")

            # Redirect
            redirect_url = state_data.get('redirect_url') or settings.LOGIN_REDIRECT_URL
            return redirect(redirect_url)

        except SocialAccount.DoesNotExist:
            pass

        # Check if user exists with same email
        if user_info.email:
            try:
                user = User.objects.get(email__iexact=user_info.email)

                # Email exists - check if verified from provider
                if user_info.email_verified:
                    # Auto-link and login
                    SocialAccount.objects.create(
                        user=user,
                        provider=provider,
                        uid=user_info.provider_user_id,
                        extra_data=user_info.raw_data or {}
                    )

                    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                    logger.info(f"Auto-linked {provider} to user {user.id}")
                    messages.success(
                        request,
                        f"Your {provider.title()} account has been linked."
                    )

                    redirect_url = state_data.get('redirect_url') or settings.LOGIN_REDIRECT_URL
                    return redirect(redirect_url)
                else:
                    # Require manual linking
                    messages.warning(
                        request,
                        f"An account with this email already exists. "
                        f"Please log in with your password to link your {provider.title()} account."
                    )
                    return redirect('accounts:login')

            except User.DoesNotExist:
                pass
            except User.MultipleObjectsReturned:
                logger.error(f"Multiple users with email {user_info.email}")
                messages.error(request, "Account error. Please contact support.")
                return redirect('accounts:login')

        # Create new user
        if not getattr(settings, 'SOCIALACCOUNT_ALLOW_REGISTRATION', True):
            messages.error(request, "New account registration is currently disabled.")
            return redirect('accounts:login')

        user = self._create_user_from_oauth(user_info)

        # Create social account
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            uid=user_info.provider_user_id,
            extra_data=user_info.raw_data or {}
        )

        # Log user in
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        logger.info(f"Created new user {user.id} via {provider}")
        messages.success(request, "Welcome to Pecunia! Your account has been created.")

        redirect_url = state_data.get('redirect_url') or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_url)

    def _create_user_from_oauth(self, user_info: OAuthUserInfo) -> User:
        """
        Create a new user from OAuth user info.
        """
        # Generate username from email
        base_username = user_info.email.split('@')[0] if user_info.email else 'user'
        username = base_username
        counter = 1

        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=user_info.email,
            first_name=user_info.first_name,
            last_name=user_info.last_name,
        )

        # Mark email as verified if provider verified it
        if user_info.email_verified and hasattr(user, 'emailaddress_set'):
            from allauth.account.models import EmailAddress
            EmailAddress.objects.create(
                user=user,
                email=user_info.email,
                verified=True,
                primary=True
            )

        return user

    def _handle_account_linking(
        self,
        request: HttpRequest,
        user_info: OAuthUserInfo,
        state_data: dict
    ) -> HttpResponse:
        """
        Handle linking OAuth account to existing user.
        """
        user_id = state_data.get('link_to_user_id')
        provider = user_info.provider

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User account not found.")
            return redirect('accounts:login')

        # Ensure current user matches
        if not request.user.is_authenticated or request.user.id != user_id:
            messages.error(request, "Session expired. Please try again.")
            return redirect('accounts:settings')

        # Link the account
        success, message = AccountLinkingService.link_account_from_oauth(
            user=user,
            provider=provider,
            provider_user_id=user_info.provider_user_id,
            extra_data=user_info.raw_data or {}
        )

        if success:
            messages.success(request, message)

            # Sync profile if requested
            ProfileSyncService.sync_from_provider(user, provider)
        else:
            messages.error(request, message)

        redirect_url = state_data.get('redirect_url') or '/settings/accounts/'
        return redirect(redirect_url)


@method_decorator(csrf_protect, name='dispatch')
class LinkAccountView(LoginRequiredMixin, View):
    """
    Initiate linking of a social account to current user.

    URL: /auth/link/<provider>/
    """

    def get(self, request: HttpRequest, provider: str) -> HttpResponse:
        """
        Redirect to OAuth flow for account linking.
        """
        if provider not in OAUTH_PROVIDERS:
            messages.error(request, f"Unsupported provider: {provider}")
            return redirect('accounts:settings')

        # Check if already linked
        if SocialAccount.objects.filter(user=request.user, provider=provider).exists():
            messages.info(request, f"Your {provider.title()} account is already linked.")
            return redirect('accounts:settings')

        try:
            oauth_url = get_oauth_url(
                request=request,
                provider_name=provider,
                redirect_url='/settings/accounts/',
                link_to_user_id=request.user.id
            )
            return HttpResponseRedirect(oauth_url)

        except Exception as e:
            logger.error(f"Failed to initiate account linking: {e}")
            messages.error(request, "Failed to initiate account linking. Please try again.")
            return redirect('accounts:settings')


@method_decorator(csrf_protect, name='dispatch')
class UnlinkAccountView(LoginRequiredMixin, View):
    """
    Unlink a social account from current user.

    URL: /auth/unlink/<provider>/
    """

    def post(self, request: HttpRequest, provider: str) -> HttpResponse:
        """
        Disconnect a social account.
        """
        success, message = AccountLinkingService.disconnect_account(
            user=request.user,
            provider=provider
        )

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': success,
                'message': message
            })

        return redirect('accounts:settings')


class LinkedAccountsView(LoginRequiredMixin, View):
    """
    View linked social accounts.

    URL: /auth/accounts/
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Display linked accounts.
        """
        linked_accounts = AccountLinkingService.get_linked_accounts(request.user)

        context = {
            'linked_accounts': linked_accounts,
            'has_password': request.user.has_usable_password(),
        }

        return render(request, 'accounts/linked_accounts.html', context)


@login_required
@require_http_methods(['POST'])
def sync_profile_from_social(request: HttpRequest, provider: str) -> HttpResponse:
    """
    Sync user profile from a social provider.

    URL: /auth/sync/<provider>/
    """
    success = ProfileSyncService.sync_from_provider(request.user, provider)

    if success:
        messages.success(request, f"Profile synced from {provider.title()}")
    else:
        messages.error(request, f"Failed to sync profile from {provider.title()}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success})

    return redirect('accounts:settings')


# Convenience view for OAuth connect page
class OAuthConnectView(View):
    """
    Display OAuth connection options.

    URL: /auth/connect/
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Show OAuth connection page.
        """
        context = {
            'providers': list(OAUTH_PROVIDERS.keys()),
            'next': request.GET.get('next', ''),
        }

        if request.user.is_authenticated:
            context['linked_accounts'] = AccountLinkingService.get_linked_accounts(
                request.user
            )

        return render(request, 'accounts/oauth_connect.html', context)


# URL patterns helper
oauth_redirect = OAuthRedirectView.as_view()
oauth_callback = OAuthCallbackView.as_view()
link_account = LinkAccountView.as_view()
unlink_account = UnlinkAccountView.as_view()
linked_accounts = LinkedAccountsView.as_view()
oauth_connect = OAuthConnectView.as_view()
