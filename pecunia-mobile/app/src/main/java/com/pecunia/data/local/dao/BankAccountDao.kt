package com.pecunia.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Embedded
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Relation
import androidx.room.Transaction
import androidx.room.Update
import com.pecunia.data.local.entity.BankAccountEntity
import com.pecunia.data.local.entity.BankConnectionEntity
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for Bank Account operations.
 * Handles all database operations related to bank accounts and connections.
 */
@Dao
interface BankAccountDao {

    /**
     * Observes all bank accounts for the current user.
     * @param userId The user's ID
     * @return Flow emitting list of bank accounts
     */
    @Query("SELECT * FROM bank_accounts WHERE userId = :userId ORDER BY institutionName ASC, name ASC")
    fun getAccounts(userId: String): Flow<List<BankAccountEntity>>

    /**
     * Gets all bank accounts synchronously.
     * @param userId The user's ID
     * @return List of bank accounts
     */
    @Query("SELECT * FROM bank_accounts WHERE userId = :userId ORDER BY institutionName ASC, name ASC")
    suspend fun getAccountsSync(userId: String): List<BankAccountEntity>

    /**
     * Observes bank accounts associated with a specific bank connection.
     * @param connectionId The bank connection's ID
     * @return Flow emitting list of accounts for the connection
     */
    @Query("SELECT * FROM bank_accounts WHERE connectionId = :connectionId ORDER BY name ASC")
    fun getAccountsByConnection(connectionId: String): Flow<List<BankAccountEntity>>

    /**
     * Gets accounts by connection synchronously.
     * @param connectionId The bank connection's ID
     * @return List of accounts for the connection
     */
    @Query("SELECT * FROM bank_accounts WHERE connectionId = :connectionId ORDER BY name ASC")
    suspend fun getAccountsByConnectionSync(connectionId: String): List<BankAccountEntity>

    /**
     * Observes a single bank account by its ID.
     * @param id The account's unique ID
     * @return Flow emitting the account or null if not found
     */
    @Query("SELECT * FROM bank_accounts WHERE id = :id")
    fun getAccountById(id: String): Flow<BankAccountEntity?>

    /**
     * Gets an account by ID synchronously.
     * @param id The account's unique ID
     * @return The account entity or null if not found
     */
    @Query("SELECT * FROM bank_accounts WHERE id = :id")
    suspend fun getAccountByIdSync(id: String): BankAccountEntity?

    /**
     * Observes accounts filtered by type (checking, savings, credit, etc.).
     * @param userId The user's ID
     * @param type The account type
     * @return Flow emitting list of accounts of the specified type
     */
    @Query("""
        SELECT * FROM bank_accounts
        WHERE userId = :userId
        AND type = :type
        ORDER BY institutionName ASC, name ASC
    """)
    fun getAccountsByType(userId: String, type: String): Flow<List<BankAccountEntity>>

    /**
     * Gets the total balance across all accounts.
     * @param userId The user's ID
     * @return The sum of all account balances
     */
    @Query("SELECT COALESCE(SUM(currentBalance), 0) FROM bank_accounts WHERE userId = :userId")
    suspend fun getTotalBalance(userId: String): Double

    /**
     * Gets the total balance by account type.
     * @param userId The user's ID
     * @param type The account type
     * @return The sum of balances for accounts of the specified type
     */
    @Query("""
        SELECT COALESCE(SUM(currentBalance), 0)
        FROM bank_accounts
        WHERE userId = :userId
        AND type = :type
    """)
    suspend fun getTotalBalanceByType(userId: String, type: String): Double

    /**
     * Observes active (non-hidden) accounts.
     * @param userId The user's ID
     * @return Flow emitting list of active accounts
     */
    @Query("""
        SELECT * FROM bank_accounts
        WHERE userId = :userId
        AND isHidden = 0
        ORDER BY institutionName ASC, name ASC
    """)
    fun getActiveAccounts(userId: String): Flow<List<BankAccountEntity>>

