"""
Two-Factor Authentication Views for Pecunia.
Handles setup, verification, and management of 2FA.
"""

import json
import logging
from datetime import timedelta
from functools import wraps
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, TimestampSigner
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .totp import TOTPService, TOTPDevice
from .backup_codes import BackupCodeService, generate_backup_codes

logger = logging.getLogger(__name__)

User = get_user_model()

# Cookie settings for trusted devices
TRUSTED_DEVICE_COOKIE_NAME = 'pecunia_2fa_trusted'
TRUSTED_DEVICE_MAX_AGE = getattr(settings, 'TRUSTED_DEVICE_MAX_AGE', 30 * 24 * 60 * 60)  # 30 days


class TrustedDeviceManager:
    """
    Manages trusted device cookies using Django's signing framework.
    """

    @staticmethod
    def _get_signer() -> TimestampSigner:
        """Get a timestamp signer for device tokens."""
        return TimestampSigner(salt='2fa-trusted-device')

    @classmethod
    def create_trusted_token(cls, user) -> str:
        """
        Create a signed token for a trusted device.

        Args:
            user: User model instance

        Returns:
            str: Signed token
        """
        signer = cls._get_signer()
        # Include email so token invalidates if user changes email address.
        data = f"{user.pk}:{user.email}"
        return signer.sign(data)

    @classmethod
    def verify_trusted_token(cls, token: str, user) -> bool:
        """
        Verify a trusted device token.

        Args:
            token: The signed token from cookie
            user: User model instance

        Returns:
            bool: True if token is valid and matches user
        """
        if not token:
            return False

        signer = cls._get_signer()
        try:
            # max_age enforces expiration server-side even if cookie persists.
            data = signer.unsign(token, max_age=TRUSTED_DEVICE_MAX_AGE)
            expected_data = f"{user.pk}:{user.email}"
            return data == expected_data
        except BadSignature:
            return False

    @classmethod
    def set_trusted_cookie(cls, response: HttpResponse, user) -> HttpResponse:
        """
        Set the trusted device cookie on a response.

        Args:
            response: HttpResponse to modify
            user: User model instance

        Returns:
            HttpResponse: Modified response with cookie
        """
        token = cls.create_trusted_token(user)
        response.set_cookie(
            TRUSTED_DEVICE_COOKIE_NAME,
            token,
            max_age=TRUSTED_DEVICE_MAX_AGE,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax'
        )
        return response

    @classmethod
    def clear_trusted_cookie(cls, response: HttpResponse) -> HttpResponse:
        """
        Clear the trusted device cookie.

        Args:
            response: HttpResponse to modify

        Returns:
            HttpResponse: Modified response with cookie deleted
        """
        response.delete_cookie(TRUSTED_DEVICE_COOKIE_NAME)
        return response

    @classmethod
    def is_device_trusted(cls, request: HttpRequest, user) -> bool:
        """
        Check if the current device is trusted for the user.

        Args:
            request: HttpRequest object
            user: User model instance

        Returns:
            bool: True if device is trusted
        """
        token = request.COOKIES.get(TRUSTED_DEVICE_COOKIE_NAME)
        return cls.verify_trusted_token(token, user)


def requires_2fa_setup(view_func):
    """
    Decorator to ensure 2FA is set up before accessing a view.
    Redirects to 2FA setup if not configured.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not TOTPService.is_2fa_enabled(request.user):
            messages.warning(request, 'Please set up two-factor authentication first.')
            return redirect('accounts:setup_2fa')
        return view_func(request, *args, **kwargs)
    return wrapper


def requires_2fa_verification(view_func):
    """
    Decorator to require 2FA verification for sensitive operations.
    Can be used on views that need extra security.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not TOTPService.is_2fa_enabled(request.user):
            return view_func(request, *args, **kwargs)

        # Check if verified recently (within 5 minutes)
        last_verified = request.session.get('2fa_verified_at')
        if last_verified:
            from datetime import datetime
            verified_time = datetime.fromisoformat(last_verified)
            if timezone.now() - verified_time < timedelta(minutes=5):
                return view_func(request, *args, **kwargs)

        # Store the intended destination
        request.session['2fa_next'] = request.get_full_path()
        return redirect('accounts:verify_2fa')

    return wrapper


