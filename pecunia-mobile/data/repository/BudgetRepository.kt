package com.pecunia.data.repository

import com.pecunia.data.local.database.dao.BudgetDao
import com.pecunia.data.local.database.entities.BudgetEntity
import com.pecunia.data.local.database.entities.BudgetPeriodType
import com.pecunia.data.remote.api.ApiService
import com.pecunia.data.remote.dto.BudgetRequest
import com.pecunia.data.remote.dto.BudgetSummaryResponse
import com.pecunia.data.remote.dto.UpdateSpentAmountRequest
import com.pecunia.di.IoDispatcher
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository handling budget operations.
 * Implements offline-first approach with local database caching.
 */
@Singleton
class BudgetRepository @Inject constructor(
    private val budgetDao: BudgetDao,
    private val apiService: ApiService,
    private val authRepository: AuthRepository,
    @IoDispatcher private val ioDispatcher: CoroutineDispatcher
) {

    /**
     * Get all budgets for the current user as a Flow.
     */
    fun getBudgets(): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getAllByUserId(userId).flowOn(ioDispatcher)
    }

    /**
     * Get active budgets only.
     */
    fun getActiveBudgets(): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getActiveBudgets(userId).flowOn(ioDispatcher)
    }

    /**
     * Get inactive (archived) budgets.
     */
    fun getInactiveBudgets(): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getInactiveBudgets(userId).flowOn(ioDispatcher)
    }

    /**
     * Get a single budget by ID.
     */
    suspend fun getBudget(id: String): BudgetEntity? = withContext(ioDispatcher) {
        budgetDao.getById(id)
    }

    /**
     * Get a single budget by ID as a Flow.
     */
    fun getBudgetFlow(id: String): Flow<BudgetEntity?> {
        return budgetDao.getByIdFlow(id).flowOn(ioDispatcher)
    }

    /**
     * Get budgets by period type.
     */
    fun getBudgetsByPeriodType(periodType: BudgetPeriodType): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getByPeriodType(userId, periodType).flowOn(ioDispatcher)
    }

    /**
     * Get budgets by category.
     */
    fun getBudgetsByCategory(category: String): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getByCategory(userId, category).flowOn(ioDispatcher)
    }

    /**
     * Get active budget for a specific category.
     */
    suspend fun getActiveBudgetByCategory(category: String): BudgetEntity? = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext null
        budgetDao.getActiveBudgetByCategory(userId, category)
    }

    /**
     * Get current active budgets (within their date range).
     */
    fun getCurrentBudgets(): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getCurrentBudgets(userId, System.currentTimeMillis()).flowOn(ioDispatcher)
    }

    /**
     * Get budgets that are over their alert threshold.
     */
    fun getBudgetsOverThreshold(): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getBudgetsOverThreshold(userId).flowOn(ioDispatcher)
    }

    /**
     * Get budgets that have exceeded their limit.
     */
    fun getExceededBudgets(): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.getExceededBudgets(userId).flowOn(ioDispatcher)
    }

    /**
     * Search budgets by query.
     */
    fun searchBudgets(query: String): Flow<List<BudgetEntity>> {
        val userId = authRepository.getCurrentUserId() ?: return kotlinx.coroutines.flow.flowOf(emptyList())
        return budgetDao.searchBudgets(userId, query).flowOn(ioDispatcher)
    }

    /**
     * Create a new budget (offline-first).
     */
    suspend fun createBudget(budget: BudgetEntity): Result<BudgetEntity> = withContext(ioDispatcher) {
        try {
            // Generate ID if not present
            val budgetWithId = if (budget.id.isBlank()) {
                budget.copy(id = UUID.randomUUID().toString())
            } else {
                budget
            }

            // Save locally first
            budgetDao.insert(budgetWithId)

            // Try to sync with server
            try {
                val response = apiService.createBudget(BudgetRequest.fromEntity(budgetWithId))
                if (response.isSuccessful && response.body() != null) {
                    val serverBudget = response.body()!!.data.toEntity()
                    budgetDao.insert(serverBudget)
                    Result.success(serverBudget)
                } else {
                    // Keep local version, mark as unsynced
                    Result.success(budgetWithId)
                }
            } catch (e: Exception) {
                // Network error - keep local version
                Result.success(budgetWithId)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Update an existing budget (offline-first).
     */
    suspend fun updateBudget(budget: BudgetEntity): Result<BudgetEntity> = withContext(ioDispatcher) {
        try {
            val updatedBudget = budget.copy(
                updatedAt = System.currentTimeMillis(),
                isSynced = false
            )

            // Update locally first
            budgetDao.update(updatedBudget)

            // Try to sync with server
            try {
                val response = apiService.updateBudget(
                    budget.id,
                    BudgetRequest.fromEntity(updatedBudget)
                )
                if (response.isSuccessful && response.body() != null) {
                    val serverBudget = response.body()!!.data.toEntity()
                    budgetDao.insert(serverBudget)
                    Result.success(serverBudget)
                } else {
                    Result.success(updatedBudget)
                }
            } catch (e: Exception) {
                // Network error - keep local version
                Result.success(updatedBudget)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Update spent amount for a budget.
     */
    suspend fun updateSpentAmount(budgetId: String, spentAmount: Double): Result<BudgetEntity> = withContext(ioDispatcher) {
        try {
            // Update locally first
            budgetDao.updateSpentAmount(budgetId, spentAmount)

            // Try to sync with server
            try {
                val response = apiService.updateBudgetSpentAmount(
                    budgetId,
                    UpdateSpentAmountRequest(spentAmount)
                )
                if (response.isSuccessful && response.body() != null) {
                    val serverBudget = response.body()!!.data.toEntity()
                    budgetDao.insert(serverBudget)
                    Result.success(serverBudget)
                } else {
                    val localBudget = budgetDao.getById(budgetId)
                        ?: return@withContext Result.failure(Exception("Budget not found: $budgetId"))
                    Result.success(localBudget)
                }
            } catch (e: Exception) {
                val localBudget = budgetDao.getById(budgetId)
                    ?: return@withContext Result.failure(Exception("Budget not found: $budgetId"))
                Result.success(localBudget)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Add amount to spent (increment spent amount).
     */
    suspend fun addToSpentAmount(budgetId: String, amount: Double): Result<BudgetEntity> = withContext(ioDispatcher) {
        try {
            val budget = budgetDao.getById(budgetId)
                ?: return@withContext Result.failure(Exception("Budget not found"))

            val newSpentAmount = budget.spentAmount + amount
            updateSpentAmount(budgetId, newSpentAmount)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Toggle budget active status.
     */
    suspend fun toggleBudgetActive(budgetId: String): Result<BudgetEntity> = withContext(ioDispatcher) {
        try {
            val budget = budgetDao.getById(budgetId)
                ?: return@withContext Result.failure(Exception("Budget not found"))

            val newActiveStatus = !budget.isActive
            budgetDao.updateActiveStatus(budgetId, newActiveStatus)

            val updatedBudget = budgetDao.getById(budgetId)
            Result.success(updatedBudget!!)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Delete a budget.
     */
    suspend fun deleteBudget(budgetId: String): Result<Unit> = withContext(ioDispatcher) {
        try {
            // Delete locally
            budgetDao.deleteById(budgetId)

            // Try to delete on server
            try {
                apiService.deleteBudget(budgetId)
            } catch (e: Exception) {
                // Ignore network errors - already deleted locally
            }

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Refresh budgets from server.
     */
    suspend fun refreshBudgets(): Result<Unit> = withContext(ioDispatcher) {
        try {
            val userId = authRepository.getCurrentUserId()
                ?: return@withContext Result.failure(AuthException("User not authenticated"))

            val response = apiService.getBudgets()
            if (response.isSuccessful && response.body() != null) {
                val budgets = response.body()!!.data.map { it.toEntity() }
                budgetDao.insertAll(budgets)
                Result.success(Unit)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Sync unsynced budgets to server.
     */
    suspend fun syncBudgets(): Result<Int> = withContext(ioDispatcher) {
        try {
            val unsyncedBudgets = budgetDao.getUnsyncedBudgets()
            if (unsyncedBudgets.isEmpty()) {
                return@withContext Result.success(0)
            }

            val requests = unsyncedBudgets.map { BudgetRequest.fromEntity(it) }
            val response = apiService.syncBudgets(requests)

            if (response.isSuccessful && response.body() != null) {
                val syncResponse = response.body()!!
                // Mark synced budgets
                unsyncedBudgets.forEach { budget ->
                    if (syncResponse.errors?.none { it.id == budget.id } != false) {
                        budgetDao.updateSyncStatus(budget.id, true)
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
     * Get budget summary/overview.
     */
    suspend fun getBudgetSummary(): Result<BudgetSummaryResponse> = withContext(ioDispatcher) {
        try {
            val response = apiService.getBudgetSummary()
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
     * Get total budgeted amount (local calculation).
     */
    suspend fun getTotalBudgetAmount(): Double = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext 0.0
        budgetDao.getTotalBudgetAmount(userId) ?: 0.0
    }

    /**
     * Get total spent amount across all budgets (local calculation).
     */
    suspend fun getTotalSpentAmount(): Double = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext 0.0
        budgetDao.getTotalSpentAmount(userId) ?: 0.0
    }

    /**
     * Get active budget count.
     */
    suspend fun getActiveBudgetCount(): Int = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext 0
        budgetDao.getActiveBudgetCount(userId)
    }

    /**
     * Get all categories used in budgets.
     */
    suspend fun getAllCategories(): List<String> = withContext(ioDispatcher) {
        val userId = authRepository.getCurrentUserId() ?: return@withContext emptyList()
        budgetDao.getAllCategories(userId)
    }

    /**
     * Clear all local budgets.
     */
    suspend fun clearLocalBudgets(): Result<Unit> = withContext(ioDispatcher) {
        try {
            val userId = authRepository.getCurrentUserId()
            if (userId != null) {
                budgetDao.deleteAllByUserId(userId)
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Reset all budgets' spent amounts to zero (for period rollover).
     */
    suspend fun resetAllSpentAmounts(): Result<Unit> = withContext(ioDispatcher) {
        try {
            val userId = authRepository.getCurrentUserId()
                ?: return@withContext Result.failure(AuthException("User not authenticated"))

            // Get all budgets for this user and reset spent amount for active ones
            val budgets = budgetDao.getAllByUserIdSync(userId)
            budgets.forEach { budget ->
                if (budget.isActive) {
                    budgetDao.updateSpentAmount(budget.id, 0.0)
                }
            }

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
