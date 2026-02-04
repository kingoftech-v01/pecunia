package com.pecunia.data.local.database.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.pecunia.data.local.database.entities.TransactionEntity
import com.pecunia.data.local.database.entities.TransactionType
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for Transaction entities.
 */
@Dao
interface TransactionDao {

    // Insert operations

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(transaction: TransactionEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(transactions: List<TransactionEntity>)

    // Update operations

    @Update
    suspend fun update(transaction: TransactionEntity)

    @Query("UPDATE transactions SET is_synced = :isSynced WHERE id = :transactionId")
    suspend fun updateSyncStatus(transactionId: String, isSynced: Boolean)

    // Delete operations

    @Delete
    suspend fun delete(transaction: TransactionEntity)

    @Query("DELETE FROM transactions WHERE id = :transactionId")
    suspend fun deleteById(transactionId: String)

    @Query("DELETE FROM transactions WHERE user_id = :userId")
    suspend fun deleteAllByUserId(userId: String)

    @Query("DELETE FROM transactions")
    suspend fun deleteAll()

    // Query operations - Single items

    @Query("SELECT * FROM transactions WHERE id = :transactionId")
    suspend fun getById(transactionId: String): TransactionEntity?

    @Query("SELECT * FROM transactions WHERE id = :transactionId")
    fun getByIdFlow(transactionId: String): Flow<TransactionEntity?>

    // Query operations - Lists

    @Query("SELECT * FROM transactions WHERE user_id = :userId ORDER BY date DESC")
    fun getAllByUserId(userId: String): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE user_id = :userId ORDER BY date DESC LIMIT :limit OFFSET :offset")
    suspend fun getByUserIdPaginated(userId: String, limit: Int, offset: Int): List<TransactionEntity>

    @Query("SELECT * FROM transactions WHERE user_id = :userId AND type = :type ORDER BY date DESC")
    fun getByType(userId: String, type: TransactionType): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE user_id = :userId AND category = :category ORDER BY date DESC")
    fun getByCategory(userId: String, category: String): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE user_id = :userId AND date BETWEEN :startDate AND :endDate ORDER BY date DESC")
    fun getByDateRange(userId: String, startDate: Long, endDate: Long): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE user_id = :userId AND date BETWEEN :startDate AND :endDate AND category = :category ORDER BY date DESC")
    fun getByCategoryAndDateRange(
        userId: String,
        category: String,
        startDate: Long,
        endDate: Long
    ): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE is_synced = 0")
    suspend fun getUnsyncedTransactions(): List<TransactionEntity>

    @Query("SELECT * FROM transactions WHERE user_id = :userId AND is_recurring = 1 ORDER BY date DESC")
    fun getRecurringTransactions(userId: String): Flow<List<TransactionEntity>>

    // Aggregate queries

    @Query("SELECT SUM(amount) FROM transactions WHERE user_id = :userId AND type = :type AND date BETWEEN :startDate AND :endDate")
    suspend fun getTotalByTypeAndDateRange(
        userId: String,
        type: TransactionType,
        startDate: Long,
        endDate: Long
    ): Double?

    @Query("SELECT SUM(amount) FROM transactions WHERE user_id = :userId AND category = :category AND date BETWEEN :startDate AND :endDate")
    suspend fun getTotalByCategoryAndDateRange(
        userId: String,
        category: String,
        startDate: Long,
        endDate: Long
    ): Double?

    @Query("SELECT COUNT(*) FROM transactions WHERE user_id = :userId")
    suspend fun getTransactionCount(userId: String): Int

    @Query("SELECT DISTINCT category FROM transactions WHERE user_id = :userId ORDER BY category")
    suspend fun getAllCategories(userId: String): List<String>

    // Search

    @Query("""
        SELECT * FROM transactions
        WHERE user_id = :userId
        AND (description LIKE '%' || :query || '%'
             OR merchant_name LIKE '%' || :query || '%'
             OR notes LIKE '%' || :query || '%')
        ORDER BY date DESC
    """)
    fun searchTransactions(userId: String, query: String): Flow<List<TransactionEntity>>
}
