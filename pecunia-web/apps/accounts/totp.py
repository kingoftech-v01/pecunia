"""
TOTP (Time-based One-Time Password) Service for Two-Factor Authentication.
Uses pyotp for TOTP generation and verification.
"""

import base64
import io
import logging
import secrets
from typing import Optional, Tuple

import pyotp
import qrcode
from django.conf import settings
from django.db import models, IntegrityError, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class TOTPDevice(models.Model):
    """
    Model to store TOTP device configuration for users.
    Each user can have one active TOTP device.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='totp_device'
    )
    secret = models.CharField(
        max_length=32,
        help_text="Base32 encoded secret key for TOTP"
    )
    name = models.CharField(
        max_length=100,
        default="Authenticator App",
        help_text="User-friendly name for the device"
    )
    confirmed = models.BooleanField(
        default=False,
        help_text="Whether the device has been verified by the user"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_counter = models.BigIntegerField(
        default=-1,
        help_text="Last successful counter to prevent replay attacks"
    )

    class Meta:
        app_label = 'accounts'
        verbose_name = "TOTP Device"
        verbose_name_plural = "TOTP Devices"

    def __str__(self):
        return f"TOTP Device for {self.user.email}"

    def verify(self, code: str) -> bool:
        """
        Verify a TOTP code against this device.
        Returns True if valid, False otherwise.
        """
        return verify_totp(self.secret, code, self)


class TOTPService:
    """
    Service class for TOTP operations.
    Provides methods for secret generation, QR codes, and verification.
    """

    # Default settings
    ISSUER_NAME = getattr(settings, 'TOTP_ISSUER_NAME', 'Pecunia')
    DIGITS = getattr(settings, 'TOTP_DIGITS', 6)
    INTERVAL = getattr(settings, 'TOTP_INTERVAL', 30)
    VALID_WINDOW = getattr(settings, 'TOTP_VALID_WINDOW', 1)

    @classmethod
    def generate_secret(cls) -> str:
        """
        Generate a new random TOTP secret.
        Returns a Base32 encoded string suitable for pyotp.

        Returns:
            str: A 32-character Base32 encoded secret
        """
        # Generate 20 bytes of random data (160 bits)
        random_bytes = secrets.token_bytes(20)
        # Encode to Base32 (standard for TOTP secrets)
        secret = base64.b32encode(random_bytes).decode('utf-8')
        return secret

    @classmethod
    def get_totp(cls, secret: str) -> pyotp.TOTP:
        """
        Create a TOTP instance from a secret.

        Args:
            secret: Base32 encoded secret

        Returns:
            pyotp.TOTP: TOTP instance configured with app settings
        """
        return pyotp.TOTP(
            secret,
            digits=cls.DIGITS,
            interval=cls.INTERVAL
        )

    @classmethod
    def verify_totp(
        cls,
        secret: str,
        code: str,
        device: Optional[TOTPDevice] = None
    ) -> bool:
        """
        Verify a TOTP code against a secret.
        Includes replay attack prevention if device is provided.

        Args:
            secret: Base32 encoded secret
            code: The 6-digit code to verify
            device: Optional TOTPDevice for replay protection

        Returns:
            bool: True if code is valid, False otherwise
        """
        if not code or not secret:
            return False

        # Clean the code (remove spaces)
        code = code.replace(' ', '').strip()

        # Validate code format
        if not code.isdigit() or len(code) != cls.DIGITS:
            return False

        totp = cls.get_totp(secret)

        # Get current counter
        current_time = timezone.now().timestamp()
        current_counter = int(current_time) // cls.INTERVAL

        if device:
            # Use atomic transaction with select_for_update for replay prevention
            with transaction.atomic():
                locked_device = TOTPDevice.objects.select_for_update().get(pk=device.pk)

                # Check for replay attack
                if current_counter <= locked_device.last_used_counter:
                    return False

                # Verify with valid window (allows for time drift)
                is_valid = totp.verify(code, valid_window=cls.VALID_WINDOW)

                if is_valid:
                    locked_device.last_used_at = timezone.now()
                    locked_device.last_used_counter = current_counter
                    locked_device.save(update_fields=['last_used_at', 'last_used_counter'])

                return is_valid
        else:
            # No device for replay tracking, just verify
            return totp.verify(code, valid_window=cls.VALID_WINDOW)

    @classmethod
    def get_provisioning_uri(cls, secret: str, email: str) -> str:
        """
        Generate the provisioning URI for authenticator apps.

        Args:
            secret: Base32 encoded secret
            email: User's email address

        Returns:
            str: otpauth:// URI for QR code generation
        """
        totp = cls.get_totp(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=cls.ISSUER_NAME
        )

    @classmethod
    def get_qr_code(
        cls,
        secret: str,
        email: str,
        format: str = 'base64'
    ) -> str:
        """
        Generate a QR code image for the TOTP secret.

        Args:
            secret: Base32 encoded secret
            email: User's email address
            format: Output format - 'base64' or 'svg'

        Returns:
            str: QR code as base64 data URI or SVG string
        """
        uri = cls.get_provisioning_uri(secret, email)

        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        if format == 'svg':
            # Generate SVG
            from qrcode.image.svg import SvgImage
            img = qr.make_image(image_factory=SvgImage)
            buffer = io.BytesIO()
            img.save(buffer)
            return buffer.getvalue().decode('utf-8')
        else:
            # Generate PNG as base64
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"

    @classmethod
    def setup_device(cls, user) -> Tuple[TOTPDevice, str]:
        """
        Set up a new TOTP device for a user.
        Removes any existing unconfirmed device.

        Args:
            user: User model instance

        Returns:
            Tuple[TOTPDevice, str]: The device and QR code data URI
        """
        # Check if user already has a confirmed device
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            raise IntegrityError("User already has 2FA enabled. Disable it first before setting up a new device.")

        # Remove any existing unconfirmed device
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()

        # Generate new secret
        secret = cls.generate_secret()

        # Create device
        try:
            device = TOTPDevice.objects.create(
                user=user,
                secret=secret,
                confirmed=False
            )
        except IntegrityError:
            logger.warning("Attempted to create duplicate TOTP device for user %s", user.pk)
            raise

        # Generate QR code
        qr_code = cls.get_qr_code(secret, user.email)

        return device, qr_code

    @classmethod
    def confirm_device(cls, device: TOTPDevice, code: str) -> bool:
        """
        Confirm a TOTP device by verifying a code.

        Args:
            device: TOTPDevice to confirm
            code: TOTP code from authenticator app

        Returns:
            bool: True if confirmed successfully
        """
        if device.confirmed:
            return True

        if cls.verify_totp(device.secret, code, device):
            device.confirmed = True
            device.save(update_fields=['confirmed'])
            return True

        return False

    @classmethod
    def get_user_device(cls, user) -> Optional[TOTPDevice]:
        """
        Get the confirmed TOTP device for a user.

        Args:
            user: User model instance

        Returns:
            Optional[TOTPDevice]: The device or None
        """
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=True)
            return device
        except TOTPDevice.DoesNotExist:
            return None

    @classmethod
    def is_2fa_enabled(cls, user) -> bool:
        """
        Check if 2FA is enabled for a user.

        Args:
            user: User model instance

        Returns:
            bool: True if 2FA is enabled
        """
        return cls.get_user_device(user) is not None

    @classmethod
    def disable_2fa(cls, user) -> bool:
        """
        Disable 2FA for a user by removing their device.

        Args:
            user: User model instance

        Returns:
            bool: True if device was removed
        """
        deleted, _ = TOTPDevice.objects.filter(user=user).delete()
        return deleted > 0


# Convenience functions for direct import
def generate_secret() -> str:
    """Generate a new TOTP secret."""
    return TOTPService.generate_secret()


def verify_totp(secret: str, code: str, device: Optional[TOTPDevice] = None) -> bool:
    """Verify a TOTP code."""
    return TOTPService.verify_totp(secret, code, device)


def get_qr_code(secret: str, email: str, format: str = 'base64') -> str:
    """Generate QR code for TOTP setup."""
    return TOTPService.get_qr_code(secret, email, format)
