package com.pecunia.data.local.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal
import java.util.UUID

/**
 * Entity representing a budget in the local Room database.
 * Supports different period types and tracks planned spending limits.
 */
@Entity(
    tableName = "budgets",
    indices = [
        Index(value = ["user_id"]),
        Index(value = ["is_active"]),
        Index(value = ["period_type"]),
        Index(value = ["start_date", "end_date"]),
        Index(value = ["user_id", "is_active"])
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
data class BudgetEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "user_id")
    val userId: UUID,

    @ColumnInfo(name = "name")
    val name: String,

    @ColumnInfo(name = "description")
    val description: String? = null,

    @ColumnInfo(name = "period_type")
    val periodType: PeriodType,

    @ColumnInfo(name = "start_date")
    val startDate: Long,

    @ColumnInfo(name = "end_date")
    val endDate: Long,

    @ColumnInfo(name = "total_planned")
    val totalPlanned: BigDecimal,

    @ColumnInfo(name = "is_active")
    val isActive: Boolean = true,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "sync_status")
    val syncStatus: SyncStatus = SyncStatus.PENDING
) {
    /**
     * Enum representing the period type for a budget.
     */
    enum class PeriodType {
        DAILY,
        WEEKLY,
        BIWEEKLY,
        MONTHLY,
        QUARTERLY,
        YEARLY,
        CUSTOM
    }

    /**
     * Enum representing the synchronization status of the budget.
     */
    enum class SyncStatus {
        PENDING,
        SYNCED,
        FAILED,
        CONFLICT
    }

    /**
     * Checks if the budget is currently within its active period.
     */
    fun isWithinPeriod(timestamp: Long = System.currentTimeMillis()): Boolean =
        timestamp in startDate..endDate

    /**
     * Checks if the budget period has ended.
     */
    fun hasEnded(timestamp: Long = System.currentTimeMillis()): Boolean =
        timestamp > endDate

    /**
     * Checks if the budget period has started.
     */
    fun hasStarted(timestamp: Long = System.currentTimeMillis()): Boolean =
        timestamp >= startDate

    /**
     * Calculates the remaining amount based on spent amount.
     */
    fun calculateRemaining(spentAmount: BigDecimal): BigDecimal =
        totalPlanned.subtract(spentAmount)

    /**
     * Calculates the percentage spent of the budget.
     */
    fun calculatePercentageSpent(spentAmount: BigDecimal): Float {
        if (totalPlanned == BigDecimal.ZERO) return 0f
        return spentAmount.divide(totalPlanned, 4, java.math.RoundingMode.HALF_UP)
            .multiply(BigDecimal(100))
            .toFloat()
    }

    /**
     * Checks if the budget is overspent.
     */
    fun isOverspent(spentAmount: BigDecimal): Boolean =
        spentAmount > totalPlanned

    /**
     * Gets the duration of the budget period in days.
     */
    fun getDurationInDays(): Long =
        (endDate - startDate) / (24 * 60 * 60 * 1000)

    companion object {
        /**
         * Creates a copy of the entity with updated timestamp.
         */
        fun BudgetEntity.withUpdatedTimestamp(): BudgetEntity =
            copy(
                updatedAt = System.currentTimeMillis(),
                syncStatus = SyncStatus.PENDING
            )

        /**
         * Creates a copy of the entity marked as synced.
         */
        fun BudgetEntity.markAsSynced(): BudgetEntity =
            copy(syncStatus = SyncStatus.SYNCED)

        /**
         * Creates a deactivated copy of the budget.
         */
        fun BudgetEntity.deactivate(): BudgetEntity =
            copy(
                isActive = false,
                updatedAt = System.currentTimeMillis(),
                syncStatus = SyncStatus.PENDING
            )
    }
}
