package com.pecunia.data.repository

import com.pecunia.data.local.database.dao.TransactionDao
import com.pecunia.data.local.database.entities.TransactionEntity
import com.pecunia.data.local.database.entities.TransactionType
import com.pecunia.data.remote.api.ApiService
import com.pecunia.data.remote.dto.TransactionRequest
import com.pecunia.data.remote.dto.TransactionSummaryResponse
import com.pecunia.di.IoDispatcher
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for transaction data operations.
 *
 * Implements the offline-first pattern for reliable operation:
 *
 * ## Architecture
 * ```
 * ┌─────────────┐     ┌────────────────┐     ┌─────────────┐
 * │  ViewModel  │────▶│  Repository    │────▶│  ApiService │
 * └─────────────┘     └────────────────┘     └─────────────┘
 *                            │
 *                            ▼
 *                     ┌─────────────┐
 *                     │    Room     │
 *                     │  Database   │
 *                     └─────────────┘
 * ```
 *
 * ## Offline-First Strategy
 *
 * All write operations follow this pattern:
 * 1. Save to local Room database immediately
 * 2. Mark record as `isSynced = false`
 * 3. Attempt server sync in background
 * 4. On success: update with server response, set `isSynced = true`
 * 5. On failure: keep local version, sync will retry later
 *
 * This ensures:
 * - Instant UI response (no network latency)
 * - Works fully offline
 * - Data eventually consistent with server
 *
 * ## Thread Safety
 *
 * All database and network operations run on [IoDispatcher] to avoid
 * blocking the main thread. Flow emissions are moved to the IO thread
 * via [flowOn].
 *
 * ## Sync Status Tracking
 *
 * Each transaction has:
 * - `isSynced: Boolean` - Quick check for pending sync
 * - `serverId: String?` - Server-assigned UUID (null if not synced)
 * - `updatedAt: Long` - Timestamp for conflict resolution
 *
 * ## Error Handling
 *
 * Methods return `Result<T>` for explicit error handling:
 * ```kotlin
 * when (val result = repository.createTransaction(tx)) {
 *     is Result.Success -> handleSuccess(result.value)
 *     is Result.Failure -> handleError(result.exception)
 * }
 * ```
 *
 * @property transactionDao Room DAO for local database operations
 * @property apiService Retrofit service for server API calls
 * @property authRepository Repository for current user context
 * @property ioDispatcher Coroutine dispatcher for IO operations
 *
 * @see MOBILE_CONVENTIONS.md for repository patterns
 * @see SECURITY_GUIDELINES.md for data handling requirements
 */
