package com.pecunia.data.remote.api

import android.content.SharedPreferences
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * OkHttp Interceptor that adds authentication headers to API requests.
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val sharedPreferences: SharedPreferences
) : Interceptor {

    companion object {
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_TOKEN_EXPIRY = "token_expiry"
        private const val HEADER_AUTHORIZATION = "Authorization"
        private const val HEADER_CONTENT_TYPE = "Content-Type"
        private const val BEARER_PREFIX = "Bearer "
        private const val CONTENT_TYPE_JSON = "application/json"
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        // Skip auth header for auth endpoints
        if (isAuthEndpoint(originalRequest.url.encodedPath)) {
            return chain.proceed(originalRequest)
        }

        val accessToken = getAccessToken()

        val request = originalRequest.newBuilder()
            .header(HEADER_CONTENT_TYPE, CONTENT_TYPE_JSON)
            .apply {
                if (!accessToken.isNullOrBlank()) {
                    header(HEADER_AUTHORIZATION, "$BEARER_PREFIX$accessToken")
                }
            }
            .build()

        val response = chain.proceed(request)

        // Handle 401 Unauthorized - token might be expired
        if (response.code == 401 && !accessToken.isNullOrBlank()) {
            response.close()

            // Try to refresh the token
            synchronized(this) {
                // Check if another thread already refreshed the token
                val currentToken = getAccessToken()
                if (currentToken != accessToken) {
                    // Token was refreshed by another thread, retry with new token
                    return chain.proceed(
                        originalRequest.newBuilder()
                            .header(HEADER_CONTENT_TYPE, CONTENT_TYPE_JSON)
                            .header(HEADER_AUTHORIZATION, "$BEARER_PREFIX$currentToken")
                            .build()
                    )
                }

                // Token refresh would be handled here
                // For now, return the original 401 response
                return chain.proceed(request)
            }
        }

        return response
    }

    /**
     * Check if the endpoint is an auth endpoint that doesn't need authentication.
     */
    private fun isAuthEndpoint(path: String): Boolean {
        val authPaths = listOf(
            "/auth/login",
            "/auth/register",
            "/auth/forgot-password",
            "/auth/reset-password",
            "/auth/refresh-token",
            "/auth/verify-email"
        )
        return authPaths.any { path.contains(it, ignoreCase = true) }
    }

    /**
     * Get the current access token from secure storage.
     */
    fun getAccessToken(): String? {
        return sharedPreferences.getString(KEY_ACCESS_TOKEN, null)
    }

    /**
     * Save tokens to secure storage.
     */
    fun saveTokens(accessToken: String, refreshToken: String, expiryTime: Long) {
        sharedPreferences.edit()
            .putString(KEY_ACCESS_TOKEN, accessToken)
            .putString(KEY_REFRESH_TOKEN, refreshToken)
            .putLong(KEY_TOKEN_EXPIRY, expiryTime)
            .apply()
    }

    /**
     * Get the refresh token from secure storage.
     */
    fun getRefreshToken(): String? {
        return sharedPreferences.getString(KEY_REFRESH_TOKEN, null)
    }

    /**
     * Check if the access token is expired.
     */
    fun isTokenExpired(): Boolean {
        val expiryTime = sharedPreferences.getLong(KEY_TOKEN_EXPIRY, 0)
        return System.currentTimeMillis() >= expiryTime
    }

    /**
     * Clear all authentication data.
     */
    fun clearTokens() {
        sharedPreferences.edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .remove(KEY_TOKEN_EXPIRY)
            .apply()
    }

    /**
     * Check if user is authenticated.
     */
    fun isAuthenticated(): Boolean {
        return !getAccessToken().isNullOrBlank() && !isTokenExpired()
    }
}
