package com.pecunia.domain.usecases

import com.pecunia.domain.models.SyncStatus
import kotlinx.coroutines.flow.Flow
import java.time.Instant

/**
 * Use case for synchronizing data between local storage and remote server.
 */
class SyncDataUseCase(
    private val syncRepository: SyncRepository
) {
    /**
     * Perform a full sync of all data.
     */
    suspend fun syncAll(): SyncResult {
        return syncRepository.syncAll()
    }

    /**
     * Sync only transactions.
     */
    suspend fun syncTransactions(): SyncResult {
        return syncRepository.syncTransactions()
    }

    /**
     * Sync only budgets.
     */
    suspend fun syncBudgets(): SyncResult {
        return syncRepository.syncBudgets()
    }

    /**
     * Sync user preferences.
     */
    suspend fun syncUserPreferences(): SyncResult {
        return syncRepository.syncUserPreferences()
    }

    /**
     * Get current sync status.
     */
    fun getSyncStatus(): Flow<SyncState> {
        return syncRepository.getSyncStatus()
    }

    /**
     * Get last sync timestamp.
     */
    suspend fun getLastSyncTime(): Instant? {
        return syncRepository.getLastSyncTime()
    }

    /**
     * Get count of pending sync items.
     */
    suspend fun getPendingSyncCount(): Int {
        return syncRepository.getPendingSyncCount()
    }

    /**
     * Force push local changes to server.
     */
    suspend fun forcePushChanges(): SyncResult {
        return syncRepository.forcePushChanges()
    }

    /**
     * Force pull changes from server (overwrites local).
     */
    suspend fun forcePullChanges(): SyncResult {
        return syncRepository.forcePullChanges()
    }

    /**
     * Resolve sync conflicts.
     */
    suspend fun resolveConflicts(
        conflicts: List<SyncConflict>,
        resolution: ConflictResolution
    ): SyncResult {
        return syncRepository.resolveConflicts(conflicts, resolution)
    }

    /**
     * Cancel ongoing sync operation.
     */
    suspend fun cancelSync() {
        syncRepository.cancelSync()
    }

    /**
     * Enable or disable auto-sync.
     */
    suspend fun setAutoSyncEnabled(enabled: Boolean) {
        syncRepository.setAutoSyncEnabled(enabled)
    }

    /**
     * Check if auto-sync is enabled.
     */
    suspend fun isAutoSyncEnabled(): Boolean {
        return syncRepository.isAutoSyncEnabled()
    }
}

/**
 * Repository interface for sync operations.
 */
interface SyncRepository {
    suspend fun syncAll(): SyncResult
    suspend fun syncTransactions(): SyncResult
    suspend fun syncBudgets(): SyncResult
    suspend fun syncUserPreferences(): SyncResult
    fun getSyncStatus(): Flow<SyncState>
    suspend fun getLastSyncTime(): Instant?
    suspend fun getPendingSyncCount(): Int
    suspend fun forcePushChanges(): SyncResult
    suspend fun forcePullChanges(): SyncResult
    suspend fun resolveConflicts(conflicts: List<SyncConflict>, resolution: ConflictResolution): SyncResult
    suspend fun cancelSync()
    suspend fun setAutoSyncEnabled(enabled: Boolean)
    suspend fun isAutoSyncEnabled(): Boolean
}

/**
 * Represents the current state of synchronization.
 */
sealed class SyncState {
    object Idle : SyncState()
    object Syncing : SyncState()
    data class Progress(val current: Int, val total: Int) : SyncState()
    data class Error(val message: String) : SyncState()
    object Completed : SyncState()
}

/**
 * Result of a sync operation.
 */
data class SyncResult(
    val success: Boolean,
    val itemsSynced: Int = 0,
    val itemsFailed: Int = 0,
    val conflicts: List<SyncConflict> = emptyList(),
    val errorMessage: String? = null,
    val timestamp: Instant = Instant.now()
)

/**
 * Represents a sync conflict between local and remote data.
 */
data class SyncConflict(
    val entityType: SyncEntityType,
    val entityId: String,
    val localVersion: String,
    val remoteVersion: String,
    val localTimestamp: Instant,
    val remoteTimestamp: Instant
)

/**
 * Type of entity being synced.
 */
enum class SyncEntityType {
    TRANSACTION,
    BUDGET,
    USER_PREFERENCES
}

/**
 * Resolution strategy for sync conflicts.
 */
enum class ConflictResolution {
    KEEP_LOCAL,
    KEEP_REMOTE,
    KEEP_NEWEST,
    MERGE
}
