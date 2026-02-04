package com.pecunia.domain.models

import java.time.Instant

/**
 * Represents a user in the finance application.
 */
data class User(
    val id: String,
    val email: String,
    val displayName: String,
    val avatarUrl: String? = null,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now(),
    val preferences: UserPreferences = UserPreferences()
)

/**
 * User preferences for app customization.
 */
data class UserPreferences(
    val currency: String = "USD",
    val locale: String = "en_US",
    val notificationsEnabled: Boolean = true,
    val budgetAlertThreshold: Float = 0.8f,
    val darkModeEnabled: Boolean = false,
    val biometricAuthEnabled: Boolean = false
)

/**
 * Represents the authentication state of the user.
 */
sealed class AuthState {
    object Loading : AuthState()
    object Unauthenticated : AuthState()
    data class Authenticated(val user: User) : AuthState()
    data class Error(val message: String) : AuthState()
}
