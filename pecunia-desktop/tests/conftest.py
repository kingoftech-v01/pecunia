"""
Root conftest.py for Pecunia Desktop test suite.

Provides shared fixtures for API, database, sync, and service tests.
"""
import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Temp directories
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def config_dir(tmp_path):
    """Provide a temporary config directory."""
    d = tmp_path / "config"
    d.mkdir()
    return d


@pytest.fixture
def data_dir(tmp_path):
    """Provide a temporary data directory."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def backup_dir(tmp_path):
    """Provide a temporary backup directory."""
    d = tmp_path / "backups"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config(tmp_path):
    """Create a mock configuration."""
    config_data = {
        "api_base_url": "https://api.test.pecunia.com/api/v1",
        "data_dir": str(tmp_path / "data"),
        "log_level": "DEBUG",
        "sync_interval": 300,
        "auto_sync": False,
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))
    return config_data


# ---------------------------------------------------------------------------
# API / Auth fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_tokens():
    """Return mock JWT tokens."""
    return {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_access",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_refresh",
    }


@pytest.fixture
def mock_user_data():
    """Return mock user API response data."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "full_name": "Test User",
        "subscription_tier": "free",
        "preferred_currency": "EUR",
        "is_email_verified": True,
        "date_joined": "2024-01-01T00:00:00Z",
        "last_login": "2024-06-01T12:00:00Z",
    }


@pytest.fixture
def mock_http_session():
    """Create a mock aiohttp session."""
    session = AsyncMock()
    session.closed = False
    return session


# ---------------------------------------------------------------------------
# Transaction fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_transaction_data():
    """Return sample transaction data."""
    return {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "amount": "42.50",
        "type": "expense",
        "description": "Weekly groceries",
        "merchant": "Carrefour",
        "transaction_date": "2024-06-15",
        "category": {
            "id": "770e8400-e29b-41d4-a716-446655440002",
            "name": "Groceries",
            "type": "expense",
        },
        "tags": ["food", "weekly"],
        "is_recurring": False,
        "is_manual": True,
        "created_at": "2024-06-15T10:00:00Z",
        "updated_at": "2024-06-15T10:00:00Z",
    }


@pytest.fixture
def sample_transactions_list(sample_transaction_data):
    """Return a list of sample transactions."""
    txns = []
    for i in range(5):
        t = sample_transaction_data.copy()
        t["id"] = f"660e8400-e29b-41d4-a716-44665544000{i}"
        t["amount"] = str(Decimal("42.50") + Decimal(i * 10))
        t["description"] = f"Transaction {i}"
        txns.append(t)
    return txns


# ---------------------------------------------------------------------------
# Budget fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_budget_data():
    """Return sample budget data."""
    return {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "name": "January Budget",
        "period_type": "monthly",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "total_planned_amount": "2000.00",
        "total_spent_amount": "500.00",
        "is_active": True,
        "items": [],
    }


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_session():
    """Create a mock async SQLAlchemy session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


# ---------------------------------------------------------------------------
# Sync fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_sync_queue():
    """Create a mock sync queue."""
    queue = MagicMock()
    queue.push = AsyncMock()
    queue.pop = AsyncMock(return_value=None)
    queue.size = MagicMock(return_value=0)
    return queue


# ---------------------------------------------------------------------------
# Keyring fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_keyring():
    """Mock the keyring module."""
    with patch("keyring.get_password", return_value=None), \
         patch("keyring.set_password"), \
         patch("keyring.delete_password"):
        yield
