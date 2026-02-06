"""
Plaid Provider.

Banking provider for international banks via Plaid API.
https://plaid.com/docs/
"""
import requests
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from django.conf import settings

from .base import (
    BaseBankProvider,
    ProviderAccount,
    ProviderTransaction,
    ProviderInstitution,
    AuthorizationResult,
    ProviderError,
    AuthorizationError,
    TokenExpiredError,
)


class PlaidProvider(BaseBankProvider):
    """
    Plaid provider implementation.

    International banking provider with wide coverage.
    Supports banks across US, Canada, UK, and Europe.
    """

    provider_name = 'plaid'
    display_name = 'Plaid'
    supported_countries = ['US', 'CA', 'GB', 'FR', 'ES', 'NL', 'IE', 'DE']

    # API endpoints
    PRODUCTION_URL = 'https://production.plaid.com'
    DEVELOPMENT_URL = 'https://development.plaid.com'
    SANDBOX_URL = 'https://sandbox.plaid.com'

    def __init__(self):
        """Initialize Plaid provider."""
        self.client_id = getattr(settings, 'PLAID_CLIENT_ID', None)
        self.secret = getattr(settings, 'PLAID_SECRET', None)
        self.environment = getattr(settings, 'PLAID_ENVIRONMENT', 'sandbox')
        super().__init__()

    def _validate_configuration(self):
        """Validate Plaid configuration."""
        if not self.client_id:
            raise ProviderError(
                "PLAID_CLIENT_ID not configured",
                code='configuration_error'
            )
        if not self.secret:
            raise ProviderError(
                "PLAID_SECRET not configured",
                code='configuration_error'
            )

    @property
    def api_url(self) -> str:
        """Get API URL based on environment."""
        urls = {
            'production': self.PRODUCTION_URL,
            'development': self.DEVELOPMENT_URL,
            'sandbox': self.SANDBOX_URL,
        }
        return urls.get(self.environment, self.SANDBOX_URL)

    def _get_headers(self) -> dict:
        """Get request headers."""
        return {
            'Content-Type': 'application/json',
        }

    def _request(
        self,
        endpoint: str,
        data: dict = None,
        **kwargs
    ) -> dict:
        """Make API request with error handling."""
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()

        # Add client credentials to data
        request_data = {
            'client_id': self.client_id,
            'secret': self.secret,
            **(data or {}),
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=request_data,
                timeout=30,
                **kwargs
            )

            response_data = response.json()

            if response.status_code >= 400 or 'error_code' in response_data:
                error = response_data.get('error_message', 'Unknown error')
                code = response_data.get('error_code', str(response.status_code))
                raise ProviderError(error, code=code, details=response_data)

            return response_data

        except requests.exceptions.Timeout:
            raise ProviderError("Request timeout", code='timeout')
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Request failed: {str(e)}", code='request_error')

    def create_link_token(
        self,
        user_id: str,
        redirect_uri: str,
        products: List[str] = None,
        country_codes: List[str] = None,
        language: str = 'en',
        **kwargs
    ) -> str:
        """
        Create a Plaid Link token for initialization.

        Plaid uses Link for the OAuth flow instead of direct authorization URLs.
        """
        products = products or ['transactions']
        country_codes = country_codes or ['US', 'GB', 'FR']

        data = {
            'user': {
                'client_user_id': user_id,
            },
            'products': products,
            'country_codes': country_codes,
            'language': language,
            'redirect_uri': redirect_uri,
        }

        # Optional: specify institution
        if kwargs.get('institution_id'):
            data['institution_id'] = kwargs['institution_id']

        # Optional: OAuth link token for reconnection
        if kwargs.get('access_token'):
            data['access_token'] = kwargs['access_token']

        response = self._request('/link/token/create', data)
        return response['link_token']

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        institution_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate Plaid Link initialization URL.

        Note: Plaid uses Link SDK, so this returns the Link token
        which should be used to initialize Link in the frontend.
        """
        user_id = kwargs.get('user_id', state)
        link_token = self.create_link_token(
            user_id=user_id,
            redirect_uri=redirect_uri,
            institution_id=institution_id,
            **kwargs
        )
        # Return link token - frontend will use this with Plaid Link SDK
        return link_token

    def exchange_code(
        self,
        code: str,
        redirect_uri: str
    ) -> AuthorizationResult:
        """
        Exchange public token for access token.

        In Plaid, the 'code' is the public_token from Link.
        """
        response = self._request(
            '/item/public_token/exchange',
            {'public_token': code}
        )

        access_token = response['access_token']
        item_id = response['item_id']

        # Get institution info
        item_response = self._request(
            '/item/get',
            {'access_token': access_token}
        )
        institution_id = item_response.get('item', {}).get('institution_id')

        institution_name = None
        institution_logo = None
        if institution_id:
            try:
                inst_response = self._request(
                    '/institutions/get_by_id',
                    {
                        'institution_id': institution_id,
                        'country_codes': ['US', 'GB', 'FR'],
                    }
                )
                institution = inst_response.get('institution', {})
                institution_name = institution.get('name')
                institution_logo = institution.get('logo')
            except ProviderError:
                pass

        return AuthorizationResult(
            access_token=access_token,
            provider_connection_id=item_id,
            institution_id=institution_id,
            institution_name=institution_name,
            institution_logo_url=institution_logo,
        )

    def refresh_access_token(
        self,
        refresh_token: str
    ) -> AuthorizationResult:
        """
        Plaid access tokens don't expire and don't need refreshing.

        This method is provided for interface compatibility.
        """
        # Plaid access tokens are permanent until revoked
        return AuthorizationResult(
            access_token=refresh_token,  # access_token is passed as refresh_token
        )

    def get_accounts(
        self,
        access_token: str,
        connection_id: Optional[str] = None
    ) -> List[ProviderAccount]:
        """Fetch accounts from Plaid."""
        response = self._request(
            '/accounts/get',
            {'access_token': access_token}
        )

        accounts = []
        for acc in response.get('accounts', []):
            balances = acc.get('balances', {})

            account = ProviderAccount(
                provider_account_id=acc['account_id'],
                name=acc.get('name', 'Unknown Account'),
                official_name=acc.get('official_name'),
                account_type=self.normalize_account_type(
                    acc.get('type', 'other')
                ),
                account_subtype=acc.get('subtype'),
                balance=Decimal(str(balances.get('current', 0) or 0)),
                available_balance=Decimal(str(balances.get('available', 0)))
                    if balances.get('available') is not None else None,
                currency=balances.get('iso_currency_code', 'USD'),
                account_number_masked=acc.get('mask'),
            )
            accounts.append(account)

        return accounts

    def get_transactions(
        self,
        access_token: str,
        account_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[ProviderTransaction]:
        """Fetch transactions from Plaid using cursor-based sync."""
        if not from_date:
            from_date = date.today() - timedelta(days=90)
        if not to_date:
            to_date = date.today()

        # CURSOR-BASED SYNC: We use /transactions/sync instead of /transactions/get
        # because it's more efficient for incremental updates. The sync endpoint
        # returns only changes since the last cursor, whereas get requires
        # re-fetching all transactions. For users with years of history, this
        # reduces API calls from hundreds to just a few.
        transactions = []
        cursor = None
        has_more = True

        while has_more:
            data = {
                'access_token': access_token,
                'cursor': cursor,
                'count': 500,  # Max allowed by Plaid per request
            }

            response = self._request('/transactions/sync', data)

            # Sync returns 'added', 'modified', and 'removed' arrays.
            # We only process 'added' here; modifications/deletions handled separately.
            for tx in response.get('added', []):
                # Filter by account_id if specified
                if account_id and tx.get('account_id') != account_id:
                    continue

                # Filter by date range
                tx_date = date.fromisoformat(tx['date'])
                if tx_date < from_date or tx_date > to_date:
                    continue

                # PLAID AMOUNT SIGN CONVENTION: Plaid uses positive amounts for
                # money leaving the account (debits/expenses) and negative for
                # money entering (credits/income). This is the opposite of bank
                # statement conventions. We store absolute values and use the
                # sign only to determine transaction_type.
                amount = Decimal(str(tx.get('amount', 0)))

                transaction = ProviderTransaction(
                    provider_transaction_id=tx['transaction_id'],
                    account_id=tx['account_id'],
                    amount=abs(amount),
                    currency=tx.get('iso_currency_code', 'USD'),
                    transaction_date=tx_date,
                    description=tx.get('name', ''),
                    transaction_type='debit' if amount > 0 else 'credit',
                    merchant_name=tx.get('merchant_name'),
                    category=tx.get('personal_finance_category', {}).get('primary')
                        if tx.get('personal_finance_category') else
                        (tx.get('category', [None])[0] if tx.get('category') else None),
                    pending=tx.get('pending', False),
                    reference=tx.get('payment_channel'),
                    metadata={
                        'payment_channel': tx.get('payment_channel'),
                        'location': tx.get('location'),
                        'category_id': tx.get('category_id'),
                    }
                )
                transactions.append(transaction)

            cursor = response.get('next_cursor')
            has_more = response.get('has_more', False)

        return transactions

    def get_institutions(
        self,
        country: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[ProviderInstitution]:
        """Get list of supported institutions."""
        country_codes = [country] if country else ['US', 'GB', 'FR', 'CA']

        data = {
            'country_codes': country_codes,
            'count': 500,
            'offset': 0,
        }

        if search:
            # Use search endpoint
            data['query'] = search
            response = self._request('/institutions/search', data)
        else:
            response = self._request('/institutions/get', data)

        institutions = []
        for inst in response.get('institutions', []):
            institution = ProviderInstitution(
                institution_id=inst['institution_id'],
                name=inst.get('name', ''),
                logo_url=inst.get('logo'),
                country=inst.get('country_codes', [None])[0]
                    if inst.get('country_codes') else None,
            )
            institutions.append(institution)

        return institutions

    def revoke_access(
        self,
        access_token: str,
        connection_id: Optional[str] = None
    ) -> bool:
        """Revoke access and remove item."""
        try:
            self._request(
                '/item/remove',
                {'access_token': access_token}
            )
            return True
        except ProviderError:
            return False

    def get_balance(
        self,
        access_token: str,
        account_id: str
    ) -> Dict[str, Decimal]:
        """Get current balance for an account."""
        response = self._request(
            '/accounts/balance/get',
            {
                'access_token': access_token,
                'options': {
                    'account_ids': [account_id],
                },
            }
        )

        for acc in response.get('accounts', []):
            if acc['account_id'] == account_id:
                balances = acc.get('balances', {})
                return {
                    'balance': Decimal(str(balances.get('current', 0) or 0)),
                    'available_balance': Decimal(str(balances.get('available', 0)))
                        if balances.get('available') is not None else None,
                    'currency': balances.get('iso_currency_code', 'USD'),
                }

        raise ProviderError(f"Account not found: {account_id}")

    def get_item_status(self, access_token: str) -> dict:
        """Get the status of a Plaid item (connection)."""
        response = self._request(
            '/item/get',
            {'access_token': access_token}
        )

        item = response.get('item', {})
        status = response.get('status', {})

        return {
            'item_id': item.get('item_id'),
            'institution_id': item.get('institution_id'),
            'error': item.get('error'),
            'consent_expiration_time': item.get('consent_expiration_time'),
            'transactions_status': status.get('transactions', {}).get('last_successful_update'),
            'investments_status': status.get('investments', {}).get('last_successful_update'),
        }

    def create_update_link_token(
        self,
        access_token: str,
        user_id: str,
        redirect_uri: str
    ) -> str:
        """Create a Link token for updating credentials."""
        data = {
            'user': {
                'client_user_id': user_id,
            },
            'access_token': access_token,
            'redirect_uri': redirect_uri,
        }

        response = self._request('/link/token/create', data)
        return response['link_token']

    def normalize_account_type(self, provider_type: str) -> str:
        """Normalize Plaid account types."""
        type_mapping = {
            'depository': 'checking',
            'checking': 'checking',
            'savings': 'savings',
            'cd': 'savings',
            'money market': 'savings',
            'credit': 'credit',
            'credit card': 'credit',
            'loan': 'loan',
            'student': 'loan',
            'auto': 'loan',
            'mortgage': 'mortgage',
            'investment': 'investment',
            'brokerage': 'investment',
            '401k': 'investment',
            'ira': 'investment',
            'roth': 'investment',
            'other': 'other',
        }
        return type_mapping.get(provider_type.lower(), 'other')
