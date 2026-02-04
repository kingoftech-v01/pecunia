package com.pecunia.ui.screens.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionSummary
import com.pecunia.domain.usecases.GetBudgetsUseCase
import com.pecunia.domain.usecases.GetTransactionsUseCase
import com.pecunia.domain.usecases.SyncDataUseCase
import com.pecunia.domain.usecases.SyncState
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.time.LocalDate
import java.time.YearMonth

/**
 * ViewModel for the Dashboard screen.
 */
class DashboardViewModel(
    private val getTransactionsUseCase: GetTransactionsUseCase,
    private val getBudgetsUseCase: GetBudgetsUseCase,
    private val syncDataUseCase: SyncDataUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    private val _events = MutableSharedFlow<DashboardEvent>()
    val events: SharedFlow<DashboardEvent> = _events.asSharedFlow()

    init {
        loadDashboardData()
        observeSyncStatus()
    }

    /**
     * Load all dashboard data.
     */
    fun loadDashboardData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            try {
                // Load data in parallel
                launch { loadRecentTransactions() }
                launch { loadBudgets() }
                launch { loadTransactionSummary() }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = e.message ?: "An error occurred"
                    )
                }
            }
        }
    }

    /**
     * Refresh dashboard data including sync.
     */
    fun refreshData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }

            try {
                // Sync data first
                val syncResult = syncDataUseCase.syncAll()

                if (syncResult.success) {
                    // Reload data after successful sync
                    loadDashboardData()
                    _events.emit(DashboardEvent.SyncCompleted)
                } else {
                    _events.emit(DashboardEvent.SyncFailed(syncResult.errorMessage ?: "Sync failed"))
                }
            } catch (e: Exception) {
                _events.emit(DashboardEvent.SyncFailed(e.message ?: "Sync failed"))
            } finally {
                _uiState.update { it.copy(isRefreshing = false) }
            }
        }
    }

    private suspend fun loadRecentTransactions() {
        getTransactionsUseCase.getRecentTransactions(10)
            .catch { e ->
                _uiState.update { it.copy(error = e.message) }
            }
            .collect { transactions ->
                _uiState.update {
                    it.copy(
                        recentTransactions = transactions,
                        isLoading = false
                    )
                }
            }
    }

    private suspend fun loadBudgets() {
        getBudgetsUseCase.getActiveBudgets()
            .catch { e ->
                _uiState.update { it.copy(error = e.message) }
            }
            .collect { budgets ->
                _uiState.update {
                    it.copy(
                        budgets = budgets,
                        budgetsNeedingAttention = budgets.count { b -> b.isNearLimit || b.isOverBudget }
                    )
                }
            }
    }

    private suspend fun loadTransactionSummary() {
        val now = LocalDate.now()
        val startOfMonth = now.withDayOfMonth(1)
        val endOfMonth = now.withDayOfMonth(now.lengthOfMonth())

        try {
            val summary = getTransactionsUseCase.getTransactionSummary(startOfMonth, endOfMonth)
            _uiState.update {
                it.copy(
                    totalBalance = summary.netAmount,
                    monthlyIncome = summary.totalIncome,
                    monthlyExpenses = summary.totalExpenses
                )
            }
        } catch (e: Exception) {
            _uiState.update { it.copy(error = e.message) }
        }
    }

    private fun observeSyncStatus() {
        viewModelScope.launch {
            syncDataUseCase.getSyncStatus().collect { status ->
                _uiState.update {
                    it.copy(
                        syncState = status,
                        isSyncing = status is SyncState.Syncing || status is SyncState.Progress
                    )
                }
            }
        }
    }

    /**
     * Mark notifications as read.
     */
    fun markNotificationsAsRead() {
        viewModelScope.launch {
            _uiState.update { it.copy(notificationCount = 0) }
        }
    }

    /**
     * Navigate to transaction detail.
     */
    fun onTransactionClicked(transactionId: String) {
        viewModelScope.launch {
            _events.emit(DashboardEvent.NavigateToTransactionDetail(transactionId))
        }
    }

    /**
     * Navigate to budget detail.
     */
    fun onBudgetClicked(budgetId: String) {
        viewModelScope.launch {
            _events.emit(DashboardEvent.NavigateToBudgetDetail(budgetId))
        }
    }

    /**
     * Clear error state.
     */
    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }
}

/**
 * UI state for the Dashboard screen.
 */
data class DashboardUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isSyncing: Boolean = false,
    val syncState: SyncState = SyncState.Idle,
    val userName: String = "User",
    val totalBalance: BigDecimal = BigDecimal.ZERO,
    val monthlyIncome: BigDecimal = BigDecimal.ZERO,
    val monthlyExpenses: BigDecimal = BigDecimal.ZERO,
    val recentTransactions: List<Transaction> = emptyList(),
    val budgets: List<Budget> = emptyList(),
    val budgetsNeedingAttention: Int = 0,
    val notificationCount: Int = 0,
    val error: String? = null
)

/**
 * Events emitted by the Dashboard ViewModel.
 */
sealed class DashboardEvent {
    data class NavigateToTransactionDetail(val transactionId: String) : DashboardEvent()
    data class NavigateToBudgetDetail(val budgetId: String) : DashboardEvent()
    object SyncCompleted : DashboardEvent()
    data class SyncFailed(val message: String) : DashboardEvent()
    data class ShowError(val message: String) : DashboardEvent()
}
