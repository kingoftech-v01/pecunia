"""
AI Services Package.

Provides AI-powered services for financial analysis using Claude API.
"""
from .base import (
    BaseAIService,
    AIServiceError,
    AIRateLimitError,
    AIResponseError,
)
from .categorization import TransactionCategorizer
from .anomaly_detection import AnomalyDetector
from .recommendations import RecommendationEngine

# Try to import claude_client if it exists
try:
    from .claude_client import ClaudeClient, SyncClaudeClient, ClaudeResponse
    _has_claude_client = True
except ImportError:
    _has_claude_client = False

# Legacy aliases for backward compatibility
TransactionCategorizationService = TransactionCategorizer
BudgetRecommendationService = RecommendationEngine
AnomalyDetectionService = AnomalyDetector

__all__ = [
    # Base classes and exceptions
    'BaseAIService',
    'AIServiceError',
    'AIRateLimitError',
    'AIResponseError',
    # Service classes (new names)
    'TransactionCategorizer',
    'AnomalyDetector',
    'RecommendationEngine',
    # Legacy aliases
    'TransactionCategorizationService',
    'BudgetRecommendationService',
    'AnomalyDetectionService',
]

# Add claude_client exports if available
if _has_claude_client:
    __all__.extend([
        'ClaudeClient',
        'SyncClaudeClient',
        'ClaudeResponse',
    ])
