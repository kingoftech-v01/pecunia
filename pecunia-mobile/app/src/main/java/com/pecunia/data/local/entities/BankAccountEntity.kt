package com.pecunia.data.local.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal
import java.util.UUID

/**
 * Entity representing a connected bank account in the local Room database.
 * Stores bank account information synced from external banking providers.
 */
@Entity(
    tableName = "bank_accounts",
    indices = [
        Index(value = ["connection_id"]),
        Index(value = ["external_id"], unique = true),
        Index(value = ["account_type"]),
        Index(value = ["is_primary"]),
        Index(value = ["user_id"]),
        Index(value = ["user_id", "is_primary"])
    ],
    foreignKeys = [
        ForeignKey(
            entity = UserEntity::class,
            parentColumns = ["id"],
            childColumns = ["user_id"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = BankConnectionEntity::class,
            parentColumns = ["id"],
            childColumns = ["connection_id"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE
        )
    ]
)
data class BankAccountEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "user_id")
    val userId: UUID,

    @ColumnInfo(name = "connection_id")
    val connectionId: UUID,

    @ColumnInfo(name = "external_id")
    val externalId: String, // ID from the banking provider

    @ColumnInfo(name = "account_type")
    val accountType: AccountType,

    @ColumnInfo(name = "name")
    val name: String,

    @ColumnInfo(name = "official_name")
    val officialName: String? = null,

    @ColumnInfo(name = "balance")
    val balance: BigDecimal,

    @ColumnInfo(name = "available_balance")
    val availableBalance: BigDecimal? = null,

    @ColumnInfo(name = "currency")
    val currency: String = "EUR",

    @ColumnInfo(name = "iban_masked")
    val ibanMasked: String? = null, // e.g., "FR76 **** **** **** **** ***1 234"

    @ColumnInfo(name = "is_primary")
    val isPrimary: Boolean = false,

    @ColumnInfo(name = "is_hidden")
    val isHidden: Boolean = false,

    @ColumnInfo(name = "institution_name")
    val institutionName: String? = null,

    @ColumnInfo(name = "institution_logo_url")
    val institutionLogoUrl: String? = null,

    @ColumnInfo(name = "last_synced_at")
    val lastSyncedAt: Long? = null,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "sync_status")
    val syncStatus: SyncStatus = SyncStatus.SYNCED
) {
    /**
     * Enum representing the type of bank account.
     */
    enum class AccountType {
        CHECKING,
        SAVINGS,
        CREDIT_CARD,
        INVESTMENT,
        LOAN,
        MORTGAGE,
        LINE_OF_CREDIT,
        OTHER
    }

    /**
     * Enum representing the synchronization status of the account.
     */
    enum class SyncStatus {
        SYNCED,
        SYNCING,
        FAILED,
        STALE
    }

    /**
     * Checks if the account is a credit type (shows negative balance as debt).
     */
    fun isCreditAccount(): Boolean =
        accountType == AccountType.CREDIT_CARD ||
        accountType == AccountType.LOAN ||
        accountType == AccountType.MORTGAGE ||
        accountType == AccountType.LINE_OF_CREDIT

    /**
     * Checks if the account is a checking or savings account.
     */
    fun isBankingAccount(): Boolean =
        accountType == AccountType.CHECKING ||
        accountType == AccountType.SAVINGS

    /**
     * Returns the display balance (positive for assets, negative for debts).
     */
    fun getDisplayBalance(): BigDecimal =
        if (isCreditAccount()) balance.negate() else balance

    /**
     * Checks if the account has a positive balance.
     */
    fun hasPositiveBalance(): Boolean = balance > BigDecimal.ZERO

    /**
     * Checks if the account sync is stale (more than 24 hours old).
     */
    fun isSyncStale(currentTime: Long = System.currentTimeMillis()): Boolean {
        val staleDuration = 24 * 60 * 60 * 1000L // 24 hours in milliseconds
        return lastSyncedAt?.let { (currentTime - it) > staleDuration } ?: true
    }

    /**
     * Checks if the account needs refresh.
     */
    fun needsRefresh(): Boolean =
        syncStatus == SyncStatus.STALE ||
        syncStatus == SyncStatus.FAILED ||
        isSyncStale()

    /**
     * Returns a masked version of the account name for display.
     */
    fun getMaskedDisplayName(): String =
        ibanMasked?.takeLast(8) ?: name

    companion object {
        /**
         * Creates a copy of the entity with updated balance and sync time.
         */
        fun BankAccountEntity.updateBalance(
            newBalance: BigDecimal,
            newAvailableBalance: BigDecimal? = null
        ): BankAccountEntity =
            copy(
                balance = newBalance,
                availableBalance = newAvailableBalance,
                lastSyncedAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis(),
                syncStatus = SyncStatus.SYNCED
            )

        /**
         * Creates a copy of the entity marked as syncing.
         */
        fun BankAccountEntity.markAsSyncing(): BankAccountEntity =
            copy(syncStatus = SyncStatus.SYNCING)

        /**
         * Creates a copy of the entity marked as sync failed.
         */
        fun BankAccountEntity.markAsSyncFailed(): BankAccountEntity =
            copy(syncStatus = SyncStatus.FAILED)

        /**
         * Creates a copy of the entity set as primary.
         */
        fun BankAccountEntity.setAsPrimary(): BankAccountEntity =
            copy(
                isPrimary = true,
                updatedAt = System.currentTimeMillis()
            )
    }
}

