package com.pecunia.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Embedded
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Relation
import androidx.room.Transaction
import androidx.room.Update
import com.pecunia.data.local.entity.BudgetEntity
import com.pecunia.data.local.entity.BudgetItemEntity
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for Budget operations.
 * Handles all database operations related to budgets and budget items.
 */
@Dao
interface BudgetDao {

    /**
     * Observes all budgets for a specific user.
     * @param userId The user's ID
     * @return Flow emitting list of budgets
     */
    @Query("SELECT * FROM budgets WHERE userId = :userId ORDER BY createdAt DESC")
    fun getBudgets(userId: String): Flow<List<BudgetEntity>>

    /**
     * Observes all active budgets for a user.
     * Active budgets are those where the current date falls within their period.
     * @param userId The user's ID
     * @param currentDate The current timestamp to check against
     * @return Flow emitting list of active budgets
     */
    @Query("""
        SELECT * FROM budgets
        WHERE userId = :userId
        AND isActive = 1
        AND startDate <= :currentDate
        AND endDate >= :currentDate
        ORDER BY name ASC
    """)
    fun getActiveBudgets(userId: String, currentDate: Long): Flow<List<BudgetEntity>>

    /**
     * Gets all active budgets synchronously.
     * @param userId The user's ID
     * @param currentDate The current timestamp
     * @return List of active budgets
     */
    @Query("""
        SELECT * FROM budgets
        WHERE userId = :userId
        AND isActive = 1
        AND startDate <= :currentDate
        AND endDate >= :currentDate
    """)
    suspend fun getActiveBudgetsSync(userId: String, currentDate: Long): List<BudgetEntity>

    /**
     * Observes a single budget by its ID.
     * @param id The budget's unique ID
     * @return Flow emitting the budget or null if not found
     */
    @Query("SELECT * FROM budgets WHERE id = :id")
    fun getBudgetById(id: String): Flow<BudgetEntity?>

    /**
     * Gets a budget synchronously by its ID.
     * @param id The budget's unique ID
     * @return The budget entity or null if not found
     */
    @Query("SELECT * FROM budgets WHERE id = :id")
    suspend fun getBudgetByIdSync(id: String): BudgetEntity?

    /**
     * Observes a budget with all its associated items.
     * @param budgetId The budget's unique ID
     * @return Flow emitting the budget with items
     */
    @Transaction
    @Query("SELECT * FROM budgets WHERE id = :budgetId")
    fun getBudgetWithItems(budgetId: String): Flow<BudgetWithItems?>

    /**
     * Gets a budget with items synchronously.
     * @param budgetId The budget's unique ID
     * @return The budget with items or null if not found
     */
    @Transaction
    @Query("SELECT * FROM budgets WHERE id = :budgetId")
    suspend fun getBudgetWithItemsSync(budgetId: String): BudgetWithItems?

    /**
     * Observes all budgets with their items for a user.
     * @param userId The user's ID
     * @return Flow emitting list of budgets with items
     */
    @Transaction
    @Query("SELECT * FROM budgets WHERE userId = :userId ORDER BY createdAt DESC")
    fun getBudgetsWithItems(userId: String): Flow<List<BudgetWithItems>>

    /**
     * Gets budgets by period type (weekly, monthly, yearly).
     * @param userId The user's ID
     * @param periodType The budget period type
     * @return Flow emitting list of budgets with the specified period
     */
    @Query("""
        SELECT * FROM budgets
        WHERE userId = :userId
        AND periodType = :periodType
        ORDER BY createdAt DESC
    """)
    fun getBudgetsByPeriodType(userId: String, periodType: String): Flow<List<BudgetEntity>>

    /**
     * Inserts a new budget into the database.
     * @param budget The budget entity to insert
     * @return The row ID of the inserted budget
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(budget: BudgetEntity): Long

    /**
     * Inserts multiple budgets into the database.
     * @param budgets List of budget entities to insert
     * @return List of row IDs for inserted budgets
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(budgets: List<BudgetEntity>): List<Long>

    /**
     * Updates an existing budget in the database.
     * @param budget The budget entity with updated values
     * @return The number of rows updated
     */
    @Update
    suspend fun update(budget: BudgetEntity): Int

    /**
     * Deletes a budget from the database.
     * @param budget The budget entity to delete
     * @return The number of rows deleted
     */
    @Delete
    suspend fun delete(budget: BudgetEntity): Int

    /**
     * Deletes a budget by its ID.
     * @param id The budget's ID to delete
     * @return The number of rows deleted
     */
    @Query("DELETE FROM budgets WHERE id = :id")
    suspend fun deleteById(id: String): Int

