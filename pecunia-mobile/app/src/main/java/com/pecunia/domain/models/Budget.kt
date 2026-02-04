package com.pecunia.domain.models

import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.time.YearMonth

/**
 * Represents the period type for a budget.
 */
enum class BudgetPeriod {
    WEEKLY,
    MONTHLY,
    QUARTERLY,
    YEARLY;

    companion object {
        fun fromString(value: String): BudgetPeriod {
            return entries.find { it.name.equals(value, ignoreCase = true) }
                ?: throw IllegalArgumentException("Unknown budget period: $value")
        }
    }
}

/**
 * Represents a budget item for a specific category within a budget.
 */
data class BudgetItem(
    val id: String,
    val budgetId: String,
    val categoryId: String,
    val category: Category? = null,
    val allocatedAmount: BigDecimal,
    val spentAmount: BigDecimal = BigDecimal.ZERO,
    val notes: String? = null,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
) {
    /**
     * Returns the remaining amount in this budget item.
     */
    val remainingAmount: BigDecimal
        get() = allocatedAmount.subtract(spentAmount)

    /**
     * Returns the percentage of budget spent (0-100+).
     */
    val spentPercentage: Double
        get() = if (allocatedAmount > BigDecimal.ZERO) {
            spentAmount.divide(allocatedAmount, 4, java.math.RoundingMode.HALF_UP)
                .multiply(BigDecimal(100))
                .toDouble()
        } else {
            0.0
        }

    /**
     * Returns true if the budget item is overspent.
     */
    val isOverBudget: Boolean
        get() = spentAmount > allocatedAmount

    /**
     * Returns true if spending is at or above 80% of allocated amount.
     */
    val isNearLimit: Boolean
        get() = spentPercentage >= 80.0 && !isOverBudget

    companion object {
        fun empty(): BudgetItem = BudgetItem(
            id = "",
            budgetId = "",
            categoryId = "",
            allocatedAmount = BigDecimal.ZERO
        )
    }
}

/**
 * Represents a budget in the application.
 */
data class Budget(
    val id: String,
    val userId: String,
    val name: String,
    val totalAmount: BigDecimal,
    val period: BudgetPeriod = BudgetPeriod.MONTHLY,
    val startDate: LocalDate,
    val endDate: LocalDate,
    val items: List<BudgetItem> = emptyList(),
    val currency: String = "USD",
    val isActive: Boolean = true,
    val notes: String? = null,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
) {
    /**
     * Returns the total allocated amount across all budget items.
     */
    val totalAllocated: BigDecimal
        get() = items.fold(BigDecimal.ZERO) { acc, item -> acc.add(item.allocatedAmount) }

    /**
     * Returns the total spent amount across all budget items.
     */
    val totalSpent: BigDecimal
        get() = items.fold(BigDecimal.ZERO) { acc, item -> acc.add(item.spentAmount) }

    /**
     * Returns the remaining amount in the budget.
     */
    val remainingAmount: BigDecimal
        get() = totalAmount.subtract(totalSpent)

    /**
     * Returns the unallocated amount (total - allocated to items).
     */
    val unallocatedAmount: BigDecimal
        get() = totalAmount.subtract(totalAllocated)

    /**
     * Returns the percentage of budget spent (0-100+).
     */
    val spentPercentage: Double
        get() = if (totalAmount > BigDecimal.ZERO) {
            totalSpent.divide(totalAmount, 4, java.math.RoundingMode.HALF_UP)
                .multiply(BigDecimal(100))
                .toDouble()
        } else {
            0.0
        }

    /**
     * Returns true if the budget is overspent.
     */
    val isOverBudget: Boolean
        get() = totalSpent > totalAmount

    /**
     * Returns true if spending is at or above 80% of total amount.
     */
    val isNearLimit: Boolean
        get() = spentPercentage >= 80.0 && !isOverBudget

    /**
     * Returns true if the budget period includes the given date.
     */
    fun containsDate(date: LocalDate): Boolean {
        return !date.isBefore(startDate) && !date.isAfter(endDate)
    }

    /**
     * Returns true if the budget is currently active (within date range).
     */
    val isCurrentlyActive: Boolean
        get() = isActive && containsDate(LocalDate.now())

    companion object {
        /**
         * Creates an empty Budget instance for initialization purposes.
         */
        fun empty(): Budget = Budget(
            id = "",
            userId = "",
            name = "",
            totalAmount = BigDecimal.ZERO,
            startDate = LocalDate.now(),
            endDate = LocalDate.now().plusMonths(1)
        )

        /**
         * Creates a monthly budget for the given month.
         */
        fun forMonth(
            id: String,
            userId: String,
            name: String,
            totalAmount: BigDecimal,
            yearMonth: YearMonth = YearMonth.now()
        ): Budget = Budget(
            id = id,
            userId = userId,
            name = name,
            totalAmount = totalAmount,
            period = BudgetPeriod.MONTHLY,
            startDate = yearMonth.atDay(1),
            endDate = yearMonth.atEndOfMonth()
        )
    }
}