    /**
     * Searches accounts by name or institution.
     * @param userId The user's ID
     * @param query The search query
     * @return Flow emitting list of matching accounts
     */
    @Query("""
        SELECT * FROM bank_accounts
        WHERE userId = :userId
        AND (name LIKE '%' || :query || '%' OR institutionName LIKE '%' || :query || '%')
        ORDER BY institutionName ASC, name ASC
    """)
    fun searchAccounts(userId: String, query: String): Flow<List<BankAccountEntity>>

    /**
     * Inserts a new bank account into the database.
     * @param account The bank account entity to insert
     * @return The row ID of the inserted account
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(account: BankAccountEntity): Long

    /**
     * Inserts multiple bank accounts into the database.
     * @param accounts List of bank account entities to insert
     * @return List of row IDs for inserted accounts
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(accounts: List<BankAccountEntity>): List<Long>

    /**
     * Updates an existing bank account in the database.
     * @param account The bank account entity with updated values
     * @return The number of rows updated
     */
    @Update
    suspend fun update(account: BankAccountEntity): Int

    /**
     * Deletes a bank account from the database.
     * @param account The bank account entity to delete
     * @return The number of rows deleted
     */
    @Delete
    suspend fun delete(account: BankAccountEntity): Int

    /**
     * Deletes a bank account by its ID.
     * @param id The account's ID to delete
     * @return The number of rows deleted
     */
    @Query("DELETE FROM bank_accounts WHERE id = :id")
    suspend fun deleteById(id: String): Int

    /**
     * Deletes all accounts for a specific connection.
     * @param connectionId The bank connection's ID
     */
    @Query("DELETE FROM bank_accounts WHERE connectionId = :connectionId")
    suspend fun deleteByConnection(connectionId: String)

    /**
     * Deletes all accounts for a user.
     * @param userId The user's ID
     */
    @Query("DELETE FROM bank_accounts WHERE userId = :userId")
    suspend fun deleteAllForUser(userId: String)

    /**
     * Updates the balance for an account.
     * @param accountId The account's ID
     * @param currentBalance The new current balance
     * @param availableBalance The new available balance
     * @param updatedAt The update timestamp
     */
    @Query("""
        UPDATE bank_accounts
        SET currentBalance = :currentBalance,
            availableBalance = :availableBalance,
            updatedAt = :updatedAt
        WHERE id = :accountId
    """)
    suspend fun updateBalance(
        accountId: String,
        currentBalance: Double,
        availableBalance: Double?,
        updatedAt: Long
    )

    /**
     * Toggles the hidden status of an account.
     * @param accountId The account's ID
     * @param isHidden Whether the account should be hidden
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE bank_accounts SET isHidden = :isHidden, updatedAt = :updatedAt WHERE id = :accountId")
    suspend fun setHiddenStatus(accountId: String, isHidden: Boolean, updatedAt: Long)

    /**
     * Updates the last synced timestamp for an account.
     * @param accountId The account's ID
     * @param lastSyncedAt The new sync timestamp
     */
    @Query("UPDATE bank_accounts SET lastSyncedAt = :lastSyncedAt WHERE id = :accountId")
    suspend fun updateLastSyncedAt(accountId: String, lastSyncedAt: Long)

    /**
     * Updates the nickname for an account.
     * @param accountId The account's ID
     * @param nickname The new nickname
     * @param updatedAt The update timestamp
     */
    @Query("UPDATE bank_accounts SET nickname = :nickname, updatedAt = :updatedAt WHERE id = :accountId")
    suspend fun updateNickname(accountId: String, nickname: String?, updatedAt: Long)

    // Bank Connection Operations

    /**
     * Observes all bank connections for a user.
     * @param userId The user's ID
     * @return Flow emitting list of bank connections
     */
    @Query("SELECT * FROM bank_connections WHERE userId = :userId ORDER BY institutionName ASC")
    fun getConnections(userId: String): Flow<List<BankConnectionEntity>>

    /**
     * Gets all connections synchronously.
     * @param userId The user's ID
     * @return List of bank connections
     */
    @Query("SELECT * FROM bank_connections WHERE userId = :userId ORDER BY institutionName ASC")
    suspend fun getConnectionsSync(userId: String): List<BankConnectionEntity>

