package com.pecunia.data.local.preferences

/**
 * Theme options for the application
 */
enum class AppTheme {
    LIGHT,
    DARK,
    SYSTEM
}

/**
 * Supported languages for the application
 */
enum class AppLanguage(val code: String) {
    FRENCH("fr"),
    ENGLISH("en");

    companion object {
        fun fromCode(code: String): AppLanguage {
            return entries.find { it.code == code } ?: FRENCH
        }
    }
}

/**
 * Data class representing all user preferences stored locally.
 *
 * This class encapsulates authentication state, user settings, and app configuration.
 * Sensitive data (tokens) are stored separately in EncryptedSharedPreferences.
 *
 * @property isLoggedIn Whether the user is currently authenticated
 * @property accessToken JWT access token for API authentication (stored encrypted)
 * @property refreshToken Refresh token for obtaining new access tokens (stored encrypted)
 * @property userId Unique identifier of the authenticated user
 * @property email Email address of the authenticated user
 * @property theme Current theme preference (light/dark/system)
 * @property language Current language preference (fr/en)
 * @property notificationsEnabled Whether push notifications are enabled
 * @property biometricEnabled Whether biometric authentication is enabled
 * @property lastSyncTimestamp Timestamp of the last successful data synchronization
 * @property onboardingCompleted Whether the user has completed the onboarding flow
 */
data class UserPreferences(
    val isLoggedIn: Boolean = false,
    val accessToken: String = "",
    val refreshToken: String = "",
    val userId: String = "",
    val email: String = "",
    val theme: AppTheme = AppTheme.SYSTEM,
    val language: AppLanguage = AppLanguage.FRENCH,
    val notificationsEnabled: Boolean = true,
    val biometricEnabled: Boolean = false,
    val lastSyncTimestamp: Long = 0L,
    val onboardingCompleted: Boolean = false
) {
    companion object {
        /**
         * Default preferences for a new/unauthenticated user
         */
        val DEFAULT = UserPreferences()
    }

    /**
     * Returns true if the user has valid authentication tokens
     */
    val hasValidTokens: Boolean
        get() = accessToken.isNotBlank() && refreshToken.isNotBlank()

    /**
     * Returns true if the user needs to complete onboarding
     */
    val needsOnboarding: Boolean
        get() = isLoggedIn && !onboardingCompleted

    /**
     * Returns true if biometric login is available for this user
     */
    val canUseBiometric: Boolean
        get() = isLoggedIn && biometricEnabled && hasValidTokens
}
