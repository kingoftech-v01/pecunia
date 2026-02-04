package com.pecunia.ui.screens.budgets

import androidx.compose.ui.graphics.Color
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pecunia.data.local.dao.BudgetDao
import com.pecunia.data.local.dao.TransactionDao
import com.pecunia.data.local.dao.CategoryDao
import com.pecunia.data.local.entities.BudgetEntity
import com.pecunia.data.local.preferences.UserPreferences
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate
import java.time.YearMonth
import java.time.ZoneId
import java.util.UUID
import javax.inject.Inject

/**
 * ViewModel for the Budgets screens (list and detail).
 * Handles budget loading, filtering, and CRUD operations.
 */
@HiltViewModel
class BudgetsViewModel @Inject constructor(
    private val budgetDao: BudgetDao,
    private val transactionDao: TransactionDao,
    private val categoryDao: CategoryDao,
    private val userPreferences: UserPreferences
) : ViewModel() {

    // List Screen State
    private val _uiState = MutableStateFlow(BudgetsUiState())
    val uiState: StateFlow<BudgetsUiState> = _uiState.asStateFlow()

    private val _events = MutableSharedFlow<BudgetsEvent>()
    val events: SharedFlow<BudgetsEvent> = _events.asSharedFlow()

    // Detail Screen State
    private val _detailState = MutableStateFlow(BudgetDetailState())
    val detailState: StateFlow<BudgetDetailState> = _detailState.asStateFlow()

    private val _detailEvents = MutableSharedFlow<BudgetDetailEvent>()
    val detailEvents: SharedFlow<BudgetDetailEvent> = _detailEvents.asSharedFlow()

    init {
        loadBudgets()
    }

    // ==================== List Screen Functions ====================

    /**
     * Load all budgets for the current user.
     */
    fun loadBudgets() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            try {
                val userId = userPreferences.getCurrentUserId() ?: return@launch

                budgetDao.getBudgets(userId)
                    .catch { e ->
                        _uiState.update { it.copy(isLoading = false, error = e.message) }
                    }
                    .collect { entities ->
                        val budgets = entities.map { entity ->
                            mapEntityToListItem(entity)
                        }

                        // Filter by selected period
                        val filteredBudgets = filterByPeriod(budgets, _uiState.value.selectedPeriod)

                        // Calculate summary
                        val totalBudgeted = filteredBudgets.sumOf { it.totalAmount }
                        val totalSpent = filteredBudgets.sumOf { it.spentAmount }
                        val totalRemaining = filteredBudgets.sumOf { it.remainingAmount }

                        val overallPercentage = if (totalBudgeted > BigDecimal.ZERO) {
                            (totalSpent.toFloat() / totalBudgeted.toFloat()).coerceIn(0f, 1f)
                        } else 0f

                        val onTrackCount = filteredBudgets.count { !it.isNearLimit && !it.isOverBudget }
                        val nearLimitCount = filteredBudgets.count { it.isNearLimit }
                        val overLimitCount = filteredBudgets.count { it.isOverBudget }

                        _uiState.update {
                            it.copy(
                                isLoading = false,
                                budgets = filteredBudgets,
                                totalBudgeted = totalBudgeted,
                                totalSpent = totalSpent,
                                totalRemaining = totalRemaining,
                                overallPercentageUsed = overallPercentage,
                                onTrackCount = onTrackCount,
                                nearLimitCount = nearLimitCount,
                                overLimitCount = overLimitCount
                            )
                        }
                    }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(isLoading = false, error = e.message ?: "Failed to load budgets")
                }
            }
        }
    }

    /**
     * Refresh budgets with pull-to-refresh.
     */
    fun refreshBudgets() {
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }

            try {
                loadBudgets()
            } finally {
                _uiState.update { it.copy(isRefreshing = false) }
            }
        }
    }

    /**
     * Update selected period.
     */
    fun onPeriodChanged(period: YearMonth) {
        _uiState.update { it.copy(selectedPeriod = period) }
        loadBudgets()
    }

    /**
     * Handle budget item click.
     */
    fun onBudgetClicked(budgetId: String) {
        viewModelScope.launch {
            _events.emit(BudgetsEvent.NavigateToDetail(budgetId))
        }
    }

    private fun filterByPeriod(
        budgets: List<BudgetListItemUiModel>,
        period: YearMonth
    ): List<BudgetListItemUiModel> {
        val startOfMonth = period.atDay(1)
        val endOfMonth = period.atEndOfMonth()

        return budgets.filter { budget ->
            // Include budgets that overlap with the selected period
            // This is a simplified filter - real implementation would check actual date ranges
            true
        }
    }

    private suspend fun mapEntityToListItem(entity: BudgetEntity): BudgetListItemUiModel {
        val spent = calculateSpentAmount(entity)
        val total = entity.totalPlanned
        val remaining = (total - spent).coerceAtLeast(BigDecimal.ZERO)
        val percentageUsed = if (total > BigDecimal.ZERO) {
            spent.divide(total, 4, RoundingMode.HALF_UP).toFloat()
        } else 0f

        val categoryName = entity.userId?.let { /* Get category name */ null }

        return BudgetListItemUiModel(
            id = entity.id.toString(),
            name = entity.name,
            totalAmount = total,
            spentAmount = spent,
            remainingAmount = remaining,
            percentageUsed = percentageUsed,
            isOverBudget = spent > total,
            isNearLimit = percentageUsed >= 0.8f && percentageUsed < 1f,
            periodType = entity.periodType.name.lowercase().replaceFirstChar { it.uppercase() },
            categoryName = categoryName,
            color = Color(0xFF6200EE) // Default color
        )
    }

    private suspend fun calculateSpentAmount(budget: BudgetEntity): BigDecimal {
        return try {
            val userId = userPreferences.getCurrentUserId() ?: return BigDecimal.ZERO
            val spent = transactionDao.getSumByTypeAndDateRange(
                userId = userId,
                type = "EXPENSE",
                startDate = budget.startDate,
                endDate = budget.endDate
            )
            BigDecimal(spent)
        } catch (e: Exception) {
            BigDecimal.ZERO
        }
    }

    // ==================== Detail Screen Functions ====================

    /**
     * Load budget detail by ID.
     */
    fun loadBudgetDetail(budgetId: String) {
        viewModelScope.launch {
            _detailState.update { it.copy(isLoading = true, error = null) }

            try {
                budgetDao.getBudgetById(budgetId)
                    .catch { e ->
                        _detailState.update { it.copy(isLoading = false, error = e.message) }
                    }
                    .collect { entity ->
                        if (entity != null) {
                            val budgetDetail = mapEntityToDetail(entity)
                            val transactions = loadBudgetTransactions(entity)

                            _detailState.update {
                                it.copy(
                                    isLoading = false,
                                    budget = budgetDetail,
                                    transactions = transactions
                                )
                            }
                        } else {
                            _detailState.update {
                                it.copy(isLoading = false, error = "Budget not found")
                            }
                        }
                    }
            } catch (e: Exception) {
                _detailState.update {
                    it.copy(isLoading = false, error = e.message ?: "Failed to load budget")
                }
            }
        }
    }

    private suspend fun mapEntityToDetail(entity: BudgetEntity): BudgetDetailUiModel {
        val spent = calculateSpentAmount(entity)
        val total = entity.totalPlanned
        val remaining = total - spent
        val percentageUsed = if (total > BigDecimal.ZERO) {
            spent.divide(total, 4, RoundingMode.HALF_UP).toFloat()
        } else 0f

        val startDate = LocalDate.ofEpochDay(entity.startDate / (24 * 60 * 60 * 1000))
        val endDate = LocalDate.ofEpochDay(entity.endDate / (24 * 60 * 60 * 1000))
        val daysInPeriod = (entity.endDate - entity.startDate) / (24 * 60 * 60 * 1000)
        val dailyBudget = if (daysInPeriod > 0) {
            total.divide(BigDecimal(daysInPeriod), 2, RoundingMode.HALF_UP)
        } else total

        val today = LocalDate.now()
        val daysElapsed = (today.toEpochDay() - startDate.toEpochDay()).coerceAtLeast(1)
        val averageDaily = if (daysElapsed > 0) {
            spent.divide(BigDecimal(daysElapsed), 2, RoundingMode.HALF_UP)
        } else BigDecimal.ZERO

        val daysRemaining = (endDate.toEpochDay() - today.toEpochDay()).toInt().coerceAtLeast(0)

        val dailySpending = calculateDailySpending(entity)

        return BudgetDetailUiModel(
            id = entity.id.toString(),
            name = entity.name,
            totalAmount = total,
            spentAmount = spent,
            remainingAmount = remaining,
            percentageUsed = percentageUsed,
            isOverBudget = spent > total,
            isNearLimit = percentageUsed >= 0.8f && percentageUsed < 1f,
            periodType = entity.periodType.name.lowercase().replaceFirstChar { it.uppercase() },
            startDate = startDate,
            endDate = endDate,
            categoryName = null,
            dailyBudget = dailyBudget,
            averageDailySpending = averageDaily,
            daysRemaining = daysRemaining,
            alertsEnabled = true,
            alertThreshold = 0.8f,
            dailySpending = dailySpending,
            color = Color(0xFF6200EE)
        )
    }

    private suspend fun loadBudgetTransactions(budget: BudgetEntity): List<BudgetTransactionUiModel> {
        return try {
            val userId = userPreferences.getCurrentUserId() ?: return emptyList()

            val transactions = transactionDao.getPendingSyncTransactions(userId)
                .filter { transaction ->
                    transaction.transactionDate in budget.startDate..budget.endDate &&
                    transaction.type == com.pecunia.data.local.entities.TransactionEntity.TransactionType.EXPENSE
                }
                .take(20)
                .map { entity ->
                    BudgetTransactionUiModel(
                        id = entity.id.toString(),
                        description = entity.description,
                        amount = entity.amount,
                        date = LocalDate.ofEpochDay(entity.transactionDate / (24 * 60 * 60 * 1000)),
                        categoryName = entity.categoryId?.toString() ?: "Uncategorized"
                    )
                }

            transactions
        } catch (e: Exception) {
            emptyList()
        }
    }

    private suspend fun calculateDailySpending(budget: BudgetEntity): List<DailySpending> {
        // This would ideally aggregate spending by day
        // For now, return empty list as placeholder
        return emptyList()
    }

    /**
     * Delete a budget.
     */
    fun deleteBudget(budgetId: String) {
        viewModelScope.launch {
            try {
                budgetDao.deleteById(budgetId)
                _detailEvents.emit(BudgetDetailEvent.DeleteSuccess)
                _events.emit(BudgetsEvent.BudgetDeleted(budgetId))
            } catch (e: Exception) {
                _detailEvents.emit(BudgetDetailEvent.ShowError(e.message ?: "Failed to delete budget"))
            }
        }
    }

    /**
     * Archive a budget.
     */
    fun archiveBudget(budgetId: String) {
        viewModelScope.launch {
            try {
                budgetDao.setActiveStatus(budgetId, false, System.currentTimeMillis())
                loadBudgets()
                _events.emit(BudgetsEvent.BudgetArchived(budgetId))
            } catch (e: Exception) {
                _events.emit(BudgetsEvent.ShowError(e.message ?: "Failed to archive budget"))
            }
        }
    }

    /**
     * Duplicate a budget.
     */
    fun duplicateBudget(budgetId: String) {
        viewModelScope.launch {
            try {
                val original = budgetDao.getBudgetByIdSync(budgetId)
                original?.let { entity ->
                    val duplicate = entity.copy(
                        id = UUID.randomUUID(),
                        name = "${entity.name} (Copy)",
                        createdAt = System.currentTimeMillis(),
                        updatedAt = System.currentTimeMillis(),
                        syncStatus = BudgetEntity.SyncStatus.PENDING
                    )
                    budgetDao.insert(duplicate)
                    loadBudgets()
                    _events.emit(BudgetsEvent.BudgetDuplicated(duplicate.id.toString()))
                }
            } catch (e: Exception) {
                _events.emit(BudgetsEvent.ShowError(e.message ?: "Failed to duplicate budget"))
            }
        }
    }
}

/**
 * UI state for the budgets list screen.
 */
data class BudgetsUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val budgets: List<BudgetListItemUiModel> = emptyList(),
    val selectedPeriod: YearMonth = YearMonth.now(),
    val totalBudgeted: BigDecimal = BigDecimal.ZERO,
    val totalSpent: BigDecimal = BigDecimal.ZERO,
    val totalRemaining: BigDecimal = BigDecimal.ZERO,
    val overallPercentageUsed: Float = 0f,
    val onTrackCount: Int = 0,
    val nearLimitCount: Int = 0,
    val overLimitCount: Int = 0
)

/**
 * UI state for the budget detail screen.
 */
data class BudgetDetailState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val budget: BudgetDetailUiModel? = null,
    val transactions: List<BudgetTransactionUiModel> = emptyList()
)

/**
 * Events emitted by the budgets list screen.
 */
sealed class BudgetsEvent {
    data class NavigateToDetail(val budgetId: String) : BudgetsEvent()
    data class BudgetDeleted(val budgetId: String) : BudgetsEvent()
    data class BudgetArchived(val budgetId: String) : BudgetsEvent()
    data class BudgetDuplicated(val budgetId: String) : BudgetsEvent()
    data class ShowError(val message: String) : BudgetsEvent()
}
