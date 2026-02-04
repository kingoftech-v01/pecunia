package com.pecunia.ui.screens.dashboard

import androidx.compose.ui.graphics.vector.ImageVector
import java.math.BigDecimal
import java.time.LocalDate

/**
 * UI state for the Dashboard screen containing all display data.
 * This class follows the unidirectional data flow pattern for Compose.
 */
data class DashboardUiState(
    // Loading and error states
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,

    // User info
    val userName: String = "User",
    val notificationCount: Int = 0,

    // Balance information
    val totalBalance: BigDecimal = BigDecimal.ZERO,
    val monthlyIncome: BigDecimal = BigDecimal.ZERO,
    val monthlyExpenses: BigDecimal = BigDecimal.ZERO,

    // Transactions
    val recentTransactions: List<TransactionUiModel> = emptyList(),

    // Budgets
    val budgets: List<BudgetUiModel> = emptyList(),
    val budgetsNeedingAttention: Int = 0,

    // AI Insights and Recommendations
    val recommendations: List<RecommendationUiModel> = emptyList(),
    val aiInsights: List<AiInsightUiModel> = emptyList(),
    val showAiInsights: Boolean = true
) {
    /**
     * Returns true if there is any data to display.
     */
    val hasData: Boolean
        get() = recentTransactions.isNotEmpty() || budgets.isNotEmpty()

    /**
     * Returns the savings rate as a percentage.
     */
    val savingsRate: Float
        get() = if (monthlyIncome > BigDecimal.ZERO) {
            ((monthlyIncome - monthlyExpenses).toFloat() / monthlyIncome.toFloat() * 100).coerceIn(0f, 100f)
        } else 0f

    /**
     * Returns true if the user is on track with their budget.
     */
    val isOnTrack: Boolean
        get() = budgetsNeedingAttention == 0 && savingsRate >= 20f

    /**
     * Returns true if there are budgets that need attention.
     */
    val hasBudgetAlerts: Boolean
        get() = budgetsNeedingAttention > 0
}

/**
 * UI model for displaying a transaction in the dashboard.
 */
data class TransactionUiModel(
    val id: String,
    val description: String,
    val amount: BigDecimal,
    val type: TransactionType,
    val categoryName: String,
    val categoryIcon: ImageVector,
    val date: LocalDate,
    val isPending: Boolean = false,
    val merchantLogo: String? = null,
    val notes: String? = null,
    val tags: List<String> = emptyList()
) {
    /**
     * Returns the formatted amount with sign prefix.
     */
    val signedAmount: BigDecimal
        get() = when (type) {
            TransactionType.EXPENSE -> amount.negate()
            TransactionType.INCOME -> amount
            TransactionType.TRANSFER -> amount
        }

    /**
     * Returns true if the transaction is recent (within 24 hours).
     */
    val isRecent: Boolean
        get() = date == LocalDate.now() || date == LocalDate.now().minusDays(1)
}

/**
 * UI model for displaying a budget in the dashboard.
 */
data class BudgetUiModel(
    val id: String,
    val name: String,
    val totalAmount: BigDecimal,
    val spentAmount: BigDecimal,
    val remaining: BigDecimal,
    val percentageUsed: Float,
    val isOverBudget: Boolean,
    val isNearLimit: Boolean,
    val categoryIcon: ImageVector? = null,
    val colorHex: String? = null,
    val daysRemaining: Int = 0
) {
    /**
     * Returns the daily budget remaining.
     */
    val dailyBudgetRemaining: BigDecimal
        get() = if (daysRemaining > 0) {
            remaining.divide(BigDecimal(daysRemaining), 2, java.math.RoundingMode.HALF_UP)
        } else BigDecimal.ZERO

    /**
     * Returns the budget status.
     */
    val status: BudgetStatus
        get() = when {
            isOverBudget -> BudgetStatus.OVER_BUDGET
            isNearLimit -> BudgetStatus.WARNING
            else -> BudgetStatus.ON_TRACK
        }
}

/**
 * Budget status enum for UI display.
 */
enum class BudgetStatus {
    ON_TRACK,
    WARNING,
    OVER_BUDGET
}

/**
 * Transaction type enum for UI purposes.
 */
enum class TransactionType {
    INCOME,
    EXPENSE,
    TRANSFER;

    companion object {
        fun fromString(value: String): TransactionType {
            return entries.find { it.name.equals(value, ignoreCase = true) } ?: EXPENSE
        }
    }
}

/**
 * UI model for AI-powered recommendations.
 */
data class RecommendationUiModel(
    val id: String,
    val title: String,
    val description: String,
    val type: RecommendationType,
    val actionLabel: String? = null,
    val potentialSavings: BigDecimal? = null,
    val priority: RecommendationPriority = RecommendationPriority.MEDIUM,
    val isNew: Boolean = false,
    val isDismissed: Boolean = false
)

/**
 * Types of recommendations the AI can provide.
 */
enum class RecommendationType {
    SPENDING_ALERT,
    SAVINGS_OPPORTUNITY,
    BUDGET_SUGGESTION,
    INVESTMENT_TIP,
    BILL_REMINDER,
    SUBSCRIPTION_REVIEW,
    CATEGORY_INSIGHT
}

/**
 * Priority levels for recommendations.
 */
enum class RecommendationPriority {
    LOW,
    MEDIUM,
    HIGH,
    URGENT
}

/**
 * UI model for AI insights displayed on the dashboard.
 */
data class AiInsightUiModel(
    val id: String,
    val title: String,
    val message: String,
    val type: InsightType,
    val icon: ImageVector? = null,
    val actionLabel: String? = null,
    val actionRoute: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
    val isRead: Boolean = false
)

/**
 * Types of AI insights.
 */
enum class InsightType {
    SPENDING_PATTERN,
    ANOMALY_DETECTION,
    GOAL_PROGRESS,
    MARKET_UPDATE,
    PERSONALIZED_TIP,
    ACHIEVEMENT,
    WARNING
}

/**
 * Events emitted by the Dashboard ViewModel.
 */
sealed class DashboardEvent {
    data class NavigateToTransactionDetail(val transactionId: String) : DashboardEvent()
    data class NavigateToBudgetDetail(val budgetId: String) : DashboardEvent()
    data class NavigateToInsightDetail(val insightId: String) : DashboardEvent()
    data object NavigateToAddTransaction : DashboardEvent()
    data object NavigateToBudgets : DashboardEvent()
    data object NavigateToScanner : DashboardEvent()
    data object NavigateToReports : DashboardEvent()
    data object SyncCompleted : DashboardEvent()
    data class SyncFailed(val message: String) : DashboardEvent()
    data class ShowError(val message: String) : DashboardEvent()
    data class ShowSnackbar(val message: String) : DashboardEvent()
    data object DismissError : DashboardEvent()
}

/**
 * User actions that can be performed on the Dashboard.
 */
sealed class DashboardAction {
    data object Refresh : DashboardAction()
    data object LoadMore : DashboardAction()
    data class TransactionClicked(val transactionId: String) : DashboardAction()
    data class BudgetClicked(val budgetId: String) : DashboardAction()
    data class InsightClicked(val insightId: String) : DashboardAction()
    data class RecommendationClicked(val recommendationId: String) : DashboardAction()
    data class DismissRecommendation(val recommendationId: String) : DashboardAction()
    data object ClearError : DashboardAction()
    data object MarkNotificationsRead : DashboardAction()
    data object ToggleAiInsights : DashboardAction()
}
