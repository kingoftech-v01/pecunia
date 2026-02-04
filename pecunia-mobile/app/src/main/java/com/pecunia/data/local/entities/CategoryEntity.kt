package com.pecunia.data.local.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

/**
 * Entity representing a transaction category in the local Room database.
 * Supports both default system categories and user-created custom categories.
 */
@Entity(
    tableName = "categories",
    indices = [
        Index(value = ["user_id"]),
        Index(value = ["type"]),
        Index(value = ["is_default"]),
        Index(value = ["name"]),
        Index(value = ["user_id", "type"]),
        Index(value = ["user_id", "name"], unique = true)
    ],
    foreignKeys = [
        ForeignKey(
            entity = UserEntity::class,
            parentColumns = ["id"],
            childColumns = ["user_id"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE
        )
    ]
)
data class CategoryEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "user_id")
    val userId: UUID? = null, // Null for system default categories

    @ColumnInfo(name = "name")
    val name: String,

    @ColumnInfo(name = "type")
    val type: CategoryType,

    @ColumnInfo(name = "icon")
    val icon: String, // Material icon name or emoji

    @ColumnInfo(name = "color")
    val color: String, // Hex color code (e.g., "#FF5722")

    @ColumnInfo(name = "is_default")
    val isDefault: Boolean = false,

    @ColumnInfo(name = "parent_category_id")
    val parentCategoryId: UUID? = null, // For subcategories

    @ColumnInfo(name = "sort_order")
    val sortOrder: Int = 0,

    @ColumnInfo(name = "is_archived")
    val isArchived: Boolean = false,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "sync_status")
    val syncStatus: SyncStatus = SyncStatus.PENDING
) {
    /**
     * Enum representing the type of category.
     */
    enum class CategoryType {
        INCOME,
        EXPENSE,
        TRANSFER,
        SAVINGS,
        INVESTMENT
    }

    /**
     * Enum representing the synchronization status of the category.
     */
    enum class SyncStatus {
        PENDING,
        SYNCED,
        FAILED,
        CONFLICT
    }

    /**
     * Checks if this is a system default category.
     */
    fun isSystemCategory(): Boolean = isDefault && userId == null

    /**
     * Checks if this is a user-created category.
     */
    fun isUserCategory(): Boolean = !isDefault && userId != null

    /**
     * Checks if this category has a parent (is a subcategory).
     */
    fun isSubcategory(): Boolean = parentCategoryId != null

    /**
     * Checks if this is an expense category.
     */
    fun isExpenseCategory(): Boolean = type == CategoryType.EXPENSE

    /**
     * Checks if this is an income category.
     */
    fun isIncomeCategory(): Boolean = type == CategoryType.INCOME

    /**
     * Validates the color format (hex).
     */
    fun isValidColor(): Boolean =
        color.matches(Regex("^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$"))

    companion object {
        /**
         * Creates a copy of the entity with updated timestamp.
         */
        fun CategoryEntity.withUpdatedTimestamp(): CategoryEntity =
            copy(
                updatedAt = System.currentTimeMillis(),
                syncStatus = SyncStatus.PENDING
            )

        /**
         * Creates a copy of the entity marked as synced.
         */
        fun CategoryEntity.markAsSynced(): CategoryEntity =
            copy(syncStatus = SyncStatus.SYNCED)

        /**
         * Creates an archived copy of the category.
         */
        fun CategoryEntity.archive(): CategoryEntity =
            copy(
                isArchived = true,
                updatedAt = System.currentTimeMillis(),
                syncStatus = SyncStatus.PENDING
            )

        /**
         * Default expense categories for new users.
         */
        val DEFAULT_EXPENSE_CATEGORIES = listOf(
            "Food & Dining" to "#FF5722",
            "Transportation" to "#2196F3",
            "Shopping" to "#E91E63",
            "Entertainment" to "#9C27B0",
            "Bills & Utilities" to "#607D8B",
            "Healthcare" to "#4CAF50",
            "Education" to "#FF9800",
            "Travel" to "#00BCD4",
            "Personal Care" to "#795548",
            "Other" to "#9E9E9E"
        )

        /**
         * Default income categories for new users.
         */
        val DEFAULT_INCOME_CATEGORIES = listOf(
            "Salary" to "#4CAF50",
            "Freelance" to "#8BC34A",
            "Investments" to "#009688",
            "Gifts" to "#E91E63",
            "Refunds" to "#03A9F4",
            "Other Income" to "#9E9E9E"
        )
    }
}
