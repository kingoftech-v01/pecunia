package com.pecunia.domain.usecases

import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionCategory
import com.pecunia.domain.models.TransactionType
import com.pecunia.domain.repository.TransactionRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.time.LocalDate
import javax.inject.Inject

/**
 * Use case for retrieving transactions.
 * Follows Clean Architecture principles with a single responsibility.
 */
class GetTransactionsUseCase @Inject constructor(
    private val transactionRepository: TransactionRepository
) {
    /**
     * Invoke operator to get all transactions with optional filters.
     *
     * @param params Optional parameters for filtering transactions.
     * @return Flow of Result containing list of transactions or error.
     */
    operator fun invoke(params: Params = Params()): Flow<Result<List<Transaction>>> {
        return when {
            params.dateRange != null -> {
                transactionRepository.getTransactionsByDateRange(
                    params.dateRange.first,
                    params.dateRange.second
                )
            }
            params.category != null -> {
                transactionRepository.getTransactionsByCategory(params.category)
            }
            params.type != null -> {
                transactionRepository.getTransactionsByType(params.type)
            }
            params.searchQuery != null -> {
                transactionRepository.searchTransactions(params.searchQuery)
            }
            params.limit != null -> {
                transactionRepository.getRecentTransactions(params.limit)
            }
            params.recurringOnly -> {
                transactionRepository.getRecurringTransactions()
            }
            else -> {
                transactionRepository.getAllTransactions()
            }
        }.map { transactions ->
            Result.success(transactions)
        }.catch { exception ->
            emit(Result.failure(exception))
        }
    }

    /**
     * Parameters for filtering transactions.
     */
    data class Params(
        val dateRange: Pair<LocalDate, LocalDate>? = null,
        val category: TransactionCategory? = null,
        val type: TransactionType? = null,
        val searchQuery: String? = null,
        val limit: Int? = null,
        val recurringOnly: Boolean = false
    )
}
