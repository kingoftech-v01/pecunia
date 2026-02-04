package com.pecunia.domain.models

import java.time.Instant

/**
 * Represents a user in the finance application.
 */
data class User(
    val id: String,
    val email: String,
    val firstName: String,
    val lastName: String,
    val profileImageUrl: String? = null,
    val currency: String = "USD",
    val isEmailVerified: Boolean = false,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
) {
    /**
     * Returns the user's full name.
     */
    val fullName: String
        get() = "$firstName $lastName".trim()

    /**
     * Returns the user's initials for avatar display.
     */
    val initials: String
        get() = buildString {
            if (firstName.isNotBlank()) append(firstName.first().uppercaseChar())
            if (lastName.isNotBlank()) append(lastName.first().uppercaseChar())
        }

    companion object {
        /**
         * Creates an empty User instance for initialization purposes.
         */
        fun empty(): User = User(
            id = "",
            email = "",
            firstName = "",
            lastName = ""
        )
    }
}
