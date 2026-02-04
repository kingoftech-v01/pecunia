"""
Tests for accounts.signals module.

Covers the post_save signal that creates/updates UserProfile on User creation.
"""
import pytest

from apps.accounts.models import User, UserProfile


@pytest.mark.django_db
class TestSignals:
    """Tests for User post_save signals."""

    def test_profile_created_on_user_creation(self, db):
        user = User.objects.create_user(
            email="signal_test@example.com",
            password="SomeP@ssw0rd12!",
        )
        assert UserProfile.objects.filter(user=user).exists()

    def test_profile_not_duplicated_on_save(self, user):
        """Saving an existing user should not create duplicate profile."""
        profile_count_before = UserProfile.objects.filter(user=user).count()
        user.first_name = "Updated"
        user.save()
        profile_count_after = UserProfile.objects.filter(user=user).count()
        assert profile_count_before == profile_count_after == 1

    def test_profile_defaults_on_creation(self, db):
        user = User.objects.create_user(
            email="defaults@example.com",
            password="SomeP@ssw0rd12!",
        )
        profile = user.profile
        assert profile.email_notifications is True
        assert profile.push_notifications is True
        assert profile.weekly_summary is True
        assert profile.budget_alerts is True
        assert profile.theme == "system"
        assert profile.language == "fr"
        assert profile.date_format == "DD/MM/YYYY"

    def test_superuser_gets_profile(self, db):
        admin = User.objects.create_superuser(
            email="signal_admin@example.com",
            password="Adm!nP@ssw0rd12",
        )
        assert hasattr(admin, "profile")
        assert admin.profile is not None

    def test_profile_survives_user_update(self, user):
        """Updating a user should not destroy the profile."""
        original_profile_id = user.profile.id
        user.first_name = "ChangedAgain"
        user.save()
        user.refresh_from_db()
        assert user.profile.id == original_profile_id

    def test_multiple_users_get_separate_profiles(self, db):
        user1 = User.objects.create_user(
            email="multi1@example.com",
            password="SomeP@ssw0rd12!",
        )
        user2 = User.objects.create_user(
            email="multi2@example.com",
            password="SomeP@ssw0rd12!",
        )
        assert user1.profile.id != user2.profile.id
        assert user1.profile.user == user1
        assert user2.profile.user == user2
