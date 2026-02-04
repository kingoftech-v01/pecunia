"""Tests for src/api/banking.py — Banking API client."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from api.client import APIResponse, APIError
from api.banking import (
    BankingAPI, BankAccount, Institution, LinkToken, SyncResult,
    AccountBalance, AccountType, AccountSubtype, ConnectionStatus,
)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def api(mock_client):
    return BankingAPI(mock_client)


class TestEnums:
    """Tests for banking enums."""

    def test_account_type_values(self):
        assert AccountType.CHECKING.value == "checking"
        assert AccountType.SAVINGS.value == "savings"
        assert AccountType.CREDIT.value == "credit"

    def test_account_subtype_values(self):
        assert AccountSubtype.CREDIT_CARD.value == "credit card"
        assert AccountSubtype.BROKERAGE.value == "brokerage"

    def test_connection_status_values(self):
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.ERROR.value == "error"
        assert ConnectionStatus.REQUIRES_REAUTH.value == "requires_reauth"


class TestInstitution:
    """Tests for Institution dataclass."""

    def test_from_dict(self):
        data = {
            "id": "ins1", "name": "Test Bank",
            "logo_url": "https://logo.png", "primary_color": "#0000FF",
            "country_codes": ["US"], "products": ["transactions"],
        }
        inst = Institution.from_dict(data)
        assert inst.name == "Test Bank"
        assert "US" in inst.country_codes

    def test_from_dict_alternative_keys(self):
        data = {"institution_id": "ins2", "name": "Bank", "logo": "https://logo.png"}
        inst = Institution.from_dict(data)
        assert inst.id == "ins2"
        assert inst.logo_url == "https://logo.png"


class TestBankAccount:
    """Tests for BankAccount dataclass."""

    def test_from_dict_with_balances(self):
        data = {
            "id": "a1", "name": "Checking", "type": "checking",
            "balances": {"current": 1500.50, "available": 1200.00, "limit": None},
            "currency": "USD", "connection_status": "connected",
        }
        acct = BankAccount.from_dict(data)
        assert acct.current_balance == 1500.50
        assert acct.available_balance == 1200.00

    def test_from_dict_flat_balances(self):
        data = {
            "id": "a2", "name": "Savings", "type": "savings",
            "current_balance": 5000, "available_balance": 5000,
            "currency": "USD", "connection_status": "connected",
        }
        acct = BankAccount.from_dict(data)
        assert acct.current_balance == 5000

    def test_display_name_with_mask(self):
        acct = BankAccount(
            id="a1", name="Checking", official_name=None, type="checking",
            subtype=None, mask="1234", current_balance=100, available_balance=100,
            limit=None, currency="USD", institution_id=None, institution_name=None,
            connection_status="connected", last_synced=None,
        )
        assert "****1234" in acct.display_name

    def test_display_name_without_mask(self):
        acct = BankAccount(
            id="a1", name="Checking", official_name=None, type="checking",
            subtype=None, mask=None, current_balance=100, available_balance=100,
            limit=None, currency="USD", institution_id=None, institution_name=None,
            connection_status="connected", last_synced=None,
        )
        assert acct.display_name == "Checking"

    def test_is_credit(self):
        acct = BankAccount(
            id="a1", name="CC", official_name=None, type="credit",
            subtype=None, mask=None, current_balance=-500, available_balance=None,
            limit=5000, currency="USD", institution_id=None, institution_name=None,
            connection_status="connected", last_synced=None,
        )
        assert acct.is_credit is True

    def test_is_not_credit(self):
        acct = BankAccount(
            id="a1", name="Check", official_name=None, type="checking",
            subtype=None, mask=None, current_balance=100, available_balance=None,
            limit=None, currency="USD", institution_id=None, institution_name=None,
            connection_status="connected", last_synced=None,
        )
        assert acct.is_credit is False

    def test_balance_property(self):
        acct = BankAccount(
            id="a1", name="Check", official_name=None, type="checking",
            subtype=None, mask=None, current_balance=1500, available_balance=1200,
            limit=None, currency="USD", institution_id=None, institution_name=None,
            connection_status="connected", last_synced=None,
        )
        assert acct.balance == 1500

    def test_balance_fallback(self):
        acct = BankAccount(
            id="a1", name="Check", official_name=None, type="checking",
            subtype=None, mask=None, current_balance=None, available_balance=1200,
            limit=None, currency="USD", institution_id=None, institution_name=None,
            connection_status="connected", last_synced=None,
        )
        assert acct.balance == 1200


class TestLinkToken:
    """Tests for LinkToken."""

    def test_from_dict(self):
        data = {"link_token": "lt_abc", "expiration": "2024-12-31", "request_id": "req1"}
        token = LinkToken.from_dict(data)
        assert token.link_token == "lt_abc"
        assert token.request_id == "req1"


class TestSyncResult:
    """Tests for SyncResult."""

    def test_from_dict(self):
        data = {"added": 10, "modified": 3, "removed": 1, "accounts_synced": 2, "has_more": False}
        result = SyncResult.from_dict(data)
        assert result.total_changes == 14
        assert result.has_more is False

    def test_total_changes(self):
        result = SyncResult(added=5, modified=2, removed=1, accounts_synced=1, has_more=False)
        assert result.total_changes == 8


class TestAccountBalance:
    """Tests for AccountBalance."""

    def test_from_dict(self):
        data = {
            "account_id": "a1",
            "balances": {"current": 1500, "available": 1200, "limit": None},
            "iso_currency_code": "USD",
            "last_updated": "2024-01-15",
        }
        balance = AccountBalance.from_dict(data)
        assert balance.current == 1500
        assert balance.currency == "USD"


class TestBankingAPI:
    """Tests for BankingAPI methods."""

    async def test_create_link_token(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"link_token": "lt_123", "expiration": "2024-12-31"},
        )
        token = await api.create_link_token()
        assert token.link_token == "lt_123"

    async def test_exchange_public_token(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"accounts": [
                {"id": "a1", "name": "Checking", "type": "checking", "currency": "USD",
                 "connection_status": "connected"},
            ]},
        )
        accounts = await api.exchange_public_token("public_abc")
        assert len(accounts) == 1

    async def test_list_accounts(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data=[
                {"id": "a1", "name": "Checking", "type": "checking", "currency": "USD",
                 "connection_status": "connected"},
            ],
        )
        accounts = await api.list_accounts()
        assert len(accounts) == 1

    async def test_get_account(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "a1", "name": "Checking", "type": "checking", "currency": "USD",
                  "connection_status": "connected"},
        )
        acct = await api.get_account("a1")
        assert acct.name == "Checking"

    async def test_get_account_not_found(self, api, mock_client):
        mock_client.get.return_value = APIResponse(success=False, status_code=404, data={})
        with pytest.raises(APIError):
            await api.get_account("nonexistent")

    async def test_update_account(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "a1", "name": "Renamed", "type": "checking", "currency": "USD",
                  "connection_status": "connected"},
        )
        acct = await api.update_account("a1", {"name": "Renamed"})
        assert acct.name == "Renamed"

    async def test_remove_account(self, api, mock_client):
        mock_client.delete.return_value = APIResponse(success=True, status_code=200, data={})
        result = await api.remove_account("a1")
        assert result is True

    async def test_sync_transactions(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"added": 5, "modified": 1, "removed": 0, "accounts_synced": 1, "has_more": False},
        )
        result = await api.sync_transactions("a1")
        assert result.added == 5

    async def test_sync_all(self, api, mock_client):
        mock_client.post.side_effect = [
            APIResponse(success=True, status_code=200,
                        data={"added": 3, "modified": 1, "removed": 0,
                              "accounts_synced": 1, "has_more": True, "next_cursor": "c1"}),
            APIResponse(success=True, status_code=200,
                        data={"added": 2, "modified": 0, "removed": 1,
                              "accounts_synced": 1, "has_more": False}),
        ]
        result = await api.sync_all()
        assert result.added == 5
        assert result.removed == 1
        assert result.accounts_synced == 2

    async def test_get_balances(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data=[{"account_id": "a1", "current": 1500, "available": 1200,
                   "limit": None, "currency": "USD", "last_updated": "2024-01-15"}],
        )
        balances = await api.get_balances()
        assert len(balances) == 1

    async def test_search_institutions(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"institutions": [{"id": "ins1", "name": "Chase"}]},
        )
        results = await api.search_institutions("chase")
        assert len(results) == 1
        assert results[0].name == "Chase"

    async def test_reauthorize_account(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"link_token": "lt_reauth", "expiration": "2024-12-31"},
        )
        token = await api.reauthorize_account("a1")
        assert token.link_token == "lt_reauth"

    async def test_activate_account(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "a1", "name": "Checking", "type": "checking", "currency": "USD",
                  "connection_status": "connected", "is_active": True},
        )
        acct = await api.activate_account("a1")
        assert acct.is_active is True

    async def test_rename_account(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "a1", "name": "My Checking", "type": "checking", "currency": "USD",
                  "connection_status": "connected"},
        )
        acct = await api.rename_account("a1", "My Checking")
        assert acct.name == "My Checking"
