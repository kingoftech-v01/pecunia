"""
Core Middleware.

Custom middleware for security, rate limiting, audit logging, and subscription checks.
Implements OWASP Top 10 protection measures.
"""
import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

# Security logger - configured to avoid logging sensitive data
security_logger = logging.getLogger('security')
audit_logger = logging.getLogger('audit')


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware to prevent abuse and DDoS attacks.

    Features:
    - IP-based rate limiting for anonymous users
    - User-based rate limiting for authenticated users
    - Tiered limits based on subscription level
    - Sliding window algorithm for accurate rate limiting
    - Bypass for whitelisted IPs and paths

    OWASP Protection:
    - A04:2021 - Insecure Design (rate limiting)
    - A05:2021 - Security Misconfiguration (DDoS protection)
    """

    # Default rate limits (requests per window)
    DEFAULT_LIMITS = {
        'anonymous': {'requests': 60, 'window': 60},      # 60 req/min
        'free': {'requests': 120, 'window': 60},          # 120 req/min
        'premium': {'requests': 300, 'window': 60},       # 300 req/min
        'pro': {'requests': 600, 'window': 60},           # 600 req/min
        'business': {'requests': 1200, 'window': 60},     # 1200 req/min
    }

    # Stricter limits for sensitive endpoints
    SENSITIVE_ENDPOINT_LIMITS = {
        '/api/auth/login/': {'requests': 5, 'window': 60},
        '/api/auth/register/': {'requests': 3, 'window': 60},
        '/api/auth/password-reset/': {'requests': 3, 'window': 300},
        '/api/auth/verify-email/': {'requests': 5, 'window': 60},
        '/api/banking/connect/': {'requests': 10, 'window': 300},
    }

    # Paths excluded from rate limiting
    EXCLUDED_PATHS = [
        '/health/',
        '/ready/',
        '/static/',
        '/favicon.ico',
    ]

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.limits = getattr(settings, 'RATE_LIMIT_CONFIG', self.DEFAULT_LIMITS)
        self.sensitive_limits = getattr(
            settings,
            'RATE_LIMIT_SENSITIVE_ENDPOINTS',
            self.SENSITIVE_ENDPOINT_LIMITS
        )
        self.whitelisted_ips = set(getattr(settings, 'RATE_LIMIT_WHITELIST_IPS', []))
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Process incoming request for rate limiting."""
        # Skip rate limiting for excluded paths
        if self._is_excluded_path(request.path):
            return None

        # Get client identifier
        client_key = self._get_client_key(request)

        # Check whitelist
        client_ip = self._get_client_ip(request)
        if client_ip in self.whitelisted_ips:
            return None

        # Determine rate limit for this request
        limit_config = self._get_limit_config(request)

        # Check and update rate limit
        is_allowed, remaining, reset_time = self._check_rate_limit(
            client_key,
            limit_config
        )

        if not is_allowed:
            security_logger.warning(
                "Rate limit exceeded",
                extra={
                    'client_ip': self._hash_ip(client_ip),
                    'path': request.path,
                    'user_id': str(request.user.id) if request.user.is_authenticated else None,
                }
            )
            return self._rate_limit_response(reset_time)

        # Store rate limit info for response headers
        request._rate_limit_remaining = remaining
        request._rate_limit_reset = reset_time

        return None

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse
    ) -> HttpResponse:
        """Add rate limit headers to response."""
        if hasattr(request, '_rate_limit_remaining'):
            response['X-RateLimit-Remaining'] = str(request._rate_limit_remaining)
            response['X-RateLimit-Reset'] = str(int(request._rate_limit_reset))
        return response

    def _get_client_key(self, request: HttpRequest) -> str:
        """Generate unique client identifier for rate limiting."""
        if request.user.is_authenticated:
            return f"ratelimit:user:{request.user.id}"
        return f"ratelimit:ip:{self._hash_ip(self._get_client_ip(request))}"

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP address from request.

        Uses TRUSTED_PROXY_COUNT from settings to select the correct
        IP from X-Forwarded-For, counting from the right.  This prevents
        spoofing via forged leftmost entries.
        """
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(',')]
            trusted_proxy_count = getattr(settings, 'TRUSTED_PROXY_COUNT', 1)
            # The rightmost `trusted_proxy_count` IPs are from trusted proxies.
            # The entry just before them is the real client IP.
            index = max(len(ips) - trusted_proxy_count, 0)
            return ips[index]

        real_ip = request.META.get('HTTP_X_REAL_IP')
        if real_ip:
            return real_ip

        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _hash_ip(self, ip: str) -> str:
        """Hash IP address for logging (privacy protection)."""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]

    def _get_limit_config(self, request: HttpRequest) -> Dict[str, int]:
        """Determine rate limit configuration for request."""
        # Check for sensitive endpoint
        for pattern, config in self.sensitive_limits.items():
            if request.path.startswith(pattern):
                return config

        # Get user tier-based limit
        if request.user.is_authenticated:
            tier = getattr(request.user, 'subscription_tier', 'free')
            return self.limits.get(tier, self.limits['free'])

        return self.limits['anonymous']

    def _check_rate_limit(
        self,
        key: str,
        config: Dict[str, int]
    ) -> tuple[bool, int, float]:
        """
        Check rate limit using sliding window algorithm.

        Returns:
            tuple: (is_allowed, remaining_requests, reset_timestamp)
        """
        now = time.time()
        window = config['window']
        max_requests = config['requests']

        # SLIDING WINDOW RATE LIMITING: Unlike fixed windows (which allow burst
        # attacks at window boundaries), we weight the previous window's count
        # by how much time remains. Example with 60s window, 100 req limit:
        #   - At t=90s (50% into window 1): prev_window=80, current=30
        #   - Weighted = 80 * 0.5 + 30 = 70 requests (allowed)
        #   - This smooths the limit across window boundaries.
        window_key = f"{key}:{int(now // window)}"
        previous_window_key = f"{key}:{int(now // window) - 1}"

        current_count = cache.get(window_key, 0)
        previous_count = cache.get(previous_window_key, 0)

        # window_progress is 0.0 at window start, approaches 1.0 at end.
        # We weight the previous window inversely: more weight early, less late.
        window_progress = (now % window) / window
        weighted_count = previous_count * (1 - window_progress) + current_count

        remaining = max(0, max_requests - int(weighted_count) - 1)
        reset_time = (int(now // window) + 1) * window

        if weighted_count >= max_requests:
            return False, 0, reset_time

        # Store for 2x window duration so previous window data survives.
        cache.set(window_key, current_count + 1, timeout=window * 2)

        return True, remaining, reset_time

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from rate limiting."""
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _rate_limit_response(self, reset_time: float) -> JsonResponse:
        """Generate rate limit exceeded response."""
        retry_after = int(reset_time - time.time())
        response = JsonResponse(
            {
                'error': 'rate_limit_exceeded',
                'message': 'Trop de requetes. Veuillez patienter avant de reessayer.',
                'retry_after': max(1, retry_after),
            },
            status=429
        )
        response['Retry-After'] = str(max(1, retry_after))
        return response


