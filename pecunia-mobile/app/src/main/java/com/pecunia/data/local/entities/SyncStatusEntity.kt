package com.pecunia.data.local.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

/**
 * Entity for tracking synchronization status of local data with the remote server.
 * Supports offline-first architecture with conflict resolution tracking.
 */
@Entity(
    tableName = "sync_status",
    indices = [
        Index(value = ["entity_type"]),
        Index(value = ["entity_id"]),
        Index(value = ["sync_state"]),
        Index(value = ["entity_type", "entity_id"], unique = true),
        Index(value = ["last_sync_attempt"]),
        Index(value = ["user_id"])
    ],
    foreignKeys = [
        ForeignKey(
            entity = UserEntity::class,
            parentColumns = ["id"],
            childColumns = ["user_id"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE
        )
    ]
)
data class SyncStatusEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "user_id")
    val userId: UUID,

    @ColumnInfo(name = "entity_type")
    val entityType: EntityType,

    @ColumnInfo(name = "entity_id")
    val entityId: UUID,

    @ColumnInfo(name = "sync_state")
    val syncState: SyncState,

    @ColumnInfo(name = "local_version")
    val localVersion: Long = 1,

    @ColumnInfo(name = "remote_version")
    val remoteVersion: Long? = null,

    @ColumnInfo(name = "last_sync_attempt")
    val lastSyncAttempt: Long? = null,

    @ColumnInfo(name = "last_successful_sync")
    val lastSuccessfulSync: Long? = null,

    @ColumnInfo(name = "retry_count")
    val retryCount: Int = 0,

    @ColumnInfo(name = "max_retries")
    val maxRetries: Int = 3,

    @ColumnInfo(name = "error_code")
    val errorCode: String? = null,

    @ColumnInfo(name = "error_message")
    val errorMessage: String? = null,

    @ColumnInfo(name = "conflict_data")
    val conflictData: String? = null, // JSON containing both versions for conflict resolution

    @ColumnInfo(name = "pending_operation")
    val pendingOperation: PendingOperation,

    @ColumnInfo(name = "priority")
    val priority: SyncPriority = SyncPriority.NORMAL,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis()
) {
    /**
     * Enum representing the type of entity being synced.
     */
    enum class EntityType {
        USER,
        TRANSACTION,
        BUDGET,
        CATEGORY,
        BANK_ACCOUNT,
        BANK_CONNECTION,
        BUDGET_CATEGORY,
        GOAL,
        NOTIFICATION_PREFERENCE
    }

    /**
     * Enum representing the current sync state.
     */
    enum class SyncState {
        PENDING,          // Awaiting sync
        IN_PROGRESS,      // Currently syncing
        SYNCED,           // Successfully synced
        FAILED,           // Sync failed, will retry
        CONFLICT,         // Version conflict detected
        ABANDONED         // Max retries exceeded
    }

    /**
     * Enum representing the pending operation type.
     */
    enum class PendingOperation {
        CREATE,
        UPDATE,
        DELETE,
        NONE
    }

    /**
     * Enum representing sync priority levels.
     */
    enum class SyncPriority {
        LOW,
        NORMAL,
        HIGH,
        CRITICAL
    }

    /**
     * Checks if the entity needs to be synced.
     */
    fun needsSync(): Boolean =
        syncState == SyncState.PENDING ||
        syncState == SyncState.FAILED ||
        syncState == SyncState.CONFLICT

    /**
     * Checks if sync has failed and can be retried.
     */
    fun canRetry(): Boolean =
        syncState == SyncState.FAILED && retryCount < maxRetries

    /**
     * Checks if sync has been abandoned due to too many failures.
     */
    fun isAbandoned(): Boolean = syncState == SyncState.ABANDONED

    /**
     * Checks if there is a conflict that needs resolution.
     */
    fun hasConflict(): Boolean = syncState == SyncState.CONFLICT

    /**
     * Checks if the entity is currently syncing.
     */
    fun isSyncing(): Boolean = syncState == SyncState.IN_PROGRESS

    /**
     * Checks if the entity is successfully synced.
     */
    fun isSynced(): Boolean = syncState == SyncState.SYNCED

    /**
     * Checks if the local version is ahead of remote.
     */
    fun isLocalAhead(): Boolean =
        remoteVersion?.let { localVersion > it } ?: true

    /**
     * Calculates the next retry delay using exponential backoff.
     */
    fun getNextRetryDelayMs(): Long {
        val baseDelay = 1000L // 1 second
        val maxDelay = 5 * 60 * 1000L // 5 minutes
        val delay = baseDelay * (1 shl retryCount.coerceAtMost(10))
        return delay.coerceAtMost(maxDelay)
    }

    companion object {
        /**
         * Creates a new sync status for a newly created entity.
         */
        fun createForNewEntity(
            userId: UUID,
            entityType: EntityType,
            entityId: UUID,
            priority: SyncPriority = SyncPriority.NORMAL
        ): SyncStatusEntity = SyncStatusEntity(
            userId = userId,
            entityType = entityType,
            entityId = entityId,
            syncState = SyncState.PENDING,
            pendingOperation = PendingOperation.CREATE,
            priority = priority
        )

        /**
         * Creates a sync status for an updated entity.
         */
        fun createForUpdate(
            userId: UUID,
            entityType: EntityType,
            entityId: UUID,
            currentVersion: Long,
            priority: SyncPriority = SyncPriority.NORMAL
        ): SyncStatusEntity = SyncStatusEntity(
            userId = userId,
            entityType = entityType,
            entityId = entityId,
            syncState = SyncState.PENDING,
            localVersion = currentVersion + 1,
            pendingOperation = PendingOperation.UPDATE,
            priority = priority
        )

        /**
         * Creates a sync status for a deleted entity.
         */
        fun createForDelete(
            userId: UUID,
            entityType: EntityType,
            entityId: UUID,
            priority: SyncPriority = SyncPriority.HIGH
        ): SyncStatusEntity = SyncStatusEntity(
            userId = userId,
            entityType = entityType,
            entityId = entityId,
            syncState = SyncState.PENDING,
            pendingOperation = PendingOperation.DELETE,
            priority = priority
        )

        /**
         * Creates a copy marked as in progress.
         */
        fun SyncStatusEntity.markAsInProgress(): SyncStatusEntity =
            copy(
                syncState = SyncState.IN_PROGRESS,
                lastSyncAttempt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )

        /**
         * Creates a copy marked as synced.
         */
        fun SyncStatusEntity.markAsSynced(newRemoteVersion: Long): SyncStatusEntity =
            copy(
                syncState = SyncState.SYNCED,
                remoteVersion = newRemoteVersion,
                lastSuccessfulSync = System.currentTimeMillis(),
                retryCount = 0,
                errorCode = null,
                errorMessage = null,
                conflictData = null,
                pendingOperation = PendingOperation.NONE,
                updatedAt = System.currentTimeMillis()
            )

        /**
         * Creates a copy marked as failed.
         */
        fun SyncStatusEntity.markAsFailed(
            errorCode: String?,
            errorMessage: String?
        ): SyncStatusEntity {
            val newRetryCount = retryCount + 1
            val newState = if (newRetryCount >= maxRetries) {
                SyncState.ABANDONED
            } else {
                SyncState.FAILED
            }
            return copy(
                syncState = newState,
                retryCount = newRetryCount,
                errorCode = errorCode,
                errorMessage = errorMessage,
                updatedAt = System.currentTimeMillis()
            )
        }

        /**
         * Creates a copy marked as having a conflict.
         */
        fun SyncStatusEntity.markAsConflict(
            conflictData: String,
            remoteVersion: Long
        ): SyncStatusEntity =
            copy(
                syncState = SyncState.CONFLICT,
                remoteVersion = remoteVersion,
                conflictData = conflictData,
                updatedAt = System.currentTimeMillis()
            )

        /**
         * Creates a copy with conflict resolved (local wins).
         */
        fun SyncStatusEntity.resolveConflictWithLocal(): SyncStatusEntity =
            copy(
                syncState = SyncState.PENDING,
                localVersion = localVersion + 1,
                conflictData = null,
                retryCount = 0,
                updatedAt = System.currentTimeMillis()
            )

        /**
         * Creates a copy with conflict resolved (remote wins).
         */
        fun SyncStatusEntity.resolveConflictWithRemote(): SyncStatusEntity =
            copy(
                syncState = SyncState.SYNCED,
                conflictData = null,
                retryCount = 0,
                pendingOperation = PendingOperation.NONE,
                updatedAt = System.currentTimeMillis()
            )
    }
}

