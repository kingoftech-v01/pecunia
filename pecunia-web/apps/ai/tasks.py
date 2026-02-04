"""
AI Celery Tasks.

Background tasks for AI-powered transaction categorization,
anomaly detection, and recommendation generation.
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from celery import shared_task, group, chain
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Transaction Categorization Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.ai.tasks.categorize_new_transactions',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    soft_time_limit=900,
    time_limit=1000,
)
def categorize_new_transactions(
    self,
    user_id: int,
    batch_size: int = 50,
    min_confidence: float = 0.75,
    auto_apply: bool = False,
) -> Dict[str, Any]:
    """
    Categorize uncategorized transactions using AI.

    This task finds transactions without categories and uses the
    AI categorization service to suggest appropriate categories.

    Args:
        self: Task instance (bound task)
        user_id: User ID whose transactions to categorize (required)
        batch_size: Number of transactions to process per batch
        min_confidence: Minimum confidence for auto-apply
        auto_apply: Whether to automatically apply high-confidence categories

    Returns:
        Dict containing categorization results
    """
    from django.contrib.auth import get_user_model
    from apps.transactions.models import Transaction, TransactionCategory
    from apps.ai.services.categorization import TransactionCategorizer

    if not user_id:
        raise ValueError("user_id is required to prevent cross-tenant data access")

    logger.info(
        f"Starting transaction categorization - user_id={user_id}, "
        f"batch_size={batch_size}, auto_apply={auto_apply}",
        extra={'task_id': self.request.id}
    )

    results = {
        'processed': 0,
        'categorized': 0,
        'auto_applied': 0,
        'errors': [],
        'started_at': timezone.now().isoformat(),
    }

    try:
        User = get_user_model()

        # Build query for uncategorized transactions scoped to user
        transactions_qs = Transaction.objects.filter(
            category__isnull=True,
            user_id=user_id,
        ).select_related('user')

        # Order by most recent first
        transactions_qs = transactions_qs.order_by('-transaction_date')

        # Get total count
        total_uncategorized = transactions_qs.count()
        logger.info(f"Found {total_uncategorized} uncategorized transactions")

        if total_uncategorized == 0:
            results['status'] = 'no_transactions'
            results['message'] = 'No uncategorized transactions found'
            return results

        # Process in batches grouped by user
        users_processed = set()
        offset = 0

        while offset < min(total_uncategorized, batch_size * 10):  # Limit total processing
            batch = list(transactions_qs[offset:offset + batch_size])

            if not batch:
                break

            # Group by user for efficient processing
            user_batches = {}
            for tx in batch:
                if tx.user_id not in user_batches:
                    user_batches[tx.user_id] = []
                user_batches[tx.user_id].append(tx)

            for uid, user_transactions in user_batches.items():
                try:
                    user = user_transactions[0].user
                    users_processed.add(uid)

                    # Initialize categorizer
                    categorizer = TransactionCategorizer()

                    # Categorize batch
                    batch_results = categorizer.categorize_batch(
                        transactions=user_transactions,
                        min_confidence=min_confidence,
                        auto_apply=auto_apply
                    )

                    # Update results
                    for br in batch_results:
                        results['processed'] += 1
                        if br.get('category_id') and not br.get('error'):
                            results['categorized'] += 1
                            if br.get('applied'):
                                results['auto_applied'] += 1

                except Exception as e:
                    logger.error(f"Error categorizing for user {uid}: {e}")
                    results['errors'].append({
                        'user_id': uid,
                        'error': str(e)
                    })

            offset += batch_size

        results['users_processed'] = len(users_processed)
        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'completed'

        logger.info(
            f"Transaction categorization completed - processed: {results['processed']}, "
            f"categorized: {results['categorized']}, auto_applied: {results['auto_applied']}",
            extra={'task_id': self.request.id, 'results': results}
        )

        return results

    except SoftTimeLimitExceeded:
        logger.error("Transaction categorization exceeded time limit")
        results['status'] = 'timeout'
        results['completed_at'] = timezone.now().isoformat()
        return results

    except Exception as e:
        logger.exception(f"Transaction categorization failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='apps.ai.tasks.categorize_user_transactions',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=300,
)
def categorize_user_transactions(
    self,
    user_id: int,
    transaction_ids: Optional[List[str]] = None,
    auto_apply: bool = True,
) -> Dict[str, Any]:
    """
    Categorize specific transactions for a user.

    Args:
        self: Task instance (bound task)
        user_id: User ID
        transaction_ids: Optional list of specific transaction IDs
        auto_apply: Whether to auto-apply high-confidence categories

    Returns:
        Dict with categorization results
    """
    from django.contrib.auth import get_user_model
    from apps.transactions.models import Transaction
    from apps.ai.services.categorization import TransactionCategorizer

    logger.info(
        f"Categorizing transactions for user {user_id}",
        extra={'task_id': self.request.id}
    )

    results = {
        'user_id': user_id,
        'processed': 0,
        'categorized': 0,
        'results': [],
    }

    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)

        # Get transactions
        if transaction_ids:
            transactions = list(Transaction.objects.filter(
                user=user,
                id__in=transaction_ids
            ))
        else:
            transactions = list(Transaction.objects.filter(
                user=user,
                category__isnull=True
            ).order_by('-transaction_date')[:50])

        if not transactions:
            results['status'] = 'no_transactions'
            return results

        categorizer = TransactionCategorizer()
        batch_results = categorizer.categorize_batch(
            transactions=transactions,
            auto_apply=auto_apply
        )

        for br in batch_results:
            results['processed'] += 1
            if br.get('category_id') and not br.get('error'):
                results['categorized'] += 1
            results['results'].append(br)

        results['status'] = 'completed'

        logger.info(
            f"User categorization completed - {results['categorized']}/{results['processed']} categorized",
            extra={'task_id': self.request.id}
        )

        return results

    except Exception as e:
        logger.error(f"User categorization failed: {e}")
        raise


# =============================================================================
# Anomaly Detection Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.ai.tasks.check_anomalies_daily',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=1800,
    time_limit=2000,
)
def check_anomalies_daily(
    self,
    user_id: int,
    lookback_days: int = 7,
    save_alerts: bool = True,
) -> Dict[str, Any]:
    """
    Daily anomaly detection check for a specific user.

    Analyzes recent transactions for unusual patterns and
    generates alerts for detected anomalies.

    Args:
        self: Task instance (bound task)
        user_id: User ID to check (required)
        lookback_days: Number of days to analyze
        save_alerts: Whether to save alerts to database

    Returns:
        Dict containing detection results
    """
    from django.contrib.auth import get_user_model
    from apps.transactions.models import Transaction
    from apps.ai.services.anomaly_detection import AnomalyDetector

    if not user_id:
        raise ValueError("user_id is required to prevent cross-tenant data access")

    logger.info(
        f"Starting daily anomaly check - user_id={user_id}, lookback_days={lookback_days}",
        extra={'task_id': self.request.id}
    )

    results = {
        'users_checked': 0,
        'anomalies_detected': 0,
        'alerts_created': 0,
        'errors': [],
        'started_at': timezone.now().isoformat(),
    }

    try:
        User = get_user_model()

        # Get user to check - scoped to single user
        users = User.objects.filter(id=user_id, is_active=True)

        detector = AnomalyDetector()

        for user in users:
            try:
                # Get recent transactions
                cutoff = timezone.now().date() - timedelta(days=lookback_days)
                recent_transactions = Transaction.objects.filter(
                    user=user,
                    transaction_date__gte=cutoff,
                    type='expense'
                ).select_related('category')

                results['users_checked'] += 1

                # Check each transaction
                for tx in recent_transactions:
                    analysis = detector.detect_unusual_spending(
                        user=user,
                        transaction=tx,
                        save_alert=save_alerts
                    )

                    if analysis.get('is_unusual'):
                        results['anomalies_detected'] += 1
                        if save_alerts:
                            results['alerts_created'] += 1

                # Also check for duplicates
                duplicates = detector.detect_duplicate_transactions(
                    user=user,
                    lookback_days=lookback_days
                )

                if duplicates:
                    logger.info(
                        f"Found {len(duplicates)} potential duplicate groups for user {user.id}"
                    )

            except Exception as e:
                logger.error(f"Error checking anomalies for user {user.id}: {e}")
                results['errors'].append({
                    'user_id': user.id,
                    'error': str(e)
                })

        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'completed'

        logger.info(
            f"Daily anomaly check completed - {results['users_checked']} users, "
            f"{results['anomalies_detected']} anomalies, {results['alerts_created']} alerts",
            extra={'task_id': self.request.id, 'results': results}
        )

        return results

    except SoftTimeLimitExceeded:
        logger.error("Anomaly check exceeded time limit")
        results['status'] = 'timeout'
        return results

    except Exception as e:
        logger.exception(f"Anomaly check failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='apps.ai.tasks.check_single_transaction_anomaly',
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=60,
)
def check_single_transaction_anomaly(
    self,
    transaction_id: str,
    save_alert: bool = True,
) -> Dict[str, Any]:
    """
    Check a single transaction for anomalies.

    Typically called after a new transaction is created.

    Args:
        self: Task instance (bound task)
        transaction_id: Transaction UUID
        save_alert: Whether to save alert if anomaly detected

    Returns:
        Dict with analysis results
    """
    from apps.transactions.models import Transaction
    from apps.ai.services.anomaly_detection import AnomalyDetector

    logger.info(
        f"Checking transaction {transaction_id} for anomalies",
        extra={'task_id': self.request.id}
    )

    try:
        transaction = Transaction.objects.select_related(
            'user', 'category'
        ).get(id=transaction_id)

        detector = AnomalyDetector()
        analysis = detector.detect_unusual_spending(
            user=transaction.user,
            transaction=transaction,
            save_alert=save_alert
        )

        analysis['transaction_id'] = transaction_id
        analysis['checked_at'] = timezone.now().isoformat()

        if analysis.get('is_unusual'):
            logger.warning(
                f"Anomaly detected in transaction {transaction_id}: "
                f"{analysis.get('risk_level')} risk",
                extra={'task_id': self.request.id}
            )

        return analysis

    except Transaction.DoesNotExist:
        logger.warning(f"Transaction {transaction_id} not found")
        return {'error': 'Transaction not found', 'transaction_id': transaction_id}

    except Exception as e:
        logger.error(f"Anomaly check failed for {transaction_id}: {e}")
        raise


@shared_task(
    bind=True,
    name='apps.ai.tasks.detect_subscription_changes',
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=600,
)
def detect_subscription_changes(
    self,
    user_id: int,
) -> Dict[str, Any]:
    """
    Detect changes in recurring subscriptions.

    Args:
        self: Task instance (bound task)
        user_id: User ID to check (required)

    Returns:
        Dict with subscription change analysis
    """
    from django.contrib.auth import get_user_model
    from apps.ai.services.anomaly_detection import AnomalyDetector

    if not user_id:
        raise ValueError("user_id is required to prevent cross-tenant data access")

    logger.info(
        f"Detecting subscription changes - user_id={user_id}",
        extra={'task_id': self.request.id}
    )

    results = {
        'users_checked': 0,
        'total_changes': 0,
        'changes_by_user': {},
        'started_at': timezone.now().isoformat(),
    }

    try:
        User = get_user_model()

        users = User.objects.filter(id=user_id, is_active=True)

        detector = AnomalyDetector()

        for user in users:
            try:
                changes = detector.detect_subscription_changes(
                    user=user,
                    lookback_months=3
                )

                results['users_checked'] += 1
                change_count = changes.get('changes_detected', 0)
                results['total_changes'] += change_count

                if change_count > 0:
                    results['changes_by_user'][user.id] = changes['changes']

            except Exception as e:
                logger.error(f"Error checking subscriptions for user {user.id}: {e}")

        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'completed'

        logger.info(
            f"Subscription check completed - {results['total_changes']} changes detected",
            extra={'task_id': self.request.id}
        )

        return results

    except Exception as e:
        logger.exception(f"Subscription detection failed: {e}")
        raise self.retry(exc=e)


# =============================================================================
# Recommendation Generation Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.ai.tasks.generate_weekly_recommendations',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=3600,
    time_limit=3900,
)
def generate_weekly_recommendations(
    self,
    user_id: int,
    num_recommendations: int = 5,
) -> Dict[str, Any]:
    """
    Generate weekly recommendations for a specific user.

    This task runs weekly to provide fresh budget and saving
    recommendations based on recent spending patterns.

    Args:
        self: Task instance (bound task)
        user_id: User ID to generate recommendations for (required)
        num_recommendations: Number of recommendations per user

    Returns:
        Dict containing generation results
    """
    from django.contrib.auth import get_user_model
    from apps.transactions.models import Transaction
    from apps.ai.services.recommendations import RecommendationEngine

    if not user_id:
        raise ValueError("user_id is required to prevent cross-tenant data access")

    logger.info(
        f"Starting weekly recommendation generation - user_id={user_id}",
        extra={'task_id': self.request.id}
    )

    results = {
        'users_processed': 0,
        'recommendations_generated': 0,
        'errors': [],
        'started_at': timezone.now().isoformat(),
    }

    try:
        User = get_user_model()

        # Get specific user to generate recommendations for
        users = User.objects.filter(id=user_id, is_active=True)

        engine = RecommendationEngine()

        for user in users:
            try:
                recommendations = engine.generate_budget_recommendations(
                    user=user,
                    num_recommendations=num_recommendations,
                    save_to_db=True
                )

                results['users_processed'] += 1
                results['recommendations_generated'] += len(recommendations)

                logger.debug(
                    f"Generated {len(recommendations)} recommendations for user {user.id}"
                )

            except Exception as e:
                logger.error(f"Error generating recommendations for user {user.id}: {e}")
                results['errors'].append({
                    'user_id': user.id,
                    'error': str(e)
                })

        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'completed'

        logger.info(
            f"Weekly recommendations completed - {results['users_processed']} users, "
            f"{results['recommendations_generated']} recommendations",
            extra={'task_id': self.request.id, 'results': results}
        )

        return results

    except SoftTimeLimitExceeded:
        logger.error("Recommendation generation exceeded time limit")
        results['status'] = 'timeout'
        return results

    except Exception as e:
        logger.exception(f"Recommendation generation failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='apps.ai.tasks.generate_user_recommendations',
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=120,
)
def generate_user_recommendations(
    self,
    user_id: int,
    recommendation_type: str = 'all',
) -> Dict[str, Any]:
    """
    Generate recommendations for a specific user.

    Args:
        self: Task instance (bound task)
        user_id: User ID
        recommendation_type: 'budget', 'saving', 'monthly', or 'all'

    Returns:
        Dict with generated recommendations
    """
    from django.contrib.auth import get_user_model
    from apps.ai.services.recommendations import RecommendationEngine

    logger.info(
        f"Generating {recommendation_type} recommendations for user {user_id}",
        extra={'task_id': self.request.id}
    )

    results = {
        'user_id': user_id,
        'recommendations': {},
    }

    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)

        engine = RecommendationEngine()

        if recommendation_type in ('budget', 'all'):
            budget_recs = engine.generate_budget_recommendations(
                user=user,
                save_to_db=True
            )
            results['recommendations']['budget'] = budget_recs

        if recommendation_type in ('saving', 'all'):
            saving_tips = engine.generate_saving_tips(user=user)
            results['recommendations']['saving_tips'] = saving_tips

        if recommendation_type in ('monthly', 'all'):
            monthly_insights = engine.generate_monthly_insights(
                user=user,
                save_to_db=True
            )
            results['recommendations']['monthly_insights'] = monthly_insights

        results['status'] = 'completed'
        results['generated_at'] = timezone.now().isoformat()

        total_recs = sum(
            len(v) if isinstance(v, list) else 1
            for v in results['recommendations'].values()
        )
        logger.info(
            f"Generated {total_recs} recommendations for user {user_id}",
            extra={'task_id': self.request.id}
        )

        return results

    except Exception as e:
        logger.error(f"User recommendation generation failed: {e}")
        raise


@shared_task(
    bind=True,
    name='apps.ai.tasks.generate_monthly_insights',
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=1800,
)
def generate_monthly_insights(
    self,
    user_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate monthly insights for a specific user.

    Typically run at the beginning of each month to analyze
    the previous month's spending.

    Args:
        self: Task instance (bound task)
        user_id: User ID to generate insights for (required)
        month: Month to analyze (defaults to previous month)
        year: Year to analyze

    Returns:
        Dict with generation results
    """
    from django.contrib.auth import get_user_model
    from apps.ai.services.recommendations import RecommendationEngine

    if not user_id:
        raise ValueError("user_id is required to prevent cross-tenant data access")

    # Default to previous month
    today = timezone.now().date()
    if month is None or year is None:
        first_of_month = today.replace(day=1)
        last_month = first_of_month - timedelta(days=1)
        month = month or last_month.month
        year = year or last_month.year

    logger.info(
        f"Generating monthly insights for {month}/{year} - user_id={user_id}",
        extra={'task_id': self.request.id}
    )

    results = {
        'month': month,
        'year': year,
        'users_processed': 0,
        'insights_generated': 0,
        'errors': [],
    }

    try:
        User = get_user_model()

        users = User.objects.filter(id=user_id, is_active=True)

        engine = RecommendationEngine()

        for user in users:
            try:
                insights = engine.generate_monthly_insights(
                    user=user,
                    month=month,
                    year=year,
                    save_to_db=True
                )

                results['users_processed'] += 1
                if insights.get('has_data'):
                    results['insights_generated'] += 1

            except Exception as e:
                logger.error(f"Error generating insights for user {user.id}: {e}")
                results['errors'].append({
                    'user_id': user.id,
                    'error': str(e)
                })

        results['status'] = 'completed'

        logger.info(
            f"Monthly insights generation completed - {results['insights_generated']} insights",
            extra={'task_id': self.request.id}
        )

        return results

    except Exception as e:
        logger.exception(f"Monthly insights generation failed: {e}")
        raise self.retry(exc=e)


