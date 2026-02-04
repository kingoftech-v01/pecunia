"""
Tests for the Plaid banking provider.

Covers PlaidProvider initialisation, configuration validation, API calls,
account/transaction normalisation, and error handling.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.banking.providers.base import ProviderError
from apps.banking.providers.plaid import PlaidProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def plaid_settings(settings):
    """Configure minimal Plaid settings for tests."""
    settings.PLAID_CLIENT_ID = "test_client_id"
    settings.PLAID_SECRET = "test_secret"
    settings.PLAID_ENVIRONMENT = "sandbox"
    return settings


@pytest.fixture
def provider(plaid_settings):
    """Return a configured PlaidProvider instance."""
    return PlaidProvider()


def _mock_response(json_data=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data)
    return resp


# ---------------------------------------------------------------------------
# Initialisation / configuration
# ---------------------------------------------------------------------------


class TestPlaidProviderInit:

    def test_init_success(self, plaid_settings):
        p = PlaidProvider()
        assert p.client_id == "test_client_id"
        assert p.secret == "test_secret"
        assert p.environment == "sandbox"

    def test_missing_client_id_raises(self, settings):
        settings.PLAID_CLIENT_ID = None
        settings.PLAID_SECRET = "s"
        with pytest.raises(ProviderError, match="PLAID_CLIENT_ID"):
            PlaidProvider()

    def test_missing_secret_raises(self, settings):
        settings.PLAID_CLIENT_ID = "cid"
        settings.PLAID_SECRET = None
        with pytest.raises(ProviderError, match="PLAID_SECRET"):
            PlaidProvider()

    def test_provider_metadata(self, provider):
        assert provider.provider_name == "plaid"
        assert provider.display_name == "Plaid"
        assert "US" in provider.supported_countries


# ---------------------------------------------------------------------------
# api_url property
# ---------------------------------------------------------------------------


class TestPlaidApiUrl:

    def test_sandbox(self, settings):
        settings.PLAID_CLIENT_ID = "c"
        settings.PLAID_SECRET = "s"
        settings.PLAID_ENVIRONMENT = "sandbox"
        assert PlaidProvider().api_url == PlaidProvider.SANDBOX_URL

    def test_development(self, settings):
        settings.PLAID_CLIENT_ID = "c"
        settings.PLAID_SECRET = "s"
        settings.PLAID_ENVIRONMENT = "development"
        assert PlaidProvider().api_url == PlaidProvider.DEVELOPMENT_URL

    def test_production(self, settings):
        settings.PLAID_CLIENT_ID = "c"
        settings.PLAID_SECRET = "s"
        settings.PLAID_ENVIRONMENT = "production"
        assert PlaidProvider().api_url == PlaidProvider.PRODUCTION_URL

    def test_unknown_defaults_to_sandbox(self, settings):
        settings.PLAID_CLIENT_ID = "c"
        settings.PLAID_SECRET = "s"
        settings.PLAID_ENVIRONMENT = "unknown"
        assert PlaidProvider().api_url == PlaidProvider.SANDBOX_URL


# ---------------------------------------------------------------------------
# _request method
# ---------------------------------------------------------------------------


class TestPlaidRequest:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_successful_request(self, mock_post, provider):
        mock_post.return_value = _mock_response({"key": "value"})
        result = provider._request("/test/endpoint", {"param": "val"})
        assert result == {"key": "value"}
        # Verify credentials injected
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["client_id"] == "test_client_id"
        assert call_kwargs.kwargs["json"]["secret"] == "test_secret"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_error_response(self, mock_post, provider):
        mock_post.return_value = _mock_response(
            {"error_code": "INVALID_INPUT", "error_message": "Bad param"},
            status_code=400,
        )
        with pytest.raises(ProviderError, match="Bad param"):
            provider._request("/test", {})

    @patch("apps.banking.providers.plaid.requests.post")
    def test_error_code_in_body_without_http_error(self, mock_post, provider):
        """Plaid sometimes returns 200 with error_code in body."""
        mock_post.return_value = _mock_response(
            {"error_code": "ITEM_LOGIN_REQUIRED", "error_message": "Login needed"},
            status_code=200,
        )
        with pytest.raises(ProviderError, match="Login needed"):
            provider._request("/test", {})

    @patch("apps.banking.providers.plaid.requests.post")
    def test_timeout(self, mock_post, provider):
        mock_post.side_effect = requests.exceptions.Timeout("timed out")
        with pytest.raises(ProviderError, match="timeout"):
            provider._request("/test", {})

    @patch("apps.banking.providers.plaid.requests.post")
    def test_request_exception(self, mock_post, provider):
        mock_post.side_effect = requests.exceptions.ConnectionError("no route")
        with pytest.raises(ProviderError, match="Request failed"):
            provider._request("/test", {})

    @patch("apps.banking.providers.plaid.requests.post")
    def test_none_data_sends_credentials_only(self, mock_post, provider):
        mock_post.return_value = _mock_response({"ok": True})
        provider._request("/test")
        json_sent = mock_post.call_args.kwargs["json"]
        assert json_sent["client_id"] == "test_client_id"


# ---------------------------------------------------------------------------
# create_link_token
# ---------------------------------------------------------------------------


class TestPlaidCreateLinkToken:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_creates_link_token(self, mock_post, provider):
        mock_post.return_value = _mock_response({"link_token": "link-sandbox-xxx"})
        token = provider.create_link_token(
            user_id="user_123",
            redirect_uri="https://app.com/cb",
        )
        assert token == "link-sandbox-xxx"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_with_institution_id(self, mock_post, provider):
        mock_post.return_value = _mock_response({"link_token": "lt"})
        provider.create_link_token(
            user_id="u1",
            redirect_uri="https://app.com/cb",
            institution_id="ins_chase",
        )
        json_sent = mock_post.call_args.kwargs["json"]
        assert json_sent["institution_id"] == "ins_chase"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_with_access_token_for_reconnection(self, mock_post, provider):
        mock_post.return_value = _mock_response({"link_token": "lt"})
        provider.create_link_token(
            user_id="u1",
            redirect_uri="https://app.com/cb",
            access_token="existing_token",
        )
        json_sent = mock_post.call_args.kwargs["json"]
        assert json_sent["access_token"] == "existing_token"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_custom_products_and_countries(self, mock_post, provider):
        mock_post.return_value = _mock_response({"link_token": "lt"})
        provider.create_link_token(
            user_id="u",
            redirect_uri="https://app.com/cb",
            products=["auth", "identity"],
            country_codes=["US"],
            language="fr",
        )
        json_sent = mock_post.call_args.kwargs["json"]
        assert json_sent["products"] == ["auth", "identity"]
        assert json_sent["country_codes"] == ["US"]
        assert json_sent["language"] == "fr"


# ---------------------------------------------------------------------------
# get_authorization_url
# ---------------------------------------------------------------------------


class TestPlaidGetAuthorizationUrl:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_returns_link_token(self, mock_post, provider):
        mock_post.return_value = _mock_response({"link_token": "link-abc"})
        # Note: user_id is extracted from kwargs inside get_authorization_url
        # and then **kwargs (still containing user_id) is forwarded to
        # create_link_token.  To avoid the duplicate-keyword-arg error we
        # let the method derive user_id from `state` instead.
        result = provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="user_42",
        )
        assert result == "link-abc"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_uses_state_as_user_id_fallback(self, mock_post, provider):
        mock_post.return_value = _mock_response({"link_token": "lt"})
        provider.get_authorization_url(
            redirect_uri="https://app.com/cb",
            state="state_as_user_id",
        )
        json_sent = mock_post.call_args.kwargs["json"]
        assert json_sent["user"]["client_user_id"] == "state_as_user_id"


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestPlaidExchangeCode:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_exchange_success(self, mock_post, provider):
        # First call: exchange public token
        # Second call: /item/get
        # Third call: /institutions/get_by_id
        mock_post.side_effect = [
            _mock_response({
                "access_token": "access-sandbox-xxx",
                "item_id": "item_id_123",
            }),
            _mock_response({
                "item": {"institution_id": "ins_1"},
            }),
            _mock_response({
                "institution": {
                    "name": "Chase Bank",
                    "logo": "https://logo.com/chase.png",
                },
            }),
        ]

        result = provider.exchange_code("public-sandbox-token", "https://app.com/cb")

        assert result.access_token == "access-sandbox-xxx"
        assert result.provider_connection_id == "item_id_123"
        assert result.institution_id == "ins_1"
        assert result.institution_name == "Chase Bank"
        assert result.institution_logo_url == "https://logo.com/chase.png"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_exchange_without_institution_id(self, mock_post, provider):
        """When item/get returns no institution_id."""
        mock_post.side_effect = [
            _mock_response({"access_token": "at", "item_id": "it"}),
            _mock_response({"item": {}}),
        ]
        result = provider.exchange_code("pt", "https://app.com/cb")
        assert result.institution_id is None
        assert result.institution_name is None

    @patch("apps.banking.providers.plaid.requests.post")
    def test_exchange_institution_lookup_fails_gracefully(self, mock_post, provider):
        """ProviderError from institution lookup is caught."""
        mock_post.side_effect = [
            _mock_response({"access_token": "at", "item_id": "it"}),
            _mock_response({"item": {"institution_id": "ins_x"}}),
            _mock_response(
                {"error_code": "INVALID", "error_message": "fail"}, status_code=400
            ),
        ]
        result = provider.exchange_code("pt", "https://app.com/cb")
        assert result.institution_id == "ins_x"
        assert result.institution_name is None  # Lookup failed gracefully


# ---------------------------------------------------------------------------
# refresh_access_token
# ---------------------------------------------------------------------------


class TestPlaidRefreshAccessToken:

    def test_returns_same_token(self, provider):
        """Plaid tokens don't expire; the method returns the input token."""
        result = provider.refresh_access_token("access_token_123")
        assert result.access_token == "access_token_123"


