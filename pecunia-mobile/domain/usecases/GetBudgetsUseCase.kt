package com.pecunia.domain.usecases

import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetAlert
import com.pecunia.domain.models.BudgetPeriod
import com.pecunia.domain.models.BudgetSummary
import com.pecunia.domain.models.BudgetWithTransactions
import com.pecunia.domain.models.TransactionCategory
import kotlinx.coroutines.flow.Flow
import java.time.YearMonth

/**
 * Use case for retrieving and managing budgets.
 */
class GetBudgetsUseCase(
    private val budgetRepository: BudgetRepository
) {
    /**
     * Get all budgets for the current user.
     */
    suspend fun getAllBudgets(): Flow<List<Budget>> {
        return budgetRepository.getAllBudgets()
    }

    /**
     * Get active budgets only.
     */
    suspend fun getActiveBudgets(): Flow<List<Budget>> {
        return budgetRepository.getActiveBudgets()
    }

    /**
     * Get a single budget by ID.
     */
    suspend fun getBudgetById(id: String): Budget? {
        return budgetRepository.getBudgetById(id)
    }

    /**
     * Get budgets by category.
     */
    suspend fun getBudgetsByCategory(category: TransactionCategory): Flow<List<Budget>> {
        return budgetRepository.getBudgetsByCategory(category)
    }

    /**
     * Get budgets by period type.
     */
    suspend fun getBudgetsByPeriod(period: BudgetPeriod): Flow<List<Budget>> {
        return budgetRepository.getBudgetsByPeriod(period)
    }

    /**
     * Get budget summary for a specific month.
     */
    suspend fun getBudgetSummary(yearMonth: YearMonth): BudgetSummary {
        return budgetRepository.getBudgetSummary(yearMonth)
    }

    /**
     * Get budget with associated transactions.
     */
    suspend fun getBudgetWithTransactions(budgetId: String): BudgetWithTransactions? {
        return budgetRepository.getBudgetWithTransactions(budgetId)
    }

    /**
     * Get all budget alerts.
     */
    suspend fun getBudgetAlerts(): Flow<List<BudgetAlert>> {
        return budgetRepository.getBudgetAlerts()
    }

    /**
     * Get budgets that are near or over limit.
     */
    suspend fun getBudgetsNeedingAttention(): Flow<List<Budget>> {
        return budgetRepository.getBudgetsNeedingAttention()
    }

    /**
     * Calculate budget progress and update current spent amount.
     */
    suspend fun refreshBudgetProgress(budgetId: String) {
        budgetRepository.refreshBudgetProgress(budgetId)
    }

    /**
     * Refresh all budget progress.
     */
    suspend fun refreshAllBudgetsProgress() {
        budgetRepository.refreshAllBudgetsProgress()
    }
}

/**
 * Repository interface for budget data access.
 */
interface BudgetRepository {
    suspend fun getAllBudgets(): Flow<List<Budget>>
    suspend fun getActiveBudgets(): Flow<List<Budget>>
    suspend fun getBudgetById(id: String): Budget?
    suspend fun getBudgetsByCategory(category: TransactionCategory): Flow<List<Budget>>
    suspend fun getBudgetsByPeriod(period: BudgetPeriod): Flow<List<Budget>>
    suspend fun getBudgetSummary(yearMonth: YearMonth): BudgetSummary
    suspend fun getBudgetWithTransactions(budgetId: String): BudgetWithTransactions?
    suspend fun getBudgetAlerts(): Flow<List<BudgetAlert>>
    suspend fun getBudgetsNeedingAttention(): Flow<List<Budget>>
    suspend fun insertBudget(budget: Budget)
    suspend fun updateBudget(budget: Budget)
    suspend fun deleteBudget(id: String)
    suspend fun refreshBudgetProgress(budgetId: String)
    suspend fun refreshAllBudgetsProgress()
}
