package com.pecunia.domain.usecases

import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionCategory
import com.pecunia.domain.models.TransactionSummary
import com.pecunia.domain.models.TransactionType
import kotlinx.coroutines.flow.Flow
import java.math.BigDecimal
import java.time.LocalDate

/**
 * Use case for retrieving and managing transactions.
 */
class GetTransactionsUseCase(
    private val transactionRepository: TransactionRepository
) {
    /**
     * Get all transactions for the current user.
     */
    suspend fun getAllTransactions(): Flow<List<Transaction>> {
        return transactionRepository.getAllTransactions()
    }

    /**
     * Get transactions within a date range.
     */
    suspend fun getTransactionsByDateRange(
        startDate: LocalDate,
        endDate: LocalDate
    ): Flow<List<Transaction>> {
        return transactionRepository.getTransactionsByDateRange(startDate, endDate)
    }

    /**
     * Get transactions by category.
     */
    suspend fun getTransactionsByCategory(
        category: TransactionCategory
    ): Flow<List<Transaction>> {
        return transactionRepository.getTransactionsByCategory(category)
    }

    /**
     * Get transactions by type (income/expense/transfer).
     */
    suspend fun getTransactionsByType(
        type: TransactionType
    ): Flow<List<Transaction>> {
        return transactionRepository.getTransactionsByType(type)
    }

    /**
     * Get a single transaction by ID.
     */
    suspend fun getTransactionById(id: String): Transaction? {
        return transactionRepository.getTransactionById(id)
    }

    /**
     * Get transaction summary for a date range.
     */
    suspend fun getTransactionSummary(
        startDate: LocalDate,
        endDate: LocalDate
    ): TransactionSummary {
        return transactionRepository.getTransactionSummary(startDate, endDate)
    }

    /**
     * Search transactions by description or merchant.
     */
    suspend fun searchTransactions(query: String): Flow<List<Transaction>> {
        return transactionRepository.searchTransactions(query)
    }

    /**
     * Get recent transactions with a limit.
     */
    suspend fun getRecentTransactions(limit: Int = 10): Flow<List<Transaction>> {
        return transactionRepository.getRecentTransactions(limit)
    }

    /**
     * Get recurring transactions.
     */
    suspend fun getRecurringTransactions(): Flow<List<Transaction>> {
        return transactionRepository.getRecurringTransactions()
    }
}

/**
 * Repository interface for transaction data access.
 */
interface TransactionRepository {
    suspend fun getAllTransactions(): Flow<List<Transaction>>
    suspend fun getTransactionsByDateRange(startDate: LocalDate, endDate: LocalDate): Flow<List<Transaction>>
    suspend fun getTransactionsByCategory(category: TransactionCategory): Flow<List<Transaction>>
    suspend fun getTransactionsByType(type: TransactionType): Flow<List<Transaction>>
    suspend fun getTransactionById(id: String): Transaction?
    suspend fun getTransactionSummary(startDate: LocalDate, endDate: LocalDate): TransactionSummary
    suspend fun searchTransactions(query: String): Flow<List<Transaction>>
    suspend fun getRecentTransactions(limit: Int): Flow<List<Transaction>>
    suspend fun getRecurringTransactions(): Flow<List<Transaction>>
    suspend fun insertTransaction(transaction: Transaction)
    suspend fun updateTransaction(transaction: Transaction)
    suspend fun deleteTransaction(id: String)
    suspend fun getTransactionsByBudgetCategory(category: TransactionCategory, startDate: LocalDate, endDate: LocalDate): List<Transaction>
}
