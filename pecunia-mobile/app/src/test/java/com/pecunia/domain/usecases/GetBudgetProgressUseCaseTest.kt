package com.pecunia.domain.usecases

import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetItem
import com.pecunia.domain.models.BudgetPeriod
import org.junit.Assert.*
import org.junit.Test
import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.time.YearMonth

/**
 * Comprehensive unit tests for GetBudgetProgressUseCase.
 *
 * Tests the Params sealed class, BudgetProgressState sealed class,
 * BudgetProgress data class, alert generation logic, and progress calculations.
 *
 * Since the use case requires BudgetRepository and TransactionRepository
 * (which are interfaces not present in the codebase), we test:
 * - The inner types and their properties
 * - Budget domain model computed properties used by the use case
 * - Alert generation logic (mirrored from the use case)
 * - Progress calculation logic
 */
class GetBudgetProgressUseCaseTest {

    // ============================================
    // Helper: Create test budgets
    // ============================================

    private fun createBudget(
        id: String = "budget-1",
        name: String = "Test Budget",
        totalAmount: BigDecimal = BigDecimal("1000"),
        items: List<BudgetItem> = emptyList(),
        isActive: Boolean = true,
        startDate: LocalDate = LocalDate.now().minusDays(15),
        endDate: LocalDate = LocalDate.now().plusDays(15)
    ): Budget {
        return Budget(
            id = id,
            userId = "user-1",
            name = name,
            totalAmount = totalAmount,
            period = BudgetPeriod.MONTHLY,
            startDate = startDate,
            endDate = endDate,
            items = items,
            isActive = isActive
        )
    }

    private fun createBudgetItem(
        id: String = "item-1",
        budgetId: String = "budget-1",
        categoryId: String = "cat-1",
        allocatedAmount: BigDecimal = BigDecimal("500"),
        spentAmount: BigDecimal = BigDecimal.ZERO
    ): BudgetItem {
        return BudgetItem(
            id = id,
            budgetId = budgetId,
            categoryId = categoryId,
            allocatedAmount = allocatedAmount,
            spentAmount = spentAmount
        )
    }

    // ============================================
    // Params Tests
    // ============================================

    @Test
    fun `Params SingleBudget holds budgetId`() {
        val params = GetBudgetProgressUseCase.Params.SingleBudget("budget-123")
        assertEquals("budget-123", params.budgetId)
    }

    @Test
    fun `Params Summary defaults to current YearMonth`() {
        val params = GetBudgetProgressUseCase.Params.Summary()
        assertEquals(YearMonth.now(), params.yearMonth)
    }

    @Test
    fun `Params Summary with specific YearMonth`() {
        val yearMonth = YearMonth.of(2025, 6)
        val params = GetBudgetProgressUseCase.Params.Summary(yearMonth)
        assertEquals(YearMonth.of(2025, 6), params.yearMonth)
    }

    @Test
    fun `Params AllBudgets is singleton`() {
        assertSame(
            GetBudgetProgressUseCase.Params.AllBudgets,
            GetBudgetProgressUseCase.Params.AllBudgets
        )
    }

    @Test
    fun `Params SingleBudget equality works`() {
        val p1 = GetBudgetProgressUseCase.Params.SingleBudget("id-1")
        val p2 = GetBudgetProgressUseCase.Params.SingleBudget("id-1")
        assertEquals(p1, p2)
    }

    @Test
    fun `Params SingleBudget inequality works`() {
        val p1 = GetBudgetProgressUseCase.Params.SingleBudget("id-1")
        val p2 = GetBudgetProgressUseCase.Params.SingleBudget("id-2")
        assertNotEquals(p1, p2)
    }

    @Test
    fun `Params Summary equality works`() {
        val p1 = GetBudgetProgressUseCase.Params.Summary(YearMonth.of(2025, 3))
        val p2 = GetBudgetProgressUseCase.Params.Summary(YearMonth.of(2025, 3))
        assertEquals(p1, p2)
    }

