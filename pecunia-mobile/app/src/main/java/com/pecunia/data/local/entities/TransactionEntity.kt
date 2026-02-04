package com.pecunia.data.local.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal
import java.util.UUID

/**
 * Entity representing a financial transaction in the local Room database.
 * Supports both manual entries and bank-synced transactions with AI categorization.
 */
@Entity(
    tableName = "transactions",
    indices = [
        Index(value = ["user_id"]),
        Index(value = ["bank_account_id"]),
        Index(value = ["category_id"]),
        Index(value = ["transaction_date"]),
        Index(value = ["type"]),
        Index(value = ["sync_status"]),
        Index(value = ["user_id", "transaction_date"]),
        Index(value = ["user_id", "category_id"]),
        Index(value = ["is_recurring"])
    ],
    foreignKeys = [
        ForeignKey(
            entity = UserEntity::class,
            parentColumns = ["id"],
            childColumns = ["user_id"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = BankAccountEntity::class,
            parentColumns = ["id"],
            childColumns = ["bank_account_id"],
            onDelete = ForeignKey.SET_NULL,
            onUpdate = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = CategoryEntity::class,
            parentColumns = ["id"],
            childColumns = ["category_id"],
            onDelete = ForeignKey.SET_NULL,
            onUpdate = ForeignKey.CASCADE
        )
    ]
)
data class TransactionEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "user_id")
    val userId: UUID,

    @ColumnInfo(name = "bank_account_id")
    val bankAccountId: UUID? = null,

    @ColumnInfo(name = "category_id")
    val categoryId: UUID? = null,

    @ColumnInfo(name = "amount")
    val amount: BigDecimal,

    @ColumnInfo(name = "type")
    val type: TransactionType,

    @ColumnInfo(name = "description")
    val description: String,

    @ColumnInfo(name = "merchant")
    val merchant: String? = null,

    @ColumnInfo(name = "transaction_date")
    val transactionDate: Long,

    @ColumnInfo(name = "is_recurring")
    val isRecurring: Boolean = false,

    @ColumnInfo(name = "is_manual")
    val isManual: Boolean = true,

    @ColumnInfo(name = "ai_category_suggestion")
    val aiCategorySuggestion: UUID? = null,

    @ColumnInfo(name = "ai_confidence")
    val aiConfidence: Float? = null,

    @ColumnInfo(name = "tags")
    val tags: String? = null, // JSON array stored as string

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "sync_status")
    val syncStatus: SyncStatus = SyncStatus.PENDING
) {
    /**
     * Enum representing the type of transaction.
     */
    enum class TransactionType {
        INCOME,
        EXPENSE,
        TRANSFER
    }

    /**
     * Enum representing the synchronization status of the transaction.
     */
    enum class SyncStatus {
        PENDING,
        SYNCED,
        FAILED,
        CONFLICT
    }

    /**
     * Checks if the transaction has a high confidence AI suggestion.
     */
    fun hasHighConfidenceSuggestion(): Boolean =
        aiConfidence != null && aiConfidence >= 0.8f

    /**
     * Checks if this is an expense transaction.
     */
    fun isExpense(): Boolean = type == TransactionType.EXPENSE

    /**
     * Checks if this is an income transaction.
     */
    fun isIncome(): Boolean = type == TransactionType.INCOME

    /**
     * Returns the signed amount (negative for expenses).
     */
    fun getSignedAmount(): BigDecimal =
        if (type == TransactionType.EXPENSE) amount.negate() else amount

    /**
     * Checks if the transaction needs synchronization.
     */
    fun needsSync(): Boolean =
        syncStatus == SyncStatus.PENDING || syncStatus == SyncStatus.FAILED

    companion object {
        /**
         * Creates a copy of the entity with updated timestamp and sync status.
         */
        fun TransactionEntity.markAsModified(): TransactionEntity =
            copy(
                updatedAt = System.currentTimeMillis(),
                syncStatus = SyncStatus.PENDING
            )

        /**
         * Creates a copy of the entity marked as synced.
         */
        fun TransactionEntity.markAsSynced(): TransactionEntity =
            copy(syncStatus = SyncStatus.SYNCED)
    }
}
