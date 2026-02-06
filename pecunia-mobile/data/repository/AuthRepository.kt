package com.pecunia.data.repository

import android.content.SharedPreferences
import com.pecunia.data.remote.api.*
import com.pecunia.di.IoDispatcher
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository handling authentication operations.
 * Implements offline-first approach with token management.
 */
@Singleton
class AuthRepository @Inject constructor(
    private val apiService: ApiService,
    private val authInterceptor: AuthInterceptor,
    private val sharedPreferences: SharedPreferences,
    @IoDispatcher private val ioDispatcher: CoroutineDispatcher
) {

    companion object {
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USER_EMAIL = "user_email"
        private const val KEY_USER_NAME = "user_name"
    }

    /**
     * Login with email and password.
     */
    suspend fun login(email: String, password: String): Result<UserDto> = withContext(ioDispatcher) {
        try {
            val response = apiService.login(LoginRequest(email, password))
            if (response.isSuccessful && response.body() != null) {
                val authResponse = response.body()!!
                saveAuthData(authResponse)
                Result.success(authResponse.user)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Register a new user.
     */
    suspend fun register(name: String, email: String, password: String): Result<UserDto> = withContext(ioDispatcher) {
        try {
            val response = apiService.register(RegisterRequest(email, password, name))
            if (response.isSuccessful && response.body() != null) {
                val authResponse = response.body()!!
                saveAuthData(authResponse)
                Result.success(authResponse.user)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Logout the current user.
     */
    suspend fun logout(): Result<Unit> = withContext(ioDispatcher) {
        try {
            // Try to logout on server
            apiService.logout()
        } catch (e: Exception) {
            // Server unreachable is fine; local logout still succeeds.
        } finally {
            // Always clear local tokens even if server fails (offline-first).
            clearAuthData()
        }
        Result.success(Unit)
    }

    /**
     * Refresh the access token using the refresh token.
     */
    suspend fun refreshToken(): Result<Unit> = withContext(ioDispatcher) {
        try {
            val refreshToken = authInterceptor.getRefreshToken()
                ?: return@withContext Result.failure(AuthException("No refresh token available"))

            val response = apiService.refreshToken(RefreshTokenRequest(refreshToken))
            if (response.isSuccessful && response.body() != null) {
                val authResponse = response.body()!!
                saveAuthData(authResponse)
                Result.success(Unit)
            } else {
                // Invalid refresh token: force re-login rather than retry loop.
                clearAuthData()
                Result.failure(AuthException("Failed to refresh token"))
            }
        } catch (e: Exception) {
            // Network error during refresh: clear tokens to force re-auth.
            clearAuthData()
            Result.failure(e)
        }
    }

    /**
     * Request password reset email.
     */
    suspend fun forgotPassword(email: String): Result<String> = withContext(ioDispatcher) {
        try {
            val response = apiService.forgotPassword(ForgotPasswordRequest(email))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.message)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Reset password with token.
     */
    suspend fun resetPassword(
        token: String,
        password: String,
        confirmPassword: String
    ): Result<String> = withContext(ioDispatcher) {
        try {
            val response = apiService.resetPassword(
                ResetPasswordRequest(token, password, confirmPassword)
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.message)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Change current user's password.
     */
    suspend fun changePassword(
        currentPassword: String,
        newPassword: String,
        confirmPassword: String
    ): Result<String> = withContext(ioDispatcher) {
        try {
            val response = apiService.changePassword(
                ChangePasswordRequest(currentPassword, newPassword, confirmPassword)
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.message)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Get current user profile.
     */
    suspend fun getCurrentUser(): Result<UserDto> = withContext(ioDispatcher) {
        try {
            val response = apiService.getCurrentUser()
            if (response.isSuccessful && response.body() != null) {
                val user = response.body()!!.data
                saveUserData(user)
                Result.success(user)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Update user profile.
     */
    suspend fun updateProfile(
        name: String? = null,
        email: String? = null,
        phone: String? = null,
        avatarUrl: String? = null
    ): Result<UserDto> = withContext(ioDispatcher) {
        try {
            val response = apiService.updateProfile(
                UpdateProfileRequest(name, email, phone, avatarUrl)
            )
            if (response.isSuccessful && response.body() != null) {
                val user = response.body()!!.data
                saveUserData(user)
                Result.success(user)
            } else {
                Result.failure(ApiException(response.code(), response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Get authentication state as a Flow.
     */
    fun observeAuthState(): Flow<AuthState> = flow {
        emit(getCurrentAuthState())
    }.flowOn(ioDispatcher)

    /**
     * Check if user is authenticated.
     */
    fun isAuthenticated(): Boolean {
        return authInterceptor.isAuthenticated()
    }

    /**
     * Get current user ID.
     */
    fun getCurrentUserId(): String? {
        return sharedPreferences.getString(KEY_USER_ID, null)
    }

    /**
     * Get current authentication state.
     */
    private fun getCurrentAuthState(): AuthState {
        return if (isAuthenticated()) {
            val userId = sharedPreferences.getString(KEY_USER_ID, null)
            val email = sharedPreferences.getString(KEY_USER_EMAIL, null)
            val name = sharedPreferences.getString(KEY_USER_NAME, null)
            if (userId != null && email != null && name != null) {
                AuthState.Authenticated(userId, email, name)
            } else {
                AuthState.Unauthenticated
            }
        } else {
            AuthState.Unauthenticated
        }
    }

    /**
     * Save authentication data from response.
     */
    private fun saveAuthData(authResponse: AuthResponse) {
        val expiryTime = System.currentTimeMillis() + (authResponse.expires_in * 1000)
        authInterceptor.saveTokens(
            authResponse.access_token,
            authResponse.refresh_token,
            expiryTime
        )
        saveUserData(authResponse.user)
    }

    /**
     * Save user data to preferences.
     */
    private fun saveUserData(user: UserDto) {
        sharedPreferences.edit()
            .putString(KEY_USER_ID, user.id)
            .putString(KEY_USER_EMAIL, user.email)
            .putString(KEY_USER_NAME, user.name)
            .apply()
    }

    /**
     * Clear all authentication data.
     */
    private fun clearAuthData() {
        authInterceptor.clearTokens()
        sharedPreferences.edit()
            .remove(KEY_USER_ID)
            .remove(KEY_USER_EMAIL)
            .remove(KEY_USER_NAME)
            .apply()
    }
}

/**
 * Sealed class representing authentication state.
 */
sealed class AuthState {
    object Unauthenticated : AuthState()
    data class Authenticated(
        val userId: String,
        val email: String,
        val name: String
    ) : AuthState()
}

/**
 * Custom exception for API errors.
 */
class ApiException(val code: Int, message: String) : Exception("API Error $code: $message")

/**
 * Custom exception for authentication errors.
 */
class AuthException(message: String) : Exception(message)
