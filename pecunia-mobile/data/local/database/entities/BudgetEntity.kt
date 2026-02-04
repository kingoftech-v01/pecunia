package com.pecunia.data.local.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room entity representing a budget.
 */
@Entity(
    tableName = "budgets",
    indices = [
        Index(value = ["user_id"]),
        Index(value = ["category"]),
        Index(value = ["period_type"])
    ]
)
data class BudgetEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: String,

    @ColumnInfo(name = "user_id")
    val userId: String,

    @ColumnInfo(name = "name")
    val name: String,

    @ColumnInfo(name = "category")
    val category: String,

    @ColumnInfo(name = "budget_amount")
    val budgetAmount: Double,

    @ColumnInfo(name = "spent_amount")
    val spentAmount: Double = 0.0,

    @ColumnInfo(name = "currency")
    val currency: String = "USD",

    @ColumnInfo(name = "period_type")
    val periodType: BudgetPeriodType,

    @ColumnInfo(name = "start_date")
    val startDate: Long,

    @ColumnInfo(name = "end_date")
    val endDate: Long,

    @ColumnInfo(name = "is_active")
    val isActive: Boolean = true,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false,

    @ColumnInfo(name = "alert_threshold")
    val alertThreshold: Double = 0.8, // Alert when 80% of budget is used

    @ColumnInfo(name = "color")
    val color: String? = null, // Hex color for UI

    @ColumnInfo(name = "icon")
    val icon: String? = null,

    @ColumnInfo(name = "notes")
    val notes: String? = null
) {
    /**
     * Calculate the remaining budget amount.
     */
    val remainingAmount: Double
        get() = budgetAmount - spentAmount

    /**
     * Calculate the percentage of budget used.
     */
    val usagePercentage: Double
        get() = if (budgetAmount > 0) (spentAmount / budgetAmount) * 100 else 0.0

    /**
     * Check if the budget is over the alert threshold.
     */
    val isOverThreshold: Boolean
        get() = usagePercentage >= (alertThreshold * 100)

    /**
     * Check if the budget is exceeded.
     */
    val isExceeded: Boolean
        get() = spentAmount > budgetAmount
}

/**
 * Enum representing budget period types.
 */
enum class BudgetPeriodType {
    DAILY,
    WEEKLY,
    BIWEEKLY,
    MONTHLY,
    QUARTERLY,
    YEARLY,
    CUSTOM
}
