package com.pecunia.ui.screens.budgets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.util.UUID

/**
 * ViewModel for budget management screens
 */
class BudgetViewModel : ViewModel() {

    // Budget List State
    private val _listState = MutableStateFlow(BudgetListUiState())
    val listState: StateFlow<BudgetListUiState> = _listState.asStateFlow()

    // Budget Detail State
    private val _detailState = MutableStateFlow(BudgetDetailUiState())
    val detailState: StateFlow<BudgetDetailUiState> = _detailState.asStateFlow()

    // Budget Form State
    private val _formState = MutableStateFlow(BudgetFormUiState())
    val formState: StateFlow<BudgetFormUiState> = _formState.asStateFlow()

    // Events
    private val _events = MutableSharedFlow<BudgetEvent>()
    val events = _events.asSharedFlow()

    // In-memory budget storage (replace with repository in production)
    private val budgets = mutableListOf<Budget>()

    init {
        loadBudgets()
        loadAvailableCategories()
    }

    // ==================== List Screen Operations ====================

    /**
     * Load all budgets
     */
    fun loadBudgets() {
        viewModelScope.launch {
            _listState.update { it.copy(isLoading = true, error = null) }
            try {
                // Simulate loading - replace with repository call
                kotlinx.coroutines.delay(300)

                // Add sample data if empty
                if (budgets.isEmpty()) {
                    budgets.addAll(generateSampleBudgets())
                }

                _listState.update { state ->
                    state.copy(
                        budgets = budgets.toList(),
                        filteredBudgets = filterBudgets(budgets, state.selectedFilter, state.searchQuery),
                        isLoading = false
                    )
                }
            } catch (e: Exception) {
                _listState.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    /**
     * Set filter for budget list
     */
    fun setFilter(filter: BudgetFilter) {
        _listState.update { state ->
            state.copy(
                selectedFilter = filter,
                filteredBudgets = filterBudgets(state.budgets, filter, state.searchQuery)
            )
        }
    }

    /**
     * Set search query
     */
    fun setSearchQuery(query: String) {
        _listState.update { state ->
            state.copy(
                searchQuery = query,
                filteredBudgets = filterBudgets(state.budgets, state.selectedFilter, query)
            )
        }
    }

    private fun filterBudgets(budgets: List<Budget>, filter: BudgetFilter, query: String): List<Budget> {
        return budgets
            .filter { budget ->
                when (filter) {
                    BudgetFilter.ALL -> true
                    BudgetFilter.ACTIVE -> budget.isActive
                    BudgetFilter.INACTIVE -> !budget.isActive
                    BudgetFilter.OVER_BUDGET -> budget.isOverBudget
                }
            }
            .filter { budget ->
                query.isBlank() || budget.name.contains(query, ignoreCase = true)
            }
            .sortedByDescending { it.createdAt }
    }

    // ==================== Detail Screen Operations ====================

    /**
     * Load budget details
     */
    fun loadBudgetDetail(budgetId: String) {
        viewModelScope.launch {
            _detailState.update { it.copy(isLoading = true, error = null) }
            try {
                kotlinx.coroutines.delay(200)
                val budget = budgets.find { it.id == budgetId }
                if (budget != null) {
                    _detailState.update { it.copy(budget = budget, isLoading = false) }
                } else {
                    _detailState.update { it.copy(isLoading = false, error = "Budget not found") }
                }
            } catch (e: Exception) {
                _detailState.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    /**
     * Show delete confirmation dialog
     */
    fun showDeleteConfirmation() {
        _detailState.update { it.copy(showDeleteConfirmation = true) }
    }

    /**
     * Hide delete confirmation dialog
     */
    fun hideDeleteConfirmation() {
        _detailState.update { it.copy(showDeleteConfirmation = false) }
    }

    /**
     * Delete budget
     */
    fun deleteBudget(budgetId: String) {
        viewModelScope.launch {
            try {
                budgets.removeAll { it.id == budgetId }
                _events.emit(BudgetEvent.BudgetDeleted)
                _events.emit(BudgetEvent.ShowSnackbar("Budget deleted successfully"))
                loadBudgets()
            } catch (e: Exception) {
                _events.emit(BudgetEvent.ShowSnackbar("Failed to delete budget: ${e.message}"))
            }
        }
    }

    // ==================== Form Screen Operations ====================

    /**
     * Initialize form for creating a new budget
     */
    fun initCreateForm() {
        _formState.update {
            BudgetFormUiState(
                startDate = LocalDate.now(),
                endDate = LocalDate.now().plusMonths(1),
                isEditMode = false
            )
        }
        loadAvailableCategories()
    }

    /**
     * Initialize form for editing an existing budget
     */
    fun initEditForm(budgetId: String) {
        viewModelScope.launch {
            _formState.update { it.copy(isLoading = true) }
            try {
                val budget = budgets.find { it.id == budgetId }
                if (budget != null) {
                    _formState.update {
                        BudgetFormUiState(
                            id = budget.id,
                            name = budget.name,
                            totalAmount = budget.totalAmount.toString(),
                            periodType = budget.periodType,
                            startDate = budget.startDate,
                            endDate = budget.endDate,
                            categoryAllocations = budget.categoryAllocations,
                            alertThreshold50 = budget.alertThresholds.contains(50),
                            alertThreshold75 = budget.alertThresholds.contains(75),
                            alertThreshold90 = budget.alertThresholds.contains(90),
                            isEditMode = true,
                            isLoading = false
                        )
                    }
                    loadAvailableCategories()
                } else {
                    _formState.update { it.copy(isLoading = false, error = "Budget not found") }
                }
            } catch (e: Exception) {
                _formState.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    /**
     * Load available categories for allocation
     */
    private fun loadAvailableCategories() {
        val categories = listOf(
            CategoryOption("1", "Food & Dining", "restaurant"),
            CategoryOption("2", "Transportation", "directions_car"),
            CategoryOption("3", "Shopping", "shopping_bag"),
            CategoryOption("4", "Entertainment", "movie"),
            CategoryOption("5", "Bills & Utilities", "receipt"),
            CategoryOption("6", "Healthcare", "medical_services"),
            CategoryOption("7", "Education", "school"),
            CategoryOption("8", "Travel", "flight"),
            CategoryOption("9", "Personal Care", "spa"),
            CategoryOption("10", "Other", "more_horiz")
        )

        val currentAllocations = _formState.value.categoryAllocations
        val updatedCategories = categories.map { category ->
            val allocation = currentAllocations.find { it.categoryId == category.id }
            category.copy(
                isSelected = allocation != null,
                allocatedAmount = allocation?.allocatedAmount?.toString() ?: ""
            )
        }

        _formState.update { it.copy(availableCategories = updatedCategories) }
    }

    /**
     * Update form field
     */
    fun updateName(name: String) {
        _formState.update { it.copy(name = name, validationErrors = it.validationErrors - "name") }
    }

    fun updateTotalAmount(amount: String) {
        _formState.update { it.copy(totalAmount = amount, validationErrors = it.validationErrors - "totalAmount") }
    }

    fun updatePeriodType(periodType: BudgetPeriodType) {
        val newEndDate = when (periodType) {
            BudgetPeriodType.DAILY -> _formState.value.startDate.plusDays(1)
            BudgetPeriodType.WEEKLY -> _formState.value.startDate.plusWeeks(1)
            BudgetPeriodType.MONTHLY -> _formState.value.startDate.plusMonths(1)
            BudgetPeriodType.QUARTERLY -> _formState.value.startDate.plusMonths(3)
            BudgetPeriodType.YEARLY -> _formState.value.startDate.plusYears(1)
            BudgetPeriodType.CUSTOM -> _formState.value.endDate
        }
        _formState.update { it.copy(periodType = periodType, endDate = newEndDate) }
    }

    fun updateStartDate(date: LocalDate) {
        _formState.update {
            it.copy(
                startDate = date,
                showStartDatePicker = false,
                validationErrors = it.validationErrors - "dates"
            )
        }
    }

    fun updateEndDate(date: LocalDate) {
        _formState.update {
            it.copy(
                endDate = date,
                showEndDatePicker = false,
                validationErrors = it.validationErrors - "dates"
            )
        }
    }

    fun showStartDatePicker() {
        _formState.update { it.copy(showStartDatePicker = true) }
    }

    fun hideStartDatePicker() {
        _formState.update { it.copy(showStartDatePicker = false) }
    }

    fun showEndDatePicker() {
        _formState.update { it.copy(showEndDatePicker = true) }
    }

    fun hideEndDatePicker() {
        _formState.update { it.copy(showEndDatePicker = false) }
    }

    fun updateAlertThreshold50(enabled: Boolean) {
        _formState.update { it.copy(alertThreshold50 = enabled) }
    }

    fun updateAlertThreshold75(enabled: Boolean) {
        _formState.update { it.copy(alertThreshold75 = enabled) }
    }

    fun updateAlertThreshold90(enabled: Boolean) {
        _formState.update { it.copy(alertThreshold90 = enabled) }
    }

    /**
     * Toggle category selection
     */
    fun toggleCategorySelection(categoryId: String) {
        _formState.update { state ->
            val updatedCategories = state.availableCategories.map { category ->
                if (category.id == categoryId) {
                    category.copy(isSelected = !category.isSelected)
                } else {
                    category
                }
            }
            state.copy(availableCategories = updatedCategories)
        }
    }

    /**
     * Update category allocation amount
     */
    fun updateCategoryAllocation(categoryId: String, amount: String) {
        _formState.update { state ->
            val updatedCategories = state.availableCategories.map { category ->
                if (category.id == categoryId) {
                    category.copy(allocatedAmount = amount)
                } else {
                    category
                }
            }
            state.copy(availableCategories = updatedCategories)
        }
    }

    /**
     * Validate and save budget
     */
    fun saveBudget() {
        viewModelScope.launch {
            val state = _formState.value
            val errors = mutableMapOf<String, String>()

            // Validation
            if (state.name.isBlank()) {
                errors["name"] = "Name is required"
            }

            val amount = state.totalAmount.toDoubleOrNull()
            if (amount == null || amount <= 0) {
                errors["totalAmount"] = "Valid amount is required"
            }

            if (!state.startDate.isBefore(state.endDate)) {
                errors["dates"] = "End date must be after start date"
            }

            if (errors.isNotEmpty()) {
                _formState.update { it.copy(validationErrors = errors) }
                return@launch
            }

            _formState.update { it.copy(isSaving = true) }

            try {
                kotlinx.coroutines.delay(300)

                // Build category allocations from selected categories
                val allocations = state.availableCategories
                    .filter { it.isSelected && it.allocatedAmount.toDoubleOrNull() != null }
                    .map { category ->
                        CategoryAllocation(
                            categoryId = category.id,
                            categoryName = category.name,
                            categoryIcon = category.icon,
                            allocatedAmount = category.allocatedAmount.toDouble()
                        )
                    }

                val budget = Budget(
                    id = state.id ?: UUID.randomUUID().toString(),
                    name = state.name,
                    totalAmount = amount!!,
                    spentAmount = if (state.isEditMode) {
                        budgets.find { it.id == state.id }?.spentAmount ?: 0.0
                    } else 0.0,
                    periodType = state.periodType,
                    startDate = state.startDate,
                    endDate = state.endDate,
                    categoryAllocations = allocations,
                    alertThresholds = state.alertThresholds,
                    isActive = true
                )

                if (state.isEditMode) {
                    val index = budgets.indexOfFirst { it.id == state.id }
                    if (index >= 0) {
                        budgets[index] = budget
                    }
                } else {
                    budgets.add(budget)
                }

                _formState.update { it.copy(isSaving = false) }
                _events.emit(BudgetEvent.BudgetSaved)
                _events.emit(BudgetEvent.ShowSnackbar(
                    if (state.isEditMode) "Budget updated successfully" else "Budget created successfully"
                ))
                loadBudgets()
            } catch (e: Exception) {
                _formState.update { it.copy(isSaving = false, error = e.message) }
                _events.emit(BudgetEvent.ShowSnackbar("Failed to save budget: ${e.message}"))
            }
        }
    }

    // ==================== Progress Calculation ====================

    /**
     * Calculate overall budget progress
     */
    fun calculateProgress(budget: Budget): Float {
        return budget.progressPercentage
    }

    /**
     * Check if budget needs alert
     */
    fun checkAlerts(budget: Budget): List<String> {
        val alerts = mutableListOf<String>()

        when (budget.currentAlertLevel) {
            AlertLevel.CRITICAL -> alerts.add("Budget exceeded! You've spent ${String.format("%.1f", budget.progressPercentage)}% of your budget.")
            AlertLevel.HIGH -> alerts.add("Warning: You've used ${String.format("%.1f", budget.progressPercentage)}% of your budget.")
            AlertLevel.MEDIUM -> alerts.add("Heads up: You've used ${String.format("%.1f", budget.progressPercentage)}% of your budget.")
            AlertLevel.LOW -> alerts.add("You've reached 50% of your budget.")
            AlertLevel.NONE -> { /* No alert */ }
        }

        // Check category-specific alerts
        budget.categoryAllocations.filter { it.isOverAllocated }.forEach { category ->
            alerts.add("${category.categoryName} is over budget!")
        }

        return alerts
    }

    /**
     * Get days remaining in budget period
     */
    fun getDaysRemaining(budget: Budget): Long {
        val today = LocalDate.now()
        return if (today.isBefore(budget.endDate)) {
            java.time.temporal.ChronoUnit.DAYS.between(today, budget.endDate)
        } else {
            0
        }
    }

    /**
     * Calculate daily spending limit
     */
    fun getDailySpendingLimit(budget: Budget): Double {
        val daysRemaining = getDaysRemaining(budget)
        return if (daysRemaining > 0) {
            budget.remainingAmount / daysRemaining
        } else {
            0.0
        }
    }

    // ==================== Sample Data ====================

    private fun generateSampleBudgets(): List<Budget> {
        return listOf(
            Budget(
                id = UUID.randomUUID().toString(),
                name = "Monthly Essentials",
                totalAmount = 2000.0,
                spentAmount = 1450.0,
                periodType = BudgetPeriodType.MONTHLY,
                startDate = LocalDate.now().withDayOfMonth(1),
                endDate = LocalDate.now().withDayOfMonth(1).plusMonths(1).minusDays(1),
                categoryAllocations = listOf(
                    CategoryAllocation("1", "Food & Dining", "restaurant", 600.0, 520.0),
                    CategoryAllocation("3", "Shopping", "shopping_bag", 400.0, 380.0),
                    CategoryAllocation("5", "Bills & Utilities", "receipt", 500.0, 450.0),
                    CategoryAllocation("2", "Transportation", "directions_car", 300.0, 100.0),
                    CategoryAllocation("10", "Other", "more_horiz", 200.0, 0.0)
                ),
                isActive = true
            ),
            Budget(
                id = UUID.randomUUID().toString(),
                name = "Entertainment",
                totalAmount = 500.0,
                spentAmount = 320.0,
                periodType = BudgetPeriodType.MONTHLY,
                startDate = LocalDate.now().withDayOfMonth(1),
                endDate = LocalDate.now().withDayOfMonth(1).plusMonths(1).minusDays(1),
                categoryAllocations = listOf(
                    CategoryAllocation("4", "Entertainment", "movie", 300.0, 200.0),
                    CategoryAllocation("9", "Personal Care", "spa", 200.0, 120.0)
                ),
                isActive = true
            ),
            Budget(
                id = UUID.randomUUID().toString(),
                name = "Vacation Fund",
                totalAmount = 3000.0,
                spentAmount = 800.0,
                periodType = BudgetPeriodType.QUARTERLY,
                startDate = LocalDate.now().withDayOfMonth(1),
                endDate = LocalDate.now().withDayOfMonth(1).plusMonths(3).minusDays(1),
                categoryAllocations = listOf(
                    CategoryAllocation("8", "Travel", "flight", 2000.0, 500.0),
                    CategoryAllocation("4", "Entertainment", "movie", 500.0, 150.0),
                    CategoryAllocation("1", "Food & Dining", "restaurant", 500.0, 150.0)
                ),
                isActive = true
            ),
            Budget(
                id = UUID.randomUUID().toString(),
                name = "Emergency Fund",
                totalAmount = 1000.0,
                spentAmount = 1100.0,
                periodType = BudgetPeriodType.MONTHLY,
                startDate = LocalDate.now().minusMonths(1).withDayOfMonth(1),
                endDate = LocalDate.now().withDayOfMonth(1).minusDays(1),
                categoryAllocations = listOf(
                    CategoryAllocation("6", "Healthcare", "medical_services", 500.0, 600.0),
                    CategoryAllocation("10", "Other", "more_horiz", 500.0, 500.0)
                ),
                isActive = false
            )
        )
    }
}
