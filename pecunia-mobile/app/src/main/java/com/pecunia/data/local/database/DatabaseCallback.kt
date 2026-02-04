package com.pecunia.data.local.database

import android.content.Context
import android.util.Log
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import com.pecunia.data.local.dao.CategoryDao
import com.pecunia.data.local.entity.CategoryEntity
import com.pecunia.domain.model.CategoryType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.Date
import java.util.UUID

/**
 * Room database callback for handling database lifecycle events.
 *
 * This callback is responsible for:
 * - Prepopulating default categories when the database is first created
 * - Performing any necessary operations when the database is opened
 * - Logging database events for debugging purposes
 *
 * @param context Application context for accessing resources if needed
 */
class DatabaseCallback(
    private val context: Context
) : RoomDatabase.Callback() {

    companion object {
        private const val TAG = "DatabaseCallback"
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /**
     * Called when the database is created for the first time.
     * This is the ideal place to prepopulate default data.
     *
     * @param db The database instance
     */
    override fun onCreate(db: SupportSQLiteDatabase) {
        super.onCreate(db)
        Log.d(TAG, "Database created for the first time")

        // Prepopulate default categories using raw SQL
        // This is more reliable than using DAOs during callback
        prepopulateDefaultCategories(db)
    }

    /**
     * Called when the database has been opened.
     * Can be used for validation, logging, or lazy initialization.
     *
     * @param db The database instance
     */
    override fun onOpen(db: SupportSQLiteDatabase) {
        super.onOpen(db)
        Log.d(TAG, "Database opened")

        // Perform any necessary validation or cleanup
        performDatabaseHealthCheck(db)
    }

    /**
     * Called when the database is configured.
     * Can be used to enable foreign key constraints, etc.
     *
     * @param db The database instance
     */
    override fun onDestructiveMigration(db: SupportSQLiteDatabase) {
        super.onDestructiveMigration(db)
        Log.w(TAG, "Destructive migration performed - all data was lost")

        // Re-prepopulate default categories after destructive migration
        prepopulateDefaultCategories(db)
    }

    /**
     * Prepopulates the database with default expense and income categories.
     * Uses raw SQL for reliability during the callback phase.
     */
    private fun prepopulateDefaultCategories(db: SupportSQLiteDatabase) {
        Log.d(TAG, "Prepopulating default categories")

        val currentTime = System.currentTimeMillis()

        // Default expense categories
        val expenseCategories = listOf(
            DefaultCategory(
                name = "Alimentation",
                icon = "restaurant",
                color = "#FF5722",
                type = CategoryType.EXPENSE,
                description = "Courses, restaurants et nourriture"
            ),
            DefaultCategory(
                name = "Transport",
                icon = "directions_car",
                color = "#2196F3",
                type = CategoryType.EXPENSE,
                description = "Carburant, transports en commun, taxi"
            ),
            DefaultCategory(
                name = "Logement",
                icon = "home",
                color = "#4CAF50",
                type = CategoryType.EXPENSE,
                description = "Loyer, charges, assurance habitation"
            ),
            DefaultCategory(
                name = "Santé",
                icon = "local_hospital",
                color = "#E91E63",
                type = CategoryType.EXPENSE,
                description = "Médecin, pharmacie, mutuelle"
            ),
            DefaultCategory(
                name = "Loisirs",
                icon = "sports_esports",
                color = "#9C27B0",
                type = CategoryType.EXPENSE,
                description = "Divertissement, sorties, hobbies"
            ),
            DefaultCategory(
                name = "Shopping",
                icon = "shopping_bag",
                color = "#FF9800",
                type = CategoryType.EXPENSE,
                description = "Vêtements, électronique, achats divers"
            ),
            DefaultCategory(
                name = "Factures",
                icon = "receipt",
                color = "#607D8B",
                type = CategoryType.EXPENSE,
                description = "Électricité, eau, internet, téléphone"
            ),
            DefaultCategory(
                name = "Éducation",
                icon = "school",
                color = "#3F51B5",
                type = CategoryType.EXPENSE,
                description = "Formation, livres, cours"
            ),
            DefaultCategory(
                name = "Voyages",
                icon = "flight",
                color = "#00BCD4",
                type = CategoryType.EXPENSE,
                description = "Vacances, déplacements, hébergement"
            ),
            DefaultCategory(
                name = "Cadeaux",
                icon = "card_giftcard",
                color = "#E040FB",
                type = CategoryType.EXPENSE,
                description = "Cadeaux pour famille et amis"
            ),
            DefaultCategory(
                name = "Épargne",
                icon = "savings",
                color = "#8BC34A",
                type = CategoryType.EXPENSE,
                description = "Versements épargne, investissements"
            ),
            DefaultCategory(
                name = "Autres dépenses",
                icon = "more_horiz",
                color = "#795548",
                type = CategoryType.EXPENSE,
                description = "Dépenses diverses non catégorisées"
            )
        )

        // Default income categories
        val incomeCategories = listOf(
            DefaultCategory(
                name = "Salaire",
                icon = "work",
                color = "#4CAF50",
                type = CategoryType.INCOME,
                description = "Salaire mensuel, primes"
            ),
            DefaultCategory(
                name = "Freelance",
                icon = "laptop",
                color = "#2196F3",
                type = CategoryType.INCOME,
                description = "Revenus d'activité indépendante"
            ),
            DefaultCategory(
                name = "Investissements",
                icon = "trending_up",
                color = "#FF9800",
                type = CategoryType.INCOME,
                description = "Dividendes, plus-values, intérêts"
            ),
            DefaultCategory(
                name = "Remboursements",
                icon = "replay",
                color = "#9C27B0",
                type = CategoryType.INCOME,
                description = "Remboursements divers, notes de frais"
            ),
            DefaultCategory(
                name = "Cadeaux reçus",
                icon = "redeem",
                color = "#E91E63",
                type = CategoryType.INCOME,
                description = "Argent reçu en cadeau"
            ),
            DefaultCategory(
                name = "Allocations",
                icon = "account_balance",
                color = "#00BCD4",
                type = CategoryType.INCOME,
                description = "Aides sociales, allocations diverses"
            ),
            DefaultCategory(
                name = "Location",
                icon = "apartment",
                color = "#607D8B",
                type = CategoryType.INCOME,
                description = "Revenus locatifs"
            ),
            DefaultCategory(
                name = "Autres revenus",
                icon = "add_circle",
                color = "#8BC34A",
                type = CategoryType.INCOME,
                description = "Revenus divers non catégorisés"
            )
        )

        // Insert all categories
        val allCategories = expenseCategories + incomeCategories

        allCategories.forEachIndexed { index, category ->
            val uuid = UUID.randomUUID().toString()
            val sql = """
                INSERT INTO categories (
                    id, uuid, name, icon, color, type, description,
                    is_default, is_active, sort_order, created_at, updated_at
                ) VALUES (
                    ${index + 1},
                    '$uuid',
                    '${category.name}',
                    '${category.icon}',
                    '${category.color}',
                    '${category.type.name}',
                    '${category.description}',
                    1,
                    1,
                    ${index + 1},
                    $currentTime,
                    $currentTime
                )
            """.trimIndent()

            try {
                db.execSQL(sql)
                Log.d(TAG, "Inserted category: ${category.name}")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to insert category: ${category.name}", e)
            }
        }

        Log.d(TAG, "Default categories prepopulated: ${allCategories.size} categories")
    }

    /**
     * Performs a health check on the database.
     * Validates integrity and logs useful statistics.
     */
    private fun performDatabaseHealthCheck(db: SupportSQLiteDatabase) {
        try {
            // Check database integrity
            val integrityCheck = db.query("PRAGMA integrity_check")
            if (integrityCheck.moveToFirst()) {
                val result = integrityCheck.getString(0)
                if (result == "ok") {
                    Log.d(TAG, "Database integrity check: OK")
                } else {
                    Log.e(TAG, "Database integrity check failed: $result")
                }
            }
            integrityCheck.close()

            // Log table statistics
            logTableStatistics(db)

        } catch (e: Exception) {
            Log.e(TAG, "Database health check failed", e)
        }
    }

    /**
     * Logs statistics about the database tables.
     * Useful for debugging and monitoring.
     */
    private fun logTableStatistics(db: SupportSQLiteDatabase) {
        val tables = listOf(
            "users",
            "accounts",
            "transactions",
            "categories",
            "budgets",
            "recurring_transactions"
        )

        tables.forEach { table ->
            try {
                val cursor = db.query("SELECT COUNT(*) FROM $table")
                if (cursor.moveToFirst()) {
                    val count = cursor.getLong(0)
                    Log.d(TAG, "Table '$table' row count: $count")
                }
                cursor.close()
            } catch (e: Exception) {
                // Table might not exist yet
                Log.d(TAG, "Table '$table' not accessible: ${e.message}")
            }
        }
    }

    /**
     * Data class for default category configuration.
     */
    private data class DefaultCategory(
        val name: String,
        val icon: String,
        val color: String,
        val type: CategoryType,
        val description: String
    )
}

/**
 * Extension object providing utility functions for database operations.
 */
object DatabaseUtils {

    /**
     * Clears all data from the database while preserving the schema.
     * Useful for logout or reset functionality.
     *
     * @param database The AppDatabase instance
     */
    suspend fun clearAllData(database: AppDatabase) {
        database.clearAllTables()
        Log.d("DatabaseUtils", "All database tables cleared")
    }

    /**
     * Exports database to a backup file.
     * Note: Implementation requires proper file handling.
     *
     * @param context Application context
     * @param database The AppDatabase instance
     * @return Path to the backup file, or null if failed
     */
    fun exportDatabase(context: Context, database: AppDatabase): String? {
        // TODO: Implement database export functionality
        Log.d("DatabaseUtils", "Database export not yet implemented")
        return null
    }

    /**
     * Imports database from a backup file.
     * Note: Implementation requires proper file handling and validation.
     *
     * @param context Application context
     * @param backupPath Path to the backup file
     * @return true if import was successful
     */
    fun importDatabase(context: Context, backupPath: String): Boolean {
        // TODO: Implement database import functionality
        Log.d("DatabaseUtils", "Database import not yet implemented")
        return false
    }
}
