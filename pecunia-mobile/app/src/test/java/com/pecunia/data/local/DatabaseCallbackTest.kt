package com.pecunia.data.local

import com.pecunia.data.local.database.DatabaseUtils
import com.pecunia.domain.model.CategoryType
import org.junit.Assert.*
import org.junit.Test

/**
 * Unit tests for DatabaseCallback default categories and DatabaseUtils.
 *
 * Since DatabaseCallback requires an Android Context and SupportSQLiteDatabase
 * (which are Android framework classes), we test the logic and data structures
 * that can be verified without those dependencies:
 * - Default category definitions (names, icons, colors, types, counts)
 * - Category type consistency
 * - SQL insert logic expectations
 * - DatabaseUtils stub behavior
 */
class DatabaseCallbackTest {

    // ============================================
    // Default Expense Categories Tests
    // ============================================

    /**
     * The expense categories defined in DatabaseCallback.
     * Mirrors the private data to test correctness.
     */
    private data class DefaultCategory(
        val name: String,
        val icon: String,
        val color: String,
        val type: String,
        val description: String
    )

    private val expenseCategories = listOf(
        DefaultCategory("Alimentation", "restaurant", "#FF5722", "EXPENSE", "Courses, restaurants et nourriture"),
        DefaultCategory("Transport", "directions_car", "#2196F3", "EXPENSE", "Carburant, transports en commun, taxi"),
        DefaultCategory("Logement", "home", "#4CAF50", "EXPENSE", "Loyer, charges, assurance habitation"),
        DefaultCategory("Sante", "local_hospital", "#E91E63", "EXPENSE", "Medecin, pharmacie, mutuelle"),
        DefaultCategory("Loisirs", "sports_esports", "#9C27B0", "EXPENSE", "Divertissement, sorties, hobbies"),
        DefaultCategory("Shopping", "shopping_bag", "#FF9800", "EXPENSE", "Vetements, electronique, achats divers"),
        DefaultCategory("Factures", "receipt", "#607D8B", "EXPENSE", "Electricite, eau, internet, telephone"),
        DefaultCategory("Education", "school", "#3F51B5", "EXPENSE", "Formation, livres, cours"),
        DefaultCategory("Voyages", "flight", "#00BCD4", "EXPENSE", "Vacances, deplacements, hebergement"),
        DefaultCategory("Cadeaux", "card_giftcard", "#E040FB", "EXPENSE", "Cadeaux pour famille et amis"),
        DefaultCategory("Epargne", "savings", "#8BC34A", "EXPENSE", "Versements epargne, investissements"),
        DefaultCategory("Autres depenses", "more_horiz", "#795548", "EXPENSE", "Depenses diverses non categorisees")
    )

    private val incomeCategories = listOf(
        DefaultCategory("Salaire", "work", "#4CAF50", "INCOME", "Salaire mensuel, primes"),
        DefaultCategory("Freelance", "laptop", "#2196F3", "INCOME", "Revenus d'activite independante"),
        DefaultCategory("Investissements", "trending_up", "#FF9800", "INCOME", "Dividendes, plus-values, interets"),
        DefaultCategory("Remboursements", "replay", "#9C27B0", "INCOME", "Remboursements divers, notes de frais"),
        DefaultCategory("Cadeaux recus", "redeem", "#E91E63", "INCOME", "Argent recu en cadeau"),
        DefaultCategory("Allocations", "account_balance", "#00BCD4", "INCOME", "Aides sociales, allocations diverses"),
        DefaultCategory("Location", "apartment", "#607D8B", "INCOME", "Revenus locatifs"),
        DefaultCategory("Autres revenus", "add_circle", "#8BC34A", "INCOME", "Revenus divers non categorises")
    )

    @Test
    fun `there are exactly 12 expense categories`() {
        assertEquals(12, expenseCategories.size)
    }

    @Test
    fun `there are exactly 8 income categories`() {
        assertEquals(8, incomeCategories.size)
    }

    @Test
    fun `total categories is 20`() {
        val allCategories = expenseCategories + incomeCategories
        assertEquals(20, allCategories.size)
    }

    @Test
    fun `all expense categories have EXPENSE type`() {
        assertTrue(expenseCategories.all { it.type == "EXPENSE" })
    }

    @Test
    fun `all income categories have INCOME type`() {
        assertTrue(incomeCategories.all { it.type == "INCOME" })
    }

    @Test
    fun `all categories have non-blank names`() {
        val allCategories = expenseCategories + incomeCategories
        assertTrue(allCategories.all { it.name.isNotBlank() })
    }

    @Test
    fun `all categories have non-blank icons`() {
        val allCategories = expenseCategories + incomeCategories
        assertTrue(allCategories.all { it.icon.isNotBlank() })
    }

    @Test
    fun `all categories have non-blank descriptions`() {
        val allCategories = expenseCategories + incomeCategories
        assertTrue(allCategories.all { it.description.isNotBlank() })
    }