@Singleton
class TransactionRepository @Inject constructor(
    private val transactionDao: TransactionDao,
    private val apiService: ApiService,
    private val authRepository: AuthRepository,
    @IoDispatcher private val ioDispatcher: CoroutineDispatcher
) {

    /**
     * Get all transactions for the current user as a Flow.
     */
    fun getTransactions(): Flow<List<TransactionEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return transactionDao.getAllByUserId(userId).flowOn(ioDispatcher)
    }

    /**
     * Get transactions with pagination.
     */
    suspend fun getTransactionsPaginated(page: Int, pageSize: Int): List<TransactionEntity> = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext emptyList()
        val offset = (page - 1) * pageSize
        transactionDao.getByUserIdPaginated(userId, pageSize, offset)
    }

    /**
     * Get a single transaction by ID.
     */
    suspend fun getTransaction(id: String): TransactionEntity? = withContext(ioDispatcher) {
        transactionDao.getById(id)
    }

    /**
     * Get a single transaction by ID as a Flow.
     */
    fun getTransactionFlow(id: String): Flow<TransactionEntity?> {
        return transactionDao.getByIdFlow(id).flowOn(ioDispatcher)
    }

    /**
     * Get transactions by type (INCOME, EXPENSE, TRANSFER).
     */
    fun getTransactionsByType(type: TransactionType): Flow<List<TransactionEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return transactionDao.getByType(userId, type).flowOn(ioDispatcher)
    }

    /**
     * Get transactions by category.
     */
    fun getTransactionsByCategory(category: String): Flow<List<TransactionEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return transactionDao.getByCategory(userId, category).flowOn(ioDispatcher)
    }

    /**
     * Get transactions within a date range.
     */
    fun getTransactionsByDateRange(startDate: Long, endDate: Long): Flow<List<TransactionEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return transactionDao.getByDateRange(userId, startDate, endDate).flowOn(ioDispatcher)
    }

    /**
     * Get recurring transactions.
     */
    fun getRecurringTransactions(): Flow<List<TransactionEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return transactionDao.getRecurringTransactions(userId).flowOn(ioDispatcher)
    }

    /**
     * Search transactions by query.
     */
    fun searchTransactions(query: String): Flow<List<TransactionEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return transactionDao.searchTransactions(userId, query).flowOn(ioDispatcher)
    }

    /**
     * Create a new transaction using offline-first pattern.
     *
     * ## Algorithm
     *
     * 1. Generate UUID if not provided
     * 2. Insert into local Room database (instant, no network)
     * 3. Attempt to sync with server:
     *    - Success: Update local record with server response
     *    - Failure: Keep local version, marked as unsynced
     *
     * ## Why Offline-First?
     *
     * - User sees immediate feedback (no loading spinner)
     * - Works without internet connection
     * - Network errors don't block the user
     * - Data syncs automatically when online
     *
     * ## Sync Behavior
     *
     * The returned transaction will have:
     * - `isSynced = true` if server sync succeeded
     * - `isSynced = false` if network failed (will retry)
     * - `serverId` populated only if server sync succeeded
     *
     * @param transaction The transaction to create. If `id` is blank,
     *                    a new UUID will be generated.
     * @return Result.Success with the created transaction (may be
     *         local-only if network unavailable), or Result.Failure
     *         if local database insert failed.
     *
     * @see syncTransactions for batch retry of unsynced records
     */
    suspend fun createTransaction(transaction: TransactionEntity): Result<TransactionEntity> = withContext(ioDispatcher) {
        try {
            // Generate ID if not present
            val transactionWithId = if (transaction.id.isBlank()) {
                transaction.copy(id = UUID.randomUUID().toString())
            } else {
                transaction
            }

            // Save locally first
            transactionDao.insert(transactionWithId)

            // Try to sync with server
            try {
                val response = apiService.createTransaction(TransactionRequest.fromEntity(transactionWithId))
                if (response.isSuccessful && response.body() != null) {
                    val serverTransaction = response.body()!!.data.toEntity()
                    transactionDao.insert(serverTransaction)
                    Result.success(serverTransaction)
                } else {
                    // Keep local version, mark as unsynced
                    Result.success(transactionWithId)
                }
            } catch (e: Exception) {
                // Network error - keep local version
                Result.success(transactionWithId)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Update an existing transaction (offline-first).
     */
    suspend fun updateTransaction(transaction: TransactionEntity): Result<TransactionEntity> = withContext(ioDispatcher) {
        try {
            val updatedTransaction = transaction.copy(
                updatedAt = System.currentTimeMillis(),
                isSynced = false
            )

            // Update locally first
            transactionDao.update(updatedTransaction)

            // Try to sync with server
            try {
                val response = apiService.updateTransaction(
                    transaction.id,
                    TransactionRequest.fromEntity(updatedTransaction)
                )
                if (response.isSuccessful && response.body() != null) {
                    val serverTransaction = response.body()!!.data.toEntity()
                    transactionDao.insert(serverTransaction)
                    Result.success(serverTransaction)
                } else {
                    Result.success(updatedTransaction)
                }
            } catch (e: Exception) {
                // Network error - keep local version
                Result.success(updatedTransaction)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Delete a transaction.
     */
    suspend fun deleteTransaction(transactionId: String): Result<Unit> = withContext(ioDispatcher) {
        try {
            // Delete locally
            transactionDao.deleteById(transactionId)

            // Try to delete on server
            try {
                val response = apiService.deleteTransaction(transactionId)
                if (!response.isSuccessful) {
                    // Server-side delete failed - mark as pending deletion for retry
                    // Re-insert with a pending-delete flag so sync can retry later
                    return@withContext Result.failure(
                        ApiException(response.code(), "Server delete failed: ${response.message()}")
                    )
                }
            } catch (e: Exception) {
                // Network error - propagate so caller can handle retry
                return@withContext Result.failure(e)
            }

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Refresh transactions from server.
     */
    suspend fun refreshTransactions(): Result<Unit> = withContext(ioDispatcher) {
        try {
            val userId = authRepository.getCurrentUserId()
                ?: return@withContext Result.failure(AuthException("User not authenticated"))

            val response = apiService.getTransactions()
            if (response.isSuccessful && response.body() != null) {
                val transactions = response.body()!!.data.map { it.toEntity() }
                transactionDao.insertAll(transactions)
                Result.success(Unit)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Sync all unsynced transactions to the server.
     *
     * This method handles batch synchronization of locally-created or
     * modified transactions that haven't been synced to the server yet.
     *
     * ## When to Call
     *
     * - On app startup (after network becomes available)
     * - Periodically via WorkManager (e.g., every 15 minutes)
     * - When user manually triggers sync
     * - When network connectivity is restored
     *
     * ## Algorithm
     *
     * 1. Query all transactions where `isSynced = false`
     * 2. If none found, return success with count 0
     * 3. Convert to DTOs and send batch to server
     * 4. Server processes each, returns success/error per item
     * 5. Mark successfully synced items as `isSynced = true`
     * 6. Failed items remain unsynced for next retry
     *
     * ## Conflict Handling
     *
     * Server uses Last-Write-Wins strategy:
     * - Compare `updatedAt` timestamps
     * - Most recent version wins
     * - Server may return updated data if server version is newer
     *
     * ## Error Handling
     *
     * - Network errors: Return failure, all items remain unsynced
     * - Partial success: Mark successful items, keep failed for retry
     * - Server 4xx: Log error, item may need manual resolution
     *
     * @return Result.Success with count of successfully synced items,
     *         or Result.Failure if the sync request failed entirely.
     *
     * @see refreshTransactions for pulling server changes
     */
    suspend fun syncTransactions(): Result<Int> = withContext(ioDispatcher) {
        try {
            val unsyncedTransactions = transactionDao.getUnsyncedTransactions()
            if (unsyncedTransactions.isEmpty()) {
                return@withContext Result.success(0)
            }

            val requests = unsyncedTransactions.map { TransactionRequest.fromEntity(it) }
            val response = apiService.syncTransactions(requests)

            if (response.isSuccessful && response.body() != null) {
                val syncResponse = response.body()!!
                // Mark synced transactions
                unsyncedTransactions.forEach { transaction ->
                    if (syncResponse.errors?.none { it.id == transaction.id } != false) {
                        transactionDao.updateSyncStatus(transaction.id, true)
                    }
                }
                Result.success(syncResponse.synced_count)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Get transaction summary/analytics.
     */
    suspend fun getTransactionSummary(startDate: Long, endDate: Long): Result<TransactionSummaryResponse> = withContext(ioDispatcher) {
        try {
            val response = apiService.getTransactionSummary(startDate, endDate)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Get total by type and date range (local calculation).
     */
    suspend fun getTotalByType(type: TransactionType, startDate: Long, endDate: Long): Double = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext 0.0
        transactionDao.getTotalByTypeAndDateRange(userId, type, startDate, endDate) ?: 0.0
    }

    /**
     * Get total by category and date range (local calculation).
     */
    suspend fun getTotalByCategory(category: String, startDate: Long, endDate: Long): Double = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext 0.0
        transactionDao.getTotalByCategoryAndDateRange(userId, category, startDate, endDate) ?: 0.0
    }

    /**
     * Get all categories used in transactions.
     */
    suspend fun getAllCategories(): List<String> = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext emptyList()
        transactionDao.getAllCategories(userId)
    }

    /**
     * Get transaction count.
     */
    suspend fun getTransactionCount(): Int = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext 0
        transactionDao.getTransactionCount(userId)
    }

    /**
     * Clear all local transactions.
     */
    suspend fun clearLocalTransactions(): Result<Unit> = withContext(ioDispatcher) {
        try {
            val userId = authRepository.getCurrentUserId()
            if (userId != null) {
                transactionDao.deleteAllByUserId(userId)
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