    /**
     * Deletes all budgets for a specific user.
     * @param userId The user's ID
     */
    @Query("DELETE FROM budgets WHERE userId = :userId")
    suspend fun deleteAllForUser(userId: String)

    /**
     * Updates the spent amount for a budget.
     * @param budgetId The budget's ID
     * @param spentAmount The new spent amount
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE budgets SET spentAmount = :spentAmount, updatedAt = :updatedAt WHERE id = :budgetId")
    suspend fun updateSpentAmount(budgetId: String, spentAmount: Double, updatedAt: Long)

    /**
     * Toggles the active status of a budget.
     * @param budgetId The budget's ID
     * @param isActive The new active status
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE budgets SET isActive = :isActive, updatedAt = :updatedAt WHERE id = :budgetId")
    suspend fun setActiveStatus(budgetId: String, isActive: Boolean, updatedAt: Long)

    /**
     * Gets budgets that need recalculation (based on last update).
     * @param userId The user's ID
     * @param lastCalculatedBefore Timestamp threshold
     * @return List of budgets needing recalculation
     */
    @Query("""
        SELECT * FROM budgets
        WHERE userId = :userId
        AND isActive = 1
        AND lastCalculatedAt < :lastCalculatedBefore
    """)
    suspend fun getBudgetsNeedingRecalculation(
        userId: String,
        lastCalculatedBefore: Long
    ): List<BudgetEntity>

    /**
     * Updates the last calculated timestamp for a budget.
     * @param budgetId The budget's ID
     * @param lastCalculatedAt The new calculation timestamp
     */
    @Query("UPDATE budgets SET lastCalculatedAt = :lastCalculatedAt WHERE id = :budgetId")
    suspend fun updateLastCalculatedAt(budgetId: String, lastCalculatedAt: Long)

    // Budget Item Operations

    /**
     * Gets all items for a specific budget.
     * @param budgetId The budget's ID
     * @return Flow emitting list of budget items
     */
    @Query("SELECT * FROM budget_items WHERE budgetId = :budgetId ORDER BY createdAt ASC")
    fun getBudgetItems(budgetId: String): Flow<List<BudgetItemEntity>>

    /**
     * Gets a budget item by its ID.
     * @param itemId The item's ID
     * @return The budget item or null if not found
     */
    @Query("SELECT * FROM budget_items WHERE id = :itemId")
    suspend fun getBudgetItemById(itemId: String): BudgetItemEntity?

    /**
     * Inserts a new budget item.
     * @param item The budget item entity to insert
     * @return The row ID of the inserted item
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBudgetItem(item: BudgetItemEntity): Long

    /**
     * Inserts multiple budget items.
     * @param items List of budget item entities to insert
     * @return List of row IDs for inserted items
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBudgetItems(items: List<BudgetItemEntity>): List<Long>

    /**
     * Updates a budget item.
     * @param item The budget item entity with updated values
     * @return The number of rows updated
     */
    @Update
    suspend fun updateBudgetItem(item: BudgetItemEntity): Int

    /**
     * Deletes a budget item.
     * @param item The budget item entity to delete
     * @return The number of rows deleted
     */
    @Delete
    suspend fun deleteBudgetItem(item: BudgetItemEntity): Int

    /**
     * Deletes all items for a specific budget.
     * @param budgetId The budget's ID
     */
    @Query("DELETE FROM budget_items WHERE budgetId = :budgetId")
    suspend fun deleteBudgetItems(budgetId: String)

    /**
     * Updates the spent amount for a budget item.
     * @param itemId The item's ID
     * @param spentAmount The new spent amount
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE budget_items SET spentAmount = :spentAmount, updatedAt = :updatedAt WHERE id = :itemId")
    suspend fun updateBudgetItemSpentAmount(itemId: String, spentAmount: Double, updatedAt: Long)

    /**
     * Inserts a budget with its items in a single transaction.
     * @param budget The budget entity
     * @param items The list of budget items
     */
    @Transaction
    suspend fun insertBudgetWithItems(budget: BudgetEntity, items: List<BudgetItemEntity>) {
        insert(budget)
        insertBudgetItems(items)
    }

    /**
     * Deletes a budget and all its items in a single transaction.
     * @param budgetId The budget's ID
     */
    @Transaction
    suspend fun deleteBudgetWithItems(budgetId: String) {
        deleteBudgetItems(budgetId)
        deleteById(budgetId)
    }
}

/**
 * Data class representing a budget with its associated items.
 */
data class BudgetWithItems(
    @Embedded val budget: BudgetEntity,
    @Relation(
        parentColumn = "id",
        entityColumn = "budgetId"
    )
    val items: List<BudgetItemEntity>
)
