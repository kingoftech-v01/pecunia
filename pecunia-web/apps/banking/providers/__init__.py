"""
Banking Providers.

Multi-provider support for bank account connections.
"""
from .base import BaseBankProvider
from .budget_insight import BudgetInsightProvider
from .truelayer import TrueLayerProvider
from .plaid import PlaidProvider


# Provider registry
PROVIDERS = {
    'budget_insight': BudgetInsightProvider,
    'truelayer': TrueLayerProvider,
    'plaid': PlaidProvider,
}


def get_provider(provider_name: str) -> BaseBankProvider:
    """
    Get a provider instance by name.

    Args:
        provider_name: The provider identifier (budget_insight, truelayer, plaid)

    Returns:
        An instance of the provider class

    Raises:
        ValueError: If provider is not supported
    """
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")
    return provider_class()


def get_available_providers() -> list:
    """
    Get list of available providers.

    Returns:
        List of provider names
    """
    return list(PROVIDERS.keys())


__all__ = [
    'BaseBankProvider',
    'BudgetInsightProvider',
    'TrueLayerProvider',
    'PlaidProvider',
    'get_provider',
    'get_available_providers',
    'PROVIDERS',
]
