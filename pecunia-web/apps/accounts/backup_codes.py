"""
Backup Codes Service for Two-Factor Authentication.
Provides one-time use backup codes for account recovery.
"""

import hashlib
import secrets
import string
from typing import List, Optional, Tuple

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class BackupCode(models.Model):
    """
    Model to store hashed backup codes for users.
    Each user can have multiple backup codes, but they are single-use.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='backup_codes'
    )
    code_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the backup code"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the code was used (null if unused)"
    )

    class Meta:
        app_label = 'accounts'
        verbose_name = "Backup Code"
        verbose_name_plural = "Backup Codes"
        indexes = [
            models.Index(fields=['user', 'used_at']),
        ]

    def __str__(self):
        status = "used" if self.used_at else "unused"
        return f"Backup code for {self.user.email} ({status})"

    @property
    def is_used(self) -> bool:
        """Check if the code has been used."""
        return self.used_at is not None


class BackupCodeService:
    """
    Service class for backup code operations.
    Handles generation, verification, and management of backup codes.
    """

    # Configuration
    CODE_LENGTH = getattr(settings, 'BACKUP_CODE_LENGTH', 8)
    CODE_COUNT = getattr(settings, 'BACKUP_CODE_COUNT', 10)
    CODE_CHARS = string.ascii_uppercase + string.digits
    # Exclude ambiguous characters
    CODE_CHARS = CODE_CHARS.replace('0', '').replace('O', '').replace('I', '').replace('1', '').replace('L', '')

    @classmethod
    def _hash_code(cls, code: str, salt: str = None) -> str:
        """
        Hash a backup code using PBKDF2-HMAC-SHA256.

        Args:
            code: Plain text backup code
            salt: Optional salt (defaults to Django SECRET_KEY)

        Returns:
            str: Hexadecimal hash of the code
        """
        # Accept "ABCD-EFGH" or "abcdefgh" interchangeably.
        normalized = code.upper().replace('-', '').replace(' ', '')
        key = (salt or settings.SECRET_KEY).encode('utf-8')

        # 100k iterations (~100ms) compensates for backup codes having less
        # entropy than passwords. Makes brute-force on stolen hashes impractical.
        return hashlib.pbkdf2_hmac(
            'sha256',
            normalized.encode('utf-8'),
            key,
            iterations=100_000,
        ).hex()

    @classmethod
    def _generate_single_code(cls) -> str:
        """
        Generate a single backup code.

        Returns:
            str: A random backup code (formatted with dash)
        """
        code = ''.join(secrets.choice(cls.CODE_CHARS) for _ in range(cls.CODE_LENGTH))
        # Format: XXXX-XXXX
        return f"{code[:4]}-{code[4:]}"

    @classmethod
    def generate_backup_codes(cls, user, count: int = None) -> List[str]:
        """
        Generate new backup codes for a user.
        This will invalidate any existing unused codes.

        Args:
            user: User model instance
            count: Number of codes to generate (default: CODE_COUNT)

        Returns:
            List[str]: List of plain text backup codes (SAVE THESE!)
        """
        if count is None:
            count = cls.CODE_COUNT

        with transaction.atomic():
            # Delete all existing backup codes for the user
            BackupCode.objects.filter(user=user).delete()

            # Generate new codes
            plain_codes = []
            for _ in range(count):
                code = cls._generate_single_code()
                plain_codes.append(code)

                # Store hashed version
                BackupCode.objects.create(
                    user=user,
                    code_hash=cls._hash_code(code)
                )

        return plain_codes

    @classmethod
    def verify_backup_code(cls, user, code: str) -> bool:
        """
        Verify and consume a backup code.
        If valid, the code is marked as used and cannot be reused.

        Args:
            user: User model instance
            code: The backup code to verify

        Returns:
            bool: True if code was valid and has been consumed
        """
        if not code:
            return False

        code_hash = cls._hash_code(code)

        with transaction.atomic():
            # Find matching unused code
            try:
                backup_code = BackupCode.objects.select_for_update().get(
                    user=user,
                    code_hash=code_hash,
                    used_at__isnull=True
                )
            except BackupCode.DoesNotExist:
                return False

            # Mark as used
            backup_code.used_at = timezone.now()
            backup_code.save(update_fields=['used_at'])

            return True

    @classmethod
    def get_remaining_codes_count(cls, user) -> int:
        """
        Get the count of unused backup codes for a user.

        Args:
            user: User model instance

        Returns:
            int: Number of remaining unused codes
        """
        return BackupCode.objects.filter(
            user=user,
            used_at__isnull=True
        ).count()

    @classmethod
    def get_codes_status(cls, user) -> dict:
        """
        Get detailed status of backup codes for a user.

        Args:
            user: User model instance

        Returns:
            dict: Status information including total, used, and remaining
        """
        codes = BackupCode.objects.filter(user=user)
        total = codes.count()
        used = codes.filter(used_at__isnull=False).count()

        return {
            'total': total,
            'used': used,
            'remaining': total - used,
            'has_codes': total > 0,
            'should_regenerate': (total - used) <= 2  # Warn when few codes left
        }

    @classmethod
    def has_backup_codes(cls, user) -> bool:
        """
        Check if user has any unused backup codes.

        Args:
            user: User model instance

        Returns:
            bool: True if user has unused backup codes
        """
        return BackupCode.objects.filter(
            user=user,
            used_at__isnull=True
        ).exists()

    @classmethod
    def invalidate_all_codes(cls, user) -> int:
        """
        Invalidate all backup codes for a user.

        Args:
            user: User model instance

        Returns:
            int: Number of codes deleted
        """
        deleted, _ = BackupCode.objects.filter(user=user).delete()
        return deleted


# Convenience functions for direct import
def generate_backup_codes(user, count: int = 10) -> List[str]:
    """Generate new backup codes for a user."""
    return BackupCodeService.generate_backup_codes(user, count)


def verify_backup_code(user, code: str) -> bool:
    """Verify and consume a backup code."""
    return BackupCodeService.verify_backup_code(user, code)
