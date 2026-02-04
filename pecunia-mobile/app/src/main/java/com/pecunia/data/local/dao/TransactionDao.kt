package com.pecunia.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Update
import com.pecunia.data.local.entity.TransactionEntity
import com.pecunia.data.local.entity.TransactionWithCategory
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for Transaction operations.
 * Handles all database operations related to financial transactions.
 */
@Dao
interface TransactionDao {

    /**
     * Observes all transactions for a specific user, ordered by date descending.
     * @param userId The user's ID
     * @return Flow emitting list of transactions
     */
    @Query("SELECT * FROM transactions WHERE userId = :userId ORDER BY date DESC, createdAt DESC")
    fun getTransactions(userId: String): Flow<List<TransactionEntity>>

    /**
     * Observes all transactions with their associated category information.
     * @param userId The user's ID
     * @return Flow emitting list of transactions with category details
     */
    @Transaction
    @Query("SELECT * FROM transactions WHERE userId = :userId ORDER BY date DESC, createdAt DESC")
    fun getTransactionsWithCategory(userId: String): Flow<List<TransactionWithCategory>>

    /**
     * Observes a single transaction by its ID.
     * @param id The transaction's unique ID
     * @return Flow emitting the transaction or null if not found
     */
    @Query("SELECT * FROM transactions WHERE id = :id")
    fun getTransactionById(id: String): Flow<TransactionEntity?>

    /**
     * Gets a transaction synchronously by its ID.
     * @param id The transaction's unique ID
     * @return The transaction entity or null if not found
     */
    @Query("SELECT * FROM transactions WHERE id = :id")
    suspend fun getTransactionByIdSync(id: String): TransactionEntity?

    /**
     * Observes transactions within a specific date range.
     * @param userId The user's ID
     * @param startDate Start date timestamp (inclusive)
     * @param endDate End date timestamp (inclusive)
     * @return Flow emitting list of transactions in the date range
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        AND date >= :startDate
        AND date <= :endDate
        ORDER BY date DESC, createdAt DESC
    """)
    fun getTransactionsByDateRange(
        userId: String,
        startDate: Long,
        endDate: Long
    ): Flow<List<TransactionEntity>>

    /**
     * Observes transactions for a specific category.
     * @param userId The user's ID
     * @param categoryId The category's ID
     * @return Flow emitting list of transactions in the category
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        AND categoryId = :categoryId
        ORDER BY date DESC, createdAt DESC
    """)
    fun getTransactionsByCategory(
        userId: String,
        categoryId: String
    ): Flow<List<TransactionEntity>>

    /**
     * Observes transactions for a specific bank account.
     * @param userId The user's ID
     * @param accountId The bank account's ID
     * @return Flow emitting list of transactions for the account
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        AND accountId = :accountId
        ORDER BY date DESC, createdAt DESC
    """)
    fun getTransactionsByAccount(
        userId: String,
        accountId: String
    ): Flow<List<TransactionEntity>>

    /**
     * Searches transactions by description, merchant name, or notes.
     * @param userId The user's ID
     * @param query The search query (partial match supported)
     * @return Flow emitting list of matching transactions
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        AND (
            description LIKE '%' || :query || '%'
            OR merchantName LIKE '%' || :query || '%'
            OR notes LIKE '%' || :query || '%'
        )
        ORDER BY date DESC, createdAt DESC
    """)
    fun searchTransactions(userId: String, query: String): Flow<List<TransactionEntity>>

    /**
     * Gets transactions by type (income, expense, transfer).
     * @param userId The user's ID
     * @param type The transaction type
     * @return Flow emitting list of transactions of the specified type
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        AND type = :type
        ORDER BY date DESC, createdAt DESC
    """)
    fun getTransactionsByType(userId: String, type: String): Flow<List<TransactionEntity>>

    /**
     * Inserts a new transaction into the database.
     * @param transaction The transaction entity to insert
     * @return The row ID of the inserted transaction
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(transaction: TransactionEntity): Long

    /**
     * Inserts multiple transactions into the database.
     * @param transactions List of transaction entities to insert
     * @return List of row IDs for inserted transactions
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(transactions: List<TransactionEntity>): List<Long>

    /**
     * Updates an existing transaction in the database.
     * @param transaction The transaction entity with updated values
     * @return The number of rows updated
     */
    @Update
    suspend fun update(transaction: TransactionEntity): Int