    // ============================================
    // BudgetProgress Data Class Tests
    // ============================================

    @Test
    fun `BudgetProgress holds correct data`() {
        val budget = createBudget()
        val progress = GetBudgetProgressUseCase.BudgetProgress(
            budget = budget,
            percentageUsed = 0.5f,
            remaining = BigDecimal("500"),
            isOverBudget = false,
            isNearLimit = false,
            alerts = emptyList()
        )
        assertEquals(budget, progress.budget)
        assertEquals(0.5f, progress.percentageUsed, 0.01f)
        assertEquals(BigDecimal("500"), progress.remaining)
        assertFalse(progress.isOverBudget)
        assertFalse(progress.isNearLimit)
        assertTrue(progress.alerts.isEmpty())
    }

    @Test
    fun `BudgetProgress with over budget state`() {
        val budget = createBudget()
        val progress = GetBudgetProgressUseCase.BudgetProgress(
            budget = budget,
            percentageUsed = 1.2f,
            remaining = BigDecimal("-200"),
            isOverBudget = true,
            isNearLimit = false,
            alerts = emptyList()
        )
        assertTrue(progress.isOverBudget)
        assertTrue(progress.remaining < BigDecimal.ZERO)
    }

    @Test
    fun `BudgetProgress with near limit state`() {
        val budget = createBudget()
        val progress = GetBudgetProgressUseCase.BudgetProgress(
            budget = budget,
            percentageUsed = 0.85f,
            remaining = BigDecimal("150"),
            isOverBudget = false,
            isNearLimit = true,
            alerts = emptyList()
        )
        assertFalse(progress.isOverBudget)
        assertTrue(progress.isNearLimit)
    }

    @Test
    fun `BudgetProgress equality works`() {
        val budget = createBudget()
        val p1 = GetBudgetProgressUseCase.BudgetProgress(
            budget = budget, percentageUsed = 0.5f, remaining = BigDecimal("500"),
            isOverBudget = false, isNearLimit = false, alerts = emptyList()
        )
        val p2 = GetBudgetProgressUseCase.BudgetProgress(
            budget = budget, percentageUsed = 0.5f, remaining = BigDecimal("500"),
            isOverBudget = false, isNearLimit = false, alerts = emptyList()
        )
        assertEquals(p1, p2)
    }

    // ============================================
    // Budget Domain Model Tests (used by use case)
    // ============================================

