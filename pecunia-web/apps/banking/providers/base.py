"""
Base Banking Provider.

Abstract base class for all banking provider implementations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from django.conf import settings


@dataclass
class ProviderAccount:
    """Standardized account data from provider."""
    provider_account_id: str
    name: str
    account_type: str
    balance: Decimal
    currency: str
    official_name: Optional[str] = None
    account_subtype: Optional[str] = None
    account_number_masked: Optional[str] = None
    iban_masked: Optional[str] = None
    available_balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None


@dataclass
class ProviderTransaction:
    """Standardized transaction data from provider."""
    provider_transaction_id: str
    account_id: str
    amount: Decimal
    currency: str
    transaction_date: date
    description: str
    transaction_type: str  # 'debit' or 'credit'
    merchant_name: Optional[str] = None
    category: Optional[str] = None
    pending: bool = False
    reference: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProviderInstitution:
    """Standardized institution data from provider."""
    institution_id: str
    name: str
    logo_url: Optional[str] = None
    country: Optional[str] = None
    bic: Optional[str] = None


@dataclass
class AuthorizationResult:
    """Result from authorization flow."""
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    consent_expires_at: Optional[datetime] = None
    provider_connection_id: Optional[str] = None
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    institution_logo_url: Optional[str] = None


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AuthorizationError(ProviderError):
    """Raised when authorization fails."""
    pass


class TokenExpiredError(ProviderError):
    """Raised when access token has expired."""
    pass


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""
    pass


class ProviderUnavailableError(ProviderError):
    """Raised when provider service is unavailable."""
    pass


class BaseBankProvider(ABC):
    """
    Abstract base class for banking providers.

    All provider implementations must inherit from this class
    and implement the abstract methods.
    """

    # Provider identification
    provider_name: str = None
    display_name: str = None
    supported_countries: List[str] = []

    def __init__(self):
        """Initialize provider with settings."""
        self._validate_configuration()

    def _validate_configuration(self):
        """Validate provider configuration is present."""
        # Subclasses should override to validate specific settings
        pass

    @abstractmethod
    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        institution_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate authorization URL for user consent.

        Args:
            redirect_uri: URL to redirect after authorization
            state: State parameter for security
            institution_id: Optional specific institution to connect

        Returns:
            Authorization URL string
        """
        pass

    @abstractmethod
    def exchange_code(
        self,
        code: str,
        redirect_uri: str
    ) -> AuthorizationResult:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from callback
            redirect_uri: Must match the redirect URI used in authorization

        Returns:
            AuthorizationResult with tokens and connection info
        """
        pass

    @abstractmethod
    def refresh_access_token(
        self,
        refresh_token: str
    ) -> AuthorizationResult:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token

        Returns:
            AuthorizationResult with new tokens
        """
        pass

    @abstractmethod
    def get_accounts(
        self,
        access_token: str,
        connection_id: Optional[str] = None
    ) -> List[ProviderAccount]:
        """
        Fetch accounts for a connection.

        Args:
            access_token: Valid access token
            connection_id: Provider-specific connection identifier

        Returns:
            List of ProviderAccount objects
        """
        pass

    @abstractmethod
    def get_transactions(
        self,
        access_token: str,
        account_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[ProviderTransaction]:
        """
        Fetch transactions for an account.

        Args:
            access_token: Valid access token
            account_id: Provider account identifier
            from_date: Start date for transactions
            to_date: End date for transactions

        Returns:
            List of ProviderTransaction objects
        """
        pass

    @abstractmethod
    def get_institutions(
        self,
        country: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[ProviderInstitution]:
        """
        Get list of supported institutions.

        Args:
            country: Filter by country code
            search: Search term for institution name

        Returns:
            List of ProviderInstitution objects
        """
        pass

    @abstractmethod
    def revoke_access(
        self,
        access_token: str,
        connection_id: Optional[str] = None
    ) -> bool:
        """
        Revoke access and delete connection.

        Args:
            access_token: Valid access token
            connection_id: Provider connection identifier

        Returns:
            True if successfully revoked
        """
        pass

    def get_balance(
        self,
        access_token: str,
        account_id: str
    ) -> Dict[str, Decimal]:
        """
        Get current balance for an account.

        Default implementation uses get_accounts.
        Providers can override for more efficient balance-only calls.

        Args:
            access_token: Valid access token
            account_id: Provider account identifier

        Returns:
            Dict with 'balance' and optionally 'available_balance'
        """
        accounts = self.get_accounts(access_token)
        for account in accounts:
            if account.provider_account_id == account_id:
                return {
                    'balance': account.balance,
                    'available_balance': account.available_balance,
                    'currency': account.currency,
                }
        raise ProviderError(f"Account not found: {account_id}")

    def normalize_account_type(self, provider_type: str) -> str:
        """
        Normalize provider-specific account type to standard type.

        Args:
            provider_type: Provider-specific account type

        Returns:
            Standardized account type
        """
        type_mapping = {
            # Common mappings
            'checking': 'checking',
            'current': 'checking',
            'compte courant': 'checking',
            'savings': 'savings',
            'livret': 'savings',
            'epargne': 'savings',
            'credit': 'credit',
            'credit card': 'credit',
            'carte': 'credit',
            'loan': 'loan',
            'pret': 'loan',
            'mortgage': 'mortgage',
            'hypotheque': 'mortgage',
            'investment': 'investment',
            'brokerage': 'investment',
            'titre': 'investment',
        }
        return type_mapping.get(provider_type.lower(), 'other')

    def normalize_transaction_type(self, amount: Decimal) -> str:
        """
        Determine transaction type from amount.

        Args:
            amount: Transaction amount (negative for debits)

        Returns:
            'debit' or 'credit'
        """
        return 'credit' if amount >= 0 else 'debit'

    def handle_error(self, response) -> None:
        """
        Handle error response from provider API.

        Args:
            response: HTTP response object

        Raises:
            Appropriate ProviderError subclass
        """
        status_code = response.status_code

        if status_code == 401:
            raise TokenExpiredError("Access token expired or invalid")
        elif status_code == 403:
            raise AuthorizationError("Access denied")
        elif status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif status_code >= 500:
            raise ProviderUnavailableError("Provider service unavailable")
        else:
            raise ProviderError(
                f"Provider error: {response.text}",
                code=str(status_code)
            )
