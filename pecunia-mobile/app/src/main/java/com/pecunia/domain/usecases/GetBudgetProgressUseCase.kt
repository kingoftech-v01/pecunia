package com.pecunia.domain.usecases

import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetAlert
import com.pecunia.domain.models.BudgetAlertType
import com.pecunia.domain.models.BudgetSummary
import com.pecunia.domain.models.BudgetWithTransactions
import com.pecunia.domain.repository.BudgetRepository
import com.pecunia.domain.repository.TransactionRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import java.math.BigDecimal
import java.time.Instant
import java.time.YearMonth
import javax.inject.Inject

/**
 * Use case for retrieving budget progress and related analytics.
 * Combines budget data with transaction data to calculate progress.
 */
class GetBudgetProgressUseCase @Inject constructor(
    private val budgetRepository: BudgetRepository,
    private val transactionRepository: TransactionRepository
) {
    /**
     * Invoke operator to get budget progress data.
     *
     * @param params Parameters specifying what progress data to retrieve.
     * @return Flow of Result containing budget progress state.
     */
    operator fun invoke(params: Params): Flow<Result<BudgetProgressState>> = flow {
        try {
            when (params) {
                is Params.SingleBudget -> {
                    budgetRepository.getBudgetWithTransactions(params.budgetId)
                        .collect { budgetWithTransactions ->
                            if (budgetWithTransactions != null) {
                                val progress = calculateProgress(budgetWithTransactions.budget)
                                val alerts = generateAlerts(budgetWithTransactions.budget)
                                emit(Result.success(
                                    BudgetProgressState.SingleBudgetProgress(
                                        budget = budgetWithTransactions.budget,
                                        transactions = budgetWithTransactions.transactions,
                                        progress = progress,
                                        alerts = alerts
                                    )
                                ))
                            } else {
                                emit(Result.failure(NoSuchElementException("Budget not found")))
                            }
                        }
                }
                is Params.Summary -> {
                    budgetRepository.getBudgetSummary(params.yearMonth)
                        .collect { summary ->
                            emit(Result.success(
                                BudgetProgressState.SummaryProgress(summary)
                            ))
                        }
                }
                is Params.AllBudgets -> {
                    budgetRepository.getActiveBudgets()
                        .map { budgets ->
                            val progressList = budgets.map { budget ->
                                BudgetProgress(
                                    budget = budget,
                                    percentageUsed = budget.percentageUsed,
                                    remaining = budget.remaining,
                                    isOverBudget = budget.isOverBudget,
                                    isNearLimit = budget.isNearLimit,
                                    alerts = generateAlerts(budget)
                                )
                            }
                            BudgetProgressState.AllBudgetsProgress(progressList)
                        }
                        .collect { state ->
                            emit(Result.success(state))
                        }
                }
            }
        } catch (e: Exception) {
            emit(Result.failure(e))
        }
    }

    /**
     * Calculate progress details for a budget.
     */
    private fun calculateProgress(budget: Budget): BudgetProgress {
        return BudgetProgress(
            budget = budget,
            percentageUsed = budget.percentageUsed,
            remaining = budget.remaining,
            isOverBudget = budget.isOverBudget,
            isNearLimit = budget.isNearLimit,
            alerts = generateAlerts(budget)
        )
    }

    /**
     * Generate alerts for a budget based on its current state.
     */
    private fun generateAlerts(budget: Budget): List<BudgetAlert> {
        val alerts = mutableListOf<BudgetAlert>()

        if (!budget.alertsEnabled) return alerts

        when {
            budget.isOverBudget -> {
                alerts.add(
                    BudgetAlert(
                        budgetId = budget.id,
                        budgetName = budget.name,
                        alertType = BudgetAlertType.OVER_BUDGET,
                        percentageUsed = budget.percentageUsed,
                        amountRemaining = budget.remaining,
                        timestamp = Instant.now()
                    )
                )
            }
            budget.percentageUsed >= 1.0f -> {
                alerts.add(
                    BudgetAlert(
                        budgetId = budget.id,
                        budgetName = budget.name,
                        alertType = BudgetAlertType.LIMIT_REACHED,
                        percentageUsed = budget.percentageUsed,
                        amountRemaining = budget.remaining,
                        timestamp = Instant.now()
                    )
                )
            }
            budget.isNearLimit -> {
                alerts.add(
                    BudgetAlert(
                        budgetId = budget.id,
                        budgetName = budget.name,
                        alertType = BudgetAlertType.APPROACHING_LIMIT,
                        percentageUsed = budget.percentageUsed,
                        amountRemaining = budget.remaining,
                        timestamp = Instant.now()
                    )
                )
            }
        }

        return alerts
    }

    /**
     * Parameters for budget progress retrieval.
     */
    sealed class Params {
        data class SingleBudget(val budgetId: String) : Params()
        data class Summary(val yearMonth: YearMonth = YearMonth.now()) : Params()
        data object AllBudgets : Params()
    }

    /**
     * Represents budget progress state.
     */
    sealed class BudgetProgressState {
        data class SingleBudgetProgress(
            val budget: Budget,
            val transactions: List<com.pecunia.domain.models.Transaction>,
            val progress: BudgetProgress,
            val alerts: List<BudgetAlert>
        ) : BudgetProgressState()

        data class SummaryProgress(
            val summary: BudgetSummary
        ) : BudgetProgressState()

        data class AllBudgetsProgress(
            val budgetProgressList: List<BudgetProgress>
        ) : BudgetProgressState()
    }

    /**
     * Progress details for a single budget.
     */
    data class BudgetProgress(
        val budget: Budget,
        val percentageUsed: Float,
        val remaining: BigDecimal,
        val isOverBudget: Boolean,
        val isNearLimit: Boolean,
        val alerts: List<BudgetAlert>
    )
}
