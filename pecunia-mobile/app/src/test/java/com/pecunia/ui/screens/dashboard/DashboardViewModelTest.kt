package com.pecunia.ui.screens.dashboard

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
import java.math.BigDecimal
import java.time.LocalDate

/**
 * Comprehensive unit tests for DashboardUiState, DashboardEvent,
 * DashboardAction, and related UI model classes.
 * Since DashboardViewModel requires Android-specific DAOs, these tests
 * focus on the UI state models, computed properties, and event types.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    // ============================================
    // DashboardUiState Tests
    // ============================================

    @Test
    fun `default DashboardUiState has correct initial values`() {
        val state = DashboardUiState()
        assertTrue(state.isLoading)
        assertFalse(state.isRefreshing)
        assertNull(state.error)
        assertEquals("User", state.userName)
        assertEquals(0, state.notificationCount)
        assertEquals(BigDecimal.ZERO, state.totalBalance)
        assertEquals(BigDecimal.ZERO, state.monthlyIncome)
        assertEquals(BigDecimal.ZERO, state.monthlyExpenses)
        assertTrue(state.recentTransactions.isEmpty())
        assertTrue(state.budgets.isEmpty())
        assertEquals(0, state.budgetsNeedingAttention)
        assertTrue(state.recommendations.isEmpty())
        assertTrue(state.aiInsights.isEmpty())
        assertTrue(state.showAiInsights)
    }

    @Test
    fun `hasData returns false when no transactions or budgets`() {
        val state = DashboardUiState()
        assertFalse(state.hasData)
    }

    @Test
    fun `hasData returns true when transactions exist`() {
        val state = DashboardUiState(
            recentTransactions = listOf(createSampleTransaction())
        )
        assertTrue(state.hasData)
    }

    @Test
    fun `hasData returns true when budgets exist`() {
        val state = DashboardUiState(
            budgets = listOf(createSampleBudget())
        )
        assertTrue(state.hasData)
    }

    @Test
    fun `hasData returns true when both exist`() {
        val state = DashboardUiState(
            recentTransactions = listOf(createSampleTransaction()),
            budgets = listOf(createSampleBudget())
        )
        assertTrue(state.hasData)
    }

    // ============================================
    // savingsRate Tests
    // ============================================

    @Test
    fun `savingsRate returns 0 when income is zero`() {
        val state = DashboardUiState(
            monthlyIncome = BigDecimal.ZERO,
            monthlyExpenses = BigDecimal("500")
        )
        assertEquals(0f, state.savingsRate, 0.01f)
    }

    @Test
    fun `savingsRate calculates correctly`() {
        val state = DashboardUiState(
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal("3500")
        )
        assertEquals(30f, state.savingsRate, 0.01f)
    }

    @Test
    fun `savingsRate is capped at 100`() {
        val state = DashboardUiState(
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal.ZERO
        )
        assertEquals(100f, state.savingsRate, 0.01f)
    }

    @Test
    fun `savingsRate is capped at 0 when expenses exceed income`() {
        val state = DashboardUiState(
            monthlyIncome = BigDecimal("3000"),
            monthlyExpenses = BigDecimal("5000")
        )
        assertEquals(0f, state.savingsRate, 0.01f)
    }

    @Test
    fun `savingsRate with equal income and expenses is 0`() {
        val state = DashboardUiState(
            monthlyIncome = BigDecimal("1000"),
            monthlyExpenses = BigDecimal("1000")
        )
        assertEquals(0f, state.savingsRate, 0.01f)
    }

    // ============================================
    // isOnTrack Tests
    // ============================================

    @Test
    fun `isOnTrack true when no budget alerts and good savings rate`() {
        val state = DashboardUiState(
            budgetsNeedingAttention = 0,
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal("3500") // 30% savings rate
        )
        assertTrue(state.isOnTrack)
    }

    @Test
    fun `isOnTrack false when budgets need attention`() {
        val state = DashboardUiState(
            budgetsNeedingAttention = 2,
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal("3500")
        )
        assertFalse(state.isOnTrack)
    }

    @Test
    fun `isOnTrack false when savings rate is low`() {
        val state = DashboardUiState(
            budgetsNeedingAttention = 0,
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal("4500") // 10% savings rate, below 20%
        )
        assertFalse(state.isOnTrack)
    }

    @Test
    fun `isOnTrack true when savings rate is exactly 20 percent`() {
        val state = DashboardUiState(
            budgetsNeedingAttention = 0,
            monthlyIncome = BigDecimal("5000"),
            monthlyExpenses = BigDecimal("4000") // 20% savings rate
        )
        assertTrue(state.isOnTrack)
    }

    // ============================================
    // hasBudgetAlerts Tests
    // ============================================

    @Test
    fun `hasBudgetAlerts true when budgets need attention`() {
        val state = DashboardUiState(budgetsNeedingAttention = 1)
        assertTrue(state.hasBudgetAlerts)
    }

    @Test
    fun `hasBudgetAlerts false when no budgets need attention`() {
        val state = DashboardUiState(budgetsNeedingAttention = 0)
        assertFalse(state.hasBudgetAlerts)
    }

    // ============================================
    // TransactionUiModel Tests
    // ============================================

    @Test
    fun `TransactionUiModel signedAmount for EXPENSE is negated`() {
        val model = createSampleTransaction(type = TransactionType.EXPENSE, amount = BigDecimal("50"))
        assertEquals(BigDecimal("-50"), model.signedAmount)
    }

    @Test
    fun `TransactionUiModel signedAmount for INCOME is positive`() {
        val model = createSampleTransaction(type = TransactionType.INCOME, amount = BigDecimal("100"))
        assertEquals(BigDecimal("100"), model.signedAmount)
    }

    @Test
    fun `TransactionUiModel signedAmount for TRANSFER is unchanged`() {
        val model = createSampleTransaction(type = TransactionType.TRANSFER, amount = BigDecimal("75"))
        assertEquals(BigDecimal("75"), model.signedAmount)
    }

    @Test
    fun `TransactionUiModel isRecent true for today`() {
        val model = createSampleTransaction(date = LocalDate.now())
        assertTrue(model.isRecent)
    }

    @Test
    fun `TransactionUiModel isRecent true for yesterday`() {
        val model = createSampleTransaction(date = LocalDate.now().minusDays(1))
        assertTrue(model.isRecent)
    }

    @Test
    fun `TransactionUiModel isRecent false for 2 days ago`() {
        val model = createSampleTransaction(date = LocalDate.now().minusDays(2))
        assertFalse(model.isRecent)
    }

    @Test
    fun `TransactionUiModel isRecent false for future date`() {
        val model = createSampleTransaction(date = LocalDate.now().plusDays(1))
        assertFalse(model.isRecent)
    }

    // ============================================
    // BudgetUiModel Tests
    // ============================================

    @Test
    fun `BudgetUiModel dailyBudgetRemaining calculates correctly`() {
        val model = createSampleBudget(
            remaining = BigDecimal("500"),
            daysRemaining = 10
        )
        assertEquals(BigDecimal("50.00"), model.dailyBudgetRemaining)
    }

    @Test
    fun `BudgetUiModel dailyBudgetRemaining returns ZERO when no days remaining`() {
        val model = createSampleBudget(
            remaining = BigDecimal("500"),
            daysRemaining = 0
        )
        assertEquals(BigDecimal.ZERO, model.dailyBudgetRemaining)
    }

    @Test
    fun `BudgetUiModel status OVER_BUDGET when isOverBudget`() {
        val model = createSampleBudget(isOverBudget = true, isNearLimit = false)
        assertEquals(BudgetStatus.OVER_BUDGET, model.status)
    }

    @Test
    fun `BudgetUiModel status WARNING when isNearLimit`() {
        val model = createSampleBudget(isOverBudget = false, isNearLimit = true)
        assertEquals(BudgetStatus.WARNING, model.status)
    }

    @Test
    fun `BudgetUiModel status ON_TRACK otherwise`() {
        val model = createSampleBudget(isOverBudget = false, isNearLimit = false)
        assertEquals(BudgetStatus.ON_TRACK, model.status)
    }

    @Test
    fun `BudgetUiModel status prioritizes OVER_BUDGET over WARNING`() {
        val model = createSampleBudget(isOverBudget = true, isNearLimit = true)
        assertEquals(BudgetStatus.OVER_BUDGET, model.status)
    }

    // ============================================
    // TransactionType Tests
    // ============================================

    @Test
    fun `TransactionType fromString with INCOME returns INCOME`() {
        assertEquals(TransactionType.INCOME, TransactionType.fromString("INCOME"))
    }

    @Test
    fun `TransactionType fromString with EXPENSE returns EXPENSE`() {
        assertEquals(TransactionType.EXPENSE, TransactionType.fromString("EXPENSE"))
    }

    @Test
    fun `TransactionType fromString with TRANSFER returns TRANSFER`() {
        assertEquals(TransactionType.TRANSFER, TransactionType.fromString("TRANSFER"))
    }

    @Test
    fun `TransactionType fromString case insensitive`() {
        assertEquals(TransactionType.INCOME, TransactionType.fromString("income"))
        assertEquals(TransactionType.EXPENSE, TransactionType.fromString("expense"))
        assertEquals(TransactionType.TRANSFER, TransactionType.fromString("transfer"))
    }

    @Test
    fun `TransactionType fromString with invalid value defaults to EXPENSE`() {
        assertEquals(TransactionType.EXPENSE, TransactionType.fromString("INVALID"))
    }

    @Test
    fun `TransactionType fromString with empty string defaults to EXPENSE`() {
        assertEquals(TransactionType.EXPENSE, TransactionType.fromString(""))
    }

    // ============================================
    // BudgetStatus Tests
    // ============================================

    @Test
    fun `BudgetStatus enum has all expected values`() {
        val values = BudgetStatus.entries
        assertEquals(3, values.size)
        assertTrue(values.contains(BudgetStatus.ON_TRACK))
        assertTrue(values.contains(BudgetStatus.WARNING))
        assertTrue(values.contains(BudgetStatus.OVER_BUDGET))
    }

    // ============================================
    // RecommendationType Tests
    // ============================================

    @Test
    fun `RecommendationType enum has all expected values`() {
        val values = RecommendationType.entries
        assertEquals(7, values.size)
        assertTrue(values.contains(RecommendationType.SPENDING_ALERT))
        assertTrue(values.contains(RecommendationType.SAVINGS_OPPORTUNITY))
        assertTrue(values.contains(RecommendationType.BUDGET_SUGGESTION))
        assertTrue(values.contains(RecommendationType.INVESTMENT_TIP))
        assertTrue(values.contains(RecommendationType.BILL_REMINDER))
        assertTrue(values.contains(RecommendationType.SUBSCRIPTION_REVIEW))
        assertTrue(values.contains(RecommendationType.CATEGORY_INSIGHT))
    }

    // ============================================
    // RecommendationPriority Tests
    // ============================================

    @Test
    fun `RecommendationPriority has correct order`() {
        assertTrue(RecommendationPriority.LOW.ordinal < RecommendationPriority.MEDIUM.ordinal)
        assertTrue(RecommendationPriority.MEDIUM.ordinal < RecommendationPriority.HIGH.ordinal)
        assertTrue(RecommendationPriority.HIGH.ordinal < RecommendationPriority.URGENT.ordinal)
    }

    // ============================================
    // InsightType Tests
    // ============================================

    @Test
    fun `InsightType enum has all expected values`() {
        val values = InsightType.entries
        assertEquals(7, values.size)
        assertTrue(values.contains(InsightType.SPENDING_PATTERN))
        assertTrue(values.contains(InsightType.ANOMALY_DETECTION))
        assertTrue(values.contains(InsightType.GOAL_PROGRESS))
        assertTrue(values.contains(InsightType.MARKET_UPDATE))
        assertTrue(values.contains(InsightType.PERSONALIZED_TIP))
        assertTrue(values.contains(InsightType.ACHIEVEMENT))
        assertTrue(values.contains(InsightType.WARNING))
    }

    // ============================================
    // DashboardEvent Tests
    // ============================================

    @Test
    fun `NavigateToTransactionDetail carries transactionId`() {
        val event = DashboardEvent.NavigateToTransactionDetail("tx-123")
        assertEquals("tx-123", event.transactionId)
    }

    @Test
    fun `NavigateToBudgetDetail carries budgetId`() {
        val event = DashboardEvent.NavigateToBudgetDetail("budget-123")
        assertEquals("budget-123", event.budgetId)
    }

    @Test
    fun `NavigateToInsightDetail carries insightId`() {
        val event = DashboardEvent.NavigateToInsightDetail("insight-1")
        assertEquals("insight-1", event.insightId)
    }

    @Test
    fun `ShowError carries message`() {
        val event = DashboardEvent.ShowError("Something went wrong")
        assertEquals("Something went wrong", event.message)
    }

    @Test
    fun `ShowSnackbar carries message`() {
        val event = DashboardEvent.ShowSnackbar("Action completed")
        assertEquals("Action completed", event.message)
    }

    @Test
    fun `SyncFailed carries message`() {
        val event = DashboardEvent.SyncFailed("Network error")
        assertEquals("Network error", event.message)
    }

    // ============================================
    // DashboardAction Tests
    // ============================================

    @Test
    fun `TransactionClicked carries transactionId`() {
        val action = DashboardAction.TransactionClicked("tx-1")
        assertEquals("tx-1", action.transactionId)
    }

    @Test
    fun `BudgetClicked carries budgetId`() {
        val action = DashboardAction.BudgetClicked("b-1")
        assertEquals("b-1", action.budgetId)
    }

    @Test
    fun `InsightClicked carries insightId`() {
        val action = DashboardAction.InsightClicked("i-1")
        assertEquals("i-1", action.insightId)
    }

    @Test
    fun `RecommendationClicked carries recommendationId`() {
        val action = DashboardAction.RecommendationClicked("r-1")
        assertEquals("r-1", action.recommendationId)
    }

    @Test
    fun `DismissRecommendation carries recommendationId`() {
        val action = DashboardAction.DismissRecommendation("r-2")
        assertEquals("r-2", action.recommendationId)
    }

    // ============================================
    // RecommendationUiModel Tests
    // ============================================

    @Test
    fun `RecommendationUiModel default values are correct`() {
        val model = RecommendationUiModel(
            id = "1",
            title = "Test",
            description = "Test description",
            type = RecommendationType.SAVINGS_OPPORTUNITY
        )
        assertNull(model.actionLabel)
        assertNull(model.potentialSavings)
        assertEquals(RecommendationPriority.MEDIUM, model.priority)
        assertFalse(model.isNew)
        assertFalse(model.isDismissed)
    }

    // ============================================
    // AiInsightUiModel Tests
    // ============================================

    @Test
    fun `AiInsightUiModel default values are correct`() {
        val model = AiInsightUiModel(
            id = "1",
            title = "Test Insight",
            message = "Test message",
            type = InsightType.SPENDING_PATTERN
        )
        assertNull(model.icon)
        assertNull(model.actionLabel)
        assertNull(model.actionRoute)
        assertTrue(model.timestamp > 0)
        assertFalse(model.isRead)
    }

    // ============================================
    // Helper Methods
    // ============================================

    private fun createSampleTransaction(
        type: TransactionType = TransactionType.EXPENSE,
        amount: BigDecimal = BigDecimal("50"),
        date: LocalDate = LocalDate.now()
    ): TransactionUiModel {
        return TransactionUiModel(
            id = "tx-1",
            description = "Test Transaction",
            amount = amount,
            type = type,
            categoryName = "Food",
            categoryIcon = androidx.compose.material.icons.Icons.Default.Receipt,
            date = date
        )
    }

    private fun createSampleBudget(
        remaining: BigDecimal = BigDecimal("500"),
        daysRemaining: Int = 15,
        isOverBudget: Boolean = false,
        isNearLimit: Boolean = false
    ): BudgetUiModel {
        return BudgetUiModel(
            id = "b-1",
            name = "Test Budget",
            totalAmount = BigDecimal("1000"),
            spentAmount = BigDecimal("500"),
            remaining = remaining,
            percentageUsed = 0.5f,
            isOverBudget = isOverBudget,
            isNearLimit = isNearLimit,
            daysRemaining = daysRemaining
        )
    }
}
