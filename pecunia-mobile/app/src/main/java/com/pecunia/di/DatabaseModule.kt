package com.pecunia.di

import android.content.Context
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import com.pecunia.data.local.database.AppDatabase
import com.pecunia.data.local.database.dao.BudgetDao
import com.pecunia.data.local.database.dao.TransactionDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.concurrent.Executors
import javax.inject.Provider
import javax.inject.Qualifier
import javax.inject.Singleton

/**
 * Qualifier for application-level CoroutineScope.
 */
@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class ApplicationScope

/**
 * Hilt module providing database-related dependencies.
 * Configures Room database and DAOs.
 */
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    private const val DATABASE_NAME = "pecunia_database"

    /**
     * Provides application-level CoroutineScope for background operations.
     */
    @Provides
    @Singleton
    @ApplicationScope
    fun provideApplicationScope(
        @DefaultDispatcher defaultDispatcher: CoroutineDispatcher
    ): CoroutineScope {
        return CoroutineScope(SupervisorJob() + defaultDispatcher)
    }

    /**
     * Provides the Room database instance.
     * Configured with:
     * - Destructive migration fallback (for development)
     * - Pre-populated callback for default data
     * - Query execution on background thread
     */
    @Provides
    @Singleton
    fun provideAppDatabase(
        @ApplicationContext context: Context,
        @ApplicationScope applicationScope: CoroutineScope,
        transactionDaoProvider: Provider<TransactionDao>,
        budgetDaoProvider: Provider<BudgetDao>
    ): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            DATABASE_NAME
        )
            .fallbackToDestructiveMigration()
            .setQueryExecutor(Executors.newFixedThreadPool(4))
            .setTransactionExecutor(Executors.newSingleThreadExecutor())
            .addCallback(object : RoomDatabase.Callback() {
                override fun onCreate(db: SupportSQLiteDatabase) {
                    super.onCreate(db)
                    // Pre-populate database with default data if needed
                    applicationScope.launch {
                        prepopulateDatabase(
                            transactionDaoProvider.get(),
                            budgetDaoProvider.get()
                        )
                    }
                }

                override fun onOpen(db: SupportSQLiteDatabase) {
                    super.onOpen(db)
                    // Enable foreign key constraints
                    db.execSQL("PRAGMA foreign_keys=ON;")
                }
            })
            .build()
    }

    /**
     * Pre-populate database with default data.
     * Called when database is created for the first time.
     */
    private suspend fun prepopulateDatabase(
        transactionDao: TransactionDao,
        budgetDao: BudgetDao
    ) {
        // Add default categories, sample data, etc.
        // This is optional and can be expanded as needed
    }

    /**
     * Provides TransactionDao for transaction database operations.
     */
    @Provides
    @Singleton
    fun provideTransactionDao(database: AppDatabase): TransactionDao {
        return database.transactionDao()
    }

    /**
     * Provides BudgetDao for budget database operations.
     */
    @Provides
    @Singleton
    fun provideBudgetDao(database: AppDatabase): BudgetDao {
        return database.budgetDao()
    }
}