    /**
     * Gets a bank connection by its ID.
     * @param id The connection's unique ID
     * @return Flow emitting the connection or null if not found
     */
    @Query("SELECT * FROM bank_connections WHERE id = :id")
    fun getConnectionById(id: String): Flow<BankConnectionEntity?>

    /**
     * Gets a connection by ID synchronously.
     * @param id The connection's unique ID
     * @return The connection entity or null if not found
     */
    @Query("SELECT * FROM bank_connections WHERE id = :id")
    suspend fun getConnectionByIdSync(id: String): BankConnectionEntity?

    /**
     * Observes a connection with all its associated accounts.
     * @param connectionId The connection's ID
     * @return Flow emitting the connection with accounts
     */
    @Transaction
    @Query("SELECT * FROM bank_connections WHERE id = :connectionId")
    fun getConnectionWithAccounts(connectionId: String): Flow<ConnectionWithAccounts?>

    /**
     * Observes all connections with their accounts for a user.
     * @param userId The user's ID
     * @return Flow emitting list of connections with accounts
     */
    @Transaction
    @Query("SELECT * FROM bank_connections WHERE userId = :userId ORDER BY institutionName ASC")
    fun getConnectionsWithAccounts(userId: String): Flow<List<ConnectionWithAccounts>>

    /**
     * Gets connections that need re-authentication.
     * @param userId The user's ID
     * @return List of connections requiring re-auth
     */
    @Query("""
        SELECT * FROM bank_connections
        WHERE userId = :userId
        AND status = 'REQUIRES_REAUTH'
    """)
    suspend fun getConnectionsRequiringReauth(userId: String): List<BankConnectionEntity>

    /**
     * Inserts a new bank connection.
     * @param connection The bank connection entity to insert
     * @return The row ID of the inserted connection
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertConnection(connection: BankConnectionEntity): Long

    /**
     * Updates a bank connection.
     * @param connection The bank connection entity with updated values
     * @return The number of rows updated
     */
    @Update
    suspend fun updateConnection(connection: BankConnectionEntity): Int

    /**
     * Deletes a bank connection.
     * @param connection The bank connection entity to delete
     * @return The number of rows deleted
     */
    @Delete
    suspend fun deleteConnection(connection: BankConnectionEntity): Int

    /**
     * Deletes a connection by its ID.
     * @param id The connection's ID
     * @return The number of rows deleted
     */
    @Query("DELETE FROM bank_connections WHERE id = :id")
    suspend fun deleteConnectionById(id: String): Int

    /**
     * Updates the status of a connection.
     * @param connectionId The connection's ID
     * @param status The new status
     * @param errorMessage Optional error message
     * @param updatedAt The update timestamp
     */
    @Query("""
        UPDATE bank_connections
        SET status = :status,
            errorMessage = :errorMessage,
            updatedAt = :updatedAt
        WHERE id = :connectionId
    """)
    suspend fun updateConnectionStatus(
        connectionId: String,
        status: String,
        errorMessage: String?,
        updatedAt: Long
    )

    /**
     * Updates the last synced timestamp for a connection.
     * @param connectionId The connection's ID
     * @param lastSyncedAt The new sync timestamp
     */
    @Query("UPDATE bank_connections SET lastSyncedAt = :lastSyncedAt WHERE id = :connectionId")
    suspend fun updateConnectionLastSyncedAt(connectionId: String, lastSyncedAt: Long)

    /**
     * Deletes a connection and all its associated accounts.
     * @param connectionId The connection's ID
     */
    @Transaction
    suspend fun deleteConnectionWithAccounts(connectionId: String) {
        deleteByConnection(connectionId)
        deleteConnectionById(connectionId)
    }
}

/**
 * Data class representing a bank connection with its associated accounts.
 */
data class ConnectionWithAccounts(
    @Embedded val connection: BankConnectionEntity,
    @Relation(
        parentColumn = "id",
        entityColumn = "connectionId"
    )
    val accounts: List<BankAccountEntity>
)
