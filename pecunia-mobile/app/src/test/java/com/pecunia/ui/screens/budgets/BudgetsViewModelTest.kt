package com.pecunia.ui.screens.budgets

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for BudgetsViewModel.
 * Tests budget listing, filtering, loading states, and data population.
 * BudgetsViewModel is the same as BudgetViewModel in this codebase,
 * testing additional state management scenarios.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class BudgetsViewModelTest {

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
    // Budget List Loading
    // ============================================

    @Test
    fun `budgets are loaded on initialization`() = runTest {
        advanceUntilIdle()

        val state = viewModel.listState.value
        assertFalse(state.isLoading)
        assertTrue(state.budgets.isNotEmpty())
    }

    @Test
    fun `loading state is set correctly during load`() = runTest {
        // The init block triggers loadBudgets which sets isLoading
        advanceUntilIdle()
        assertFalse(viewModel.listState.value.isLoading)
    }

    @Test
    fun `sample budgets include all expected entries`() = runTest {
        advanceUntilIdle()

        val budgetNames = viewModel.listState.value.budgets.map { it.name }
        assertTrue(budgetNames.contains("Monthly Essentials"))
        assertTrue(budgetNames.contains("Entertainment"))
        assertTrue(budgetNames.contains("Vacation Fund"))
        assertTrue(budgetNames.contains("Emergency Fund"))
    }

    @Test
    fun `Monthly Essentials budget has correct data`() = runTest {
        advanceUntilIdle()

        val budget = viewModel.listState.value.budgets.find { it.name == "Monthly Essentials" }
        assertNotNull(budget)
        assertEquals(2000.0, budget!!.totalAmount, 0.01)
        assertEquals(1450.0, budget.spentAmount, 0.01)
        assertTrue(budget.isActive)
        assertEquals(BudgetPeriodType.MONTHLY, budget.periodType)
    }

    @Test
    fun `Entertainment budget has correct category allocations`() = runTest {
        advanceUntilIdle()

        val budget = viewModel.listState.value.budgets.find { it.name == "Entertainment" }
        assertNotNull(budget)
        assertEquals(2, budget!!.categoryAllocations.size)
    }

    @Test
    fun `Emergency Fund budget is inactive`() = runTest {
        advanceUntilIdle()

        val budget = viewModel.listState.value.budgets.find { it.name == "Emergency Fund" }
        assertNotNull(budget)
        assertFalse(budget!!.isActive)
    }

    @Test
    fun `Emergency Fund budget is over budget`() = runTest {
        advanceUntilIdle()

        val budget = viewModel.listState.value.budgets.find { it.name == "Emergency Fund" }
        assertNotNull(budget)
        assertTrue(budget!!.isOverBudget)
    }

    // ============================================
    // Filter Combination Tests
    // ============================================

    @Test
    fun `filter and search work together`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ACTIVE)
        viewModel.setSearchQuery("Monthly")

        val filtered = viewModel.listState.value.filteredBudgets
        assertTrue(filtered.all { it.isActive })
        assertTrue(filtered.all { it.name.contains("Monthly", ignoreCase = true) })
    }

    @Test
    fun `changing filter preserves search query`() = runTest {
        advanceUntilIdle()

        viewModel.setSearchQuery("Budget")
        viewModel.setFilter(BudgetFilter.ALL)

        assertEquals("Budget", viewModel.listState.value.searchQuery)
    }

    @Test
    fun `changing search preserves filter`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ACTIVE)
        viewModel.setSearchQuery("Monthly")

        assertEquals(BudgetFilter.ACTIVE, viewModel.listState.value.selectedFilter)
    }

    @Test
    fun `filtered budgets are sorted by createdAt descending`() = runTest {
        advanceUntilIdle()

        viewModel.setFilter(BudgetFilter.ALL)
        val filtered = viewModel.listState.value.filteredBudgets

        for (i in 0 until filtered.size - 1) {
            assertTrue(filtered[i].createdAt >= filtered[i + 1].createdAt)
        }
    }

    // ============================================
    // Multiple Operations Tests
    // ============================================

    @Test
    fun `creating and then deleting a budget restores original count`() = runTest {
        advanceUntilIdle()
        val originalCount = viewModel.listState.value.budgets.size

        // Create
        viewModel.initCreateForm()
        viewModel.updateName("Temporary Budget")
        viewModel.updateTotalAmount("500")
        viewModel.saveBudget()
        advanceUntilIdle()

        assertEquals(originalCount + 1, viewModel.listState.value.budgets.size)

        // Delete the new one
        val newBudget = viewModel.listState.value.budgets.find { it.name == "Temporary Budget" }
        assertNotNull(newBudget)
        viewModel.deleteBudget(newBudget!!.id)
        advanceUntilIdle()

        assertEquals(originalCount, viewModel.listState.value.budgets.size)
    }

    @Test
    fun `editing budget preserves spent amount`() = runTest {
        advanceUntilIdle()

        val existingBudget = viewModel.listState.value.budgets.first()
        val originalSpent = existingBudget.spentAmount

        viewModel.initEditForm(existingBudget.id)
        advanceUntilIdle()

        viewModel.updateName("Edited Name")
        viewModel.saveBudget()
        advanceUntilIdle()

        val updated = viewModel.listState.value.budgets.find { it.id == existingBudget.id }
        assertNotNull(updated)
        assertEquals(originalSpent, updated!!.spentAmount, 0.01)
    }

    // ============================================
    // BudgetEvent Tests
    // ============================================

    @Test
    fun `BudgetEvent ShowSnackbar contains message`() {
        val event = BudgetEvent.ShowSnackbar("Test message")
        assertEquals("Test message", event.message)
    }

    @Test
    fun `BudgetEvent NavigateToDetail contains budgetId`() {
        val event = BudgetEvent.NavigateToDetail("budget-123")
        assertEquals("budget-123", event.budgetId)
    }

    @Test
    fun `BudgetEvent NavigateToEdit contains budgetId`() {
        val event = BudgetEvent.NavigateToEdit("budget-456")
        assertEquals("budget-456", event.budgetId)
    }
}
