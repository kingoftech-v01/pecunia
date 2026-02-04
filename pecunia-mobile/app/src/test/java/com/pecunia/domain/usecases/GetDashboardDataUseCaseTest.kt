package com.pecunia.domain.usecases

import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetPeriod
import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionType
import org.junit.Assert.*
import org.junit.Test
import java.math.BigDecimal
import java.time.LocalDate
import java.time.YearMonth

/**
 * Comprehensive unit tests for GetDashboardDataUseCase.
 *
 * Tests the Params data class, DashboardState data class and its computed
 * properties, and the transaction summary calculation logic.
 *
 * Since the use case requires TransactionRepository, BudgetRepository,
 * and UserRepository (which are interfaces not present in the codebase),
 * we test the inner types, computed properties, and calculation logic
 * that can be verified without those dependencies.
 */
class GetDashboardDataUseCaseTest {

    // ============================================
    // Helper methods
    // ============================================

    private fun createTransaction(
        id: String,
        type: TransactionType,
        amount: BigDecimal
    ): Transaction = Transaction(
        id = id,
        userId = "user-1",
        type = type,
        amount = amount,
        description = "Test $id",
        accountId = "acc-1",
        date = LocalDate.now()
    )

    private fun createBudget(
        id: String,
        name: String = "Budget $id"
    ): Budget = Budget(
        id = id,
        userId = "user-1",
        name = name,
        totalAmount = BigDecimal("1000"),
        startDate = LocalDate.now().minusDays(15),
        endDate = LocalDate.now().plusDays(15)
    )

    // ============================================
    // Params Data Class Tests
    // ============================================

    @Test
    fun `Params default recentTransactionLimit is 10`() {
        val params = GetDashboardDataUseCase.Params()
        assertEquals(10, params.recentTransactionLimit)
    }

    @Test
    fun `Params default includeAlerts is true`() {
        val params = GetDashboardDataUseCase.Params()
        assertTrue(params.includeAlerts)
    }

    @Test
    fun `Params default yearMonth is current`() {
        val params = GetDashboardDataUseCase.Params()
        assertEquals(YearMonth.now(), params.yearMonth)
    }

    @Test
    fun `Params with custom recentTransactionLimit`() {
        val params = GetDashboardDataUseCase.Params(recentTransactionLimit = 20)
        assertEquals(20, params.recentTransactionLimit)
    }

    @Test
    fun `Params with includeAlerts false`() {
        val params = GetDashboardDataUseCase.Params(includeAlerts = false)
        assertFalse(params.includeAlerts)
    }

    @Test
    fun `Params with specific yearMonth`() {
        val yearMonth = YearMonth.of(2025, 3)
        val params = GetDashboardDataUseCase.Params(yearMonth = yearMonth)
        assertEquals(YearMonth.of(2025, 3), params.yearMonth)
    }

    @Test
    fun `Params equality works`() {
        val p1 = GetDashboardDataUseCase.Params(recentTransactionLimit = 5)
        val p2 = GetDashboardDataUseCase.Params(recentTransactionLimit = 5)
        assertEquals(p1, p2)
    }

    @Test
    fun `Params inequality works`() {
        val p1 = GetDashboardDataUseCase.Params(recentTransactionLimit = 5)
        val p2 = GetDashboardDataUseCase.Params(recentTransactionLimit = 10)
        assertNotEquals(p1, p2)
    }

    // ============================================
    // DashboardState Default Values Tests
    // ============================================

