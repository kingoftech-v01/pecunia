"""
Tests for the Powens (Budget Insight) banking provider.

Covers BudgetInsightProvider initialisation, OAuth URL generation, token exchange,
account/transaction fetching, institution search, connection management,
and utility methods.
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
    ProviderUnavailableError,
)
from apps.banking.providers.budget_insight import BudgetInsightProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def bi_settings(settings):
    settings.BUDGET_INSIGHT_CLIENT_ID = "bi_client_id"
    settings.BUDGET_INSIGHT_CLIENT_SECRET = "bi_client_secret"
    settings.BUDGET_INSIGHT_DOMAIN = "mydomain"
    settings.BUDGET_INSIGHT_SANDBOX = True
    return settings


@pytest.fixture
def provider(bi_settings):
    return BudgetInsightProvider()


def _mock_response(json_data=None, status_code=200, text=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text if text is not None else str(json_data or {})
    return resp


# ---------------------------------------------------------------------------
# Initialisation / configuration
# ---------------------------------------------------------------------------


class TestBudgetInsightInit:

    def test_init_success(self, bi_settings):
        p = BudgetInsightProvider()
        assert p.client_id == "bi_client_id"
        assert p.client_secret == "bi_client_secret"
        assert p.domain == "mydomain"
        assert p.use_sandbox is True

    def test_missing_client_id_raises(self, settings):
        settings.BUDGET_INSIGHT_CLIENT_ID = None
        with pytest.raises(ProviderError, match="BUDGET_INSIGHT_CLIENT_ID"):
            BudgetInsightProvider()

    def test_provider_metadata(self, provider):
        assert provider.provider_name == "budget_insight"
        assert provider.display_name == "Powens (Budget Insight)"
        assert "FR" in provider.supported_countries


# ---------------------------------------------------------------------------
# api_url property
# ---------------------------------------------------------------------------


class TestBudgetInsightApiUrl:

    def test_sandbox_url(self, provider):
        assert provider.api_url == BudgetInsightProvider.SANDBOX_URL

    def test_production_with_domain(self, settings):
        settings.BUDGET_INSIGHT_CLIENT_ID = "c"
        settings.BUDGET_INSIGHT_SANDBOX = False
        settings.BUDGET_INSIGHT_DOMAIN = "mybank"
        p = BudgetInsightProvider()
        assert p.api_url == "https://mybank.biapi.pro/2.0"

    def test_production_without_domain(self, settings):
        settings.BUDGET_INSIGHT_CLIENT_ID = "c"
        settings.BUDGET_INSIGHT_SANDBOX = False
        settings.BUDGET_INSIGHT_DOMAIN = None
        p = BudgetInsightProvider()
        assert p.api_url == BudgetInsightProvider.BASE_URL


# ---------------------------------------------------------------------------
# _get_headers
# ---------------------------------------------------------------------------


class TestBudgetInsightGetHeaders:

    def test_without_token(self, provider):
        headers = provider._get_headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"

    def test_with_token(self, provider):
        headers = provider._get_headers(access_token="tok_bi")
        assert headers["Authorization"] == "Bearer tok_bi"


# ---------------------------------------------------------------------------
# _request
# ---------------------------------------------------------------------------


class TestBudgetInsightRequest:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_successful_request(self, mock_req, provider):
        mock_req.return_value = _mock_response({"accounts": []})
        result = provider._request("GET", "/users/me/accounts", "token")
        assert result == {"accounts": []}

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_401_raises_token_expired(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=401, text="Unauthorized")
        with pytest.raises(TokenExpiredError):
            provider._request("GET", "/users/me/accounts", "bad_token")

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_403_raises_authorization_error(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=403, text="Forbidden")
        with pytest.raises(AuthorizationError):
            provider._request("GET", "/endpoint")

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_500_raises_unavailable(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=500, text="Internal")
        with pytest.raises(ProviderUnavailableError):
            provider._request("GET", "/endpoint")

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_empty_response_body(self, mock_req, provider):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = ""
        mock_req.return_value = resp
        result = provider._request("DELETE", "/endpoint")
        assert result == {}

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_timeout(self, mock_req, provider):
        mock_req.side_effect = requests.exceptions.Timeout()
        with pytest.raises(ProviderError, match="timeout"):
            provider._request("GET", "/endpoint")

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_connection_error(self, mock_req, provider):
        mock_req.side_effect = requests.exceptions.ConnectionError("refused")
        with pytest.raises(ProviderError, match="Request failed"):
            provider._request("GET", "/endpoint")


# ---------------------------------------------------------------------------
# get_authorization_url
# ---------------------------------------------------------------------------


class TestBudgetInsightGetAuthorizationUrl:

    def test_generates_valid_url(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="csrf_state",
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert "/auth/webview/connect" in parsed.path
        assert params["response_type"] == ["code"]
        assert params["client_id"] == ["bi_client_id"]
        assert params["redirect_uri"] == ["https://app.com/cb"]
        assert params["state"] == ["csrf_state"]

    def test_with_institution_id(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="s",
            institution_id="40",
        )
        params = parse_qs(urlparse(url).query)
        assert params["connector_ids"] == ["40"]

    def test_without_institution_id(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="s",
        )
        params = parse_qs(urlparse(url).query)
        assert "connector_ids" not in params

    def test_connector_capabilities_kwarg(self, provider):
        url = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="s",
            connector_capabilities="bank",
        )
        params = parse_qs(urlparse(url).query)
        assert params["connector_capabilities"] == ["bank"]


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestBudgetInsightExchangeCode:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_exchange_success(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "access_token": "bi_access_xxx",
            "refresh_token": "bi_refresh_xxx",
            "expires_in": 3600,
            "id_user": "user_bi_123",
        })
        result = provider.exchange_code("auth_code", "https://app.com/cb")
        assert result.access_token == "bi_access_xxx"
        assert result.refresh_token == "bi_refresh_xxx"
        assert result.token_expires_at is not None
        assert result.provider_connection_id == "user_bi_123"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_exchange_default_expires_in(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "access_token": "tok",
        })
        result = provider.exchange_code("code", "https://app.com/cb")
        assert result.token_expires_at is not None


# ---------------------------------------------------------------------------
# refresh_access_token
# ---------------------------------------------------------------------------


class TestBudgetInsightRefreshAccessToken:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_refresh_success(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "access_token": "new_bi_access",
            "refresh_token": "new_bi_refresh",
            "expires_in": 1800,
        })
        result = provider.refresh_access_token("old_refresh")
        assert result.access_token == "new_bi_access"
        assert result.refresh_token == "new_bi_refresh"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_refresh_keeps_old_refresh_if_not_returned(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "access_token": "new_access",
        })
        result = provider.refresh_access_token("keep_me")
        assert result.refresh_token == "keep_me"


# ---------------------------------------------------------------------------
# get_accounts
# ---------------------------------------------------------------------------


class TestBudgetInsightGetAccounts:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_returns_accounts(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "accounts": [
                {
                    "id": 12345,
                    "name": "Compte Courant",
                    "original_name": "COMPTE COURANT EUR",
                    "type": "checking",
                    "balance": 2500.75,
                    "coming": 100.00,
                    "currency": {"id": "EUR"},
                    "number": "12345678",
                    "iban": "FR7630006000011234567890189",
                },
            ]
        })
        accounts = provider.get_accounts("token")
        assert len(accounts) == 1
        assert accounts[0].provider_account_id == "12345"
        assert accounts[0].name == "Compte Courant"
        assert accounts[0].official_name == "COMPTE COURANT EUR"
        assert accounts[0].account_type == "checking"
        assert accounts[0].balance == Decimal("2500.75")
        assert accounts[0].available_balance == Decimal("100.00")
        assert accounts[0].currency == "EUR"
        assert accounts[0].account_number_masked == "****5678"
        assert accounts[0].iban_masked == "FR76****0189"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_with_connection_id(self, mock_req, provider):
        mock_req.return_value = _mock_response({"accounts": []})
        provider.get_accounts("token", connection_id="conn_42")
        url = mock_req.call_args.args[1]
        assert "/connections/conn_42/accounts" in url

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_without_connection_id(self, mock_req, provider):
        mock_req.return_value = _mock_response({"accounts": []})
        provider.get_accounts("token")
        url = mock_req.call_args.args[1]
        assert "/users/me/accounts" in url

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_null_coming_field(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "accounts": [
                {
                    "id": 1,
                    "name": "Acc",
                    "type": "savings",
                    "balance": 500,
                    "coming": None,
                    "currency": {"id": "EUR"},
                },
            ]
        })
        accounts = provider.get_accounts("token")
        assert accounts[0].available_balance is None

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_empty_accounts(self, mock_req, provider):
        mock_req.return_value = _mock_response({"accounts": []})
        assert provider.get_accounts("token") == []


# ---------------------------------------------------------------------------
# get_transactions
# ---------------------------------------------------------------------------


class TestBudgetInsightGetTransactions:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_returns_transactions(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "transactions": [
                {
                    "id": 99001,
                    "date": "2025-01-15",
                    "value": -42.50,
                    "original_wording": "CARTE CARREFOUR",
                    "wording": "Carrefour",
                    "currency": {"id": "EUR"},
                    "id_category": 10,
                    "coming": False,
                    "type": "card",
                    "stemmed_wording": "carrefour",
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert len(txs) == 1
        assert txs[0].provider_transaction_id == "99001"
        assert txs[0].amount == Decimal("42.50")
        assert txs[0].transaction_type == "debit"
        assert txs[0].description == "CARTE CARREFOUR"
        assert txs[0].merchant_name == "Carrefour"
        assert txs[0].category == 10

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_credit_transaction(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "transactions": [
                {
                    "id": 99002,
                    "date": "2025-01-20",
                    "value": 3000.00,
                    "wording": "Salary",
                    "currency": {"id": "EUR"},
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert txs[0].transaction_type == "credit"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_date_params(self, mock_req, provider):
        mock_req.return_value = _mock_response({"transactions": []})
        provider.get_transactions(
            "token", "acc_1",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["params"]["min_date"] == "2025-01-01"
        assert call_kwargs["params"]["max_date"] == "2025-01-31"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_no_date_params(self, mock_req, provider):
        mock_req.return_value = _mock_response({"transactions": []})
        provider.get_transactions("token", "acc_1")
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs.get("params", {}) == {}

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_uses_original_wording_over_wording(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "transactions": [
                {
                    "id": 1,
                    "date": "2025-01-15",
                    "value": -10,
                    "original_wording": "ORIGINAL",
                    "wording": "Simplified",
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert txs[0].description == "ORIGINAL"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_falls_back_to_wording(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "transactions": [
                {
                    "id": 2,
                    "date": "2025-01-15",
                    "value": -5,
                    "wording": "Fallback",
                },
            ]
        })
        txs = provider.get_transactions("token", "acc_1")
        assert txs[0].description == "Fallback"


# ---------------------------------------------------------------------------
# get_institutions
# ---------------------------------------------------------------------------


class TestBudgetInsightGetInstitutions:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_returns_institutions(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "connectors": [
                {
                    "id": 40,
                    "name": "BNP Paribas",
                    "urls": {"logo": "https://logo.com/bnp.png"},
                    "country": "FR",
                    "bic": "BNPAFRPP",
                },
                {
                    "id": 41,
                    "name": "Societe Generale",
                    "urls": {"logo": "https://logo.com/sg.png"},
                    "country": "FR",
                },
            ]
        })
        institutions = provider.get_institutions()
        assert len(institutions) == 2
        assert institutions[0].institution_id == "40"
        assert institutions[0].bic == "BNPAFRPP"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_filter_by_search(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "connectors": [
                {"id": 40, "name": "BNP Paribas"},
                {"id": 41, "name": "Societe Generale"},
            ]
        })
        result = provider.get_institutions(search="bnp")
        assert len(result) == 1
        assert result[0].name == "BNP Paribas"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_country_param_passed(self, mock_req, provider):
        mock_req.return_value = _mock_response({"connectors": []})
        provider.get_institutions(country="FR")
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["params"]["country"] == "FR"

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_empty_connectors(self, mock_req, provider):
        mock_req.return_value = _mock_response({"connectors": []})
        assert provider.get_institutions() == []


# ---------------------------------------------------------------------------
# revoke_access
# ---------------------------------------------------------------------------


class TestBudgetInsightRevokeAccess:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_revoke_with_connection_id(self, mock_req, provider):
        mock_req.return_value = _mock_response({})
        result = provider.revoke_access("token", connection_id="conn_1")
        assert result is True
        url = mock_req.call_args.args[1]
        assert "/connections/conn_1" in url

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_revoke_without_connection_id(self, mock_req, provider):
        mock_req.return_value = _mock_response({})
        result = provider.revoke_access("token")
        assert result is True
        url = mock_req.call_args.args[1]
        assert "/users/me" in url
        assert "connections" not in url

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_revoke_failure(self, mock_req, provider):
        mock_req.return_value = _mock_response({}, status_code=500, text="Error")
        assert provider.revoke_access("token", connection_id="c") is False


# ---------------------------------------------------------------------------
# get_connection_status
# ---------------------------------------------------------------------------


class TestBudgetInsightGetConnectionStatus:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_returns_status(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "state": "SyncDone",
            "last_update": "2025-01-15T10:00:00Z",
            "error": None,
            "error_message": None,
        })
        result = provider.get_connection_status("token", "conn_1")
        assert result["status"] == "SyncDone"
        assert result["error"] is None

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_error_state(self, mock_req, provider):
        mock_req.return_value = _mock_response({
            "state": "wrongpass",
            "last_update": "2025-01-10T10:00:00Z",
            "error": "wrongpass",
            "error_message": "Wrong credentials",
        })
        result = provider.get_connection_status("token", "conn_1")
        assert result["status"] == "wrongpass"
        assert result["error_message"] == "Wrong credentials"


# ---------------------------------------------------------------------------
# trigger_sync
# ---------------------------------------------------------------------------


class TestBudgetInsightTriggerSync:

    @patch("apps.banking.providers.budget_insight.requests.request")
    def test_trigger_sync(self, mock_req, provider):
        mock_req.return_value = _mock_response({"status": "ok"})
        result = provider.trigger_sync("token", "conn_1")
        assert result == {"status": "ok"}
        url = mock_req.call_args.args[1]
        assert "/connections/conn_1/sync" in url


# ---------------------------------------------------------------------------
# Masking utilities
# ---------------------------------------------------------------------------


class TestBudgetInsightMasking:

    def test_mask_account_number_normal(self, provider):
        assert provider._mask_account_number("12345678") == "****5678"

    def test_mask_account_number_short(self, provider):
        assert provider._mask_account_number("1234") == "1234"

    def test_mask_account_number_none(self, provider):
        assert provider._mask_account_number(None) is None

    def test_mask_iban_normal(self, provider):
        assert provider._mask_iban("FR7630006000011234567890189") == "FR76****0189"

    def test_mask_iban_short(self, provider):
        assert provider._mask_iban("FR761234") == "FR761234"

    def test_mask_iban_none(self, provider):
        assert provider._mask_iban(None) is None


# ---------------------------------------------------------------------------
# normalize_account_type (Powens-specific override)
# ---------------------------------------------------------------------------


class TestBudgetInsightNormalizeAccountType:

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            ("checking", "checking"),
            ("savings", "savings"),
            ("deposit", "savings"),
            ("loan", "loan"),
            ("market", "investment"),
            ("joint", "checking"),
            ("card", "credit"),
            ("life_insurance", "investment"),
            ("pea", "investment"),
            ("capitalisation", "investment"),
            ("perp", "investment"),
            ("madelin", "investment"),
            ("rsp", "savings"),
            ("pee", "investment"),
            ("perco", "investment"),
            ("article83", "investment"),
            ("real_estate", "investment"),
            ("unknown", "other"),
            ("random_type", "other"),
        ],
    )
    def test_normalize(self, input_type, expected, provider):
        assert provider.normalize_account_type(input_type) == expected