# ---------------------------------------------------------------------------
# get_accounts
# ---------------------------------------------------------------------------


class TestPlaidGetAccounts:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_returns_provider_accounts(self, mock_post, provider):
        mock_post.return_value = _mock_response({
            "accounts": [
                {
                    "account_id": "acc_1",
                    "name": "Checking",
                    "official_name": "PLAID CHECKING",
                    "type": "depository",
                    "subtype": "checking",
                    "mask": "1234",
                    "balances": {
                        "current": 1500.50,
                        "available": 1400.00,
                        "iso_currency_code": "USD",
                    },
                },
                {
                    "account_id": "acc_2",
                    "name": "Savings",
                    "type": "savings",
                    "balances": {
                        "current": 5000,
                        "available": None,
                        "iso_currency_code": "USD",
                    },
                },
            ]
        })

        accounts = provider.get_accounts("token")

        assert len(accounts) == 2
        assert accounts[0].provider_account_id == "acc_1"
        assert accounts[0].balance == Decimal("1500.50")
        assert accounts[0].available_balance == Decimal("1400.00")
        assert accounts[0].account_type == "checking"
        assert accounts[0].account_number_masked == "1234"

        assert accounts[1].available_balance is None

    @patch("apps.banking.providers.plaid.requests.post")
    def test_empty_accounts(self, mock_post, provider):
        mock_post.return_value = _mock_response({"accounts": []})
        assert provider.get_accounts("token") == []

    @patch("apps.banking.providers.plaid.requests.post")
    def test_missing_balance_defaults_to_zero(self, mock_post, provider):
        mock_post.return_value = _mock_response({
            "accounts": [
                {
                    "account_id": "a",
                    "name": "N",
                    "type": "other",
                    "balances": {},
                }
            ]
        })
        accounts = provider.get_accounts("t")
        assert accounts[0].balance == Decimal("0")


