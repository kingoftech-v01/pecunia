package com.pecunia.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.pecunia.data.local.entity.UserEntity
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for User operations.
 * Handles all database operations related to the authenticated user.
 */
@Dao
interface UserDao {

    /**
     * Observes the current user.
     * Returns a Flow that emits the user whenever it changes.
     * @return Flow emitting the current user or null if not logged in
     */
    @Query("SELECT * FROM users LIMIT 1")
    fun getUser(): Flow<UserEntity?>

    /**
     * Gets the current user synchronously.
     * Use this for one-shot operations where observation is not needed.
     * @return The current user or null if not logged in
     */
    @Query("SELECT * FROM users LIMIT 1")
    suspend fun getUserSync(): UserEntity?

    /**
     * Gets user by their unique identifier.
     * @param userId The user's unique ID
     * @return Flow emitting the user or null if not found
     */
    @Query("SELECT * FROM users WHERE id = :userId")
    fun getUserById(userId: String): Flow<UserEntity?>

    /**
     * Gets user by email address.
     * @param email The user's email
     * @return The user entity or null if not found
     */
    @Query("SELECT * FROM users WHERE email = :email LIMIT 1")
    suspend fun getUserByEmail(email: String): UserEntity?

    /**
     * Inserts a new user into the database.
     * If a user with the same ID exists, it will be replaced.
     * @param user The user entity to insert
     * @return The row ID of the inserted user
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(user: UserEntity): Long

    /**
     * Updates an existing user in the database.
     * @param user The user entity with updated values
     * @return The number of rows updated
     */
    @Update
    suspend fun update(user: UserEntity): Int

    /**
     * Deletes a user from the database.
     * @param user The user entity to delete
     * @return The number of rows deleted
     */
    @Delete
    suspend fun delete(user: UserEntity): Int

    /**
     * Clears all users from the database.
     * Typically used during logout to remove all user data.
     */
    @Query("DELETE FROM users")
    suspend fun clearUser()

    /**
     * Checks if a user exists in the database.
     * @return True if at least one user exists, false otherwise
     */
    @Query("SELECT EXISTS(SELECT 1 FROM users LIMIT 1)")
    suspend fun hasUser(): Boolean

    /**
     * Updates the user's last sync timestamp.
     * @param userId The user's ID
     * @param timestamp The new sync timestamp
     */
    @Query("UPDATE users SET lastSyncedAt = :timestamp WHERE id = :userId")
    suspend fun updateLastSyncedAt(userId: String, timestamp: Long)

    /**
     * Updates the user's premium status.
     * @param userId The user's ID
     * @param isPremium Whether the user has premium subscription
     */
    @Query("UPDATE users SET isPremium = :isPremium WHERE id = :userId")
    suspend fun updatePremiumStatus(userId: String, isPremium: Boolean)

    /**
     * Updates the user's profile picture URL.
     * @param userId The user's ID
     * @param profilePictureUrl The new profile picture URL
     */
    @Query("UPDATE users SET profilePictureUrl = :profilePictureUrl WHERE id = :userId")
    suspend fun updateProfilePicture(userId: String, profilePictureUrl: String?)
}