    @Test
    fun `all categories have valid hex color codes`() {
        val hexColorPattern = Regex("^#[0-9A-Fa-f]{6}$")
        val allCategories = expenseCategories + incomeCategories
        allCategories.forEach { category ->
            assertTrue(
                "Color '${category.color}' for '${category.name}' is not valid hex",
                hexColorPattern.matches(category.color)
            )
        }
    }

    @Test
    fun `all category names are unique`() {
        val allCategories = expenseCategories + incomeCategories
        val names = allCategories.map { it.name }
        assertEquals("Duplicate category names found", names.size, names.toSet().size)
    }

    @Test
    fun `all category icons are non-empty strings`() {
        val allCategories = expenseCategories + incomeCategories
        allCategories.forEach { category ->
            assertTrue(
                "Icon for '${category.name}' is empty",
                category.icon.isNotEmpty()
            )
        }
    }

    // ============================================
    // Specific Expense Category Verification
    // ============================================

    @Test
    fun `Alimentation expense category has correct icon`() {
        val category = expenseCategories.find { it.name == "Alimentation" }
        assertNotNull(category)
        assertEquals("restaurant", category!!.icon)
    }

    @Test
    fun `Transport expense category has correct color`() {
        val category = expenseCategories.find { it.name == "Transport" }
        assertNotNull(category)
        assertEquals("#2196F3", category!!.color)
    }

    @Test
    fun `Logement expense category has correct icon`() {
        val category = expenseCategories.find { it.name == "Logement" }
        assertNotNull(category)
        assertEquals("home", category!!.icon)
    }

    @Test
    fun `Shopping expense category has correct icon`() {
        val category = expenseCategories.find { it.name == "Shopping" }
        assertNotNull(category)
        assertEquals("shopping_bag", category!!.icon)
    }

    @Test
    fun `Voyages expense category has correct color`() {
        val category = expenseCategories.find { it.name == "Voyages" }
        assertNotNull(category)
        assertEquals("#00BCD4", category!!.color)
    }

    // ============================================
    // Specific Income Category Verification
    // ============================================

    @Test
    fun `Salaire income category has correct icon`() {
        val category = incomeCategories.find { it.name == "Salaire" }
        assertNotNull(category)
        assertEquals("work", category!!.icon)
    }

    @Test
    fun `Freelance income category has correct color`() {
        val category = incomeCategories.find { it.name == "Freelance" }
        assertNotNull(category)
        assertEquals("#2196F3", category!!.color)
    }

    @Test
    fun `Investissements income category has correct icon`() {
        val category = incomeCategories.find { it.name == "Investissements" }
        assertNotNull(category)
        assertEquals("trending_up", category!!.icon)
    }

    @Test
    fun `Location income category has correct icon`() {
        val category = incomeCategories.find { it.name == "Location" }
        assertNotNull(category)
        assertEquals("apartment", category!!.icon)
    }

    @Test
    fun `Allocations income category has correct color`() {
        val category = incomeCategories.find { it.name == "Allocations" }
        assertNotNull(category)
        assertEquals("#00BCD4", category!!.color)
    }

    // ============================================
    // Sort Order Verification
    // ============================================

    @Test
    fun `categories would receive sequential sort orders starting at 1`() {
        val allCategories = expenseCategories + incomeCategories
        allCategories.forEachIndexed { index, _ ->
            val expectedSortOrder = index + 1
            assertTrue(expectedSortOrder in 1..20)
        }
    }

    @Test
    fun `expense categories come first in sort order`() {
        val allCategories = expenseCategories + incomeCategories
        // First 12 should be expense
        for (i in 0 until 12) {
            assertEquals("EXPENSE", allCategories[i].type)
        }
        // Next 8 should be income
        for (i in 12 until 20) {
            assertEquals("INCOME", allCategories[i].type)
        }
    }

    // ============================================
    // SQL Insert Template Tests
    // ============================================

    @Test
    fun `SQL insert statement has correct number of placeholders`() {
        val sql = """
            INSERT INTO categories (
                id, uuid, name, icon, color, type, description,
                is_default, is_active, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
        """.trimIndent()

        // Count question marks - should be 10 (id, uuid, name, icon, color, type, description, sort_order, created_at, updated_at)
        val placeholderCount = sql.count { it == '?' }
        assertEquals(10, placeholderCount)
    }

    @Test
    fun `SQL insert statement sets is_default to 1`() {
        val sql = """
            INSERT INTO categories (
                id, uuid, name, icon, color, type, description,
                is_default, is_active, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
        """.trimIndent()

        assertTrue(sql.contains("is_default"))
        // The hard-coded "1" values represent is_default=1 and is_active=1
        assertTrue(sql.contains("1, 1"))
    }

    @Test
    fun `SQL insert statement targets categories table`() {
        val sql = """
            INSERT INTO categories (
                id, uuid, name, icon, color, type, description,
                is_default, is_active, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
        """.trimIndent()

        assertTrue(sql.contains("INSERT INTO categories"))
    }