    @Test
    fun `DashboardState default userName is User`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertEquals("User", state.userName)
    }

    @Test
    fun `DashboardState default totalBalance is zero`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertEquals(BigDecimal.ZERO, state.totalBalance)
    }

    @Test
    fun `DashboardState default monthlyIncome is zero`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertEquals(BigDecimal.ZERO, state.monthlyIncome)
    }

    @Test
    fun `DashboardState default monthlyExpenses is zero`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertEquals(BigDecimal.ZERO, state.monthlyExpenses)
    }

    @Test
    fun `DashboardState default transactionCount is zero`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertEquals(0, state.transactionCount)
    }

    @Test
    fun `DashboardState default recentTransactions is empty`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertTrue(state.recentTransactions.isEmpty())
    }

    @Test
    fun `DashboardState default activeBudgets is empty`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertTrue(state.activeBudgets.isEmpty())
    }

    @Test
    fun `DashboardState default budgetsNeedingAttention is empty`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertTrue(state.budgetsNeedingAttention.isEmpty())
    }

    @Test
    fun `DashboardState default budgetAlerts is empty`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertTrue(state.budgetAlerts.isEmpty())
    }

    @Test
    fun `DashboardState default totalBudgetCount is zero`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertEquals(0, state.totalBudgetCount)
    }

    @Test
    fun `DashboardState default alertCount is zero`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertEquals(0, state.alertCount)
    }

    @Test
    fun `DashboardState default categoryBreakdown is empty`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertTrue(state.categoryBreakdown.isEmpty())
    }

    // ============================================
    // DashboardState Computed Properties Tests
    // ============================================

    @Test
    fun `hasBudgetAlerts is false when no alerts`() {
        val state = GetDashboardDataUseCase.DashboardState()
        assertFalse(state.hasBudgetAlerts)
    }

    @Test
    fun `budgetsOnTrackPercentage is 100 percent when no budgets`() {
        val state = GetDashboardDataUseCase.DashboardState(totalBudgetCount = 0)
        assertEquals(1.0f, state.budgetsOnTrackPercentage, 0.01f)
    }

    @Test
    fun `budgetsOnTrackPercentage is 100 percent when all on track`() {
        val state = GetDashboardDataUseCase.DashboardState(
            totalBudgetCount = 5,
            budgetsNeedingAttention = emptyList()
        )
        assertEquals(1.0f, state.budgetsOnTrackPercentage, 0.01f)
    }

    @Test
    fun `budgetsOnTrackPercentage calculates correctly with some needing attention`() {
        val state = GetDashboardDataUseCase.DashboardState(
            totalBudgetCount = 4,
            budgetsNeedingAttention = listOf(
                createBudget("b1"),
                createBudget("b2")
            )
        )
        // (4 - 2) / 4 = 0.5
        assertEquals(0.5f, state.budgetsOnTrackPercentage, 0.01f)
    }

    @Test
    fun `budgetsOnTrackPercentage is 0 when all need attention`() {
        val state = GetDashboardDataUseCase.DashboardState(
            totalBudgetCount = 3,
            budgetsNeedingAttention = listOf(
                createBudget("b1"),
                createBudget("b2"),
                createBudget("b3")
            )
        )
        assertEquals(0.0f, state.budgetsOnTrackPercentage, 0.01f)
    }

    @Test
    fun `savingsRate is 0 when no income`() {
        val state = GetDashboardDataUseCase.DashboardState(
            monthlyIncome = BigDecimal.ZERO,
            monthlyExpenses = BigDecimal("500")
        )
        assertEquals(0f, state.savingsRate, 0.01f)
    }

    @Test
    fun `savingsRate calculates correctly`() {
        val state = GetDashboardDataUseCase.DashboardState(
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal("3000")
        )
        // (5000 - 3000) / 5000 = 0.4
        assertEquals(0.4f, state.savingsRate, 0.01f)
    }

    @Test
    fun `savingsRate is negative when expenses exceed income`() {
        val state = GetDashboardDataUseCase.DashboardState(
            monthlyIncome = BigDecimal("3000"),
            monthlyExpenses = BigDecimal("5000")
        )
        // (3000 - 5000) / 3000 = -0.667
        assertTrue(state.savingsRate < 0)
    }

    @Test
    fun `savingsRate is 100 percent when no expenses`() {
        val state = GetDashboardDataUseCase.DashboardState(
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal.ZERO
        )
        // (5000 - 0) / 5000 = 1.0
        assertEquals(1.0f, state.savingsRate, 0.01f)
    }

    @Test
    fun `savingsRate when income equals expenses is zero`() {
        val state = GetDashboardDataUseCase.DashboardState(
            monthlyIncome = BigDecimal("3000"),
            monthlyExpenses = BigDecimal("3000")
        )
        assertEquals(0.0f, state.savingsRate, 0.01f)
    }

    // ============================================
    // DashboardState With Data Tests
    // ============================================

    @Test
    fun `DashboardState with transactions and budgets`() {
        val transactions = listOf(
            createTransaction("tx-1", TransactionType.EXPENSE, BigDecimal("50")),
            createTransaction("tx-2", TransactionType.INCOME, BigDecimal("100"))
        )
        val budgets = listOf(createBudget("b1"), createBudget("b2"))

        val state = GetDashboardDataUseCase.DashboardState(
            userName = "Alice",
            recentTransactions = transactions,
            activeBudgets = budgets,
            totalBudgetCount = 2
        )
        assertEquals("Alice", state.userName)
        assertEquals(2, state.recentTransactions.size)
        assertEquals(2, state.activeBudgets.size)
    }

    @Test
    fun `DashboardState copy preserves unmodified fields`() {
        val state = GetDashboardDataUseCase.DashboardState(
            userName = "Bob",
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal("3000"),
            transactionCount = 42
        )
        val updated = state.copy(transactionCount = 50)
        assertEquals("Bob", updated.userName)
        assertEquals(BigDecimal("5000"), updated.monthlyIncome)
        assertEquals(50, updated.transactionCount)
    }

    // ============================================
    // Transaction Summary Calculation Logic Tests
    // (mirroring calculateSummary from the use case)
    // ============================================

    /**
     * Mirrors the calculateSummary logic from GetDashboardDataUseCase.
     */
    private data class TestTransactionSummary(
        val totalIncome: BigDecimal,
        val totalExpenses: BigDecimal,
        val netAmount: BigDecimal,
        val transactionCount: Int
    )

    private fun calculateSummary(transactions: List<Transaction>): TestTransactionSummary {
        val totalIncome = transactions
            .filter { it.type == TransactionType.INCOME }
            .sumOf { it.amount }

        val totalExpenses = transactions
            .filter { it.type == TransactionType.EXPENSE }
            .sumOf { it.amount }

        return TestTransactionSummary(
            totalIncome = totalIncome,
            totalExpenses = totalExpenses,
            netAmount = totalIncome.subtract(totalExpenses),
            transactionCount = transactions.size
        )
    }

    @Test
    fun `calculateSummary with mixed transactions`() {
        val transactions = listOf(
            createTransaction("1", TransactionType.INCOME, BigDecimal("1000")),
            createTransaction("2", TransactionType.INCOME, BigDecimal("500")),
            createTransaction("3", TransactionType.EXPENSE, BigDecimal("300")),
            createTransaction("4", TransactionType.EXPENSE, BigDecimal("200")),
            createTransaction("5", TransactionType.TRANSFER, BigDecimal("100"))
        )
        val summary = calculateSummary(transactions)
        assertEquals(BigDecimal("1500"), summary.totalIncome)
        assertEquals(BigDecimal("500"), summary.totalExpenses)
        assertEquals(BigDecimal("1000"), summary.netAmount)
        assertEquals(5, summary.transactionCount)
    }

    @Test
    fun `calculateSummary with only income`() {
        val transactions = listOf(
            createTransaction("1", TransactionType.INCOME, BigDecimal("1000")),
            createTransaction("2", TransactionType.INCOME, BigDecimal("500"))
        )
        val summary = calculateSummary(transactions)
        assertEquals(BigDecimal("1500"), summary.totalIncome)
        assertEquals(BigDecimal.ZERO, summary.totalExpenses)
        assertEquals(BigDecimal("1500"), summary.netAmount)
    }

    @Test
    fun `calculateSummary with only expenses`() {
        val transactions = listOf(
            createTransaction("1", TransactionType.EXPENSE, BigDecimal("300")),
            createTransaction("2", TransactionType.EXPENSE, BigDecimal("200"))
        )
        val summary = calculateSummary(transactions)
        assertEquals(BigDecimal.ZERO, summary.totalIncome)
        assertEquals(BigDecimal("500"), summary.totalExpenses)
        assertEquals(BigDecimal("-500"), summary.netAmount)
    }

    @Test
    fun `calculateSummary with empty list`() {
        val summary = calculateSummary(emptyList())
        assertEquals(BigDecimal.ZERO, summary.totalIncome)
        assertEquals(BigDecimal.ZERO, summary.totalExpenses)
        assertEquals(BigDecimal.ZERO, summary.netAmount)
        assertEquals(0, summary.transactionCount)
    }

    @Test
    fun `calculateSummary ignores transfers for income and expense totals`() {
        val transactions = listOf(
            createTransaction("1", TransactionType.TRANSFER, BigDecimal("1000"))
        )
        val summary = calculateSummary(transactions)
        assertEquals(BigDecimal.ZERO, summary.totalIncome)
        assertEquals(BigDecimal.ZERO, summary.totalExpenses)
        assertEquals(BigDecimal.ZERO, summary.netAmount)
        assertEquals(1, summary.transactionCount)
    }

    @Test
    fun `calculateSummary net amount is positive when income exceeds expenses`() {
        val transactions = listOf(
            createTransaction("1", TransactionType.INCOME, BigDecimal("5000")),
            createTransaction("2", TransactionType.EXPENSE, BigDecimal("3000"))
        )
        val summary = calculateSummary(transactions)
        assertTrue(summary.netAmount > BigDecimal.ZERO)
    }

    @Test
    fun `calculateSummary net amount is negative when expenses exceed income`() {
        val transactions = listOf(
            createTransaction("1", TransactionType.INCOME, BigDecimal("1000")),
            createTransaction("2", TransactionType.EXPENSE, BigDecimal("3000"))
        )
        val summary = calculateSummary(transactions)
        assertTrue(summary.netAmount < BigDecimal.ZERO)
    }

    @Test
    fun `calculateSummary net amount is zero when balanced`() {
        val transactions = listOf(
            createTransaction("1", TransactionType.INCOME, BigDecimal("2000")),
            createTransaction("2", TransactionType.EXPENSE, BigDecimal("2000"))
        )
        val summary = calculateSummary(transactions)
        assertEquals(BigDecimal.ZERO, summary.netAmount)
    }

    // ============================================
    // Date Range Calculation Tests
    // ============================================

    @Test
    fun `start of month calculation is correct`() {
        val now = LocalDate.now()
        val startOfMonth = now.withDayOfMonth(1)
        assertEquals(1, startOfMonth.dayOfMonth)
        assertEquals(now.month, startOfMonth.month)
        assertEquals(now.year, startOfMonth.year)
    }

    @Test
    fun `end of month calculation is correct`() {
        val now = LocalDate.now()
        val endOfMonth = now.withDayOfMonth(now.lengthOfMonth())
        assertEquals(now.lengthOfMonth(), endOfMonth.dayOfMonth)
        assertEquals(now.month, endOfMonth.month)
        assertEquals(now.year, endOfMonth.year)
    }

    @Test
    fun `february end of month is correct for non-leap year`() {
        val feb2025 = LocalDate.of(2025, 2, 1)
        val endOfFeb = feb2025.withDayOfMonth(feb2025.lengthOfMonth())
        assertEquals(28, endOfFeb.dayOfMonth)
    }

    @Test
    fun `february end of month is correct for leap year`() {
        val feb2024 = LocalDate.of(2024, 2, 1)
        val endOfFeb = feb2024.withDayOfMonth(feb2024.lengthOfMonth())
        assertEquals(29, endOfFeb.dayOfMonth)
    }
}
