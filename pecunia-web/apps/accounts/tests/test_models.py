"""
Tests for accounts.models module.

Covers User, UserProfile, and UserManager with all methods, branches, and edge cases.
"""
import uuid

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User, UserProfile, UserManager


# ---------------------------------------------------------------------------
# UserManager tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserManager:
    """Tests for UserManager custom manager."""

    def test_create_user_with_email_and_password(self):
        user = User.objects.create_user(
            email="normal@example.com",
            password="SomeP@ssw0rd12!",
        )
        assert user.email == "normal@example.com"
        assert user.check_password("SomeP@ssw0rd12!")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="SomeP@ssw0rd12!",
        )
        # Django normalizes the domain part to lowercase
        assert user.email == "Test@example.com"

    def test_create_user_without_email_raises_value_error(self):
        with pytest.raises(ValueError, match="The Email field must be set"):
            User.objects.create_user(email="", password="SomeP@ssw0rd12!")

    def test_create_user_without_password(self):
        user = User.objects.create_user(email="nopass@example.com")
        assert user.has_usable_password() is False

    def test_create_user_with_extra_fields(self):
        user = User.objects.create_user(
            email="extra@example.com",
            password="SomeP@ssw0rd12!",
            first_name="First",
            last_name="Last",
            preferred_currency="USD",
        )
        assert user.first_name == "First"
        assert user.last_name == "Last"
        assert user.preferred_currency == "USD"

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Adm!nP@ssw0rd12",
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True

    def test_create_superuser_is_staff_false_raises(self):
        with pytest.raises(ValueError, match="Superuser must have is_staff=True"):
            User.objects.create_superuser(
                email="bad@example.com",
                password="Adm!nP@ssw0rd12",
                is_staff=False,
            )

    def test_create_superuser_is_superuser_false_raises(self):
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True"):
            User.objects.create_superuser(
                email="bad2@example.com",
                password="Adm!nP@ssw0rd12",
                is_superuser=False,
            )

    def test_create_superuser_defaults_is_active_true(self):
        admin = User.objects.create_superuser(
            email="admin2@example.com",
            password="Adm!nP@ssw0rd12",
        )
        assert admin.is_active is True


# ---------------------------------------------------------------------------
# User model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserModel:
    """Tests for the User model."""

    def test_user_has_uuid_primary_key(self, user):
        assert isinstance(user.id, uuid.UUID)

    def test_user_str_returns_email(self, user):
        assert str(user) == "testuser@example.com"

    def test_get_full_name_with_first_and_last(self, user):
        assert user.get_full_name() == "Test User"

    def test_get_full_name_with_only_first_name(self, db):
        u = User.objects.create_user(
            email="first@example.com",
            password="SomeP@ssw0rd12!",
            first_name="OnlyFirst",
        )
        assert u.get_full_name() == "OnlyFirst"

    def test_get_full_name_with_no_names_returns_email(self, db):
        u = User.objects.create_user(
            email="noname@example.com",
            password="SomeP@ssw0rd12!",
        )
        assert u.get_full_name() == "noname@example.com"

    def test_get_short_name_with_first_name(self, user):
        assert user.get_short_name() == "Test"

    def test_get_short_name_without_first_name(self, db):
        u = User.objects.create_user(
            email="nofirst@example.com",
            password="SomeP@ssw0rd12!",
        )
        assert u.get_short_name() == "nofirst"

    def test_username_field_is_email(self):
        assert User.USERNAME_FIELD == "email"

    def test_required_fields_empty(self):
        assert User.REQUIRED_FIELDS == []

    def test_default_subscription_tier(self, user):
        assert user.subscription_tier == "free"

    def test_default_preferred_currency(self, db):
        u = User.objects.create_user(
            email="default@example.com",
            password="SomeP@ssw0rd12!",
        )
        assert u.preferred_currency == "EUR"

    def test_default_is_email_verified(self, user):
        assert user.is_email_verified is False

    def test_email_unique_constraint(self, user):
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="testuser@example.com",
                password="Another!Pass123",
            )

    def test_subscription_tier_choices(self):
        valid_tiers = [choice[0] for choice in User.SUBSCRIPTION_TIERS]
        assert "free" in valid_tiers
        assert "premium" in valid_tiers
        assert "pro" in valid_tiers
        assert "business" in valid_tiers

    def test_currency_choices(self):
        valid_currencies = [choice[0] for choice in User.CURRENCIES]
        assert "EUR" in valid_currencies
        assert "USD" in valid_currencies
        assert "GBP" in valid_currencies
        assert "CHF" in valid_currencies

    def test_user_ordering(self):
        assert User._meta.ordering == ["-date_joined"]

    def test_verbose_name(self):
        assert User._meta.verbose_name == "user"
        assert User._meta.verbose_name_plural == "users"

    def test_date_joined_set_on_creation(self, user):
        assert user.date_joined is not None

    def test_last_login_null_by_default(self, db):
        u = User.objects.create_user(
            email="newuser@example.com",
            password="SomeP@ssw0rd12!",
        )
        assert u.last_login is None

    def test_premium_user_tier(self, premium_user):
        assert premium_user.subscription_tier == "premium"

    def test_inactive_user(self, inactive_user):
        assert inactive_user.is_active is False

    def test_superuser_flags(self, superuser):
        assert superuser.is_staff is True
        assert superuser.is_superuser is True


# ---------------------------------------------------------------------------
# UserProfile model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserProfileModel:
    """Tests for the UserProfile model."""

    def test_profile_has_uuid_primary_key(self, user):
        profile = user.profile
        assert isinstance(profile.id, uuid.UUID)

    def test_profile_str(self, user):
        assert str(user.profile) == "Profile for testuser@example.com"

    def test_profile_default_notification_preferences(self, user):
        profile = user.profile
        assert profile.email_notifications is True
        assert profile.push_notifications is True
        assert profile.weekly_summary is True
        assert profile.budget_alerts is True

    def test_profile_default_display_preferences(self, user):
        profile = user.profile
        assert profile.theme == "system"
        assert profile.language == "fr"
        assert profile.date_format == "DD/MM/YYYY"

    def test_profile_timestamps(self, user):
        profile = user.profile
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_profile_verbose_name(self):
        assert UserProfile._meta.verbose_name == "user profile"
        assert UserProfile._meta.verbose_name_plural == "user profiles"

    def test_profile_user_cascade_delete(self, user):
        profile_id = user.profile.id
        user.delete()
        assert not UserProfile.objects.filter(id=profile_id).exists()

    def test_profile_one_to_one_relationship(self, user):
        assert user.profile.user == user

    def test_profile_update_preferences(self, user):
        profile = user.profile
        profile.theme = "dark"
        profile.language = "en"
        profile.email_notifications = False
        profile.save()
        profile.refresh_from_db()
        assert profile.theme == "dark"
        assert profile.language == "en"
        assert profile.email_notifications is False
