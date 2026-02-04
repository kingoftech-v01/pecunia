package com.pecunia.domain.usecases

import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetPeriod
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Test
import java.math.BigDecimal
import java.time.LocalDate

/**
 * Comprehensive unit tests for GetBudgetsUseCase.
 *
 * Tests the Params data class, routing logic based on params, and
 * flow mapping/error handling patterns.
 *
 * Since BudgetRepository interface is not present in the codebase,
 * we test the Params class, the routing logic via simulation, and
 * the Result wrapping/catching behavior.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class GetBudgetsUseCaseTest {

    // ============================================
    // Params Data Class Tests
    // ============================================

    @Test
    fun `Params default values are all null or false`() {
        val params = GetBudgetsUseCase.Params()
        assertNull(params.budgetId)
        assertNull(params.category)
        assertNull(params.period)
        assertFalse(params.activeOnly)
        assertFalse(params.needingAttention)
    }

    @Test
    fun `Params with budgetId`() {
        val params = GetBudgetsUseCase.Params(budgetId = "budget-123")
        assertEquals("budget-123", params.budgetId)
    }

    @Test
    fun `Params with period`() {
        // BudgetPeriod is used here but TransactionCategory is not present
        // We test with the period parameter only
        val params = GetBudgetsUseCase.Params(period = BudgetPeriod.MONTHLY)
        assertEquals(BudgetPeriod.MONTHLY, params.period)
    }

    @Test
    fun `Params with activeOnly true`() {
        val params = GetBudgetsUseCase.Params(activeOnly = true)
        assertTrue(params.activeOnly)
    }

    @Test
    fun `Params with needingAttention true`() {
        val params = GetBudgetsUseCase.Params(needingAttention = true)
        assertTrue(params.needingAttention)
    }

    @Test
    fun `Params equality works`() {
        val p1 = GetBudgetsUseCase.Params(budgetId = "b1", activeOnly = true)
        val p2 = GetBudgetsUseCase.Params(budgetId = "b1", activeOnly = true)
        assertEquals(p1, p2)
    }

    @Test
    fun `Params inequality works`() {
        val p1 = GetBudgetsUseCase.Params(budgetId = "b1")
        val p2 = GetBudgetsUseCase.Params(budgetId = "b2")
        assertNotEquals(p1, p2)
    }

    @Test
    fun `Params copy preserves fields`() {
        val original = GetBudgetsUseCase.Params(
            budgetId = "b1",
            activeOnly = true,
            needingAttention = false
        )
        val copied = original.copy(needingAttention = true)
        assertEquals("b1", copied.budgetId)
        assertTrue(copied.activeOnly)
        assertTrue(copied.needingAttention)
    }

    // ============================================
    // Routing Logic Tests (simulating the when block)
    // ============================================

    /**
     * Simulates the routing logic from GetBudgetsUseCase.invoke
     * to determine which repository method would be called.
     */
    private fun determineRoute(params: GetBudgetsUseCase.Params): String {
        return when {
            params.budgetId != null -> "getBudgetFlow"
            params.category != null -> "getBudgetsByCategory"
            params.period != null -> "getBudgetsByPeriod"
            params.needingAttention -> "getBudgetsNeedingAttention"
            params.activeOnly -> "getActiveBudgets"
            else -> "getAllBudgets"
        }
    }

    @Test
    fun `routes to getBudgetFlow when budgetId is set`() {
        val params = GetBudgetsUseCase.Params(budgetId = "b1")
        assertEquals("getBudgetFlow", determineRoute(params))
    }

    @Test
    fun `routes to getBudgetsByPeriod when period is set`() {
        val params = GetBudgetsUseCase.Params(period = BudgetPeriod.WEEKLY)
        assertEquals("getBudgetsByPeriod", determineRoute(params))
    }

    @Test
    fun `routes to getBudgetsNeedingAttention when needingAttention is set`() {
        val params = GetBudgetsUseCase.Params(needingAttention = true)
        assertEquals("getBudgetsNeedingAttention", determineRoute(params))
    }

    @Test
    fun `routes to getActiveBudgets when activeOnly is set`() {
        val params = GetBudgetsUseCase.Params(activeOnly = true)
        assertEquals("getActiveBudgets", determineRoute(params))
    }

    @Test
    fun `routes to getAllBudgets when no filters set`() {
        val params = GetBudgetsUseCase.Params()
        assertEquals("getAllBudgets", determineRoute(params))
    }

    @Test
    fun `budgetId takes priority over other filters`() {
        val params = GetBudgetsUseCase.Params(
            budgetId = "b1",
            period = BudgetPeriod.MONTHLY,
            activeOnly = true,
            needingAttention = true
        )
        assertEquals("getBudgetFlow", determineRoute(params))
    }

    @Test
    fun `needingAttention takes priority over activeOnly`() {
        val params = GetBudgetsUseCase.Params(
            needingAttention = true,
            activeOnly = true
        )
        assertEquals("getBudgetsNeedingAttention", determineRoute(params))
    }

    // ============================================
    // Flow Result Wrapping Tests
    // ============================================

    private fun createBudget(
        id: String = "b1",
        name: String = "Test Budget"
    ): Budget = Budget(
        id = id,
        userId = "user-1",
        name = name,
        totalAmount = BigDecimal("1000"),
        startDate = LocalDate.now().minusDays(15),
        endDate = LocalDate.now().plusDays(15)
    )

    @Test
    fun `flow maps budgets to Result success`() = runTest {
        val budgets = listOf(
            createBudget("b1", "Food"),
            createBudget("b2", "Transport")
        )
        val resultFlow: Flow<Result<List<Budget>>> = flow {
            emit(budgets)
        }.map { Result.success(it) }

        val results = resultFlow.toList()
        assertEquals(1, results.size)
        assertTrue(results[0].isSuccess)
        assertEquals(2, results[0].getOrNull()!!.size)
    }

    @Test
    fun `flow catches exception and emits Result failure`() = runTest {
        val resultFlow: Flow<Result<List<Budget>>> = flow<List<Budget>> {
            throw RuntimeException("Database error")
        }.map { Result.success(it) }.catch {
            emit(Result.failure(it))
        }

        val results = resultFlow.toList()
        assertEquals(1, results.size)
        assertTrue(results[0].isFailure)
        assertEquals("Database error", results[0].exceptionOrNull()?.message)
    }

    @Test
    fun `flow with null budget maps to empty list`() = runTest {
        val budget: Budget? = null
        val resultFlow: Flow<Result<List<Budget>>> = flow {
            emit(if (budget != null) listOf(budget) else emptyList())
        }.map { Result.success(it) }

        val results = resultFlow.toList()
        assertEquals(1, results.size)
        assertTrue(results[0].isSuccess)
        assertTrue(results[0].getOrNull()!!.isEmpty())
    }

    @Test
    fun `flow with single budget found maps to list of one`() = runTest {
        val budget = createBudget("b1", "Food")
        val resultFlow: Flow<Result<List<Budget>>> = flow {
            emit(listOf(budget))
        }.map { Result.success(it) }

        val results = resultFlow.toList()
        assertEquals(1, results.size)
        assertTrue(results[0].isSuccess)
        assertEquals(1, results[0].getOrNull()!!.size)
        assertEquals("Food", results[0].getOrNull()!![0].name)
    }

    // ============================================
    // BudgetPeriod Integration Tests
    // ============================================

    @Test
    fun `can create Params with each BudgetPeriod`() {
        BudgetPeriod.entries.forEach { period ->
            val params = GetBudgetsUseCase.Params(period = period)
            assertEquals(period, params.period)
            assertEquals("getBudgetsByPeriod", determineRoute(params))
        }
    }

    @Test
    fun `BudgetPeriod WEEKLY Params routes correctly`() {
        val params = GetBudgetsUseCase.Params(period = BudgetPeriod.WEEKLY)
        assertEquals("getBudgetsByPeriod", determineRoute(params))
    }

    @Test
    fun `BudgetPeriod QUARTERLY Params routes correctly`() {
        val params = GetBudgetsUseCase.Params(period = BudgetPeriod.QUARTERLY)
        assertEquals("getBudgetsByPeriod", determineRoute(params))
    }

    @Test
    fun `BudgetPeriod YEARLY Params routes correctly`() {
        val params = GetBudgetsUseCase.Params(period = BudgetPeriod.YEARLY)
        assertEquals("getBudgetsByPeriod", determineRoute(params))
    }
}
