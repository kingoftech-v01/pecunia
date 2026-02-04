package com.pecunia.domain.usecases

import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetAlert
import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionSummary
import com.pecunia.domain.repository.BudgetRepository
import com.pecunia.domain.repository.TransactionRepository
import com.pecunia.domain.repository.UserRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import java.math.BigDecimal
import java.time.LocalDate
import java.time.YearMonth
import javax.inject.Inject

/**
 * Use case for retrieving aggregated dashboard data.
 * Combines data from multiple repositories into a single dashboard state.
 */
class GetDashboardDataUseCase @Inject constructor(
    private val transactionRepository: TransactionRepository,
    private val budgetRepository: BudgetRepository,
    private val userRepository: UserRepository
) {
    /**
     * Invoke operator to get dashboard data.
     *
     * @param params Parameters for customizing dashboard data retrieval.
     * @return Flow of Result containing dashboard state.
     */
    operator fun invoke(params: Params = Params()): Flow<Result<DashboardState>> {
        val now = LocalDate.now()
        val startOfMonth = now.withDayOfMonth(1)
        val endOfMonth = now.withDayOfMonth(now.lengthOfMonth())
        val recentTransactionLimit = params.recentTransactionLimit

        return combine(
            transactionRepository.getRecentTransactions(recentTransactionLimit),
            budgetRepository.getActiveBudgets(),
            budgetRepository.getBudgetsNeedingAttention(),
            budgetRepository.getBudgetAlerts(),
            getUserInfo()
        ) { recentTransactions, activeBudgets, budgetsNeedingAttention, alerts, userInfo ->

            DashboardState(
                userName = userInfo.name,
                recentTransactions = recentTransactions,
                activeBudgets = activeBudgets,
                budgetsNeedingAttention = budgetsNeedingAttention,
                budgetAlerts = alerts,
                totalBudgetCount = activeBudgets.size,
                alertCount = alerts.size
            )
        }.combine(
            getTransactionSummary(startOfMonth, endOfMonth)
        ) { dashboardState, summary ->
            dashboardState.copy(
                totalBalance = summary.netAmount,
                monthlyIncome = summary.totalIncome,
                monthlyExpenses = summary.totalExpenses,
                transactionCount = summary.transactionCount,
                categoryBreakdown = summary.categoryBreakdown
            )
        }.map { state ->
            Result.success(state)
        }.catch { exception ->
            emit(Result.failure(exception))
        }
    }

    /**
     * Get user information for dashboard greeting.
     */
    private fun getUserInfo(): Flow<UserInfo> = flow {
        try {
            val user = userRepository.getCurrentUser()
            emit(UserInfo(
                id = user?.id ?: "",
                name = user?.displayName ?: "User"
            ))
        } catch (e: Exception) {
            emit(UserInfo(id = "", name = "User"))
        }
    }

    /**
     * Get transaction summary for the specified date range.
     */
    private fun getTransactionSummary(
        startDate: LocalDate,
        endDate: LocalDate
    ): Flow<TransactionSummary> {
        return transactionRepository.getTransactionsByDateRange(startDate, endDate)
            .map { transactions ->
                calculateSummary(transactions)
            }
    }

    /**
     * Calculate transaction summary from list of transactions.
     */
    private fun calculateSummary(transactions: List<Transaction>): TransactionSummary {
        val totalIncome = transactions
            .filter { it.type == com.pecunia.domain.models.TransactionType.INCOME }
            .sumOf { it.amount }

        val totalExpenses = transactions
            .filter { it.type == com.pecunia.domain.models.TransactionType.EXPENSE }
            .sumOf { it.amount }

        val categoryBreakdown = transactions
            .filter { it.type == com.pecunia.domain.models.TransactionType.EXPENSE }
            .groupBy { it.category }
            .mapValues { (_, txns) -> txns.sumOf { it.amount } }

        return TransactionSummary(
            totalIncome = totalIncome,
            totalExpenses = totalExpenses,
            netAmount = totalIncome.subtract(totalExpenses),
            transactionCount = transactions.size,
            categoryBreakdown = categoryBreakdown
        )
    }

    /**
     * Parameters for dashboard data retrieval.
     */
    data class Params(
        val recentTransactionLimit: Int = 10,
        val includeAlerts: Boolean = true,
        val yearMonth: YearMonth = YearMonth.now()
    )

    /**
     * Simple user info for dashboard display.
     */
    private data class UserInfo(
        val id: String,
        val name: String
    )

    /**
     * Represents the complete dashboard state.
     */
    data class DashboardState(
        val userName: String = "User",
        val totalBalance: BigDecimal = BigDecimal.ZERO,
        val monthlyIncome: BigDecimal = BigDecimal.ZERO,
        val monthlyExpenses: BigDecimal = BigDecimal.ZERO,
        val transactionCount: Int = 0,
        val recentTransactions: List<Transaction> = emptyList(),
        val activeBudgets: List<Budget> = emptyList(),
        val budgetsNeedingAttention: List<Budget> = emptyList(),
        val budgetAlerts: List<BudgetAlert> = emptyList(),
        val totalBudgetCount: Int = 0,
        val alertCount: Int = 0,
        val categoryBreakdown: Map<com.pecunia.domain.models.TransactionCategory, BigDecimal> = emptyMap()
    ) {
        /**
         * Check if there are any budgets requiring user attention.
         */
        val hasBudgetAlerts: Boolean
            get() = budgetAlerts.isNotEmpty()

        /**
         * Get the percentage of budgets that are on track.
         */
        val budgetsOnTrackPercentage: Float
            get() = if (totalBudgetCount > 0) {
                (totalBudgetCount - budgetsNeedingAttention.size).toFloat() / totalBudgetCount
            } else {
                1.0f
            }

        /**
         * Get the savings rate for the current month.
         */
        val savingsRate: Float
            get() = if (monthlyIncome > BigDecimal.ZERO) {
                (monthlyIncome.subtract(monthlyExpenses)).toFloat() / monthlyIncome.toFloat()
            } else {
                0f
            }
    }
}
