"""Tests for Transaction models."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.db import IntegrityError
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionCategory, RecurringTransaction


@pytest.mark.django_db
class TestTransactionCategory:
    """Tests for TransactionCategory model."""

    def test_str_expense(self, category):
        assert str(category) == "Groceries (expense)"

    def test_str_income(self, income_category):
        assert str(income_category) == "Salary (income)"

    def test_default_color(self, user):
        cat = TransactionCategory.objects.create(
            user=user, name="Test", type="expense"
        )
        assert cat.color == "#6366f1"

    def test_default_is_default(self, category):
        assert category.is_default is False

    def test_blank_icon(self, user):
        cat = TransactionCategory.objects.create(
            user=user, name="NoIcon", type="expense"
        )
        assert cat.icon == ""

    def test_unique_together(self, user, category):
        with pytest.raises(IntegrityError):
            TransactionCategory.objects.create(
                user=user, name="Groceries", type="expense"
            )

    def test_same_name_different_type(self, user, category):
        cat = TransactionCategory.objects.create(
            user=user, name="Groceries", type="income"
        )
        assert cat.name == "Groceries"
        assert cat.type == "income"

    def test_same_name_different_user(self, user2, category):
        cat = TransactionCategory.objects.create(
            user=user2, name="Groceries", type="expense"
        )
        assert cat.user == user2

    def test_ordering(self, user):
        TransactionCategory.objects.create(user=user, name="Zebra", type="expense")
        TransactionCategory.objects.create(user=user, name="Alpha", type="expense")
        cats = list(TransactionCategory.objects.filter(user=user))
        names = [c.name for c in cats]
        assert names == sorted(names)

    def test_timestamps(self, category):
        assert category.created_at is not None
        assert category.updated_at is not None

    def test_verbose_names(self):
        assert TransactionCategory._meta.verbose_name == "transaction category"
        assert TransactionCategory._meta.verbose_name_plural == "transaction categories"


@pytest.mark.django_db
class TestTransaction:
    """Tests for Transaction model."""

    def test_str(self, transaction):
        expected = f"expense: 42.50 on {timezone.now().date()}"
        assert str(transaction) == expected

    def test_signed_amount_expense(self, transaction):
        assert transaction.signed_amount == Decimal("-42.50")

    def test_signed_amount_income(self, income_transaction):
        assert income_transaction.signed_amount == Decimal("3000.00")

    def test_signed_amount_transfer(self, user):
        tx = Transaction.objects.create(
            user=user,
            amount=Decimal("100.00"),
            type="transfer",
            transaction_date=date.today(),
        )
        assert tx.signed_amount == Decimal("100.00")

    def test_signed_amount_expense_abs(self, user):
        """signed_amount uses abs() so even if stored positive, expense is negative."""
        tx = Transaction.objects.create(
            user=user,
            amount=Decimal("50.00"),
            type="expense",
            transaction_date=date.today(),
        )
        assert tx.signed_amount == Decimal("-50.00")

    def test_default_values(self, user):
        tx = Transaction.objects.create(
            user=user,
            amount=Decimal("10.00"),
            type="expense",
            transaction_date=date.today(),
        )
        assert tx.is_recurring is False
        assert tx.is_manual is True
        assert tx.tags == []
        assert tx.attachments == []
        assert tx.description == ""
        assert tx.merchant == ""
        assert tx.reference == ""
        assert tx.notes == ""

    def test_nullable_fields(self, user):
        tx = Transaction.objects.create(
            user=user,
            amount=Decimal("10.00"),
            type="expense",
            transaction_date=date.today(),
        )
        assert tx.bank_account is None
        assert tx.category is None
        assert tx.ai_category_suggestion is None
        assert tx.ai_confidence is None

    def test_ordering(self, user):
        Transaction.objects.create(
            user=user,
            amount=Decimal("10.00"),
            type="expense",
            transaction_date=date.today() - timedelta(days=2),
        )
        Transaction.objects.create(
            user=user,
            amount=Decimal("20.00"),
            type="expense",
            transaction_date=date.today(),
        )
        transactions = list(Transaction.objects.filter(user=user))
        assert transactions[0].transaction_date >= transactions[-1].transaction_date

    def test_json_tags(self, user):
        tx = Transaction.objects.create(
            user=user,
            amount=Decimal("10.00"),
            type="expense",
            transaction_date=date.today(),
            tags=["food", "weekly"],
        )
        assert tx.tags == ["food", "weekly"]

    def test_timestamps(self, transaction):
        assert transaction.created_at is not None
        assert transaction.updated_at is not None

    def test_verbose_names(self):
        assert Transaction._meta.verbose_name == "transaction"
        assert Transaction._meta.verbose_name_plural == "transactions"


@pytest.mark.django_db
class TestRecurringTransaction:
    """Tests for RecurringTransaction model."""

    def test_str(self, recurring_transaction):
        assert str(recurring_transaction) == "Netflix (monthly)"

    def test_fields(self, recurring_transaction):
        assert recurring_transaction.amount == Decimal("15.99")
        assert recurring_transaction.type == "expense"
        assert recurring_transaction.frequency == "monthly"
        assert recurring_transaction.is_active is True

    def test_ordering(self, user, category):
        RecurringTransaction.objects.create(
            user=user, name="Earlier", amount=Decimal("10.00"),
            type="expense", frequency="monthly",
            start_date=date.today(),
            next_occurrence=date.today() + timedelta(days=10),
        )
        RecurringTransaction.objects.create(
            user=user, name="Later", amount=Decimal("20.00"),
            type="expense", frequency="monthly",
            start_date=date.today(),
            next_occurrence=date.today() + timedelta(days=30),
        )
        rts = list(RecurringTransaction.objects.filter(user=user))
        assert rts[0].next_occurrence <= rts[-1].next_occurrence

    def test_end_date_optional(self, user):
        rt = RecurringTransaction.objects.create(
            user=user, name="No End", amount=Decimal("10.00"),
            type="income", frequency="weekly",
            start_date=date.today(),
            next_occurrence=date.today() + timedelta(days=7),
        )
        assert rt.end_date is None

    def test_timestamps(self, recurring_transaction):
        assert recurring_transaction.created_at is not None
        assert recurring_transaction.updated_at is not None

    def test_verbose_names(self):
        assert RecurringTransaction._meta.verbose_name == "recurring transaction"
        assert RecurringTransaction._meta.verbose_name_plural == "recurring transactions"
