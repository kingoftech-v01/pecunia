package com.pecunia.domain.models

import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate

/**
 * Represents a financial transaction.
 */
data class Transaction(
    val id: String,
    val userId: String,
    val amount: BigDecimal,
    val currency: String = "USD",
    val type: TransactionType,
    val category: TransactionCategory,
    val description: String,
    val merchant: String? = null,
    val date: LocalDate,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now(),
    val receiptImageUrl: String? = null,
    val tags: List<String> = emptyList(),
    val isRecurring: Boolean = false,
    val recurringDetails: RecurringDetails? = null,
    val syncStatus: SyncStatus = SyncStatus.SYNCED
)

/**
 * Type of transaction.
 */
enum class TransactionType {
    INCOME,
    EXPENSE,
    TRANSFER
}

/**
 * Category for transactions.
 */
enum class TransactionCategory(val displayName: String, val icon: String) {
    // Income categories
    SALARY("Salary", "work"),
    FREELANCE("Freelance", "computer"),
    INVESTMENT("Investment", "trending_up"),
    GIFT("Gift", "card_giftcard"),
    OTHER_INCOME("Other Income", "attach_money"),

    // Expense categories
    FOOD("Food & Dining", "restaurant"),
    GROCERIES("Groceries", "shopping_cart"),
    TRANSPORTATION("Transportation", "directions_car"),
    UTILITIES("Utilities", "power"),
    ENTERTAINMENT("Entertainment", "movie"),
    SHOPPING("Shopping", "shopping_bag"),
    HEALTHCARE("Healthcare", "local_hospital"),
    EDUCATION("Education", "school"),
    TRAVEL("Travel", "flight"),
    HOUSING("Housing", "home"),
    INSURANCE("Insurance", "security"),
    SUBSCRIPTIONS("Subscriptions", "subscriptions"),
    OTHER_EXPENSE("Other Expense", "receipt_long");

    companion object {
        fun incomeCategories(): List<TransactionCategory> = listOf(
            SALARY, FREELANCE, INVESTMENT, GIFT, OTHER_INCOME
        )

        fun expenseCategories(): List<TransactionCategory> = listOf(
            FOOD, GROCERIES, TRANSPORTATION, UTILITIES, ENTERTAINMENT,
            SHOPPING, HEALTHCARE, EDUCATION, TRAVEL, HOUSING,
            INSURANCE, SUBSCRIPTIONS, OTHER_EXPENSE
        )
    }
}

/**
 * Details for recurring transactions.
 */
data class RecurringDetails(
    val frequency: RecurringFrequency,
    val startDate: LocalDate,
    val endDate: LocalDate? = null,
    val nextOccurrence: LocalDate
)

/**
 * Frequency for recurring transactions.
 */
enum class RecurringFrequency {
    DAILY,
    WEEKLY,
    BIWEEKLY,
    MONTHLY,
    QUARTERLY,
    YEARLY
}

/**
 * Sync status for offline-first capability.
 */
enum class SyncStatus {
    SYNCED,
    PENDING_SYNC,
    SYNC_FAILED
}

/**
 * Summary of transactions for a period.
 */
data class TransactionSummary(
    val totalIncome: BigDecimal,
    val totalExpenses: BigDecimal,
    val netAmount: BigDecimal,
    val transactionCount: Int,
    val categoryBreakdown: Map<TransactionCategory, BigDecimal>
)
