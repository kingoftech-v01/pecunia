package com.pecunia.ui.screens.budgets

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.time.LocalDate

/**
 * Comprehensive unit tests for BudgetViewModel.
 * Tests budget list, detail, form operations, filtering, progress calculation,
 * alerts, and sample data generation.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class BudgetViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var viewModel: BudgetViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        viewModel = BudgetViewModel()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    // ============================================
    // Initial State Tests
    // ============================================

    @Test
    fun `initial list state is loading then populated`() = runTest {
        advanceUntilIdle()

        val state = viewModel.listState.value
        assertFalse(state.isLoading)
        assertTrue(state.budgets.isNotEmpty())
    }

    @Test
    fun `initial list state has sample budgets`() = runTest {
        advanceUntilIdle()

        val state = viewModel.listState.value
        assertEquals(4, state.budgets.size)
    }

    @Test
    fun `initial detail state is empty`() {
        val state = viewModel.detailState.value
        assertNull(state.budget)
        assertFalse(state.isLoading)
        assertNull(state.error)
    }

    @Test
    fun `initial form state is default`() {
        val state = viewModel.formState.value
        assertEquals("", state.name)
        assertEquals("", state.totalAmount)
        assertEquals(BudgetPeriodType.MONTHLY, state.periodType)
        assertFalse(state.isEditMode)
    }

    // ============================================
    // Load Budgets Tests
    // ============================================

    @Test
    fun `loadBudgets populates budget list`() = runTest {
        advanceUntilIdle()

        val state = viewModel.listState.value
        assertFalse(state.isLoading)
        assertNull(state.error)
        assertTrue(state.budgets.isNotEmpty())
    }

    @Test
    fun `loadBudgets sets filtered budgets based on default filter`() = runTest {
        advanceUntilIdle()

        val state = viewModel.listState.value
        assertTrue(state.filteredBudgets.isNotEmpty())
    }

    @Test
    fun `loadBudgets generates sample data on first call`() = runTest {
        advanceUntilIdle()

        val budgets = viewModel.listState.value.budgets
        assertTrue(budgets.any { it.name == "Monthly Essentials" })
        assertTrue(budgets.any { it.name == "Entertainment" })
        assertTrue(budgets.any { it.name == "Vacation Fund" })
        assertTrue(budgets.any { it.name == "Emergency Fund" })
    }

    // ============================================
    // Filter Tests
    // ============================================

    @Test
    fun `setFilter with ALL shows all budgets`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ALL)

        val state = viewModel.listState.value
        assertEquals(BudgetFilter.ALL, state.selectedFilter)
        assertEquals(state.budgets.size, state.filteredBudgets.size)
    }

    @Test
    fun `setFilter with ACTIVE shows only active budgets`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ACTIVE)

        val state = viewModel.listState.value
        assertEquals(BudgetFilter.ACTIVE, state.selectedFilter)
        assertTrue(state.filteredBudgets.all { it.isActive })
    }

    @Test
    fun `setFilter with INACTIVE shows only inactive budgets`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.INACTIVE)

        val state = viewModel.listState.value
        assertEquals(BudgetFilter.INACTIVE, state.selectedFilter)
        assertTrue(state.filteredBudgets.all { !it.isActive })
    }

    @Test
    fun `setFilter with OVER_BUDGET shows only over-budget items`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.OVER_BUDGET)

        val state = viewModel.listState.value
        assertEquals(BudgetFilter.OVER_BUDGET, state.selectedFilter)
        assertTrue(state.filteredBudgets.all { it.isOverBudget })
    }

    @Test
    fun `setSearchQuery filters budgets by name`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ALL)
        viewModel.setSearchQuery("Entertainment")

        val state = viewModel.listState.value
        assertEquals("Entertainment", state.searchQuery)
        assertTrue(state.filteredBudgets.all { it.name.contains("Entertainment", ignoreCase = true) })
    }

    @Test
    fun `setSearchQuery with blank query shows all matching filter`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ALL)
        viewModel.setSearchQuery("")

        val state = viewModel.listState.value
        assertEquals(state.budgets.size, state.filteredBudgets.size)
    }

    @Test
    fun `setSearchQuery is case insensitive`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ALL)
        viewModel.setSearchQuery("entertainment")

        val state = viewModel.listState.value
        assertTrue(state.filteredBudgets.isNotEmpty())
    }

    @Test
    fun `setSearchQuery with non-matching query returns empty list`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ALL)
        viewModel.setSearchQuery("nonexistent")

        assertTrue(viewModel.listState.value.filteredBudgets.isEmpty())
    }

    // ============================================
    // Budget Detail Tests
    // ============================================

    @Test
    fun `loadBudgetDetail with valid id loads budget`() = runTest {
        advanceUntilIdle()

        val budgetId = viewModel.listState.value.budgets.first().id
        viewModel.loadBudgetDetail(budgetId)
        advanceUntilIdle()

        val state = viewModel.detailState.value
        assertNotNull(state.budget)
        assertEquals(budgetId, state.budget!!.id)
        assertFalse(state.isLoading)
    }

    @Test
    fun `loadBudgetDetail with invalid id shows error`() = runTest {
        advanceUntilIdle()

        viewModel.loadBudgetDetail("non-existent-id")
        advanceUntilIdle()

        val state = viewModel.detailState.value
        assertNull(state.budget)
        assertEquals("Budget not found", state.error)
    }

    @Test
    fun `showDeleteConfirmation sets flag`() {
        viewModel.showDeleteConfirmation()
        assertTrue(viewModel.detailState.value.showDeleteConfirmation)
    }

    @Test
    fun `hideDeleteConfirmation clears flag`() {
        viewModel.showDeleteConfirmation()
        viewModel.hideDeleteConfirmation()
        assertFalse(viewModel.detailState.value.showDeleteConfirmation)
    }

    // ============================================
    // Delete Budget Tests
    // ============================================

    @Test
    fun `deleteBudget removes budget from list`() = runTest {
        advanceUntilIdle()

        val initialCount = viewModel.listState.value.budgets.size
        val budgetId = viewModel.listState.value.budgets.first().id

        viewModel.deleteBudget(budgetId)
        advanceUntilIdle()

        assertTrue(viewModel.listState.value.budgets.size < initialCount)
    }

    @Test
    fun `deleteBudget emits BudgetDeleted event`() = runTest {
        advanceUntilIdle()

        val budgetId = viewModel.listState.value.budgets.first().id

        var event: BudgetEvent? = null
        val job = launch {
            event = viewModel.events.first()
        }

        viewModel.deleteBudget(budgetId)
        advanceUntilIdle()

        assertEquals(BudgetEvent.BudgetDeleted, event)
        job.cancel()
    }

    // ============================================
    // Form - Create Tests
    // ============================================

    @Test
    fun `initCreateForm resets form to defaults`() = runTest {
        advanceUntilIdle()

        viewModel.initCreateForm()

        val state = viewModel.formState.value
        assertEquals("", state.name)
        assertEquals("", state.totalAmount)
        assertFalse(state.isEditMode)
        assertNull(state.id)
    }

    @Test
    fun `initCreateForm sets start date to today`() = runTest {
        advanceUntilIdle()

        viewModel.initCreateForm()

        assertEquals(LocalDate.now(), viewModel.formState.value.startDate)
    }

    @Test
    fun `initCreateForm sets end date to one month from today`() = runTest {
        advanceUntilIdle()

        viewModel.initCreateForm()

        assertEquals(LocalDate.now().plusMonths(1), viewModel.formState.value.endDate)
    }

    @Test
    fun `initCreateForm loads available categories`() = runTest {
        advanceUntilIdle()

        viewModel.initCreateForm()

        assertTrue(viewModel.formState.value.availableCategories.isNotEmpty())
        assertEquals(10, viewModel.formState.value.availableCategories.size)
    }

    // ============================================
    // Form - Edit Tests
    // ============================================

    @Test
    fun `initEditForm loads existing budget data`() = runTest {
        advanceUntilIdle()

        val budget = viewModel.listState.value.budgets.first()
        viewModel.initEditForm(budget.id)
        advanceUntilIdle()

        val state = viewModel.formState.value
        assertEquals(budget.id, state.id)
        assertEquals(budget.name, state.name)
        assertEquals(budget.totalAmount.toString(), state.totalAmount)
        assertEquals(budget.periodType, state.periodType)
        assertTrue(state.isEditMode)
    }

    @Test
    fun `initEditForm with invalid id shows error`() = runTest {
        advanceUntilIdle()

        viewModel.initEditForm("non-existent-id")
        advanceUntilIdle()

        assertEquals("Budget not found", viewModel.formState.value.error)
    }

    // ============================================
    // Form Field Update Tests
    // ============================================

    @Test
    fun `updateName updates name and clears validation error`() {
        viewModel.updateName("My Budget")
        assertEquals("My Budget", viewModel.formState.value.name)
        assertFalse(viewModel.formState.value.validationErrors.containsKey("name"))
    }

    @Test
    fun `updateTotalAmount updates amount and clears validation error`() {
        viewModel.updateTotalAmount("1000.00")
        assertEquals("1000.00", viewModel.formState.value.totalAmount)
        assertFalse(viewModel.formState.value.validationErrors.containsKey("totalAmount"))
    }

    @Test
    fun `updatePeriodType DAILY sets end date to tomorrow`() {
        val startDate = viewModel.formState.value.startDate
        viewModel.updatePeriodType(BudgetPeriodType.DAILY)

        assertEquals(BudgetPeriodType.DAILY, viewModel.formState.value.periodType)
        assertEquals(startDate.plusDays(1), viewModel.formState.value.endDate)
    }

    @Test
    fun `updatePeriodType WEEKLY sets end date to one week later`() {
        val startDate = viewModel.formState.value.startDate
        viewModel.updatePeriodType(BudgetPeriodType.WEEKLY)

        assertEquals(startDate.plusWeeks(1), viewModel.formState.value.endDate)
    }

    @Test
    fun `updatePeriodType MONTHLY sets end date to one month later`() {
        val startDate = viewModel.formState.value.startDate
        viewModel.updatePeriodType(BudgetPeriodType.MONTHLY)

        assertEquals(startDate.plusMonths(1), viewModel.formState.value.endDate)
    }

    @Test
    fun `updatePeriodType QUARTERLY sets end date to three months later`() {
        val startDate = viewModel.formState.value.startDate
        viewModel.updatePeriodType(BudgetPeriodType.QUARTERLY)

        assertEquals(startDate.plusMonths(3), viewModel.formState.value.endDate)
    }

    @Test
    fun `updatePeriodType YEARLY sets end date to one year later`() {
        val startDate = viewModel.formState.value.startDate
        viewModel.updatePeriodType(BudgetPeriodType.YEARLY)

        assertEquals(startDate.plusYears(1), viewModel.formState.value.endDate)
    }

    @Test
    fun `updatePeriodType CUSTOM does not change end date`() {
        val originalEndDate = viewModel.formState.value.endDate
        viewModel.updatePeriodType(BudgetPeriodType.CUSTOM)

        assertEquals(originalEndDate, viewModel.formState.value.endDate)
    }

    @Test
    fun `updateStartDate updates start date and hides picker`() {
        val newDate = LocalDate.of(2025, 1, 1)
        viewModel.updateStartDate(newDate)

        assertEquals(newDate, viewModel.formState.value.startDate)
        assertFalse(viewModel.formState.value.showStartDatePicker)
    }

    @Test
    fun `updateEndDate updates end date and hides picker`() {
        val newDate = LocalDate.of(2025, 12, 31)
        viewModel.updateEndDate(newDate)

        assertEquals(newDate, viewModel.formState.value.endDate)
        assertFalse(viewModel.formState.value.showEndDatePicker)
    }

    @Test
    fun `showStartDatePicker sets flag`() {
        viewModel.showStartDatePicker()
        assertTrue(viewModel.formState.value.showStartDatePicker)
    }

    @Test
    fun `hideStartDatePicker clears flag`() {
        viewModel.showStartDatePicker()
        viewModel.hideStartDatePicker()
        assertFalse(viewModel.formState.value.showStartDatePicker)
    }

    @Test
    fun `showEndDatePicker sets flag`() {
        viewModel.showEndDatePicker()
        assertTrue(viewModel.formState.value.showEndDatePicker)
    }

    @Test
    fun `hideEndDatePicker clears flag`() {
        viewModel.showEndDatePicker()
        viewModel.hideEndDatePicker()
        assertFalse(viewModel.formState.value.showEndDatePicker)
    }

    // ============================================
    // Alert Threshold Tests
    // ============================================

    @Test
    fun `updateAlertThreshold50 updates value`() {
        viewModel.updateAlertThreshold50(false)
        assertFalse(viewModel.formState.value.alertThreshold50)

        viewModel.updateAlertThreshold50(true)
        assertTrue(viewModel.formState.value.alertThreshold50)
    }

    @Test
    fun `updateAlertThreshold75 updates value`() {
        viewModel.updateAlertThreshold75(false)
        assertFalse(viewModel.formState.value.alertThreshold75)
    }

    @Test
    fun `updateAlertThreshold90 updates value`() {
        viewModel.updateAlertThreshold90(false)
        assertFalse(viewModel.formState.value.alertThreshold90)
    }

    // ============================================
    // Category Selection Tests
    // ============================================

    @Test
    fun `toggleCategorySelection toggles selection`() = runTest {
        advanceUntilIdle()
        viewModel.initCreateForm()

        val categoryId = viewModel.formState.value.availableCategories.first().id
        val wasSelected = viewModel.formState.value.availableCategories.first().isSelected

        viewModel.toggleCategorySelection(categoryId)

        val updatedCategory = viewModel.formState.value.availableCategories.first { it.id == categoryId }
        assertEquals(!wasSelected, updatedCategory.isSelected)
    }

    @Test
    fun `toggleCategorySelection does not affect other categories`() = runTest {
        advanceUntilIdle()
        viewModel.initCreateForm()

        val categories = viewModel.formState.value.availableCategories
        val firstId = categories.first().id

        viewModel.toggleCategorySelection(firstId)

        val updated = viewModel.formState.value.availableCategories
        for (i in 1 until updated.size) {
            assertEquals(categories[i].isSelected, updated[i].isSelected)
        }
    }

    @Test
    fun `updateCategoryAllocation updates amount for specified category`() = runTest {
        advanceUntilIdle()
        viewModel.initCreateForm()

        val categoryId = viewModel.formState.value.availableCategories.first().id
        viewModel.updateCategoryAllocation(categoryId, "500.00")

        val updated = viewModel.formState.value.availableCategories.first { it.id == categoryId }
        assertEquals("500.00", updated.allocatedAmount)
    }

    // ============================================
    // Save Budget Tests
    // ============================================

    @Test
    fun `saveBudget with blank name shows validation error`() = runTest {
        advanceUntilIdle()

        viewModel.updateName("")
        viewModel.updateTotalAmount("1000")
        viewModel.saveBudget()
        advanceUntilIdle()

        assertTrue(viewModel.formState.value.validationErrors.containsKey("name"))
    }

    @Test
    fun `saveBudget with invalid amount shows validation error`() = runTest {
        advanceUntilIdle()

        viewModel.updateName("Test Budget")
        viewModel.updateTotalAmount("invalid")
        viewModel.saveBudget()
        advanceUntilIdle()

        assertTrue(viewModel.formState.value.validationErrors.containsKey("totalAmount"))
    }

    @Test
    fun `saveBudget with zero amount shows validation error`() = runTest {
        advanceUntilIdle()

        viewModel.updateName("Test Budget")
        viewModel.updateTotalAmount("0")
        viewModel.saveBudget()
        advanceUntilIdle()

        assertTrue(viewModel.formState.value.validationErrors.containsKey("totalAmount"))
    }

    @Test
    fun `saveBudget with negative amount shows validation error`() = runTest {
        advanceUntilIdle()

        viewModel.updateName("Test Budget")
        viewModel.updateTotalAmount("-100")
        viewModel.saveBudget()
        advanceUntilIdle()

        assertTrue(viewModel.formState.value.validationErrors.containsKey("totalAmount"))
    }

    @Test
    fun `saveBudget with end date before start date shows validation error`() = runTest {
        advanceUntilIdle()

        viewModel.updateName("Test Budget")
        viewModel.updateTotalAmount("1000")
        viewModel.updateStartDate(LocalDate.of(2025, 6, 1))
        viewModel.updateEndDate(LocalDate.of(2025, 1, 1))
        viewModel.saveBudget()
        advanceUntilIdle()

        assertTrue(viewModel.formState.value.validationErrors.containsKey("dates"))
    }

    @Test
    fun `saveBudget with valid data creates new budget`() = runTest {
        advanceUntilIdle()
        val initialCount = viewModel.listState.value.budgets.size

        viewModel.initCreateForm()
        viewModel.updateName("New Budget")
        viewModel.updateTotalAmount("1500")
        viewModel.saveBudget()
        advanceUntilIdle()

        assertTrue(viewModel.listState.value.budgets.size > initialCount)
    }

    @Test
    fun `saveBudget in edit mode updates existing budget`() = runTest {
        advanceUntilIdle()

        val existingBudget = viewModel.listState.value.budgets.first()
        viewModel.initEditForm(existingBudget.id)
        advanceUntilIdle()

        viewModel.updateName("Updated Budget Name")
        viewModel.saveBudget()
        advanceUntilIdle()

        val updated = viewModel.listState.value.budgets.find { it.id == existingBudget.id }
        assertNotNull(updated)
        assertEquals("Updated Budget Name", updated!!.name)
    }

    @Test
    fun `saveBudget emits BudgetSaved event`() = runTest {
        advanceUntilIdle()

        viewModel.initCreateForm()
        viewModel.updateName("New Budget")
        viewModel.updateTotalAmount("1000")

        var event: BudgetEvent? = null
        val job = launch {
            event = viewModel.events.first()
        }

        viewModel.saveBudget()
        advanceUntilIdle()

        assertEquals(BudgetEvent.BudgetSaved, event)
        job.cancel()
    }

    // ============================================
    // Progress Calculation Tests
    // ============================================

    @Test
    fun `calculateProgress returns correct percentage`() {
        val budget = Budget(
            id = "1",
            name = "Test",
            totalAmount = 1000.0,
            spentAmount = 500.0
        )
        assertEquals(50.0f, viewModel.calculateProgress(budget), 0.1f)
    }

    @Test
    fun `calculateProgress with zero total returns 0`() {
        val budget = Budget(totalAmount = 0.0, spentAmount = 0.0)
        assertEquals(0.0f, viewModel.calculateProgress(budget), 0.01f)
    }

    @Test
    fun `calculateProgress with overspend returns 100`() {
        val budget = Budget(totalAmount = 100.0, spentAmount = 200.0)
        assertEquals(100.0f, viewModel.calculateProgress(budget), 0.1f)
    }

    // ============================================
    // Alert Tests
    // ============================================

    @Test
    fun `checkAlerts for budget under 50 percent returns no alerts`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 100.0)
        val alerts = viewModel.checkAlerts(budget)
        assertTrue(alerts.isEmpty())
    }

    @Test
    fun `checkAlerts for budget at 50 percent returns LOW alert`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 500.0)
        val alerts = viewModel.checkAlerts(budget)
        assertTrue(alerts.isNotEmpty())
        assertTrue(alerts.any { it.contains("50%") })
    }

    @Test
    fun `checkAlerts for budget at 75 percent returns MEDIUM alert`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 750.0)
        val alerts = viewModel.checkAlerts(budget)
        assertTrue(alerts.isNotEmpty())
    }

    @Test
    fun `checkAlerts for budget at 90 percent returns HIGH alert`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 900.0)
        val alerts = viewModel.checkAlerts(budget)
        assertTrue(alerts.isNotEmpty())
        assertTrue(alerts.any { it.contains("Warning") })
    }

    @Test
    fun `checkAlerts for over-budget returns CRITICAL alert`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 1200.0)
        val alerts = viewModel.checkAlerts(budget)
        assertTrue(alerts.isNotEmpty())
        assertTrue(alerts.any { it.contains("exceeded") })
    }

    @Test
    fun `checkAlerts includes over-allocated category alerts`() {
        val budget = Budget(
            totalAmount = 1000.0,
            spentAmount = 500.0,
            categoryAllocations = listOf(
                CategoryAllocation("1", "Food", "food", 200.0, 300.0)
            )
        )
        val alerts = viewModel.checkAlerts(budget)
        assertTrue(alerts.any { it.contains("Food") && it.contains("over budget") })
    }

    // ============================================
    // getDaysRemaining Tests
    // ============================================

    @Test
    fun `getDaysRemaining for future end date returns positive value`() {
        val budget = Budget(endDate = LocalDate.now().plusDays(10))
        val remaining = viewModel.getDaysRemaining(budget)
        assertEquals(10L, remaining)
    }

    @Test
    fun `getDaysRemaining for past end date returns 0`() {
        val budget = Budget(endDate = LocalDate.now().minusDays(5))
        val remaining = viewModel.getDaysRemaining(budget)
        assertEquals(0L, remaining)
    }

    @Test
    fun `getDaysRemaining for today returns 0`() {
        val budget = Budget(endDate = LocalDate.now())
        val remaining = viewModel.getDaysRemaining(budget)
        assertEquals(0L, remaining)
    }

    // ============================================
    // getDailySpendingLimit Tests
    // ============================================

    @Test
    fun `getDailySpendingLimit calculates correctly`() {
        val budget = Budget(
            totalAmount = 1000.0,
            spentAmount = 500.0,
            endDate = LocalDate.now().plusDays(10)
        )
        val limit = viewModel.getDailySpendingLimit(budget)
        assertEquals(50.0, limit, 0.01)
    }

    @Test
    fun `getDailySpendingLimit for past budget returns 0`() {
        val budget = Budget(
            totalAmount = 1000.0,
            spentAmount = 500.0,
            endDate = LocalDate.now().minusDays(1)
        )
        val limit = viewModel.getDailySpendingLimit(budget)
        assertEquals(0.0, limit, 0.01)
    }

    @Test
    fun `getDailySpendingLimit for over-budget returns negative divided value`() {
        val budget = Budget(
            totalAmount = 100.0,
            spentAmount = 200.0,
            endDate = LocalDate.now().plusDays(10)
        )
        val limit = viewModel.getDailySpendingLimit(budget)
        assertTrue(limit < 0)
    }

    // ============================================
    // Budget Model Tests
    // ============================================

    @Test
    fun `Budget remainingAmount is total minus spent`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 300.0)
        assertEquals(700.0, budget.remainingAmount, 0.01)
    }

    @Test
    fun `Budget progressPercentage is capped at 100`() {
        val budget = Budget(totalAmount = 100.0, spentAmount = 200.0)
        assertEquals(100.0f, budget.progressPercentage, 0.01f)
    }

    @Test
    fun `Budget progressPercentage is 0 when total is 0`() {
        val budget = Budget(totalAmount = 0.0, spentAmount = 0.0)
        assertEquals(0.0f, budget.progressPercentage, 0.01f)
    }

    @Test
    fun `Budget isOverBudget returns true when spent exceeds total`() {
        val budget = Budget(totalAmount = 100.0, spentAmount = 150.0)
        assertTrue(budget.isOverBudget)
    }

    @Test
    fun `Budget isOverBudget returns false when spent is less than total`() {
        val budget = Budget(totalAmount = 100.0, spentAmount = 50.0)
        assertFalse(budget.isOverBudget)
    }

    @Test
    fun `Budget currentAlertLevel NONE when under 50 percent`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 100.0)
        assertEquals(AlertLevel.NONE, budget.currentAlertLevel)
    }

    @Test
    fun `Budget currentAlertLevel LOW at 50 percent`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 500.0)
        assertEquals(AlertLevel.LOW, budget.currentAlertLevel)
    }

    @Test
    fun `Budget currentAlertLevel MEDIUM at 75 percent`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 750.0)
        assertEquals(AlertLevel.MEDIUM, budget.currentAlertLevel)
    }

    @Test
    fun `Budget currentAlertLevel HIGH at 90 percent`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 900.0)
        assertEquals(AlertLevel.HIGH, budget.currentAlertLevel)
    }

    @Test
    fun `Budget currentAlertLevel CRITICAL at 100 percent`() {
        val budget = Budget(totalAmount = 1000.0, spentAmount = 1000.0)
        assertEquals(AlertLevel.CRITICAL, budget.currentAlertLevel)
    }

    // ============================================
    // CategoryAllocation Model Tests
    // ============================================

    @Test
    fun `CategoryAllocation remainingAmount is correct`() {
        val allocation = CategoryAllocation("1", "Food", "food", 200.0, 150.0)
        assertEquals(50.0, allocation.remainingAmount, 0.01)
    }

    @Test
    fun `CategoryAllocation progressPercentage is correct`() {
        val allocation = CategoryAllocation("1", "Food", "food", 200.0, 100.0)
        assertEquals(50.0f, allocation.progressPercentage, 0.01f)
    }

    @Test
    fun `CategoryAllocation isOverAllocated true when spent exceeds allocated`() {
        val allocation = CategoryAllocation("1", "Food", "food", 100.0, 150.0)
        assertTrue(allocation.isOverAllocated)
    }

    @Test
    fun `CategoryAllocation isOverAllocated false when under limit`() {
        val allocation = CategoryAllocation("1", "Food", "food", 100.0, 50.0)
        assertFalse(allocation.isOverAllocated)
    }

    @Test
    fun `CategoryAllocation progressPercentage is 0 when allocated is 0`() {
        val allocation = CategoryAllocation("1", "Food", "food", 0.0, 0.0)
        assertEquals(0.0f, allocation.progressPercentage, 0.01f)
    }

    // ============================================
    // BudgetFormUiState Model Tests
    // ============================================

    @Test
    fun `BudgetFormUiState isValid with valid data`() {
        val state = BudgetFormUiState(
            name = "Budget",
            totalAmount = "1000",
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 2, 1)
        )
        assertTrue(state.isValid)
    }

    @Test
    fun `BudgetFormUiState isValid false with blank name`() {
        val state = BudgetFormUiState(name = "", totalAmount = "1000")
        assertFalse(state.isValid)
    }

    @Test
    fun `BudgetFormUiState isValid false with invalid amount`() {
        val state = BudgetFormUiState(name = "Budget", totalAmount = "invalid")
        assertFalse(state.isValid)
    }

    @Test
    fun `BudgetFormUiState isValid false with zero amount`() {
        val state = BudgetFormUiState(name = "Budget", totalAmount = "0")
        assertFalse(state.isValid)
    }

    @Test
    fun `BudgetFormUiState alertThresholds reflects enabled thresholds`() {
        val state = BudgetFormUiState(
            alertThreshold50 = true,
            alertThreshold75 = false,
            alertThreshold90 = true
        )
        assertEquals(listOf(50, 90), state.alertThresholds)
    }

    @Test
    fun `BudgetFormUiState alertThresholds empty when all disabled`() {
        val state = BudgetFormUiState(
            alertThreshold50 = false,
            alertThreshold75 = false,
            alertThreshold90 = false
        )
        assertTrue(state.alertThresholds.isEmpty())
    }

    // ============================================
    // BudgetFilter Enum Tests
    // ============================================

    @Test
    fun `BudgetFilter ALL has correct display name`() {
        assertEquals("All", BudgetFilter.ALL.displayName)
    }

    @Test
    fun `BudgetFilter ACTIVE has correct display name`() {
        assertEquals("Active", BudgetFilter.ACTIVE.displayName)
    }

    @Test
    fun `BudgetFilter INACTIVE has correct display name`() {
        assertEquals("Inactive", BudgetFilter.INACTIVE.displayName)
    }

    @Test
    fun `BudgetFilter OVER_BUDGET has correct display name`() {
        assertEquals("Over Budget", BudgetFilter.OVER_BUDGET.displayName)
    }

    // ============================================
    // BudgetPeriodType Enum Tests
    // ============================================

    @Test
    fun `BudgetPeriodType DAILY has correct display name`() {
        assertEquals("Daily", BudgetPeriodType.DAILY.displayName)
    }

    @Test
    fun `BudgetPeriodType WEEKLY has correct display name`() {
        assertEquals("Weekly", BudgetPeriodType.WEEKLY.displayName)
    }

    @Test
    fun `BudgetPeriodType MONTHLY has correct display name`() {
        assertEquals("Monthly", BudgetPeriodType.MONTHLY.displayName)
    }

    @Test
    fun `BudgetPeriodType QUARTERLY has correct display name`() {
        assertEquals("Quarterly", BudgetPeriodType.QUARTERLY.displayName)
    }

    @Test
    fun `BudgetPeriodType YEARLY has correct display name`() {
        assertEquals("Yearly", BudgetPeriodType.YEARLY.displayName)
    }

    @Test
    fun `BudgetPeriodType CUSTOM has correct display name`() {
        assertEquals("Custom", BudgetPeriodType.CUSTOM.displayName)
    }
}
