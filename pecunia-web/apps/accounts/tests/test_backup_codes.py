"""
Tests for accounts.backup_codes module.

Covers BackupCode model, BackupCodeService, and convenience functions
with all branches including generation, verification, and management.
"""
import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.backup_codes import (
    BackupCode,
    BackupCodeService,
    generate_backup_codes,
    verify_backup_code,
)


# ---------------------------------------------------------------------------
# BackupCode model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBackupCodeModel:
    """Tests for the BackupCode model."""

    def test_create_backup_code(self, user):
        code = BackupCode.objects.create(
            user=user,
            code_hash="abc123hash",
        )
        assert code.pk is not None
        assert code.used_at is None

    def test_str_unused(self, user):
        code = BackupCode.objects.create(
            user=user,
            code_hash="abc123hash",
        )
        assert "unused" in str(code)
        assert user.email in str(code)

    def test_str_used(self, user):
        code = BackupCode.objects.create(
            user=user,
            code_hash="abc123hash",
            used_at=timezone.now(),
        )
        assert "used" in str(code)

    def test_is_used_property_false(self, user):
        code = BackupCode.objects.create(
            user=user,
            code_hash="abc123hash",
        )
        assert code.is_used is False

    def test_is_used_property_true(self, user):
        code = BackupCode.objects.create(
            user=user,
            code_hash="abc123hash",
            used_at=timezone.now(),
        )
        assert code.is_used is True

    def test_verbose_names(self):
        assert BackupCode._meta.verbose_name == "Backup Code"
        assert BackupCode._meta.verbose_name_plural == "Backup Codes"


