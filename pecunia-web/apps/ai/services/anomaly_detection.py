"""
Anomaly Detection Service.

AI-powered detection of unusual spending patterns and anomalies.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum, Count, Avg, StdDev, Max, Min, F, Q
from django.db.models.functions import TruncDate, TruncWeek, ExtractWeekDay
from django.core.cache import cache
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionCategory
from apps.ai.models import AIRecommendation
from .base import BaseAIService, AIServiceError

logger = logging.getLogger(__name__)


class AnomalyDetector(BaseAIService):
    """
    AI-powered anomaly detection service.

    Detects unusual spending patterns, duplicates, and subscription changes
    using statistical analysis combined with AI reasoning.
    """

    # Detection thresholds
    AMOUNT_STDDEV_THRESHOLD = 2.5  # Standard deviations for amount anomaly
    FREQUENCY_THRESHOLD = 3.0  # Times normal frequency for burst detection
    DUPLICATE_TIME_WINDOW_HOURS = 72  # Hours to look for duplicates
    DUPLICATE_AMOUNT_TOLERANCE = 0.01  # 1% tolerance for duplicate amounts

    # Cache configuration
    CACHE_PREFIX = "ai_anomaly"
    CACHE_TTL_PATTERNS = 3600  # 1 hour
    CACHE_TTL_ANALYSIS = 1800  # 30 minutes

    def get_system_prompt(self) -> str:
        """Get the system prompt for anomaly detection."""
        return """You are a financial fraud and anomaly detection AI. Your task is to analyze
transaction data and identify potentially unusual or concerning patterns.

You must respond ONLY with valid JSON in the requested format.

