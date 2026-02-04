"""
Transaction Categorization Service.

AI-powered automatic transaction categorization using Claude API.
Provides intelligent categorization with learning capabilities.
"""
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from collections import defaultdict

from django.db.models import QuerySet, Count
from django.core.cache import cache
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionCategory
from apps.ai.models import AICategorizationLog, AIAnalysisCache
from .base import BaseAIService, AIServiceError, AIResponseError

logger = logging.getLogger(__name__)


class TransactionCategorizer(BaseAIService):
    """
    AI-powered transaction categorization service.

    Uses Claude AI to analyze transaction descriptions and
    suggest appropriate categories with learning from user corrections.
    """

    # Cache configuration
    CACHE_PREFIX = "ai_categorizer"
    CACHE_TTL_SINGLE = 86400  # 24 hours
    CACHE_TTL_BATCH = 3600  # 1 hour
    CACHE_TTL_SUGGESTIONS = 1800  # 30 minutes

    # Batch processing configuration
    MAX_BATCH_SIZE = 50
    MIN_CONFIDENCE_AUTO_APPLY = 0.75

    # Learning configuration
    LEARNING_WEIGHT_DECAY = 0.1  # Weight decay for older corrections

    def get_system_prompt(self) -> str:
        """Get the system prompt for categorization."""
        return """You are a financial transaction categorization expert. Your task is to analyze
transaction descriptions and suggest the most appropriate category.

You must respond ONLY with valid JSON in the following format:
{
    "category_id": "uuid-of-suggested-category",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this category was chosen",
    "keywords": ["keyword1", "keyword2"]
}

Guidelines:
- Analyze merchant names, transaction descriptions, and amounts
- Consider common spending patterns for similar transactions
- Provide confidence score between 0 and 1 (1 = very confident)
- If unsure, suggest the most likely category with lower confidence
- Be consistent in categorizing similar transactions
- Consider the transaction type (income vs expense) when categorizing
- Extract relevant keywords that helped identify the category
- Pay attention to merchant patterns (e.g., "AMZN" = Amazon, "SPTFY" = Spotify)"""

    def categorize_single(
        self,
        description: str,
        merchant: Optional[str] = None,
        amount: Optional[Decimal] = None,
        transaction_type: str = 'expense',
        user=None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Categorize a single transaction by description and merchant.

        Args:
            description: Transaction description
            merchant: Merchant name (optional)
            amount: Transaction amount (optional)
            transaction_type: 'income' or 'expense'
            user: User instance for category lookup
            use_cache: Whether to use cached results

        Returns:
            dict: Categorization result with category_id, confidence, reasoning
        """
        if not user:
            return self._error_response("User is required for categorization")

        # Generate cache key
        cache_key = self._get_categorization_cache_key(
            description, merchant, transaction_type, user.id
        )

        # Check cache
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Using cached categorization for: {description[:50]}")
                cached['from_cache'] = True
                return cached

        # Check for learned patterns first
        learned_result = self._check_learned_patterns(
            description, merchant, user
        )
        if learned_result and learned_result.get('confidence', 0) >= 0.9:
            if use_cache:
                cache.set(cache_key, learned_result, self.CACHE_TTL_SINGLE)
            return learned_result

        # Get user's categories
        user_categories = TransactionCategory.objects.filter(
            user=user,
            type=transaction_type
        )

        if not user_categories.exists():
            return self._error_response(
                f"No {transaction_type} categories found for user"
            )

        # Build context
        categories_context = self._format_categories(user_categories)
        transaction_context = self._build_transaction_context(
            description, merchant, amount, transaction_type
        )

        messages = [
            {
                "role": "user",
                "content": f"""Please categorize this transaction:

{transaction_context}

Available categories:
{categories_context}

Respond with JSON containing the suggested category_id, confidence score, reasoning, and keywords."""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                temperature=0.2
            )

            result = self._parse_json_response(response)

            # Validate category exists
            category_id = result.get("category_id")
            if category_id:
                if not user_categories.filter(id=category_id).exists():
                    logger.warning(f"AI suggested non-existent category {category_id}")
                    result["category_id"] = None
                    result["confidence"] = 0

            result['from_cache'] = False

            # Cache result
            if use_cache and result.get("category_id"):
                cache.set(cache_key, result, self.CACHE_TTL_SINGLE)

            return result

        except AIServiceError as e:
            logger.error(f"Categorization failed: {e}")
            return self._error_response(str(e))

    def categorize_batch(
        self,
        transactions: List[Transaction],
        min_confidence: float = None,
        auto_apply: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Categorize multiple transactions in batch.

        Args:
            transactions: List of Transaction instances
            min_confidence: Minimum confidence for auto-apply (default: 0.75)
            auto_apply: Whether to automatically apply high-confidence categories

        Returns:
            list: List of categorization results with transaction_id
        """
        if not transactions:
            return []

        if min_confidence is None:
            min_confidence = self.MIN_CONFIDENCE_AUTO_APPLY

        # Process in batches
        results = []
        for i in range(0, len(transactions), self.MAX_BATCH_SIZE):
            batch = transactions[i:i + self.MAX_BATCH_SIZE]
            batch_results = self._categorize_batch_internal(
                batch, min_confidence, auto_apply
            )
            results.extend(batch_results)

        return results

    def _categorize_batch_internal(
        self,
        transactions: List[Transaction],
        min_confidence: float,
        auto_apply: bool,
    ) -> List[Dict[str, Any]]:
        """Internal method to categorize a single batch."""
        if not transactions:
            return []

        # Get user from first transaction
        user = transactions[0].user
        user_categories = TransactionCategory.objects.filter(user=user)

        if not user_categories.exists():
            return [{
                "transaction_id": str(t.id),
                "category_id": None,
                "confidence": 0,
                "reasoning": "No categories available",
                "error": True,
                "auto_apply": False
            } for t in transactions]

        categories_context = self._format_categories(user_categories)

        # Format all transactions
        transactions_context = "\n\n".join([
            f"Transaction {i+1} (ID: {t.id}):\n{self._format_transaction(t)}"
            for i, t in enumerate(transactions)
        ])

        messages = [
            {
                "role": "user",
                "content": f"""Please categorize these transactions:

{transactions_context}

Available categories:
{categories_context}

Respond with a JSON array containing an object for each transaction with:
- transaction_id: the transaction ID
- category_id: suggested category UUID
- confidence: confidence score (0-1)
- reasoning: brief explanation
- keywords: relevant keywords extracted"""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                max_tokens=4096,
                temperature=0.2
            )

            results = self._parse_json_response(response)

            if not isinstance(results, list):
                results = results.get("results", results.get("transactions", []))

            # Process and validate results
            processed_results = []
            transaction_map = {str(t.id): t for t in transactions}

            for result in results:
                tx_id = str(result.get("transaction_id", ""))
                category_id = result.get("category_id")
                confidence = result.get("confidence", 0)

                # Validate category exists
                if category_id and not user_categories.filter(id=category_id).exists():
                    category_id = None
                    confidence = 0

                should_auto_apply = (
                    confidence >= min_confidence and
                    category_id is not None
                )

                processed_result = {
                    "transaction_id": tx_id,
                    "category_id": category_id,
                    "confidence": confidence,
                    "reasoning": result.get("reasoning", ""),
                    "keywords": result.get("keywords", []),
                    "auto_apply": should_auto_apply,
                    "error": False
                }

                # Auto-apply if requested and confident
                if auto_apply and should_auto_apply and tx_id in transaction_map:
                    tx = transaction_map[tx_id]
                    tx.ai_category_suggestion_id = category_id
                    tx.ai_confidence = confidence
                    tx.save(update_fields=['ai_category_suggestion', 'ai_confidence', 'updated_at'])
                    processed_result['applied'] = True

                processed_results.append(processed_result)

            # Log batch categorization
            self._log_batch_categorization(transactions[0].user, processed_results)

            return processed_results

        except AIServiceError as e:
            logger.error(f"Batch categorization failed: {e}")
            return [{
                "transaction_id": str(t.id),
                "category_id": None,
                "confidence": 0,
                "reasoning": f"Batch categorization failed: {str(e)}",
                "error": True,
                "auto_apply": False
            } for t in transactions]

    def get_category_suggestions(
        self,
        description: str,
        user=None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get multiple category suggestions ranked by relevance.

        Args:
            description: Transaction description to analyze
            user: User instance for category lookup
            limit: Maximum number of suggestions to return

        Returns:
            list: Ranked list of category suggestions with scores
        """
        if not user:
            return []

        # Generate cache key
        cache_key = self._get_cache_key(
            "suggestions",
            user.id,
            hashlib.sha256(description.encode()).hexdigest()
        )

        cached = cache.get(cache_key)
        if cached:
            return cached[:limit]

        user_categories = TransactionCategory.objects.filter(user=user)

        if not user_categories.exists():
            return []

        categories_context = self._format_categories(user_categories)

        messages = [
            {
                "role": "user",
                "content": f"""Analyze this transaction description and suggest the most likely categories:

Description: {description}

Available categories:
{categories_context}

Respond with a JSON array of the top {limit} category suggestions, each with:
- category_id: the category UUID
- category_name: the category name
- score: relevance score (0-1)
- reasoning: brief explanation why this category might fit"""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                temperature=0.3
            )

            suggestions = self._parse_json_response(response)

            if not isinstance(suggestions, list):
                suggestions = suggestions.get("suggestions", [])

            # Validate and filter suggestions
            valid_suggestions = []
            for s in suggestions:
                cat_id = s.get("category_id")
                if cat_id and user_categories.filter(id=cat_id).exists():
                    valid_suggestions.append({
                        "category_id": cat_id,
                        "category_name": s.get("category_name", ""),
                        "score": min(max(s.get("score", 0), 0), 1),
                        "reasoning": s.get("reasoning", "")
                    })

            # Sort by score
            valid_suggestions.sort(key=lambda x: x["score"], reverse=True)

            # Cache results
            cache.set(cache_key, valid_suggestions, self.CACHE_TTL_SUGGESTIONS)

            return valid_suggestions[:limit]

        except AIServiceError as e:
            logger.error(f"Failed to get category suggestions: {e}")
            return []

    def learn_from_correction(
        self,
        transaction: Transaction,
        correct_category: TransactionCategory,
        original_suggestion_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Learn from user correction to improve future categorizations.

        Args:
            transaction: The transaction that was corrected
            correct_category: The correct category chosen by user
            original_suggestion_id: ID of the AI's original suggestion

        Returns:
            dict: Learning result with pattern info
        """
        user = transaction.user

        # Record the correction
        try:
            log = AICategorizationLog.objects.filter(
                transaction=transaction
            ).order_by('-created_at').first()

            if log:
                log.was_accepted = (str(log.suggested_category_id) == str(correct_category.id))
                log.actual_category = correct_category
                log.save()
            else:
                # Create new log for manual categorization
                AICategorizationLog.objects.create(
                    user=user,
                    transaction=transaction,
                    suggested_category=None,
                    confidence_score=0,
                    reasoning="Manual categorization",
                    was_accepted=False,
                    actual_category=correct_category
                )

        except Exception as e:
            logger.warning(f"Failed to update categorization log: {e}")

        # Extract learning patterns
        patterns = self._extract_learning_patterns(transaction, correct_category)

        # Store learned pattern in cache
        self._store_learned_pattern(user, patterns, correct_category)

        # Invalidate related caches
        self._invalidate_categorization_cache(
            transaction.description,
            transaction.merchant,
            transaction.type,
            user.id
        )

        return {
            "learned": True,
            "patterns": patterns,
            "category": str(correct_category.id),
            "category_name": correct_category.name
        }

    def _check_learned_patterns(
        self,
        description: str,
        merchant: Optional[str],
        user
    ) -> Optional[Dict[str, Any]]:
        """Check if we have learned patterns matching this transaction."""
        # Check merchant-based patterns first (highest confidence)
        if merchant:
            merchant_pattern_key = self._get_cache_key(
                "learned_merchant",
                user.id,
                merchant.lower().strip()
            )
            merchant_pattern = cache.get(merchant_pattern_key)
            if merchant_pattern:
                return {
                    "category_id": merchant_pattern["category_id"],
                    "confidence": min(merchant_pattern.get("confidence", 0.9), 0.95),
                    "reasoning": f"Learned from previous categorization of {merchant}",
                    "from_learning": True
                }

        # Check description keyword patterns
        desc_words = set(description.lower().split())
        patterns_key = self._get_cache_key("learned_patterns", user.id)
        patterns = cache.get(patterns_key, {})

        best_match = None
        best_score = 0

        for pattern_key, pattern_data in patterns.items():
            pattern_words = set(pattern_data.get("keywords", []))
            if not pattern_words:
                continue

            # Calculate match score
            intersection = desc_words & pattern_words
            if intersection:
                score = len(intersection) / len(pattern_words)
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = pattern_data

        if best_match:
            return {
                "category_id": best_match["category_id"],
                "confidence": min(best_score * 0.9, 0.85),
                "reasoning": f"Matched learned patterns from similar transactions",
                "from_learning": True
            }

        return None

    def _extract_learning_patterns(
        self,
        transaction: Transaction,
        category: TransactionCategory
    ) -> Dict[str, Any]:
        """Extract learning patterns from a transaction."""
        patterns = {
            "keywords": [],
            "merchant": None,
            "amount_range": None,
        }

        # Extract merchant pattern
        if transaction.merchant:
            patterns["merchant"] = transaction.merchant.lower().strip()

        # Extract description keywords
        if transaction.description:
            words = transaction.description.lower().split()
            # Filter out common words and short words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of'}
            keywords = [w for w in words if len(w) > 2 and w not in stop_words]
            patterns["keywords"] = keywords[:10]

        # Extract amount range
        amount = float(transaction.amount)
        if amount < 10:
            patterns["amount_range"] = "small"
        elif amount < 100:
            patterns["amount_range"] = "medium"
        elif amount < 500:
            patterns["amount_range"] = "large"
        else:
            patterns["amount_range"] = "very_large"

        return patterns

    def _store_learned_pattern(
        self,
        user,
        patterns: Dict[str, Any],
        category: TransactionCategory
    ) -> None:
        """Store learned patterns in cache."""
        try:
            # Store merchant pattern
            if patterns.get("merchant"):
                merchant_key = self._get_cache_key(
                    "learned_merchant",
                    user.id,
                    patterns["merchant"]
                )
                cache.set(merchant_key, {
                    "category_id": str(category.id),
                    "confidence": 0.9,
                    "updated_at": timezone.now().isoformat()
                }, 86400 * 30)  # 30 days

            # Store keyword patterns
            if patterns.get("keywords"):
                patterns_key = self._get_cache_key("learned_patterns", user.id)
                existing = cache.get(patterns_key, {})

                pattern_id = hashlib.sha256(
                    "|".join(sorted(patterns["keywords"])).encode()
                ).hexdigest()[:16]

                existing[pattern_id] = {
                    "category_id": str(category.id),
                    "keywords": patterns["keywords"],
                    "confidence": 0.8,
                    "updated_at": timezone.now().isoformat()
                }

                # Keep only most recent patterns
                if len(existing) > 100:
                    sorted_patterns = sorted(
                        existing.items(),
                        key=lambda x: x[1].get("updated_at", ""),
                        reverse=True
                    )
                    existing = dict(sorted_patterns[:100])

                cache.set(patterns_key, existing, 86400 * 30)

        except Exception as e:
            logger.warning(f"Failed to store learned pattern: {e}")

    def _get_categorization_cache_key(
        self,
        description: str,
        merchant: Optional[str],
        transaction_type: str,
        user_id
    ) -> str:
        """Generate a unique cache key for categorization."""
        content = f"{description}|{merchant or ''}|{transaction_type}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return self._get_cache_key("categorize", user_id, content_hash)

    def _invalidate_categorization_cache(
        self,
        description: str,
        merchant: Optional[str],
        transaction_type: str,
        user_id
    ) -> None:
        """Invalidate categorization cache for a specific pattern."""
        cache_key = self._get_categorization_cache_key(
            description, merchant, transaction_type, user_id
        )
        cache.delete(cache_key)

    def _format_categories(
        self,
        categories: QuerySet[TransactionCategory]
    ) -> str:
        """Format categories for AI context."""
        lines = []
        for cat in categories:
            lines.append(f"- ID: {cat.id}, Name: {cat.name}, Type: {cat.type}")
        return "\n".join(lines) if lines else "No categories available"

    def _format_transaction(self, transaction: Transaction) -> str:
        """Format transaction for AI context."""
        return self._build_transaction_context(
            transaction.description,
            transaction.merchant,
            transaction.amount,
            transaction.type
        )

    def _build_transaction_context(
        self,
        description: str,
        merchant: Optional[str],
        amount: Optional[Decimal],
        transaction_type: str
    ) -> str:
        """Build transaction context string for AI."""
        parts = [f"Type: {transaction_type}"]

        if amount:
            parts.append(f"Amount: {self.format_currency(float(amount))}")

        if merchant:
            parts.append(f"Merchant: {merchant}")

        if description:
            parts.append(f"Description: {description}")

        return "\n".join(parts)

    def _log_batch_categorization(
        self,
        user,
        results: List[Dict[str, Any]]
    ) -> None:
        """Log batch categorization results for analytics."""
        try:
            # Store batch summary in cache for analytics
            today = timezone.now().date().isoformat()
            stats_key = self._get_cache_key("batch_stats", user.id, today)
            stats = cache.get(stats_key, {
                "total": 0,
                "successful": 0,
                "auto_applied": 0,
                "avg_confidence": 0
            })

            confidences = []
            for r in results:
                stats["total"] += 1
                if not r.get("error"):
                    stats["successful"] += 1
                    if r.get("confidence"):
                        confidences.append(r["confidence"])
                if r.get("applied"):
                    stats["auto_applied"] += 1

            if confidences:
                all_conf = stats["avg_confidence"] * (stats["total"] - len(results))
                all_conf += sum(confidences)
                stats["avg_confidence"] = all_conf / stats["total"]

            cache.set(stats_key, stats, 86400 * 7)

        except Exception as e:
            logger.warning(f"Failed to log batch categorization: {e}")

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            "category_id": None,
            "confidence": 0,
            "reasoning": message,
            "error": True,
            "from_cache": False
        }