# =============================================================================
# Audit Log Middleware
# =============================================================================

class AuditLogMiddleware(MiddlewareMixin):
    """
    Comprehensive audit logging middleware.

    Features:
    - Logs all API requests and responses
    - Captures security-relevant events
    - Sanitizes sensitive data before logging
    - Structured logging format for SIEM integration
    - Request correlation IDs for tracing

    OWASP Protection:
    - A09:2021 - Security Logging and Monitoring Failures
    """

    # Sensitive fields to redact from logs
    SENSITIVE_FIELDS = {
        'password', 'password1', 'password2', 'new_password', 'old_password',
        'token', 'access_token', 'refresh_token', 'api_key', 'secret',
        'credit_card', 'card_number', 'cvv', 'cvc', 'pin',
        'ssn', 'social_security', 'tax_id',
        'authorization', 'cookie', 'session',
        'iban', 'account_number', 'routing_number',
    }

    # Paths to exclude from detailed logging
    EXCLUDED_PATHS = [
        '/health/',
        '/ready/',
        '/static/',
        '/favicon.ico',
        '/api/docs/',
    ]

    # Paths requiring enhanced logging
    ENHANCED_LOGGING_PATHS = [
        '/api/auth/',
        '/api/banking/',
        '/api/subscriptions/',
        '/admin/',
    ]

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        super().__init__(get_response)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request and log audit trail."""
        # Skip excluded paths
        if self._is_excluded_path(request.path):
            return self.get_response(request)

        # Generate correlation ID
        correlation_id = request.META.get(
            'HTTP_X_CORRELATION_ID',
            str(uuid.uuid4())
        )
        request.correlation_id = correlation_id

        # Record start time
        start_time = time.time()

        # Capture request data
        request_data = self._capture_request_data(request)

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log audit entry
        self._log_audit_entry(
            request=request,
            response=response,
            request_data=request_data,
            duration_ms=duration_ms,
            correlation_id=correlation_id
        )

        # Add correlation ID to response
        response['X-Correlation-ID'] = correlation_id

        return response

    def _capture_request_data(self, request: HttpRequest) -> Dict[str, Any]:
        """Capture and sanitize request data for logging."""
        data = {
            'method': request.method,
            'path': request.path,
            'query_params': self._sanitize_dict(dict(request.GET)),
        }

        # Capture body for write operations (POST, PUT, PATCH, DELETE)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            try:
                if request.content_type == 'application/json':
                    body = json.loads(request.body.decode('utf-8'))
                    data['body'] = self._sanitize_dict(body)
                elif hasattr(request, 'POST'):
                    data['body'] = self._sanitize_dict(dict(request.POST))
            except (json.JSONDecodeError, UnicodeDecodeError):
                data['body'] = '[binary_data]'

        return data

    def _sanitize_dict(self, data: Dict) -> Dict:
        """Recursively sanitize sensitive fields from dictionary."""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            lower_key = key.lower()

            # Check if key matches sensitive patterns
            is_sensitive = any(
                sensitive in lower_key
                for sensitive in self.SENSITIVE_FIELDS
            )

            if is_sensitive:
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def _log_audit_entry(
        self,
        request: HttpRequest,
        response: HttpResponse,
        request_data: Dict[str, Any],
        duration_ms: float,
        correlation_id: str
    ) -> None:
        """Create structured audit log entry."""
        # Determine log level based on response status
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Build audit entry
        audit_entry = {
            'timestamp': timezone.now().isoformat(),
            'correlation_id': correlation_id,
            'event_type': 'api_request',

            # Request info
            'request': {
                **request_data,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                'referer': request.META.get('HTTP_REFERER', '')[:200],
            },

            # Response info
            'response': {
                'status_code': response.status_code,
                'content_length': len(response.content) if hasattr(response, 'content') else 0,
            },

            # User info (no PII in logs)
            'user': {
                'id': str(request.user.id) if request.user.is_authenticated else None,
                'is_authenticated': request.user.is_authenticated,
                'tier': getattr(request.user, 'subscription_tier', None) if request.user.is_authenticated else None,
            },

            # Client info (hashed for privacy)
            'client': {
                'ip_hash': hashlib.sha256(
                    self._get_client_ip(request).encode()
                ).hexdigest()[:16],
            },

            # Performance
            'duration_ms': round(duration_ms, 2),
        }

        # Enhanced logging for security-sensitive paths
        if self._requires_enhanced_logging(request.path):
            audit_entry['security_event'] = True
            audit_entry['action'] = self._determine_action(request)

        # Log the entry
        audit_logger.log(log_level, json.dumps(audit_entry))

        # Additional security logging for failed auth attempts
        if response.status_code == 401 or (
            response.status_code == 400 and
            'auth' in request.path.lower()
        ):
            security_logger.warning(
                "Authentication failure",
                extra={
                    'correlation_id': correlation_id,
                    'path': request.path,
                    'ip_hash': audit_entry['client']['ip_hash'],
                }
            )

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP address.

        Uses TRUSTED_PROXY_COUNT from settings to select the correct
        IP from X-Forwarded-For, counting from the right.
        """
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(',')]
            trusted_proxy_count = getattr(settings, 'TRUSTED_PROXY_COUNT', 1)
            index = max(len(ips) - trusted_proxy_count, 0)
            return ips[index]
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from logging."""
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _requires_enhanced_logging(self, path: str) -> bool:
        """Check if path requires enhanced security logging."""
        return any(path.startswith(enhanced) for enhanced in self.ENHANCED_LOGGING_PATHS)

    def _determine_action(self, request: HttpRequest) -> str:
        """Determine the security action from request."""
        path = request.path.lower()
        method = request.method

        if 'login' in path:
            return 'login_attempt'
        elif 'logout' in path:
            return 'logout'
        elif 'register' in path:
            return 'registration'
        elif 'password' in path:
            return 'password_change'
        elif 'banking' in path and method == 'POST':
            return 'bank_connection'
        elif 'subscription' in path:
            return 'subscription_change'
        else:
            return f"{method.lower()}_{path.replace('/', '_').strip('_')}"


# =============================================================================
# Subscription Check Middleware
# =============================================================================

class SubscriptionCheckMiddleware(MiddlewareMixin):
    """
    Middleware to verify subscription status and enforce tier limits.

    Features:
    - Validates active subscription before accessing premium features
    - Enforces tier-based access control
    - Caches subscription status for performance
    - Handles grace periods for expired subscriptions
    - Injects subscription info into request for downstream use

    OWASP Protection:
    - A01:2021 - Broken Access Control
    """

    # Paths that require active subscription
    SUBSCRIPTION_REQUIRED_PATHS = [
        '/api/banking/',
        '/api/ai/',
        '/api/export/',
    ]

    # Paths that require premium tier or higher
    PREMIUM_REQUIRED_PATHS = [
        '/api/ai/insights/',
        '/api/export/pdf/',
        '/api/banking/multi-account/',
    ]

    # Paths that require pro tier or higher
    PRO_REQUIRED_PATHS = [
        '/api/family/',
        '/api/export/advanced/',
    ]

    # Paths that require business tier
    BUSINESS_REQUIRED_PATHS = [
        '/api/organization/',
        '/api/api-keys/',
    ]

    # Excluded paths (public or free tier)
    EXCLUDED_PATHS = [
        '/api/auth/',
        '/api/subscriptions/plans/',
        '/api/subscriptions/checkout/',
        '/health/',
        '/static/',
    ]

    # Tier hierarchy
    TIER_LEVELS = {
        'free': 0,
        'premium': 1,
        'pro': 2,
        'business': 3,
    }

    # Cache timeout for subscription status (5 minutes)
    CACHE_TIMEOUT = 300

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Verify subscription status before processing request."""
        # Skip for excluded paths
        if self._is_excluded_path(request.path):
            return None

        # Skip for unauthenticated users (handled by auth middleware)
        if not request.user.is_authenticated:
            return None

        # Get subscription info (cached)
        subscription_info = self._get_subscription_info(request.user)

        # Attach subscription info to request
        request.subscription = subscription_info

        # Check if subscription is required
        if self._requires_subscription(request.path):
            if not subscription_info['is_active']:
                return self._subscription_required_response(
                    subscription_info.get('status')
                )

        # Check tier requirements
        required_tier = self._get_required_tier(request.path)
        if required_tier:
            user_tier_level = self.TIER_LEVELS.get(subscription_info['tier'], 0)
            required_tier_level = self.TIER_LEVELS.get(required_tier, 0)

            if user_tier_level < required_tier_level:
                return self._tier_upgrade_required_response(
                    current_tier=subscription_info['tier'],
                    required_tier=required_tier
                )

        # Check feature-specific limits
        limit_check = self._check_feature_limits(request, subscription_info)
        if limit_check:
            return limit_check

        return None

    def _get_subscription_info(self, user) -> Dict[str, Any]:
        """Get subscription info with caching."""
        cache_key = f"subscription_info:{user.id}"
        cached_info = cache.get(cache_key)

        if cached_info:
            return cached_info

        # Fetch fresh subscription info
        try:
            from apps.subscriptions.models import Subscription

            subscription = Subscription.objects.select_related('plan').filter(
                user=user
            ).first()

            if subscription:
                info = {
                    'is_active': subscription.is_active,
                    'tier': subscription.tier,
                    'status': subscription.status,
                    'plan_id': str(subscription.plan.id),
                    'expires_at': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                    'features': {
                        'ai_categorization': subscription.has_feature('ai_categorization'),
                        'ai_insights': subscription.has_feature('ai_insights'),
                        'bank_sync': subscription.has_feature('bank_sync'),
                        'export_csv': subscription.has_feature('export_csv'),
                        'export_pdf': subscription.has_feature('export_pdf'),
                        'multi_currency': subscription.has_feature('multi_currency'),
                        'api_access': subscription.has_feature('api_access'),
                    },
                    'limits': {
                        'max_bank_accounts': subscription.get_limit('max_bank_accounts'),
                        'max_budgets': subscription.get_limit('max_budgets'),
                        'max_transactions_per_month': subscription.get_limit('max_transactions_per_month'),
                        'max_categories': subscription.get_limit('max_categories'),
                        'max_family_members': subscription.get_limit('max_family_members'),
                    },
                }
            else:
                # No subscription - use free tier
                info = self._get_free_tier_info()
        except Exception:
            # Fallback to user's subscription_tier field
            info = {
                'is_active': True,
                'tier': getattr(user, 'subscription_tier', 'free'),
                'status': 'active',
                'features': {},
                'limits': {},
            }

        # Cache the result
        cache.set(cache_key, info, self.CACHE_TIMEOUT)

        return info

    def _get_free_tier_info(self) -> Dict[str, Any]:
        """Get default free tier subscription info."""
        return {
            'is_active': True,
            'tier': 'free',
            'status': 'active',
            'features': {
                'ai_categorization': False,
                'ai_insights': False,
                'bank_sync': False,
                'export_csv': False,
                'export_pdf': False,
                'multi_currency': False,
                'api_access': False,
            },
            'limits': {
                'max_bank_accounts': 1,
                'max_budgets': 3,
                'max_transactions_per_month': 100,
                'max_categories': 10,
                'max_family_members': 0,
            },
        }

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from subscription checks."""
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _requires_subscription(self, path: str) -> bool:
        """Check if path requires an active subscription."""
        return any(
            path.startswith(sub_path)
            for sub_path in self.SUBSCRIPTION_REQUIRED_PATHS
        )

    def _get_required_tier(self, path: str) -> Optional[str]:
        """Determine the minimum required tier for path."""
        for business_path in self.BUSINESS_REQUIRED_PATHS:
            if path.startswith(business_path):
                return 'business'

        for pro_path in self.PRO_REQUIRED_PATHS:
            if path.startswith(pro_path):
                return 'pro'

        for premium_path in self.PREMIUM_REQUIRED_PATHS:
            if path.startswith(premium_path):
                return 'premium'

        return None

    def _check_feature_limits(
        self,
        request: HttpRequest,
        subscription_info: Dict[str, Any]
    ) -> Optional[HttpResponse]:
        """Check if request exceeds feature limits."""
        path = request.path
        limits = subscription_info.get('limits', {})

        # Check bank account limit
        if path.startswith('/api/banking/accounts/') and request.method == 'POST':
            current_count = self._get_current_bank_accounts(request.user)
            max_allowed = limits.get('max_bank_accounts', 1)

            if current_count >= max_allowed:
                return self._limit_exceeded_response(
                    limit_type='bank_accounts',
                    current=current_count,
                    max_allowed=max_allowed
                )

        # Check budget limit
        if path.startswith('/api/budgets/') and request.method == 'POST':
            current_count = self._get_current_budgets(request.user)
            max_allowed = limits.get('max_budgets', 3)

            if current_count >= max_allowed:
                return self._limit_exceeded_response(
                    limit_type='budgets',
                    current=current_count,
                    max_allowed=max_allowed
                )

        return None

    def _get_current_bank_accounts(self, user) -> int:
        """Get current bank account count for user (short-lived cache)."""
        cache_key = f"bank_account_count:{user.id}"
        count = cache.get(cache_key)
        if count is not None:
            return count
        try:
            from apps.banking.models import BankAccount
            count = BankAccount.objects.filter(user=user).count()
        except Exception:
            count = 0
        cache.set(cache_key, count, timeout=30)
        return count

    def _get_current_budgets(self, user) -> int:
        """Get current budget count for user (short-lived cache)."""
        cache_key = f"budget_count:{user.id}"
        count = cache.get(cache_key)
        if count is not None:
            return count
        try:
            from apps.budgets.models import Budget
            count = Budget.objects.filter(user=user).count()
        except Exception:
            count = 0
        cache.set(cache_key, count, timeout=30)
        return count

    def _subscription_required_response(
        self,
        status: Optional[str] = None
    ) -> JsonResponse:
        """Generate subscription required response."""
        message = 'Un abonnement actif est requis pour acceder a cette fonctionnalite.'

        if status == 'past_due':
            message = 'Votre abonnement est en retard de paiement. Veuillez mettre a jour vos informations de paiement.'
        elif status == 'canceled':
            message = 'Votre abonnement a ete annule. Veuillez renouveler pour continuer.'
        elif status == 'expired':
            message = 'Votre abonnement a expire. Veuillez le renouveler pour continuer.'

        return JsonResponse(
            {
                'error': 'subscription_required',
                'message': message,
                'status': status,
                'upgrade_url': '/subscriptions/plans/',
            },
            status=402
        )

    def _tier_upgrade_required_response(
        self,
        current_tier: str,
        required_tier: str
    ) -> JsonResponse:
        """Generate tier upgrade required response."""
        tier_names = {
            'free': 'Gratuit',
            'premium': 'Premium',
            'pro': 'Pro/Family',
            'business': 'Business',
        }

        return JsonResponse(
            {
                'error': 'tier_upgrade_required',
                'message': f'Cette fonctionnalite necessite un abonnement {tier_names.get(required_tier, required_tier)}.',
                'current_tier': current_tier,
                'required_tier': required_tier,
                'upgrade_url': '/subscriptions/plans/',
            },
            status=403
        )

    def _limit_exceeded_response(
        self,
        limit_type: str,
        current: int,
        max_allowed: int
    ) -> JsonResponse:
        """Generate limit exceeded response."""
        limit_names = {
            'bank_accounts': 'comptes bancaires',
            'budgets': 'budgets',
            'transactions': 'transactions',
            'categories': 'categories',
        }

        return JsonResponse(
            {
                'error': 'limit_exceeded',
                'message': f'Vous avez atteint la limite de {limit_names.get(limit_type, limit_type)} pour votre abonnement.',
                'limit_type': limit_type,
                'current': current,
                'max_allowed': max_allowed,
                'upgrade_url': '/subscriptions/plans/',
            },
            status=403
        )


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to all responses.

    Implements defense-in-depth with multiple security headers.

    OWASP Protection:
    - A02:2021 - Cryptographic Failures
    - A03:2021 - Injection (XSS)
    - A05:2021 - Security Misconfiguration
    """

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse
    ) -> HttpResponse:
        """Add security headers to response."""
        # Content Security Policy
        csp_config = getattr(settings, 'CONTENT_SECURITY_POLICY', None)
        if csp_config:
            response['Content-Security-Policy'] = csp_config

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'

        # Clickjacking protection
        if 'X-Frame-Options' not in response:
            response['X-Frame-Options'] = 'DENY'

        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy (feature policy)
        permissions_policy = getattr(settings, 'PERMISSIONS_POLICY', None)
        if permissions_policy:
            response['Permissions-Policy'] = permissions_policy

        # HSTS (handled by Django's SecurityMiddleware, but ensure it's set)
        if request.is_secure():
            if 'Strict-Transport-Security' not in response:
                response['Strict-Transport-Security'] = (
                    'max-age=31536000; includeSubDomains; preload'
                )

        # Remove server header if present
        if 'Server' in response:
            del response['Server']

        # Remove X-Powered-By if present
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        return response


