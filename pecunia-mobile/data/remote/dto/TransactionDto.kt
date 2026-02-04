package com.pecunia.data.remote.dto

import com.pecunia.data.local.database.entities.TransactionEntity
import com.pecunia.data.local.database.entities.TransactionType
import com.google.gson.annotations.JsonAdapter
import com.google.gson.annotations.SerializedName
import java.math.BigDecimal

/**
 * Data Transfer Object for Transaction from API.
 */
data class TransactionDto(
    @SerializedName("id")
    val id: String,

    @SerializedName("user_id")
    val userId: String,

    @SerializedName("amount")
    val amount: BigDecimal,

    @SerializedName("currency")
    val currency: String,

    @SerializedName("type")
    val type: String,

    @SerializedName("category")
    val category: String,

    @SerializedName("description")
    val description: String?,

    @SerializedName("merchant_name")
    val merchantName: String?,

    @SerializedName("date")
    val date: Long,

    @SerializedName("created_at")
    val createdAt: Long,

    @SerializedName("updated_at")
    val updatedAt: Long,

    @SerializedName("account_id")
    val accountId: String?,

    @SerializedName("is_recurring")
    val isRecurring: Boolean,

    @SerializedName("recurring_id")
    val recurringId: String?,

    @SerializedName("notes")
    val notes: String?,

    @SerializedName("tags")
    val tags: List<String>?
) {
    /**
     * Convert DTO to Entity for local storage.
     */
    fun toEntity(): TransactionEntity {
        return TransactionEntity(
            id = id,
            userId = userId,
            amount = amount.toDouble(),
            currency = currency,
            type = TransactionType.valueOf(type.uppercase()),
            category = category,
            description = description,
            merchantName = merchantName,
            date = date,
            createdAt = createdAt,
            updatedAt = updatedAt,
            isSynced = true,
            accountId = accountId,
            isRecurring = isRecurring,
            recurringId = recurringId,
            notes = notes,
            tags = tags?.joinToString(",")
        )
    }
}

/**
 * Request DTO for creating/updating a transaction.
 */
data class TransactionRequest(
    @SerializedName("amount")
    val amount: BigDecimal,

    @SerializedName("currency")
    val currency: String = "USD",

    @SerializedName("type")
    val type: String,

    @SerializedName("category")
    val category: String,

    @SerializedName("description")
    val description: String?,

    @SerializedName("merchant_name")
    val merchantName: String?,

    @SerializedName("date")
    val date: Long,

    @SerializedName("account_id")
    val accountId: String?,

    @SerializedName("is_recurring")
    val isRecurring: Boolean = false,

    @SerializedName("recurring_id")
    val recurringId: String? = null,

    @SerializedName("notes")
    val notes: String? = null,

    @SerializedName("tags")
    val tags: List<String>? = null
) {
    companion object {
        /**
         * Create a request from an entity.
         */
        fun fromEntity(entity: TransactionEntity): TransactionRequest {
            return TransactionRequest(
                amount = BigDecimal.valueOf(entity.amount),
                currency = entity.currency,
                type = entity.type.name,
                category = entity.category,
                description = entity.description,
                merchantName = entity.merchantName,
                date = entity.date,
                accountId = entity.accountId,
                isRecurring = entity.isRecurring,
                recurringId = entity.recurringId,
                notes = entity.notes,
                tags = entity.tags?.split(",")?.map { it.trim() }?.filter { it.isNotEmpty() }
            )
        }
    }
}

/**
 * Response wrapper for paginated transaction list.
 */
data class TransactionListResponse(
    @SerializedName("data")
    val data: List<TransactionDto>,

    @SerializedName("total")
    val total: Int,

    @SerializedName("page")
    val page: Int,

    @SerializedName("page_size")
    val pageSize: Int,

    @SerializedName("has_more")
    val hasMore: Boolean
)

/**
 * Response wrapper for single transaction.
 */
data class TransactionResponse(
    @SerializedName("data")
    val data: TransactionDto,

    @SerializedName("message")
    val message: String?
)

/**
 * Response for transaction summary/analytics.
 */
data class TransactionSummaryResponse(
    @SerializedName("total_income")
    val totalIncome: BigDecimal,

    @SerializedName("total_expense")
    val totalExpense: BigDecimal,

    @SerializedName("net_balance")
    val netBalance: BigDecimal,

    @SerializedName("category_breakdown")
    val categoryBreakdown: List<CategoryBreakdown>,

    @SerializedName("period_start")
    val periodStart: Long,

    @SerializedName("period_end")
    val periodEnd: Long
)

/**
 * Category breakdown for analytics.
 */
data class CategoryBreakdown(
    @SerializedName("category")
    val category: String,

    @SerializedName("amount")
    val amount: BigDecimal,

    @SerializedName("percentage")
    val percentage: BigDecimal,

    @SerializedName("transaction_count")
    val transactionCount: Int
)
