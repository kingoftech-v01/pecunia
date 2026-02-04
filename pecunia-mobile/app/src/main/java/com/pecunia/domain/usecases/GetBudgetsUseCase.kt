package com.pecunia.domain.usecases

import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetPeriod
import com.pecunia.domain.models.TransactionCategory
import com.pecunia.domain.repository.BudgetRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import javax.inject.Inject

/**
 * Use case for retrieving budgets.
 * Follows Clean Architecture principles with a single responsibility.
 */
class GetBudgetsUseCase @Inject constructor(
    private val budgetRepository: BudgetRepository
) {
    /**
     * Invoke operator to get budgets with optional filters.
     *
     * @param params Optional parameters for filtering budgets.
     * @return Flow of Result containing list of budgets or error.
     */
    operator fun invoke(params: Params = Params()): Flow<Result<List<Budget>>> {
        return when {
            params.budgetId != null -> {
                budgetRepository.getBudgetFlow(params.budgetId)
                    .map { budget ->
                        if (budget != null) listOf(budget) else emptyList()
                    }
            }
            params.category != null -> {
                budgetRepository.getBudgetsByCategory(params.category)
            }
            params.period != null -> {
                budgetRepository.getBudgetsByPeriod(params.period)
            }
            params.needingAttention -> {
                budgetRepository.getBudgetsNeedingAttention()
            }
            params.activeOnly -> {
                budgetRepository.getActiveBudgets()
            }
            else -> {
                budgetRepository.getAllBudgets()
            }
        }.map { budgets ->
            Result.success(budgets)
        }.catch { exception ->
            emit(Result.failure(exception))
        }
    }

    /**
     * Parameters for filtering budgets.
     */
    data class Params(
        val budgetId: String? = null,
        val category: TransactionCategory? = null,
        val period: BudgetPeriod? = null,
        val activeOnly: Boolean = false,
        val needingAttention: Boolean = false
    )
}
