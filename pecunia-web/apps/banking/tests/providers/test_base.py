"""
Tests for the base banking provider.

Covers dataclasses, exception hierarchy, BaseBankProvider concrete methods,
and the provider registry in __init__.py.
"""
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from apps.banking.providers.base import (
    AuthorizationError,
    AuthorizationResult,
    BaseBankProvider,
    ProviderAccount,
    ProviderError,
    ProviderInstitution,
    ProviderTransaction,
    ProviderUnavailableError,
    RateLimitError,
    TokenExpiredError,
)
from apps.banking.providers import get_provider, get_available_providers, PROVIDERS


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class TestProviderError:

    def test_message(self):
        err = ProviderError("something broke")
        assert str(err) == "something broke"
        assert err.message == "something broke"

    def test_code_and_details(self):
        err = ProviderError("msg", code="ERR_01", details={"key": "val"})
        assert err.code == "ERR_01"
        assert err.details == {"key": "val"}

    def test_defaults(self):
        err = ProviderError("x")
        assert err.code is None
        assert err.details == {}


class TestAuthorizationError:

    def test_inherits_provider_error(self):
        err = AuthorizationError("denied", code="auth_err")
        assert isinstance(err, ProviderError)
        assert err.code == "auth_err"


class TestTokenExpiredError:

    def test_inherits_provider_error(self):
        err = TokenExpiredError("expired")
        assert isinstance(err, ProviderError)


class TestRateLimitError:

    def test_inherits_provider_error(self):
        err = RateLimitError("slow down")
        assert isinstance(err, ProviderError)


class TestProviderUnavailableError:

    def test_inherits_provider_error(self):
        err = ProviderUnavailableError("down")
        assert isinstance(err, ProviderError)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestProviderAccount:

    def test_required_fields(self):
        acc = ProviderAccount(
            provider_account_id="acc1",
            name="Checking",
            account_type="checking",
            balance=Decimal("100.50"),
            currency="USD",
        )
        assert acc.provider_account_id == "acc1"
        assert acc.balance == Decimal("100.50")

    def test_optional_fields_default(self):
        acc = ProviderAccount(
            provider_account_id="a",
            name="n",
            account_type="other",
            balance=Decimal("0"),
            currency="EUR",
        )
        assert acc.official_name is None
        assert acc.account_subtype is None
        assert acc.account_number_masked is None
        assert acc.iban_masked is None
        assert acc.available_balance is None
        assert acc.credit_limit is None


class TestProviderTransaction:

    def test_fields(self):
        tx = ProviderTransaction(
            provider_transaction_id="tx1",
            account_id="acc1",
            amount=Decimal("42.00"),
            currency="EUR",
            transaction_date=date(2025, 1, 15),
            description="Coffee shop",
            transaction_type="debit",
        )
        assert tx.pending is False
        assert tx.metadata is None

    def test_optional_fields(self):
        tx = ProviderTransaction(
            provider_transaction_id="tx2",
            account_id="acc1",
            amount=Decimal("10.00"),
            currency="USD",
            transaction_date=date.today(),
            description="Transfer",
            transaction_type="credit",
            merchant_name="Shop",
            category="food",
            pending=True,
            reference="REF123",
            metadata={"source": "auto"},
        )
        assert tx.merchant_name == "Shop"
        assert tx.metadata == {"source": "auto"}


class TestProviderInstitution:

    def test_fields(self):
        inst = ProviderInstitution(
            institution_id="ins_1",
            name="Bank X",
            logo_url="https://logo.com/x.png",
            country="DE",
            bic="DEUTDEFF",
        )
        assert inst.bic == "DEUTDEFF"

    def test_optional_defaults(self):
        inst = ProviderInstitution(institution_id="i", name="n")
        assert inst.logo_url is None
        assert inst.country is None
        assert inst.bic is None


class TestAuthorizationResult:

    def test_fields(self):
        result = AuthorizationResult(
            access_token="tok",
            refresh_token="ref",
            token_expires_at=datetime(2025, 6, 1),
            consent_expires_at=datetime(2025, 9, 1),
            provider_connection_id="conn_1",
            institution_id="ins_1",
            institution_name="Bank",
            institution_logo_url="https://logo.com",
        )
        assert result.access_token == "tok"
        assert result.institution_name == "Bank"

    def test_defaults(self):
        result = AuthorizationResult(access_token="t")
        assert result.refresh_token is None
        assert result.token_expires_at is None
        assert result.consent_expires_at is None
        assert result.provider_connection_id is None
        assert result.institution_id is None
        assert result.institution_name is None
        assert result.institution_logo_url is None


# ---------------------------------------------------------------------------
# BaseBankProvider concrete methods
# ---------------------------------------------------------------------------


