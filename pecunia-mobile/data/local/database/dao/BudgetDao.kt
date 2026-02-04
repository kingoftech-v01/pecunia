package com.pecunia.data.local.database.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.pecunia.data.local.database.entities.BudgetEntity
import com.pecunia.data.local.database.entities.BudgetPeriodType
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for Budget entities.
 */
@Dao
interface BudgetDao {

    // Insert operations

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(budget: BudgetEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(budgets: List<BudgetEntity>)

    // Update operations

    @Update
    suspend fun update(budget: BudgetEntity)

    @Query("UPDATE budgets SET spent_amount = :spentAmount, updated_at = :updatedAt WHERE id = :budgetId")
    suspend fun updateSpentAmount(budgetId: String, spentAmount: Double, updatedAt: Long = System.currentTimeMillis())

    @Query("UPDATE budgets SET is_synced = :isSynced WHERE id = :budgetId")
    suspend fun updateSyncStatus(budgetId: String, isSynced: Boolean)

    @Query("UPDATE budgets SET is_active = :isActive, updated_at = :updatedAt WHERE id = :budgetId")
    suspend fun updateActiveStatus(budgetId: String, isActive: Boolean, updatedAt: Long = System.currentTimeMillis())

    // Delete operations

    @Delete
    suspend fun delete(budget: BudgetEntity)

    @Query("DELETE FROM budgets WHERE id = :budgetId")
    suspend fun deleteById(budgetId: String)

    @Query("DELETE FROM budgets WHERE user_id = :userId")
    suspend fun deleteAllByUserId(userId: String)

    @Query("DELETE FROM budgets")
    suspend fun deleteAll()

    // Query operations - Single items

    @Query("SELECT * FROM budgets WHERE id = :budgetId")
    suspend fun getById(budgetId: String): BudgetEntity?

    @Query("SELECT * FROM budgets WHERE id = :budgetId")
    fun getByIdFlow(budgetId: String): Flow<BudgetEntity?>

    @Query("SELECT * FROM budgets WHERE user_id = :userId AND category = :category AND is_active = 1 LIMIT 1")
    suspend fun getActiveBudgetByCategory(userId: String, category: String): BudgetEntity?

    // Query operations - Lists

    @Query("SELECT * FROM budgets WHERE user_id = :userId ORDER BY created_at DESC")
    fun getAllByUserId(userId: String): Flow<List<BudgetEntity>>

    @Query("SELECT * FROM budgets WHERE user_id = :userId AND is_active = 1 ORDER BY category")
    fun getActiveBudgets(userId: String): Flow<List<BudgetEntity>>

    @Query("SELECT * FROM budgets WHERE user_id = :userId AND is_active = 0 ORDER BY updated_at DESC")
    fun getInactiveBudgets(userId: String): Flow<List<BudgetEntity>>

    @Query("SELECT * FROM budgets WHERE user_id = :userId AND period_type = :periodType AND is_active = 1 ORDER BY category")
    fun getByPeriodType(userId: String, periodType: BudgetPeriodType): Flow<List<BudgetEntity>>

    @Query("SELECT * FROM budgets WHERE user_id = :userId AND category = :category ORDER BY created_at DESC")
    fun getByCategory(userId: String, category: String): Flow<List<BudgetEntity>>

    @Query("SELECT * FROM budgets WHERE is_synced = 0")
    suspend fun getUnsyncedBudgets(): List<BudgetEntity>

    @Query("""
        SELECT * FROM budgets
        WHERE user_id = :userId
        AND is_active = 1
        AND (spent_amount / budget_amount) >= alert_threshold
        ORDER BY (spent_amount / budget_amount) DESC
    """)
    fun getBudgetsOverThreshold(userId: String): Flow<List<BudgetEntity>>

    @Query("""
        SELECT * FROM budgets
        WHERE user_id = :userId
        AND is_active = 1
        AND spent_amount > budget_amount
        ORDER BY (spent_amount - budget_amount) DESC
    """)
    fun getExceededBudgets(userId: String): Flow<List<BudgetEntity>>

    @Query("""
        SELECT * FROM budgets
        WHERE user_id = :userId
        AND is_active = 1
        AND :currentDate BETWEEN start_date AND end_date
        ORDER BY category
    """)
    fun getCurrentBudgets(userId: String, currentDate: Long): Flow<List<BudgetEntity>>

    // Aggregate queries

    @Query("SELECT SUM(budget_amount) FROM budgets WHERE user_id = :userId AND is_active = 1")
    suspend fun getTotalBudgetAmount(userId: String): Double?

    @Query("SELECT SUM(spent_amount) FROM budgets WHERE user_id = :userId AND is_active = 1")
    suspend fun getTotalSpentAmount(userId: String): Double?

    @Query("SELECT COUNT(*) FROM budgets WHERE user_id = :userId AND is_active = 1")
    suspend fun getActiveBudgetCount(userId: String): Int

    @Query("SELECT DISTINCT category FROM budgets WHERE user_id = :userId ORDER BY category")
    suspend fun getAllCategories(userId: String): List<String>

    // Search

    @Query("""
        SELECT * FROM budgets
        WHERE user_id = :userId
        AND (name LIKE '%' || :query || '%'
             OR category LIKE '%' || :query || '%'
             OR notes LIKE '%' || :query || '%')
        ORDER BY is_active DESC, created_at DESC
    """)
    fun searchBudgets(userId: String, query: String): Flow<List<BudgetEntity>>
}
