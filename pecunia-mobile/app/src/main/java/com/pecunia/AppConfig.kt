package com.pecunia

import javax.inject.Inject
import javax.inject.Singleton

/**
 * Application configuration class.
 * Provides centralized access to:
 * - API URLs for different environments
 * - Network timeouts
 * - Feature flags
 * - Build variant information
 */
@Singleton
class AppConfig @Inject constructor() {

    // ============================================
    // BUILD CONFIGURATION
    // ============================================

    /**
     * Whether the app is running in debug mode.
     */
    val isDebug: Boolean = BuildConfig.DEBUG

    /**
     * Whether the app is configured for production environment.
     */
    val isProduction: Boolean = !BuildConfig.DEBUG

    /**
     * Application version name.
     */
    val versionName: String = BuildConfig.VERSION_NAME

    /**
     * Application version code.
     */
    val versionCode: Int = BuildConfig.VERSION_CODE

    // ============================================
    // API CONFIGURATION
    // ============================================

    /**
     * API URLs for different environments.
     */
    object ApiUrls {
        // Development environment
        const val DEV_BASE_URL = "https://api-dev.pecunia.com/v1/"
        const val DEV_AUTH_URL = "https://auth-dev.pecunia.com/"
        const val DEV_CDN_URL = "https://cdn-dev.pecunia.com/"

        // Staging environment
        const val STAGING_BASE_URL = "https://api-staging.pecunia.com/v1/"
        const val STAGING_AUTH_URL = "https://auth-staging.pecunia.com/"
        const val STAGING_CDN_URL = "https://cdn-staging.pecunia.com/"

        // Production environment
        const val PROD_BASE_URL = "https://api.pecunia.com/v1/"
        const val PROD_AUTH_URL = "https://auth.pecunia.com/"
        const val PROD_CDN_URL = "https://cdn.pecunia.com/"
    }

    /**
     * Get the current base API URL based on build variant.
     */
    val baseApiUrl: String
        get() = if (isProduction) ApiUrls.PROD_BASE_URL else ApiUrls.DEV_BASE_URL

    /**
     * Get the current auth API URL based on build variant.
     */
    val authApiUrl: String
        get() = if (isProduction) ApiUrls.PROD_AUTH_URL else ApiUrls.DEV_AUTH_URL

    /**
     * Get the current CDN URL based on build variant.
     */
    val cdnUrl: String
        get() = if (isProduction) ApiUrls.PROD_CDN_URL else ApiUrls.DEV_CDN_URL

    // ============================================
    // TIMEOUT CONFIGURATION
    // ============================================

    /**
     * Network timeout configuration in seconds.
     */
    object Timeouts {
        const val CONNECT_TIMEOUT_SECONDS = 30L
        const val READ_TIMEOUT_SECONDS = 30L
        const val WRITE_TIMEOUT_SECONDS = 30L
        const val CALL_TIMEOUT_SECONDS = 60L

        // Specific timeouts for different operations
        const val AUTH_TIMEOUT_SECONDS = 15L
        const val UPLOAD_TIMEOUT_SECONDS = 120L
        const val DOWNLOAD_TIMEOUT_SECONDS = 300L

        // Retry configuration
        const val MAX_RETRIES = 3
        const val RETRY_DELAY_MS = 1000L
        const val RETRY_MULTIPLIER = 2.0
    }

    // ============================================
    // CACHE CONFIGURATION
    // ============================================

    /**
     * Cache configuration for different data types.
     */
    object Cache {
        const val HTTP_CACHE_SIZE_MB = 50L
        const val IMAGE_CACHE_SIZE_MB = 100L
        const val DATABASE_CACHE_SIZE_MB = 25L

        // Cache durations in milliseconds
        const val TRANSACTIONS_CACHE_DURATION_MS = 5 * 60 * 1000L // 5 minutes
        const val ACCOUNTS_CACHE_DURATION_MS = 10 * 60 * 1000L // 10 minutes
        const val CATEGORIES_CACHE_DURATION_MS = 60 * 60 * 1000L // 1 hour
        const val USER_PROFILE_CACHE_DURATION_MS = 30 * 60 * 1000L // 30 minutes
    }

    // ============================================
    // FEATURE FLAGS
    // ============================================

    /**
     * Feature flags for controlling app behavior.
     * Can be overridden by remote config in production.
     */
    object FeatureFlags {
        // Authentication features
        var isBiometricAuthEnabled: Boolean = true
        var isSocialLoginEnabled: Boolean = true
        var isGoogleSignInEnabled: Boolean = true
        var isAppleSignInEnabled: Boolean = true

        // Core features
        var isReceiptScannerEnabled: Boolean = true
        var isMultiCurrencyEnabled: Boolean = true
        var isBudgetAlertsEnabled: Boolean = true
        var isRecurringTransactionsEnabled: Boolean = true

        // Banking features
        var isBankSyncEnabled: Boolean = true
        var isPlaidIntegrationEnabled: Boolean = true
        var isOpenBankingEnabled: Boolean = false // Coming soon

