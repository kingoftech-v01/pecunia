package com.pecunia.domain.models

import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate

/**
 * Represents the type of financial transaction.
 */
enum class TransactionType {
    INCOME,
    EXPENSE,
    TRANSFER;

    companion object {
        fun fromString(value: String): TransactionType {
            return entries.find { it.name.equals(value, ignoreCase = true) }
                ?: throw IllegalArgumentException("Unknown transaction type: $value")
        }
    }
}

/**
 * Represents the status of a transaction.
 */
enum class TransactionStatus {
    PENDING,
    COMPLETED,
    CANCELLED,
    FAILED
}

/**
 * Represents a financial transaction in the application.
 */
data class Transaction(
    val id: String,
    val userId: String,
    val type: TransactionType,
    val amount: BigDecimal,
    val currency: String = "USD",
    val description: String,
    val categoryId: String? = null,
    val category: Category? = null,
    val accountId: String,
    val toAccountId: String? = null, // For transfer transactions
    val date: LocalDate,
    val status: TransactionStatus = TransactionStatus.COMPLETED,
    val notes: String? = null,
    val tags: List<String> = emptyList(),
    val isRecurring: Boolean = false,
    val recurringId: String? = null,
    val attachmentUrls: List<String> = emptyList(),
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
) {
    /**
     * Returns the absolute amount value.
     */
    val absoluteAmount: BigDecimal
        get() = amount.abs()

    /**
     * Returns true if this is an income transaction.
     */
    val isIncome: Boolean
        get() = type == TransactionType.INCOME

    /**
     * Returns true if this is an expense transaction.
     */
    val isExpense: Boolean
        get() = type == TransactionType.EXPENSE

    /**
     * Returns true if this is a transfer transaction.
     */
    val isTransfer: Boolean
        get() = type == TransactionType.TRANSFER

    /**
     * Returns the signed amount (negative for expenses, positive for income).
     */
    val signedAmount: BigDecimal
        get() = when (type) {
            TransactionType.EXPENSE -> amount.negate()
            TransactionType.INCOME -> amount
            TransactionType.TRANSFER -> BigDecimal.ZERO
        }

    companion object {
        /**
         * Creates an empty Transaction instance for initialization purposes.
         */
        fun empty(): Transaction = Transaction(
            id = "",
            userId = "",
            type = TransactionType.EXPENSE,
            amount = BigDecimal.ZERO,
            description = "",
            accountId = "",
            date = LocalDate.now()
        )
    }
}
