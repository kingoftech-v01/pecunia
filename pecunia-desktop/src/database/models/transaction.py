"""
Transaction and TransactionCategory SQLAlchemy models for the finance application.

Provides financial transaction tracking with offline-first support and
user-defined categories.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from . import Base


class TransactionType(str, PyEnum):
    """Enumeration for transaction types."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class TransactionCategory(Base):
    """
    Model representing a transaction category.

    Categories can be user-defined or system defaults, and are used to
    classify transactions for reporting and budgeting purposes.
    """
    __tablename__ = "transaction_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType),
        nullable=False,
        default=TransactionType.EXPENSE
    )
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color code
    server_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="category",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_transaction_categories_user_id", "user_id"),
        Index("ix_transaction_categories_server_id", "server_id"),
        Index("ix_transaction_categories_type", "type"),
        Index("ix_transaction_categories_user_name", "user_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<TransactionCategory(id={self.id}, name='{self.name}', type={self.type.value})>"

    @property
    def is_synced(self) -> bool:
        """Check if the category has been synced to the server."""
        return self.server_id is not None

    def mark_as_synced(self, server_id: int) -> None:
        """Mark the category as synced with the given server ID."""
        self.server_id = server_id

    @classmethod
    def get_by_server_id(cls, session: Session, server_id: int) -> Optional["TransactionCategory"]:
        """Retrieve a category by its server ID."""
        return session.query(cls).filter(cls.server_id == server_id).first()

    @classmethod
    def get_unsynced(cls, session: Session, user_id: int) -> List["TransactionCategory"]:
        """Get all categories that haven't been synced to the server."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.server_id.is_(None)
        ).all()

    @classmethod
    def get_synced(cls, session: Session, user_id: int) -> List["TransactionCategory"]:
        """Get all categories that have been synced to the server."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.server_id.isnot(None)
        ).all()

    @classmethod
    def get_by_type(
        cls,
        session: Session,
        user_id: int,
        category_type: TransactionType
    ) -> List["TransactionCategory"]:
        """Get all categories of a specific type for a user."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.type == category_type
        ).all()

    @classmethod
    def get_all_for_user(cls, session: Session, user_id: int) -> List["TransactionCategory"]:
        """Get all categories for a user."""
        return session.query(cls).filter(cls.user_id == user_id).all()


class Transaction(Base):
    """
    Model representing a financial transaction.

    Transactions track income, expenses, and transfers with support for
    offline-first functionality via sync status tracking.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("transaction_categories.id", ondelete="SET NULL"),
        nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    merchant: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    server_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    category: Mapped[Optional["TransactionCategory"]] = relationship(
        "TransactionCategory",
        back_populates="transactions"
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_transaction_date", "transaction_date"),
        Index("ix_transactions_is_synced", "is_synced"),
        Index("ix_transactions_server_id", "server_id"),
        Index("ix_transactions_type", "type"),
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_user_synced", "user_id", "is_synced"),
        Index("ix_transactions_merchant", "merchant"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, amount={self.amount}, "
            f"type={self.type.value}, synced={self.is_synced})>"
        )

    def mark_as_synced(self, server_id: int) -> None:
        """Mark the transaction as synced with the given server ID."""
        self.server_id = server_id
        self.is_synced = True
        self.updated_at = datetime.utcnow()

    def mark_as_unsynced(self) -> None:
        """Mark the transaction as requiring sync (after local modification)."""
        self.is_synced = False
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_by_server_id(cls, session: Session, server_id: int) -> Optional["Transaction"]:
        """Retrieve a transaction by its server ID."""
        return session.query(cls).filter(cls.server_id == server_id).first()

    @classmethod
    def get_unsynced(cls, session: Session, user_id: int) -> List["Transaction"]:
        """Get all transactions that need to be synced to the server."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_synced == False
        ).order_by(cls.created_at.asc()).all()

    @classmethod
    def get_synced(cls, session: Session, user_id: int) -> List["Transaction"]:
        """Get all transactions that have been synced to the server."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_synced == True
        ).order_by(cls.transaction_date.desc()).all()

    @classmethod
    def get_by_date_range(
        cls,
        session: Session,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        transaction_type: Optional[TransactionType] = None
    ) -> List["Transaction"]:
        """
        Get transactions within a date range, optionally filtered by type.

        Args:
            session: Database session
            user_id: The user's ID
            start_date: Start of the date range (inclusive)
            end_date: End of the date range (inclusive)
            transaction_type: Optional filter by transaction type

        Returns:
            List of transactions matching the criteria
        """
        query = session.query(cls).filter(
            cls.user_id == user_id,
            cls.transaction_date >= start_date,
            cls.transaction_date <= end_date
        )

        if transaction_type is not None:
            query = query.filter(cls.type == transaction_type)

        return query.order_by(cls.transaction_date.desc()).all()

    @classmethod
    def get_by_category(
        cls,
        session: Session,
        user_id: int,
        category_id: int
    ) -> List["Transaction"]:
        """Get all transactions for a specific category."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.category_id == category_id
        ).order_by(cls.transaction_date.desc()).all()

    @classmethod
    def get_pending_sync_count(cls, session: Session, user_id: int) -> int:
        """Get the count of transactions pending sync for a user."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_synced == False
        ).count()

    @classmethod
    def get_all_for_user(
        cls,
        session: Session,
        user_id: int,
        limit: Optional[int] = None
    ) -> List["Transaction"]:
        """Get all transactions for a user, optionally limited."""
        query = session.query(cls).filter(
            cls.user_id == user_id
        ).order_by(cls.transaction_date.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_by_merchant(
        cls,
        session: Session,
        user_id: int,
        merchant: str
    ) -> List["Transaction"]:
        """Get all transactions for a specific merchant."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.merchant == merchant
        ).order_by(cls.transaction_date.desc()).all()