        // Analytics features
        var isAdvancedAnalyticsEnabled: Boolean = true
        var isExportPdfEnabled: Boolean = true
        var isExportCsvEnabled: Boolean = true

        // UI features
        var isDarkModeEnabled: Boolean = true
        var isCustomThemesEnabled: Boolean = false // Premium feature
        var isWidgetsEnabled: Boolean = true

        // Experimental features (debug only)
        var isExperimentalFeaturesEnabled: Boolean = BuildConfig.DEBUG
        var isAiCategorizationEnabled: Boolean = false
        var isSmartBudgetSuggestionsEnabled: Boolean = false

        // Debug features
        var isNetworkLoggingEnabled: Boolean = BuildConfig.DEBUG
        var isStrictModeEnabled: Boolean = BuildConfig.DEBUG
        var isLeakCanaryEnabled: Boolean = BuildConfig.DEBUG
    }

    // ============================================
    // PAGINATION CONFIGURATION
    // ============================================

    /**
     * Pagination settings for lists.
     */
    object Pagination {
        const val DEFAULT_PAGE_SIZE = 20
        const val TRANSACTIONS_PAGE_SIZE = 30
        const val SEARCH_PAGE_SIZE = 25
        const val NOTIFICATIONS_PAGE_SIZE = 15
        const val PREFETCH_DISTANCE = 5
    }

    // ============================================
    // SECURITY CONFIGURATION
    // ============================================

    /**
     * Security-related configuration.
     */
    object Security {
        const val TOKEN_REFRESH_THRESHOLD_SECONDS = 300 // Refresh token 5 minutes before expiry
        const val SESSION_TIMEOUT_MINUTES = 30
        const val MAX_LOGIN_ATTEMPTS = 5
        const val LOCKOUT_DURATION_MINUTES = 15
        const val PIN_LENGTH = 6
        const val BIOMETRIC_TIMEOUT_SECONDS = 30

        // Encryption
        const val KEY_ALIAS = "pecunia_key"
        const val KEY_STORE_TYPE = "AndroidKeyStore"
    }

    // ============================================
    // DEEP LINK CONFIGURATION
    // ============================================

    /**
     * Deep link configuration.
     */
    object DeepLinks {
        const val SCHEME = "pecunia"
        const val HOST = "app"
        const val WEB_HOST = "www.pecunia.com"
        const val HTTPS_SCHEME = "https"

        // Deep link paths
        const val PATH_TRANSACTION = "transaction"
        const val PATH_BUDGET = "budget"
        const val PATH_ACCOUNT = "account"
        const val PATH_AUTH = "auth"
        const val PATH_SETTINGS = "settings"
    }

    // ============================================
    // ANALYTICS CONFIGURATION
    // ============================================

    /**
     * Analytics event names and parameters.
     */
    object Analytics {
        // Screen events
        const val SCREEN_VIEW = "screen_view"
        const val SCREEN_NAME_PARAM = "screen_name"

        // User events
        const val USER_LOGIN = "user_login"
        const val USER_REGISTER = "user_register"
        const val USER_LOGOUT = "user_logout"

        // Transaction events
        const val TRANSACTION_CREATED = "transaction_created"
        const val TRANSACTION_UPDATED = "transaction_updated"
        const val TRANSACTION_DELETED = "transaction_deleted"
        const val RECEIPT_SCANNED = "receipt_scanned"

        // Budget events
        const val BUDGET_CREATED = "budget_created"
        const val BUDGET_UPDATED = "budget_updated"
        const val BUDGET_ALERT_TRIGGERED = "budget_alert_triggered"

        // Export events
        const val EXPORT_STARTED = "export_started"
        const val EXPORT_COMPLETED = "export_completed"
    }

    // ============================================
    // HELPER METHODS
    // ============================================

    /**
     * Check if a feature is enabled.
     */
    fun isFeatureEnabled(feature: Feature): Boolean {
        return when (feature) {
            Feature.BIOMETRIC_AUTH -> FeatureFlags.isBiometricAuthEnabled
            Feature.RECEIPT_SCANNER -> FeatureFlags.isReceiptScannerEnabled
            Feature.MULTI_CURRENCY -> FeatureFlags.isMultiCurrencyEnabled
            Feature.BANK_SYNC -> FeatureFlags.isBankSyncEnabled
            Feature.ADVANCED_ANALYTICS -> FeatureFlags.isAdvancedAnalyticsEnabled
            Feature.DARK_MODE -> FeatureFlags.isDarkModeEnabled
            Feature.WIDGETS -> FeatureFlags.isWidgetsEnabled
            Feature.AI_CATEGORIZATION -> FeatureFlags.isAiCategorizationEnabled
        }
    }

    /**
     * Enum of toggleable features.
     */
    enum class Feature {
        BIOMETRIC_AUTH,
        RECEIPT_SCANNER,
        MULTI_CURRENCY,
        BANK_SYNC,
        ADVANCED_ANALYTICS,
        DARK_MODE,
        WIDGETS,
        AI_CATEGORIZATION
    }
}
