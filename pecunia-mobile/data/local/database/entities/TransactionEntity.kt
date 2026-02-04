package com.pecunia.data.local.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room entity representing a financial transaction.
 */
@Entity(
    tableName = "transactions",
    indices = [
        Index(value = ["user_id"]),
        Index(value = ["category"]),
        Index(value = ["date"]),
        Index(value = ["type"])
    ]
)
data class TransactionEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: String,

    @ColumnInfo(name = "user_id")
    val userId: String,

    @ColumnInfo(name = "amount")
    val amount: Double,

    @ColumnInfo(name = "currency")
    val currency: String = "USD",

    @ColumnInfo(name = "type")
    val type: TransactionType,

    @ColumnInfo(name = "category")
    val category: String,

    @ColumnInfo(name = "description")
    val description: String?,

    @ColumnInfo(name = "merchant_name")
    val merchantName: String?,

    @ColumnInfo(name = "date")
    val date: Long,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false,

    @ColumnInfo(name = "account_id")
    val accountId: String?,

    @ColumnInfo(name = "is_recurring")
    val isRecurring: Boolean = false,

    @ColumnInfo(name = "recurring_id")
    val recurringId: String? = null,

    @ColumnInfo(name = "notes")
    val notes: String? = null,

    @ColumnInfo(name = "tags")
    val tags: String? = null // Stored as comma-separated values
)

/**
 * Enum representing transaction types.
 */
enum class TransactionType {
    INCOME,
    EXPENSE,
    TRANSFER
}
