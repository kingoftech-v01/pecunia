package com.pecunia.ui.screens.budgets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pecunia.data.local.dao.BudgetDao
import com.pecunia.data.local.dao.CategoryDao
import com.pecunia.data.local.entities.BudgetEntity
import com.pecunia.data.local.preferences.UserPreferences
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.time.LocalDate
import java.time.ZoneId
import java.util.UUID
import javax.inject.Inject

/**
 * ViewModel for the Budget Form screen.
 * Handles budget creation and editing with validation.
 */
@HiltViewModel
class BudgetFormViewModel @Inject constructor(
    private val budgetDao: BudgetDao,
    private val categoryDao: CategoryDao,
    private val userPreferences: UserPreferences
) : ViewModel() {

    private val _uiState = MutableStateFlow(BudgetFormState())
    val uiState: StateFlow<BudgetFormState> = _uiState.asStateFlow()

    private val _events = MutableSharedFlow<BudgetFormEvent>()
    val events: SharedFlow<BudgetFormEvent> = _events.asSharedFlow()

    private var originalBudgetId: String? = null

    init {
        loadCategories()
    }

    /**
     * Initialize form for new budget.
     */
    fun initNewBudget() {
        _uiState.update {
            BudgetFormState(
                isLoading = false,
                isEditMode = false,
                startDate = LocalDate.now().withDayOfMonth(1),
                endDate = LocalDate.now().plusMonths(1).withDayOfMonth(1).minusDays(1)
            )
        }
    }

    /**
     * Load existing budget for editing.
     */
    fun loadBudget(budgetId: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }

            try {
                val budget = budgetDao.getBudgetByIdSync(budgetId)

                if (budget != null) {
                    originalBudgetId = budgetId

                    val startDate = LocalDate.ofEpochDay(budget.startDate / (24 * 60 * 60 * 1000))
                    val endDate = LocalDate.ofEpochDay(budget.endDate / (24 * 60 * 60 * 1000))

                    val periodType = when (budget.periodType) {
                        BudgetEntity.PeriodType.DAILY -> BudgetPeriodTypeForm.DAILY
                        BudgetEntity.PeriodType.WEEKLY -> BudgetPeriodTypeForm.WEEKLY
                        BudgetEntity.PeriodType.MONTHLY -> BudgetPeriodTypeForm.MONTHLY
                        BudgetEntity.PeriodType.QUARTERLY -> BudgetPeriodTypeForm.QUARTERLY
                        BudgetEntity.PeriodType.YEARLY -> BudgetPeriodTypeForm.YEARLY
                        else -> BudgetPeriodTypeForm.CUSTOM
                    }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isEditMode = true,
                            name = budget.name,
                            amount = budget.totalPlanned.toPlainString(),
                            periodType = periodType,
                            startDate = startDate,
                            endDate = endDate,
                            alertAt50 = budget.alertThreshold50,
                            alertAt75 = budget.alertThreshold75,
                            alertAt90 = budget.alertThreshold90,
                            alertAt100 = budget.alertOverBudget
                        )
                    }

                    // Load category allocations if available
                    loadCategoryAllocations(budgetId)
                } else {
                    _events.emit(BudgetFormEvent.ShowError("Budget not found"))
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false) }
                _events.emit(BudgetFormEvent.ShowError(e.message ?: "Failed to load budget"))
            }
        }
    }

    /**
     * Load available categories.
     */
    private fun loadCategories() {
        viewModelScope.launch {
            try {
                val userId = userPreferences.getCurrentUserId() ?: return@launch

                categoryDao.getExpenseCategories(userId).collect { entities ->
                    val categories = entities.map { entity ->
                        CategoryFormItem(
                            id = entity.id.toString(),
                            name = entity.name,
                            icon = entity.icon ?: "category"
                        )
                    }

                    _uiState.update { it.copy(availableCategories = categories) }
                }
            } catch (e: Exception) {
                // Use default categories if loading fails
                val defaultCategories = listOf(
                    CategoryFormItem("1", "Food & Dining", "restaurant"),
                    CategoryFormItem("2", "Transportation", "directions_car"),
                    CategoryFormItem("3", "Shopping", "shopping_bag"),
                    CategoryFormItem("4", "Entertainment", "movie"),
                    CategoryFormItem("5", "Bills & Utilities", "receipt"),
                    CategoryFormItem("6", "Healthcare", "medical_services"),
                    CategoryFormItem("7", "Education", "school"),
                    CategoryFormItem("8", "Travel", "flight"),
                    CategoryFormItem("9", "Personal Care", "spa"),
                    CategoryFormItem("10", "Other", "more_horiz")
                )
                _uiState.update { it.copy(availableCategories = defaultCategories) }
            }
        }
    }

    /**
     * Load category allocations for existing budget.
     */
    private suspend fun loadCategoryAllocations(budgetId: String) {
        try {
            // Load allocations from database
            // This would require a CategoryAllocationDao in production
            // For now, we'll leave allocations empty
        } catch (e: Exception) {
            // Ignore errors
        }
    }

    // ==================== Form Updates ====================

    /**
     * Update budget name.
     */
    fun updateName(name: String) {
        _uiState.update {
            it.copy(
                name = name,
                errors = it.errors - "name"
            )
        }
    }

    /**
     * Update budget amount.
     */
    fun updateAmount(amount: String) {
        _uiState.update {
            it.copy(
                amount = amount,
                errors = it.errors - "amount"
            )
        }
    }

    /**
     * Update period type.
     */
    fun updatePeriodType(periodType: BudgetPeriodTypeForm) {
        val newEndDate = calculateEndDate(periodType, _uiState.value.startDate)

        _uiState.update {
            it.copy(
                periodType = periodType,
                endDate = if (periodType != BudgetPeriodTypeForm.CUSTOM) newEndDate else it.endDate
            )
        }
    }

    /**
     * Update start date.
     */
    fun updateStartDate(date: LocalDate) {
        val currentState = _uiState.value
        val newEndDate = if (currentState.periodType != BudgetPeriodTypeForm.CUSTOM) {
            calculateEndDate(currentState.periodType, date)
        } else {
            currentState.endDate
        }

        _uiState.update {
            it.copy(
                startDate = date,
                endDate = if (newEndDate.isBefore(date)) date.plusDays(1) else newEndDate,
                errors = it.errors - "date"
            )
        }
    }

    /**
     * Update end date.
     */
    fun updateEndDate(date: LocalDate) {
        _uiState.update {
            it.copy(
                endDate = date,
                errors = it.errors - "date"
            )
        }
    }

    /**
     * Update alert threshold.
     */
    fun updateAlertThreshold(percentage: Int, enabled: Boolean) {
        _uiState.update {
            when (percentage) {
                50 -> it.copy(alertAt50 = enabled)
                75 -> it.copy(alertAt75 = enabled)
                90 -> it.copy(alertAt90 = enabled)
                100 -> it.copy(alertAt100 = enabled)
                else -> it
            }
        }
    }

    /**
     * Toggle category selection.
     */
    fun toggleCategory(categoryId: String) {
        _uiState.update { state ->
            val currentAllocations = state.categoryAllocations.toMutableList()
            val existingIndex = currentAllocations.indexOfFirst { it.categoryId == categoryId }

            if (existingIndex >= 0) {
                // Remove category
                currentAllocations.removeAt(existingIndex)
            } else {
                // Add category
                val category = state.availableCategories.find { it.id == categoryId }
                if (category != null) {
                    currentAllocations.add(
                        CategoryAllocationForm(
                            categoryId = categoryId,
                            categoryName = category.name,
                            amount = ""
                        )
                    )
                }
            }

            state.copy(categoryAllocations = currentAllocations)
        }
    }

    /**
     * Update category allocation amount.
     */
    fun updateCategoryAmount(categoryId: String, amount: String) {
        _uiState.update { state ->
            val updatedAllocations = state.categoryAllocations.map { allocation ->
                if (allocation.categoryId == categoryId) {
                    allocation.copy(amount = amount)
                } else {
                    allocation
                }
            }
            state.copy(categoryAllocations = updatedAllocations)
        }
    }

    // ==================== Save ====================

    /**
     * Validate and save budget.
     */
    fun saveBudget() {
        viewModelScope.launch {
            val state = _uiState.value
            val errors = validateForm(state)

            if (errors.isNotEmpty()) {
                _uiState.update { it.copy(errors = errors) }
                _events.emit(BudgetFormEvent.ValidationError("Please fix the errors"))
                return@launch
            }

            _uiState.update { it.copy(isSaving = true) }

            try {
                val userId = userPreferences.getCurrentUserId()
                    ?: throw IllegalStateException("User not logged in")

                val startDateMillis = state.startDate
                    .atStartOfDay(ZoneId.systemDefault())
                    .toInstant()
                    .toEpochMilli()

                val endDateMillis = state.endDate
                    .atStartOfDay(ZoneId.systemDefault())
                    .toInstant()
                    .toEpochMilli()

                val periodType = when (state.periodType) {
                    BudgetPeriodTypeForm.DAILY -> BudgetEntity.PeriodType.DAILY
                    BudgetPeriodTypeForm.WEEKLY -> BudgetEntity.PeriodType.WEEKLY
                    BudgetPeriodTypeForm.MONTHLY -> BudgetEntity.PeriodType.MONTHLY
                    BudgetPeriodTypeForm.QUARTERLY -> BudgetEntity.PeriodType.QUARTERLY
                    BudgetPeriodTypeForm.YEARLY -> BudgetEntity.PeriodType.YEARLY
                    BudgetPeriodTypeForm.CUSTOM -> BudgetEntity.PeriodType.CUSTOM
                }

                val budget = BudgetEntity(
                    id = if (state.isEditMode) UUID.fromString(originalBudgetId) else UUID.randomUUID(),
                    userId = userId,
                    name = state.name.trim(),
                    totalPlanned = BigDecimal(state.amount),
                    periodType = periodType,
                    startDate = startDateMillis,
                    endDate = endDateMillis,
                    alertThreshold50 = state.alertAt50,
                    alertThreshold75 = state.alertAt75,
                    alertThreshold90 = state.alertAt90,
                    alertOverBudget = state.alertAt100,
                    isActive = true,
                    createdAt = if (state.isEditMode) {
                        budgetDao.getBudgetByIdSync(originalBudgetId!!)?.createdAt
                            ?: System.currentTimeMillis()
                    } else {
                        System.currentTimeMillis()
                    },
                    updatedAt = System.currentTimeMillis(),
                    syncStatus = BudgetEntity.SyncStatus.PENDING
                )

                if (state.isEditMode) {
                    budgetDao.update(budget)
                } else {
                    budgetDao.insert(budget)
                }

                // Save category allocations if any
                saveCategoryAllocations(budget.id.toString(), state.categoryAllocations)

                _uiState.update { it.copy(isSaving = false) }
                _events.emit(BudgetFormEvent.SaveSuccess)
            } catch (e: Exception) {
                _uiState.update { it.copy(isSaving = false) }
                _events.emit(BudgetFormEvent.ShowError(e.message ?: "Failed to save budget"))
            }
        }
    }

    /**
     * Save category allocations.
     */
    private suspend fun saveCategoryAllocations(
        budgetId: String,
        allocations: List<CategoryAllocationForm>
    ) {
        // This would save to a category_allocations table
        // Implementation depends on database schema
    }

    // ==================== Helpers ====================

    /**
     * Calculate end date based on period type and start date.
     */
    private fun calculateEndDate(periodType: BudgetPeriodTypeForm, startDate: LocalDate): LocalDate {
        return when (periodType) {
            BudgetPeriodTypeForm.DAILY -> startDate.plusDays(1)
            BudgetPeriodTypeForm.WEEKLY -> startDate.plusWeeks(1).minusDays(1)
            BudgetPeriodTypeForm.MONTHLY -> startDate.plusMonths(1).minusDays(1)
            BudgetPeriodTypeForm.QUARTERLY -> startDate.plusMonths(3).minusDays(1)
            BudgetPeriodTypeForm.YEARLY -> startDate.plusYears(1).minusDays(1)
            BudgetPeriodTypeForm.CUSTOM -> startDate.plusMonths(1).minusDays(1)
        }
    }

    /**
     * Validate form fields.
     */
    private fun validateForm(state: BudgetFormState): Map<String, String> {
        val errors = mutableMapOf<String, String>()

        if (state.name.isBlank()) {
            errors["name"] = "Budget name is required"
        } else if (state.name.length > 100) {
            errors["name"] = "Name must be less than 100 characters"
        }

        val amount = state.amount.toDoubleOrNull()
        if (state.amount.isBlank()) {
            errors["amount"] = "Budget amount is required"
        } else if (amount == null || amount <= 0) {
            errors["amount"] = "Please enter a valid amount"
        } else if (amount > 1_000_000_000) {
            errors["amount"] = "Amount is too large"
        }

        if (!state.startDate.isBefore(state.endDate)) {
            errors["date"] = "End date must be after start date"
        }

        // Validate category allocations don't exceed budget
        val totalAllocated = state.categoryAllocations.sumOf {
            it.amount.toDoubleOrNull() ?: 0.0
        }
        if (amount != null && totalAllocated > amount) {
            errors["allocations"] = "Category allocations exceed budget amount"
        }

        return errors
    }
}
