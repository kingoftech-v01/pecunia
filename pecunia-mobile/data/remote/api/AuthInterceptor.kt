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

            // Double-check locking: prevents thundering herd of concurrent refresh requests.
            synchronized(this) {
                // Another thread may have already refreshed; check before retrying.
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

                // Attempt to refresh the token using the refresh token
                val refreshToken = getRefreshToken()
                if (refreshToken.isNullOrBlank()) {
                    clearTokens()
                    return chain.proceed(request)
                }

                return try {
                    val refreshRequest = originalRequest.newBuilder()
                        .url(originalRequest.url.newBuilder()
                            .encodedPath("/auth/refresh-token")
                            .build())
                        .post(okhttp3.RequestBody.create(
                            okhttp3.MediaType.parse("application/json"),
                            """{"refresh_token":"$refreshToken"}"""
                        ))
                        .build()

                    val refreshResponse = chain.proceed(refreshRequest)
                    if (refreshResponse.isSuccessful) {
                        val responseBody = refreshResponse.body?.string()
                        val gson = com.google.gson.Gson()
                        val tokenResponse = gson.fromJson(responseBody, TokenRefreshResponse::class.java)
                        if (tokenResponse != null) {
                            saveTokens(
                                tokenResponse.accessToken,
                                tokenResponse.refreshToken,
                                tokenResponse.expiresAt
                            )
                            refreshResponse.close()
                            // Retry original request with new token
                            chain.proceed(
                                originalRequest.newBuilder()
                                    .header(HEADER_CONTENT_TYPE, CONTENT_TYPE_JSON)
                                    .header(HEADER_AUTHORIZATION, "$BEARER_PREFIX${tokenResponse.accessToken}")
                                    .build()
                            )
                        } else {
                            clearTokens()
                            refreshResponse
                        }
                    } else {
                        clearTokens()
                        refreshResponse
                    }
                } catch (e: Exception) {
                    clearTokens()
                    chain.proceed(request)
                }
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
    internal fun getAccessToken(): String? {
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
    internal fun getRefreshToken(): String? {
        return sharedPreferences.getString(KEY_REFRESH_TOKEN, null)
    }

    /**
     * Check if the access token is expired.
     * Note: This relies on the client device clock. If the client clock is skewed,
     * token expiry checks may be inaccurate. The server-side 401 response handling
     * in intercept() provides a fallback for clock skew issues.
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

    /**
     * Data class for token refresh response deserialization.
     */
    private data class TokenRefreshResponse(
        @com.google.gson.annotations.SerializedName("access_token")
        val accessToken: String,
        @com.google.gson.annotations.SerializedName("refresh_token")
        val refreshToken: String,
        @com.google.gson.annotations.SerializedName("expires_at")
        val expiresAt: Long
    )
}
