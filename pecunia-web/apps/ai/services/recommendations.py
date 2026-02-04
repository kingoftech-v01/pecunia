"""
Recommendation Engine Service.

AI-powered budget and spending recommendations using Claude API.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncMonth, TruncWeek
from django.core.cache import cache
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionCategory
from apps.ai.models import AIRecommendation, AIAnalysisCache
from .base import BaseAIService, AIServiceError

logger = logging.getLogger(__name__)


class RecommendationEngine(BaseAIService):
    """
    AI-powered recommendation engine for financial insights.

    Generates personalized budget recommendations, saving tips,
    and monthly insights based on user spending patterns.
    """

    # Cache configuration
    CACHE_PREFIX = "ai_recommendations"
    CACHE_TTL_BUDGET = 3600  # 1 hour
    CACHE_TTL_TIPS = 7200  # 2 hours
    CACHE_TTL_INSIGHTS = 86400  # 24 hours

    # Recommendation limits
    MAX_BUDGET_RECOMMENDATIONS = 10
    MAX_SAVING_TIPS = 7
    MAX_INSIGHTS = 5

    def get_system_prompt(self) -> str:
        """Get the system prompt for recommendations."""
        return """You are a personal finance advisor AI. Your task is to analyze spending patterns
and provide actionable, personalized financial recommendations.

You must respond ONLY with valid JSON in the requested format.

