"""
Powens (Budget Insight) Provider.

Banking provider for French and European banks via Powens/Budget Insight API.
https://docs.powens.com/
"""
import requests
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List
from urllib.parse import urlencode
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


class BudgetInsightProvider(BaseBankProvider):
    """
    Powens (formerly Budget Insight) provider implementation.

    Primary provider for French banks with PSD2 compliance.
    Supports 350+ French and European banking institutions.
    """

    provider_name = 'budget_insight'
    display_name = 'Powens (Budget Insight)'
    supported_countries = ['FR', 'ES', 'DE', 'IT', 'BE', 'NL', 'PT']

    # API endpoints
    BASE_URL = 'https://api.budget-insight.com'
    SANDBOX_URL = 'https://api.sandbox.budget-insight.com'

    def __init__(self):
        """Initialize Budget Insight provider."""
        super().__init__()
        self.client_id = getattr(settings, 'BUDGET_INSIGHT_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'BUDGET_INSIGHT_CLIENT_SECRET', None)
        self.domain = getattr(settings, 'BUDGET_INSIGHT_DOMAIN', None)
        self.use_sandbox = getattr(settings, 'BUDGET_INSIGHT_SANDBOX', True)

    def _validate_configuration(self):
        """Validate Budget Insight configuration."""
        if not self.client_id:
            raise ProviderError(
                "BUDGET_INSIGHT_CLIENT_ID not configured",
                code='configuration_error'
            )

    @property
    def api_url(self) -> str:
        """Get API URL based on environment."""
        if self.use_sandbox:
            return self.SANDBOX_URL
        if self.domain:
            return f"https://{self.domain}.biapi.pro/2.0"
        return self.BASE_URL

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
        **kwargs
    ) -> dict:
        """Make API request with error handling."""
        url = f"{self.api_url}{endpoint}"
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
        Generate Powens authorization URL.

        Uses the webview authorization flow for user consent.
        """
        # First, create a temporary token for the authorization
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'state': state,
        }

        if institution_id:
            params['connector_ids'] = institution_id

        # Optional parameters
        if 'connector_capabilities' in kwargs:
            params['connector_capabilities'] = kwargs['connector_capabilities']

        base_auth_url = f"{self.api_url}/auth/webview/connect"
        return f"{base_auth_url}?{urlencode(params)}"

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
            '/auth/token',
            data=data
        )

        # Calculate expiration
        expires_in = response.get('expires_in', 3600)
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return AuthorizationResult(
            access_token=response['access_token'],
            refresh_token=response.get('refresh_token'),
            token_expires_at=token_expires_at,
            provider_connection_id=response.get('id_user'),
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
            '/auth/token',
            data=data
        )

        expires_in = response.get('expires_in', 3600)
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

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
        """Fetch accounts from Powens."""
        endpoint = '/users/me/accounts'
        if connection_id:
            endpoint = f'/users/me/connections/{connection_id}/accounts'

        response = self._request('GET', endpoint, access_token)

        accounts = []
        for acc in response.get('accounts', []):
            account = ProviderAccount(
                provider_account_id=str(acc['id']),
                name=acc.get('name', 'Unknown Account'),
                official_name=acc.get('original_name'),
                account_type=self.normalize_account_type(
                    acc.get('type', 'other')
                ),
                account_subtype=acc.get('type'),
                balance=Decimal(str(acc.get('balance', 0))),
                available_balance=Decimal(str(acc['coming']))
                    if acc.get('coming') is not None else None,
                currency=acc.get('currency', {}).get('id', 'EUR'),
                account_number_masked=acc.get('number'),
                iban_masked=self._mask_iban(acc.get('iban')),
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
        """Fetch transactions from Powens."""
        endpoint = f'/users/me/accounts/{account_id}/transactions'

        params = {}
        if from_date:
            params['min_date'] = from_date.isoformat()
        if to_date:
            params['max_date'] = to_date.isoformat()

        response = self._request(
            'GET',
            endpoint,
            access_token,
            params=params
        )

        transactions = []
        for tx in response.get('transactions', []):
            amount = Decimal(str(tx.get('value', 0)))
            transaction = ProviderTransaction(
                provider_transaction_id=str(tx['id']),
                account_id=account_id,
                amount=abs(amount),
                currency=tx.get('currency', {}).get('id', 'EUR'),
                transaction_date=date.fromisoformat(tx['date']),
                description=tx.get('original_wording', tx.get('wording', '')),
                transaction_type=self.normalize_transaction_type(amount),
                merchant_name=tx.get('wording'),
                category=tx.get('id_category'),
                pending=tx.get('coming', False),
                reference=tx.get('original_value'),
                metadata={
                    'type': tx.get('type'),
                    'stemmed_wording': tx.get('stemmed_wording'),
                }
            )
            transactions.append(transaction)

        return transactions

    def get_institutions(
        self,
        country: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[ProviderInstitution]:
        """Get list of supported institutions (connectors)."""
        endpoint = '/connectors'
        params = {'expand': 'fields'}

        if country:
            # Powens uses different country filtering
            params['country'] = country

        response = self._request('GET', endpoint, params=params)

        institutions = []
        for connector in response.get('connectors', []):
            # Filter by search if provided
            name = connector.get('name', '')
            if search and search.lower() not in name.lower():
                continue

            institution = ProviderInstitution(
                institution_id=str(connector['id']),
                name=name,
                logo_url=connector.get('urls', {}).get('logo'),
                country=connector.get('country'),
                bic=connector.get('bic'),
            )
            institutions.append(institution)

        return institutions

    def revoke_access(
        self,
        access_token: str,
        connection_id: Optional[str] = None
    ) -> bool:
        """Revoke access and delete user connection."""
        try:
            if connection_id:
                # Delete specific connection
                self._request(
                    'DELETE',
                    f'/users/me/connections/{connection_id}',
                    access_token
                )
            else:
                # Delete all user data
                self._request('DELETE', '/users/me', access_token)
            return True
        except ProviderError:
            return False

    def get_connection_status(
        self,
        access_token: str,
        connection_id: str
    ) -> dict:
        """Get the sync status of a connection."""
        response = self._request(
            'GET',
            f'/users/me/connections/{connection_id}',
            access_token
        )

        return {
            'status': response.get('state'),
            'last_update': response.get('last_update'),
            'error': response.get('error'),
            'error_message': response.get('error_message'),
        }

    def trigger_sync(
        self,
        access_token: str,
        connection_id: str
    ) -> dict:
        """Trigger a manual sync for a connection."""
        response = self._request(
            'POST',
            f'/users/me/connections/{connection_id}/sync',
            access_token
        )
        return response

    def _mask_iban(self, iban: Optional[str]) -> Optional[str]:
        """Mask IBAN for display."""
        if not iban:
            return None
        if len(iban) <= 8:
            return iban
        return f"{iban[:4]}****{iban[-4:]}"

    def normalize_account_type(self, provider_type: str) -> str:
        """Normalize Powens account types."""
        type_mapping = {
            'checking': 'checking',
            'savings': 'savings',
            'deposit': 'savings',
            'loan': 'loan',
            'market': 'investment',
            'joint': 'checking',
            'card': 'credit',
            'life_insurance': 'investment',
            'pea': 'investment',
            'capitalisation': 'investment',
            'perp': 'investment',
            'madelin': 'investment',
            'rsp': 'savings',
            'pee': 'investment',
            'perco': 'investment',
            'article83': 'investment',
            'real_estate': 'investment',
            'unknown': 'other',
        }
        return type_mapping.get(provider_type.lower(), 'other')
