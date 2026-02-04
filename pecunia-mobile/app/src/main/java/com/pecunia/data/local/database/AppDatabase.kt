package com.pecunia.data.local.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.pecunia.data.local.dao.AccountDao
import com.pecunia.data.local.dao.BudgetDao
import com.pecunia.data.local.dao.CategoryDao
import com.pecunia.data.local.dao.RecurringTransactionDao
import com.pecunia.data.local.dao.TransactionDao
import com.pecunia.data.local.dao.UserDao
import com.pecunia.data.local.entity.AccountEntity
import com.pecunia.data.local.entity.BudgetEntity
import com.pecunia.data.local.entity.CategoryEntity
import com.pecunia.data.local.entity.RecurringTransactionEntity
import com.pecunia.data.local.entity.TransactionEntity
import com.pecunia.data.local.entity.UserEntity

/**
 * Main Room database for the Pecunia.
 *
 * This database manages all local data storage including:
 * - User profiles and authentication data
 * - Bank accounts and balances
 * - Financial transactions
 * - Budget tracking
 * - Categories for transaction classification
 * - Recurring transactions for scheduled payments
 */
@Database(
    entities = [
        UserEntity::class,
        AccountEntity::class,
        TransactionEntity::class,
        CategoryEntity::class,
        BudgetEntity::class,
        RecurringTransactionEntity::class
    ],
    version = 1,
    exportSchema = true
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {

    // ============================================
    // Abstract DAO declarations
    // ============================================

    /**
     * DAO for user-related database operations.
     */
    abstract fun userDao(): UserDao

    /**
     * DAO for account-related database operations.
     */
    abstract fun accountDao(): AccountDao

    /**
     * DAO for transaction-related database operations.
     */
    abstract fun transactionDao(): TransactionDao

    /**
     * DAO for category-related database operations.
     */
    abstract fun categoryDao(): CategoryDao

    /**
     * DAO for budget-related database operations.
     */
    abstract fun budgetDao(): BudgetDao

    /**
     * DAO for recurring transaction-related database operations.
     */
    abstract fun recurringTransactionDao(): RecurringTransactionDao

    companion object {
        private const val DATABASE_NAME = "pecunia_database"

        @Volatile
        private var INSTANCE: AppDatabase? = null

        /**
         * Returns the singleton instance of [AppDatabase].
         *
         * Uses double-checked locking to ensure thread-safe lazy initialization.
         * The database is configured with:
         * - Type converters for complex data types
         * - Callback for prepopulating default data
         * - Fallback to destructive migration in development (should be changed in production)
         *
         * @param context Application context used to create the database
         * @return The singleton [AppDatabase] instance
         */
        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: buildDatabase(context).also { INSTANCE = it }
            }
        }

        /**
         * Builds and configures the Room database instance.
         */
        private fun buildDatabase(context: Context): AppDatabase {
            return Room.databaseBuilder(
                context.applicationContext,
                AppDatabase::class.java,
                DATABASE_NAME
            )
                .addCallback(DatabaseCallback(context))
                .addMigrations(*getAllMigrations())
                // Fallback to destructive migration for development
                // TODO: Remove this in production and implement proper migrations
                .fallbackToDestructiveMigration()
                .build()
        }

        /**
         * Returns all database migrations.
         * Add new migrations here as the schema evolves.
         */
        private fun getAllMigrations(): Array<Migration> {
            return arrayOf(
                // Future migrations will be added here
                // MIGRATION_1_2,
                // MIGRATION_2_3,
            )
        }

        // ============================================
        // Migration Definitions
        // ============================================

        /**
         * Example migration from version 1 to 2.
         * Uncomment and modify when needed.
         */
        /*
        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                // Example: Add a new column to transactions table
                // database.execSQL(
                //     "ALTER TABLE transactions ADD COLUMN notes TEXT DEFAULT NULL"
                // )
            }
        }
        */

        /**
         * Example migration from version 2 to 3.
         * Uncomment and modify when needed.
         */
        /*
        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(database: SupportSQLiteDatabase) {
                // Example: Create a new index
                // database.execSQL(
                //     "CREATE INDEX IF NOT EXISTS index_transactions_category_id ON transactions(category_id)"
                // )
            }
        }
        */

        /**
         * Clears the database instance.
         * Useful for testing or when signing out a user.
         */
        fun clearInstance() {
            INSTANCE?.close()
            INSTANCE = null
        }

        /**
         * Checks if the database instance exists.
         * @return true if the database has been initialized
         */
        fun isInitialized(): Boolean = INSTANCE != null
    }
}