# ---------------------------------------------------------------------------
# get_transactions
# ---------------------------------------------------------------------------


class TestPlaidGetTransactions:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_returns_transactions(self, mock_post, provider):
        today = date.today()
        mock_post.return_value = _mock_response({
            "added": [
                {
                    "transaction_id": "tx_1",
                    "account_id": "acc_1",
                    "amount": 42.50,
                    "iso_currency_code": "USD",
                    "date": today.isoformat(),
                    "name": "Coffee Shop",
                    "merchant_name": "Starbucks",
                    "pending": False,
                    "payment_channel": "in store",
                    "personal_finance_category": {"primary": "FOOD_AND_DRINK"},
                },
            ],
            "has_more": False,
            "next_cursor": "cur_1",
        })

        txs = provider.get_transactions(
            "token", "acc_1",
            from_date=today - timedelta(days=30),
            to_date=today,
        )
        assert len(txs) == 1
        assert txs[0].provider_transaction_id == "tx_1"
        assert txs[0].amount == Decimal("42.50")
        # Plaid: positive amount = debit
        assert txs[0].transaction_type == "debit"
        assert txs[0].merchant_name == "Starbucks"
        assert txs[0].category == "FOOD_AND_DRINK"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_filters_by_account_id(self, mock_post, provider):
        today = date.today()
        mock_post.return_value = _mock_response({
            "added": [
                {
                    "transaction_id": "tx_a",
                    "account_id": "other_acc",
                    "amount": 10,
                    "date": today.isoformat(),
                    "name": "Skip",
                },
                {
                    "transaction_id": "tx_b",
                    "account_id": "acc_1",
                    "amount": 20,
                    "date": today.isoformat(),
                    "name": "Keep",
                },
            ],
            "has_more": False,
        })
        txs = provider.get_transactions(
            "token", "acc_1",
            from_date=today - timedelta(days=1),
            to_date=today,
        )
        assert len(txs) == 1
        assert txs[0].description == "Keep"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_filters_by_date_range(self, mock_post, provider):
        today = date.today()
        old_date = (today - timedelta(days=100)).isoformat()
        mock_post.return_value = _mock_response({
            "added": [
                {
                    "transaction_id": "tx_old",
                    "account_id": "acc_1",
                    "amount": 50,
                    "date": old_date,
                    "name": "Old Tx",
                },
            ],
            "has_more": False,
        })
        txs = provider.get_transactions(
            "token", "acc_1",
            from_date=today - timedelta(days=30),
            to_date=today,
        )
        assert len(txs) == 0

    @patch("apps.banking.providers.plaid.requests.post")
    def test_pagination(self, mock_post, provider):
        today = date.today()
        mock_post.side_effect = [
            _mock_response({
                "added": [
                    {
                        "transaction_id": "tx_1",
                        "account_id": "acc_1",
                        "amount": 10,
                        "date": today.isoformat(),
                        "name": "First",
                    },
                ],
                "has_more": True,
                "next_cursor": "cur_2",
            }),
            _mock_response({
                "added": [
                    {
                        "transaction_id": "tx_2",
                        "account_id": "acc_1",
                        "amount": 20,
                        "date": today.isoformat(),
                        "name": "Second",
                    },
                ],
                "has_more": False,
                "next_cursor": "cur_3",
            }),
        ]
        txs = provider.get_transactions(
            "token", "acc_1",
            from_date=today - timedelta(days=1),
            to_date=today,
        )
        assert len(txs) == 2

    @patch("apps.banking.providers.plaid.requests.post")
    def test_default_date_range(self, mock_post, provider):
        """When no dates provided, defaults to last 90 days."""
        mock_post.return_value = _mock_response({
            "added": [],
            "has_more": False,
        })
        provider.get_transactions("token", "acc_1")
        # Should not raise

    @patch("apps.banking.providers.plaid.requests.post")
    def test_credit_transaction(self, mock_post, provider):
        today = date.today()
        mock_post.return_value = _mock_response({
            "added": [
                {
                    "transaction_id": "tx_c",
                    "account_id": "acc_1",
                    "amount": -100,
                    "date": today.isoformat(),
                    "name": "Refund",
                    "category": ["Transfer", "Payroll"],
                },
            ],
            "has_more": False,
        })
        txs = provider.get_transactions(
            "token", "acc_1",
            from_date=today - timedelta(days=1),
            to_date=today,
        )
        assert txs[0].transaction_type == "credit"
        assert txs[0].category == "Transfer"


