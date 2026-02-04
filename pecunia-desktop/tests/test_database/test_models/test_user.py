"""Tests for src/database/models/user.py — User model."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from database.models.user import User


class TestUserCreation:
    """Tests for User model creation."""

    def test_default_values(self):
        user = User()
        assert user.email is None
        assert user.subscription_tier is None or user.subscription_tier == "free"
        assert user.preferred_currency == "USD"
        assert user.is_current is False
        assert user.is_active is True
        assert user.sync_version == 0
        assert user.is_dirty is True

    def test_create_with_fields(self):
        user = User(
            email="test@test.com",
            first_name="John",
            last_name="Doe",
        )
        assert user.email == "test@test.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"


class TestUserProperties:
    """Tests for User model properties."""

    def test_full_name_with_both_names(self):
        user = User(first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"

    def test_full_name_with_first_only(self):
        user = User(first_name="John")
        assert user.full_name == "John"

    def test_full_name_with_last_only(self):
        user = User(last_name="Doe")
        assert user.full_name == "Doe"

    def test_full_name_fallback_to_email(self):
        user = User(email="test@test.com")
        assert user.full_name == "test@test.com"

    def test_is_deleted_false(self):
        user = User()
        assert user.is_deleted is False

    def test_is_deleted_true(self):
        user = User()
        user.deleted_at = datetime.utcnow()
        assert user.is_deleted is True


class TestUserMethods:
    """Tests for User model methods."""

    def test_mark_dirty(self):
        user = User(is_dirty=False)
        user.mark_dirty()
        assert user.is_dirty is True
        assert user.updated_at is not None

    def test_mark_synced(self):
        user = User(is_dirty=True, sync_version=0)
        user.mark_synced(server_id="srv1")
        assert user.is_dirty is False
        assert user.last_sync_at is not None
        assert user.sync_version == 1
        assert user.server_id == "srv1"

    def test_mark_synced_without_server_id(self):
        user = User(is_dirty=True, sync_version=2)
        user.mark_synced()
        assert user.is_dirty is False
        assert user.sync_version == 3
        assert user.server_id is None

    def test_set_as_current(self):
        user = User(is_current=False)
        user.set_as_current()
        assert user.is_current is True

    def test_clear_current(self):
        user = User(is_current=True)
        user.clear_current()
        assert user.is_current is False

    def test_soft_delete(self):
        user = User(is_active=True, is_current=True)
        user.soft_delete()
        assert user.deleted_at is not None
        assert user.is_active is False
        assert user.is_current is False
        assert user.is_dirty is True

    def test_restore(self):
        user = User()
        user.soft_delete()
        user.restore()
        assert user.deleted_at is None
        assert user.is_active is True
        assert user.is_dirty is True


class TestUserSerialization:
    """Tests for User serialization."""

    def test_to_dict(self):
        now = datetime.utcnow()
        user = User(
            id="u1", email="test@test.com", first_name="John", last_name="Doe",
            is_current=True, is_active=True, sync_version=3,
            created_at=now, updated_at=now,
        )
        d = user.to_dict()
        assert d["id"] == "u1"
        assert d["email"] == "test@test.com"
        assert d["first_name"] == "John"
        assert d["is_current"] is True
        assert d["sync_version"] == 3

    def test_to_dict_handles_none_dates(self):
        user = User(id="u2", email="a@b.com")
        user.created_at = None
        user.updated_at = None
        d = user.to_dict()
        assert d["created_at"] is None
        assert d["updated_at"] is None

    def test_from_dict(self):
        data = {
            "id": "u1", "email": "test@test.com",
            "first_name": "John", "last_name": "Doe",
            "preferred_currency": "EUR", "sync_version": 5,
        }
        user = User.from_dict(data)
        assert user.email == "test@test.com"
        assert user.first_name == "John"
        assert user.preferred_currency == "EUR"
        assert user.sync_version == 5

    def test_from_dict_parses_dates(self):
        data = {
            "id": "u1", "email": "a@b.com",
            "created_at": "2024-01-01T12:00:00",
        }
        user = User.from_dict(data)
        assert isinstance(user.created_at, datetime)
        assert user.created_at.year == 2024

    def test_from_dict_ignores_unknown_fields(self):
        data = {"id": "u1", "email": "a@b.com", "unknown_field": "xyz"}
        user = User.from_dict(data)
        assert not hasattr(user, "unknown_field") or getattr(user, "unknown_field", None) is None

    def test_round_trip(self):
        user = User(
            id="u1", email="test@test.com",
            first_name="John", last_name="Doe",
        )
        user.created_at = datetime(2024, 1, 1)
        user.updated_at = datetime(2024, 6, 1)
        d = user.to_dict()
        user2 = User.from_dict(d)
        assert user2.email == user.email
        assert user2.first_name == user.first_name


class TestUserRepr:
    """Tests for User repr."""

    def test_repr(self):
        user = User(id="u1")
        repr_str = repr(user)
        assert "u1" in repr_str
        assert "User" in repr_str
