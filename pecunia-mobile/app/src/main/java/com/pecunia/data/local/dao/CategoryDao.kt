package com.pecunia.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.pecunia.data.local.entity.CategoryEntity
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for Category operations.
 * Handles all database operations related to transaction categories.
 */
@Dao
interface CategoryDao {

    /**
     * Observes all categories for a specific user, including default categories.
     * @param userId The user's ID
     * @return Flow emitting list of categories ordered by name
     */
    @Query("""
        SELECT * FROM categories
        WHERE userId = :userId OR isDefault = 1
        ORDER BY isDefault DESC, name ASC
    """)
    fun getCategories(userId: String): Flow<List<CategoryEntity>>

    /**
     * Gets all categories synchronously.
     * @param userId The user's ID
     * @return List of categories
     */
    @Query("""
        SELECT * FROM categories
        WHERE userId = :userId OR isDefault = 1
        ORDER BY isDefault DESC, name ASC
    """)
    suspend fun getCategoriesSync(userId: String): List<CategoryEntity>

    /**
     * Observes categories filtered by type (income, expense, transfer).
     * @param userId The user's ID
     * @param type The category type
     * @return Flow emitting list of categories of the specified type
     */
    @Query("""
        SELECT * FROM categories
        WHERE (userId = :userId OR isDefault = 1)
        AND type = :type
        ORDER BY isDefault DESC, name ASC
    """)
    fun getCategoriesByType(userId: String, type: String): Flow<List<CategoryEntity>>

    /**
     * Gets categories by type synchronously.
     * @param userId The user's ID
     * @param type The category type
     * @return List of categories of the specified type
     */
    @Query("""
        SELECT * FROM categories
        WHERE (userId = :userId OR isDefault = 1)
        AND type = :type
        ORDER BY isDefault DESC, name ASC
    """)
    suspend fun getCategoriesByTypeSync(userId: String, type: String): List<CategoryEntity>

    /**
     * Observes all default/system categories.
     * Default categories are available to all users.
     * @return Flow emitting list of default categories
     */
    @Query("SELECT * FROM categories WHERE isDefault = 1 ORDER BY name ASC")
    fun getDefaultCategories(): Flow<List<CategoryEntity>>

    /**
     * Gets all default categories synchronously.
     * @return List of default categories
     */
    @Query("SELECT * FROM categories WHERE isDefault = 1 ORDER BY name ASC")
    suspend fun getDefaultCategoriesSync(): List<CategoryEntity>

    /**
     * Observes user-created custom categories (excluding defaults).
     * @param userId The user's ID
     * @return Flow emitting list of custom categories
     */
    @Query("""
        SELECT * FROM categories
        WHERE userId = :userId
        AND isDefault = 0
        ORDER BY name ASC
    """)
    fun getCustomCategories(userId: String): Flow<List<CategoryEntity>>

    /**
     * Gets a category by its ID.
     * @param id The category's unique ID
     * @return Flow emitting the category or null if not found
     */
    @Query("SELECT * FROM categories WHERE id = :id")
    fun getCategoryById(id: String): Flow<CategoryEntity?>

    /**
     * Gets a category by ID synchronously.
     * @param id The category's unique ID
     * @return The category entity or null if not found
     */
    @Query("SELECT * FROM categories WHERE id = :id")
    suspend fun getCategoryByIdSync(id: String): CategoryEntity?

    /**
     * Searches categories by name.
     * @param userId The user's ID
     * @param query The search query (partial match supported)
     * @return Flow emitting list of matching categories
     */
    @Query("""
        SELECT * FROM categories
        WHERE (userId = :userId OR isDefault = 1)
        AND name LIKE '%' || :query || '%'
        ORDER BY isDefault DESC, name ASC
    """)
    fun searchCategories(userId: String, query: String): Flow<List<CategoryEntity>>

    /**
     * Gets a category by name for a user.
     * @param userId The user's ID
     * @param name The category name
     * @return The category or null if not found
     */
    @Query("""
        SELECT * FROM categories
        WHERE (userId = :userId OR isDefault = 1)
        AND name = :name
        LIMIT 1
    """)
    suspend fun getCategoryByName(userId: String, name: String): CategoryEntity?

    /**
     * Gets categories with a parent category (subcategories).
     * @param userId The user's ID
     * @param parentId The parent category's ID
     * @return Flow emitting list of subcategories
     */
    @Query("""
        SELECT * FROM categories
        WHERE (userId = :userId OR isDefault = 1)
        AND parentId = :parentId
        ORDER BY name ASC
    """)
    fun getSubcategories(userId: String, parentId: String): Flow<List<CategoryEntity>>