class ConcreteProvider(BaseBankProvider):
    """Minimal concrete implementation for testing base class methods."""

    provider_name = "test"
    display_name = "Test Provider"
    supported_countries = ["US"]

    def get_authorization_url(self, redirect_uri, state, institution_id=None, **kw):
        return "https://auth.test.com"

    def exchange_code(self, code, redirect_uri):
        return AuthorizationResult(access_token="tok")

    def refresh_access_token(self, refresh_token):
        return AuthorizationResult(access_token="new_tok")

    def get_accounts(self, access_token, connection_id=None):
        return [
            ProviderAccount(
                provider_account_id="a1",
                name="Acc 1",
                account_type="checking",
                balance=Decimal("500"),
                currency="USD",
                available_balance=Decimal("490"),
            ),
            ProviderAccount(
                provider_account_id="a2",
                name="Acc 2",
                account_type="savings",
                balance=Decimal("1000"),
                currency="USD",
            ),
        ]

    def get_transactions(self, access_token, account_id, from_date=None, to_date=None):
        return []

    def get_institutions(self, country=None, search=None):
        return []

    def revoke_access(self, access_token, connection_id=None):
        return True


class TestBaseBankProviderGetBalance:

    def test_returns_balance_for_matching_account(self):
        provider = ConcreteProvider()
        result = provider.get_balance("token", "a1")
        assert result["balance"] == Decimal("500")
        assert result["available_balance"] == Decimal("490")
        assert result["currency"] == "USD"

    def test_raises_for_missing_account(self):
        provider = ConcreteProvider()
        with pytest.raises(ProviderError, match="Account not found"):
            provider.get_balance("token", "nonexistent")


class TestBaseBankProviderNormalizeAccountType:

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            ("checking", "checking"),
            ("current", "checking"),
            ("CURRENT", "checking"),
            ("Compte Courant", "checking"),
            ("savings", "savings"),
            ("livret", "savings"),
            ("epargne", "savings"),
            ("credit", "credit"),
            ("Credit Card", "credit"),
            ("carte", "credit"),
            ("loan", "loan"),
            ("pret", "loan"),
            ("mortgage", "mortgage"),
            ("hypotheque", "mortgage"),
            ("investment", "investment"),
            ("brokerage", "investment"),
            ("titre", "investment"),
            ("random_type", "other"),
        ],
    )
    def test_normalize(self, input_type, expected):
        provider = ConcreteProvider()
        assert provider.normalize_account_type(input_type) == expected


class TestBaseBankProviderNormalizeTransactionType:

    def test_positive_is_credit(self):
        provider = ConcreteProvider()
        assert provider.normalize_transaction_type(Decimal("10")) == "credit"

    def test_zero_is_credit(self):
        provider = ConcreteProvider()
        assert provider.normalize_transaction_type(Decimal("0")) == "credit"

    def test_negative_is_debit(self):
        provider = ConcreteProvider()
        assert provider.normalize_transaction_type(Decimal("-5")) == "debit"


class TestBaseBankProviderHandleError:

    def _make_response(self, status_code, text="error body"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        return resp

    def test_401_raises_token_expired(self):
        provider = ConcreteProvider()
        with pytest.raises(TokenExpiredError):
            provider.handle_error(self._make_response(401))

    def test_403_raises_authorization_error(self):
        provider = ConcreteProvider()
        with pytest.raises(AuthorizationError):
            provider.handle_error(self._make_response(403))

    def test_429_raises_rate_limit(self):
        provider = ConcreteProvider()
        with pytest.raises(RateLimitError):
            provider.handle_error(self._make_response(429))

    def test_500_raises_unavailable(self):
        provider = ConcreteProvider()
        with pytest.raises(ProviderUnavailableError):
            provider.handle_error(self._make_response(500))

    def test_502_raises_unavailable(self):
        provider = ConcreteProvider()
        with pytest.raises(ProviderUnavailableError):
            provider.handle_error(self._make_response(502))

    def test_other_raises_provider_error(self):
        provider = ConcreteProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.handle_error(self._make_response(422, "Unprocessable"))
        assert exc_info.value.code == "422"
        assert "Unprocessable" in str(exc_info.value)


class TestBaseBankProviderValidateConfiguration:

    def test_default_validate_passes(self):
        """The default _validate_configuration is a no-op."""
        provider = ConcreteProvider()
        # Should not raise
        provider._validate_configuration()


# ---------------------------------------------------------------------------
# Provider registry (__init__.py)
# ---------------------------------------------------------------------------


class TestProviderRegistry:

    @patch("apps.banking.providers.PlaidProvider.__init__", return_value=None)
    def test_get_provider_plaid(self, mock_init, settings):
        settings.PLAID_CLIENT_ID = "test"
        settings.PLAID_SECRET = "test"
        provider = get_provider("plaid")
        assert provider is not None

    def test_get_provider_unknown_raises(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            get_provider("nonexistent")

    def test_get_available_providers(self):
        providers = get_available_providers()
        assert "plaid" in providers
        assert "truelayer" in providers
        assert "budget_insight" in providers

    def test_providers_dict(self):
        assert len(PROVIDERS) == 3
