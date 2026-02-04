"""
Tests for the TrueLayer banking provider.

Covers TrueLayerProvider initialisation, OAuth URL generation, token exchange,
account/transaction fetching, institution search, and utility methods.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from apps.banking.providers.base import (
    ProviderError,
    TokenExpiredError,
    AuthorizationError,
    RateLimitError,
    ProviderUnavailableError,
)
from apps.banking.providers.truelayer import TrueLayerProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tl_settings(settings):
    settings.TRUELAYER_CLIENT_ID = "tl_client_id"
    settings.TRUELAYER_CLIENT_SECRET = "tl_client_secret"
    settings.TRUELAYER_SANDBOX = True
    return settings


@pytest.fixture
def provider(tl_settings):
    return TrueLayerProvider()


def _mock_response(json_data=None, status_code=200, text=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text if text is not None else str(json_data or {})
    return resp


# ---------------------------------------------------------------------------
# Initialisation / configuration
# ---------------------------------------------------------------------------


class TestTrueLayerInit:

    def test_init_success(self, tl_settings):
        p = TrueLayerProvider()
        assert p.client_id == "tl_client_id"
        assert p.client_secret == "tl_client_secret"
        assert p.use_sandbox is True

    def test_missing_client_id_raises(self, settings):
        settings.TRUELAYER_CLIENT_ID = None
        with pytest.raises(ProviderError, match="TRUELAYER_CLIENT_ID"):
            TrueLayerProvider()

    def test_provider_metadata(self, provider):
        assert provider.provider_name == "truelayer"
        assert provider.display_name == "TrueLayer"
        assert "GB" in provider.supported_countries


# ---------------------------------------------------------------------------
# URL properties
# ---------------------------------------------------------------------------


class TestTrueLayerUrls:

    def test_sandbox_auth_url(self, provider):
        assert provider.auth_url == TrueLayerProvider.SANDBOX_AUTH_URL

    def test_sandbox_api_url(self, provider):
        assert provider.api_url == TrueLayerProvider.SANDBOX_API_URL

    def test_production_auth_url(self, settings):
        settings.TRUELAYER_CLIENT_ID = "c"
        settings.TRUELAYER_SANDBOX = False
        p = TrueLayerProvider()
        assert p.auth_url == TrueLayerProvider.AUTH_URL

    def test_production_api_url(self, settings):
        settings.TRUELAYER_CLIENT_ID = "c"
        settings.TRUELAYER_SANDBOX = False
        p = TrueLayerProvider()
        assert p.api_url == TrueLayerProvider.API_URL


# ---------------------------------------------------------------------------
# _get_headers
# ---------------------------------------------------------------------------


class TestTrueLayerGetHeaders:

    def test_without_token(self, provider):
        headers = provider._get_headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"

    def test_with_token(self, provider):
        headers = provider._get_headers(access_token="tok_abc")
        assert headers["Authorization"] == "Bearer tok_abc"


# ---------------------------------------------------------------------------
# _request
# ---------------------------------------------------------------------------


class TestTrueLayerRequest:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_successful_get(self, mock_req, provider):
        mock_req.return_value = _mock_response({"results": []})
        result = provider._request("GET", "/data/v1/accounts", "token")
        assert result == {"results": []}

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_uses_custom_base_url(self, mock_req, provider):
        mock_req.return_value = _mock_response({})
        provider._request("POST", "/connect/token", base_url="https://custom.com")
        url = mock_req.call_args.args[1]
        assert url.startswith("https://custom.com")

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_401_raises_token_expired(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=401, text="Unauthorized")
        with pytest.raises(TokenExpiredError):
            provider._request("GET", "/data/v1/accounts", "bad_token")

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_403_raises_authorization_error(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=403, text="Forbidden")
        with pytest.raises(AuthorizationError):
            provider._request("GET", "/data/v1/accounts", "token")

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_429_raises_rate_limit(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=429, text="Too Many")
        with pytest.raises(RateLimitError):
            provider._request("GET", "/endpoint")

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_500_raises_unavailable(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=500, text="Internal")
        with pytest.raises(ProviderUnavailableError):
            provider._request("GET", "/endpoint")

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_empty_response_body(self, mock_req, provider):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = ""
        mock_req.return_value = resp
        result = provider._request("DELETE", "/endpoint")
        assert result == {}

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_timeout(self, mock_req, provider):
        mock_req.side_effect = requests.exceptions.Timeout()
        with pytest.raises(ProviderError, match="timeout"):
            provider._request("GET", "/endpoint")

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_connection_error(self, mock_req, provider):
        mock_req.side_effect = requests.exceptions.ConnectionError("conn refused")
        with pytest.raises(ProviderError, match="Request failed"):
            provider._request("GET", "/endpoint")


# ---------------------------------------------------------------------------
# get_authorization_url
# ---------------------------------------------------------------------------


class TestTrueLayerGetAuthorizationUrl:

    def test_generates_valid_url(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="csrf_state_123",
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert "truelayer" in parsed.hostname
        assert params["response_type"] == ["code"]
        assert params["client_id"] == ["tl_client_id"]
        assert params["redirect_uri"] == ["https://app.com/cb"]
        assert params["state"] == ["csrf_state_123"]
        assert "offline_access" in params["scope"][0]

    def test_includes_institution(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="s",
            institution_id="ob-hsbc",
        )
        params = parse_qs(urlparse(url).query)
        assert params["providers"] == ["ob-hsbc"]

    def test_without_institution(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="s",
        )
        params = parse_qs(urlparse(url).query)
        assert "providers" not in params

    def test_enable_mock(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="s",
            enable_mock=True,
        )
        params = parse_qs(urlparse(url).query)
        assert params["enable_mock"] == ["true"]

    def test_custom_scopes(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="s",
            scopes=["info", "accounts"],
        )
        params = parse_qs(urlparse(url).query)
        assert params["scope"] == ["info accounts"]


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestTrueLayerExchangeCode:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_exchange_success(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "access_token": "tl_access_xxx",
            "refresh_token": "tl_refresh_xxx",
            "expires_in": 3600,
        })
        result = provider.exchange_code("auth_code", "https://app.com/cb")
        assert result.access_token == "tl_access_xxx"
        assert result.refresh_token == "tl_refresh_xxx"
        assert result.token_expires_at is not None
        assert result.consent_expires_at is not None

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_exchange_default_expires_in(self, mock_req, provider):
        """When expires_in not in response, defaults to 3600."""
        mock_req.return_value = _mock_response({
            "access_token": "tok",
        })
        result = provider.exchange_code("code", "https://app.com/cb")
        assert result.token_expires_at is not None


# ---------------------------------------------------------------------------
# refresh_access_token
# ---------------------------------------------------------------------------


class TestTrueLayerRefreshAccessToken:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_refresh_success(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 7200,
        })
        result = provider.refresh_access_token("old_refresh")
        assert result.access_token == "new_access"
        assert result.refresh_token == "new_refresh"

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_refresh_keeps_old_refresh_token_if_not_returned(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "access_token": "new_access",
        })
        result = provider.refresh_access_token("old_refresh")
        assert result.refresh_token == "old_refresh"


# ---------------------------------------------------------------------------
# get_accounts
# ---------------------------------------------------------------------------


class TestTrueLayerGetAccounts:

    @patch.object(TrueLayerProvider, "_get_account_balance")
    @patch("apps.banking.providers.truelayer.requests.request")
    def test_returns_accounts(self, mock_req, mock_balance, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "account_id": "acc_tl_1",
                    "display_name": "Current Account",
                    "description": "GBP Current",
                    "account_type": "transaction",
                    "currency": "GBP",
                    "account_number": {
                        "number": "12345678",
                        "iban": "GB29NWBK60161331926819",
                    },
                },
            ]
        })
        mock_balance.return_value = {
            "current": Decimal("3000.00"),
            "available": Decimal("2900.00"),
        }

        accounts = provider.get_accounts("token")
        assert len(accounts) == 1
        assert accounts[0].provider_account_id == "acc_tl_1"
        assert accounts[0].name == "Current Account"
        assert accounts[0].account_type == "checking"
        assert accounts[0].balance == Decimal("3000.00")
        assert accounts[0].available_balance == Decimal("2900.00")
        assert accounts[0].account_number_masked == "****5678"
        assert accounts[0].iban_masked == "GB29****6819"

    @patch.object(TrueLayerProvider, "_get_account_balance")
    @patch("apps.banking.providers.truelayer.requests.request")
    def test_empty_accounts(self, mock_req, mock_balance, provider):
        mock_req.return_value = _mock_response({"results": []})
        assert provider.get_accounts("token") == []


# ---------------------------------------------------------------------------
# _get_account_balance
# ---------------------------------------------------------------------------


class TestTrueLayerGetAccountBalance:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_returns_balance(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "current": 1500.50,
                    "available": 1400.00,
                },
            ]
        })
        result = provider._get_account_balance("token", "acc_1")
        assert result["current"] == Decimal("1500.50")
        assert result["available"] == Decimal("1400.00")

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_null_available(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "current": 500,
                    "available": None,
                },
            ]
        })
        result = provider._get_account_balance("token", "acc_1")
        assert result["available"] is None

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_empty_results(self, mock_req, provider):
        mock_req.return_value = _mock_response({"results": []})
        result = provider._get_account_balance("token", "acc_1")
        assert result == {"current": Decimal("0")}

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_error_returns_zero(self, mock_req, provider):
        """ProviderError should be caught and return zero balance."""
        mock_req.return_value = _mock_response({}, status_code=500, text="Error")
        result = provider._get_account_balance("token", "acc_1")
        assert result == {"current": Decimal("0")}


# ---------------------------------------------------------------------------
# get_transactions
# ---------------------------------------------------------------------------


class TestTrueLayerGetTransactions:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_returns_transactions(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "transaction_id": "tx_tl_1",
                    "amount": -42.50,
                    "currency": "GBP",
                    "timestamp": "2025-01-15T14:30:00Z",
                    "description": "Grocery Store",
                    "merchant_name": "Tesco",
                    "transaction_classification": ["Shopping"],
                    "transaction_type": "DEBIT",
                    "reference": "REF001",
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert len(txs) == 1
        assert txs[0].provider_transaction_id == "tx_tl_1"
        assert txs[0].amount == Decimal("42.50")
        assert txs[0].transaction_type == "debit"
        assert txs[0].merchant_name == "Tesco"
        assert txs[0].category == "Shopping"

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_pending_transaction(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "transaction_id": "tx_p",
                    "amount": 10,
                    "timestamp": "2025-01-15T00:00:00Z",
                    "description": "Pending",
                    "transaction_type": "PENDING",
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert txs[0].pending is True

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_missing_timestamp_uses_today(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "transaction_id": "tx_no_ts",
                    "amount": 5,
                    "description": "No timestamp",
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert txs[0].transaction_date == date.today()

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_date_params_passed(self, mock_req, provider):
        mock_req.return_value = _mock_response({"results": []})
        from_d = date(2025, 1, 1)
        to_d = date(2025, 1, 31)
        provider.get_transactions("token", "acc_1", from_date=from_d, to_date=to_d)
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["params"]["from"] == "2025-01-01"
        assert call_kwargs["params"]["to"] == "2025-01-31"

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_no_classification(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "transaction_id": "tx_nc",
                    "amount": 10,
                    "timestamp": "2025-01-15T00:00:00Z",
                    "description": "No cat",
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert txs[0].category is None


# ---------------------------------------------------------------------------
# get_institutions
# ---------------------------------------------------------------------------


class TestTrueLayerGetInstitutions:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_returns_institutions(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "provider_id": "ob-hsbc",
                    "display_name": "HSBC",
                    "logo_url": "https://logo.com/hsbc.png",
                    "country": "GB",
                },
                {
                    "provider_id": "ob-bnp",
                    "display_name": "BNP Paribas",
                    "logo_url": "https://logo.com/bnp.png",
                    "country": "FR",
                },
            ]
        })
        result = provider.get_institutions()
        assert len(result) == 2

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_filter_by_country(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {"provider_id": "p1", "display_name": "UK Bank", "country": "GB"},
                {"provider_id": "p2", "display_name": "FR Bank", "country": "FR"},
            ]
        })
        result = provider.get_institutions(country="GB")
        assert len(result) == 1
        assert result[0].name == "UK Bank"

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_filter_by_search(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {"provider_id": "p1", "display_name": "HSBC"},
                {"provider_id": "p2", "display_name": "Barclays"},
            ]
        })
        result = provider.get_institutions(search="hsbc")
        assert len(result) == 1
        assert result[0].name == "HSBC"

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_filter_combined(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {"provider_id": "p1", "display_name": "HSBC UK", "country": "GB"},
                {"provider_id": "p2", "display_name": "HSBC FR", "country": "FR"},
                {"provider_id": "p3", "display_name": "Barclays", "country": "GB"},
            ]
        })
        result = provider.get_institutions(country="GB", search="hsbc")
        assert len(result) == 1
        assert result[0].name == "HSBC UK"


# ---------------------------------------------------------------------------
# revoke_access
# ---------------------------------------------------------------------------


class TestTrueLayerRevokeAccess:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_revoke_success(self, mock_req, provider):
        mock_req.return_value = _mock_response({})
        assert provider.revoke_access("token") is True

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_revoke_failure(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=500, text="Error")
        assert provider.revoke_access("bad_token") is False


# ---------------------------------------------------------------------------
# get_identity
# ---------------------------------------------------------------------------


class TestTrueLayerGetIdentity:

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_returns_identity(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "results": [
                {
                    "full_name": "John Doe",
                    "emails": ["john@example.com"],
                    "phones": ["+44123456789"],
                    "addresses": [{"city": "London"}],
                },
            ]
        })
        result = provider.get_identity("token")
        assert result["full_name"] == "John Doe"
        assert result["emails"] == ["john@example.com"]

    @patch("apps.banking.providers.truelayer.requests.request")
    def test_empty_results(self, mock_req, provider):
        mock_req.return_value = _mock_response({"results": []})
        assert provider.get_identity("token") == {}


# ---------------------------------------------------------------------------
# Masking utilities
# ---------------------------------------------------------------------------


class TestTrueLayerMasking:

    def test_mask_account_number_normal(self, provider):
        assert provider._mask_account_number("12345678") == "****5678"

    def test_mask_account_number_short(self, provider):
        assert provider._mask_account_number("1234") == "1234"

    def test_mask_account_number_none(self, provider):
        assert provider._mask_account_number(None) is None

    def test_mask_iban_normal(self, provider):
        assert provider._mask_iban("GB29NWBK60161331926819") == "GB29****6819"

    def test_mask_iban_short(self, provider):
        assert provider._mask_iban("GB29NWBK") == "GB29NWBK"

    def test_mask_iban_none(self, provider):
        assert provider._mask_iban(None) is None


# ---------------------------------------------------------------------------
# normalize_account_type (TrueLayer-specific override)
# ---------------------------------------------------------------------------


class TestTrueLayerNormalizeAccountType:

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            ("transaction", "checking"),
            ("savings", "savings"),
            ("business_transaction", "checking"),
            ("business_savings", "savings"),
            ("isa", "savings"),
            ("credit_card", "credit"),
            ("loan", "loan"),
            ("mortgage", "mortgage"),
            ("pension", "investment"),
            ("investment", "investment"),
            ("random", "other"),
        ],
    )
    def test_normalize(self, input_type, expected, provider):
        assert provider.normalize_account_type(input_type) == expected