Guidelines:
- Focus on practical, achievable recommendations
- Prioritize high-impact changes that can save the most money
- Be encouraging but honest about spending habits
- Consider the user's overall financial picture
- Suggest specific amounts and timelines when possible
- Avoid generic advice - be specific to the user's data
- Recommendations should be actionable within 30 days
- Always explain the potential benefit of each recommendation
- Consider seasonal spending patterns and upcoming events
- Balance between saving money and quality of life"""

    def generate_budget_recommendations(
        self,
        user,
        num_recommendations: int = 5,
        save_to_db: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized budget recommendations.

        Args:
            user: User instance
            num_recommendations: Number of recommendations to generate
            save_to_db: Whether to save recommendations to database

        Returns:
            list: List of recommendation dicts
        """
        num_recommendations = min(num_recommendations, self.MAX_BUDGET_RECOMMENDATIONS)

        # Check cache
        cache_key = self._get_cache_key("budget", user.id)
        cached = cache.get(cache_key)
        if cached and not save_to_db:
            return cached[:num_recommendations]

        # Gather comprehensive spending data
        spending_data = self._gather_comprehensive_spending_data(user)

        if not spending_data.get("has_transactions"):
            return [{
                "title": "Start Tracking Your Expenses",
                "content": "Add your first transactions to get personalized budget recommendations.",
                "type": "spending",
                "priority": "medium",
                "potential_savings": None
            }]

        # Get budget data if available
        budget_data = self._gather_budget_data(user)

        messages = [
            {
                "role": "user",
                "content": f"""Based on this user's financial data, provide {num_recommendations} personalized budget recommendations:

SPENDING DATA:
{self._format_spending_data(spending_data)}

BUDGET STATUS:
{self._format_budget_data(budget_data)}

Provide actionable recommendations focused on:
1. Categories where spending is significantly over budget
2. Categories with unusual spending increases
3. Opportunities to reduce recurring expenses
4. Quick wins for immediate savings
5. Long-term financial health improvements

Respond with a JSON array of recommendations, each with:
- title: Short recommendation title (max 100 chars)
- content: Detailed explanation and action steps (2-3 sentences)
- type: One of: budget, spending, saving, goal
- priority: One of: low, medium, high, urgent
- potential_savings: Estimated monthly savings (number or null)
- category_id: Related category UUID (or null if general)
- timeframe: "immediate", "this_week", "this_month"
- difficulty: "easy", "medium", "hard"
- impact: "low", "medium", "high\""""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                max_tokens=2048,
                temperature=0.4
            )

            recommendations = self._parse_json_response(response)

            if not isinstance(recommendations, list):
                recommendations = recommendations.get("recommendations", [])

            # Process and validate recommendations
            processed = self._process_recommendations(recommendations, user)

            # Cache results
            cache.set(cache_key, processed, self.CACHE_TTL_BUDGET)

            # Save to database if requested
            if save_to_db and processed:
                self._save_recommendations(user, processed[:num_recommendations])

            return processed[:num_recommendations]

        except AIServiceError as e:
            logger.error(f"Failed to generate budget recommendations: {e}")
            return []

    def generate_saving_tips(
        self,
        user,
        focus_areas: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized saving tips.

        Args:
            user: User instance
            focus_areas: Optional list of categories to focus on

        Returns:
            list: List of saving tip dicts
        """
        cache_key = self._get_cache_key("tips", user.id)
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Get spending patterns
        spending_data = self._gather_comprehensive_spending_data(user)

        if not spending_data.get("has_transactions"):
            return []

        # Identify areas for improvement
        improvement_areas = self._identify_improvement_areas(user, spending_data)

        focus_context = ""
        if focus_areas:
            focus_context = f"\nFocus especially on these areas: {', '.join(focus_areas)}"

        messages = [
            {
                "role": "user",
                "content": f"""Generate saving tips based on this spending analysis:

{self._format_spending_data(spending_data)}

IMPROVEMENT OPPORTUNITIES:
{self._format_improvement_areas(improvement_areas)}
{focus_context}

Provide {self.MAX_SAVING_TIPS} specific, actionable saving tips.

Respond with JSON array:
[
    {{
        "title": "Tip title",
        "description": "Detailed explanation (2-3 sentences)",
        "estimated_savings": 50.00,
        "category": "Category name or 'General'",
        "implementation_steps": ["Step 1", "Step 2"],
        "difficulty": "easy/medium/hard",
        "quick_win": true/false
    }}
]"""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                max_tokens=1500,
                temperature=0.5
            )

            tips = self._parse_json_response(response)

            if not isinstance(tips, list):
                tips = tips.get("tips", [])

            # Validate and enhance tips
            processed_tips = []
            for tip in tips[:self.MAX_SAVING_TIPS]:
                processed_tips.append({
                    "title": tip.get("title", "Saving Tip")[:100],
                    "description": tip.get("description", ""),
                    "estimated_savings": tip.get("estimated_savings"),
                    "category": tip.get("category", "General"),
                    "implementation_steps": tip.get("implementation_steps", []),
                    "difficulty": tip.get("difficulty", "medium"),
                    "quick_win": tip.get("quick_win", False)
                })

            # Sort by quick wins first, then by estimated savings
            processed_tips.sort(
                key=lambda x: (
                    not x.get("quick_win", False),
                    -(x.get("estimated_savings") or 0)
                )
            )

            cache.set(cache_key, processed_tips, self.CACHE_TTL_TIPS)
            return processed_tips

        except AIServiceError as e:
            logger.error(f"Failed to generate saving tips: {e}")
            return []

    def generate_monthly_insights(
        self,
        user,
        month: Optional[int] = None,
        year: Optional[int] = None,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive monthly financial insights.

        Args:
            user: User instance
            month: Month to analyze (defaults to previous month)
            year: Year to analyze
            save_to_db: Whether to save insights to database

        Returns:
            dict: Monthly insights with analysis and recommendations
        """
        # Default to previous month
        today = timezone.now().date()
        if month is None or year is None:
            first_of_month = today.replace(day=1)
            last_month = first_of_month - timedelta(days=1)
            month = month or last_month.month
            year = year or last_month.year

        cache_key = self._get_cache_key("monthly", user.id, f"{year}-{month}")
        cached = cache.get(cache_key)
        if cached and not save_to_db:
            return cached

        # Get month data
        month_data = self._gather_month_data(user, month, year)

        if not month_data.get("has_transactions"):
            return {
                "month": month,
                "year": year,
                "has_data": False,
                "message": "No transactions found for this month"
            }

        # Get comparison data
        comparison_data = self._gather_comparison_data(user, month, year)

        # Generate AI insights
        messages = [
            {
                "role": "user",
                "content": f"""Provide comprehensive monthly financial insights:

THIS MONTH ({month}/{year}):
{self._format_month_data(month_data)}

COMPARISON WITH PREVIOUS MONTHS:
{self._format_comparison_data(comparison_data)}

Generate insights covering:
1. Overall spending analysis
2. Notable changes from previous months
3. Top spending categories and trends
4. Achievements (positive patterns)
5. Areas needing attention
6. Actionable recommendations for next month

Respond with JSON:
{{
    "summary": "2-3 sentence overview",
    "spending_score": 1-100,
    "trend": "improving/stable/declining",
    "key_metrics": {{
        "total_spent": amount,
        "total_income": amount,
        "savings_rate": percentage,
        "vs_last_month": percentage change
    }},
    "highlights": [
        {{
            "type": "achievement/concern/insight",
            "title": "Brief title",
            "description": "Explanation"
        }}
    ],
    "category_analysis": [
        {{
            "category": "name",
            "amount": spent,
            "change_percent": vs last month,
            "status": "over_budget/on_track/under_budget",
            "insight": "brief observation"
        }}
    ],
    "recommendations": [
        {{
            "title": "Recommendation",
            "description": "Action to take",
            "priority": "high/medium/low"
        }}
    ],
    "next_month_focus": "One key thing to focus on"
}}"""
            }
        ]

        try:
            response = self._make_request(
                messages=messages,
                system=self.get_system_prompt(),
                max_tokens=2500,
                temperature=0.3
            )

            insights = self._parse_json_response(response)
            insights["month"] = month
            insights["year"] = year
            insights["has_data"] = True
            insights["generated_at"] = timezone.now().isoformat()

            # Cache results
            cache.set(cache_key, insights, self.CACHE_TTL_INSIGHTS)

            # Save to database if requested
            if save_to_db:
                self._save_monthly_insights(user, insights, month, year)

            return insights

        except AIServiceError as e:
            logger.error(f"Failed to generate monthly insights: {e}")
            return {
                "month": month,
                "year": year,
                "has_data": True,
                "error": str(e),
                "raw_data": month_data
            }

    def _gather_comprehensive_spending_data(self, user) -> Dict[str, Any]:
        """Gather comprehensive user spending data for analysis."""
        now = timezone.now().date()
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        ninety_days_ago = now - timedelta(days=90)

        # Current period (30 days)
        current_expenses = Transaction.objects.filter(
            user=user,
            type='expense',
            transaction_date__gte=thirty_days_ago
        )

        # Previous period (30-60 days ago)
        previous_expenses = Transaction.objects.filter(
            user=user,
            type='expense',
            transaction_date__gte=sixty_days_ago,
            transaction_date__lt=thirty_days_ago
        )

        # Calculate totals
        current_total = current_expenses.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        previous_total = previous_expenses.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # By category
        by_category = current_expenses.values(
            'category__id', 'category__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id'),
            avg=Avg('amount')
        ).order_by('-total')

        # Previous period by category
        prev_by_category = {
            item['category__id']: float(item['total'])
            for item in previous_expenses.values('category__id').annotate(
                total=Sum('amount')
            )
        }

        # Income
        current_income = Transaction.objects.filter(
            user=user,
            type='income',
            transaction_date__gte=thirty_days_ago
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Transaction count
        transaction_count = current_expenses.count()

        # Top merchants
        top_merchants = current_expenses.exclude(
            merchant__isnull=True
        ).exclude(
            merchant=''
        ).values('merchant').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]

        # Recurring expenses
        recurring_total = current_expenses.filter(
            is_recurring=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return {
            "has_transactions": transaction_count > 0,
            "total_expenses_30d": float(current_total),
            "total_expenses_previous_30d": float(previous_total),
            "total_income_30d": float(current_income),
            "expense_change_percent": self._calc_change_percent(
                float(previous_total), float(current_total)
            ),
            "by_category": [
                {
                    "id": str(cat['category__id']) if cat['category__id'] else None,
                    "name": cat['category__name'] or "Uncategorized",
                    "total": float(cat['total']),
                    "count": cat['count'],
                    "avg": float(cat['avg']),
                    "previous": prev_by_category.get(cat['category__id'], 0),
                    "change_percent": self._calc_change_percent(
                        prev_by_category.get(cat['category__id'], 0),
                        float(cat['total'])
                    )
                }
                for cat in by_category
            ],
            "top_merchants": [
                {
                    "name": m['merchant'],
                    "total": float(m['total']),
                    "count": m['count']
                }
                for m in top_merchants
            ],
            "transaction_count_30d": transaction_count,
            "average_transaction": float(current_total / transaction_count) if transaction_count > 0 else 0,
            "net_30d": float(current_income - current_total),
            "recurring_expenses": float(recurring_total),
            "savings_rate": float(
                ((current_income - current_total) / current_income * 100)
                if current_income > 0 else 0
            )
        }

    def _gather_budget_data(self, user) -> Dict[str, Any]:
        """Gather user's budget data."""
        try:
            from apps.budgets.models import Budget, BudgetItem
        except ImportError:
            return {"has_budgets": False}

        today = timezone.now().date()

        budgets = Budget.objects.filter(
            user=user,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today,
        ).prefetch_related('items', 'items__category')

        if not budgets.exists():
            return {"has_budgets": False}

        budget_status = []
        for budget in budgets:
            for item in budget.items.all():
                planned = float(item.planned_amount) if item.planned_amount else 0
                spent = float(item.spent_amount) if item.spent_amount else 0
                percentage = (spent / planned * 100) if planned > 0 else 0

                budget_status.append({
                    "budget_name": budget.name,
                    "category": item.category.name if item.category else (item.name or "Unknown"),
                    "category_id": str(item.category.id) if item.category else None,
                    "budgeted": planned,
                    "spent": spent,
                    "remaining": planned - spent,
                    "percentage": round(percentage, 1),
                    "status": "over" if percentage > 100 else (
                        "warning" if percentage > 80 else "ok"
                    )
                })

        return {
            "has_budgets": True,
            "total_budgeted": sum(b["budgeted"] for b in budget_status),
            "total_spent": sum(b["spent"] for b in budget_status),
            "budgets": sorted(budget_status, key=lambda x: -x["percentage"])
        }

    def _gather_month_data(
        self,
        user,
        month: int,
        year: int
    ) -> Dict[str, Any]:
        """Gather data for a specific month."""
        from calendar import monthrange

        start_date = datetime(year, month, 1).date()
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day).date()

        transactions = Transaction.objects.filter(
            user=user,
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        )

        if not transactions.exists():
            return {"has_transactions": False}

        expenses = transactions.filter(type='expense')
        income = transactions.filter(type='income')

        expense_total = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        income_total = income.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        by_category = expenses.values(
            'category__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        by_week = expenses.annotate(
            week=TruncWeek('transaction_date')
        ).values('week').annotate(
            total=Sum('amount')
        ).order_by('week')

        return {
            "has_transactions": True,
            "total_expenses": float(expense_total),
            "total_income": float(income_total),
            "net": float(income_total - expense_total),
            "transaction_count": transactions.count(),
            "by_category": list(by_category),
            "by_week": list(by_week),
            "savings_rate": float(
                ((income_total - expense_total) / income_total * 100)
                if income_total > 0 else 0
            )
        }

    def _gather_comparison_data(
        self,
        user,
        month: int,
        year: int
    ) -> Dict[str, Any]:
        """Gather comparison data from previous months."""
        comparison = []

        for i in range(1, 4):  # Last 3 months
            if month - i <= 0:
                comp_month = 12 + (month - i)
                comp_year = year - 1
            else:
                comp_month = month - i
                comp_year = year

            month_data = self._gather_month_data(user, comp_month, comp_year)
            if month_data.get("has_transactions"):
                comparison.append({
                    "month": comp_month,
                    "year": comp_year,
                    "total_expenses": month_data["total_expenses"],
                    "total_income": month_data["total_income"],
                    "savings_rate": month_data["savings_rate"]
                })

        return {
            "has_comparison": len(comparison) > 0,
            "months": comparison,
            "avg_expenses": sum(m["total_expenses"] for m in comparison) / len(comparison) if comparison else 0,
            "avg_income": sum(m["total_income"] for m in comparison) / len(comparison) if comparison else 0
        }

    def _identify_improvement_areas(
        self,
        user,
        spending_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify areas where user can improve spending."""
        areas = []

        for cat in spending_data.get("by_category", []):
            change = cat.get("change_percent", 0)
            if change > 20:  # 20% increase
                areas.append({
                    "category": cat["name"],
                    "issue": "spending_increase",
                    "change_percent": change,
                    "current": cat["total"],
                    "previous": cat["previous"]
                })

        # Check for high recurring expenses
        recurring = spending_data.get("recurring_expenses", 0)
        total = spending_data.get("total_expenses_30d", 1)
        if recurring > 0 and (recurring / total) > 0.5:
            areas.append({
                "category": "Recurring Expenses",
                "issue": "high_recurring",
                "recurring_amount": recurring,
                "percentage_of_total": round((recurring / total) * 100, 1)
            })

        # Check savings rate
        savings_rate = spending_data.get("savings_rate", 0)
        if savings_rate < 10:
            areas.append({
                "category": "Savings",
                "issue": "low_savings_rate",
                "current_rate": savings_rate,
                "recommended_rate": 20
            })

        return areas

    def _process_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        user
    ) -> List[Dict[str, Any]]:
        """Process and validate recommendations."""
        user_categories = {
            str(c.id): c.name
            for c in TransactionCategory.objects.filter(user=user)
        }

        processed = []
        for rec in recommendations[:self.MAX_BUDGET_RECOMMENDATIONS]:
            # Validate category_id if provided
            cat_id = rec.get("category_id")
            if cat_id and cat_id not in user_categories:
                cat_id = None

            processed_rec = {
                "title": rec.get("title", "Recommendation")[:255],
                "content": rec.get("content", ""),
                "type": rec.get("type", "spending"),
                "priority": rec.get("priority", "medium"),
                "potential_savings": rec.get("potential_savings"),
                "category_id": cat_id,
                "category_name": user_categories.get(cat_id) if cat_id else None,
                "timeframe": rec.get("timeframe", "this_month"),
                "difficulty": rec.get("difficulty", "medium"),
                "impact": rec.get("impact", "medium"),
                "metadata": {
                    "generated_at": timezone.now().isoformat(),
                }
            }
            processed.append(processed_rec)

        # Sort by priority and impact
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        impact_order = {"high": 0, "medium": 1, "low": 2}

        processed.sort(key=lambda x: (
            priority_order.get(x["priority"], 2),
            impact_order.get(x["impact"], 1)
        ))

        return processed

    # Mapping from AI-generated type strings to model RecommendationType values
    TYPE_MAP = {
        'budget': AIRecommendation.RecommendationType.BUDGET_ALERT,
        'spending': AIRecommendation.RecommendationType.SPENDING_INSIGHT,
        'saving': AIRecommendation.RecommendationType.SAVING_TIP,
        'goal': AIRecommendation.RecommendationType.SAVING_TIP,
        'anomaly': AIRecommendation.RecommendationType.ANOMALY,
    }

    def _save_recommendations(
        self,
        user,
        recommendations: List[Dict[str, Any]]
    ) -> None:
        """Save recommendations to database."""
        try:
            # Mark old recommendations of same types as expired (but don't dismiss active ones)
            mapped_types = set()
            for r in recommendations:
                mapped = self.TYPE_MAP.get(r["type"])
                if mapped:
                    mapped_types.add(mapped)

            if mapped_types:
                AIRecommendation.objects.filter(
                    user=user,
                    type__in=mapped_types,
                    is_dismissed=False,
                    is_read=True,
                ).update(
                    expires_at=timezone.now()
                )

            # Create new recommendations
            for rec in recommendations:
                rec_type = self.TYPE_MAP.get(rec['type'], AIRecommendation.RecommendationType.SPENDING_INSIGHT)
                priority_value = AIRecommendation.normalize_priority(rec.get('priority', 'medium'))

                AIRecommendation.objects.create(
                    user=user,
                    title=rec['title'],
                    content=rec['content'],
                    type=rec_type,
                    priority=priority_value,
                    related_category_id=rec.get('category_id'),
                    confidence_score=0.8,
                    metadata={
                        "potential_savings": rec.get("potential_savings"),
                        "timeframe": rec.get("timeframe"),
                        "difficulty": rec.get("difficulty"),
                        "impact": rec.get("impact"),
                        **rec.get("metadata", {})
                    },
                    expires_at=timezone.now() + timedelta(days=30)
                )

            logger.info(f"Saved {len(recommendations)} recommendations for user {user.id}")

        except Exception as e:
            logger.error(f"Failed to save recommendations: {e}")

    def _save_monthly_insights(
        self,
        user,
        insights: Dict[str, Any],
        month: int,
        year: int
    ) -> None:
        """Save monthly insights to cache/database."""
        try:
            # Save as analysis cache
            cache_key = f"monthly_insights_{year}_{month}"

            AIAnalysisCache.objects.update_or_create(
                user=user,
                analysis_type='monthly_insights',
                cache_key=cache_key,
                defaults={
                    'result': insights,
                    'expires_at': timezone.now() + timedelta(days=60)
                }
            )

            # Create a summary recommendation
            summary = insights.get("summary", "")
            if summary and insights.get("spending_score", 50) < 60:
                priority_value = 2 if insights.get("spending_score", 50) >= 40 else 3
                AIRecommendation.objects.create(
                    user=user,
                    title=f"Monthly Review: {month}/{year}",
                    content=summary,
                    type=AIRecommendation.RecommendationType.SPENDING_INSIGHT,
                    priority=priority_value,
                    metadata={
                        "month": month,
                        "year": year,
                        "spending_score": insights.get("spending_score"),
                        "trend": insights.get("trend")
                    },
                    expires_at=timezone.now() + timedelta(days=30)
                )

        except Exception as e:
            logger.error(f"Failed to save monthly insights: {e}")

    def _calc_change_percent(self, old: float, new: float) -> float:
        """Calculate percentage change."""
        if old == 0:
            return 100.0 if new > 0 else 0.0
        return round(((new - old) / old) * 100, 1)

    def _format_spending_data(self, data: Dict[str, Any]) -> str:
        """Format spending data for AI context."""
        lines = [
            f"Total expenses (30 days): {self.format_currency(data['total_expenses_30d'])}",
            f"Previous 30 days: {self.format_currency(data['total_expenses_previous_30d'])}",
            f"Change: {data['expense_change_percent']}%",
            f"Total income (30 days): {self.format_currency(data['total_income_30d'])}",
            f"Net (30 days): {self.format_currency(data['net_30d'])}",
            f"Savings rate: {data['savings_rate']:.1f}%",
            f"Transaction count: {data['transaction_count_30d']}",
            f"Average transaction: {self.format_currency(data['average_transaction'])}",
            f"Recurring expenses: {self.format_currency(data['recurring_expenses'])}",
            "",
            "SPENDING BY CATEGORY:"
        ]

        for cat in data.get("by_category", [])[:10]:
            change_str = f" ({cat['change_percent']:+.1f}%)" if cat.get('previous') else ""
            lines.append(
                f"  - {cat['name']}: {self.format_currency(cat['total'])} "
                f"({cat['count']} transactions){change_str}"
            )

        if data.get("top_merchants"):
            lines.append("")
            lines.append("TOP MERCHANTS:")
            for m in data["top_merchants"][:5]:
                lines.append(
                    f"  - {m['name']}: {self.format_currency(m['total'])} ({m['count']} transactions)"
                )

        return "\n".join(lines)

    def _format_budget_data(self, data: Dict[str, Any]) -> str:
        """Format budget data for AI context."""
        if not data.get("has_budgets"):
            return "No budgets set for this month."

        lines = [
            f"Total budgeted: {self.format_currency(data['total_budgeted'])}",
            f"Total spent: {self.format_currency(data['total_spent'])}",
            "",
            "BUDGET STATUS:"
        ]

        for b in data.get("budgets", []):
            status_emoji = {
                "over": "[OVER]",
                "warning": "[WARNING]",
                "ok": "[OK]"
            }.get(b["status"], "")

            lines.append(
                f"  - {b['category']}: {self.format_currency(b['spent'])} / "
                f"{self.format_currency(b['budgeted'])} ({b['percentage']}%) {status_emoji}"
            )

        return "\n".join(lines)

    def _format_month_data(self, data: Dict[str, Any]) -> str:
        """Format month data for AI context."""
        lines = [
            f"Total expenses: {self.format_currency(data['total_expenses'])}",
            f"Total income: {self.format_currency(data['total_income'])}",
            f"Net: {self.format_currency(data['net'])}",
            f"Savings rate: {data['savings_rate']:.1f}%",
            f"Transaction count: {data['transaction_count']}",
            "",
            "BY CATEGORY:"
        ]

        for cat in data.get("by_category", [])[:10]:
            lines.append(
                f"  - {cat['category__name'] or 'Uncategorized'}: "
                f"{self.format_currency(float(cat['total']))}"
            )

        return "\n".join(lines)

    def _format_comparison_data(self, data: Dict[str, Any]) -> str:
        """Format comparison data for AI context."""
        if not data.get("has_comparison"):
            return "No historical data for comparison."

        lines = [
            f"Average expenses (previous 3 months): {self.format_currency(data['avg_expenses'])}",
            f"Average income (previous 3 months): {self.format_currency(data['avg_income'])}",
            "",
            "MONTHLY BREAKDOWN:"
        ]

        for m in data.get("months", []):
            lines.append(
                f"  - {m['month']}/{m['year']}: "
                f"Expenses {self.format_currency(m['total_expenses'])}, "
                f"Income {self.format_currency(m['total_income'])}, "
                f"Savings {m['savings_rate']:.1f}%"
            )

        return "\n".join(lines)

    def _format_improvement_areas(self, areas: List[Dict[str, Any]]) -> str:
        """Format improvement areas for AI context."""
        if not areas:
            return "No specific improvement areas identified."

        lines = []
        for area in areas:
            if area["issue"] == "spending_increase":
                lines.append(
                    f"- {area['category']}: {area['change_percent']:.1f}% increase "
                    f"({self.format_currency(area['previous'])} -> {self.format_currency(area['current'])})"
                )
            elif area["issue"] == "high_recurring":
                lines.append(
                    f"- Recurring expenses: {self.format_currency(area['recurring_amount'])} "
                    f"({area['percentage_of_total']}% of total)"
                )
            elif area["issue"] == "low_savings_rate":
                lines.append(
                    f"- Low savings rate: {area['current_rate']:.1f}% "
                    f"(recommended: {area['recommended_rate']}%)"
                )

        return "\n".join(lines)
