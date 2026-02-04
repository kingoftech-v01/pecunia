"""
User model for the Pecunia Desktop application.

Provides user account management with offline-first support.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, Integer, Index
)
from sqlalchemy.orm import relationship, Mapped

from . import Base


class User(Base):
    """
    User model representing an application user.

    Stores user credentials and profile information locally with
    sync tracking for offline-first architecture.
    """

    __tablename__ = "users"

    # Primary key - UUID for cross-device compatibility
    id: Mapped[str] = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Server ID for mapping to backend
    server_id: Mapped[Optional[str]] = Column(String(255), unique=True, nullable=True)

    # User credentials
    email: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)

    # Profile information
    first_name: Mapped[Optional[str]] = Column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = Column(String(100), nullable=True)

    # Subscription tier
    subscription_tier: Mapped[Optional[str]] = Column(String(50), nullable=True, default="free")

    # Currency preference
    preferred_currency: Mapped[str] = Column(String(3), default="USD", nullable=False)

    # Sync tracking
    last_sync_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Flag for currently active/logged-in user
    is_current: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    # Account status
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Sync version tracking
    sync_version: Mapped[int] = Column(Integer, default=0, nullable=False)
    is_dirty: Mapped[bool] = Column(Boolean, default=True, nullable=False)

    # Soft delete support
    deleted_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Indexes
    __table_args__ = (
        Index('ix_users_sync', 'is_dirty', 'last_sync_at'),
        Index('ix_users_active', 'is_active', 'deleted_at'),
        Index('ix_users_current', 'is_current'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id})>"

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.email

    @property
    def is_deleted(self) -> bool:
        """Check if the user is soft-deleted."""
        return self.deleted_at is not None

    def mark_dirty(self) -> None:
        """Mark the user record as needing sync."""
        self.is_dirty = True
        self.updated_at = datetime.utcnow()

    def mark_synced(self, server_id: Optional[str] = None) -> None:
        """Mark the user record as synced."""
        self.is_dirty = False
        self.last_sync_at = datetime.utcnow()
        self.sync_version += 1
        if server_id:
            self.server_id = server_id

    def set_as_current(self) -> None:
        """Set this user as the currently active user."""
        self.is_current = True

    def clear_current(self) -> None:
        """Clear the current user flag."""
        self.is_current = False

    def soft_delete(self) -> None:
        """Soft delete the user record."""
        self.deleted_at = datetime.utcnow()
        self.is_active = False
        self.is_current = False
        self.mark_dirty()

    def restore(self) -> None:
        """Restore a soft-deleted user record."""
        self.deleted_at = None
        self.is_active = True
        self.mark_dirty()

    def to_dict(self) -> dict:
        """Convert the user to a dictionary for serialization."""
        return {
            "id": self.id,
            "server_id": self.server_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "subscription_tier": self.subscription_tier,
            "preferred_currency": self.preferred_currency,
            "is_current": self.is_current,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "sync_version": self.sync_version,
        }

    # Allowlist of fields that can be deserialized from external data
    _DESERIALIZABLE_FIELDS = frozenset({
        'id', 'server_id', 'email', 'first_name', 'last_name',
        'subscription_tier', 'preferred_currency', 'is_active',
        'created_at', 'updated_at', 'last_sync_at', 'sync_version',
    })

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create a User instance from a dictionary."""
        user = cls()
        for key, value in data.items():
            if key in cls._DESERIALIZABLE_FIELDS:
                if key.endswith('_at') and value and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(user, key, value)
        return user