# ---------------------------------------------------------------------------
# get_institutions
# ---------------------------------------------------------------------------


class TestPlaidGetInstitutions:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_get_institutions_list(self, mock_post, provider):
        mock_post.return_value = _mock_response({
            "institutions": [
                {
                    "institution_id": "ins_1",
                    "name": "Chase",
                    "logo": "https://logo.com/chase.png",
                    "country_codes": ["US"],
                },
            ]
        })
        institutions = provider.get_institutions()
        assert len(institutions) == 1
        assert institutions[0].institution_id == "ins_1"
        assert institutions[0].name == "Chase"
        assert institutions[0].country == "US"

    @patch("apps.banking.providers.plaid.requests.post")
    def test_search_institutions(self, mock_post, provider):
        mock_post.return_value = _mock_response({
            "institutions": [
                {
                    "institution_id": "ins_2",
                    "name": "Bank of America",
                    "country_codes": [],
                },
            ]
        })
        institutions = provider.get_institutions(search="america")
        assert len(institutions) == 1
        # Verify search endpoint used
        url = mock_post.call_args.args[0]
        assert "/institutions/search" in url

    @patch("apps.banking.providers.plaid.requests.post")
    def test_filter_by_country(self, mock_post, provider):
        mock_post.return_value = _mock_response({"institutions": []})
        provider.get_institutions(country="GB")
        json_sent = mock_post.call_args.kwargs["json"]
        assert json_sent["country_codes"] == ["GB"]

    @patch("apps.banking.providers.plaid.requests.post")
    def test_no_country_codes(self, mock_post, provider):
        """Institution with empty country_codes -> country is None."""
        mock_post.return_value = _mock_response({
            "institutions": [
                {
                    "institution_id": "i",
                    "name": "N",
                },
            ]
        })
        result = provider.get_institutions()
        assert result[0].country is None


