package com.pecunia.domain.usecases

import com.pecunia.domain.repository.SyncRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import java.time.Instant
import javax.inject.Inject

/**
 * Use case for synchronizing data between local storage and remote server.
 * Handles offline-first data synchronization strategy.
 */
class SyncDataUseCase @Inject constructor(
    private val syncRepository: SyncRepository
) {
    /**
     * Invoke operator to perform data synchronization.
     *
     * @param params Parameters specifying synchronization behavior.
     * @return Flow of Result containing sync state updates.
     */
    operator fun invoke(params: Params = Params.SyncAll): Flow<Result<SyncState>> = flow {
        try {
            emit(Result.success(SyncState.Syncing))

            val result = when (params) {
                is Params.SyncAll -> syncRepository.syncAll()
                is Params.SyncTransactions -> syncRepository.syncTransactions()
                is Params.SyncBudgets -> syncRepository.syncBudgets()
                is Params.SyncUserPreferences -> syncRepository.syncUserPreferences()
                is Params.ForcePush -> syncRepository.forcePushChanges()
                is Params.ForcePull -> syncRepository.forcePullChanges()
                is Params.ResolveConflicts -> syncRepository.resolveConflicts(
                    params.conflicts,
                    params.resolution
                )
            }

            if (result.success) {
                emit(Result.success(
                    SyncState.Completed(
                        itemsSynced = result.itemsSynced,
                        itemsFailed = result.itemsFailed,
                        timestamp = result.timestamp,
                        conflicts = result.conflicts
                    )
                ))
            } else {
                emit(Result.success(
                    SyncState.Error(
                        message = result.errorMessage ?: "Sync failed",
                        conflicts = result.conflicts
                    )
                ))
            }
        } catch (e: Exception) {
            emit(Result.success(SyncState.Error(e.message ?: "Unknown error occurred")))
        }
    }

    /**
     * Get current sync status as a Flow.
     *
     * @return Flow of sync status updates.
     */
    fun observeSyncStatus(): Flow<Result<SyncStatusInfo>> {
        return syncRepository.getSyncStatus()
            .map { state ->
                Result.success(
                    SyncStatusInfo(
                        state = state,
                        lastSyncTime = syncRepository.getLastSyncTime(),
                        pendingCount = syncRepository.getPendingSyncCount(),
                        isAutoSyncEnabled = syncRepository.isAutoSyncEnabled()
                    )
                )
            }
            .catch { exception ->
                emit(Result.failure(exception))
            }
    }

    /**
     * Parameters for synchronization operation.
     */
    sealed class Params {
        data object SyncAll : Params()
        data object SyncTransactions : Params()
        data object SyncBudgets : Params()
        data object SyncUserPreferences : Params()
        data object ForcePush : Params()
        data object ForcePull : Params()
        data class ResolveConflicts(
            val conflicts: List<SyncConflict>,
            val resolution: ConflictResolution
        ) : Params()
    }

    /**
     * Represents the current state of synchronization.
     */
    sealed class SyncState {
        data object Idle : SyncState()
        data object Syncing : SyncState()
        data class Progress(val current: Int, val total: Int) : SyncState()
        data class Error(
            val message: String,
            val conflicts: List<SyncConflict> = emptyList()
        ) : SyncState()
        data class Completed(
            val itemsSynced: Int,
            val itemsFailed: Int,
            val timestamp: Instant,
            val conflicts: List<SyncConflict> = emptyList()
        ) : SyncState()
    }

    /**
     * Detailed sync status information.
     */
    data class SyncStatusInfo(
        val state: RepositorySyncState,
        val lastSyncTime: Instant?,
        val pendingCount: Int,
        val isAutoSyncEnabled: Boolean
    )
}

/**
 * Result of a sync operation from repository.
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

/**
 * Sync state from repository layer.
 */
sealed class RepositorySyncState {
    data object Idle : RepositorySyncState()
    data object Syncing : RepositorySyncState()
    data class Progress(val current: Int, val total: Int) : RepositorySyncState()
    data class Error(val message: String) : RepositorySyncState()
    data object Completed : RepositorySyncState()
}