# ---------------------------------------------------------------------------
# BackupCodeService tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBackupCodeService:
    """Tests for BackupCodeService."""

    def test_generate_backup_codes_default_count(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        assert len(codes) == BackupCodeService.CODE_COUNT
        assert BackupCode.objects.filter(user=user).count() == BackupCodeService.CODE_COUNT

    def test_generate_backup_codes_custom_count(self, user):
        codes = BackupCodeService.generate_backup_codes(user, count=5)
        assert len(codes) == 5
        assert BackupCode.objects.filter(user=user).count() == 5

    def test_generate_backup_codes_format(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        for code in codes:
            # Format: XXXX-XXXX
            assert "-" in code
            parts = code.split("-")
            assert len(parts) == 2
            assert len(parts[0]) == 4
            assert len(parts[1]) == 4

    def test_generate_backup_codes_replaces_existing(self, user):
        first_codes = BackupCodeService.generate_backup_codes(user)
        second_codes = BackupCodeService.generate_backup_codes(user)
        # Old codes should be deleted
        assert BackupCode.objects.filter(user=user).count() == BackupCodeService.CODE_COUNT
        # Codes should be different
        assert set(first_codes) != set(second_codes)

    def test_generate_backup_codes_no_ambiguous_chars(self, user):
        """Generated codes should not contain 0, O, I, 1, L."""
        codes = BackupCodeService.generate_backup_codes(user, count=20)
        for code in codes:
            clean = code.replace("-", "")
            for ch in "0OI1L":
                assert ch not in clean

    def test_verify_backup_code_valid(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        assert BackupCodeService.verify_backup_code(user, codes[0]) is True

    def test_verify_backup_code_marks_as_used(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        BackupCodeService.verify_backup_code(user, codes[0])
        # Code should now be used
        used = BackupCode.objects.filter(user=user, used_at__isnull=False).count()
        assert used == 1

    def test_verify_backup_code_cannot_reuse(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        assert BackupCodeService.verify_backup_code(user, codes[0]) is True
        assert BackupCodeService.verify_backup_code(user, codes[0]) is False

    def test_verify_backup_code_invalid(self, user):
        BackupCodeService.generate_backup_codes(user)
        assert BackupCodeService.verify_backup_code(user, "XXXX-XXXX") is False

    def test_verify_backup_code_empty(self, user):
        assert BackupCodeService.verify_backup_code(user, "") is False

    def test_verify_backup_code_none(self, user):
        assert BackupCodeService.verify_backup_code(user, None) is False

    def test_verify_backup_code_case_insensitive(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        lower_code = codes[0].lower()
        assert BackupCodeService.verify_backup_code(user, lower_code) is True

    def test_verify_backup_code_with_spaces(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        spaced = codes[0].replace("-", " ")
        assert BackupCodeService.verify_backup_code(user, spaced) is True

    def test_verify_backup_code_without_dashes(self, user):
        codes = BackupCodeService.generate_backup_codes(user)
        nodash = codes[0].replace("-", "")
        assert BackupCodeService.verify_backup_code(user, nodash) is True

    def test_get_remaining_codes_count(self, user):
        codes = BackupCodeService.generate_backup_codes(user, count=5)
        assert BackupCodeService.get_remaining_codes_count(user) == 5
        # Use one
        BackupCodeService.verify_backup_code(user, codes[0])
        assert BackupCodeService.get_remaining_codes_count(user) == 4

    def test_get_remaining_codes_count_zero(self, user):
        assert BackupCodeService.get_remaining_codes_count(user) == 0

    def test_get_codes_status(self, user):
        codes = BackupCodeService.generate_backup_codes(user, count=5)
        BackupCodeService.verify_backup_code(user, codes[0])

        status = BackupCodeService.get_codes_status(user)
        assert status["total"] == 5
        assert status["used"] == 1
        assert status["remaining"] == 4
        assert status["has_codes"] is True
        assert status["should_regenerate"] is False

    def test_get_codes_status_empty(self, user):
        status = BackupCodeService.get_codes_status(user)
        assert status["total"] == 0
        assert status["used"] == 0
        assert status["remaining"] == 0
        assert status["has_codes"] is False
        assert status["should_regenerate"] is True

    def test_get_codes_status_should_regenerate(self, user):
        codes = BackupCodeService.generate_backup_codes(user, count=3)
        BackupCodeService.verify_backup_code(user, codes[0])
        # 2 remaining - at threshold
        status = BackupCodeService.get_codes_status(user)
        assert status["should_regenerate"] is True

    def test_has_backup_codes_true(self, user):
        BackupCodeService.generate_backup_codes(user)
        assert BackupCodeService.has_backup_codes(user) is True

    def test_has_backup_codes_false(self, user):
        assert BackupCodeService.has_backup_codes(user) is False

    def test_has_backup_codes_all_used(self, user):
        codes = BackupCodeService.generate_backup_codes(user, count=2)
        for code in codes:
            BackupCodeService.verify_backup_code(user, code)
        assert BackupCodeService.has_backup_codes(user) is False

    def test_invalidate_all_codes(self, user):
        BackupCodeService.generate_backup_codes(user, count=5)
        deleted = BackupCodeService.invalidate_all_codes(user)
        assert deleted == 5
        assert BackupCode.objects.filter(user=user).count() == 0

    def test_invalidate_all_codes_empty(self, user):
        deleted = BackupCodeService.invalidate_all_codes(user)
        assert deleted == 0

    def test_codes_isolated_per_user(self, user, user2):
        codes1 = BackupCodeService.generate_backup_codes(user, count=3)
        codes2 = BackupCodeService.generate_backup_codes(user2, count=3)
        # User1's code should not work for user2
        assert BackupCodeService.verify_backup_code(user2, codes1[0]) is False
        assert BackupCodeService.verify_backup_code(user, codes2[0]) is False

    def test_hash_code_deterministic(self):
        hash1 = BackupCodeService._hash_code("ABCD-EFGH")
        hash2 = BackupCodeService._hash_code("ABCD-EFGH")
        assert hash1 == hash2

    def test_hash_code_normalizes_case(self):
        hash1 = BackupCodeService._hash_code("abcd-efgh")
        hash2 = BackupCodeService._hash_code("ABCD-EFGH")
        assert hash1 == hash2

    def test_hash_code_normalizes_dashes(self):
        hash1 = BackupCodeService._hash_code("ABCDEFGH")
        hash2 = BackupCodeService._hash_code("ABCD-EFGH")
        assert hash1 == hash2

    def test_hash_code_normalizes_spaces(self):
        hash1 = BackupCodeService._hash_code("ABCDEFGH")
        hash2 = BackupCodeService._hash_code("ABCD EFGH")
        assert hash1 == hash2


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_backup_codes_function(self, user):
        codes = generate_backup_codes(user, count=5)
        assert len(codes) == 5

    def test_verify_backup_code_function(self, user):
        codes = generate_backup_codes(user)
        assert verify_backup_code(user, codes[0]) is True
        assert verify_backup_code(user, "XXXX-XXXX") is False
