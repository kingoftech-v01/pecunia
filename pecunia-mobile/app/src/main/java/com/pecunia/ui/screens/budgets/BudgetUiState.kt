package com.pecunia.ui.screens.budgets

import java.time.LocalDate

/**
 * Represents a budget entity
 */
data class Budget(
    val id: String = "",
    val name: String = "",
    val totalAmount: Double = 0.0,
    val spentAmount: Double = 0.0,
    val periodType: BudgetPeriodType = BudgetPeriodType.MONTHLY,
    val startDate: LocalDate = LocalDate.now(),
    val endDate: LocalDate = LocalDate.now().plusMonths(1),
    val categoryAllocations: List<CategoryAllocation> = emptyList(),
    val alertThresholds: List<Int> = listOf(50, 75, 90),
    val isActive: Boolean = true,
    val createdAt: Long = System.currentTimeMillis()
) {
    val remainingAmount: Double
        get() = totalAmount - spentAmount

    val progressPercentage: Float
        get() = if (totalAmount > 0) (spentAmount / totalAmount * 100).toFloat().coerceIn(0f, 100f) else 0f

    val isOverBudget: Boolean
        get() = spentAmount > totalAmount

    val currentAlertLevel: AlertLevel
        get() = when {
            progressPercentage >= 100 -> AlertLevel.CRITICAL
            progressPercentage >= (alertThresholds.getOrNull(2) ?: 90) -> AlertLevel.HIGH
            progressPercentage >= (alertThresholds.getOrNull(1) ?: 75) -> AlertLevel.MEDIUM
            progressPercentage >= (alertThresholds.getOrNull(0) ?: 50) -> AlertLevel.LOW
            else -> AlertLevel.NONE
        }
}

/**
 * Budget period types
 */
enum class BudgetPeriodType(val displayName: String) {
    DAILY("Daily"),
    WEEKLY("Weekly"),
    MONTHLY("Monthly"),
    QUARTERLY("Quarterly"),
    YEARLY("Yearly"),
    CUSTOM("Custom")
}

/**
 * Alert levels for budget progress
 */
enum class AlertLevel {
    NONE,
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL
}

/**
 * Category allocation within a budget
 */
data class CategoryAllocation(
    val categoryId: String,
    val categoryName: String,
    val categoryIcon: String = "category",
    val allocatedAmount: Double,
    val spentAmount: Double = 0.0
) {
    val remainingAmount: Double
        get() = allocatedAmount - spentAmount

    val progressPercentage: Float
        get() = if (allocatedAmount > 0) (spentAmount / allocatedAmount * 100).toFloat().coerceIn(0f, 100f) else 0f

    val isOverAllocated: Boolean
        get() = spentAmount > allocatedAmount
}

/**
 * Filter options for budget list
 */
enum class BudgetFilter(val displayName: String) {
    ALL("All"),
    ACTIVE("Active"),
    INACTIVE("Inactive"),
    OVER_BUDGET("Over Budget")
}

/**
 * UI state for budget list screen
 */
data class BudgetListUiState(
    val budgets: List<Budget> = emptyList(),
    val filteredBudgets: List<Budget> = emptyList(),
    val selectedFilter: BudgetFilter = BudgetFilter.ACTIVE,
    val isLoading: Boolean = false,
    val error: String? = null,
    val searchQuery: String = ""
)

/**
 * UI state for budget detail screen
 */
data class BudgetDetailUiState(
    val budget: Budget? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
    val showDeleteConfirmation: Boolean = false
)

/**
 * UI state for budget form screen
 */
data class BudgetFormUiState(
    val id: String? = null,
    val name: String = "",
    val totalAmount: String = "",
    val periodType: BudgetPeriodType = BudgetPeriodType.MONTHLY,
    val startDate: LocalDate = LocalDate.now(),
    val endDate: LocalDate = LocalDate.now().plusMonths(1),
    val categoryAllocations: List<CategoryAllocation> = emptyList(),
    val alertThreshold50: Boolean = true,
    val alertThreshold75: Boolean = true,
    val alertThreshold90: Boolean = true,
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val error: String? = null,
    val validationErrors: Map<String, String> = emptyMap(),
    val isEditMode: Boolean = false,
    val showStartDatePicker: Boolean = false,
    val showEndDatePicker: Boolean = false,
    val availableCategories: List<CategoryOption> = emptyList()
) {
    val isValid: Boolean
        get() = name.isNotBlank() &&
                totalAmount.toDoubleOrNull() != null &&
                totalAmount.toDoubleOrNull()!! > 0 &&
                startDate.isBefore(endDate)

    val alertThresholds: List<Int>
        get() = buildList {
            if (alertThreshold50) add(50)
            if (alertThreshold75) add(75)
            if (alertThreshold90) add(90)
        }
}

/**
 * Category option for selection
 */
data class CategoryOption(
    val id: String,
    val name: String,
    val icon: String = "category",
    val isSelected: Boolean = false,
    val allocatedAmount: String = ""
)

/**
 * Events for budget screens
 */
sealed class BudgetEvent {
    data class ShowSnackbar(val message: String) : BudgetEvent()
    data class NavigateToDetail(val budgetId: String) : BudgetEvent()
    data object NavigateToCreate : BudgetEvent()
    data class NavigateToEdit(val budgetId: String) : BudgetEvent()
    data object NavigateBack : BudgetEvent()
    data object BudgetDeleted : BudgetEvent()
    data object BudgetSaved : BudgetEvent()
}