@login_required
@require_http_methods(["GET", "POST"])
def setup_2fa(request: HttpRequest) -> HttpResponse:
    """
    View for setting up two-factor authentication.
    Displays QR code and verifies initial setup.
    """
    user = request.user

    # Check if already set up
    existing_device = TOTPService.get_user_device(user)
    if existing_device:
        messages.info(request, 'Two-factor authentication is already enabled.')
        return redirect('accounts:manage_2fa')

    if request.method == 'POST':
        # Verify the code to confirm setup
        code = request.POST.get('code', '').strip()

        try:
            device = TOTPDevice.objects.get(user=user, confirmed=False)
        except TOTPDevice.DoesNotExist:
            messages.error(request, 'Setup session expired. Please start again.')
            return redirect('accounts:setup_2fa')

        if TOTPService.confirm_device(device, code):
            # Generate backup codes
            backup_codes = generate_backup_codes(user)

            # Store codes in session for display
            request.session['backup_codes'] = backup_codes
            request.session['backup_codes_shown'] = False

            messages.success(request, 'Two-factor authentication enabled successfully!')
            logger.info(f"2FA enabled for user {user.email}")

            return redirect('accounts:show_backup_codes')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')

    # GET request or failed POST - show setup form
    device, qr_code = TOTPService.setup_device(user)

    # Format secret for manual entry (groups of 4)
    secret_formatted = ' '.join(
        device.secret[i:i+4] for i in range(0, len(device.secret), 4)
    )

    context = {
        'qr_code': qr_code,
        'secret': secret_formatted,
        'secret_raw': device.secret,
    }

    return render(request, 'accounts/2fa_setup.html', context)


@login_required
def show_backup_codes(request: HttpRequest) -> HttpResponse:
    """
    Display backup codes after 2FA setup.
    Codes are shown only once and must be saved by user.
    """
    backup_codes = request.session.get('backup_codes')

    if not backup_codes:
        messages.warning(request, 'No backup codes to display.')
        return redirect('accounts:manage_2fa')

    # Mark as shown
    request.session['backup_codes_shown'] = True

    # Clear from session after displaying
    if request.method == 'POST' and request.POST.get('confirmed'):
        del request.session['backup_codes']
        del request.session['backup_codes_shown']
        messages.success(request, 'Backup codes saved. Keep them in a safe place!')
        return redirect('accounts:manage_2fa')

    context = {
        'backup_codes': backup_codes,
    }

    return render(request, 'accounts/backup_codes.html', context)


@require_http_methods(["GET", "POST"])
def verify_2fa(request: HttpRequest) -> HttpResponse:
    """
    View for verifying 2FA code during login or sensitive operations.
    """
    # Get user from session (set during login)
    user_id = request.session.get('2fa_user_id')

    if request.user.is_authenticated:
        user = request.user
    elif user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            messages.error(request, 'Session expired. Please log in again.')
            return redirect('accounts:login')
    else:
        return redirect('accounts:login')

    # Check if 2FA is enabled
    device = TOTPService.get_user_device(user)
    if not device:
        # No 2FA, complete login
        if not request.user.is_authenticated:
            from django.contrib.auth import login
            login(request, user)
        return redirect(request.session.get('2fa_next', 'dashboard'))

    # Check if device is trusted
    if TrustedDeviceManager.is_device_trusted(request, user):
        if not request.user.is_authenticated:
            from django.contrib.auth import login
            login(request, user)
        request.session['2fa_verified_at'] = timezone.now().isoformat()
        return redirect(request.session.get('2fa_next', 'dashboard'))

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        use_backup = request.POST.get('use_backup') == '1'
        remember_device = request.POST.get('remember_device') == '1'

        is_valid = False

        if use_backup:
            # Verify backup code
            is_valid = BackupCodeService.verify_backup_code(user, code)
            if is_valid:
                logger.info(f"2FA verified with backup code for {user.email}")
                # Check remaining codes
                remaining = BackupCodeService.get_remaining_codes_count(user)
                if remaining <= 2:
                    messages.warning(
                        request,
                        f'You have only {remaining} backup codes remaining. '
                        'Consider generating new ones.'
                    )
        else:
            # Verify TOTP code
            is_valid = device.verify(code)
            if is_valid:
                logger.info(f"2FA verified with TOTP for {user.email}")

        if is_valid:
            # Complete authentication
            if not request.user.is_authenticated:
                from django.contrib.auth import login
                login(request, user)
                # Clean up session
                if '2fa_user_id' in request.session:
                    del request.session['2fa_user_id']

            # Mark as verified
            request.session['2fa_verified_at'] = timezone.now().isoformat()

            # Get redirect URL
            next_url = request.session.pop('2fa_next', None) or 'dashboard'

            response = redirect(next_url)

            # Set trusted device cookie if requested
            if remember_device:
                TrustedDeviceManager.set_trusted_cookie(response, user)

            return response
        else:
            messages.error(request, 'Invalid verification code. Please try again.')

    # GET request
    backup_status = BackupCodeService.get_codes_status(user)

    context = {
        'has_backup_codes': backup_status['has_codes'],
        'backup_codes_remaining': backup_status['remaining'],
    }

    return render(request, 'accounts/2fa_verify.html', context)


