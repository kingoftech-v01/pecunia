package com.pecunia.domain.usecases

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Test
import java.time.Instant

/**
 * Comprehensive unit tests for SyncDataUseCase.
 *
 * Tests the Params sealed class, SyncState sealed class, SyncStatusInfo,
 * SyncResult, SyncConflict, SyncEntityType enum, ConflictResolution enum,
 * and RepositorySyncState sealed class.
 *
 * Since SyncRepository interface is not present in the codebase,
 * we test all the data types, enums, and flow behavior patterns
 * that can be verified without that dependency.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class SyncDataUseCaseTest {

    // ============================================
    // Params Tests
    // ============================================

    @Test
    fun `Params SyncAll is singleton`() {
        assertSame(SyncDataUseCase.Params.SyncAll, SyncDataUseCase.Params.SyncAll)
    }

    @Test
    fun `Params SyncTransactions is singleton`() {
        assertSame(SyncDataUseCase.Params.SyncTransactions, SyncDataUseCase.Params.SyncTransactions)
    }

    @Test
    fun `Params SyncBudgets is singleton`() {
        assertSame(SyncDataUseCase.Params.SyncBudgets, SyncDataUseCase.Params.SyncBudgets)
    }

    @Test
    fun `Params SyncUserPreferences is singleton`() {
        assertSame(SyncDataUseCase.Params.SyncUserPreferences, SyncDataUseCase.Params.SyncUserPreferences)
    }

    @Test
    fun `Params ForcePush is singleton`() {
        assertSame(SyncDataUseCase.Params.ForcePush, SyncDataUseCase.Params.ForcePush)
    }

    @Test
    fun `Params ForcePull is singleton`() {
        assertSame(SyncDataUseCase.Params.ForcePull, SyncDataUseCase.Params.ForcePull)
    }

    @Test
    fun `Params ResolveConflicts carries conflicts and resolution`() {
        val conflict = SyncConflict(
            entityType = SyncEntityType.TRANSACTION,
            entityId = "tx-1",
            localVersion = "v1",
            remoteVersion = "v2",
            localTimestamp = Instant.now().minusSeconds(60),
            remoteTimestamp = Instant.now()
        )
        val params = SyncDataUseCase.Params.ResolveConflicts(
            conflicts = listOf(conflict),
            resolution = ConflictResolution.KEEP_LOCAL
        )
        assertEquals(1, params.conflicts.size)
        assertEquals(ConflictResolution.KEEP_LOCAL, params.resolution)
    }

    @Test
    fun `Params ResolveConflicts with multiple conflicts`() {
        val conflicts = listOf(
            SyncConflict(
                entityType = SyncEntityType.TRANSACTION,
                entityId = "tx-1",
                localVersion = "v1",
                remoteVersion = "v2",
                localTimestamp = Instant.now(),
                remoteTimestamp = Instant.now()
            ),
            SyncConflict(
                entityType = SyncEntityType.BUDGET,
                entityId = "b-1",
                localVersion = "v3",
                remoteVersion = "v4",
                localTimestamp = Instant.now(),
                remoteTimestamp = Instant.now()
            )
        )
        val params = SyncDataUseCase.Params.ResolveConflicts(
            conflicts = conflicts,
            resolution = ConflictResolution.KEEP_NEWEST
        )
        assertEquals(2, params.conflicts.size)
    }

    @Test
    fun `all Params types are Params instances`() {
        val allParams: List<SyncDataUseCase.Params> = listOf(
            SyncDataUseCase.Params.SyncAll,
            SyncDataUseCase.Params.SyncTransactions,
            SyncDataUseCase.Params.SyncBudgets,
            SyncDataUseCase.Params.SyncUserPreferences,
            SyncDataUseCase.Params.ForcePush,
            SyncDataUseCase.Params.ForcePull,
            SyncDataUseCase.Params.ResolveConflicts(
                conflicts = emptyList(),
                resolution = ConflictResolution.MERGE
            )
        )
        assertEquals(7, allParams.size)
        assertTrue(allParams.all { it is SyncDataUseCase.Params })
    }

    // ============================================
    // SyncState Tests
    // ============================================

    @Test
    fun `SyncState Idle is singleton`() {
        assertSame(SyncDataUseCase.SyncState.Idle, SyncDataUseCase.SyncState.Idle)
    }

    @Test
    fun `SyncState Syncing is singleton`() {
        assertSame(SyncDataUseCase.SyncState.Syncing, SyncDataUseCase.SyncState.Syncing)
    }

    @Test
    fun `SyncState Progress holds current and total`() {
        val progress = SyncDataUseCase.SyncState.Progress(current = 5, total = 10)
        assertEquals(5, progress.current)
        assertEquals(10, progress.total)
    }

    @Test
    fun `SyncState Error holds message`() {
        val error = SyncDataUseCase.SyncState.Error(message = "Network error")
        assertEquals("Network error", error.message)
    }

    @Test
    fun `SyncState Error default conflicts is empty`() {
        val error = SyncDataUseCase.SyncState.Error(message = "Error")
        assertTrue(error.conflicts.isEmpty())
    }

    @Test
    fun `SyncState Error with conflicts`() {
        val conflict = SyncConflict(
            entityType = SyncEntityType.TRANSACTION,
            entityId = "tx-1",
            localVersion = "v1",
            remoteVersion = "v2",
            localTimestamp = Instant.now(),
            remoteTimestamp = Instant.now()
        )
        val error = SyncDataUseCase.SyncState.Error(
            message = "Conflict detected",
            conflicts = listOf(conflict)
        )
        assertEquals(1, error.conflicts.size)
    }

    @Test
    fun `SyncState Completed holds all fields`() {
        val timestamp = Instant.now()
        val completed = SyncDataUseCase.SyncState.Completed(
            itemsSynced = 10,
            itemsFailed = 2,
            timestamp = timestamp,
            conflicts = emptyList()
        )
        assertEquals(10, completed.itemsSynced)
        assertEquals(2, completed.itemsFailed)
        assertEquals(timestamp, completed.timestamp)
        assertTrue(completed.conflicts.isEmpty())
    }

    @Test
    fun `SyncState Completed default conflicts is empty`() {
        val completed = SyncDataUseCase.SyncState.Completed(
            itemsSynced = 5,
            itemsFailed = 0,
            timestamp = Instant.now()
        )
        assertTrue(completed.conflicts.isEmpty())
    }

    @Test
    fun `SyncState Completed with conflicts`() {
        val conflict = SyncConflict(
            entityType = SyncEntityType.BUDGET,
            entityId = "b-1",
            localVersion = "v1",
            remoteVersion = "v2",
            localTimestamp = Instant.now(),
            remoteTimestamp = Instant.now()
        )
        val completed = SyncDataUseCase.SyncState.Completed(
            itemsSynced = 8,
            itemsFailed = 1,
            timestamp = Instant.now(),
            conflicts = listOf(conflict)
        )
        assertEquals(1, completed.conflicts.size)
    }

    @Test
    fun `all SyncState types are SyncState instances`() {
        val allStates: List<SyncDataUseCase.SyncState> = listOf(
            SyncDataUseCase.SyncState.Idle,
            SyncDataUseCase.SyncState.Syncing,
            SyncDataUseCase.SyncState.Progress(0, 10),
            SyncDataUseCase.SyncState.Error("err"),
            SyncDataUseCase.SyncState.Completed(0, 0, Instant.now())
        )
        assertEquals(5, allStates.size)
    }

    // ============================================
    // SyncStatusInfo Tests
    // ============================================

    @Test
    fun `SyncStatusInfo holds all fields`() {
        val timestamp = Instant.now()
        val info = SyncDataUseCase.SyncStatusInfo(
            state = RepositorySyncState.Idle,
            lastSyncTime = timestamp,
            pendingCount = 5,
            isAutoSyncEnabled = true
        )
        assertTrue(info.state is RepositorySyncState.Idle)
        assertEquals(timestamp, info.lastSyncTime)
        assertEquals(5, info.pendingCount)
        assertTrue(info.isAutoSyncEnabled)
    }

    @Test
    fun `SyncStatusInfo with null lastSyncTime`() {
        val info = SyncDataUseCase.SyncStatusInfo(
            state = RepositorySyncState.Idle,
            lastSyncTime = null,
            pendingCount = 0,
            isAutoSyncEnabled = false
        )
        assertNull(info.lastSyncTime)
    }

    @Test
    fun `SyncStatusInfo with syncing state`() {
        val info = SyncDataUseCase.SyncStatusInfo(
            state = RepositorySyncState.Syncing,
            lastSyncTime = Instant.now(),
            pendingCount = 3,
            isAutoSyncEnabled = true
        )
        assertTrue(info.state is RepositorySyncState.Syncing)
    }

    @Test
    fun `SyncStatusInfo equality works`() {
        val time = Instant.now()
        val i1 = SyncDataUseCase.SyncStatusInfo(
            state = RepositorySyncState.Idle,
            lastSyncTime = time,
            pendingCount = 5,
            isAutoSyncEnabled = true
        )
        val i2 = SyncDataUseCase.SyncStatusInfo(
            state = RepositorySyncState.Idle,
            lastSyncTime = time,
            pendingCount = 5,
            isAutoSyncEnabled = true
        )
        assertEquals(i1, i2)
    }

    // ============================================
    // SyncResult Tests
    // ============================================

    @Test
    fun `SyncResult successful with defaults`() {
        val result = SyncResult(success = true)
        assertTrue(result.success)
        assertEquals(0, result.itemsSynced)
        assertEquals(0, result.itemsFailed)
        assertTrue(result.conflicts.isEmpty())
        assertNull(result.errorMessage)
    }

    @Test
    fun `SyncResult successful with items`() {
        val result = SyncResult(
            success = true,
            itemsSynced = 10,
            itemsFailed = 0
        )
        assertTrue(result.success)
        assertEquals(10, result.itemsSynced)
        assertEquals(0, result.itemsFailed)
    }

    @Test
    fun `SyncResult failed with error message`() {
        val result = SyncResult(
            success = false,
            errorMessage = "Network error"
        )
        assertFalse(result.success)
        assertEquals("Network error", result.errorMessage)
    }

    @Test
    fun `SyncResult with conflicts`() {
        val conflict = SyncConflict(
            entityType = SyncEntityType.TRANSACTION,
            entityId = "tx-1",
            localVersion = "v1",
            remoteVersion = "v2",
            localTimestamp = Instant.now(),
            remoteTimestamp = Instant.now()
        )
        val result = SyncResult(
            success = false,
            conflicts = listOf(conflict),
            errorMessage = "Conflicts found"
        )
        assertEquals(1, result.conflicts.size)
    }

    @Test
    fun `SyncResult timestamp defaults to now`() {
        val before = Instant.now()
        val result = SyncResult(success = true)
        val after = Instant.now()
        assertTrue(!result.timestamp.isBefore(before))
        assertTrue(!result.timestamp.isAfter(after))
    }

    @Test
    fun `SyncResult equality works`() {
        val time = Instant.now()
        val r1 = SyncResult(success = true, itemsSynced = 5, timestamp = time)
        val r2 = SyncResult(success = true, itemsSynced = 5, timestamp = time)
        assertEquals(r1, r2)
    }

    // ============================================
    // SyncConflict Tests
    // ============================================

    @Test
    fun `SyncConflict holds all fields`() {
        val localTime = Instant.now().minusSeconds(120)
        val remoteTime = Instant.now()
        val conflict = SyncConflict(
            entityType = SyncEntityType.TRANSACTION,
            entityId = "tx-42",
            localVersion = "local-v1",
            remoteVersion = "remote-v2",
            localTimestamp = localTime,
            remoteTimestamp = remoteTime
        )
        assertEquals(SyncEntityType.TRANSACTION, conflict.entityType)
        assertEquals("tx-42", conflict.entityId)
        assertEquals("local-v1", conflict.localVersion)
        assertEquals("remote-v2", conflict.remoteVersion)
        assertEquals(localTime, conflict.localTimestamp)
        assertEquals(remoteTime, conflict.remoteTimestamp)
    }

    @Test
    fun `SyncConflict with BUDGET entity type`() {
        val conflict = SyncConflict(
            entityType = SyncEntityType.BUDGET,
            entityId = "b-1",
            localVersion = "v1",
            remoteVersion = "v2",
            localTimestamp = Instant.now(),
            remoteTimestamp = Instant.now()
        )
        assertEquals(SyncEntityType.BUDGET, conflict.entityType)
    }

    @Test
    fun `SyncConflict with USER_PREFERENCES entity type`() {
        val conflict = SyncConflict(
            entityType = SyncEntityType.USER_PREFERENCES,
            entityId = "pref-1",
            localVersion = "v1",
            remoteVersion = "v2",
            localTimestamp = Instant.now(),
            remoteTimestamp = Instant.now()
        )
        assertEquals(SyncEntityType.USER_PREFERENCES, conflict.entityType)
    }

    @Test
    fun `SyncConflict equality works`() {
        val time = Instant.now()
        val c1 = SyncConflict(SyncEntityType.TRANSACTION, "tx-1", "v1", "v2", time, time)
        val c2 = SyncConflict(SyncEntityType.TRANSACTION, "tx-1", "v1", "v2", time, time)
        assertEquals(c1, c2)
    }

    @Test
    fun `SyncConflict inequality on entityId`() {
        val time = Instant.now()
        val c1 = SyncConflict(SyncEntityType.TRANSACTION, "tx-1", "v1", "v2", time, time)
        val c2 = SyncConflict(SyncEntityType.TRANSACTION, "tx-2", "v1", "v2", time, time)
        assertNotEquals(c1, c2)
    }

    // ============================================
    // SyncEntityType Tests
    // ============================================

    @Test
    fun `SyncEntityType has three values`() {
        assertEquals(3, SyncEntityType.entries.size)
    }

    @Test
    fun `SyncEntityType TRANSACTION exists`() {
        assertNotNull(SyncEntityType.TRANSACTION)
    }

    @Test
    fun `SyncEntityType BUDGET exists`() {
        assertNotNull(SyncEntityType.BUDGET)
    }

    @Test
    fun `SyncEntityType USER_PREFERENCES exists`() {
        assertNotNull(SyncEntityType.USER_PREFERENCES)
    }

    // ============================================
    // ConflictResolution Tests
    // ============================================

    @Test
    fun `ConflictResolution has four values`() {
        assertEquals(4, ConflictResolution.entries.size)
    }

    @Test
    fun `ConflictResolution KEEP_LOCAL exists`() {
        assertNotNull(ConflictResolution.KEEP_LOCAL)
    }

    @Test
    fun `ConflictResolution KEEP_REMOTE exists`() {
        assertNotNull(ConflictResolution.KEEP_REMOTE)
    }

    @Test
    fun `ConflictResolution KEEP_NEWEST exists`() {
        assertNotNull(ConflictResolution.KEEP_NEWEST)
    }

    @Test
    fun `ConflictResolution MERGE exists`() {
        assertNotNull(ConflictResolution.MERGE)
    }

    // ============================================
    // RepositorySyncState Tests
    // ============================================

    @Test
    fun `RepositorySyncState Idle is singleton`() {
        assertSame(RepositorySyncState.Idle, RepositorySyncState.Idle)
    }

    @Test
    fun `RepositorySyncState Syncing is singleton`() {
        assertSame(RepositorySyncState.Syncing, RepositorySyncState.Syncing)
    }

    @Test
    fun `RepositorySyncState Completed is singleton`() {
        assertSame(RepositorySyncState.Completed, RepositorySyncState.Completed)
    }

    @Test
    fun `RepositorySyncState Progress holds values`() {
        val progress = RepositorySyncState.Progress(current = 3, total = 10)
        assertEquals(3, progress.current)
        assertEquals(10, progress.total)
    }

    @Test
    fun `RepositorySyncState Error holds message`() {
        val error = RepositorySyncState.Error("Failed")
        assertEquals("Failed", error.message)
    }

    @Test
    fun `all RepositorySyncState types are RepositorySyncState instances`() {
        val allStates: List<RepositorySyncState> = listOf(
            RepositorySyncState.Idle,
            RepositorySyncState.Syncing,
            RepositorySyncState.Completed,
            RepositorySyncState.Progress(0, 5),
            RepositorySyncState.Error("err")
        )
        assertEquals(5, allStates.size)
    }

    // ============================================
    // Flow Emission Pattern Tests
    // ============================================

    @Test
    fun `sync flow emits Syncing then Completed on success`() = runTest {
        val syncFlow = flow {
            emit(Result.success(SyncDataUseCase.SyncState.Syncing as SyncDataUseCase.SyncState))
            emit(Result.success(
                SyncDataUseCase.SyncState.Completed(
                    itemsSynced = 10,
                    itemsFailed = 0,
                    timestamp = Instant.now()
                ) as SyncDataUseCase.SyncState
            ))
        }
        val results = syncFlow.toList()
        assertEquals(2, results.size)
        assertTrue(results[0].isSuccess)
        assertTrue(results[0].getOrNull() is SyncDataUseCase.SyncState.Syncing)
        assertTrue(results[1].isSuccess)
        assertTrue(results[1].getOrNull() is SyncDataUseCase.SyncState.Completed)
    }

    @Test
    fun `sync flow emits Syncing then Error on failure`() = runTest {
        val syncFlow = flow {
            emit(Result.success(SyncDataUseCase.SyncState.Syncing as SyncDataUseCase.SyncState))
            emit(Result.success(
                SyncDataUseCase.SyncState.Error("Sync failed") as SyncDataUseCase.SyncState
            ))
        }
        val results = syncFlow.toList()
        assertEquals(2, results.size)
        val lastState = results[1].getOrNull()
        assertTrue(lastState is SyncDataUseCase.SyncState.Error)
        assertEquals("Sync failed", (lastState as SyncDataUseCase.SyncState.Error).message)
    }

    @Test
    fun `sync flow handles exception by emitting Error state`() = runTest {
        val syncFlow = flow {
            emit(Result.success(SyncDataUseCase.SyncState.Syncing as SyncDataUseCase.SyncState))
            // Simulate catching an exception
            try {
                throw RuntimeException("Connection lost")
            } catch (e: Exception) {
                emit(Result.success(
                    SyncDataUseCase.SyncState.Error(e.message ?: "Unknown error occurred") as SyncDataUseCase.SyncState
                ))
            }
        }
        val results = syncFlow.toList()
        assertEquals(2, results.size)
        val lastState = results[1].getOrNull()
        assertTrue(lastState is SyncDataUseCase.SyncState.Error)
        assertEquals("Connection lost", (lastState as SyncDataUseCase.SyncState.Error).message)
    }

    // ============================================
    // SyncResult to SyncState Mapping Tests
    // (mirroring the mapping in invoke)
    // ============================================

    private fun mapResultToState(result: SyncResult): SyncDataUseCase.SyncState {
        return if (result.success) {
            SyncDataUseCase.SyncState.Completed(
                itemsSynced = result.itemsSynced,
                itemsFailed = result.itemsFailed,
                timestamp = result.timestamp,
                conflicts = result.conflicts
            )
        } else {
            SyncDataUseCase.SyncState.Error(
                message = result.errorMessage ?: "Sync failed",
                conflicts = result.conflicts
            )
        }
    }

    @Test
    fun `successful SyncResult maps to Completed state`() {
        val result = SyncResult(success = true, itemsSynced = 10, itemsFailed = 0)
        val state = mapResultToState(result)
        assertTrue(state is SyncDataUseCase.SyncState.Completed)
        val completed = state as SyncDataUseCase.SyncState.Completed
        assertEquals(10, completed.itemsSynced)
        assertEquals(0, completed.itemsFailed)
    }

    @Test
    fun `failed SyncResult maps to Error state`() {
        val result = SyncResult(success = false, errorMessage = "Server error")
        val state = mapResultToState(result)
        assertTrue(state is SyncDataUseCase.SyncState.Error)
        assertEquals("Server error", (state as SyncDataUseCase.SyncState.Error).message)
    }

    @Test
    fun `failed SyncResult with null error message uses default`() {
        val result = SyncResult(success = false, errorMessage = null)
        val state = mapResultToState(result)
        assertTrue(state is SyncDataUseCase.SyncState.Error)
        assertEquals("Sync failed", (state as SyncDataUseCase.SyncState.Error).message)
    }

    @Test
    fun `SyncResult with conflicts preserves them in state`() {
        val conflict = SyncConflict(
            entityType = SyncEntityType.TRANSACTION,
            entityId = "tx-1",
            localVersion = "v1",
            remoteVersion = "v2",
            localTimestamp = Instant.now(),
            remoteTimestamp = Instant.now()
        )
        val result = SyncResult(
            success = false,
            conflicts = listOf(conflict),
            errorMessage = "Conflicts found"
        )
        val state = mapResultToState(result) as SyncDataUseCase.SyncState.Error
        assertEquals(1, state.conflicts.size)
    }
}
