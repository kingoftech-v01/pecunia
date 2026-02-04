"""
Tests for accounts.serializers module.

Covers UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
UserProfileSerializer, and ChangePasswordSerializer with all validation
branches and edge cases.
"""
import pytest
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User, UserProfile
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


# ---------------------------------------------------------------------------
# UserRegistrationSerializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserRegistrationSerializer:
    """Tests for user registration serializer."""

    VALID_DATA = {
        "email": "newuser@example.com",
        "password": "Str0ngP@ssw0rd!",
        "password_confirm": "Str0ngP@ssw0rd!",
        "first_name": "New",
        "last_name": "User",
        "preferred_currency": "EUR",
    }

    def test_valid_registration(self):
        serializer = UserRegistrationSerializer(data=self.VALID_DATA)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.email == "newuser@example.com"
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.check_password("Str0ngP@ssw0rd!")

    def test_password_mismatch(self):
        data = {**self.VALID_DATA, "password_confirm": "Different123!!"}
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors

    def test_weak_password_rejected(self):
        data = {**self.VALID_DATA, "password": "123", "password_confirm": "123"}
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "password" in serializer.errors

    def test_missing_email(self):
        data = {**self.VALID_DATA}
        del data["email"]
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_missing_password(self):
        data = {**self.VALID_DATA}
        del data["password"]
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "password" in serializer.errors

    def test_missing_password_confirm(self):
        data = {**self.VALID_DATA}
        del data["password_confirm"]
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors

    def test_duplicate_email(self, user):
        data = {**self.VALID_DATA, "email": user.email}
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_password_confirm_not_in_validated_data(self):
        serializer = UserRegistrationSerializer(data=self.VALID_DATA)
        assert serializer.is_valid()
        user = serializer.save()
        # password_confirm should not remain as a user attribute
        assert not hasattr(user, "password_confirm")

    def test_optional_fields_blank(self):
        data = {
            "email": "minimal@example.com",
            "password": "Str0ngP@ssw0rd!",
            "password_confirm": "Str0ngP@ssw0rd!",
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.first_name == ""
        assert user.last_name == ""

    def test_meta_fields(self):
        fields = UserRegistrationSerializer.Meta.fields
        assert "email" in fields
        assert "password" in fields
        assert "password_confirm" in fields
        assert "first_name" in fields
        assert "last_name" in fields
        assert "preferred_currency" in fields


# ---------------------------------------------------------------------------
# UserLoginSerializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserLoginSerializer:
    """Tests for user login serializer."""

    def test_valid_login(self, user, user_password):
        data = {"email": user.email, "password": user_password}
        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["user"] == user

    def test_invalid_password(self, user):
        data = {"email": user.email, "password": "WrongPass123!!"}
        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert "detail" in serializer.errors

    def test_nonexistent_email(self):
        data = {"email": "nobody@example.com", "password": "DoesNotMatter1!"}
        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert "detail" in serializer.errors

    def test_inactive_user(self, inactive_user, user_password):
        # inactive_user.is_active is False; Django's authenticate() returns None
        # for inactive users by default
        data = {"email": inactive_user.email, "password": user_password}
        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()

    def test_missing_email_field(self, user_password):
        data = {"password": user_password}
        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_missing_password_field(self, user):
        data = {"email": user.email}
        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert "password" in serializer.errors

    def test_empty_email(self, user_password):
        data = {"email": "", "password": user_password}
        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()

    def test_empty_password(self, user):
        data = {"email": user.email, "password": ""}
        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()


# ---------------------------------------------------------------------------
# UserSerializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserSerializer:
    """Tests for user detail serializer."""

    def test_serialized_fields(self, user):
        serializer = UserSerializer(user)
        data = serializer.data
        assert data["email"] == user.email
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"
        assert data["full_name"] == "Test User"
        assert data["subscription_tier"] == "free"
        assert data["preferred_currency"] == "EUR"
        assert data["is_email_verified"] is False
        assert "id" in data
        assert "date_joined" in data

    def test_full_name_computed_field(self, user):
        serializer = UserSerializer(user)
        assert serializer.data["full_name"] == user.get_full_name()

    def test_read_only_fields_not_writable(self, user):
        serializer = UserSerializer(
            user,
            data={"email": "hacked@example.com", "subscription_tier": "premium"},
            partial=True,
        )
        assert serializer.is_valid()
        updated = serializer.save()
        # read_only fields should not have changed
        assert updated.email == "testuser@example.com"
        assert updated.subscription_tier == "free"

    def test_update_first_name(self, user):
        serializer = UserSerializer(user, data={"first_name": "Updated"}, partial=True)
        assert serializer.is_valid()
        updated = serializer.save()
        assert updated.first_name == "Updated"

    def test_update_last_name(self, user):
        serializer = UserSerializer(user, data={"last_name": "Updated"}, partial=True)
        assert serializer.is_valid()
        updated = serializer.save()
        assert updated.last_name == "Updated"

    def test_update_preferred_currency(self, user):
        serializer = UserSerializer(
            user, data={"preferred_currency": "USD"}, partial=True
        )
        assert serializer.is_valid()
        updated = serializer.save()
        assert updated.preferred_currency == "USD"

    def test_meta_fields_list(self):
        expected_fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "subscription_tier", "preferred_currency",
            "is_email_verified", "date_joined", "last_login",
        ]
        assert UserSerializer.Meta.fields == expected_fields

    def test_meta_read_only_fields(self):
        ro = UserSerializer.Meta.read_only_fields
        assert "id" in ro
        assert "email" in ro
        assert "subscription_tier" in ro
        assert "is_email_verified" in ro
        assert "date_joined" in ro
        assert "last_login" in ro