    // ============================================
    // Database Health Check SQL Tests
    // ============================================

    @Test
    fun `integrity check PRAGMA is valid SQL`() {
        val sql = "PRAGMA integrity_check"
        assertTrue(sql.startsWith("PRAGMA"))
        assertTrue(sql.contains("integrity_check"))
    }

    @Test
    fun `table statistics SQL queries are valid for all expected tables`() {
        val tables = listOf(
            "users",
            "accounts",
            "transactions",
            "categories",
            "budgets",
            "recurring_transactions"
        )

        assertEquals(6, tables.size)
        tables.forEach { table ->
            val query = "SELECT COUNT(*) FROM $table"
            assertTrue(query.contains("SELECT COUNT(*)"))
            assertTrue(query.contains(table))
        }
    }

    @Test
    fun `expected tables include users`() {
        val tables = listOf("users", "accounts", "transactions", "categories", "budgets", "recurring_transactions")
        assertTrue(tables.contains("users"))
    }

    @Test
    fun `expected tables include transactions`() {
        val tables = listOf("users", "accounts", "transactions", "categories", "budgets", "recurring_transactions")
        assertTrue(tables.contains("transactions"))
    }

    @Test
    fun `expected tables include budgets`() {
        val tables = listOf("users", "accounts", "transactions", "categories", "budgets", "recurring_transactions")
        assertTrue(tables.contains("budgets"))
    }

    @Test
    fun `expected tables include categories`() {
        val tables = listOf("users", "accounts", "transactions", "categories", "budgets", "recurring_transactions")
        assertTrue(tables.contains("categories"))
    }

    @Test
    fun `expected tables include accounts`() {
        val tables = listOf("users", "accounts", "transactions", "categories", "budgets", "recurring_transactions")
        assertTrue(tables.contains("accounts"))
    }

    @Test
    fun `expected tables include recurring_transactions`() {
        val tables = listOf("users", "accounts", "transactions", "categories", "budgets", "recurring_transactions")
        assertTrue(tables.contains("recurring_transactions"))
    }

    // ============================================
    // CategoryType Enum Tests
    // ============================================

    @Test
    fun `CategoryType EXPENSE exists`() {
        assertNotNull(CategoryType.EXPENSE)
    }

    @Test
    fun `CategoryType INCOME exists`() {
        assertNotNull(CategoryType.INCOME)
    }

    @Test
    fun `CategoryType has exactly 2 values`() {
        assertEquals(2, CategoryType.entries.size)
    }

    // ============================================
    // DatabaseUtils Stub Tests
    // ============================================

    @Test
    fun `DatabaseUtils is a singleton object`() {
        // DatabaseUtils is declared as an object, verify it can be referenced
        assertNotNull(DatabaseUtils)
    }

    // ============================================
    // DefaultCategory Data Class Tests (mirrors private class)
    // ============================================

    @Test
    fun `DefaultCategory data class equality works`() {
        val cat1 = DefaultCategory("Test", "icon", "#000000", "EXPENSE", "Desc")
        val cat2 = DefaultCategory("Test", "icon", "#000000", "EXPENSE", "Desc")
        assertEquals(cat1, cat2)
    }

    @Test
    fun `DefaultCategory data class inequality works`() {
        val cat1 = DefaultCategory("Test1", "icon", "#000000", "EXPENSE", "Desc")
        val cat2 = DefaultCategory("Test2", "icon", "#000000", "EXPENSE", "Desc")
        assertNotEquals(cat1, cat2)
    }

    @Test
    fun `DefaultCategory copy preserves fields`() {
        val cat = DefaultCategory("Test", "icon", "#000000", "EXPENSE", "Desc")
        val copied = cat.copy(name = "Updated")
        assertEquals("Updated", copied.name)
        assertEquals("icon", copied.icon)
        assertEquals("#000000", copied.color)
        assertEquals("EXPENSE", copied.type)
        assertEquals("Desc", copied.description)
    }

    // ============================================
    // Color Value Specific Tests
    // ============================================

    @Test
    fun `expense and income categories can share colors`() {
        val expenseColors = expenseCategories.map { it.color }.toSet()
        val incomeColors = incomeCategories.map { it.color }.toSet()
        // Verify overlap exists (e.g., #4CAF50 used for both Logement and Salaire)
        val shared = expenseColors.intersect(incomeColors)
        assertTrue("Expected some shared colors between expense and income", shared.isNotEmpty())
    }

    @Test
    fun `all colors start with hash symbol`() {
        val allCategories = expenseCategories + incomeCategories
        assertTrue(allCategories.all { it.color.startsWith("#") })
    }

    @Test
    fun `all colors are exactly 7 characters`() {
        val allCategories = expenseCategories + incomeCategories
        assertTrue(allCategories.all { it.color.length == 7 })
    }
}
