package com.pecunia.domain.models

import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.time.YearMonth

/**
 * Represents a budget for tracking spending limits.
 */
data class Budget(
    val id: String,
    val userId: String,
    val name: String,
    val amount: BigDecimal,
    val currency: String = "USD",
    val category: TransactionCategory? = null,
    val period: BudgetPeriod,
    val startDate: LocalDate,
    val endDate: LocalDate? = null,
    val currentSpent: BigDecimal = BigDecimal.ZERO,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now(),
    val isActive: Boolean = true,
    val alertsEnabled: Boolean = true,
    val alertThreshold: Float = 0.8f,
    val color: String = "#4CAF50",
    val icon: String = "account_balance_wallet"
) {
    /**
     * Calculate the remaining budget amount.
     */
    val remaining: BigDecimal
        get() = amount.subtract(currentSpent)

    /**
     * Calculate the percentage of budget used.
     */
    val percentageUsed: Float
        get() = if (amount > BigDecimal.ZERO) {
            currentSpent.toFloat() / amount.toFloat()
        } else {
            0f
        }

    /**
     * Check if budget is over the limit.
     */
    val isOverBudget: Boolean
        get() = currentSpent > amount

    /**
     * Check if budget is near the alert threshold.
     */
    val isNearLimit: Boolean
        get() = percentageUsed >= alertThreshold && !isOverBudget
}

/**
 * Budget period type.
 */
enum class BudgetPeriod(val displayName: String) {
    DAILY("Daily"),
    WEEKLY("Weekly"),
    BIWEEKLY("Bi-weekly"),
    MONTHLY("Monthly"),
    QUARTERLY("Quarterly"),
    YEARLY("Yearly"),
    CUSTOM("Custom")
}

/**
 * Summary of all budgets.
 */
data class BudgetSummary(
    val totalBudgeted: BigDecimal,
    val totalSpent: BigDecimal,
    val totalRemaining: BigDecimal,
    val budgetsOnTrack: Int,
    val budgetsNearLimit: Int,
    val budgetsOverLimit: Int,
    val period: YearMonth
)

/**
 * Budget with associated transactions.
 */
data class BudgetWithTransactions(
    val budget: Budget,
    val transactions: List<Transaction>
)

/**
 * Budget alert notification.
 */
data class BudgetAlert(
    val budgetId: String,
    val budgetName: String,
    val alertType: BudgetAlertType,
    val percentageUsed: Float,
    val amountRemaining: BigDecimal,
    val timestamp: Instant = Instant.now()
)

/**
 * Type of budget alert.
 */
enum class BudgetAlertType {
    APPROACHING_LIMIT,
    LIMIT_REACHED,
    OVER_BUDGET
}
