"""
Root conftest.py for Pecunia Web project.

Provides shared fixtures, factories, and utilities for all tests.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserProfile
from apps.transactions.models import Transaction, TransactionCategory, RecurringTransaction
from apps.budgets.models import Budget, BudgetItem
from apps.banking.models import BankConnection, BankAccount, SyncLog


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_password():
    return "TestP@ssw0rd123!"


@pytest.fixture
def user(db, user_password):
    """Create a basic test user."""
    u = User.objects.create_user(
        email="testuser@example.com",
        password=user_password,
        first_name="Test",
        last_name="User",
        preferred_currency="EUR",
    )
    return u


@pytest.fixture
def user2(db, user_password):
    """Create a second test user for isolation tests."""
    return User.objects.create_user(
        email="otheruser@example.com",
        password=user_password,
        first_name="Other",
        last_name="User",
        preferred_currency="USD",
    )


@pytest.fixture
def superuser(db, user_password):
    """Create a superuser."""
    return User.objects.create_superuser(
        email="admin@example.com",
        password=user_password,
    )


@pytest.fixture
def premium_user(db, user_password):
    """Create a premium-tier user."""
    return User.objects.create_user(
        email="premium@example.com",
        password=user_password,
        first_name="Premium",
        last_name="User",
        subscription_tier="premium",
    )


@pytest.fixture
def inactive_user(db, user_password):
    """Create an inactive user."""
    u = User.objects.create_user(
        email="inactive@example.com",
        password=user_password,
        is_active=False,
    )
    return u


# ---------------------------------------------------------------------------
# Auth/API fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def auth_client(user):
    """Authenticated API client."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def auth_client2(user2):
    """Authenticated API client for user2."""
    client = APIClient()
    refresh = RefreshToken.for_user(user2)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def user_tokens(user):
    """Return JWT tokens for the test user."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


# ---------------------------------------------------------------------------
# Transaction fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def category(db, user):
    """Create a test transaction category."""
    return TransactionCategory.objects.create(
        user=user,
        name="Groceries",
        type="expense",
        icon="shopping-cart",
        color="#22c55e",
    )


@pytest.fixture
def income_category(db, user):
    """Create an income category."""
    return TransactionCategory.objects.create(
        user=user,
        name="Salary",
        type="income",
        icon="briefcase",
        color="#3b82f6",
    )


@pytest.fixture
def transaction(db, user, category):
    """Create a test transaction."""
    return Transaction.objects.create(
        user=user,
        category=category,
        amount=Decimal("42.50"),
        type="expense",
        description="Weekly groceries",
        merchant="Carrefour",
        transaction_date=timezone.now().date(),
    )


@pytest.fixture
def income_transaction(db, user, income_category):
    """Create an income transaction."""
    return Transaction.objects.create(
        user=user,
        category=income_category,
        amount=Decimal("3000.00"),
        type="income",
        description="Monthly salary",
        merchant="Employer Inc.",
        transaction_date=timezone.now().date(),
    )


@pytest.fixture
def recurring_transaction(db, user, category):
    """Create a recurring transaction."""
    return RecurringTransaction.objects.create(
        user=user,
        category=category,
        name="Netflix",
        amount=Decimal("15.99"),
        type="expense",
        frequency="monthly",
        start_date=timezone.now().date(),
        next_occurrence=timezone.now().date() + timedelta(days=30),
    )


# ---------------------------------------------------------------------------
# Budget fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def budget(db, user):
    """Create a test budget."""
    return Budget.objects.create(
        user=user,
        name="January Budget",
        period_type="monthly",
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        total_planned_amount=Decimal("2000.00"),
        total_spent_amount=Decimal("500.00"),
    )


@pytest.fixture
def budget_item(db, budget, category):
    """Create a budget item."""
    return BudgetItem.objects.create(
        budget=budget,
        category=category,
        name="Groceries Budget",
        planned_amount=Decimal("500.00"),
        spent_amount=Decimal("150.00"),
    )


# ---------------------------------------------------------------------------
# Banking fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def encryption_key(settings):
    """Set up Fernet encryption key for tests."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    settings.BANK_ENCRYPTION_KEY = key
    return key


@pytest.fixture
def bank_connection(db, user, encryption_key):
    """Create a test bank connection."""
    conn = BankConnection.objects.create(
        user=user,
        provider="plaid",
        institution_id="ins_123",
        institution_name="Test Bank",
        status="active",
    )
    conn.access_token = "test_access_token_123"
    conn.refresh_token = "test_refresh_token_456"
    conn.save()
    return conn


@pytest.fixture
def bank_account(db, user, bank_connection):
    """Create a test bank account."""
    return BankAccount.objects.create(
        user=user,
        connection=bank_connection,
        provider_account_id="acc_123",
        name="Test Checking",
        account_type="checking",
        balance=Decimal("5000.00"),
        available_balance=Decimal("4800.00"),
        currency="EUR",
    )


@pytest.fixture
def sync_log(db, bank_connection):
    """Create a test sync log."""
    return SyncLog.objects.create(
        connection=bank_connection,
        sync_type="full",
        status="success",
        accounts_synced=2,
        transactions_synced=50,
    )