/**
 * Entity for tracking the overall sync queue status.
 * Provides a summary of pending sync operations.
 */
@Entity(
    tableName = "sync_queue_status",
    indices = [
        Index(value = ["user_id"], unique = true)
    ],
    foreignKeys = [
        ForeignKey(
            entity = UserEntity::class,
            parentColumns = ["id"],
            childColumns = ["user_id"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE
        )
    ]
)
data class SyncQueueStatusEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "user_id")
    val userId: UUID,

    @ColumnInfo(name = "pending_count")
    val pendingCount: Int = 0,

    @ColumnInfo(name = "failed_count")
    val failedCount: Int = 0,

    @ColumnInfo(name = "conflict_count")
    val conflictCount: Int = 0,

    @ColumnInfo(name = "is_syncing")
    val isSyncing: Boolean = false,

    @ColumnInfo(name = "last_full_sync")
    val lastFullSync: Long? = null,

    @ColumnInfo(name = "next_scheduled_sync")
    val nextScheduledSync: Long? = null,

    @ColumnInfo(name = "is_offline_mode")
    val isOfflineMode: Boolean = false,

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis()
) {
    /**
     * Checks if there are any pending operations.
     */
    fun hasPendingOperations(): Boolean = pendingCount > 0

    /**
     * Checks if there are any issues requiring attention.
     */
    fun hasIssues(): Boolean = failedCount > 0 || conflictCount > 0

    /**
     * Gets the total number of items requiring sync.
     */
    fun getTotalPendingItems(): Int = pendingCount + failedCount

    /**
     * Checks if the sync is overdue (more than 1 hour since last sync).
     */
    fun isSyncOverdue(currentTime: Long = System.currentTimeMillis()): Boolean {
        val oneHour = 60 * 60 * 1000L
        return lastFullSync?.let { (currentTime - it) > oneHour } ?: true
    }

    companion object {
        /**
         * Creates initial sync queue status for a new user.
         */
        fun createForUser(userId: UUID): SyncQueueStatusEntity =
            SyncQueueStatusEntity(userId = userId)
    }
}
