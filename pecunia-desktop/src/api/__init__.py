"""
Pecunia Desktop API Module

Provides async HTTP client services for communicating with the backend API.
"""

from .client import (
    APIClient,
    APIError,
    APIResponse,
    AuthenticationError,
    NetworkError,
    ValidationError,
    TimeoutError,
    HTTPMethod,
    RequestContext,
    get_api_client,
    get_api_client_sync,
    close_api_client,
    with_retry,
)
from .auth import AuthService, TokenStorage
from .transactions import TransactionsAPI
from .budgets import BudgetsAPI
from .banking import BankingAPI

__all__ = [
    # Client classes and functions
    'APIClient',
    'APIError',
    'APIResponse',
    'AuthenticationError',
    'NetworkError',
    'ValidationError',
    'TimeoutError',
    'HTTPMethod',
    'RequestContext',
    'get_api_client',
    'get_api_client_sync',
    'close_api_client',
    'with_retry',
    # Services
    'AuthService',
    'TokenStorage',
    'TransactionsAPI',
    'BudgetsAPI',
    'BankingAPI',
]
