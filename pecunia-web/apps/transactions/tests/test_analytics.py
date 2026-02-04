"""Tests for Transaction Analytics."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.core.cache import cache
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionCategory, RecurringTransaction
from apps.transactions.analytics import (
    AnalyticsPeriod,
    TransactionAnalytics,
    get_spending_by_category,
    get_income_vs_expense,
    get_daily_balance,
    get_top_merchants,
    get_recurring_analysis,
)


@pytest.fixture(autouse=True)
def clear_analytics_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()


class TestAnalyticsPeriod:
    """Tests for AnalyticsPeriod helper class."""

    def test_week_period(self):
        period = AnalyticsPeriod("week")
        today = timezone.now().date()
        assert period.start_date == today - timedelta(days=7)
        assert period.end_date == today

    def test_month_period(self):
        period = AnalyticsPeriod("month")
        today = timezone.now().date()
        assert period.start_date == today.replace(day=1)
        assert period.end_date == today

    def test_quarter_period(self):
        period = AnalyticsPeriod("quarter")
        today = timezone.now().date()
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        assert period.start_date.month == quarter_month
        assert period.start_date.day == 1

    def test_year_period(self):
        period = AnalyticsPeriod("year")
        today = timezone.now().date()
        assert period.start_date == today.replace(month=1, day=1)

    def test_all_period(self):
        period = AnalyticsPeriod("all")
        assert period.start_date is None
        assert period.end_date == timezone.now().date()

    def test_custom_period(self):
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)
        period = AnalyticsPeriod("custom", start, end)
        assert period.start_date == start
        assert period.end_date == end

    def test_custom_period_no_dates_falls_through(self):
        period = AnalyticsPeriod("custom")
        # custom without start_date falls through to default (first of month)
        today = timezone.now().date()
        assert period.start_date == today.replace(day=1)
        # custom without end_date returns today
        assert period.end_date == today

    def test_default_period_is_month(self):
        period = AnalyticsPeriod()
        today = timezone.now().date()
        assert period.start_date == today.replace(day=1)

    def test_unknown_period_falls_to_default(self):
        period = AnalyticsPeriod("unknown")
        today = timezone.now().date()
        # Falls through all elif branches to the final return
        assert period.start_date == today.replace(day=1)

    def test_previous_start_date_month(self):
        period = AnalyticsPeriod("month")
        prev_start = period.previous_start_date
        assert prev_start is not None
        assert prev_start < period.start_date

    def test_previous_end_date_month(self):
        period = AnalyticsPeriod("month")
        assert period.previous_end_date == period.start_date - timedelta(days=1)

    def test_previous_start_date_all(self):
        period = AnalyticsPeriod("all")
        assert period.previous_start_date is None

    def test_previous_end_date_when_no_start(self):
        period = AnalyticsPeriod("all")
        # start_date is None, so previous_end_date is None
        assert period.previous_end_date is None

    def test_cache_key_suffix_month(self):
        period = AnalyticsPeriod("month")
        today = timezone.now().date()
        assert period.get_cache_key_suffix() == f"month_{today}"

    def test_cache_key_suffix_custom(self):
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)
        period = AnalyticsPeriod("custom", start, end)
        assert period.get_cache_key_suffix() == f"custom_{start}_{end}"

    def test_cache_key_suffix_all(self):
        period = AnalyticsPeriod("all")
        today = timezone.now().date()
        assert period.get_cache_key_suffix() == f"all_{today}"


@pytest.mark.django_db
class TestTransactionAnalytics:
    """Tests for TransactionAnalytics service."""

    @pytest.fixture
    def analytics(self, user):
        return TransactionAnalytics(user)

    @pytest.fixture
    def expense_transactions(self, user, category):
        """Create several expense transactions."""
        today = timezone.now().date()
        txs = []
        for i in range(3):
            txs.append(Transaction.objects.create(
                user=user,
                category=category,
                amount=Decimal("100.00"),
                type="expense",
                description=f"Expense {i}",
                merchant="Store A",
                transaction_date=today,
            ))
        return txs

    @pytest.fixture
    def income_txns(self, user, income_category):
        """Create income transactions."""
        today = timezone.now().date()
        return [Transaction.objects.create(
            user=user,
            category=income_category,
            amount=Decimal("3000.00"),
            type="income",
            description="Salary",
            merchant="Employer Inc.",
            transaction_date=today,
        )]

    # --- get_spending_by_category ---

    def test_spending_by_category(self, analytics, expense_transactions):
        result = analytics.get_spending_by_category()
        assert result["total_spending"] == 300.0
        assert len(result["categories"]) == 1
        assert result["categories"][0]["name"] == "Groceries"
        assert "chart_data" in result

    def test_spending_by_category_empty(self, analytics):
        result = analytics.get_spending_by_category()
        assert result["total_spending"] == 0
        assert len(result["categories"]) == 0

    def test_spending_by_category_percentages(self, analytics, expense_transactions):
        result = analytics.get_spending_by_category()
        total_pct = sum(c["percentage"] for c in result["categories"])
        assert total_pct == pytest.approx(100.0, abs=1.0)

    def test_spending_by_category_custom_period(self, analytics, expense_transactions):
        result = analytics.get_spending_by_category(
            period="custom",
            start_date=timezone.now().date() - timedelta(days=7),
            end_date=timezone.now().date(),
        )
        assert result["total_spending"] > 0

    def test_spending_by_category_exclude_uncategorized(self, analytics, user):
        Transaction.objects.create(
            user=user, amount=Decimal("50.00"), type="expense",
            transaction_date=timezone.now().date(),
        )
        result = analytics.get_spending_by_category(include_uncategorized=False)
        for cat in result["categories"]:
            assert cat["id"] is not None

    def test_spending_by_category_limit(self, analytics, user):
        for i in range(5):
            cat = TransactionCategory.objects.create(
                user=user, name=f"Cat{i}", type="expense"
            )
            Transaction.objects.create(
                user=user, category=cat,
                amount=Decimal(str(10 * (i + 1))),
                type="expense", transaction_date=timezone.now().date(),
            )
        result = analytics.get_spending_by_category(limit=3)
        assert len(result["categories"]) <= 3

    def test_spending_by_category_caching(self, analytics, expense_transactions):
        result1 = analytics.get_spending_by_category()
        result2 = analytics.get_spending_by_category()
        assert result1 == result2

    # --- get_income_vs_expense ---

    def test_income_vs_expense(self, analytics, expense_transactions, income_txns):
        result = analytics.get_income_vs_expense()
        assert result["summary"]["total_income"] > 0
        assert result["summary"]["total_expense"] > 0
        assert "net_balance" in result["summary"]
        assert "savings_rate" in result["summary"]
        assert "chart_data" in result

    def test_income_vs_expense_empty(self, analytics):
        result = analytics.get_income_vs_expense()
        assert result["summary"]["total_income"] == 0
        assert result["summary"]["total_expense"] == 0
        assert result["summary"]["savings_rate"] == 0

    def test_income_vs_expense_group_by_day(self, analytics, expense_transactions):
        result = analytics.get_income_vs_expense(group_by="day")
        assert "data_points" in result

    def test_income_vs_expense_group_by_week(self, analytics, expense_transactions):
        result = analytics.get_income_vs_expense(group_by="week")
        assert "data_points" in result

    def test_income_vs_expense_previous_comparison(
        self, analytics, user, category, income_category
    ):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("200.00"), type="expense",
            transaction_date=prev_month_start,
        )
        Transaction.objects.create(
            user=user, category=income_category,
            amount=Decimal("1000.00"), type="income",
            transaction_date=prev_month_start,
        )
        Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("300.00"), type="expense",
            transaction_date=today,
        )
        Transaction.objects.create(
            user=user, category=income_category,
            amount=Decimal("2000.00"), type="income",
            transaction_date=today,
        )

        result = analytics.get_income_vs_expense(period="month")
        assert result["comparison"] is not None
        assert "income_change_percent" in result["comparison"]
        assert "expense_change_percent" in result["comparison"]

    def test_income_vs_expense_no_previous_income(
        self, analytics, user, category
    ):
        """When previous period has zero income, income_change should handle it."""
        today = timezone.now().date()
        Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("300.00"), type="expense",
            transaction_date=today,
        )
        result = analytics.get_income_vs_expense(period="month")
        # comparison should exist (month has previous_start)
        if result["comparison"]:
            assert "income_change_percent" in result["comparison"]

    # --- get_daily_balance ---

    def test_daily_balance(self, analytics, expense_transactions, income_txns):
        result = analytics.get_daily_balance()
        assert "daily_balances" in result
        assert "summary" in result
        assert "chart_data" in result

    def test_daily_balance_with_initial(self, analytics, expense_transactions):
        result = analytics.get_daily_balance(initial_balance=Decimal("1000.00"))
        assert result["summary"]["initial_balance"] == 1000.0

    def test_daily_balance_empty(self, analytics):
        result = analytics.get_daily_balance()
        assert result["summary"]["total_change"] == 0
        assert result["summary"]["initial_balance"] == 0
        assert result["summary"]["final_balance"] == 0

    def test_daily_balance_min_max(self, analytics, user, category):
        today = timezone.now().date()
        Transaction.objects.create(
            user=user, amount=Decimal("1000.00"), type="income",
            transaction_date=today - timedelta(days=1),
        )
        Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("500.00"), type="expense",
            transaction_date=today,
        )
        result = analytics.get_daily_balance(period="week")
        summary = result["summary"]
        assert summary["max_balance"] >= summary["min_balance"]

    # --- get_top_merchants ---

    def test_top_merchants(self, analytics, expense_transactions):
        result = analytics.get_top_merchants()
        assert len(result["merchants"]) > 0
        assert result["merchants"][0]["name"] == "Store A"
        assert result["merchants"][0]["count"] == 3

    def test_top_merchants_empty(self, analytics):
        result = analytics.get_top_merchants()
        assert result["merchant_count"] == 0

    def test_top_merchants_excludes_empty_merchant(self, analytics, user):
        Transaction.objects.create(
            user=user, amount=Decimal("10.00"), type="expense",
            merchant="", transaction_date=timezone.now().date(),
        )
        result = analytics.get_top_merchants()
        assert result["merchant_count"] == 0

    def test_top_merchants_income_type(self, analytics, income_txns):
        result = analytics.get_top_merchants(transaction_type="income")
        assert isinstance(result["merchants"], list)
        if result["merchants"]:
            assert result["merchants"][0]["name"] == "Employer Inc."

    def test_top_merchants_all_types(
        self, analytics, expense_transactions, income_txns
    ):
        result = analytics.get_top_merchants(transaction_type="all")
        assert result["merchant_count"] >= 1

    def test_top_merchants_limit(self, analytics, user):
        for i in range(5):
            Transaction.objects.create(
                user=user, amount=Decimal(str(10 * (i + 1))),
                type="expense", merchant=f"Merchant{i}",
                transaction_date=timezone.now().date(),
            )
        result = analytics.get_top_merchants(limit=3)
        assert len(result["merchants"]) <= 3

    # --- get_recurring_analysis ---

    def test_recurring_analysis(self, analytics, recurring_transaction):
        result = analytics.get_recurring_analysis()
        assert result["recurring_expense"]["count"] == 1
        assert result["recurring_income"]["count"] == 0
        assert result["summary"]["total_recurring"] == 1
        assert "projections" in result

    def test_recurring_analysis_empty(self, analytics):
        result = analytics.get_recurring_analysis()
        assert result["summary"]["total_recurring"] == 0
        assert result["recurring_income"]["monthly_total"] == 0
        assert result["recurring_expense"]["monthly_total"] == 0

    def test_recurring_analysis_upcoming(self, analytics, user, category):
        today = timezone.now().date()
        RecurringTransaction.objects.create(
            user=user, category=category, name="Soon",
            amount=Decimal("50.00"), type="expense", frequency="monthly",
            start_date=today, next_occurrence=today + timedelta(days=5),
            is_active=True,
        )
        result = analytics.get_recurring_analysis()
        assert len(result["upcoming"]) >= 1
        assert result["upcoming"][0]["days_until"] == 5

    def test_recurring_analysis_income(self, analytics, user, income_category):
        today = timezone.now().date()
        RecurringTransaction.objects.create(
            user=user, category=income_category, name="Salary",
            amount=Decimal("3000.00"), type="income", frequency="monthly",
            start_date=today, next_occurrence=today + timedelta(days=15),
            is_active=True,
        )
        result = analytics.get_recurring_analysis()
        assert result["recurring_income"]["count"] == 1
        assert result["recurring_income"]["monthly_total"] == 3000.0

    # --- get_trends ---

    def test_get_trends_with_data(self, analytics, expense_transactions):
        result = analytics.get_trends(period="year")
        assert "monthly_data" in result
        assert "trend" in result
        assert result["trend"]["direction"] in ["up", "down", "stable"]
        assert "prediction" in result

    def test_get_trends_income_metric(self, analytics, income_txns):
        result = analytics.get_trends(metric="income")
        assert result["period"]["metric"] == "income"

    def test_get_trends_empty(self, analytics):
        result = analytics.get_trends()
        assert result["trend"]["direction"] == "stable"
        assert result["trend"]["change_percent"] == 0

    def test_get_trends_balance_metric(self, analytics, expense_transactions):
        result = analytics.get_trends(metric="balance")
        assert "monthly_data" in result

    def test_get_trends_confidence(self, analytics, user):
        """With < 6 months data, confidence should be low."""
        Transaction.objects.create(
            user=user, amount=Decimal("100.00"), type="expense",
            transaction_date=timezone.now().date(),
        )
        result = analytics.get_trends(period="year")
        assert result["prediction"]["confidence"] == "low"

    # --- get_dashboard_summary ---

    def test_dashboard_summary(self, analytics, expense_transactions, income_txns):
        result = analytics.get_dashboard_summary()
        assert result["current_month"]["income"] > 0
        assert result["current_month"]["expense"] > 0
        assert result["current_month"]["balance"] == (
            result["current_month"]["income"] - result["current_month"]["expense"]
        )
        assert "comparison" in result
        assert "savings_rate" in result

    def test_dashboard_summary_empty(self, analytics):
        result = analytics.get_dashboard_summary()
        assert result["current_month"]["income"] == 0
        assert result["current_month"]["expense"] == 0
        assert result["savings_rate"] == 0

    def test_dashboard_summary_top_category(
        self, analytics, expense_transactions, category
    ):
        result = analytics.get_dashboard_summary()
        assert result["top_category"] is not None
        assert result["top_category"]["name"] == "Groceries"

    def test_dashboard_summary_no_top_category(self, analytics):
        result = analytics.get_dashboard_summary()
        assert result["top_category"] is None

    # --- cache ---

    def test_invalidate_cache(self, analytics, expense_transactions):
        analytics.get_spending_by_category()
        analytics.invalidate_cache()
        # Should not raise and should re-compute
        result = analytics.get_spending_by_category()
        assert result["total_spending"] > 0

    def test_get_cache_key(self, analytics):
        period = AnalyticsPeriod("month")
        key = analytics._get_cache_key("test_method", period)
        assert "test_method" in key
        assert str(analytics.user.id) in key

    # --- _calculate_monthly_equivalent ---

    def test_monthly_equivalent_daily(self, analytics):
        result = analytics._calculate_monthly_equivalent(Decimal("10"), "daily")
        assert result == Decimal("300")

    def test_monthly_equivalent_weekly(self, analytics):
        result = analytics._calculate_monthly_equivalent(Decimal("100"), "weekly")
        assert result == Decimal("433")

    def test_monthly_equivalent_biweekly(self, analytics):
        result = analytics._calculate_monthly_equivalent(Decimal("100"), "biweekly")
        assert result == Decimal("217")

    def test_monthly_equivalent_monthly(self, analytics):
        result = analytics._calculate_monthly_equivalent(Decimal("100"), "monthly")
        assert result == Decimal("100")

    def test_monthly_equivalent_quarterly(self, analytics):
        result = analytics._calculate_monthly_equivalent(Decimal("300"), "quarterly")
        assert result == Decimal("99")

    def test_monthly_equivalent_yearly(self, analytics):
        result = analytics._calculate_monthly_equivalent(Decimal("1200"), "yearly")
        assert result == Decimal("99.6")

    def test_monthly_equivalent_unknown(self, analytics):
        result = analytics._calculate_monthly_equivalent(Decimal("100"), "unknown")
        assert result == Decimal("100")


@pytest.mark.django_db
class TestConvenienceFunctions:
    """Tests for convenience analytics functions."""

    def test_get_spending_by_category(self, user):
        result = get_spending_by_category(user)
        assert "categories" in result
        assert "total_spending" in result

    def test_get_income_vs_expense(self, user):
        result = get_income_vs_expense(user)
        assert "summary" in result

    def test_get_daily_balance(self, user):
        result = get_daily_balance(user)
        assert "daily_balances" in result

    def test_get_top_merchants(self, user):
        result = get_top_merchants(user)
        assert "merchants" in result

    def test_get_recurring_analysis(self, user):
        result = get_recurring_analysis(user)
        assert "summary" in result
