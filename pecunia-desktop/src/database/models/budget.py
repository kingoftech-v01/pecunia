"""
Budget and BudgetItem SQLAlchemy models for the finance application.

Provides budget planning and tracking with offline-first support,
allowing users to set spending limits by category and track progress.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from . import Base


class BudgetPeriodType(str, PyEnum):
    """Enumeration for budget period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class Budget(Base):
    """
    Model representing a budget.

    Budgets define spending limits over a time period and contain
    budget items that allocate amounts to specific categories.
    """
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    period_type: Mapped[BudgetPeriodType] = mapped_column(
        Enum(BudgetPeriodType),
        nullable=False,
        default=BudgetPeriodType.MONTHLY
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    items: Mapped[List["BudgetItem"]] = relationship(
        "BudgetItem",
        back_populates="budget",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Indexes
    __table_args__ = (
        Index("ix_budgets_user_id", "user_id"),
        Index("ix_budgets_server_id", "server_id"),
        Index("ix_budgets_is_synced", "is_synced"),
        Index("ix_budgets_is_active", "is_active"),
        Index("ix_budgets_period_type", "period_type"),
        Index("ix_budgets_user_active", "user_id", "is_active"),
        Index("ix_budgets_user_synced", "user_id", "is_synced"),
        Index("ix_budgets_date_range", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Budget(id={self.id}, name='{self.name}', "
            f"period={self.period_type.value}, active={self.is_active})>"
        )

    @property
    def total_planned(self) -> Decimal:
        """Calculate the total planned amount across all budget items."""
        return sum((item.planned_amount for item in self.items), Decimal("0.00"))

    @property
    def total_spent(self) -> Decimal:
        """Calculate the total spent amount across all budget items."""
        return sum((item.spent_amount for item in self.items), Decimal("0.00"))

    @property
    def total_remaining(self) -> Decimal:
        """Calculate the total remaining amount across all budget items."""
        return self.total_planned - self.total_spent

    @property
    def overall_progress_percentage(self) -> float:
        """
        Calculate the overall budget progress as a percentage.

        Returns:
            Percentage of budget spent (0.0 to 100.0+).
            Returns 0.0 if no amount is planned.
        """
        total_planned = self.total_planned
        if total_planned == Decimal("0.00"):
            return 0.0
        return float((self.total_spent / total_planned) * 100)

    @property
    def is_over_budget(self) -> bool:
        """Check if total spending exceeds the total planned amount."""
        return self.total_spent > self.total_planned

    @property
    def is_current(self) -> bool:
        """Check if the budget period includes today's date."""
        today = date.today()
        if self.end_date:
            return self.start_date <= today <= self.end_date
        return self.start_date <= today

    def get_item_by_category(self, category_id: int) -> Optional["BudgetItem"]:
        """
        Get a budget item by category ID.

        Args:
            category_id: The category ID to search for.

        Returns:
            The matching BudgetItem or None if not found.
        """
        for item in self.items:
            if item.category_id == category_id:
                return item
        return None

    def calculate_progress(self) -> dict:
        """
        Calculate comprehensive budget progress statistics.

        Returns:
            Dictionary containing:
                - total_planned: Total planned amount
                - total_spent: Total spent amount
                - total_remaining: Remaining amount
                - progress_percentage: Overall progress percentage
                - is_over_budget: Whether spending exceeds planned
                - items_over_budget: Count of items over their planned amount
                - items_on_track: Count of items under 80% spent
                - items_warning: Count of items between 80-100% spent
        """
        items_over = 0
        items_warning = 0
        items_on_track = 0

        for item in self.items:
            progress = item.progress_percentage
            if progress > 100:
                items_over += 1
            elif progress >= 80:
                items_warning += 1
            else:
                items_on_track += 1

        return {
            "total_planned": self.total_planned,
            "total_spent": self.total_spent,
            "total_remaining": self.total_remaining,
            "progress_percentage": self.overall_progress_percentage,
            "is_over_budget": self.is_over_budget,
            "items_over_budget": items_over,
            "items_warning": items_warning,
            "items_on_track": items_on_track,
        }

    def mark_as_synced(self, server_id: int) -> None:
        """Mark the budget as synced with the given server ID."""
        self.server_id = server_id
        self.is_synced = True
        self.updated_at = datetime.utcnow()

    def mark_as_unsynced(self) -> None:
        """Mark the budget as requiring sync (after local modification)."""
        self.is_synced = False
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_by_server_id(cls, session: Session, server_id: int) -> Optional["Budget"]:
        """Retrieve a budget by its server ID."""
        return session.query(cls).filter(cls.server_id == server_id).first()

    @classmethod
    def get_unsynced(cls, session: Session, user_id: int) -> List["Budget"]:
        """Get all budgets that need to be synced to the server."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_synced == False
        ).order_by(cls.created_at.asc()).all()

    @classmethod
    def get_active(cls, session: Session, user_id: int) -> List["Budget"]:
        """Get all active budgets for a user."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_active == True
        ).order_by(cls.start_date.desc()).all()

    @classmethod
    def get_current(cls, session: Session, user_id: int) -> List["Budget"]:
        """
        Get budgets that are active and include today's date.

        Args:
            session: Database session
            user_id: The user's ID

        Returns:
            List of current active budgets
        """
        today = date.today()
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.is_active == True,
            cls.start_date <= today,
            (cls.end_date >= today) | (cls.end_date.is_(None))
        ).order_by(cls.start_date.desc()).all()

    @classmethod
    def get_by_period_type(
        cls,
        session: Session,
        user_id: int,
        period_type: BudgetPeriodType
    ) -> List["Budget"]:
        """Get all budgets of a specific period type for a user."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.period_type == period_type
        ).order_by(cls.start_date.desc()).all()

    @classmethod
    def get_all_for_user(
        cls,
        session: Session,
        user_id: int,
        include_inactive: bool = False
    ) -> List["Budget"]:
        """
        Get all budgets for a user.

        Args:
            session: Database session
            user_id: The user's ID
            include_inactive: Whether to include inactive budgets

        Returns:
            List of budgets
        """
        query = session.query(cls).filter(cls.user_id == user_id)
        if not include_inactive:
            query = query.filter(cls.is_active == True)
        return query.order_by(cls.start_date.desc()).all()


class BudgetItem(Base):
    """
    Model representing a budget item (category allocation within a budget).

    Budget items define planned spending amounts for specific categories
    and track actual spending against those plans.
    """
    __tablename__ = "budget_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    budget_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transaction_categories.id", ondelete="CASCADE"),
        nullable=False
    )
    planned_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    spent_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00")
    )
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
    budget: Mapped["Budget"] = relationship("Budget", back_populates="items")
    category: Mapped["TransactionCategory"] = relationship("TransactionCategory")

    # Indexes
    __table_args__ = (
        Index("ix_budget_items_budget_id", "budget_id"),
        Index("ix_budget_items_category_id", "category_id"),
        Index("ix_budget_items_server_id", "server_id"),
        Index("ix_budget_items_budget_category", "budget_id", "category_id", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<BudgetItem(id={self.id}, budget_id={self.budget_id}, "
            f"category_id={self.category_id}, planned={self.planned_amount}, "
            f"spent={self.spent_amount})>"
        )

    @property
    def remaining_amount(self) -> Decimal:
        """Calculate the remaining amount for this budget item."""
        return self.planned_amount - self.spent_amount

    @property
    def progress_percentage(self) -> float:
        """
        Calculate the progress percentage for this budget item.

        Returns:
            Percentage of planned amount spent (0.0 to 100.0+).
            Returns 0.0 if no amount is planned.
        """
        if self.planned_amount == Decimal("0.00"):
            return 0.0 if self.spent_amount == Decimal("0.00") else 100.0
        return float((self.spent_amount / self.planned_amount) * 100)

    @property
    def is_over_budget(self) -> bool:
        """Check if spending exceeds the planned amount."""
        return self.spent_amount > self.planned_amount

    @property
    def is_synced(self) -> bool:
        """Check if the budget item has been synced to the server."""
        return self.server_id is not None

    def add_spending(self, amount: Decimal) -> None:
        """
        Add spending to this budget item.

        Args:
            amount: Amount to add (positive for spending, negative for refunds)
        """
        self.spent_amount += amount
        self.updated_at = datetime.utcnow()

    def reset_spending(self) -> None:
        """Reset the spent amount to zero."""
        self.spent_amount = Decimal("0.00")
        self.updated_at = datetime.utcnow()

    def update_planned(self, amount: Decimal) -> None:
        """
        Update the planned amount for this budget item.

        Args:
            amount: New planned amount
        """
        self.planned_amount = amount
        self.updated_at = datetime.utcnow()

    def calculate_progress(self) -> dict:
        """
        Calculate comprehensive progress statistics for this item.

        Returns:
            Dictionary containing:
                - planned_amount: Planned spending amount
                - spent_amount: Actual spent amount
                - remaining_amount: Remaining amount
                - progress_percentage: Progress as percentage
                - is_over_budget: Whether spending exceeds planned
                - status: 'on_track', 'warning', or 'over_budget'
        """
        progress = self.progress_percentage
        if progress > 100:
            status = "over_budget"
        elif progress >= 80:
            status = "warning"
        else:
            status = "on_track"

        return {
            "planned_amount": self.planned_amount,
            "spent_amount": self.spent_amount,
            "remaining_amount": self.remaining_amount,
            "progress_percentage": progress,
            "is_over_budget": self.is_over_budget,
            "status": status,
        }

    def mark_as_synced(self, server_id: int) -> None:
        """Mark the budget item as synced with the given server ID."""
        self.server_id = server_id
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_by_server_id(cls, session: Session, server_id: int) -> Optional["BudgetItem"]:
        """Retrieve a budget item by its server ID."""
        return session.query(cls).filter(cls.server_id == server_id).first()

    @classmethod
    def get_by_budget(cls, session: Session, budget_id: int) -> List["BudgetItem"]:
        """Get all budget items for a specific budget."""
        return session.query(cls).filter(cls.budget_id == budget_id).all()

    @classmethod
    def get_by_category(
        cls,
        session: Session,
        category_id: int
    ) -> List["BudgetItem"]:
        """Get all budget items for a specific category across all budgets."""
        return session.query(cls).filter(cls.category_id == category_id).all()

    @classmethod
    def get_over_budget(cls, session: Session, budget_id: int) -> List["BudgetItem"]:
        """Get all budget items that are over budget."""
        return session.query(cls).filter(
            cls.budget_id == budget_id,
            cls.spent_amount > cls.planned_amount
        ).all()

    @classmethod
    def get_unsynced_for_budget(cls, session: Session, budget_id: int) -> List["BudgetItem"]:
        """Get all budget items that haven't been synced to the server."""
        return session.query(cls).filter(
            cls.budget_id == budget_id,
            cls.server_id.is_(None)
        ).all()
