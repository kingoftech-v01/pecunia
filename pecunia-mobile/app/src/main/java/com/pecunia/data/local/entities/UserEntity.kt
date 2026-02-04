package com.pecunia.data.local.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

/**
 * Entity representing a user in the local Room database.
 * Contains user profile information, subscription details, and preferences.
 */
@Entity(
    tableName = "users",
    indices = [
        Index(value = ["email"], unique = true)
    ]
)
data class UserEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: UUID = UUID.randomUUID(),

    @ColumnInfo(name = "email")
    val email: String,

    @ColumnInfo(name = "first_name")
    val firstName: String,

    @ColumnInfo(name = "last_name")
    val lastName: String,

    @ColumnInfo(name = "subscription_tier")
    val subscriptionTier: SubscriptionTier = SubscriptionTier.FREE,

    @ColumnInfo(name = "preferred_currency")
    val preferredCurrency: String = "EUR",

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis()
) {
    /**
     * Enum representing the different subscription tiers available.
     */
    enum class SubscriptionTier {
        FREE,
        BASIC,
        PREMIUM,
        ENTERPRISE
    }

    /**
     * Returns the user's full name.
     */
    fun getFullName(): String = "$firstName $lastName"

    /**
     * Checks if the user has a premium subscription.
     */
    fun hasPremiumAccess(): Boolean =
        subscriptionTier == SubscriptionTier.PREMIUM ||
        subscriptionTier == SubscriptionTier.ENTERPRISE

    companion object {
        /**
         * Creates a copy of the entity with updated timestamp.
         */
        fun UserEntity.withUpdatedTimestamp(): UserEntity =
            copy(updatedAt = System.currentTimeMillis())
    }
}
