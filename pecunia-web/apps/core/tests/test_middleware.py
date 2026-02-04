"""
Comprehensive tests for apps.core.middleware.

Covers:
- RequestSanitizationMiddleware
- RateLimitMiddleware
- SubscriptionCheckMiddleware
- AuditLogMiddleware
- SecurityHeadersMiddleware
"""
import hashlib
import json
import time
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.test import RequestFactory, override_settings

from apps.core.middleware import (
    RequestSanitizationMiddleware,
    RateLimitMiddleware,
    SubscriptionCheckMiddleware,
    AuditLogMiddleware,
    SecurityHeadersMiddleware,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_response_200(request):
    """Dummy get_response returning a 200 OK."""
    return HttpResponse("OK", status=200, content_type="text/html")


def _get_response_401(request):
    """Dummy get_response returning a 401 Unauthorized."""
    return HttpResponse("Unauthorized", status=401)


def _get_response_500(request):
    """Dummy get_response returning a 500 Server Error."""
    return HttpResponse("Server Error", status=500)


def _make_anon_user():
    """Create a mock anonymous user."""
    user = MagicMock()
    user.is_authenticated = False
    user.id = None
    return user


def _make_auth_user(user_id=1, tier="free", is_staff=False, is_superuser=False,
                    is_email_verified=True):
    """Create a mock authenticated user."""
    user = MagicMock()
    user.is_authenticated = True
    user.id = user_id
    user.subscription_tier = tier
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.is_email_verified = is_email_verified
    return user


@pytest.fixture
def rf():
    return RequestFactory()


# ============================================================================
# RequestSanitizationMiddleware
# ============================================================================

class TestRequestSanitizationMiddleware:
    """Tests for RequestSanitizationMiddleware."""

    def _make_middleware(self):
        return RequestSanitizationMiddleware(_get_response_200)

    # --- Safe requests pass through ---

    def test_safe_get_request_passes(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/transactions/", {"search": "coffee"})
        result = mw.process_request(request)
        assert result is None  # None means "continue processing"

    def test_safe_post_request_passes(self, rf):
        mw = self._make_middleware()
        body = json.dumps({"description": "Buy groceries", "amount": 42})
        request = rf.post(
            "/api/transactions/",
            data=body,
            content_type="application/json",
        )
        result = mw.process_request(request)
        assert result is None

    # --- SQL injection in query params ---

    def test_sql_injection_select_from_in_query_param(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/search/", {"q": "SELECT * FROM users"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_union_select_in_query_param(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "' UNION SELECT password FROM auth_user--"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_drop_table_in_query_param(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "DROP TABLE users"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_insert_into(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "INSERT INTO users VALUES(1)"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_update_set(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "UPDATE users SET admin=1"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_delete_from_where(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "DELETE FROM users WHERE id=1"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_or_1_equals_1(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "' OR 1=1"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_comment_suffix(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "admin';--"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_exec(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "EXEC('dangerous')"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_create_table(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"q": "CREATE TABLE foo (id int)"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    # --- XSS payloads ---

    def test_xss_script_tag_in_query(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"name": "<script>alert('xss')</script>"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_xss_javascript_protocol(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"url": "javascript:alert(1)"})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_xss_onerror_attribute(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"img": 'onerror="alert(1)"'})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_xss_iframe_in_query(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"name": '<iframe src="evil.com"></iframe>'})
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    # --- Path traversal ---

    def test_path_traversal_in_path(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/../../../etc/passwd")
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_path_traversal_encoded(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/%2e%2e%2f%2e%2e%2fetc/passwd")
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    # --- Body-based attacks ---

    def test_xss_in_post_body(self, rf):
        mw = self._make_middleware()
        body = json.dumps({"name": "<script>evil()</script>"})
        request = rf.post(
            "/api/items/",
            data=body,
            content_type="application/json",
        )
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_sql_injection_in_post_body(self, rf):
        mw = self._make_middleware()
        body = json.dumps({"query": "SELECT password FROM users"})
        request = rf.post(
            "/api/items/",
            data=body,
            content_type="application/json",
        )
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_binary_body_skipped(self, rf):
        """Non-UTF-8 body should not cause an error."""
        mw = self._make_middleware()
        request = rf.post(
            "/api/upload/",
            data=b"\x80\x81\x82\xff",
            content_type="application/octet-stream",
        )
        result = mw.process_request(request)
        assert result is None

    def test_get_method_body_not_checked(self, rf):
        """GET requests don't have body inspection."""
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        result = mw.process_request(request)
        assert result is None

    def test_patch_with_suspicious_body(self, rf):
        mw = self._make_middleware()
        body = json.dumps({"name": "<script>x</script>"})
        request = rf.patch(
            "/api/items/1/",
            data=body,
            content_type="application/json",
        )
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    def test_put_with_suspicious_body(self, rf):
        mw = self._make_middleware()
        body = json.dumps({"cmd": "UNION ALL SELECT 1"})
        request = rf.put(
            "/api/items/1/",
            data=body,
            content_type="application/json",
        )
        result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 400

    # --- _is_suspicious edge cases ---

    def test_empty_value_not_suspicious(self):
        mw = self._make_middleware()
        assert mw._is_suspicious("") is False

    def test_normal_text_not_suspicious(self):
        mw = self._make_middleware()
        assert mw._is_suspicious("Hello world") is False

    # --- _get_client_ip ---

    def test_get_client_ip_x_forwarded_for_single(self, rf):
        """Single IP in X-Forwarded-For with TRUSTED_PROXY_COUNT=1 -> index 0."""
        mw = self._make_middleware()
        request = rf.get("/api/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4"
        assert mw._get_client_ip(request) == "1.2.3.4"

    def test_get_client_ip_x_forwarded_for_multiple(self, rf):
        """Two IPs with TRUSTED_PROXY_COUNT=1 -> rightmost 1 is proxy, client is at index 1."""
        mw = self._make_middleware()
        request = rf.get("/api/test/")
        # With TRUSTED_PROXY_COUNT=1: index = max(2-1, 0) = 1
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4, 10.0.0.1"
        assert mw._get_client_ip(request) == "10.0.0.1"

    def test_get_client_ip_no_forwarded_falls_to_remote(self, rf):
        """Without X-Forwarded-For, falls directly to REMOTE_ADDR."""
        mw = self._make_middleware()
        request = rf.get("/api/test/", REMOTE_ADDR="9.9.9.9")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        ip = mw._get_client_ip(request)
        assert ip == "9.9.9.9"

    def test_get_client_ip_remote_addr(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/test/", REMOTE_ADDR="9.8.7.6")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        request.META.pop("HTTP_X_REAL_IP", None)
        assert mw._get_client_ip(request) == "9.8.7.6"

    def test_get_client_ip_fallback(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/test/")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        request.META.pop("HTTP_X_REAL_IP", None)
        request.META.pop("REMOTE_ADDR", None)
        assert mw._get_client_ip(request) == "0.0.0.0"

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_get_client_ip_trusted_proxy_count(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "1.1.1.1, 2.2.2.2, 3.3.3.3"
        # 3 IPs, 2 trusted proxies -> index = max(3 - 2, 0) = 1
        assert mw._get_client_ip(request) == "2.2.2.2"

    # --- _blocked_response ---

    def test_blocked_response_format(self):
        mw = self._make_middleware()
        resp = mw._blocked_response()
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert data["error"] == "bad_request"


# ============================================================================
# RateLimitMiddleware
# ============================================================================

class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def _make_middleware(self, **settings_override):
        with override_settings(**settings_override) if settings_override else _noop_ctx():
            mw = RateLimitMiddleware(_get_response_200)
        return mw

    # --- Excluded paths ---

    def test_health_path_excluded(self, rf):
        mw = self._make_middleware()
        request = rf.get("/health/")
        request.user = _make_anon_user()
        assert mw.process_request(request) is None

    def test_ready_path_excluded(self, rf):
        mw = self._make_middleware()
        request = rf.get("/ready/")
        request.user = _make_anon_user()
        assert mw.process_request(request) is None

    def test_static_path_excluded(self, rf):
        mw = self._make_middleware()
        request = rf.get("/static/main.css")
        request.user = _make_anon_user()
        assert mw.process_request(request) is None

    def test_favicon_excluded(self, rf):
        mw = self._make_middleware()
        request = rf.get("/favicon.ico")
        request.user = _make_anon_user()
        assert mw.process_request(request) is None

    # --- Whitelisted IPs ---

    @override_settings(RATE_LIMIT_WHITELIST_IPS=["10.0.0.1"])
    def test_whitelisted_ip_not_limited(self, rf):
        mw = RateLimitMiddleware(_get_response_200)
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        assert mw.process_request(request) is None

    # --- Allowed request sets headers ---

    def test_allowed_request_sets_remaining_attribute(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        request.META["REMOTE_ADDR"] = "1.2.3.4"
        with patch.object(mw, "_check_rate_limit", return_value=(True, 59, time.time() + 60)):
            result = mw.process_request(request)
        assert result is None
        assert hasattr(request, "_rate_limit_remaining")
        assert request._rate_limit_remaining == 59

    # --- Rate limited request ---

    def test_rate_limited_returns_429(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        request.META["REMOTE_ADDR"] = "1.2.3.4"
        with patch.object(mw, "_check_rate_limit", return_value=(False, 0, time.time() + 30)):
            result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 429
        data = json.loads(result.content)
        assert data["error"] == "rate_limit_exceeded"
        assert "Retry-After" in result

    # --- process_response adds headers ---

    def test_process_response_with_rate_limit_info(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request._rate_limit_remaining = 42
        request._rate_limit_reset = 1700000000.0
        response = HttpResponse("OK")
        response = mw.process_response(request, response)
        assert response["X-RateLimit-Remaining"] == "42"
        assert response["X-RateLimit-Reset"] == "1700000000"

    def test_process_response_without_rate_limit_info(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        response = mw.process_response(request, response)
        assert "X-RateLimit-Remaining" not in response

    # --- _get_client_key ---

    def test_client_key_authenticated(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_auth_user(user_id=99)
        assert mw._get_client_key(request) == "ratelimit:user:99"

    def test_client_key_anonymous(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        request.META["REMOTE_ADDR"] = "1.2.3.4"
        key = mw._get_client_key(request)
        assert key.startswith("ratelimit:ip:")

    # --- _get_limit_config ---

    def test_limit_config_sensitive_endpoint(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/auth/login/")
        request.user = _make_anon_user()
        config = mw._get_limit_config(request)
        assert config["requests"] == 5
        assert config["window"] == 60

    def test_limit_config_authenticated_free(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_auth_user(tier="free")
        config = mw._get_limit_config(request)
        assert config == mw.limits["free"]

    def test_limit_config_authenticated_premium(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_auth_user(tier="premium")
        config = mw._get_limit_config(request)
        assert config == mw.limits["premium"]

    def test_limit_config_anonymous(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        config = mw._get_limit_config(request)
        assert config == mw.limits["anonymous"]

    def test_limit_config_unknown_tier_fallback(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_auth_user(tier="nonexistent")
        config = mw._get_limit_config(request)
        # Falls back to 'free'
        assert config == mw.limits["free"]

    # --- _check_rate_limit with cache ---

    @patch("apps.core.middleware.cache")
    def test_check_rate_limit_allowed(self, mock_cache):
        mock_cache.get.return_value = 0
        mw = self._make_middleware()
        allowed, remaining, reset = mw._check_rate_limit(
            "test_key", {"requests": 60, "window": 60}
        )
        assert allowed is True
        assert remaining >= 0
        mock_cache.set.assert_called_once()

    @patch("apps.core.middleware.cache")
    def test_check_rate_limit_exceeded(self, mock_cache):
        # Return high counts to exceed limit
        mock_cache.get.return_value = 100
        mw = self._make_middleware()
        allowed, remaining, reset = mw._check_rate_limit(
            "test_key", {"requests": 5, "window": 60}
        )
        assert allowed is False
        assert remaining == 0

    # --- _hash_ip ---

    def test_hash_ip_returns_fixed_length(self):
        mw = self._make_middleware()
        h = mw._hash_ip("1.2.3.4")
        assert len(h) == 16

    def test_hash_ip_deterministic(self):
        mw = self._make_middleware()
        assert mw._hash_ip("1.2.3.4") == mw._hash_ip("1.2.3.4")

    # --- _is_excluded_path ---

    def test_is_excluded_path_true(self):
        mw = self._make_middleware()
        assert mw._is_excluded_path("/health/") is True

    def test_is_excluded_path_false(self):
        mw = self._make_middleware()
        assert mw._is_excluded_path("/api/items/") is False

    # --- _rate_limit_response ---

    def test_rate_limit_response_format(self):
        mw = self._make_middleware()
        resp = mw._rate_limit_response(time.time() + 30)
        assert resp.status_code == 429
        data = json.loads(resp.content)
        assert "retry_after" in data
        assert data["retry_after"] >= 1


# ============================================================================
# AuditLogMiddleware
# ============================================================================

class TestAuditLogMiddleware:
    """Tests for AuditLogMiddleware."""

    def _make_middleware(self, get_response=None):
        return AuditLogMiddleware(get_response or _get_response_200)

    # --- Excluded paths bypass logging ---

    def test_excluded_path_health(self, rf):
        mw = self._make_middleware()
        request = rf.get("/health/")
        request.user = _make_anon_user()
        response = mw(request)
        assert response.status_code == 200
        assert "X-Correlation-ID" not in response

    def test_excluded_path_static(self, rf):
        mw = self._make_middleware()
        request = rf.get("/static/main.js")
        request.user = _make_anon_user()
        response = mw(request)
        assert "X-Correlation-ID" not in response

    def test_excluded_path_api_docs(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/docs/")
        request.user = _make_anon_user()
        response = mw(request)
        assert "X-Correlation-ID" not in response

    # --- Correlation ID ---

    def test_adds_correlation_id_to_response(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        response = mw(request)
        assert "X-Correlation-ID" in response
        # Verify it's a valid UUID
        uuid.UUID(response["X-Correlation-ID"])

    def test_uses_existing_correlation_id(self, rf):
        mw = self._make_middleware()
        existing_id = "my-custom-correlation-id"
        request = rf.get("/api/items/", HTTP_X_CORRELATION_ID=existing_id)
        request.user = _make_anon_user()
        response = mw(request)
        assert response["X-Correlation-ID"] == existing_id

    # --- Request data capture ---

    def test_capture_get_request_data(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/", {"page": "2", "search": "test"})
        request.user = _make_anon_user()
        data = mw._capture_request_data(request)
        assert data["method"] == "GET"
        assert data["path"] == "/api/items/"
        assert "page" in data["query_params"]

    def test_capture_post_json_body(self, rf):
        mw = self._make_middleware()
        body = json.dumps({"name": "Test", "amount": 100})
        request = rf.post("/api/items/", data=body, content_type="application/json")
        request.user = _make_anon_user()
        data = mw._capture_request_data(request)
        assert "body" in data
        assert data["body"]["name"] == "Test"

    def test_capture_post_invalid_json(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/items/", data="not json", content_type="application/json")
        request.user = _make_anon_user()
        data = mw._capture_request_data(request)
        assert data["body"] == "[binary_data]"

    def test_capture_post_form_data(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/items/", data={"name": "Test"})
        request.user = _make_anon_user()
        data = mw._capture_request_data(request)
        # POST data with default content type is form data
        assert "body" in data

    def test_capture_delete_body(self, rf):
        mw = self._make_middleware()
        body = json.dumps({"reason": "test"})
        request = rf.delete("/api/items/1/", data=body, content_type="application/json")
        request.user = _make_anon_user()
        data = mw._capture_request_data(request)
        assert "body" in data

    # --- Sensitive field sanitization ---

    def test_sanitize_password_field(self):
        mw = self._make_middleware()
        result = mw._sanitize_dict({"password": "secret123", "username": "john"})
        assert result["password"] == "[REDACTED]"
        assert result["username"] == "john"

    def test_sanitize_token_fields(self):
        mw = self._make_middleware()
        result = mw._sanitize_dict({
            "access_token": "abc",
            "refresh_token": "def",
            "api_key": "xyz"
        })
        assert result["access_token"] == "[REDACTED]"
        assert result["refresh_token"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"

    def test_sanitize_financial_fields(self):
        mw = self._make_middleware()
        result = mw._sanitize_dict({
            "credit_card": "4111111111111111",
            "cvv": "123",
            "iban": "FR7630006000011234567890189",
            "account_number": "123456789",
        })
        for key in ["credit_card", "cvv", "iban", "account_number"]:
            assert result[key] == "[REDACTED]"

    def test_sanitize_nested_dict(self):
        mw = self._make_middleware()
        result = mw._sanitize_dict({
            "user": {"password": "secret", "name": "John"},
            "data": "visible",
        })
        assert result["user"]["password"] == "[REDACTED]"
        assert result["user"]["name"] == "John"
        assert result["data"] == "visible"

    def test_sanitize_list_of_dicts(self):
        mw = self._make_middleware()
        result = mw._sanitize_dict({
            "items": [{"token": "abc"}, {"name": "safe"}]
        })
        assert result["items"][0]["token"] == "[REDACTED]"
        assert result["items"][1]["name"] == "safe"

    def test_sanitize_non_dict_input(self):
        mw = self._make_middleware()
        assert mw._sanitize_dict("string") == "string"

    def test_sanitize_list_with_non_dict_items(self):
        mw = self._make_middleware()
        result = mw._sanitize_dict({"tags": ["one", "two", 3]})
        assert result["tags"] == ["one", "two", 3]

    def test_sanitize_case_insensitive(self):
        mw = self._make_middleware()
        result = mw._sanitize_dict({"Password": "secret", "API_KEY": "xyz"})
        assert result["Password"] == "[REDACTED]"
        assert result["API_KEY"] == "[REDACTED]"

    # --- _log_audit_entry ---

    @patch("apps.core.middleware.audit_logger")
    @patch("apps.core.middleware.security_logger")
    def test_log_audit_entry_200_info(self, mock_sec_log, mock_audit_log, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        request.META["HTTP_USER_AGENT"] = "TestAgent"
        response = HttpResponse("OK", status=200)
        mw._log_audit_entry(
            request=request,
            response=response,
            request_data={"method": "GET", "path": "/api/items/", "query_params": {}},
            duration_ms=15.5,
            correlation_id="test-123",
        )
        mock_audit_log.log.assert_called_once()
        # Should be INFO level (20)
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == 20  # logging.INFO

    @patch("apps.core.middleware.audit_logger")
    @patch("apps.core.middleware.security_logger")
    def test_log_audit_entry_404_warning(self, mock_sec_log, mock_audit_log, rf):
        mw = self._make_middleware()
        request = rf.get("/api/missing/")
        request.user = _make_anon_user()
        response = HttpResponse("Not Found", status=404)
        mw._log_audit_entry(
            request=request, response=response,
            request_data={"method": "GET", "path": "/api/missing/", "query_params": {}},
            duration_ms=5.0, correlation_id="test-456",
        )
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == 30  # logging.WARNING

    @patch("apps.core.middleware.audit_logger")
    @patch("apps.core.middleware.security_logger")
    def test_log_audit_entry_500_error(self, mock_sec_log, mock_audit_log, rf):
        mw = self._make_middleware()
        request = rf.get("/api/error/")
        request.user = _make_anon_user()
        response = HttpResponse("Error", status=500)
        mw._log_audit_entry(
            request=request, response=response,
            request_data={"method": "GET", "path": "/api/error/", "query_params": {}},
            duration_ms=100.0, correlation_id="test-789",
        )
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == 40  # logging.ERROR

    @patch("apps.core.middleware.audit_logger")
    @patch("apps.core.middleware.security_logger")
    def test_log_audit_entry_401_logs_security(self, mock_sec_log, mock_audit_log, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_anon_user()
        response = HttpResponse("Unauthorized", status=401)
        mw._log_audit_entry(
            request=request, response=response,
            request_data={"method": "GET", "path": "/api/items/", "query_params": {}},
            duration_ms=5.0, correlation_id="test-auth",
        )
        mock_sec_log.warning.assert_called_once()

    @patch("apps.core.middleware.audit_logger")
    @patch("apps.core.middleware.security_logger")
    def test_log_audit_entry_400_on_auth_path_logs_security(
        self, mock_sec_log, mock_audit_log, rf
    ):
        mw = self._make_middleware()
        request = rf.post("/api/auth/login/")
        request.user = _make_anon_user()
        response = HttpResponse("Bad Request", status=400)
        mw._log_audit_entry(
            request=request, response=response,
            request_data={"method": "POST", "path": "/api/auth/login/", "query_params": {}},
            duration_ms=5.0, correlation_id="test-auth-fail",
        )
        mock_sec_log.warning.assert_called_once()

    # --- Enhanced logging ---

    @patch("apps.core.middleware.audit_logger")
    @patch("apps.core.middleware.security_logger")
    def test_enhanced_logging_for_auth_path(self, mock_sec_log, mock_audit_log, rf):
        mw = self._make_middleware()
        request = rf.post("/api/auth/login/")
        request.user = _make_anon_user()
        response = HttpResponse("OK", status=200)
        mw._log_audit_entry(
            request=request, response=response,
            request_data={"method": "POST", "path": "/api/auth/login/", "query_params": {}},
            duration_ms=5.0, correlation_id="test-enhanced",
        )
        logged_json = mock_audit_log.log.call_args[0][1]
        entry = json.loads(logged_json)
        assert entry["security_event"] is True
        assert entry["action"] == "login_attempt"

    # --- _requires_enhanced_logging ---

    def test_requires_enhanced_logging_auth(self):
        mw = self._make_middleware()
        assert mw._requires_enhanced_logging("/api/auth/login/") is True

    def test_requires_enhanced_logging_banking(self):
        mw = self._make_middleware()
        assert mw._requires_enhanced_logging("/api/banking/accounts/") is True

    def test_requires_enhanced_logging_admin(self):
        mw = self._make_middleware()
        assert mw._requires_enhanced_logging("/admin/users/") is True

    def test_requires_enhanced_logging_normal(self):
        mw = self._make_middleware()
        assert mw._requires_enhanced_logging("/api/items/") is False

    # --- _determine_action ---

    def test_determine_action_login(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/auth/login/")
        assert mw._determine_action(request) == "login_attempt"

    def test_determine_action_logout(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/auth/logout/")
        assert mw._determine_action(request) == "logout"

    def test_determine_action_register(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/auth/register/")
        assert mw._determine_action(request) == "registration"

    def test_determine_action_password(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/auth/password-reset/")
        assert mw._determine_action(request) == "password_change"

    def test_determine_action_banking_post(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/banking/connect/")
        assert mw._determine_action(request) == "bank_connection"

    def test_determine_action_subscription(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/subscriptions/plans/")
        assert mw._determine_action(request) == "subscription_change"

    def test_determine_action_generic(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        action = mw._determine_action(request)
        assert action.startswith("get_")

    # --- Full request-response cycle ---

    @patch("apps.core.middleware.audit_logger")
    @patch("apps.core.middleware.security_logger")
    def test_full_cycle_authenticated(self, mock_sec_log, mock_audit_log, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.user = _make_auth_user(user_id=42, tier="premium")
        response = mw(request)
        assert response.status_code == 200
        assert "X-Correlation-ID" in response
        mock_audit_log.log.assert_called_once()
        entry = json.loads(mock_audit_log.log.call_args[0][1])
        assert entry["user"]["is_authenticated"] is True
        assert entry["user"]["id"] == "42"

    # --- _get_client_ip ---

    def test_audit_get_client_ip_forwarded_single(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4"
        assert mw._get_client_ip(request) == "1.2.3.4"

    def test_audit_get_client_ip_forwarded_multiple(self, rf):
        """With TRUSTED_PROXY_COUNT=1 and 2 IPs, index = max(2-1,0) = 1."""
        mw = self._make_middleware()
        request = rf.get("/api/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4, 10.0.0.1"
        assert mw._get_client_ip(request) == "10.0.0.1"

    def test_audit_get_client_ip_no_header(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/test/", REMOTE_ADDR="5.5.5.5")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        assert mw._get_client_ip(request) == "5.5.5.5"


# ============================================================================
# SubscriptionCheckMiddleware
# ============================================================================

class TestSubscriptionCheckMiddleware:
    """Tests for SubscriptionCheckMiddleware."""

    def _make_middleware(self):
        return SubscriptionCheckMiddleware(_get_response_200)

    # --- Excluded paths ---

    def test_excluded_path_auth(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/auth/login/")
        request.user = _make_auth_user()
        assert mw.process_request(request) is None

    def test_excluded_path_plans(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/subscriptions/plans/")
        request.user = _make_auth_user()
        assert mw.process_request(request) is None

    def test_excluded_path_health(self, rf):
        mw = self._make_middleware()
        request = rf.get("/health/")
        request.user = _make_auth_user()
        assert mw.process_request(request) is None

    # --- Unauthenticated user ---

    def test_unauthenticated_user_passes(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/banking/accounts/")
        request.user = _make_anon_user()
        assert mw.process_request(request) is None

    # --- Subscription required ---

    def test_inactive_subscription_returns_402(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/banking/accounts/")
        request.user = _make_auth_user()
        info = {"is_active": False, "tier": "free", "status": "expired",
                "features": {}, "limits": {}}
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 402

    def test_active_subscription_passes_banking(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/banking/accounts/")
        request.user = _make_auth_user()
        info = {"is_active": True, "tier": "premium", "status": "active",
                "features": {}, "limits": {}}
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is None

    # --- Subscription required responses ---

    def test_subscription_required_past_due(self):
        mw = self._make_middleware()
        resp = mw._subscription_required_response("past_due")
        data = json.loads(resp.content)
        assert resp.status_code == 402
        assert "paiement" in data["message"]

    def test_subscription_required_canceled(self):
        mw = self._make_middleware()
        resp = mw._subscription_required_response("canceled")
        data = json.loads(resp.content)
        assert "annule" in data["message"]

    def test_subscription_required_expired(self):
        mw = self._make_middleware()
        resp = mw._subscription_required_response("expired")
        data = json.loads(resp.content)
        assert "expire" in data["message"]

    def test_subscription_required_generic(self):
        mw = self._make_middleware()
        resp = mw._subscription_required_response(None)
        data = json.loads(resp.content)
        assert data["error"] == "subscription_required"

    # --- Tier checks ---

    def test_premium_path_requires_premium(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/ai/insights/report/")
        request.user = _make_auth_user(tier="free")
        info = {"is_active": True, "tier": "free", "status": "active",
                "features": {}, "limits": {}}
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 403
        data = json.loads(result.content)
        assert data["error"] == "tier_upgrade_required"
        assert data["required_tier"] == "premium"

    def test_premium_user_accesses_premium_path(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/ai/insights/report/")
        request.user = _make_auth_user(tier="premium")
        info = {"is_active": True, "tier": "premium", "status": "active",
                "features": {}, "limits": {}}
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is None

    def test_pro_path_requires_pro(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/family/members/")
        request.user = _make_auth_user(tier="premium")
        info = {"is_active": True, "tier": "premium", "status": "active",
                "features": {}, "limits": {}}
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 403
        data = json.loads(result.content)
        assert data["required_tier"] == "pro"

    def test_business_path_requires_business(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/organization/team/")
        request.user = _make_auth_user(tier="pro")
        info = {"is_active": True, "tier": "pro", "status": "active",
                "features": {}, "limits": {}}
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 403
        data = json.loads(result.content)
        assert data["required_tier"] == "business"

    def test_business_user_accesses_business_path(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/organization/team/")
        request.user = _make_auth_user(tier="business")
        info = {"is_active": True, "tier": "business", "status": "active",
                "features": {}, "limits": {}}
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is None

    # --- _get_required_tier ---

    def test_get_required_tier_business(self):
        mw = self._make_middleware()
        assert mw._get_required_tier("/api/organization/team/") == "business"
        assert mw._get_required_tier("/api/api-keys/list/") == "business"

    def test_get_required_tier_pro(self):
        mw = self._make_middleware()
        assert mw._get_required_tier("/api/family/members/") == "pro"
        assert mw._get_required_tier("/api/export/advanced/report/") == "pro"

    def test_get_required_tier_premium(self):
        mw = self._make_middleware()
        assert mw._get_required_tier("/api/ai/insights/summary/") == "premium"
        assert mw._get_required_tier("/api/export/pdf/report/") == "premium"
        assert mw._get_required_tier("/api/banking/multi-account/sync/") == "premium"

    def test_get_required_tier_none(self):
        mw = self._make_middleware()
        assert mw._get_required_tier("/api/items/") is None

    # --- Feature limit checks ---

    def test_bank_account_limit_exceeded(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/banking/accounts/")
        request.user = _make_auth_user()
        info = {
            "is_active": True, "tier": "free", "status": "active",
            "features": {}, "limits": {"max_bank_accounts": 1}
        }
        with patch.object(mw, "_get_subscription_info", return_value=info), \
             patch.object(mw, "_get_current_bank_accounts", return_value=1):
            result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 403
        data = json.loads(result.content)
        assert data["error"] == "limit_exceeded"
        assert data["limit_type"] == "bank_accounts"

    def test_bank_account_limit_ok(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/banking/accounts/")
        request.user = _make_auth_user()
        info = {
            "is_active": True, "tier": "premium", "status": "active",
            "features": {}, "limits": {"max_bank_accounts": 5}
        }
        with patch.object(mw, "_get_subscription_info", return_value=info), \
             patch.object(mw, "_get_current_bank_accounts", return_value=2):
            result = mw.process_request(request)
        assert result is None

    def test_budget_limit_exceeded(self, rf):
        mw = self._make_middleware()
        request = rf.post("/api/budgets/")
        request.user = _make_auth_user()
        info = {
            "is_active": True, "tier": "free", "status": "active",
            "features": {}, "limits": {"max_budgets": 3}
        }
        with patch.object(mw, "_get_subscription_info", return_value=info), \
             patch.object(mw, "_get_current_budgets", return_value=3):
            result = mw.process_request(request)
        assert result is not None
        assert result.status_code == 403
        data = json.loads(result.content)
        assert data["limit_type"] == "budgets"

    def test_get_request_no_limit_check(self, rf):
        """GET requests should not trigger limit checks."""
        mw = self._make_middleware()
        request = rf.get("/api/banking/accounts/")
        request.user = _make_auth_user()
        info = {
            "is_active": True, "tier": "free", "status": "active",
            "features": {}, "limits": {"max_bank_accounts": 1}
        }
        with patch.object(mw, "_get_subscription_info", return_value=info):
            result = mw.process_request(request)
        assert result is None

    # --- _get_current_bank_accounts / _get_current_budgets with cache ---

    @patch("apps.core.middleware.cache")
    def test_get_current_bank_accounts_cached(self, mock_cache):
        mw = self._make_middleware()
        mock_cache.get.return_value = 3
        user = _make_auth_user()
        assert mw._get_current_bank_accounts(user) == 3

    @patch("apps.core.middleware.cache")
    def test_get_current_bank_accounts_import_error(self, mock_cache):
        mw = self._make_middleware()
        mock_cache.get.return_value = None
        user = _make_auth_user()
        with patch("apps.core.middleware.cache") as mc:
            mc.get.return_value = None
            # If BankAccount model import fails, should return 0
            with patch.dict("sys.modules", {"apps.banking.models": None}):
                count = mw._get_current_bank_accounts(user)
                # It will try to import and fail, returning 0
                assert count >= 0

    @patch("apps.core.middleware.cache")
    def test_get_current_budgets_cached(self, mock_cache):
        mw = self._make_middleware()
        mock_cache.get.return_value = 5
        user = _make_auth_user()
        assert mw._get_current_budgets(user) == 5

    # --- _get_subscription_info error fallback ---

    @patch("apps.core.middleware.cache")
    def test_get_subscription_info_fallback_on_error(self, mock_cache):
        mw = self._make_middleware()
        mock_cache.get.return_value = None
        user = _make_auth_user(tier="premium")
        # Simulate import error in the subscription model
        with patch.dict("sys.modules", {"apps.subscriptions.models": None}):
            info = mw._get_subscription_info(user)
        # Should use fallback info
        assert info["is_active"] is True
        assert info["tier"] == "premium"

    # --- _get_subscription_info from cache ---

    @patch("apps.core.middleware.cache")
    def test_get_subscription_info_from_cache(self, mock_cache):
        mw = self._make_middleware()
        cached = {"is_active": True, "tier": "pro", "status": "active",
                  "features": {}, "limits": {}}
        mock_cache.get.return_value = cached
        user = _make_auth_user()
        info = mw._get_subscription_info(user)
        assert info == cached

    # --- _get_free_tier_info ---

    def test_free_tier_info(self):
        mw = self._make_middleware()
        info = mw._get_free_tier_info()
        assert info["is_active"] is True
        assert info["tier"] == "free"
        assert info["limits"]["max_bank_accounts"] == 1
        assert info["limits"]["max_budgets"] == 3

    # --- _tier_upgrade_required_response ---

    def test_tier_upgrade_response_premium(self):
        mw = self._make_middleware()
        resp = mw._tier_upgrade_required_response("free", "premium")
        data = json.loads(resp.content)
        assert resp.status_code == 403
        assert "Premium" in data["message"]
        assert data["current_tier"] == "free"
        assert data["required_tier"] == "premium"

    # --- _limit_exceeded_response ---

    def test_limit_exceeded_response(self):
        mw = self._make_middleware()
        resp = mw._limit_exceeded_response("bank_accounts", 1, 1)
        data = json.loads(resp.content)
        assert resp.status_code == 403
        assert data["limit_type"] == "bank_accounts"
        assert data["current"] == 1
        assert data["max_allowed"] == 1


# ============================================================================
# SecurityHeadersMiddleware
# ============================================================================

class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    def _make_middleware(self):
        return SecurityHeadersMiddleware(_get_response_200)

    def test_always_set_headers(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert result["X-Content-Type-Options"] == "nosniff"
        assert result["X-XSS-Protection"] == "1; mode=block"
        assert result["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_x_frame_options_default(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert result["X-Frame-Options"] == "DENY"

    def test_x_frame_options_preserved(self, rf):
        """If X-Frame-Options is already set, it should not be overwritten."""
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        response["X-Frame-Options"] = "SAMEORIGIN"
        result = mw.process_response(request, response)
        assert result["X-Frame-Options"] == "SAMEORIGIN"

    @override_settings(CONTENT_SECURITY_POLICY="default-src 'self'")
    def test_csp_header_set(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert result["Content-Security-Policy"] == "default-src 'self'"

    @override_settings(CONTENT_SECURITY_POLICY=None)
    def test_csp_header_not_set_when_none(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert "Content-Security-Policy" not in result

    @override_settings(PERMISSIONS_POLICY="camera=(), microphone=()")
    def test_permissions_policy_set(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert result["Permissions-Policy"] == "camera=(), microphone=()"

    @override_settings(PERMISSIONS_POLICY=None)
    def test_permissions_policy_not_set_when_none(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert "Permissions-Policy" not in result

    def test_hsts_for_secure_request(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.is_secure = lambda: True
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert "Strict-Transport-Security" in result
        assert "max-age=31536000" in result["Strict-Transport-Security"]
        assert "includeSubDomains" in result["Strict-Transport-Security"]
        assert "preload" in result["Strict-Transport-Security"]

    def test_no_hsts_for_insecure_request(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.is_secure = lambda: False
        response = HttpResponse("OK")
        result = mw.process_response(request, response)
        assert "Strict-Transport-Security" not in result

    def test_hsts_not_overwritten_if_present(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        request.is_secure = lambda: True
        response = HttpResponse("OK")
        response["Strict-Transport-Security"] = "max-age=600"
        result = mw.process_response(request, response)
        assert result["Strict-Transport-Security"] == "max-age=600"

    def test_server_header_removed(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        response["Server"] = "nginx/1.19"
        result = mw.process_response(request, response)
        assert "Server" not in result

    def test_x_powered_by_removed(self, rf):
        mw = self._make_middleware()
        request = rf.get("/api/items/")
        response = HttpResponse("OK")
        response["X-Powered-By"] = "Django"
        result = mw.process_response(request, response)
        assert "X-Powered-By" not in result


# ============================================================================
# Helper context manager for no-op
# ============================================================================

from contextlib import contextmanager

@contextmanager
def _noop_ctx():
    yield