# =============================================================================
# Request Sanitization Middleware
# =============================================================================

class RequestSanitizationMiddleware(MiddlewareMixin):
    """
    Middleware to sanitize incoming requests.

    Features:
    - Input validation and sanitization
    - SQL injection pattern detection
    - XSS payload detection
    - Path traversal prevention

    OWASP Protection:
    - A03:2021 - Injection
    """

    # Suspicious patterns (SQL injection, XSS, etc.)
    # These patterns are designed to avoid false positives on legitimate
    # financial terms like "FROM account", "SELECT plan", etc.
    SUSPICIOUS_PATTERNS = [
        # SQL Injection patterns - require SQL-like structure, not bare keywords
        r"(\bSELECT\b\s+[\w\*,\s]+\bFROM\b\s+\w+)",        # SELECT ... FROM table
        r"(\bINSERT\b\s+\bINTO\b\s+\w+)",                    # INSERT INTO table
        r"(\bUPDATE\b\s+\w+\s+\bSET\b)",                     # UPDATE table SET
        r"(\bDELETE\b\s+\bFROM\b\s+\w+\s+\bWHERE\b)",       # DELETE FROM table WHERE
        r"(\b(DROP|ALTER|TRUNCATE)\b\s+\b(TABLE|DATABASE|INDEX)\b)",  # DDL statements
        r"(\bUNION\b\s+(ALL\s+)?\bSELECT\b)",                # UNION [ALL] SELECT
        r"(\bCREATE\b\s+\b(TABLE|DATABASE|INDEX)\b)",         # CREATE TABLE/DATABASE
        r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
        r"(--\s*$|;--)",
        r"(\bEXEC(UTE)?\b\s*\()",

        # XSS patterns
        r"(<script[^>]*>)",
        r"(javascript\s*:)",
        r"(on\w+\s*=)",
        r"(<iframe[^>]*>)",

        # Path traversal
        r"(\.\.\/|\.\.\\)",
        r"(%2e%2e%2f|%2e%2e\/|\.\.%2f)",
    ]

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SUSPICIOUS_PATTERNS
        ]
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Sanitize incoming request."""
        # Check query parameters
        for key, value in request.GET.items():
            if self._is_suspicious(value):
                security_logger.warning(
                    "Suspicious query parameter detected",
                    extra={
                        'path': request.path,
                        'parameter': key,
                        'ip_hash': hashlib.sha256(
                            self._get_client_ip(request).encode()
                        ).hexdigest()[:16],
                    }
                )
                return self._blocked_response()

        # Check path for traversal attempts
        if self._is_suspicious(request.path):
            security_logger.warning(
                "Suspicious path detected",
                extra={
                    'path': request.path,
                    'ip_hash': hashlib.sha256(
                        self._get_client_ip(request).encode()
                    ).hexdigest()[:16],
                }
            )
            return self._blocked_response()

        # Check request body for POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = request.body.decode('utf-8')
                if self._is_suspicious(body):
                    security_logger.warning(
                        "Suspicious request body detected",
                        extra={
                            'path': request.path,
                            'method': request.method,
                            'ip_hash': hashlib.sha256(
                                self._get_client_ip(request).encode()
                            ).hexdigest()[:16],
                        }
                    )
                    return self._blocked_response()
            except (UnicodeDecodeError, ValueError):
                pass  # Binary content, skip check

        return None

    def _is_suspicious(self, value: str) -> bool:
        """Check if value contains suspicious patterns."""
        if not value:
            return False

        for pattern in self.compiled_patterns:
            if pattern.search(value):
                return True
        return False

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP address.

        Uses TRUSTED_PROXY_COUNT from settings to select the correct
        IP from X-Forwarded-For, counting from the right.
        """
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(',')]
            trusted_proxy_count = getattr(settings, 'TRUSTED_PROXY_COUNT', 1)
            index = max(len(ips) - trusted_proxy_count, 0)
            return ips[index]
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _blocked_response(self) -> JsonResponse:
        """Generate blocked request response."""
        return JsonResponse(
            {
                'error': 'bad_request',
                'message': 'La requete contient des donnees invalides.',
            },
            status=400
        )
