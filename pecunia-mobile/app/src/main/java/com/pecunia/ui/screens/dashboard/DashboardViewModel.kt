package com.pecunia.ui.screens.dashboard

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pecunia.data.local.dao.BudgetDao
import com.pecunia.data.local.dao.TransactionDao
import com.pecunia.data.local.preferences.UserPreferences
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.time.LocalDate
import java.time.ZoneId
import javax.inject.Inject

/**
 * ViewModel for the Dashboard screen managing UI state and business logic.
 * Uses Hilt for dependency injection and follows MVVM architecture.
 */
@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val transactionDao: TransactionDao,
    private val budgetDao: BudgetDao,
    private val userPreferences: UserPreferences
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    private val _events = MutableSharedFlow<DashboardEvent>()
    val events: SharedFlow<DashboardEvent> = _events.asSharedFlow()

    init {
        loadDashboardData()
        observeUserPreferences()
        loadAiInsights()
        loadRecommendations()
    }

    /**
     * Load all dashboard data including transactions, budgets, and insights.
     */
    fun loadDashboardData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            try {
                // Load data in parallel
                launch { loadRecentTransactions() }
                launch { loadBudgets() }
                launch { loadMonthlyStats() }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = e.message ?: "An error occurred while loading data"
                    )
                }
            }
        }
    }

    /**
     * Refresh dashboard data with pull-to-refresh.
     */
    fun refreshData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }

            try {
                // Simulate network delay for better UX
                delay(500)

                // Reload all data
                loadRecentTransactions()
                loadBudgets()
                loadMonthlyStats()
                loadAiInsights()
                loadRecommendations()

                _events.emit(DashboardEvent.SyncCompleted)
            } catch (e: Exception) {
                _events.emit(DashboardEvent.ShowError(e.message ?: "Refresh failed"))
            } finally {
                _uiState.update { it.copy(isRefreshing = false) }
            }
        }
    }

    /**
     * Process user actions from the UI.
     */
    fun onAction(action: DashboardAction) {
        when (action) {
            is DashboardAction.Refresh -> refreshData()
            is DashboardAction.TransactionClicked -> onTransactionClicked(action.transactionId)
            is DashboardAction.BudgetClicked -> onBudgetClicked(action.budgetId)
            is DashboardAction.InsightClicked -> onInsightClicked(action.insightId)
            is DashboardAction.RecommendationClicked -> onRecommendationClicked(action.recommendationId)
            is DashboardAction.DismissRecommendation -> dismissRecommendation(action.recommendationId)
            is DashboardAction.ClearError -> clearError()
            is DashboardAction.MarkNotificationsRead -> markNotificationsAsRead()
            is DashboardAction.ToggleAiInsights -> toggleAiInsights()
            is DashboardAction.LoadMore -> { /* Implement pagination if needed */ }
        }
    }

    private fun observeUserPreferences() {
        viewModelScope.launch {
            userPreferences.userNameFlow.collect { name ->
                _uiState.update { it.copy(userName = name ?: "User") }
            }
        }
    }

    private suspend fun loadRecentTransactions() {
        try {
            val userId = userPreferences.getCurrentUserId() ?: return

            transactionDao.getRecentTransactions(userId, 10)
                .catch { e ->
                    _uiState.update { it.copy(error = e.message) }
                }
                .collect { transactions ->
                    val transactionModels = transactions.map { entity ->
                        TransactionUiModel(
                            id = entity.id,
                            description = entity.description,
                            amount = BigDecimal(entity.amount.toString()),
                            type = TransactionType.fromString(entity.type),
                            categoryName = entity.categoryId ?: "Uncategorized",
                            categoryIcon = getCategoryIcon(entity.categoryId),
                            date = LocalDate.ofEpochDay(entity.date / (24 * 60 * 60 * 1000)),
                            isPending = entity.syncStatus != "SYNCED"
                        )
                    }

                    _uiState.update {
                        it.copy(
                            recentTransactions = transactionModels,
                            isLoading = false
                        )
                    }
                }
        } catch (e: Exception) {
            _uiState.update {
                it.copy(
                    isLoading = false,
                    error = e.message
                )
            }
        }
    }

    private suspend fun loadBudgets() {
        try {
            val userId = userPreferences.getCurrentUserId() ?: return
            val currentDate = System.currentTimeMillis()

            budgetDao.getActiveBudgets(userId, currentDate)
                .catch { e ->
                    _uiState.update { it.copy(error = e.message) }
                }
                .collect { budgets ->
                    val budgetModels = budgets.map { entity ->
                        val spent = entity.spentAmount ?: 0.0
                        val total = entity.totalAmount ?: 0.0
                        val remaining = (total - spent).coerceAtLeast(0.0)
                        val percentageUsed = if (total > 0) (spent / total).toFloat() else 0f

                        BudgetUiModel(
                            id = entity.id,
                            name = entity.name,
                            totalAmount = BigDecimal(total),
                            spentAmount = BigDecimal(spent),
                            remaining = BigDecimal(remaining),
                            percentageUsed = percentageUsed,
                            isOverBudget = spent > total,
                            isNearLimit = percentageUsed >= 0.8f && percentageUsed < 1f,
                            daysRemaining = calculateDaysRemaining(entity.endDate)
                        )
                    }

                    val needsAttention = budgetModels.count { it.isOverBudget || it.isNearLimit }

                    _uiState.update {
                        it.copy(
                            budgets = budgetModels,
                            budgetsNeedingAttention = needsAttention
                        )
                    }
                }
        } catch (e: Exception) {
            _uiState.update { it.copy(error = e.message) }
        }
    }

    private fun calculateDaysRemaining(endDate: Long?): Int {
        if (endDate == null) return 0
        // Convert millis to days since epoch for LocalDate; 86400000 = ms per day.
        val end = LocalDate.ofEpochDay(endDate / (24 * 60 * 60 * 1000))
        val today = LocalDate.now()
        return java.time.temporal.ChronoUnit.DAYS.between(today, end).toInt().coerceAtLeast(0)
    }

    private suspend fun loadMonthlyStats() {
        try {
            val userId = userPreferences.getCurrentUserId() ?: return

            val now = LocalDate.now()
            val startOfMonth = now.withDayOfMonth(1)
            val endOfMonth = now.withDayOfMonth(now.lengthOfMonth())

            val startMillis = startOfMonth.atStartOfDay(ZoneId.systemDefault()).toInstant().toEpochMilli()
            val endMillis = endOfMonth.atStartOfDay(ZoneId.systemDefault()).toInstant().toEpochMilli()

            val income = transactionDao.getSumByTypeAndDateRange(userId, "INCOME", startMillis, endMillis)
            val expenses = transactionDao.getSumByTypeAndDateRange(userId, "EXPENSE", startMillis, endMillis)
            val balance = income - expenses

            _uiState.update {
                it.copy(
                    totalBalance = BigDecimal(balance),
                    monthlyIncome = BigDecimal(income),
                    monthlyExpenses = BigDecimal(expenses)
                )
            }
        } catch (e: Exception) {
            _uiState.update { it.copy(error = e.message) }
        }
    }

    /**
     * Load AI-powered insights for the user.
     */
    private fun loadAiInsights() {
        viewModelScope.launch {
            // In a real app, this would call an AI service
            // For now, we'll generate sample insights based on the user's data
            val insights = generateSampleInsights()
            _uiState.update { it.copy(aiInsights = insights) }
        }
    }

    private fun generateSampleInsights(): List<AiInsightUiModel> {
        return listOf(
            AiInsightUiModel(
                id = "insight_1",
                title = "Spending Pattern Detected",
                message = "Your food expenses increased by 15% compared to last month. Consider meal planning to reduce costs.",
                type = InsightType.SPENDING_PATTERN,
                icon = Icons.Outlined.Restaurant,
                actionLabel = "View Details",
                isRead = false
            ),
            AiInsightUiModel(
                id = "insight_2",
                title = "Savings Goal Progress",
                message = "Great job! You're on track to reach your emergency fund goal by March.",
                type = InsightType.GOAL_PROGRESS,
                icon = Icons.Outlined.TrendingUp,
                actionLabel = "View Goal",
                isRead = true
            ),
            AiInsightUiModel(
                id = "insight_3",
                title = "Subscription Review",
                message = "You have 3 subscriptions totaling \$45/month. Review them to find potential savings.",
                type = InsightType.PERSONALIZED_TIP,
                icon = Icons.Outlined.Subscriptions,
                actionLabel = "Review Subscriptions",
                isRead = false
            )
        )
    }

    /**
     * Load personalized recommendations.
     */
    private fun loadRecommendations() {
        viewModelScope.launch {
            val recommendations = generateSampleRecommendations()
            _uiState.update { it.copy(recommendations = recommendations) }
        }
    }

    private fun generateSampleRecommendations(): List<RecommendationUiModel> {
        return listOf(
            RecommendationUiModel(
                id = "rec_1",
                title = "Reduce Dining Out",
                description = "Based on your spending patterns, cooking at home 2 more times per week could save you money.",
                type = RecommendationType.SAVINGS_OPPORTUNITY,
                actionLabel = "See How",
                potentialSavings = BigDecimal("80"),
                priority = RecommendationPriority.MEDIUM,
                isNew = true
            ),
            RecommendationUiModel(
                id = "rec_2",
                title = "Set Up Emergency Fund",
                description = "You don't have an emergency fund yet. Start with \$500 as a safety net.",
                type = RecommendationType.BUDGET_SUGGESTION,
                actionLabel = "Create Budget",
                priority = RecommendationPriority.HIGH,
                isNew = false
            ),
            RecommendationUiModel(
                id = "rec_3",
                title = "Bill Due Reminder",
                description = "Your electricity bill is due in 3 days. Schedule a payment to avoid late fees.",
                type = RecommendationType.BILL_REMINDER,
                actionLabel = "Pay Now",
                priority = RecommendationPriority.URGENT,
                isNew = true
            )
        )
    }

    /**
     * Handle transaction item click.
     */
    fun onTransactionClicked(transactionId: String) {
        viewModelScope.launch {
            _events.emit(DashboardEvent.NavigateToTransactionDetail(transactionId))
        }
    }

    /**
     * Handle budget item click.
     */
    fun onBudgetClicked(budgetId: String) {
        viewModelScope.launch {
            _events.emit(DashboardEvent.NavigateToBudgetDetail(budgetId))
        }
    }

    /**
     * Handle insight item click.
     */
    fun onInsightClicked(insightId: String) {
        viewModelScope.launch {
            // Mark insight as read
            _uiState.update { currentState ->
                currentState.copy(
                    aiInsights = currentState.aiInsights.map { insight ->
                        if (insight.id == insightId) insight.copy(isRead = true) else insight
                    }
                )
            }
            _events.emit(DashboardEvent.NavigateToInsightDetail(insightId))
        }
    }

    /**
     * Handle recommendation item click.
     */
    private fun onRecommendationClicked(recommendationId: String) {
        viewModelScope.launch {
            // Mark recommendation as not new
            _uiState.update { currentState ->
                currentState.copy(
                    recommendations = currentState.recommendations.map { rec ->
                        if (rec.id == recommendationId) rec.copy(isNew = false) else rec
                    }
                )
            }
        }
    }

    /**
     * Dismiss a recommendation.
     */
    fun dismissRecommendation(recommendationId: String) {
        _uiState.update { currentState ->
            currentState.copy(
                recommendations = currentState.recommendations.map { rec ->
                    if (rec.id == recommendationId) rec.copy(isDismissed = true) else rec
                }
            )
        }
    }

    /**
     * Toggle AI insights visibility.
     */
    private fun toggleAiInsights() {
        _uiState.update { it.copy(showAiInsights = !it.showAiInsights) }
    }

    /**
     * Clear error state.
     */
    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }

    /**
     * Mark notifications as read.
     */
    fun markNotificationsAsRead() {
        viewModelScope.launch {
            _uiState.update { it.copy(notificationCount = 0) }
            _events.emit(DashboardEvent.ShowSnackbar("Notifications marked as read"))
        }
    }

    /**
     * Get the appropriate icon for a category.
     */
    private fun getCategoryIcon(categoryId: String?): ImageVector {
        return when (categoryId?.lowercase()) {
            "food", "dining", "restaurant" -> Icons.Default.Restaurant
            "groceries", "grocery" -> Icons.Default.ShoppingCart
            "transportation", "transport", "car" -> Icons.Default.DirectionsCar
            "utilities", "bills" -> Icons.Default.Power
            "entertainment" -> Icons.Default.Movie
            "shopping" -> Icons.Default.ShoppingBag
            "healthcare", "health", "medical" -> Icons.Default.LocalHospital
            "education" -> Icons.Default.School
            "travel" -> Icons.Default.Flight
            "housing", "home", "rent" -> Icons.Default.Home
            "salary", "income", "work" -> Icons.Default.Work
            "investment", "investments" -> Icons.Default.TrendingUp
            "gift", "gifts" -> Icons.Default.CardGiftcard
            "subscription", "subscriptions" -> Icons.Default.Subscriptions
            "insurance" -> Icons.Default.Security
            "personal" -> Icons.Default.Person
            "fitness", "gym" -> Icons.Default.FitnessCenter
            "pets" -> Icons.Default.Pets
            "charity", "donation" -> Icons.Default.VolunteerActivism
            else -> Icons.Default.Receipt
        }
    }
}