/**
 * Entity representing a bank connection (institution link) in the local Room database.
 * This represents the connection to a banking institution via aggregation services.
 */
@Entity(
    tableName = "bank_connections",
    indices = [
        Index(value = ["user_id"]),
        Index(value = ["external_connection_id"], unique = true),
        Index(value = ["status"])
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
data class BankConnectionEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "user_id")
    val userId: UUID,

    @ColumnInfo(name = "external_connection_id")
    val externalConnectionId: String, // ID from the aggregation provider

    @ColumnInfo(name = "institution_id")
    val institutionId: String,

    @ColumnInfo(name = "institution_name")
    val institutionName: String,

    @ColumnInfo(name = "institution_logo_url")
    val institutionLogoUrl: String? = null,

    @ColumnInfo(name = "status")
    val status: ConnectionStatus,

    @ColumnInfo(name = "error_code")
    val errorCode: String? = null,

    @ColumnInfo(name = "error_message")
    val errorMessage: String? = null,

    @ColumnInfo(name = "last_successful_sync")
    val lastSuccessfulSync: Long? = null,

    @ColumnInfo(name = "consent_expires_at")
    val consentExpiresAt: Long? = null,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis()
) {
    /**
     * Enum representing the connection status.
     */
    enum class ConnectionStatus {
        ACTIVE,
        PENDING,
        REQUIRES_REAUTHENTICATION,
        ERROR,
        DISCONNECTED
    }

    /**
     * Checks if the connection is active and healthy.
     */
    fun isHealthy(): Boolean = status == ConnectionStatus.ACTIVE

    /**
     * Checks if the connection requires user action.
     */
    fun requiresUserAction(): Boolean =
        status == ConnectionStatus.REQUIRES_REAUTHENTICATION ||
        status == ConnectionStatus.ERROR

    /**
     * Checks if the consent is about to expire (within 7 days).
     */
    fun isConsentExpiringSoon(currentTime: Long = System.currentTimeMillis()): Boolean {
        val sevenDays = 7 * 24 * 60 * 60 * 1000L
        return consentExpiresAt?.let { (it - currentTime) < sevenDays } ?: false
    }

    /**
     * Checks if the consent has expired.
     */
    fun isConsentExpired(currentTime: Long = System.currentTimeMillis()): Boolean =
        consentExpiresAt?.let { currentTime > it } ?: false
}