# =============================================================================
# Cleanup Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.ai.tasks.cleanup_old_recommendations',
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=600,
)
def cleanup_old_recommendations(
    self,
    days_to_keep: int = 30,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Clean up old and expired AI recommendations.

    Args:
        self: Task instance (bound task)
        days_to_keep: Number of days to keep recommendations
        dry_run: If True, only count records without deleting

    Returns:
        Dict with cleanup results
    """
    from apps.ai.models import AIRecommendation, AICategorizationLog, AIAnalysisCache

    logger.info(
        f"Starting AI data cleanup - days_to_keep={days_to_keep}, dry_run={dry_run}",
        extra={'task_id': self.request.id}
    )

    results = {
        'dry_run': dry_run,
        'deleted': {},
        'started_at': timezone.now().isoformat(),
    }

    cutoff_date = timezone.now() - timedelta(days=days_to_keep)

    try:
        # Clean up expired recommendations
        expired_recs = AIRecommendation.objects.filter(
            Q(expires_at__lt=timezone.now()) |
            Q(created_at__lt=cutoff_date, is_dismissed=True)
        )
        rec_count = expired_recs.count()

        if not dry_run and rec_count > 0:
            expired_recs.delete()

        results['deleted']['recommendations'] = rec_count

        # Clean up old categorization logs
        old_logs_cutoff = timezone.now() - timedelta(days=days_to_keep * 2)
        old_logs = AICategorizationLog.objects.filter(
            created_at__lt=old_logs_cutoff
        )
        log_count = old_logs.count()

        if not dry_run and log_count > 0:
            # Delete in batches
            while old_logs.exists():
                batch_ids = list(old_logs.values_list('id', flat=True)[:1000])
                AICategorizationLog.objects.filter(id__in=batch_ids).delete()

        results['deleted']['categorization_logs'] = log_count

        # Clean up expired analysis cache
        expired_cache = AIAnalysisCache.objects.filter(
            expires_at__lt=timezone.now()
        )
        cache_count = expired_cache.count()

        if not dry_run and cache_count > 0:
            expired_cache.delete()

        results['deleted']['analysis_cache'] = cache_count

        # Clear old recommendations from cache
        if not dry_run:
            _cleanup_ai_cache()

        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'completed'

        total_deleted = sum(results['deleted'].values())
        logger.info(
            f"AI cleanup completed - {total_deleted} records "
            f"{'would be' if dry_run else ''} deleted",
            extra={'task_id': self.request.id, 'results': results}
        )

        return results

    except Exception as e:
        logger.exception(f"AI cleanup failed: {e}")
        raise self.retry(exc=e)


def _cleanup_ai_cache() -> int:
    """Clean up AI-related cache keys."""
    cleaned = 0

    # Clear pattern caches older than 7 days
    # Note: This requires cache backend that supports pattern deletion
    # For Redis, you could use cache.delete_pattern('ai_*')

    try:
        # For standard Django cache, we can't iterate keys
        # but we can try to delete known patterns
        patterns_to_clear = [
            'ai_categorizer:*',
            'ai_anomaly:*',
            'ai_recommendations:*',
        ]

        # If using django-redis, try pattern deletion
        if hasattr(cache, 'delete_pattern'):
            for pattern in patterns_to_clear:
                try:
                    cache.delete_pattern(pattern)
                    cleaned += 1
                except Exception:
                    pass

    except Exception as e:
        logger.warning(f"Cache cleanup failed: {e}")

    return cleaned


# =============================================================================
# Utility Tasks
# =============================================================================

@shared_task(name='apps.ai.tasks.ai_health_check')
def ai_health_check() -> Dict[str, Any]:
    """
    AI service health check task.

    Verifies AI services are functioning correctly.

    Returns:
        Dict with health status
    """
    from apps.ai.services.categorization import TransactionCategorizer
    from apps.ai.services.anomaly_detection import AnomalyDetector
    from apps.ai.services.recommendations import RecommendationEngine

    results = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'services': {},
    }

    # Check each service can be initialized
    services = [
        ('categorizer', TransactionCategorizer),
        ('anomaly_detector', AnomalyDetector),
        ('recommendation_engine', RecommendationEngine),
    ]

    for name, service_class in services:
        try:
            service = service_class()
            results['services'][name] = {
                'status': 'ok',
                'model': service.model
            }
        except Exception as e:
            results['services'][name] = {
                'status': 'error',
                'error': str(e)
            }
            results['status'] = 'degraded'

    return results


@shared_task(
    bind=True,
    name='apps.ai.tasks.refresh_user_patterns',
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=300,
)
def refresh_user_patterns(
    self,
    user_id: int,
) -> Dict[str, Any]:
    """
    Refresh spending patterns for a user.

    Forces recalculation of spending patterns used for anomaly detection.

    Args:
        self: Task instance (bound task)
        user_id: User ID

    Returns:
        Dict with pattern refresh results
    """
    from django.contrib.auth import get_user_model
    from apps.ai.services.anomaly_detection import AnomalyDetector

    logger.info(
        f"Refreshing patterns for user {user_id}",
        extra={'task_id': self.request.id}
    )

    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)

        detector = AnomalyDetector()

        # Force refresh by not using cache
        patterns = detector.get_spending_patterns(user, use_cache=False)

        return {
            'user_id': user_id,
            'status': 'refreshed',
            'has_data': patterns.get('has_data', False),
            'period_days': patterns.get('period_days', 0),
            'transaction_count': patterns.get('overall', {}).get('total_transactions', 0),
            'refreshed_at': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Pattern refresh failed for user {user_id}: {e}")
        raise