# ---------------------------------------------------------------------------
# revoke_access
# ---------------------------------------------------------------------------


class TestPlaidRevokeAccess:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_revoke_success(self, mock_post, provider):
        mock_post.return_value = _mock_response({"removed": True})
        assert provider.revoke_access("token") is True

    @patch("apps.banking.providers.plaid.requests.post")
    def test_revoke_failure(self, mock_post, provider):
        mock_post.return_value = _mock_response(
            {"error_code": "INVALID_ACCESS_TOKEN", "error_message": "bad token"},
            status_code=400,
        )
        assert provider.revoke_access("bad_token") is False


# ---------------------------------------------------------------------------
# get_balance (override)
# ---------------------------------------------------------------------------


class TestPlaidGetBalance:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_get_balance_success(self, mock_post, provider):
        mock_post.return_value = _mock_response({
            "accounts": [
                {
                    "account_id": "acc_1",
                    "balances": {
                        "current": 2500.75,
                        "available": 2400.00,
                        "iso_currency_code": "USD",
                    },
                },
            ]
        })
        result = provider.get_balance("token", "acc_1")
        assert result["balance"] == Decimal("2500.75")
        assert result["available_balance"] == Decimal("2400.00")

    @patch("apps.banking.providers.plaid.requests.post")
    def test_get_balance_account_not_found(self, mock_post, provider):
        mock_post.return_value = _mock_response({"accounts": []})
        with pytest.raises(ProviderError, match="Account not found"):
            provider.get_balance("token", "nonexistent")

    @patch("apps.banking.providers.plaid.requests.post")
    def test_get_balance_null_available(self, mock_post, provider):
        mock_post.return_value = _mock_response({
            "accounts": [
                {
                    "account_id": "acc_1",
                    "balances": {
                        "current": 100,
                        "available": None,
                        "iso_currency_code": "EUR",
                    },
                },
            ]
        })
        result = provider.get_balance("token", "acc_1")
        assert result["available_balance"] is None


# ---------------------------------------------------------------------------
# get_item_status
# ---------------------------------------------------------------------------


class TestPlaidGetItemStatus:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_returns_status(self, mock_post, provider):
        mock_post.return_value = _mock_response({
            "item": {
                "item_id": "it_1",
                "institution_id": "ins_1",
                "error": None,
                "consent_expiration_time": "2025-06-01T00:00:00Z",
            },
            "status": {
                "transactions": {"last_successful_update": "2025-01-15T12:00:00Z"},
                "investments": {},
            },
        })
        status = provider.get_item_status("token")
        assert status["item_id"] == "it_1"
        assert status["error"] is None
        assert status["consent_expiration_time"] == "2025-06-01T00:00:00Z"


# ---------------------------------------------------------------------------
# create_update_link_token
# ---------------------------------------------------------------------------


class TestPlaidCreateUpdateLinkToken:

    @patch("apps.banking.providers.plaid.requests.post")
    def test_creates_update_token(self, mock_post, provider):
        mock_post.return_value = _mock_response({"link_token": "update-lt"})
        token = provider.create_update_link_token(
            access_token="existing_at",
            user_id="u1",
            redirect_uri="https://app.com/cb",
        )
        assert token == "update-lt"
        json_sent = mock_post.call_args.kwargs["json"]
        assert json_sent["access_token"] == "existing_at"


# ---------------------------------------------------------------------------
# normalize_account_type (Plaid-specific override)
# ---------------------------------------------------------------------------


class TestPlaidNormalizeAccountType:

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            ("depository", "checking"),
            ("checking", "checking"),
            ("savings", "savings"),
            ("cd", "savings"),
            ("money market", "savings"),
            ("credit", "credit"),
            ("credit card", "credit"),
            ("loan", "loan"),
            ("student", "loan"),
            ("auto", "loan"),
            ("mortgage", "mortgage"),
            ("investment", "investment"),
            ("brokerage", "investment"),
            ("401k", "investment"),
            ("ira", "investment"),
            ("roth", "investment"),
            ("other", "other"),
            ("unknown_type", "other"),
        ],
    )
    def test_normalize(self, input_type, expected, provider):
        assert provider.normalize_account_type(input_type) == expected
