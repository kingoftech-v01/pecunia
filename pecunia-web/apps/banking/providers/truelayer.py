"""
TrueLayer Provider.

Banking provider for European banks via TrueLayer API.
https://docs.truelayer.com/
"""
import requests
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List
from urllib.parse import urlencode
from django.conf import settings
from django.utils import timezone

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


class TrueLayerProvider(BaseBankProvider):
    """
    TrueLayer provider implementation.

    European open banking provider with PSD2 compliance.
    Supports banks across UK and Europe.
    """

    provider_name = 'truelayer'
    display_name = 'TrueLayer'
    supported_countries = ['GB', 'IE', 'FR', 'DE', 'ES', 'IT', 'NL', 'FI', 'LT']

    # API endpoints
    AUTH_URL = 'https://auth.truelayer.com'
    API_URL = 'https://api.truelayer.com'
    SANDBOX_AUTH_URL = 'https://auth.truelayer-sandbox.com'
    SANDBOX_API_URL = 'https://api.truelayer-sandbox.com'

    def __init__(self):
        """Initialize TrueLayer provider."""
        self.client_id = getattr(settings, 'TRUELAYER_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'TRUELAYER_CLIENT_SECRET', None)
        self.use_sandbox = getattr(settings, 'TRUELAYER_SANDBOX', True)
        super().__init__()

    def _validate_configuration(self):
        """Validate TrueLayer configuration."""
        if not self.client_id:
            raise ProviderError(
                "TRUELAYER_CLIENT_ID not configured",
                code='configuration_error'
            )

    @property
    def auth_url(self) -> str:
        """Get auth URL based on environment."""
        return self.SANDBOX_AUTH_URL if self.use_sandbox else self.AUTH_URL

    @property
    def api_url(self) -> str:
        """Get API URL based on environment."""
        return self.SANDBOX_API_URL if self.use_sandbox else self.API_URL

    def _get_headers(self, access_token: Optional[str] = None) -> dict:
        """Get request headers."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        access_token: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ) -> dict:
        """Make API request with error handling."""
        url = f"{base_url or self.api_url}{endpoint}"
        headers = self._get_headers(access_token)

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=30,
                **kwargs
            )

            if response.status_code >= 400:
                self.handle_error(response)

            return response.json() if response.text else {}

        except requests.exceptions.Timeout:
            raise ProviderError("Request timeout", code='timeout')
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Request failed: {str(e)}", code='request_error')

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        institution_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate TrueLayer authorization URL.

        Uses OAuth 2.0 authorization code flow.
        """
        # Default scopes for full data access
        scopes = kwargs.get('scopes', [
            'info',
            'accounts',
            'balance',
            'transactions',
            'offline_access',
        ])

        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'state': state,
            'scope': ' '.join(scopes),
            'response_mode': 'form_post',
        }

        if institution_id:
            params['providers'] = institution_id

        # Optional: enable mock data for testing
        if kwargs.get('enable_mock'):
            params['enable_mock'] = 'true'

        return f"{self.auth_url}/?{urlencode(params)}"

    def exchange_code(
        self,
        code: str,
        redirect_uri: str
    ) -> AuthorizationResult:
        """Exchange authorization code for access tokens."""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
        }

        response = self._request(
            'POST',
            '/connect/token',
            base_url=self.auth_url,
            data=data
        )

        # TrueLayer access tokens typically expire in 1 hour
        expires_in = response.get('expires_in', 3600)
        token_expires_at = timezone.now() + timedelta(seconds=expires_in)

        # Consent typically valid for 90 days
        consent_expires_at = timezone.now() + timedelta(days=90)

        return AuthorizationResult(
            access_token=response['access_token'],
            refresh_token=response.get('refresh_token'),
            token_expires_at=token_expires_at,
            consent_expires_at=consent_expires_at,
        )

    def refresh_access_token(
        self,
        refresh_token: str
    ) -> AuthorizationResult:
        """Refresh an expired access token."""
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        response = self._request(
            'POST',
            '/connect/token',
            base_url=self.auth_url,
            data=data
        )

        expires_in = response.get('expires_in', 3600)
        token_expires_at = timezone.now() + timedelta(seconds=expires_in)

        return AuthorizationResult(
            access_token=response['access_token'],
            refresh_token=response.get('refresh_token', refresh_token),
            token_expires_at=token_expires_at,
        )

    def get_accounts(
        self,
        access_token: str,
        connection_id: Optional[str] = None
    ) -> List[ProviderAccount]:
        """Fetch accounts from TrueLayer."""
        response = self._request('GET', '/data/v1/accounts', access_token)

        accounts = []
        for acc in response.get('results', []):
            # Get balance for this account
            balance_data = self._get_account_balance(
                access_token,
                acc['account_id']
            )

            account = ProviderAccount(
                provider_account_id=acc['account_id'],
                name=acc.get('display_name', 'Unknown Account'),
                official_name=acc.get('description'),
                account_type=self.normalize_account_type(
                    acc.get('account_type', 'other')
                ),
                account_subtype=acc.get('account_type'),
                balance=balance_data.get('current', Decimal('0')),
                available_balance=balance_data.get('available'),
                currency=acc.get('currency', 'EUR'),
                account_number_masked=self._mask_account_number(
                    acc.get('account_number', {}).get('number')
                ),
                iban_masked=self._mask_iban(
                    acc.get('account_number', {}).get('iban')
                ),
            )
            accounts.append(account)

        return accounts

    def _get_account_balance(
        self,
        access_token: str,
        account_id: str
    ) -> dict:
        """Get balance for a specific account."""
        try:
            response = self._request(
                'GET',
                f'/data/v1/accounts/{account_id}/balance',
                access_token
            )
            results = response.get('results', [{}])
            if results:
                balance = results[0]
                return {
                    'current': Decimal(str(balance.get('current', 0))),
                    'available': Decimal(str(balance.get('available', 0)))
                        if balance.get('available') is not None else None,
                }
        except ProviderError:
            pass
        return {'current': Decimal('0')}

    def get_transactions(
        self,
        access_token: str,
        account_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[ProviderTransaction]:
        """Fetch transactions from TrueLayer."""
        endpoint = f'/data/v1/accounts/{account_id}/transactions'

        params = {}
        if from_date:
            params['from'] = from_date.isoformat()
        if to_date:
            params['to'] = to_date.isoformat()

        response = self._request(
            'GET',
            endpoint,
            access_token,
            params=params
        )

        transactions = []
        for tx in response.get('results', []):
            amount = Decimal(str(tx.get('amount', 0)))

            # Parse transaction date
            tx_date = tx.get('timestamp', '')[:10]
            if tx_date:
                tx_date = date.fromisoformat(tx_date)
            else:
                tx_date = date.today()

            transaction = ProviderTransaction(
                provider_transaction_id=tx['transaction_id'],
                account_id=account_id,
                amount=abs(amount),
                currency=tx.get('currency', 'EUR'),
                transaction_date=tx_date,
                description=tx.get('description', ''),
                transaction_type=self.normalize_transaction_type(amount),
                merchant_name=tx.get('merchant_name'),
                category=tx.get('transaction_classification', [None])[0]
                    if tx.get('transaction_classification') else None,
                pending=tx.get('transaction_type') == 'PENDING',
                reference=tx.get('reference'),
                metadata={
                    'transaction_type': tx.get('transaction_type'),
                    'transaction_category': tx.get('transaction_category'),
                    'provider_transaction_id': tx.get('provider_transaction_id'),
                }
            )
            transactions.append(transaction)

        return transactions

    def get_institutions(
        self,
        country: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[ProviderInstitution]:
        """Get list of supported institutions (providers)."""
        response = self._request(
            'GET',
            '/data/v1/providers',
            base_url=self.api_url
        )

        institutions = []
        for provider in response.get('results', []):
            # Filter by country if provided
            if country and provider.get('country') != country:
                continue

            # Filter by search if provided
            name = provider.get('display_name', '')
            if search and search.lower() not in name.lower():
                continue

            institution = ProviderInstitution(
                institution_id=provider['provider_id'],
                name=name,
                logo_url=provider.get('logo_url'),
                country=provider.get('country'),
            )
            institutions.append(institution)

        return institutions

    def revoke_access(
        self,
        access_token: str,
        connection_id: Optional[str] = None
    ) -> bool:
        """Revoke access token."""
        try:
            # TrueLayer uses token revocation endpoint
            data = {
                'token': access_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }
            self._request(
                'POST',
                '/connect/revoke',
                base_url=self.auth_url,
                data=data
            )
            return True
        except ProviderError:
            return False

    def get_identity(self, access_token: str) -> dict:
        """Get identity information for the connected account."""
        response = self._request('GET', '/data/v1/info', access_token)
        results = response.get('results', [{}])
        if results:
            info = results[0]
            return {
                'full_name': info.get('full_name'),
                'emails': info.get('emails', []),
                'phones': info.get('phones', []),
                'addresses': info.get('addresses', []),
            }
        return {}

    def _mask_account_number(self, number: Optional[str]) -> Optional[str]:
        """Mask account number for display."""
        if not number:
            return None
        if len(number) <= 4:
            return number
        return f"****{number[-4:]}"

    def _mask_iban(self, iban: Optional[str]) -> Optional[str]:
        """Mask IBAN for display."""
        if not iban:
            return None
        if len(iban) <= 8:
            return iban
        return f"{iban[:4]}****{iban[-4:]}"

    def normalize_account_type(self, provider_type: str) -> str:
        """Normalize TrueLayer account types."""
        type_mapping = {
            'transaction': 'checking',
            'savings': 'savings',
            'business_transaction': 'checking',
            'business_savings': 'savings',
            'isa': 'savings',
            'credit_card': 'credit',
            'loan': 'loan',
            'mortgage': 'mortgage',
            'pension': 'investment',
            'investment': 'investment',
        }
        return type_mapping.get(provider_type.lower(), 'other')