    /**
     * Gets top-level categories (no parent).
     * @param userId The user's ID
     * @return Flow emitting list of top-level categories
     */
    @Query("""
        SELECT * FROM categories
        WHERE (userId = :userId OR isDefault = 1)
        AND parentId IS NULL
        ORDER BY isDefault DESC, name ASC
    """)
    fun getTopLevelCategories(userId: String): Flow<List<CategoryEntity>>

    /**
     * Inserts a new category into the database.
     * @param category The category entity to insert
     * @return The row ID of the inserted category
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(category: CategoryEntity): Long

    /**
     * Inserts multiple categories into the database.
     * @param categories List of category entities to insert
     * @return List of row IDs for inserted categories
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(categories: List<CategoryEntity>): List<Long>

    /**
     * Updates an existing category in the database.
     * @param category The category entity with updated values
     * @return The number of rows updated
     */
    @Update
    suspend fun update(category: CategoryEntity): Int

    /**
     * Deletes a category from the database.
     * @param category The category entity to delete
     * @return The number of rows deleted
     */
    @Delete
    suspend fun delete(category: CategoryEntity): Int

    /**
     * Deletes a category by its ID.
     * Note: This should not delete default categories.
     * @param id The category's ID to delete
     * @return The number of rows deleted
     */
    @Query("DELETE FROM categories WHERE id = :id AND isDefault = 0")
    suspend fun deleteById(id: String): Int

    /**
     * Deletes all custom categories for a user.
     * Default categories are preserved.
     * @param userId The user's ID
     */
    @Query("DELETE FROM categories WHERE userId = :userId AND isDefault = 0")
    suspend fun deleteCustomCategoriesForUser(userId: String)

    /**
     * Checks if a category with the given name exists for a user.
     * @param userId The user's ID
     * @param name The category name to check
     * @return True if the category exists, false otherwise
     */
    @Query("""
        SELECT EXISTS(
            SELECT 1 FROM categories
            WHERE (userId = :userId OR isDefault = 1)
            AND name = :name
            LIMIT 1
        )
    """)
    suspend fun categoryExists(userId: String, name: String): Boolean

    /**
     * Gets the count of transactions using a specific category.
     * Useful for determining if a category can be safely deleted.
     * @param categoryId The category's ID
     * @return The number of transactions using this category
     */
    @Query("SELECT COUNT(*) FROM transactions WHERE categoryId = :categoryId")
    suspend fun getTransactionCountForCategory(categoryId: String): Int

    /**
     * Updates the icon for a category.
     * @param categoryId The category's ID
     * @param icon The new icon identifier
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE categories SET icon = :icon, updatedAt = :updatedAt WHERE id = :categoryId")
    suspend fun updateIcon(categoryId: String, icon: String, updatedAt: Long)

    /**
     * Updates the color for a category.
     * @param categoryId The category's ID
     * @param color The new color value
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE categories SET color = :color, updatedAt = :updatedAt WHERE id = :categoryId")
    suspend fun updateColor(categoryId: String, color: String, updatedAt: Long)

    /**
     * Gets categories ordered by usage frequency.
     * @param userId The user's ID
     * @param limit Maximum number of categories to return
     * @return List of most used categories
     */
    @Query("""
        SELECT c.* FROM categories c
        LEFT JOIN (
            SELECT categoryId, COUNT(*) as count
            FROM transactions
            WHERE userId = :userId
            GROUP BY categoryId
        ) t ON c.id = t.categoryId
        WHERE c.userId = :userId OR c.isDefault = 1
        ORDER BY t.count DESC NULLS LAST
        LIMIT :limit
    """)
    suspend fun getMostUsedCategories(userId: String, limit: Int): List<CategoryEntity>

    /**
     * Gets categories that haven't been used recently.
     * @param userId The user's ID
     * @param sinceDate Timestamp threshold
     * @return List of unused categories
     */
    @Query("""
        SELECT c.* FROM categories c
        WHERE (c.userId = :userId OR c.isDefault = 1)
        AND c.id NOT IN (
            SELECT DISTINCT categoryId FROM transactions
            WHERE userId = :userId
            AND date >= :sinceDate
            AND categoryId IS NOT NULL
        )
        ORDER BY c.name ASC
    """)
    suspend fun getUnusedCategories(userId: String, sinceDate: Long): List<CategoryEntity>
}