# ---------------------------------------------------------------------------
# UserProfileSerializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserProfileSerializer:
    """Tests for user profile serializer."""

    def test_serialized_fields(self, user):
        profile = user.profile
        serializer = UserProfileSerializer(profile)
        data = serializer.data
        assert data["email_notifications"] is True
        assert data["push_notifications"] is True
        assert data["weekly_summary"] is True
        assert data["budget_alerts"] is True
        assert data["theme"] == "system"
        assert data["language"] == "fr"
        assert data["date_format"] == "DD/MM/YYYY"
        assert "created_at" in data
        assert "updated_at" in data

    def test_update_notification_preferences(self, user):
        profile = user.profile
        serializer = UserProfileSerializer(
            profile,
            data={"email_notifications": False, "push_notifications": False},
            partial=True,
        )
        assert serializer.is_valid()
        updated = serializer.save()
        assert updated.email_notifications is False
        assert updated.push_notifications is False

    def test_update_display_preferences(self, user):
        profile = user.profile
        serializer = UserProfileSerializer(
            profile,
            data={"theme": "dark", "language": "en"},
            partial=True,
        )
        assert serializer.is_valid()
        updated = serializer.save()
        assert updated.theme == "dark"
        assert updated.language == "en"

    def test_read_only_timestamps(self, user):
        profile = user.profile
        original_created = profile.created_at
        serializer = UserProfileSerializer(
            profile,
            data={"created_at": "2000-01-01T00:00:00Z"},
            partial=True,
        )
        assert serializer.is_valid()
        updated = serializer.save()
        # created_at is read-only and should not change
        assert updated.created_at == original_created

    def test_meta_fields(self):
        fields = UserProfileSerializer.Meta.fields
        assert "email_notifications" in fields
        assert "push_notifications" in fields
        assert "weekly_summary" in fields
        assert "budget_alerts" in fields
        assert "theme" in fields
        assert "language" in fields
        assert "date_format" in fields
        assert "created_at" in fields
        assert "updated_at" in fields

    def test_meta_read_only_fields(self):
        ro = UserProfileSerializer.Meta.read_only_fields
        assert "created_at" in ro
        assert "updated_at" in ro


# ---------------------------------------------------------------------------
# ChangePasswordSerializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChangePasswordSerializer:
    """Tests for password change serializer."""

    def _make_request(self, user):
        """Create a mock request with user attached."""
        factory = APIRequestFactory()
        request = factory.post("/fake/")
        request.user = user
        return request

    def test_valid_password_change(self, user, user_password):
        request = self._make_request(user)
        data = {
            "current_password": user_password,
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        serializer = ChangePasswordSerializer(
            data=data, context={"request": request}
        )
        assert serializer.is_valid(), serializer.errors

    def test_wrong_current_password(self, user):
        request = self._make_request(user)
        data = {
            "current_password": "WrongOldP@ss123!",
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        serializer = ChangePasswordSerializer(
            data=data, context={"request": request}
        )
        assert not serializer.is_valid()
        assert "current_password" in serializer.errors

    def test_new_passwords_mismatch(self, user, user_password):
        request = self._make_request(user)
        data = {
            "current_password": user_password,
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "DifferentP@ss123!",
        }
        serializer = ChangePasswordSerializer(
            data=data, context={"request": request}
        )
        assert not serializer.is_valid()
        assert "new_password_confirm" in serializer.errors

    def test_weak_new_password(self, user, user_password):
        request = self._make_request(user)
        data = {
            "current_password": user_password,
            "new_password": "123",
            "new_password_confirm": "123",
        }
        serializer = ChangePasswordSerializer(
            data=data, context={"request": request}
        )
        assert not serializer.is_valid()
        assert "new_password" in serializer.errors

    def test_missing_current_password(self, user):
        request = self._make_request(user)
        data = {
            "new_password": "N3wStr0ngP@ss!",
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        serializer = ChangePasswordSerializer(
            data=data, context={"request": request}
        )
        assert not serializer.is_valid()
        assert "current_password" in serializer.errors

    def test_missing_new_password(self, user, user_password):
        request = self._make_request(user)
        data = {
            "current_password": user_password,
            "new_password_confirm": "N3wStr0ngP@ss!",
        }
        serializer = ChangePasswordSerializer(
            data=data, context={"request": request}
        )
        assert not serializer.is_valid()
        assert "new_password" in serializer.errors

    def test_missing_new_password_confirm(self, user, user_password):
        request = self._make_request(user)
        data = {
            "current_password": user_password,
            "new_password": "N3wStr0ngP@ss!",
        }
        serializer = ChangePasswordSerializer(
            data=data, context={"request": request}
        )
        assert not serializer.is_valid()
        assert "new_password_confirm" in serializer.errors
