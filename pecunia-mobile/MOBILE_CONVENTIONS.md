# Mobile Platform Conventions - FinanceApp Kotlin/Android

**Version**: 1.0
**Last Updated**: 2026-01-28
**Status**: MANDATORY for all Android development

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [Dependency Injection (Hilt)](#3-dependency-injection-hilt)
4. [Domain Layer](#4-domain-layer)
5. [Data Layer](#5-data-layer)
6. [Presentation Layer](#6-presentation-layer)
7. [Navigation](#7-navigation)
8. [Error Handling](#8-error-handling)
9. [Testing Standards](#9-testing-standards)
10. [Security Guidelines](#10-security-guidelines)
11. [Build Configuration](#11-build-configuration)
12. [Code Style](#12-code-style)

---

## 1. Architecture Overview

### Clean Architecture with MVVM

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Screens   │  │  ViewModels │  │    State    │              │
│  │  (Compose)  │◄─│   (MVVM)    │◄─│  (StateFlow)│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Use Cases  │  │   Models    │  │ Repository  │              │
│  │  (Business) │  │  (Entities) │  │ Interfaces  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Repository  │  │   Local     │  │   Remote    │              │
│  │   Impl      │◄─│   (Room)    │  │  (Retrofit) │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Separation of Concerns** | Each layer has a single responsibility |
| **Dependency Rule** | Dependencies point inward only |
| **Abstraction** | Domain layer contains only interfaces |
| **Offline-First** | Local database is the source of truth |
| **Reactive** | Use Flow/StateFlow for data streams |

---

## 2. Project Structure

### Module Structure

```
financeapp-mobile/
├── app/                           # Application module
│   ├── src/main/
│   │   ├── java/com/financeapp/
│   │   │   ├── FinanceApp.kt     # Application class
│   │   │   ├── di/               # Hilt modules
│   │   │   │   ├── AppModule.kt
│   │   │   │   ├── DatabaseModule.kt
│   │   │   │   └── NetworkModule.kt
│   │   │   └── navigation/       # Navigation
│   │   │       ├── NavGraph.kt
│   │   │       ├── Route.kt
│   │   │       └── NavActions.kt
│   │   └── res/
│   └── build.gradle.kts
│
├── domain/                        # Domain module
│   ├── models/                   # Domain entities
│   │   ├── User.kt
│   │   ├── Transaction.kt
│   │   └── Budget.kt
│   ├── repository/               # Repository interfaces
│   │   ├── TransactionRepository.kt
│   │   └── BudgetRepository.kt
│   └── usecases/                 # Business logic
│       ├── GetTransactionsUseCase.kt
│       └── SyncDataUseCase.kt
│
├── data/                          # Data module
│   ├── local/
│   │   ├── database/             # Room database
│   │   │   ├── AppDatabase.kt
│   │   │   ├── dao/
│   │   │   │   ├── TransactionDao.kt
│   │   │   │   └── BudgetDao.kt
│   │   │   └── entity/
│   │   │       ├── TransactionEntity.kt
│   │   │       └── BudgetEntity.kt
│   │   └── preferences/          # SharedPreferences
│   │       └── TokenStorage.kt
│   ├── remote/
│   │   ├── api/                  # Retrofit services
│   │   │   ├── ApiService.kt
│   │   │   └── AuthInterceptor.kt
│   │   └── dto/                  # Data transfer objects
│   │       ├── TransactionDto.kt
│   │       └── BudgetDto.kt
│   ├── repository/               # Repository implementations
│   │   ├── TransactionRepositoryImpl.kt
│   │   └── BudgetRepositoryImpl.kt
│   └── mapper/                   # Entity/DTO mappers
│       └── TransactionMapper.kt
│
├── ui/                            # Presentation module
│   ├── screens/
│   │   ├── dashboard/
│   │   │   ├── DashboardScreen.kt
│   │   │   └── DashboardViewModel.kt
│   │   ├── transactions/
│   │   │   ├── TransactionListScreen.kt
│   │   │   ├── TransactionDetailScreen.kt
│   │   │   └── TransactionViewModel.kt
│   │   └── settings/
│   │       ├── SettingsScreen.kt
│   │       └── SettingsViewModel.kt
│   ├── components/               # Reusable Compose components
│   │   ├── TransactionCard.kt
│   │   ├── AmountText.kt
│   │   └── LoadingIndicator.kt
│   └── theme/
│       ├── Theme.kt
│       ├── Color.kt
│       └── Type.kt
│
├── build.gradle.kts
└── settings.gradle.kts
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Packages | lowercase | `com.financeapp.data.repository` |
| Classes | PascalCase | `TransactionRepository` |
| Functions | camelCase | `getTransactions()` |
| Variables | camelCase | `transactionList` |
| Constants | SCREAMING_SNAKE | `MAX_PAGE_SIZE` |
| Composables | PascalCase | `TransactionCard()` |
| ViewModels | PascalCase + ViewModel | `TransactionViewModel` |
| Use Cases | PascalCase + UseCase | `GetTransactionsUseCase` |

---

## 3. Dependency Injection (Hilt)

### Application Module

```kotlin
/**
 * AppModule - Core application dependencies.
 *
 * Provides:
 * - Coroutine dispatchers
 * - Encrypted SharedPreferences
 * - Application-wide singletons
 */
@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    /**
     * Provide IO dispatcher for background operations.
     */
    @Provides
    @IoDispatcher
    fun provideIoDispatcher(): CoroutineDispatcher = Dispatchers.IO

    /**
     * Provide Default dispatcher for CPU-intensive work.
     */
    @Provides
    @DefaultDispatcher
    fun provideDefaultDispatcher(): CoroutineDispatcher = Dispatchers.Default

    /**
     * Provide Main dispatcher for UI operations.
     */
    @Provides
    @MainDispatcher
    fun provideMainDispatcher(): CoroutineDispatcher = Dispatchers.Main

    /**
     * Provide encrypted SharedPreferences for secure storage.
     *
     * Uses AES-256 encryption for both keys and values.
     */
    @Provides
    @Singleton
    fun provideEncryptedSharedPreferences(
        @ApplicationContext context: Context
    ): SharedPreferences {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        return EncryptedSharedPreferences.create(
            context,
            "secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }
}

/**
 * Qualifier for IO dispatcher.
 */
@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class IoDispatcher

/**
 * Qualifier for Default dispatcher.
 */
@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class DefaultDispatcher

/**
 * Qualifier for Main dispatcher.
 */
@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class MainDispatcher
```

### Database Module

```kotlin
/**
 * DatabaseModule - Room database dependencies.
 *
 * Provides:
 * - AppDatabase singleton
 * - All DAOs
 */
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    /**
     * Provide Room database instance.
     *
     * Configuration:
     * - Encrypted with SQLCipher (if enabled)
     * - Proper migration strategy
     * - Query executor optimization
     */
    @Provides
    @Singleton
    fun provideAppDatabase(
        @ApplicationContext context: Context
    ): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "financeapp.db"
        )
            .addMigrations(MIGRATION_1_2, MIGRATION_2_3)
            .setQueryCallback({ sqlQuery, bindArgs ->
                // Log queries in debug builds
                if (BuildConfig.DEBUG) {
                    Log.d("RoomQuery", "Query: $sqlQuery, Args: $bindArgs")
                }
            }, Executors.newSingleThreadExecutor())
            .build()
    }

    @Provides
    fun provideTransactionDao(database: AppDatabase): TransactionDao {
        return database.transactionDao()
    }

    @Provides
    fun provideBudgetDao(database: AppDatabase): BudgetDao {
        return database.budgetDao()
    }
}
```

### Network Module

```kotlin
/**
 * NetworkModule - Retrofit and OkHttp dependencies.
 *
 * Provides:
 * - OkHttpClient with interceptors
 * - Retrofit instance
 * - API services
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    private const val BASE_URL = "https://api.financeapp.com/"
    private const val CONNECT_TIMEOUT = 10L
    private const val READ_TIMEOUT = 30L
    private const val WRITE_TIMEOUT = 30L

    /**
     * Provide OkHttpClient with security and logging.
     *
     * Features:
     * - Certificate pinning (production)
     * - Auth token injection
     * - Request/response logging (debug only)
     * - Connection pooling
     */
    @Provides
    @Singleton
    fun provideOkHttpClient(
        authInterceptor: AuthInterceptor
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(CONNECT_TIMEOUT, TimeUnit.SECONDS)
            .readTimeout(READ_TIMEOUT, TimeUnit.SECONDS)
            .writeTimeout(WRITE_TIMEOUT, TimeUnit.SECONDS)
            .addInterceptor(authInterceptor)
            .connectionPool(
                ConnectionPool(5, 5, TimeUnit.MINUTES)
            )

        // Certificate pinning for production
        if (!BuildConfig.DEBUG) {
            val certificatePinner = CertificatePinner.Builder()
                .add("api.financeapp.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
                .add("api.financeapp.com", "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=")
                .build()
            builder.certificatePinner(certificatePinner)
        }

        // Logging for debug builds only
        if (BuildConfig.DEBUG) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.HEADERS // Not BODY in production!
            }
            builder.addInterceptor(loggingInterceptor)
        }

        return builder.build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }
}
```

### Repository Module

```kotlin
/**
 * RepositoryModule - Repository implementations.
 */
@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindTransactionRepository(
        impl: TransactionRepositoryImpl
    ): TransactionRepository

    @Binds
    @Singleton
    abstract fun bindBudgetRepository(
        impl: BudgetRepositoryImpl
    ): BudgetRepository

    @Binds
    @Singleton
    abstract fun bindAuthRepository(
        impl: AuthRepositoryImpl
    ): AuthRepository
}
```

---

## 4. Domain Layer

### Domain Model Template

```kotlin
/**
 * Transaction domain model.
 *
 * Represents a financial transaction in the domain layer.
 * Contains only business logic and computed properties.
 *
 * @property id Unique identifier (UUID string)
 * @property amount Transaction amount (always positive)
 * @property type Transaction type (income, expense, transfer)
 * @property category Transaction category
 * @property description User description
 * @property date Transaction date
 * @property isSynced Whether synced with server
 */
data class Transaction(
    val id: String,
    val userId: String,
    val amount: BigDecimal,
    val type: TransactionType,
    val category: TransactionCategory,
    val description: String,
    val date: LocalDate,
    val tags: List<String> = emptyList(),
    val isRecurring: Boolean = false,
    val isSynced: Boolean = false,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
) {
    /**
     * Signed amount (negative for expenses).
     */
    val signedAmount: BigDecimal
        get() = when (type) {
            TransactionType.EXPENSE -> -amount
            else -> amount
        }

    /**
     * Formatted amount string for display.
     */
    fun formatAmount(currency: Currency = Currency.getInstance("EUR")): String {
        val format = NumberFormat.getCurrencyInstance().apply {
            this.currency = currency
        }
        return format.format(signedAmount)
    }

    /**
     * Check if transaction is from current month.
     */
    val isCurrentMonth: Boolean
        get() {
            val now = LocalDate.now()
            return date.year == now.year && date.month == now.month
        }
}

/**
 * Transaction type enumeration.
 */
enum class TransactionType {
    INCOME,
    EXPENSE,
    TRANSFER;

    /**
     * Convert to API value (lowercase).
     */
    fun toApiValue(): String = name.lowercase()

    companion object {
        fun fromApiValue(value: String): TransactionType {
            return valueOf(value.uppercase())
        }
    }
}

/**
 * Transaction category enumeration.
 */
enum class TransactionCategory(
    val displayName: String,
    val icon: String
) {
    SALARY("Salary", "ic_salary"),
    FOOD("Food & Dining", "ic_food"),
    TRANSPORTATION("Transportation", "ic_transport"),
    UTILITIES("Utilities", "ic_utilities"),
    ENTERTAINMENT("Entertainment", "ic_entertainment"),
    SHOPPING("Shopping", "ic_shopping"),
    HEALTHCARE("Healthcare", "ic_health"),
    EDUCATION("Education", "ic_education"),
    TRAVEL("Travel", "ic_travel"),
    SUBSCRIPTIONS("Subscriptions", "ic_subscription"),
    INVESTMENTS("Investments", "ic_investment"),
    OTHER_INCOME("Other Income", "ic_income"),
    OTHER_EXPENSE("Other Expense", "ic_expense");

    fun toApiValue(): String = name.lowercase()

    companion object {
        fun fromApiValue(value: String): TransactionCategory {
            return entries.find { it.name.equals(value, ignoreCase = true) }
                ?: OTHER_EXPENSE
        }
    }
}
```

### Use Case Template

```kotlin
/**
 * GetTransactionsUseCase - Business logic for transaction retrieval.
 *
 * Provides various methods to query transactions with filtering,
 * sorting, and aggregation.
 *
 * All methods return Flow for reactive updates.
 */
class GetTransactionsUseCase @Inject constructor(
    private val repository: TransactionRepository
) {
    /**
     * Get all transactions for the current user.
     *
     * @return Flow of transaction list, sorted by date descending
     */
    operator fun invoke(): Flow<List<Transaction>> {
        return repository.getTransactions()
    }

    /**
     * Get transactions within a date range.
     *
     * @param startDate Start of range (inclusive)
     * @param endDate End of range (inclusive)
     * @return Flow of filtered transactions
     */
    fun getByDateRange(
        startDate: LocalDate,
        endDate: LocalDate
    ): Flow<List<Transaction>> {
        return repository.getTransactionsByDateRange(startDate, endDate)
    }

    /**
     * Get transactions by category.
     *
     * @param category Category to filter by
     * @return Flow of filtered transactions
     */
    fun getByCategory(category: TransactionCategory): Flow<List<Transaction>> {
        return repository.getTransactionsByCategory(category)
    }

    /**
     * Get transactions by type (income/expense/transfer).
     *
     * @param type Transaction type to filter by
     * @return Flow of filtered transactions
     */
    fun getByType(type: TransactionType): Flow<List<Transaction>> {
        return repository.getTransactionsByType(type)
    }

    /**
     * Search transactions by description.
     *
     * @param query Search query
     * @return Flow of matching transactions
     */
    fun search(query: String): Flow<List<Transaction>> {
        return repository.searchTransactions(query)
    }

    /**
     * Get transaction summary for a period.
     *
     * @param startDate Start of period
     * @param endDate End of period
     * @return Summary with totals and counts
     */
    suspend fun getSummary(
        startDate: LocalDate,
        endDate: LocalDate
    ): TransactionSummary {
        return repository.getTransactionSummary(startDate, endDate)
    }

    /**
     * Get recurring transactions.
     *
     * @return Flow of recurring transactions
     */
    fun getRecurring(): Flow<List<Transaction>> {
        return repository.getRecurringTransactions()
    }
}

/**
 * Transaction summary data class.
 */
data class TransactionSummary(
    val totalIncome: BigDecimal,
    val totalExpenses: BigDecimal,
    val netAmount: BigDecimal,
    val transactionCount: Int,
    val byCategory: Map<TransactionCategory, BigDecimal>
) {
    val savingsRate: Float
        get() = if (totalIncome > BigDecimal.ZERO) {
            (netAmount.toFloat() / totalIncome.toFloat()) * 100
        } else 0f
}
```

### Repository Interface Template

```kotlin
/**
 * TransactionRepository - Interface for transaction data access.
 *
 * Defines the contract for transaction storage and retrieval.
 * Implementations handle the actual data source (Room, API, etc.).
 */
interface TransactionRepository {

    /**
     * Get all transactions as a Flow.
     */
    fun getTransactions(): Flow<List<Transaction>>

    /**
     * Get transactions within a date range.
     */
    fun getTransactionsByDateRange(
        startDate: LocalDate,
        endDate: LocalDate
    ): Flow<List<Transaction>>

    /**
     * Get transactions by category.
     */
    fun getTransactionsByCategory(
        category: TransactionCategory
    ): Flow<List<Transaction>>

    /**
     * Get transactions by type.
     */
    fun getTransactionsByType(
        type: TransactionType
    ): Flow<List<Transaction>>

    /**
     * Search transactions by description.
     */
    fun searchTransactions(query: String): Flow<List<Transaction>>

    /**
     * Get transaction summary for a period.
     */
    suspend fun getTransactionSummary(
        startDate: LocalDate,
        endDate: LocalDate
    ): TransactionSummary

    /**
     * Get recurring transactions.
     */
    fun getRecurringTransactions(): Flow<List<Transaction>>

    /**
     * Get single transaction by ID.
     */
    suspend fun getTransaction(id: String): Transaction?

    /**
     * Create new transaction.
     *
     * @param transaction Transaction to create
     * @return Result with created transaction or error
     */
    suspend fun createTransaction(transaction: Transaction): Result<Transaction>

    /**
     * Update existing transaction.
     *
     * @param transaction Transaction with updated values
     * @return Result with updated transaction or error
     */
    suspend fun updateTransaction(transaction: Transaction): Result<Transaction>

    /**
     * Delete transaction.
     *
     * @param id Transaction ID to delete
     * @return Result indicating success or error
     */
    suspend fun deleteTransaction(id: String): Result<Unit>

    /**
     * Sync transactions with server.
     *
     * @return Result with sync statistics or error
     */
    suspend fun syncTransactions(): Result<SyncResult>
}
```

---

## 5. Data Layer

### Room Entity Template

```kotlin
/**
 * TransactionEntity - Room database entity.
 *
 * Maps to the 'transactions' table in the local database.
 * Contains sync tracking fields for offline-first operation.
 */
@Entity(
    tableName = "transactions",
    indices = [
        Index(value = ["user_id"]),
        Index(value = ["category"]),
        Index(value = ["date"]),
        Index(value = ["type"]),
        Index(value = ["is_synced"])
    ],
    foreignKeys = [
        ForeignKey(
            entity = UserEntity::class,
            parentColumns = ["id"],
            childColumns = ["user_id"],
            onDelete = ForeignKey.CASCADE
        )
    ]
)
data class TransactionEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: String,

    @ColumnInfo(name = "server_id")
    val serverId: String? = null,

    @ColumnInfo(name = "user_id")
    val userId: String,

    @ColumnInfo(name = "amount")
    val amount: Double,

    @ColumnInfo(name = "type")
    val type: String,

    @ColumnInfo(name = "category")
    val category: String,

    @ColumnInfo(name = "description")
    val description: String,

    @ColumnInfo(name = "date")
    val date: Long, // Epoch milliseconds

    @ColumnInfo(name = "tags")
    val tags: String = "", // Comma-separated

    @ColumnInfo(name = "is_recurring")
    val isRecurring: Boolean = false,

    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false,

    @ColumnInfo(name = "sync_status")
    val syncStatus: String = "pending",

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis()
)
```

### DAO Template

```kotlin
/**
 * TransactionDao - Data Access Object for transactions.
 *
 * Provides all database operations for transactions.
 * Uses Flow for reactive queries.
 */
@Dao
interface TransactionDao {

    // ==========================================================================
    // QUERIES
    // ==========================================================================

    /**
     * Get all transactions ordered by date descending.
     */
    @Query("""
        SELECT * FROM transactions
        WHERE user_id = :userId
        ORDER BY date DESC
    """)
    fun getTransactions(userId: String): Flow<List<TransactionEntity>>

    /**
     * Get transactions within a date range.
     */
    @Query("""
        SELECT * FROM transactions
        WHERE user_id = :userId
        AND date BETWEEN :startDate AND :endDate
        ORDER BY date DESC
    """)
    fun getTransactionsByDateRange(
        userId: String,
        startDate: Long,
        endDate: Long
    ): Flow<List<TransactionEntity>>

    /**
     * Get transactions by category.
     */
    @Query("""
        SELECT * FROM transactions
        WHERE user_id = :userId
        AND category = :category
        ORDER BY date DESC
    """)
    fun getTransactionsByCategory(
        userId: String,
        category: String
    ): Flow<List<TransactionEntity>>

    /**
     * Get transactions by type.
     */
    @Query("""
        SELECT * FROM transactions
        WHERE user_id = :userId
        AND type = :type
        ORDER BY date DESC
    """)
    fun getTransactionsByType(
        userId: String,
        type: String
    ): Flow<List<TransactionEntity>>

    /**
     * Search transactions by description.
     */
    @Query("""
        SELECT * FROM transactions
        WHERE user_id = :userId
        AND description LIKE '%' || :query || '%'
        ORDER BY date DESC
    """)
    fun searchTransactions(
        userId: String,
        query: String
    ): Flow<List<TransactionEntity>>

    /**
     * Get single transaction by ID.
     */
    @Query("SELECT * FROM transactions WHERE id = :id")
    suspend fun getTransaction(id: String): TransactionEntity?

    /**
     * Get transaction summary (aggregates).
     */
    @Query("""
        SELECT
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as totalIncome,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as totalExpenses,
            COUNT(*) as transactionCount
        FROM transactions
        WHERE user_id = :userId
        AND date BETWEEN :startDate AND :endDate
    """)
    suspend fun getTransactionSummary(
        userId: String,
        startDate: Long,
        endDate: Long
    ): TransactionSummaryEntity

    /**
     * Get unsynced transactions.
     */
    @Query("""
        SELECT * FROM transactions
        WHERE is_synced = 0
        ORDER BY created_at ASC
    """)
    suspend fun getUnsyncedTransactions(): List<TransactionEntity>

    // ==========================================================================
    // INSERTS
    // ==========================================================================

    /**
     * Insert single transaction.
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(transaction: TransactionEntity)

    /**
     * Insert multiple transactions.
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(transactions: List<TransactionEntity>)

    // ==========================================================================
    // UPDATES
    // ==========================================================================

    /**
     * Update transaction.
     */
    @Update
    suspend fun update(transaction: TransactionEntity)

    /**
     * Mark transaction as synced.
     */
    @Query("""
        UPDATE transactions
        SET is_synced = 1, sync_status = 'synced', server_id = :serverId
        WHERE id = :id
    """)
    suspend fun markSynced(id: String, serverId: String)

    // ==========================================================================
    // DELETES
    // ==========================================================================

    /**
     * Delete transaction by ID.
     */
    @Query("DELETE FROM transactions WHERE id = :id")
    suspend fun delete(id: String)

    /**
     * Delete all transactions for user.
     */
    @Query("DELETE FROM transactions WHERE user_id = :userId")
    suspend fun deleteAllForUser(userId: String)
}

/**
 * Summary entity for aggregate queries.
 */
data class TransactionSummaryEntity(
    val totalIncome: Double,
    val totalExpenses: Double,
    val transactionCount: Int
)
```

### Repository Implementation Template

```kotlin
/**
 * TransactionRepositoryImpl - Implementation of TransactionRepository.
 *
 * Implements offline-first strategy:
 * 1. All reads come from local database
 * 2. Writes go to local first, then sync
 * 3. Sync pulls from server and merges
 */
class TransactionRepositoryImpl @Inject constructor(
    private val transactionDao: TransactionDao,
    private val apiService: ApiService,
    private val mapper: TransactionMapper,
    private val tokenStorage: TokenStorage,
    @IoDispatcher private val ioDispatcher: CoroutineDispatcher
) : TransactionRepository {

    private val userId: String
        get() = tokenStorage.getUserId() ?: throw IllegalStateException("User not logged in")

    override fun getTransactions(): Flow<List<Transaction>> {
        return transactionDao.getTransactions(userId)
            .map { entities -> entities.map(mapper::entityToDomain) }
            .flowOn(ioDispatcher)
    }

    override fun getTransactionsByDateRange(
        startDate: LocalDate,
        endDate: LocalDate
    ): Flow<List<Transaction>> {
        return transactionDao.getTransactionsByDateRange(
            userId,
            startDate.toEpochMilli(),
            endDate.toEpochMilli()
        )
            .map { entities -> entities.map(mapper::entityToDomain) }
            .flowOn(ioDispatcher)
    }

    override suspend fun createTransaction(
        transaction: Transaction
    ): Result<Transaction> = withContext(ioDispatcher) {
        try {
            // Generate local ID
            val localTransaction = transaction.copy(
                id = UUID.randomUUID().toString(),
                isSynced = false
            )

            // Save locally first
            val entity = mapper.domainToEntity(localTransaction)
            transactionDao.insert(entity)

            // Try to sync immediately (non-blocking)
            trySyncTransaction(entity)

            Result.success(localTransaction)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun updateTransaction(
        transaction: Transaction
    ): Result<Transaction> = withContext(ioDispatcher) {
        try {
            val updatedTransaction = transaction.copy(
                isSynced = false,
                updatedAt = Instant.now()
            )

            val entity = mapper.domainToEntity(updatedTransaction)
            transactionDao.update(entity)

            // Try to sync
            trySyncTransaction(entity)

            Result.success(updatedTransaction)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun deleteTransaction(id: String): Result<Unit> = withContext(ioDispatcher) {
        try {
            val transaction = transactionDao.getTransaction(id)

            // Delete locally
            transactionDao.delete(id)

            // Try to delete on server
            transaction?.serverId?.let { serverId ->
                try {
                    apiService.deleteTransaction(serverId)
                } catch (e: Exception) {
                    // Server delete failed, but local is deleted
                    // Could queue for later deletion
                }
            }

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun syncTransactions(): Result<SyncResult> = withContext(ioDispatcher) {
        try {
            var pushed = 0
            var pulled = 0
            var conflicts = 0

            // Push unsynced local changes
            val unsyncedTransactions = transactionDao.getUnsyncedTransactions()
            for (entity in unsyncedTransactions) {
                try {
                    val response = if (entity.serverId == null) {
                        apiService.createTransaction(mapper.entityToDto(entity))
                    } else {
                        apiService.updateTransaction(entity.serverId, mapper.entityToDto(entity))
                    }

                    if (response.isSuccessful) {
                        val serverId = response.body()?.id ?: entity.serverId
                        if (serverId != null) {
                            transactionDao.markSynced(entity.id, serverId)
                            pushed++
                        }
                    }
                } catch (e: Exception) {
                    // Individual sync failure, continue with others
                }
            }

            // Pull remote changes
            val remoteResponse = apiService.getTransactions()
            if (remoteResponse.isSuccessful) {
                val remoteTransactions = remoteResponse.body()?.data ?: emptyList()

                for (dto in remoteTransactions) {
                    val existingEntity = transactionDao.getTransaction(dto.id)

                    if (existingEntity == null) {
                        // New remote transaction
                        val entity = mapper.dtoToEntity(dto, userId)
                        transactionDao.insert(entity)
                        pulled++
                    } else if (!existingEntity.isSynced) {
                        // Conflict: local has changes, remote has changes
                        // Strategy: Server wins (can be customized)
                        val entity = mapper.dtoToEntity(dto, userId)
                        transactionDao.insert(entity)
                        conflicts++
                    }
                }
            }

            Result.success(SyncResult(pushed, pulled, conflicts))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private suspend fun trySyncTransaction(entity: TransactionEntity) {
        try {
            val response = if (entity.serverId == null) {
                apiService.createTransaction(mapper.entityToDto(entity))
            } else {
                apiService.updateTransaction(entity.serverId, mapper.entityToDto(entity))
            }

            if (response.isSuccessful) {
                val serverId = response.body()?.id
                if (serverId != null) {
                    transactionDao.markSynced(entity.id, serverId)
                }
            }
        } catch (e: Exception) {
            // Sync will happen later
        }
    }
}

/**
 * Sync result data class.
 */
data class SyncResult(
    val pushed: Int,
    val pulled: Int,
    val conflicts: Int
)
```

---

## 6. Presentation Layer

### ViewModel Template

```kotlin
/**
 * TransactionListViewModel - ViewModel for transaction list screen.
 *
 * Responsibilities:
 * - Manage UI state
 * - Handle user actions
 * - Coordinate with use cases
 * - Emit one-time events
 */
@HiltViewModel
class TransactionListViewModel @Inject constructor(
    private val getTransactionsUseCase: GetTransactionsUseCase,
    private val deleteTransactionUseCase: DeleteTransactionUseCase,
    private val syncDataUseCase: SyncDataUseCase,
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {

    // ==========================================================================
    // STATE
    // ==========================================================================

    private val _uiState = MutableStateFlow(TransactionListUiState())
    val uiState: StateFlow<TransactionListUiState> = _uiState.asStateFlow()

    private val _events = Channel<TransactionListEvent>(Channel.BUFFERED)
    val events: Flow<TransactionListEvent> = _events.receiveAsFlow()

    // ==========================================================================
    // INITIALIZATION
    // ==========================================================================

    init {
        loadTransactions()
    }

    // ==========================================================================
    // PUBLIC METHODS
    // ==========================================================================

    /**
     * Load transactions from repository.
     */
    fun loadTransactions() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            getTransactionsUseCase()
                .catch { e ->
                    _uiState.update {
                        it.copy(isLoading = false, error = e.message)
                    }
                }
                .collect { transactions ->
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            transactions = transactions,
                            error = null
                        )
                    }
                }
        }
    }

    /**
     * Delete a transaction.
     */
    fun deleteTransaction(id: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isDeleting = true) }

            deleteTransactionUseCase(id)
                .onSuccess {
                    _events.send(TransactionListEvent.TransactionDeleted)
                }
                .onFailure { e ->
                    _events.send(TransactionListEvent.Error(e.message ?: "Delete failed"))
                }

            _uiState.update { it.copy(isDeleting = false) }
        }
    }

    /**
     * Sync transactions with server.
     */
    fun sync() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSyncing = true) }

            syncDataUseCase.syncTransactions()
                .onSuccess { result ->
                    _events.send(TransactionListEvent.SyncCompleted(result))
                }
                .onFailure { e ->
                    _events.send(TransactionListEvent.Error(e.message ?: "Sync failed"))
                }

            _uiState.update { it.copy(isSyncing = false) }
        }
    }

    /**
     * Filter transactions by type.
     */
    fun setTypeFilter(type: TransactionType?) {
        _uiState.update { it.copy(selectedType = type) }
    }

    /**
     * Filter transactions by category.
     */
    fun setCategoryFilter(category: TransactionCategory?) {
        _uiState.update { it.copy(selectedCategory = category) }
    }
}

/**
 * UI state for transaction list screen.
 */
data class TransactionListUiState(
    val isLoading: Boolean = false,
    val isDeleting: Boolean = false,
    val isSyncing: Boolean = false,
    val transactions: List<Transaction> = emptyList(),
    val error: String? = null,
    val selectedType: TransactionType? = null,
    val selectedCategory: TransactionCategory? = null
) {
    /**
     * Filtered transactions based on current filters.
     */
    val filteredTransactions: List<Transaction>
        get() = transactions
            .filter { selectedType == null || it.type == selectedType }
            .filter { selectedCategory == null || it.category == selectedCategory }
}

/**
 * One-time events for transaction list screen.
 */
sealed class TransactionListEvent {
    object TransactionDeleted : TransactionListEvent()
    data class SyncCompleted(val result: SyncResult) : TransactionListEvent()
    data class Error(val message: String) : TransactionListEvent()
}
```

### Compose Screen Template

```kotlin
/**
 * TransactionListScreen - Composable for displaying transaction list.
 *
 * Features:
 * - Pull-to-refresh
 * - Filtering by type/category
 * - Swipe to delete
 * - Loading and error states
 */
@Composable
fun TransactionListScreen(
    viewModel: TransactionListViewModel = hiltViewModel(),
    onTransactionClick: (String) -> Unit,
    onAddClick: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current

    // Handle one-time events
    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is TransactionListEvent.TransactionDeleted -> {
                    Toast.makeText(
                        context,
                        "Transaction deleted",
                        Toast.LENGTH_SHORT
                    ).show()
                }
                is TransactionListEvent.SyncCompleted -> {
                    Toast.makeText(
                        context,
                        "Synced: ${event.result.pushed} up, ${event.result.pulled} down",
                        Toast.LENGTH_SHORT
                    ).show()
                }
                is TransactionListEvent.Error -> {
                    Toast.makeText(
                        context,
                        event.message,
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }

    TransactionListContent(
        uiState = uiState,
        onTransactionClick = onTransactionClick,
        onAddClick = onAddClick,
        onRefresh = viewModel::loadTransactions,
        onSync = viewModel::sync,
        onDelete = viewModel::deleteTransaction,
        onTypeFilterChange = viewModel::setTypeFilter,
        onCategoryFilterChange = viewModel::setCategoryFilter
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TransactionListContent(
    uiState: TransactionListUiState,
    onTransactionClick: (String) -> Unit,
    onAddClick: () -> Unit,
    onRefresh: () -> Unit,
    onSync: () -> Unit,
    onDelete: (String) -> Unit,
    onTypeFilterChange: (TransactionType?) -> Unit,
    onCategoryFilterChange: (TransactionCategory?) -> Unit
) {
    val pullRefreshState = rememberPullToRefreshState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Transactions") },
                actions = {
                    IconButton(onClick = onSync, enabled = !uiState.isSyncing) {
                        if (uiState.isSyncing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(Icons.Default.Sync, contentDescription = "Sync")
                        }
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = onAddClick) {
                Icon(Icons.Default.Add, contentDescription = "Add Transaction")
            }
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .pullToRefresh(
                    state = pullRefreshState,
                    isRefreshing = uiState.isLoading,
                    onRefresh = onRefresh
                )
        ) {
            when {
                uiState.isLoading && uiState.transactions.isEmpty() -> {
                    LoadingIndicator(modifier = Modifier.align(Alignment.Center))
                }
                uiState.error != null && uiState.transactions.isEmpty() -> {
                    ErrorMessage(
                        message = uiState.error,
                        onRetry = onRefresh,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                uiState.filteredTransactions.isEmpty() -> {
                    EmptyState(
                        message = "No transactions yet",
                        actionLabel = "Add your first transaction",
                        onAction = onAddClick,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                else -> {
                    TransactionList(
                        transactions = uiState.filteredTransactions,
                        onTransactionClick = onTransactionClick,
                        onDelete = onDelete
                    )
                }
            }

            PullToRefreshContainer(
                state = pullRefreshState,
                modifier = Modifier.align(Alignment.TopCenter)
            )
        }
    }
}

@Composable
private fun TransactionList(
    transactions: List<Transaction>,
    onTransactionClick: (String) -> Unit,
    onDelete: (String) -> Unit
) {
    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(
            items = transactions,
            key = { it.id }
        ) { transaction ->
            TransactionCard(
                transaction = transaction,
                onClick = { onTransactionClick(transaction.id) },
                onDelete = { onDelete(transaction.id) }
            )
        }
    }
}
```

### Composable Component Template

```kotlin
/**
 * TransactionCard - Reusable card component for displaying a transaction.
 *
 * Features:
 * - Category icon
 * - Amount with color coding
 * - Swipe to delete
 * - Click handling
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionCard(
    transaction: Transaction,
    onClick: () -> Unit,
    onDelete: () -> Unit,
    modifier: Modifier = Modifier
) {
    val dismissState = rememberSwipeToDismissBoxState(
        confirmValueChange = { dismissValue ->
            if (dismissValue == SwipeToDismissBoxValue.EndToStart) {
                onDelete()
                true
            } else {
                false
            }
        }
    )

    SwipeToDismissBox(
        state = dismissState,
        backgroundContent = {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.error)
                    .padding(horizontal = 16.dp),
                contentAlignment = Alignment.CenterEnd
            ) {
                Icon(
                    imageVector = Icons.Default.Delete,
                    contentDescription = "Delete",
                    tint = MaterialTheme.colorScheme.onError
                )
            }
        },
        content = {
            Card(
                onClick = onClick,
                modifier = modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Category icon and description
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CategoryIcon(category = transaction.category)

                        Column {
                            Text(
                                text = transaction.description.ifEmpty {
                                    transaction.category.displayName
                                },
                                style = MaterialTheme.typography.bodyLarge,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )

                            Text(
                                text = transaction.date.format(
                                    DateTimeFormatter.ofPattern("MMM d, yyyy")
                                ),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    // Amount
                    AmountText(
                        amount = transaction.signedAmount,
                        type = transaction.type
                    )
                }
            }
        }
    )
}

/**
 * AmountText - Formatted amount with color coding.
 */
@Composable
fun AmountText(
    amount: BigDecimal,
    type: TransactionType,
    modifier: Modifier = Modifier
) {
    val color = when (type) {
        TransactionType.INCOME -> MaterialTheme.colorScheme.primary
        TransactionType.EXPENSE -> MaterialTheme.colorScheme.error
        TransactionType.TRANSFER -> MaterialTheme.colorScheme.tertiary
    }

    val prefix = when (type) {
        TransactionType.INCOME -> "+"
        TransactionType.EXPENSE -> "-"
        TransactionType.TRANSFER -> ""
    }

    Text(
        text = "$prefix${NumberFormat.getCurrencyInstance().format(amount.abs())}",
        style = MaterialTheme.typography.titleMedium,
        color = color,
        fontWeight = FontWeight.SemiBold,
        modifier = modifier
    )
}
```

---

## 7. Navigation

### Route Definition

```kotlin
/**
 * Route - Sealed class defining all navigation routes.
 *
 * Uses type-safe navigation with argument support.
 */
sealed class Route(val route: String) {

    // ==========================================================================
    // AUTH ROUTES
    // ==========================================================================

    object Login : Route("login")
    object Register : Route("register")
    object ForgotPassword : Route("forgot_password")

    // ==========================================================================
    // MAIN ROUTES
    // ==========================================================================

    object Dashboard : Route("dashboard")
    object Transactions : Route("transactions")
    object Budgets : Route("budgets")
    object Settings : Route("settings")

    // ==========================================================================
    // DETAIL ROUTES
    // ==========================================================================

    object TransactionDetail : Route("transaction/{transactionId}") {
        fun createRoute(transactionId: String) = "transaction/$transactionId"
    }

    object TransactionForm : Route("transaction/form?transactionId={transactionId}") {
        fun createRoute(transactionId: String? = null) =
            if (transactionId != null) "transaction/form?transactionId=$transactionId"
            else "transaction/form"
    }

    object BudgetDetail : Route("budget/{budgetId}") {
        fun createRoute(budgetId: String) = "budget/$budgetId"
    }

    // ==========================================================================
    // NESTED GRAPHS
    // ==========================================================================

    object AuthGraph : Route("auth_graph")
    object MainGraph : Route("main_graph")
}
```

### Navigation Graph

```kotlin
/**
 * AppNavGraph - Main navigation graph.
 *
 * Defines all navigation destinations and their transitions.
 */
@Composable
fun AppNavGraph(
    navController: NavHostController,
    startDestination: String = Route.AuthGraph.route
) {
    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {
        // Auth graph
        navigation(
            startDestination = Route.Login.route,
            route = Route.AuthGraph.route
        ) {
            composable(Route.Login.route) {
                LoginScreen(
                    onLoginSuccess = {
                        navController.navigate(Route.MainGraph.route) {
                            popUpTo(Route.AuthGraph.route) { inclusive = true }
                        }
                    },
                    onRegisterClick = {
                        navController.navigate(Route.Register.route)
                    },
                    onForgotPasswordClick = {
                        navController.navigate(Route.ForgotPassword.route)
                    }
                )
            }

            composable(Route.Register.route) {
                RegisterScreen(
                    onRegisterSuccess = {
                        navController.navigate(Route.MainGraph.route) {
                            popUpTo(Route.AuthGraph.route) { inclusive = true }
                        }
                    },
                    onBackClick = { navController.popBackStack() }
                )
            }
        }

        // Main graph
        navigation(
            startDestination = Route.Dashboard.route,
            route = Route.MainGraph.route
        ) {
            composable(Route.Dashboard.route) {
                DashboardScreen(
                    onTransactionClick = { id ->
                        navController.navigate(Route.TransactionDetail.createRoute(id))
                    },
                    onViewAllTransactions = {
                        navController.navigate(Route.Transactions.route)
                    }
                )
            }

            composable(Route.Transactions.route) {
                TransactionListScreen(
                    onTransactionClick = { id ->
                        navController.navigate(Route.TransactionDetail.createRoute(id))
                    },
                    onAddClick = {
                        navController.navigate(Route.TransactionForm.createRoute())
                    }
                )
            }

            composable(
                route = Route.TransactionDetail.route,
                arguments = listOf(
                    navArgument("transactionId") { type = NavType.StringType }
                )
            ) { backStackEntry ->
                val transactionId = backStackEntry.arguments?.getString("transactionId")
                    ?: return@composable

                TransactionDetailScreen(
                    transactionId = transactionId,
                    onBackClick = { navController.popBackStack() },
                    onEditClick = {
                        navController.navigate(Route.TransactionForm.createRoute(transactionId))
                    }
                )
            }

            composable(
                route = Route.TransactionForm.route,
                arguments = listOf(
                    navArgument("transactionId") {
                        type = NavType.StringType
                        nullable = true
                        defaultValue = null
                    }
                )
            ) { backStackEntry ->
                val transactionId = backStackEntry.arguments?.getString("transactionId")

                TransactionFormScreen(
                    transactionId = transactionId,
                    onSaveSuccess = { navController.popBackStack() },
                    onBackClick = { navController.popBackStack() }
                )
            }

            composable(Route.Settings.route) {
                SettingsScreen(
                    onLogout = {
                        navController.navigate(Route.AuthGraph.route) {
                            popUpTo(Route.MainGraph.route) { inclusive = true }
                        }
                    }
                )
            }
        }
    }
}
```

---

## 8. Error Handling

```kotlin
/**
 * FinanceAppException - Base exception for application errors.
 */
sealed class FinanceAppException(
    override val message: String,
    val code: String
) : Exception(message) {

    /**
     * Network-related errors.
     */
    data class NetworkException(
        override val message: String = "Network error"
    ) : FinanceAppException(message, "NETWORK_ERROR")

    /**
     * Authentication errors.
     */
    data class AuthException(
        override val message: String = "Authentication failed"
    ) : FinanceAppException(message, "AUTH_ERROR")

    /**
     * Validation errors.
     */
    data class ValidationException(
        override val message: String,
        val field: String? = null
    ) : FinanceAppException(message, "VALIDATION_ERROR")

    /**
     * Server errors.
     */
    data class ServerException(
        override val message: String,
        val statusCode: Int
    ) : FinanceAppException(message, "SERVER_ERROR")

    /**
     * Database errors.
     */
    data class DatabaseException(
        override val message: String = "Database error"
    ) : FinanceAppException(message, "DATABASE_ERROR")

    /**
     * Sync errors.
     */
    data class SyncException(
        override val message: String = "Sync failed"
    ) : FinanceAppException(message, "SYNC_ERROR")
}

/**
 * Extension to convert exceptions to user-friendly messages.
 */
fun Throwable.toUserMessage(): String {
    return when (this) {
        is FinanceAppException.NetworkException -> "Please check your internet connection"
        is FinanceAppException.AuthException -> "Please log in again"
        is FinanceAppException.ValidationException -> message
        is FinanceAppException.ServerException -> "Server error. Please try again later"
        is FinanceAppException.DatabaseException -> "Error saving data"
        is FinanceAppException.SyncException -> "Sync failed. Will retry later"
        else -> "An unexpected error occurred"
    }
}
```

---

## 9. Testing Standards

### Unit Test Template

```kotlin
/**
 * TransactionRepositoryTest - Unit tests for TransactionRepository.
 */
@ExperimentalCoroutinesApi
class TransactionRepositoryImplTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private lateinit var repository: TransactionRepositoryImpl
    private lateinit var transactionDao: FakeTransactionDao
    private lateinit var apiService: FakeApiService
    private lateinit var mapper: TransactionMapper

    @Before
    fun setup() {
        transactionDao = FakeTransactionDao()
        apiService = FakeApiService()
        mapper = TransactionMapper()

        repository = TransactionRepositoryImpl(
            transactionDao = transactionDao,
            apiService = apiService,
            mapper = mapper,
            tokenStorage = FakeTokenStorage(),
            ioDispatcher = mainDispatcherRule.testDispatcher
        )
    }

    @Test
    fun `getTransactions returns flow of transactions`() = runTest {
        // Arrange
        val entities = listOf(
            createTransactionEntity(id = "1", amount = 100.0),
            createTransactionEntity(id = "2", amount = 200.0)
        )
        transactionDao.setTransactions(entities)

        // Act
        val result = repository.getTransactions().first()

        // Assert
        assertEquals(2, result.size)
        assertEquals(BigDecimal("100.00"), result[0].amount)
    }

    @Test
    fun `createTransaction saves locally and syncs`() = runTest {
        // Arrange
        val transaction = createTransaction(amount = BigDecimal("150.00"))
        apiService.shouldSucceed = true

        // Act
        val result = repository.createTransaction(transaction)

        // Assert
        assertTrue(result.isSuccess)
        assertEquals(1, transactionDao.getInsertedCount())
    }

    @Test
    fun `createTransaction handles network failure gracefully`() = runTest {
        // Arrange
        val transaction = createTransaction(amount = BigDecimal("150.00"))
        apiService.shouldSucceed = false

        // Act
        val result = repository.createTransaction(transaction)

        // Assert
        assertTrue(result.isSuccess) // Local save should succeed
        assertEquals(1, transactionDao.getInsertedCount())
        // Should be marked as unsynced
        val saved = transactionDao.getTransaction(result.getOrNull()!!.id)
        assertFalse(saved!!.isSynced)
    }
}
```

### ViewModel Test Template

```kotlin
/**
 * TransactionListViewModelTest - Unit tests for TransactionListViewModel.
 */
@ExperimentalCoroutinesApi
class TransactionListViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private lateinit var viewModel: TransactionListViewModel
    private lateinit var getTransactionsUseCase: FakeGetTransactionsUseCase
    private lateinit var deleteTransactionUseCase: FakeDeleteTransactionUseCase

    @Before
    fun setup() {
        getTransactionsUseCase = FakeGetTransactionsUseCase()
        deleteTransactionUseCase = FakeDeleteTransactionUseCase()

        viewModel = TransactionListViewModel(
            getTransactionsUseCase = getTransactionsUseCase,
            deleteTransactionUseCase = deleteTransactionUseCase,
            syncDataUseCase = FakeSyncDataUseCase(),
            savedStateHandle = SavedStateHandle()
        )
    }

    @Test
    fun `initial state is loading`() = runTest {
        assertTrue(viewModel.uiState.value.isLoading)
    }

    @Test
    fun `loadTransactions updates state with transactions`() = runTest {
        // Arrange
        val transactions = listOf(
            createTransaction(id = "1"),
            createTransaction(id = "2")
        )
        getTransactionsUseCase.setTransactions(transactions)

        // Act
        viewModel.loadTransactions()
        advanceUntilIdle()

        // Assert
        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertEquals(2, state.transactions.size)
        assertNull(state.error)
    }

    @Test
    fun `deleteTransaction emits success event`() = runTest {
        // Arrange
        deleteTransactionUseCase.shouldSucceed = true
        val events = mutableListOf<TransactionListEvent>()
        val job = launch { viewModel.events.toList(events) }

        // Act
        viewModel.deleteTransaction("1")
        advanceUntilIdle()

        // Assert
        assertTrue(events.any { it is TransactionListEvent.TransactionDeleted })

        job.cancel()
    }
}
```

---

## 10. Security Guidelines

### Sensitive Data Handling

```kotlin
/**
 * Security best practices for mobile app.
 */
object SecurityConfig {

    /**
     * Data that should NEVER be logged.
     */
    val SENSITIVE_FIELDS = setOf(
        "password",
        "access_token",
        "refresh_token",
        "pin",
        "cvv",
        "card_number"
    )

    /**
     * Check if a field name is sensitive.
     */
    fun isSensitive(fieldName: String): Boolean {
        return SENSITIVE_FIELDS.any { fieldName.contains(it, ignoreCase = true) }
    }
}

/**
 * Secure logging that filters sensitive data.
 */
object SecureLog {

    fun d(tag: String, message: String) {
        if (BuildConfig.DEBUG) {
            Log.d(tag, sanitize(message))
        }
    }

    fun i(tag: String, message: String) {
        Log.i(tag, sanitize(message))
    }

    fun e(tag: String, message: String, throwable: Throwable? = null) {
        Log.e(tag, sanitize(message), throwable)
    }

    private fun sanitize(message: String): String {
        var sanitized = message
        SecurityConfig.SENSITIVE_FIELDS.forEach { field ->
            sanitized = sanitized.replace(
                Regex("(?i)$field[\"']?\\s*[:=]\\s*[\"']?[^\"'\\s,}]+"),
                "$field=[REDACTED]"
            )
        }
        return sanitized
    }
}
```

### Network Security Config

```xml
<!-- res/xml/network_security_config.xml -->
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <!-- Disable cleartext traffic -->
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>

    <!-- Production API with certificate pinning -->
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">api.financeapp.com</domain>
        <pin-set expiration="2027-01-01">
            <!-- Primary pin -->
            <pin digest="SHA-256">AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=</pin>
            <!-- Backup pin -->
            <pin digest="SHA-256">BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=</pin>
        </pin-set>
    </domain-config>

    <!-- Debug overrides -->
    <debug-overrides>
        <trust-anchors>
            <certificates src="user" />
        </trust-anchors>
    </debug-overrides>
</network-security-config>
```

---

## 11. Build Configuration

### build.gradle.kts (App Module)

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.dagger.hilt.android")
    id("com.google.devtools.ksp")
    kotlin("plugin.serialization")
}

android {
    namespace = "com.financeapp"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.financeapp"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            isDebuggable = true
            applicationIdSuffix = ".debug"
        }

        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.01.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.7.6")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.50")
    ksp("com.google.dagger:hilt-compiler:2.50")

    // Room
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Security
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
    testImplementation("io.mockk:mockk:1.13.9")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}
```

---

## 12. Code Style

### Kotlin Style Guidelines

| Rule | Example |
|------|---------|
| Max line length | 120 characters |
| Indentation | 4 spaces |
| Trailing commas | Always use |
| Explicit return types | For public functions |
| Named arguments | For functions with 3+ params |

### Compose Guidelines

| Rule | Description |
|------|-------------|
| Stateless composables | Prefer stateless over stateful |
| Preview functions | Provide for all UI components |
| Modifier parameter | Always first optional param |
| Default modifier | `Modifier = Modifier` |

### Documentation Requirements

| Element | Required |
|---------|----------|
| Public classes | KDoc with description |
| Public functions | KDoc with @param/@return |
| Complex logic | Inline comments |
| ViewModels | State and event documentation |
| Use cases | Business logic explanation |

---

**This document is MANDATORY for all Android development in FinanceApp.**

*Last reviewed: 2026-01-28*