@login_required
@require_POST
def disable_2fa(request: HttpRequest) -> HttpResponse:
    """
    Disable two-factor authentication.
    Requires current password or backup code verification.
    """
    user = request.user

    if not TOTPService.is_2fa_enabled(user):
        messages.info(request, 'Two-factor authentication is not enabled.')
        return redirect('accounts:manage_2fa')

    # Verify password
    password = request.POST.get('password', '')
    if not user.check_password(password):
        messages.error(request, 'Invalid password.')
        return redirect('accounts:manage_2fa')

    # Disable 2FA
    TOTPService.disable_2fa(user)
    BackupCodeService.invalidate_all_codes(user)

    # Clear trusted device
    response = redirect('accounts:manage_2fa')
    TrustedDeviceManager.clear_trusted_cookie(response)

    messages.success(request, 'Two-factor authentication has been disabled.')
    logger.info(f"2FA disabled for user {user.email}")

    return response


@login_required
@require_POST
def regenerate_backup_codes(request: HttpRequest) -> HttpResponse:
    """
    Generate new backup codes, invalidating old ones.
    """
    user = request.user

    if not TOTPService.is_2fa_enabled(user):
        messages.error(request, 'Two-factor authentication must be enabled first.')
        return redirect('accounts:setup_2fa')

    # Verify current code or password
    verification = request.POST.get('verification', '')
    device = TOTPService.get_user_device(user)

    is_verified = (
        device.verify(verification) or
        user.check_password(verification)
    )

    if not is_verified:
        messages.error(request, 'Invalid verification. Please enter your current 2FA code or password.')
        return redirect('accounts:manage_2fa')

    # Generate new codes
    backup_codes = generate_backup_codes(user)
    request.session['backup_codes'] = backup_codes
    request.session['backup_codes_shown'] = False

    messages.success(request, 'New backup codes generated. Your old codes are now invalid.')
    logger.info(f"Backup codes regenerated for {user.email}")

    return redirect('accounts:show_backup_codes')


@login_required
def manage_2fa(request: HttpRequest) -> HttpResponse:
    """
    Main 2FA management page.
    Shows status and provides options to enable/disable.
    """
    user = request.user
    is_enabled = TOTPService.is_2fa_enabled(user)

    context = {
        'is_2fa_enabled': is_enabled,
    }

    if is_enabled:
        device = TOTPService.get_user_device(user)
        backup_status = BackupCodeService.get_codes_status(user)

        context.update({
            'device': device,
            'backup_codes_remaining': backup_status['remaining'],
            'should_regenerate_codes': backup_status['should_regenerate'],
        })

    return render(request, 'accounts/manage_2fa.html', context)


@login_required
def revoke_trusted_devices(request: HttpRequest) -> HttpResponse:
    """
    Revoke all trusted devices for the user.
    This is done by changing the signing salt (affects all users)
    or by adding a user-specific token version.
    """
    if request.method == 'POST':
        # For per-user revocation, we'd need to store a version number
        # For now, clear the current device's cookie
        response = redirect('accounts:manage_2fa')
        TrustedDeviceManager.clear_trusted_cookie(response)
        messages.success(request, 'Trusted devices have been revoked.')
        return response

    return redirect('accounts:manage_2fa')


# API Views for AJAX/SPA support

@login_required
@require_POST
def api_verify_2fa(request: HttpRequest) -> JsonResponse:
    """
    API endpoint for 2FA verification.
    Returns JSON response for AJAX requests.
    """
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        use_backup = data.get('use_backup', False)
    except json.JSONDecodeError:
        code = request.POST.get('code', '')
        use_backup = request.POST.get('use_backup') == '1'

    user = request.user
    device = TOTPService.get_user_device(user)

    if not device:
        return JsonResponse({
            'success': True,
            'message': '2FA not enabled',
            '2fa_required': False,
        })

    if use_backup:
        is_valid = BackupCodeService.verify_backup_code(user, code)
    else:
        is_valid = device.verify(code)

    if is_valid:
        request.session['2fa_verified_at'] = timezone.now().isoformat()
        return JsonResponse({
            'success': True,
            'message': 'Verification successful',
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Invalid verification code',
        }, status=400)


@login_required
def api_2fa_status(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to get 2FA status for the current user.
    """
    user = request.user
    is_enabled = TOTPService.is_2fa_enabled(user)

    response_data = {
        'enabled': is_enabled,
    }

    if is_enabled:
        backup_status = BackupCodeService.get_codes_status(user)
        response_data['backup_codes_remaining'] = backup_status['remaining']

    return JsonResponse(response_data)