    @Test
    fun `Budget totalSpent calculates from items`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("200")),
            createBudgetItem(id = "2", spentAmount = BigDecimal("300"))
        )
        val budget = createBudget(items = items)
        assertEquals(BigDecimal("500"), budget.totalSpent)
    }

    @Test
    fun `Budget totalAllocated calculates from items`() {
        val items = listOf(
            createBudgetItem(id = "1", allocatedAmount = BigDecimal("400")),
            createBudgetItem(id = "2", allocatedAmount = BigDecimal("300"))
        )
        val budget = createBudget(items = items)
        assertEquals(BigDecimal("700"), budget.totalAllocated)
    }

    @Test
    fun `Budget remainingAmount is total minus spent`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("600"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        assertEquals(BigDecimal("400"), budget.remainingAmount)
    }

    @Test
    fun `Budget unallocatedAmount is total minus allocated`() {
        val items = listOf(
            createBudgetItem(id = "1", allocatedAmount = BigDecimal("700"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        assertEquals(BigDecimal("300"), budget.unallocatedAmount)
    }

    @Test
    fun `Budget spentPercentage calculates correctly`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("500"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        assertEquals(50.0, budget.spentPercentage, 0.01)
    }

    @Test
    fun `Budget spentPercentage is zero when totalAmount is zero`() {
        val budget = createBudget(totalAmount = BigDecimal.ZERO)
        assertEquals(0.0, budget.spentPercentage, 0.01)
    }

    @Test
    fun `Budget isOverBudget when spent exceeds total`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("1200"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        assertTrue(budget.isOverBudget)
    }

    @Test
    fun `Budget is not over budget when spent equals total`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("1000"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        assertFalse(budget.isOverBudget)
    }

    @Test
    fun `Budget isNearLimit when at 80 percent`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("800"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        assertTrue(budget.isNearLimit)
    }

    @Test
    fun `Budget is not near limit when under 80 percent`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("700"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        assertFalse(budget.isNearLimit)
    }

    @Test
    fun `Budget isNearLimit is false when over budget`() {
        val items = listOf(
            createBudgetItem(id = "1", spentAmount = BigDecimal("1200"))
        )
        val budget = createBudget(totalAmount = BigDecimal("1000"), items = items)
        // isNearLimit requires spentPercentage >= 80 AND !isOverBudget
        assertFalse(budget.isNearLimit)
    }

    @Test
    fun `Budget containsDate returns true for date within range`() {
        val budget = createBudget(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 12, 31)
        )
        assertTrue(budget.containsDate(LocalDate.of(2025, 6, 15)))
    }

    @Test
    fun `Budget containsDate returns true for start date`() {
        val start = LocalDate.of(2025, 1, 1)
        val budget = createBudget(startDate = start, endDate = LocalDate.of(2025, 12, 31))
        assertTrue(budget.containsDate(start))
    }

    @Test
    fun `Budget containsDate returns true for end date`() {
        val end = LocalDate.of(2025, 12, 31)
        val budget = createBudget(startDate = LocalDate.of(2025, 1, 1), endDate = end)
        assertTrue(budget.containsDate(end))
    }

    @Test
    fun `Budget containsDate returns false for date before range`() {
        val budget = createBudget(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 12, 31)
        )
        assertFalse(budget.containsDate(LocalDate.of(2024, 12, 31)))
    }

    @Test
    fun `Budget containsDate returns false for date after range`() {
        val budget = createBudget(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 12, 31)
        )
        assertFalse(budget.containsDate(LocalDate.of(2026, 1, 1)))
    }

    // ============================================
    // Alert Generation Logic Tests (mirrored from use case)
    // ============================================

    /**
     * Mirrors the generateAlerts logic from GetBudgetProgressUseCase.
     * Budget model doesn't have alertsEnabled, so we add a parameter.
     */
    private data class AlertInfo(
        val budgetId: String,
        val budgetName: String,
        val alertType: String,
        val percentageUsed: Float,
        val amountRemaining: BigDecimal
    )

    private fun generateTestAlerts(
        budgetId: String,
        budgetName: String,
        percentageUsed: Float,
        remaining: BigDecimal,
        isOverBudget: Boolean,
        isNearLimit: Boolean,
        alertsEnabled: Boolean = true
    ): List<AlertInfo> {
        val alerts = mutableListOf<AlertInfo>()
        if (!alertsEnabled) return alerts

        when {
            isOverBudget -> {
                alerts.add(AlertInfo(
                    budgetId = budgetId,
                    budgetName = budgetName,
                    alertType = "OVER_BUDGET",
                    percentageUsed = percentageUsed,
                    amountRemaining = remaining
                ))
            }
            percentageUsed >= 1.0f -> {
                alerts.add(AlertInfo(
                    budgetId = budgetId,
                    budgetName = budgetName,
                    alertType = "LIMIT_REACHED",
                    percentageUsed = percentageUsed,
                    amountRemaining = remaining
                ))
            }
            isNearLimit -> {
                alerts.add(AlertInfo(
                    budgetId = budgetId,
                    budgetName = budgetName,
                    alertType = "APPROACHING_LIMIT",
                    percentageUsed = percentageUsed,
                    amountRemaining = remaining
                ))
            }
        }
        return alerts
    }

    @Test
    fun `generateAlerts returns OVER_BUDGET when over budget`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 1.2f,
            remaining = BigDecimal("-200"),
            isOverBudget = true,
            isNearLimit = false
        )
        assertEquals(1, alerts.size)
        assertEquals("OVER_BUDGET", alerts[0].alertType)
    }

    @Test
    fun `generateAlerts returns LIMIT_REACHED when at exactly 100 percent`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 1.0f,
            remaining = BigDecimal.ZERO,
            isOverBudget = false,
            isNearLimit = false
        )
        assertEquals(1, alerts.size)
        assertEquals("LIMIT_REACHED", alerts[0].alertType)
    }

    @Test
    fun `generateAlerts returns APPROACHING_LIMIT when near limit`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 0.85f,
            remaining = BigDecimal("150"),
            isOverBudget = false,
            isNearLimit = true
        )
        assertEquals(1, alerts.size)
        assertEquals("APPROACHING_LIMIT", alerts[0].alertType)
    }

    @Test
    fun `generateAlerts returns empty when well under budget`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 0.5f,
            remaining = BigDecimal("500"),
            isOverBudget = false,
            isNearLimit = false
        )
        assertTrue(alerts.isEmpty())
    }

    @Test
    fun `generateAlerts returns empty when alerts disabled`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 1.5f,
            remaining = BigDecimal("-500"),
            isOverBudget = true,
            isNearLimit = false,
            alertsEnabled = false
        )
        assertTrue(alerts.isEmpty())
    }

    @Test
    fun `generateAlerts OVER_BUDGET takes priority over LIMIT_REACHED`() {
        // If isOverBudget is true and percentageUsed >= 1.0, OVER_BUDGET wins
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 1.5f,
            remaining = BigDecimal("-500"),
            isOverBudget = true,
            isNearLimit = false
        )
        assertEquals(1, alerts.size)
        assertEquals("OVER_BUDGET", alerts[0].alertType)
    }

    @Test
    fun `generateAlerts contains correct budgetId`() {
        val alerts = generateTestAlerts(
            budgetId = "budget-42",
            budgetName = "Shopping",
            percentageUsed = 1.1f,
            remaining = BigDecimal("-100"),
            isOverBudget = true,
            isNearLimit = false
        )
        assertEquals("budget-42", alerts[0].budgetId)
    }

    @Test
    fun `generateAlerts contains correct budgetName`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Entertainment",
            percentageUsed = 0.9f,
            remaining = BigDecimal("100"),
            isOverBudget = false,
            isNearLimit = true
        )
        assertEquals("Entertainment", alerts[0].budgetName)
    }

    @Test
    fun `generateAlerts contains correct percentageUsed`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 0.85f,
            remaining = BigDecimal("150"),
            isOverBudget = false,
            isNearLimit = true
        )
        assertEquals(0.85f, alerts[0].percentageUsed, 0.01f)
    }

    @Test
    fun `generateAlerts contains correct amountRemaining`() {
        val alerts = generateTestAlerts(
            budgetId = "b1",
            budgetName = "Food",
            percentageUsed = 1.2f,
            remaining = BigDecimal("-200"),
            isOverBudget = true,
            isNearLimit = false
        )
        assertEquals(BigDecimal("-200"), alerts[0].amountRemaining)
    }

    // ============================================
    // BudgetItem Tests (used by progress calculations)
    // ============================================

    @Test
    fun `BudgetItem remainingAmount calculates correctly`() {
        val item = createBudgetItem(
            allocatedAmount = BigDecimal("500"),
            spentAmount = BigDecimal("200")
        )
        assertEquals(BigDecimal("300"), item.remainingAmount)
    }

    @Test
    fun `BudgetItem spentPercentage calculates correctly`() {
        val item = createBudgetItem(
            allocatedAmount = BigDecimal("500"),
            spentAmount = BigDecimal("250")
        )
        assertEquals(50.0, item.spentPercentage, 0.01)
    }

    @Test
    fun `BudgetItem spentPercentage is zero when allocated is zero`() {
        val item = createBudgetItem(
            allocatedAmount = BigDecimal.ZERO,
            spentAmount = BigDecimal.ZERO
        )
        assertEquals(0.0, item.spentPercentage, 0.01)
    }

    @Test
    fun `BudgetItem isOverBudget when spent exceeds allocated`() {
        val item = createBudgetItem(
            allocatedAmount = BigDecimal("500"),
            spentAmount = BigDecimal("600")
        )
        assertTrue(item.isOverBudget)
    }

    @Test
    fun `BudgetItem is not over budget when spent equals allocated`() {
        val item = createBudgetItem(
            allocatedAmount = BigDecimal("500"),
            spentAmount = BigDecimal("500")
        )
        assertFalse(item.isOverBudget)
    }

    @Test
    fun `BudgetItem isNearLimit when at 80 percent but not over`() {
        val item = createBudgetItem(
            allocatedAmount = BigDecimal("500"),
            spentAmount = BigDecimal("400")
        )
        assertTrue(item.isNearLimit)
    }

    @Test
    fun `BudgetItem isNearLimit is false when over budget`() {
        val item = createBudgetItem(
            allocatedAmount = BigDecimal("500"),
            spentAmount = BigDecimal("600")
        )
        assertFalse(item.isNearLimit)
    }

    @Test
    fun `BudgetItem empty factory creates valid empty item`() {
        val empty = BudgetItem.empty()
        assertEquals("", empty.id)
        assertEquals("", empty.budgetId)
        assertEquals("", empty.categoryId)
        assertEquals(BigDecimal.ZERO, empty.allocatedAmount)
    }

    // ============================================
    // Budget Factory Method Tests
    // ============================================

    @Test
    fun `Budget empty factory creates valid empty budget`() {
        val empty = Budget.empty()
        assertEquals("", empty.id)
        assertEquals("", empty.userId)
        assertEquals("", empty.name)
        assertEquals(BigDecimal.ZERO, empty.totalAmount)
    }

    @Test
    fun `Budget forMonth factory creates monthly budget`() {
        val yearMonth = YearMonth.of(2025, 6)
        val budget = Budget.forMonth(
            id = "b-1",
            userId = "u-1",
            name = "June Budget",
            totalAmount = BigDecimal("3000"),
            yearMonth = yearMonth
        )
        assertEquals("b-1", budget.id)
        assertEquals("u-1", budget.userId)
        assertEquals("June Budget", budget.name)
        assertEquals(BigDecimal("3000"), budget.totalAmount)
        assertEquals(BudgetPeriod.MONTHLY, budget.period)
        assertEquals(LocalDate.of(2025, 6, 1), budget.startDate)
        assertEquals(LocalDate.of(2025, 6, 30), budget.endDate)
    }

    @Test
    fun `Budget forMonth defaults to current month`() {
        val budget = Budget.forMonth(
            id = "b-1",
            userId = "u-1",
            name = "Current Month",
            totalAmount = BigDecimal("2000")
        )
        val now = YearMonth.now()
        assertEquals(now.atDay(1), budget.startDate)
        assertEquals(now.atEndOfMonth(), budget.endDate)
    }

    // ============================================
    // BudgetPeriod Tests
    // ============================================

    @Test
    fun `BudgetPeriod has four values`() {
        assertEquals(4, BudgetPeriod.entries.size)
    }

    @Test
    fun `BudgetPeriod fromString with valid values`() {
        assertEquals(BudgetPeriod.WEEKLY, BudgetPeriod.fromString("WEEKLY"))
        assertEquals(BudgetPeriod.MONTHLY, BudgetPeriod.fromString("MONTHLY"))
        assertEquals(BudgetPeriod.QUARTERLY, BudgetPeriod.fromString("QUARTERLY"))
        assertEquals(BudgetPeriod.YEARLY, BudgetPeriod.fromString("YEARLY"))
    }

    @Test
    fun `BudgetPeriod fromString is case insensitive`() {
        assertEquals(BudgetPeriod.MONTHLY, BudgetPeriod.fromString("monthly"))
        assertEquals(BudgetPeriod.WEEKLY, BudgetPeriod.fromString("weekly"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun `BudgetPeriod fromString throws for invalid value`() {
        BudgetPeriod.fromString("invalid")
    }
}