Guidelines:
- Flag transactions that significantly deviate from normal patterns
- Consider merchant changes, amount variations, and timing
- Distinguish between legitimate large purchases and potential fraud
- Be cautious but not alarmist - false positives are costly
- Provide clear explanations for why something seems unusual
- Assign severity: low (informational), medium (review recommended), high (immediate attention)
- Consider context like holidays, pay periods, and seasonal spending
- Look for patterns that suggest subscription changes or price increases"""

    def detect_unusual_spending(
        self,
        user,
        transaction: Transaction,
        save_alert: bool = True,
    ) -> Dict[str, Any]:
        """
        Detect if a transaction represents unusual spending.

        Args:
            user: User instance
            transaction: Transaction to analyze
            save_alert: Whether to save alert to database

        Returns:
            dict: Analysis result with is_unusual flag and details
        """
        # Get user's spending patterns
        patterns = self.get_spending_patterns(user)

        if not patterns.get("has_data"):
            return {
                "is_unusual": False,
                "risk_level": "low",
                "details": "Insufficient data for comparison",
                "confidence": 0
            }

        # Statistical analysis
        amount = float(transaction.amount)
        category = transaction.category

        # Check amount anomaly
        is_amount_anomaly, amount_details = self._check_amount_anomaly(
            amount, patterns, category
        )

        # Check timing anomaly
        is_timing_anomaly, timing_details = self._check_timing_anomaly(
            transaction, patterns
        )

        # Check merchant anomaly
        is_merchant_anomaly, merchant_details = self._check_merchant_anomaly(
            user, transaction
        )

        # Combine flags
        anomaly_flags = {
            "amount": is_amount_anomaly,
            "timing": is_timing_anomaly,
            "merchant": is_merchant_anomaly
        }

        # If any flag, use AI for detailed analysis
        if any(anomaly_flags.values()):
            ai_analysis = self._ai_analyze_transaction(
                transaction, patterns, anomaly_flags, {
                    "amount": amount_details,
                    "timing": timing_details,
                    "merchant": merchant_details
                }
            )

            # Save alert if unusual and requested
            if save_alert and ai_analysis.get("is_unusual"):
                self._save_anomaly_alert(user, transaction, ai_analysis)

            return ai_analysis

        return {
            "is_unusual": False,
            "risk_level": "low",
            "details": "Transaction appears normal",
            "confidence": 0.95,
            "checks_passed": ["amount", "timing", "merchant"]
        }

    def detect_duplicate_transactions(
        self,
        user,
        lookback_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Detect potential duplicate transactions.

        Args:
            user: User instance
            lookback_days: Number of days to look back

        Returns:
            list: List of potential duplicate groups
        """
        cache_key = self._get_cache_key("duplicates", user.id)
        cached = cache.get(cache_key)
        if cached:
            return cached

        cutoff_date = timezone.now().date() - timedelta(days=lookback_days)

        transactions = Transaction.objects.filter(
            user=user,
            transaction_date__gte=cutoff_date
        ).order_by('transaction_date', 'amount')

        # Group potential duplicates
        duplicate_groups = []
        checked_ids = set()

        for tx in transactions:
            if tx.id in checked_ids:
                continue

            # Find potential duplicates
            potential_duplicates = self._find_potential_duplicates(tx, transactions)

            if potential_duplicates:
                group = {
                    "primary": self._transaction_to_dict(tx),
                    "duplicates": [
                        self._transaction_to_dict(d) for d in potential_duplicates
                    ],
                    "duplicate_count": len(potential_duplicates),
                    "total_amount": float(
                        tx.amount + sum(d.amount for d in potential_duplicates)
                    ),
                    "confidence": self._calculate_duplicate_confidence(
                        tx, potential_duplicates
                    )
                }
                duplicate_groups.append(group)

                checked_ids.add(tx.id)
                for d in potential_duplicates:
                    checked_ids.add(d.id)

        # Sort by confidence
        duplicate_groups.sort(key=lambda x: x["confidence"], reverse=True)

        # Use AI to validate high-confidence duplicates
        if duplicate_groups:
            duplicate_groups = self._ai_validate_duplicates(duplicate_groups[:20])

        cache.set(cache_key, duplicate_groups, self.CACHE_TTL_ANALYSIS)
        return duplicate_groups

    def detect_subscription_changes(
        self,
        user,
        lookback_months: int = 3,
    ) -> Dict[str, Any]:
        """
        Detect changes in recurring subscription patterns.

        Args:
            user: User instance
            lookback_months: Number of months to analyze

        Returns:
            dict: Subscription analysis with changes detected
        """
        cache_key = self._get_cache_key("subscriptions", user.id)
        cached = cache.get(cache_key)
        if cached:
            return cached

        cutoff_date = timezone.now().date() - timedelta(days=lookback_months * 30)

        # Get recurring transactions
        recurring_transactions = Transaction.objects.filter(
            user=user,
            transaction_date__gte=cutoff_date,
            is_recurring=True
        ).order_by('merchant', 'transaction_date')

        if not recurring_transactions.exists():
            # Try to identify subscriptions by pattern
            recurring_transactions = self._identify_recurring_patterns(user, cutoff_date)

        # Group by merchant/description
        subscription_groups = defaultdict(list)
        for tx in recurring_transactions:
            key = tx.merchant or tx.description[:50]
            subscription_groups[key].append(tx)

        # Analyze each subscription
        changes = []
        for key, txs in subscription_groups.items():
            if len(txs) >= 2:
                change = self._analyze_subscription_changes(key, txs)
                if change:
                    changes.append(change)

        result = {
            "subscription_count": len(subscription_groups),
            "changes_detected": len(changes),
            "changes": changes,
            "total_monthly_subscriptions": self._calculate_monthly_subscription_cost(
                subscription_groups
            ),
            "analyzed_at": timezone.now().isoformat()
        }

        cache.set(cache_key, result, self.CACHE_TTL_ANALYSIS)
        return result

    def get_spending_patterns(
        self,
        user,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get user's spending patterns for anomaly detection.

        Args:
            user: User instance
            use_cache: Whether to use cached patterns

        Returns:
            dict: Comprehensive spending patterns
        """
        cache_key = self._get_cache_key("patterns", user.id)

        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                return cached

        # Get last 90 days of data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)

        transactions = Transaction.objects.filter(
            user=user,
            type='expense',
            transaction_date__gte=start_date
        )

        if not transactions.exists():
            return {"has_data": False}

        # Overall statistics
        overall_stats = transactions.aggregate(
            avg_amount=Avg('amount'),
            stddev_amount=StdDev('amount'),
            max_amount=Max('amount'),
            min_amount=Min('amount'),
            total_count=Count('id'),
            total_amount=Sum('amount')
        )

        # Daily spending patterns
        daily_stats = transactions.annotate(
            date=TruncDate('transaction_date')
        ).values('date').annotate(
            daily_total=Sum('amount'),
            daily_count=Count('id')
        ).aggregate(
            avg_daily=Avg('daily_total'),
            stddev_daily=StdDev('daily_total'),
            avg_tx_per_day=Avg('daily_count')
        )

        # Weekly patterns (day of week)
        weekday_stats = transactions.annotate(
            weekday=ExtractWeekDay('transaction_date')
        ).values('weekday').annotate(
            avg_amount=Avg('amount'),
            count=Count('id')
        ).order_by('weekday')

        # Category patterns
        category_stats = transactions.values(
            'category__id', 'category__name'
        ).annotate(
            avg_amount=Avg('amount'),
            stddev_amount=StdDev('amount'),
            max_amount=Max('amount'),
            total=Sum('amount'),
            count=Count('id')
        )

        # Merchant frequency
        merchant_stats = transactions.exclude(
            merchant__isnull=True
        ).exclude(
            merchant=''
        ).values('merchant').annotate(
            count=Count('id'),
            avg_amount=Avg('amount'),
            total=Sum('amount')
        ).order_by('-count')[:50]

        patterns = {
            "has_data": True,
            "period_days": 90,
            "overall": {
                "avg_amount": float(overall_stats['avg_amount'] or 0),
                "stddev_amount": float(overall_stats['stddev_amount'] or 0),
                "max_amount": float(overall_stats['max_amount'] or 0),
                "min_amount": float(overall_stats['min_amount'] or 0),
                "total_transactions": overall_stats['total_count'] or 0,
                "total_spending": float(overall_stats['total_amount'] or 0)
            },
            "daily": {
                "avg_daily_spending": float(daily_stats['avg_daily'] or 0),
                "stddev_daily_spending": float(daily_stats['stddev_daily'] or 0),
                "avg_transactions_per_day": float(daily_stats['avg_tx_per_day'] or 0)
            },
            "by_weekday": {
                item['weekday']: {
                    "avg_amount": float(item['avg_amount']),
                    "count": item['count']
                } for item in weekday_stats
            },
            "by_category": {
                str(item['category__id']): {
                    "name": item['category__name'],
                    "avg_amount": float(item['avg_amount'] or 0),
                    "stddev_amount": float(item['stddev_amount'] or 0),
                    "max_amount": float(item['max_amount'] or 0),
                    "total": float(item['total'] or 0),
                    "count": item['count']
                } for item in category_stats if item['category__id']
            },
            "merchants": {
                item['merchant']: {
                    "count": item['count'],
                    "avg_amount": float(item['avg_amount']),
                    "total": float(item['total'])
                } for item in merchant_stats
            },
            "generated_at": timezone.now().isoformat()
        }

        cache.set(cache_key, patterns, self.CACHE_TTL_PATTERNS)
        return patterns

    def _check_amount_anomaly(
        self,
        amount: float,
        patterns: Dict[str, Any],
        category: Optional[TransactionCategory]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if amount is anomalous."""
        details = {"checks": []}

        # Check against overall patterns
        overall = patterns.get("overall", {})
        avg = overall.get("avg_amount", 0)
        stddev = overall.get("stddev_amount", 0)

        if stddev > 0:
            z_score = (amount - avg) / stddev
            details["z_score_overall"] = round(z_score, 2)
            details["checks"].append(f"Overall z-score: {z_score:.2f}")

            if z_score > self.AMOUNT_STDDEV_THRESHOLD:
                details["reason"] = f"Amount is {z_score:.1f} standard deviations above average"
                return True, details

        # Check against category patterns
        if category:
            cat_patterns = patterns.get("by_category", {}).get(str(category.id), {})
            if cat_patterns:
                cat_avg = cat_patterns.get("avg_amount", 0)
                cat_stddev = cat_patterns.get("stddev_amount", 0)
                cat_max = cat_patterns.get("max_amount", 0)

                if cat_stddev > 0:
                    cat_z_score = (amount - cat_avg) / cat_stddev
                    details["z_score_category"] = round(cat_z_score, 2)
                    details["checks"].append(f"Category z-score: {cat_z_score:.2f}")

                    if cat_z_score > self.AMOUNT_STDDEV_THRESHOLD:
                        details["reason"] = (
                            f"Amount is {cat_z_score:.1f} standard deviations "
                            f"above category average"
                        )
                        return True, details

                if amount > cat_max * 1.5:
                    details["reason"] = f"Amount exceeds 150% of category maximum"
                    return True, details

        return False, details

    def _check_timing_anomaly(
        self,
        transaction: Transaction,
        patterns: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if transaction timing is anomalous."""
        details = {"checks": []}

        # Check day of week patterns
        tx_date = transaction.transaction_date
        if hasattr(tx_date, 'isoweekday'):
            weekday = tx_date.isoweekday()
        else:
            weekday = tx_date.weekday() + 1

        weekday_patterns = patterns.get("by_weekday", {})
        weekday_data = weekday_patterns.get(weekday, {})

        if weekday_data:
            avg_count = weekday_data.get("count", 0)
            details["weekday_avg_count"] = avg_count
            details["checks"].append(f"Weekday {weekday} average count: {avg_count}")

        # Check for unusual time of month patterns
        day_of_month = tx_date.day
        if day_of_month > 28:
            details["checks"].append("End of month transaction")

        return False, details

    def _check_merchant_anomaly(
        self,
        user,
        transaction: Transaction
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if merchant is new or unusual."""
        details = {"checks": []}

        if not transaction.merchant:
            return False, details

        merchant = transaction.merchant.lower().strip()

        # Check if new merchant
        previous_transactions = Transaction.objects.filter(
            user=user,
            merchant__iexact=merchant,
            transaction_date__lt=transaction.transaction_date
        ).exists()

        if not previous_transactions:
            details["is_new_merchant"] = True
            details["checks"].append("First transaction with this merchant")

            # Flag if large amount with new merchant
            if float(transaction.amount) > 100:
                details["reason"] = f"Large amount ({transaction.amount}) with new merchant"
                return True, details

        return False, details

    def _ai_analyze_transaction(
        self,
        transaction: Transaction,
        patterns: Dict[str, Any],
        anomaly_flags: Dict[str, bool],
        check_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to analyze flagged transaction."""
        context = f"""Analyze this transaction for potential anomalies:

Transaction:
- Amount: {self.format_currency(float(transaction.amount))}
- Merchant: {transaction.merchant or 'Unknown'}
- Category: {transaction.category.name if transaction.category else 'Uncategorized'}
- Date: {transaction.transaction_date}
- Description: {transaction.description}

Flags raised:
- Amount anomaly: {anomaly_flags['amount']} - {check_details.get('amount', {}).get('reason', 'N/A')}
- Timing anomaly: {anomaly_flags['timing']}
- New/unusual merchant: {anomaly_flags['merchant']}

User's spending patterns:
- Average transaction: {self.format_currency(patterns['overall']['avg_amount'])}
- Std deviation: {self.format_currency(patterns['overall']['stddev_amount'])}
- Max transaction: {self.format_currency(patterns['overall']['max_amount'])}
- Daily average: {self.format_currency(patterns['daily']['avg_daily_spending'])}"""

        messages = [
            {
                "role": "user",
                "content": f"""{context}

Analyze this and respond with JSON:
{{
    "is_unusual": true/false,
    "risk_level": "low/medium/high",
    "confidence": 0.0-1.0,
    "explanation": "detailed explanation",
    "recommended_action": "what user should do",
    "false_positive_likelihood": "low/medium/high"
}}"""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                temperature=0.2
            )

            result = self._parse_json_response(response)
            result["anomaly_flags"] = anomaly_flags
            result["check_details"] = check_details
            return result

        except AIServiceError as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "is_unusual": any(anomaly_flags.values()),
                "risk_level": "medium",
                "confidence": 0.5,
                "explanation": "Unable to complete AI analysis",
                "error": str(e),
                "anomaly_flags": anomaly_flags
            }

    def _find_potential_duplicates(
        self,
        transaction: Transaction,
        all_transactions
    ) -> List[Transaction]:
        """Find potential duplicates of a transaction."""
        duplicates = []
        tx_date = transaction.transaction_date
        tx_amount = float(transaction.amount)

        for other in all_transactions:
            if other.id == transaction.id:
                continue

            # Check date proximity
            date_diff = abs((other.transaction_date - tx_date).days)
            if date_diff > 3:  # More than 3 days apart
                continue

            # Check amount similarity
            other_amount = float(other.amount)
            if tx_amount == 0 or other_amount == 0:
                continue

            amount_diff = abs(tx_amount - other_amount) / max(tx_amount, other_amount)
            if amount_diff > self.DUPLICATE_AMOUNT_TOLERANCE:
                continue

            # Check merchant/description similarity
            if transaction.merchant and other.merchant:
                if transaction.merchant.lower() != other.merchant.lower():
                    continue
            elif transaction.description and other.description:
                # Check description similarity
                desc1 = transaction.description.lower()[:50]
                desc2 = other.description.lower()[:50]
                if desc1 != desc2:
                    continue
            else:
                continue

            duplicates.append(other)

        return duplicates

    def _calculate_duplicate_confidence(
        self,
        primary: Transaction,
        duplicates: List[Transaction]
    ) -> float:
        """Calculate confidence score for duplicate detection."""
        if not duplicates:
            return 0

        base_confidence = 0.5

        # Same exact amount
        if all(d.amount == primary.amount for d in duplicates):
            base_confidence += 0.2

        # Same merchant
        if primary.merchant and all(
            d.merchant and d.merchant.lower() == primary.merchant.lower()
            for d in duplicates
        ):
            base_confidence += 0.2

        # Close dates
        dates = [primary.transaction_date] + [d.transaction_date for d in duplicates]
        date_range = (max(dates) - min(dates)).days
        if date_range <= 1:
            base_confidence += 0.1

        return min(base_confidence, 0.95)

    def _ai_validate_duplicates(
        self,
        duplicate_groups: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use AI to validate duplicate detection."""
        if not duplicate_groups:
            return []

        # Format for AI
        groups_text = "\n\n".join([
            f"Group {i+1}:\n"
            f"- Primary: {g['primary']['amount']} at {g['primary']['merchant']} on {g['primary']['date']}\n"
            f"- Duplicates: {len(g['duplicates'])} transactions\n"
            f"- Total: {g['total_amount']}"
            for i, g in enumerate(duplicate_groups[:10])
        ])

        messages = [
            {
                "role": "user",
                "content": f"""Analyze these potential duplicate transaction groups:

{groups_text}

For each group, determine if they are likely true duplicates (same transaction posted multiple times) or legitimate separate transactions.

Respond with JSON array:
[
    {{
        "group_index": 0,
        "is_likely_duplicate": true/false,
        "confidence": 0.0-1.0,
        "reasoning": "explanation"
    }}
]"""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                temperature=0.2
            )

            validations = self._parse_json_response(response)

            # Update groups with AI validation
            for v in validations:
                idx = v.get("group_index", 0)
                if idx < len(duplicate_groups):
                    duplicate_groups[idx]["ai_validation"] = {
                        "is_likely_duplicate": v.get("is_likely_duplicate", True),
                        "ai_confidence": v.get("confidence", 0.5),
                        "reasoning": v.get("reasoning", "")
                    }

        except AIServiceError as e:
            logger.warning(f"AI duplicate validation failed: {e}")

        return duplicate_groups

    def _identify_recurring_patterns(
        self,
        user,
        cutoff_date
    ) -> List[Transaction]:
        """Identify recurring transactions by pattern analysis."""
        transactions = Transaction.objects.filter(
            user=user,
            type='expense',
            transaction_date__gte=cutoff_date
        ).exclude(
            merchant__isnull=True
        ).exclude(
            merchant=''
        )

        # Group by merchant and look for patterns
        merchant_groups = defaultdict(list)
        for tx in transactions:
            merchant_groups[tx.merchant.lower()].append(tx)

        recurring = []
        for merchant, txs in merchant_groups.items():
            if len(txs) >= 2:
                # Check for amount consistency
                amounts = [float(tx.amount) for tx in txs]
                if len(set(amounts)) == 1 or (
                    max(amounts) - min(amounts)
                ) / max(amounts) < 0.05:
                    recurring.extend(txs)

        return recurring

    def _analyze_subscription_changes(
        self,
        key: str,
        transactions: List[Transaction]
    ) -> Optional[Dict[str, Any]]:
        """Analyze a subscription for changes."""
        if len(transactions) < 2:
            return None

        amounts = [float(tx.amount) for tx in transactions]
        dates = [tx.transaction_date for tx in transactions]

        # Check for amount changes
        if len(set(amounts)) > 1:
            old_amount = amounts[0]
            new_amount = amounts[-1]
            change_percent = ((new_amount - old_amount) / old_amount) * 100

            if abs(change_percent) >= 5:  # 5% change threshold
                return {
                    "subscription": key,
                    "change_type": "price_increase" if change_percent > 0 else "price_decrease",
                    "old_amount": old_amount,
                    "new_amount": new_amount,
                    "change_percent": round(change_percent, 1),
                    "first_seen": dates[0].isoformat(),
                    "last_seen": dates[-1].isoformat(),
                    "transaction_count": len(transactions)
                }

        # Check for frequency changes
        if len(transactions) >= 3:
            intervals = [
                (dates[i+1] - dates[i]).days
                for i in range(len(dates) - 1)
            ]
            avg_interval = sum(intervals) / len(intervals)
            last_interval = intervals[-1]

            if abs(last_interval - avg_interval) > avg_interval * 0.5:
                return {
                    "subscription": key,
                    "change_type": "frequency_change",
                    "avg_interval_days": round(avg_interval, 1),
                    "last_interval_days": last_interval,
                    "current_amount": amounts[-1],
                    "transaction_count": len(transactions)
                }

        return None

    def _calculate_monthly_subscription_cost(
        self,
        subscription_groups: Dict[str, List[Transaction]]
    ) -> float:
        """Calculate estimated monthly subscription cost."""
        total = 0

        for key, txs in subscription_groups.items():
            if len(txs) < 2:
                continue

            # Get latest amount
            latest_amount = float(txs[-1].amount)

            # Estimate frequency
            dates = [tx.transaction_date for tx in txs]
            avg_days = sum(
                (dates[i+1] - dates[i]).days
                for i in range(len(dates) - 1)
            ) / (len(dates) - 1)

            # Convert to monthly
            monthly_multiplier = 30 / avg_days if avg_days > 0 else 1
            total += latest_amount * monthly_multiplier

        return round(total, 2)

    def _transaction_to_dict(self, transaction: Transaction) -> Dict[str, Any]:
        """Convert transaction to dict for serialization."""
        return {
            "id": str(transaction.id),
            "amount": float(transaction.amount),
            "merchant": transaction.merchant,
            "description": transaction.description,
            "date": transaction.transaction_date.isoformat(),
            "category": transaction.category.name if transaction.category else None
        }

    def _save_anomaly_alert(
        self,
        user,
        transaction: Transaction,
        analysis: Dict[str, Any]
    ) -> None:
        """Save anomaly alert to database."""
        try:
            risk_to_priority = {
                "low": "low",
                "medium": "medium",
                "high": "urgent"
            }

            AIRecommendation.objects.create(
                user=user,
                type='anomaly',
                title=f"Unusual Transaction: {self.format_currency(float(transaction.amount))}",
                content=analysis.get("explanation", "Unusual spending pattern detected"),
                priority=risk_to_priority.get(
                    analysis.get("risk_level", "medium"),
                    "medium"
                ),
                related_transaction=transaction,
                related_category=transaction.category,
                confidence_score=analysis.get("confidence"),
                metadata={
                    "risk_level": analysis.get("risk_level"),
                    "anomaly_flags": analysis.get("anomaly_flags", {}),
                    "recommended_action": analysis.get("recommended_action"),
                    "detected_at": timezone.now().isoformat()
                },
                expires_at=timezone.now() + timedelta(days=7)
            )

            logger.info(f"Saved anomaly alert for transaction {transaction.id}")

        except Exception as e:
            logger.error(f"Failed to save anomaly alert: {e}")
