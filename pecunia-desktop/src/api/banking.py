"""
Banking API client for Pecunia Desktop.

Handles all banking-related API operations including Plaid integration,
account linking, and transaction synchronization.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import Endpoints
from .client import APIClient, APIResponse, APIError

logger = logging.getLogger(__name__)


class AccountType(Enum):
    """Bank account types."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    INVESTMENT = "investment"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OTHER = "other"


class AccountSubtype(Enum):
    """Bank account subtypes."""
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money market"
    CD = "cd"
    CREDIT_CARD = "credit card"
    AUTO = "auto"
    STUDENT = "student"
    MORTGAGE = "mortgage"
    HOME_EQUITY = "home equity"
    BROKERAGE = "brokerage"
    IRA = "ira"
    ROTH = "roth"
    K401 = "401k"
    OTHER = "other"


class ConnectionStatus(Enum):
    """Bank connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"
    REQUIRES_REAUTH = "requires_reauth"


@dataclass
class Institution:
    """Represents a financial institution."""
    id: str
    name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    url: Optional[str] = None
    country_codes: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Institution':
        """Create Institution from dictionary."""
        return cls(
            id=data.get('id', data.get('institution_id', '')),
            name=data.get('name', ''),
            logo_url=data.get('logo_url', data.get('logo')),
            primary_color=data.get('primary_color'),
            url=data.get('url'),
            country_codes=data.get('country_codes', []),
            products=data.get('products', []),
        )


@dataclass
class BankAccount:
    """Represents a linked bank account."""
    id: str
    name: str
    official_name: Optional[str]
    type: str
    subtype: Optional[str]
    mask: Optional[str]
    current_balance: Optional[float]
    available_balance: Optional[float]
    limit: Optional[float]
    currency: str
    institution_id: Optional[str]
    institution_name: Optional[str]
    connection_status: str
    last_synced: Optional[str]
    is_active: bool = True
    plaid_account_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BankAccount':
        """Create BankAccount from dictionary."""
        balances = data.get('balances', {})

        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            official_name=data.get('official_name'),
            type=data.get('type', AccountType.OTHER.value),
            subtype=data.get('subtype'),
            mask=data.get('mask'),
            current_balance=balances.get('current') if balances else data.get('current_balance'),
            available_balance=balances.get('available') if balances else data.get('available_balance'),
            limit=balances.get('limit') if balances else data.get('limit'),
            currency=data.get('currency', data.get('iso_currency_code', 'USD')),
            institution_id=data.get('institution_id'),
            institution_name=data.get('institution_name'),
            connection_status=data.get('connection_status', ConnectionStatus.CONNECTED.value),
            last_synced=data.get('last_synced'),
            is_active=data.get('is_active', True),
            plaid_account_id=data.get('plaid_account_id', data.get('account_id')),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    @property
    def display_name(self) -> str:
        """Get display name with mask."""
        if self.mask:
            return f"{self.name} (****{self.mask})"
        return self.name

    @property
    def is_credit(self) -> bool:
        """Check if this is a credit account."""
        return self.type == AccountType.CREDIT.value

    @property
    def balance(self) -> float:
        """Get the primary balance (current or available)."""
        return self.current_balance or self.available_balance or 0.0


@dataclass
class LinkToken:
    """Plaid Link token for account linking."""
    link_token: str
    expiration: str
    request_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LinkToken':
        """Create LinkToken from dictionary."""
        return cls(
            link_token=data.get('link_token', ''),
            expiration=data.get('expiration', ''),
            request_id=data.get('request_id'),
        )


@dataclass
class SyncResult:
    """Result of a transaction sync operation."""
    added: int
    modified: int
    removed: int
    accounts_synced: int
    has_more: bool
    next_cursor: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncResult':
        """Create SyncResult from dictionary."""
        return cls(
            added=data.get('added', 0),
            modified=data.get('modified', 0),
            removed=data.get('removed', 0),
            accounts_synced=data.get('accounts_synced', 0),
            has_more=data.get('has_more', False),
            next_cursor=data.get('next_cursor'),
            errors=data.get('errors', []),
        )

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return self.added + self.modified + self.removed


@dataclass
class AccountBalance:
    """Account balance information."""
    account_id: str
    current: Optional[float]
    available: Optional[float]
    limit: Optional[float]
    currency: str
    last_updated: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountBalance':
        """Create AccountBalance from dictionary."""
        balances = data.get('balances', data)
        return cls(
            account_id=data.get('account_id', ''),
            current=balances.get('current'),
            available=balances.get('available'),
            limit=balances.get('limit'),
            currency=data.get('iso_currency_code', data.get('currency', 'USD')),
            last_updated=data.get('last_updated', ''),
        )


class BankingAPI:
    """
    API client for banking operations.

    Provides methods for linking bank accounts via Plaid,
    syncing transactions, and managing connected accounts.
    """

    def __init__(self, api_client: APIClient):
        """
        Initialize the banking API client.

        Args:
            api_client: The base API client instance.
        """
        self._client = api_client

    async def create_link_token(
        self,
        redirect_uri: Optional[str] = None,
        products: Optional[List[str]] = None,
    ) -> LinkToken:
        """
        Create a Plaid Link token for account linking.

        Args:
            redirect_uri: OAuth redirect URI (for OAuth institutions).
            products: List of Plaid products to enable.

        Returns:
            LinkToken object for initializing Plaid Link.
        """
        data = {}
        if redirect_uri:
            data['redirect_uri'] = redirect_uri
        if products:
            data['products'] = products

        response = await self._client.post(
            Endpoints.BANKING_LINK_TOKEN,
            data=data if data else None,
        )

        if not response.is_ok:
            raise APIError("Failed to create link token", response.status_code, response)

        return LinkToken.from_dict(response.data)

    async def exchange_public_token(
        self,
        public_token: str,
        institution_id: Optional[str] = None,
        account_ids: Optional[List[str]] = None,
    ) -> List[BankAccount]:
        """
        Exchange a Plaid public token for access token and link accounts.

        Args:
            public_token: Public token from Plaid Link.
            institution_id: Institution ID from Plaid.
            account_ids: Specific account IDs to link (optional).

        Returns:
            List of newly linked BankAccount objects.
        """
        data = {'public_token': public_token}
        if institution_id:
            data['institution_id'] = institution_id
        if account_ids:
            data['account_ids'] = account_ids

        response = await self._client.post(
            Endpoints.BANKING_EXCHANGE_TOKEN,
            data=data,
        )

        if not response.is_ok:
            raise APIError("Failed to exchange token", response.status_code, response)

        accounts = response.data.get('accounts', response.data)
        if isinstance(accounts, list):
            return [BankAccount.from_dict(a) for a in accounts]
        return [BankAccount.from_dict(accounts)]

    async def list_accounts(
        self,
        include_inactive: bool = False,
    ) -> List[BankAccount]:
        """
        List all linked bank accounts.

        Args:
            include_inactive: Whether to include inactive accounts.

        Returns:
            List of BankAccount objects.
        """
        params = {}
        if include_inactive:
            params['include_inactive'] = 'true'

        response = await self._client.get(
            Endpoints.BANKING_ACCOUNTS,
            params=params,
        )

        if not response.is_ok:
            raise APIError("Failed to fetch accounts", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [BankAccount.from_dict(a) for a in items]

    async def get_account(self, account_id: str) -> BankAccount:
        """
        Get a single bank account by ID.

        Args:
            account_id: The account ID.

        Returns:
            BankAccount object.

        Raises:
            APIError: If account not found.
        """
        endpoint = Endpoints.BANKING_ACCOUNTS_BY_ID.format(id=account_id)
        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Account not found", response.status_code, response)

        return BankAccount.from_dict(response.data)

    async def update_account(
        self,
        account_id: str,
        updates: Dict[str, Any],
    ) -> BankAccount:
        """
        Update account settings.

        Args:
            account_id: The account ID.
            updates: Dictionary of fields to update.

        Returns:
            Updated BankAccount object.
        """
        endpoint = Endpoints.BANKING_ACCOUNTS_BY_ID.format(id=account_id)
        response = await self._client.patch(endpoint, data=updates)

        if not response.is_ok:
            raise APIError("Failed to update account", response.status_code, response)

        return BankAccount.from_dict(response.data)

    async def remove_account(self, account_id: str) -> bool:
        """
        Remove/unlink a bank account.

        Args:
            account_id: The account ID to remove.

        Returns:
            True if removal was successful.
        """
        endpoint = Endpoints.BANKING_ACCOUNTS_BY_ID.format(id=account_id)
        response = await self._client.delete(endpoint)

        if not response.is_ok:
            raise APIError("Failed to remove account", response.status_code, response)

        return True

    async def sync_transactions(
        self,
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> SyncResult:
        """
        Sync transactions from linked accounts.

        Args:
            account_id: Optional specific account to sync.
            cursor: Pagination cursor for incremental sync.

        Returns:
            SyncResult with counts of changes.
        """
        data = {}
        if account_id:
            data['account_id'] = account_id
        if cursor:
            data['cursor'] = cursor

        response = await self._client.post(
            Endpoints.BANKING_SYNC,
            data=data if data else None,
        )

        if not response.is_ok:
            raise APIError("Failed to sync transactions", response.status_code, response)

        return SyncResult.from_dict(response.data)

    async def sync_all(self) -> SyncResult:
        """
        Sync transactions from all linked accounts.

        Returns:
            Combined SyncResult from all accounts.
        """
        total_result = SyncResult(
            added=0,
            modified=0,
            removed=0,
            accounts_synced=0,
            has_more=False,
        )

        # Sync until no more data
        cursor = None
        while True:
            result = await self.sync_transactions(cursor=cursor)
            total_result.added += result.added
            total_result.modified += result.modified
            total_result.removed += result.removed
            total_result.accounts_synced += result.accounts_synced
            total_result.errors.extend(result.errors)

            if not result.has_more:
                break
            cursor = result.next_cursor

        return total_result

    async def get_balances(
        self,
        account_ids: Optional[List[str]] = None,
    ) -> List[AccountBalance]:
        """
        Get current balances for accounts.

        Args:
            account_ids: Optional list of specific account IDs.

        Returns:
            List of AccountBalance objects.
        """
        params = {}
        if account_ids:
            params['account_ids'] = ','.join(account_ids)

        response = await self._client.get(
            f"{Endpoints.BANKING_ACCOUNTS}/balances",
            params=params,
        )

        if not response.is_ok:
            raise APIError("Failed to fetch balances", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [AccountBalance.from_dict(b) for b in items]

    async def refresh_balances(
        self,
        account_id: Optional[str] = None,
    ) -> List[AccountBalance]:
        """
        Force refresh balances from the bank.

        Args:
            account_id: Optional specific account to refresh.

        Returns:
            Updated AccountBalance objects.
        """
        data = {}
        if account_id:
            data['account_id'] = account_id

        response = await self._client.post(
            f"{Endpoints.BANKING_ACCOUNTS}/refresh-balances",
            data=data if data else None,
        )

        if not response.is_ok:
            raise APIError("Failed to refresh balances", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [AccountBalance.from_dict(b) for b in items]

    async def search_institutions(
        self,
        query: str,
        country_codes: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Institution]:
        """
        Search for financial institutions.

        Args:
            query: Search query string.
            country_codes: Filter by country codes.
            limit: Maximum number of results.

        Returns:
            List of matching Institution objects.
        """
        params = {
            'query': query,
            'limit': limit,
        }
        if country_codes:
            params['country_codes'] = ','.join(country_codes)

        response = await self._client.get(
            Endpoints.BANKING_INSTITUTIONS,
            params=params,
        )

        if not response.is_ok:
            raise APIError("Failed to search institutions", response.status_code, response)

        items = response.data.get('institutions', response.data) if isinstance(response.data, dict) else response.data
        return [Institution.from_dict(i) for i in items]

    async def get_institution(self, institution_id: str) -> Institution:
        """
        Get details for a specific institution.

        Args:
            institution_id: The institution ID.

        Returns:
            Institution object.
        """
        response = await self._client.get(
            f"{Endpoints.BANKING_INSTITUTIONS}/{institution_id}",
        )

        if not response.is_ok:
            raise APIError("Institution not found", response.status_code, response)

        return Institution.from_dict(response.data)

    async def reauthorize_account(self, account_id: str) -> LinkToken:
        """
        Get a link token for re-authorizing an account.

        Args:
            account_id: The account ID that needs reauthorization.

        Returns:
            LinkToken for update mode.
        """
        response = await self._client.post(
            f"{Endpoints.BANKING_ACCOUNTS}/{account_id}/reauthorize",
        )

        if not response.is_ok:
            raise APIError("Failed to create reauth token", response.status_code, response)

        return LinkToken.from_dict(response.data)

    async def get_connection_status(
        self,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get connection status for linked accounts.

        Args:
            account_id: Optional specific account.

        Returns:
            Dictionary with connection status information.
        """
        endpoint = Endpoints.BANKING_ACCOUNTS
        if account_id:
            endpoint = f"{endpoint}/{account_id}/status"
        else:
            endpoint = f"{endpoint}/status"

        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Failed to get connection status", response.status_code, response)

        return response.data

    async def activate_account(self, account_id: str) -> BankAccount:
        """
        Activate a deactivated account.

        Args:
            account_id: The account ID.

        Returns:
            Updated BankAccount.
        """
        return await self.update_account(account_id, {'is_active': True})

    async def deactivate_account(self, account_id: str) -> BankAccount:
        """
        Deactivate an account (stop syncing).

        Args:
            account_id: The account ID.

        Returns:
            Updated BankAccount.
        """
        return await self.update_account(account_id, {'is_active': False})

    async def rename_account(self, account_id: str, new_name: str) -> BankAccount:
        """
        Rename a linked account.

        Args:
            account_id: The account ID.
            new_name: New display name.

        Returns:
            Updated BankAccount.
        """
        return await self.update_account(account_id, {'name': new_name})
