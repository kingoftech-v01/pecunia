package com.pecunia.domain.models

import java.time.Instant

/**
 * Represents the type of category (for income or expense transactions).
 */
enum class CategoryType {
    INCOME,
    EXPENSE;

    companion object {
        fun fromString(value: String): CategoryType {
            return entries.find { it.name.equals(value, ignoreCase = true) }
                ?: throw IllegalArgumentException("Unknown category type: $value")
        }
    }
}

/**
 * Represents a transaction category in the application.
 */
data class Category(
    val id: String,
    val userId: String? = null, // null for system default categories
    val name: String,
    val type: CategoryType,
    val icon: String? = null,
    val color: String? = null, // Hex color code (e.g., "#FF5733")
    val parentId: String? = null, // For subcategories
    val isDefault: Boolean = false,
    val isActive: Boolean = true,
    val sortOrder: Int = 0,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
) {
    /**
     * Returns true if this is a user-created category.
     */
    val isCustom: Boolean
        get() = userId != null

    /**
     * Returns true if this is a subcategory.
     */
    val isSubcategory: Boolean
        get() = parentId != null

    /**
     * Returns true if this is an income category.
     */
    val isIncomeCategory: Boolean
        get() = type == CategoryType.INCOME

    /**
     * Returns true if this is an expense category.
     */
    val isExpenseCategory: Boolean
        get() = type == CategoryType.EXPENSE

    companion object {
        /**
         * Creates an empty Category instance for initialization purposes.
         */
        fun empty(): Category = Category(
            id = "",
            name = "",
            type = CategoryType.EXPENSE
        )

        /**
         * Default expense categories.
         */
        val defaultExpenseCategories = listOf(
            "Food & Dining",
            "Transportation",
            "Shopping",
            "Entertainment",
            "Bills & Utilities",
            "Health & Fitness",
            "Travel",
            "Education",
            "Personal Care",
            "Other"
        )

        /**
         * Default income categories.
         */
        val defaultIncomeCategories = listOf(
            "Salary",
            "Freelance",
            "Investments",
            "Gifts",
            "Refunds",
            "Other Income"
        )
    }
}