    /**
     * Deletes a transaction from the database.
     * @param transaction The transaction entity to delete
     * @return The number of rows deleted
     */
    @Delete
    suspend fun delete(transaction: TransactionEntity): Int

    /**
     * Deletes multiple transactions by their IDs.
     * @param ids List of transaction IDs to delete
     * @return The number of rows deleted
     */
    @Query("DELETE FROM transactions WHERE id IN (:ids)")
    suspend fun deleteByIds(ids: List<String>): Int

    /**
     * Deletes all transactions for a specific user.
     * @param userId The user's ID
     */
    @Query("DELETE FROM transactions WHERE userId = :userId")
    suspend fun deleteAllForUser(userId: String)

    /**
     * Gets all transactions pending synchronization.
     * @param userId The user's ID
     * @return List of transactions that need to be synced
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        AND syncStatus != 'SYNCED'
        ORDER BY updatedAt ASC
    """)
    suspend fun getPendingSyncTransactions(userId: String): List<TransactionEntity>

    /**
     * Updates the sync status of a transaction.
     * @param id The transaction's ID
     * @param syncStatus The new sync status
     */
    @Query("UPDATE transactions SET syncStatus = :syncStatus, updatedAt = :updatedAt WHERE id = :id")
    suspend fun updateSyncStatus(id: String, syncStatus: String, updatedAt: Long)

    /**
     * Marks multiple transactions as synced.
     * @param ids List of transaction IDs
     * @param syncStatus The sync status to set
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE transactions SET syncStatus = :syncStatus, updatedAt = :updatedAt WHERE id IN (:ids)")
    suspend fun markAsSynced(ids: List<String>, syncStatus: String, updatedAt: Long)

    /**
     * Gets the sum of transactions by type within a date range.
     * @param userId The user's ID
     * @param type The transaction type
     * @param startDate Start date timestamp
     * @param endDate End date timestamp
     * @return The total sum of transactions
     */
    @Query("""
        SELECT COALESCE(SUM(amount), 0) FROM transactions
        WHERE userId = :userId
        AND type = :type
        AND date >= :startDate
        AND date <= :endDate
    """)
    suspend fun getSumByTypeAndDateRange(
        userId: String,
        type: String,
        startDate: Long,
        endDate: Long
    ): Double

    /**
     * Gets the count of transactions for a specific category.
     * @param userId The user's ID
     * @param categoryId The category's ID
     * @return The number of transactions in the category
     */
    @Query("""
        SELECT COUNT(*) FROM transactions
        WHERE userId = :userId
        AND categoryId = :categoryId
    """)
    suspend fun getTransactionCountByCategory(userId: String, categoryId: String): Int

    /**
     * Gets spending breakdown by category within a date range.
     * @param userId The user's ID
     * @param type The transaction type (typically 'expense')
     * @param startDate Start date timestamp
     * @param endDate End date timestamp
     * @return Map of category ID to total amount
     */
    @Query("""
        SELECT categoryId, SUM(amount) as total
        FROM transactions
        WHERE userId = :userId
        AND type = :type
        AND date >= :startDate
        AND date <= :endDate
        GROUP BY categoryId
    """)
    suspend fun getSpendingByCategory(
        userId: String,
        type: String,
        startDate: Long,
        endDate: Long
    ): List<CategorySpending>

    /**
     * Gets recent transactions with a limit.
     * @param userId The user's ID
     * @param limit Maximum number of transactions to return
     * @return Flow emitting list of recent transactions
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        ORDER BY date DESC, createdAt DESC
        LIMIT :limit
    """)
    fun getRecentTransactions(userId: String, limit: Int): Flow<List<TransactionEntity>>

    /**
     * Gets transactions that are recurring.
     * @param userId The user's ID
     * @return Flow emitting list of recurring transactions
     */
    @Query("""
        SELECT * FROM transactions
        WHERE userId = :userId
        AND isRecurring = 1
        ORDER BY date DESC
    """)
    fun getRecurringTransactions(userId: String): Flow<List<TransactionEntity>>
}

/**
 * Data class for category spending aggregation results.
 */
data class CategorySpending(
    val categoryId: String?,
    val total: Double
)
