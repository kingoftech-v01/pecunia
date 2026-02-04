package com.pecunia.data.remote.dto

import com.pecunia.data.local.database.entities.BudgetEntity
import com.pecunia.data.local.database.entities.BudgetPeriodType
import com.google.gson.annotations.SerializedName

/**
 * Data Transfer Object for Budget from API.
 */
data class BudgetDto(
    @SerializedName("id")
    val id: String,

    @SerializedName("user_id")
    val userId: String,

    @SerializedName("name")
    val name: String,

    @SerializedName("category")
    val category: String,

    @SerializedName("budget_amount")
    val budgetAmount: Double,

    @SerializedName("spent_amount")
    val spentAmount: Double,

    @SerializedName("currency")
    val currency: String,

    @SerializedName("period_type")
    val periodType: String,

    @SerializedName("start_date")
    val startDate: Long,

    @SerializedName("end_date")
    val endDate: Long,

    @SerializedName("is_active")
    val isActive: Boolean,

    @SerializedName("created_at")
    val createdAt: Long,

    @SerializedName("updated_at")
    val updatedAt: Long,

    @SerializedName("alert_threshold")
    val alertThreshold: Double,

    @SerializedName("color")
    val color: String?,

    @SerializedName("icon")
    val icon: String?,

    @SerializedName("notes")
    val notes: String?
) {
    /**
     * Convert DTO to Entity for local storage.
     */
    fun toEntity(): BudgetEntity {
        return BudgetEntity(
            id = id,
            userId = userId,
            name = name,
            category = category,
            budgetAmount = budgetAmount,
            spentAmount = spentAmount,
            currency = currency,
            periodType = try {
                BudgetPeriodType.valueOf(periodType.uppercase())
            } catch (e: IllegalArgumentException) {
                BudgetPeriodType.MONTHLY // Safe fallback for unknown server values
            },
            startDate = startDate,
            endDate = endDate,
            isActive = isActive,
            createdAt = createdAt,
            updatedAt = updatedAt,
            isSynced = true,
            alertThreshold = alertThreshold,
            color = color,
            icon = icon,
            notes = notes
        )
    }
}

/**
 * Request DTO for creating/updating a budget.
 */
data class BudgetRequest(
    @SerializedName("name")
    val name: String,

    @SerializedName("category")
    val category: String,

    @SerializedName("budget_amount")
    val budgetAmount: Double,

    @SerializedName("currency")
    val currency: String = "USD",

    @SerializedName("period_type")
    val periodType: String,

    @SerializedName("start_date")
    val startDate: Long,

    @SerializedName("end_date")
    val endDate: Long,

    @SerializedName("alert_threshold")
    val alertThreshold: Double = 0.8,

    @SerializedName("color")
    val color: String? = null,

    @SerializedName("icon")
    val icon: String? = null,

    @SerializedName("notes")
    val notes: String? = null
) {
    companion object {
        /**
         * Create a request from an entity.
         */
        fun fromEntity(entity: BudgetEntity): BudgetRequest {
            return BudgetRequest(
                name = entity.name,
                category = entity.category,
                budgetAmount = entity.budgetAmount,
                currency = entity.currency,
                periodType = entity.periodType.name,
                startDate = entity.startDate,
                endDate = entity.endDate,
                alertThreshold = entity.alertThreshold,
                color = entity.color,
                icon = entity.icon,
                notes = entity.notes
            )
        }
    }
}

/**
 * Response wrapper for paginated budget list.
 */
data class BudgetListResponse(
    @SerializedName("data")
    val data: List<BudgetDto>,

    @SerializedName("total")
    val total: Int,

    @SerializedName("page")
    val page: Int,

    @SerializedName("page_size")
    val pageSize: Int,

    @SerializedName("has_more")
    val hasMore: Boolean
)

/**
 * Response wrapper for single budget.
 */
data class BudgetResponse(
    @SerializedName("data")
    val data: BudgetDto,

    @SerializedName("message")
    val message: String?
)

/**
 * Response for budget summary/overview.
 */
data class BudgetSummaryResponse(
    @SerializedName("total_budgeted")
    val totalBudgeted: Double,

    @SerializedName("total_spent")
    val totalSpent: Double,

    @SerializedName("total_remaining")
    val totalRemaining: Double,

    @SerializedName("overall_percentage")
    val overallPercentage: Double,

    @SerializedName("budgets_over_threshold")
    val budgetsOverThreshold: Int,

    @SerializedName("budgets_exceeded")
    val budgetsExceeded: Int,

    @SerializedName("active_budgets")
    val activeBudgets: Int
)

/**
 * Request to update spent amount on a budget.
 */
data class UpdateSpentAmountRequest(
    @SerializedName("spent_amount")
    val spentAmount: Double
)
