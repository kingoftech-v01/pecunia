package com.pecunia

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Comprehensive unit tests for AppConfig.
 * Tests API URLs, timeout values, cache settings, feature flags,
 * pagination, security, deep links, and analytics constants.
 */
class AppConfigTest {

    private lateinit var appConfig: AppConfig

    @Before
    fun setUp() {
        appConfig = AppConfig()
    }

    // ============================================
    // API URL Tests
    // ============================================

    @Test
    fun `dev base URL is properly formatted`() {
        assertEquals("https://api-dev.pecunia.com/v1/", AppConfig.ApiUrls.DEV_BASE_URL)
    }

    @Test
    fun `dev auth URL is properly formatted`() {
        assertEquals("https://auth-dev.pecunia.com/", AppConfig.ApiUrls.DEV_AUTH_URL)
    }

    @Test
    fun `dev CDN URL is properly formatted`() {
        assertEquals("https://cdn-dev.pecunia.com/", AppConfig.ApiUrls.DEV_CDN_URL)
    }

    @Test
    fun `staging base URL is properly formatted`() {
        assertEquals("https://api-staging.pecunia.com/v1/", AppConfig.ApiUrls.STAGING_BASE_URL)
    }

    @Test
    fun `staging auth URL is properly formatted`() {
        assertEquals("https://auth-staging.pecunia.com/", AppConfig.ApiUrls.STAGING_AUTH_URL)
    }

    @Test
    fun `staging CDN URL is properly formatted`() {
        assertEquals("https://cdn-staging.pecunia.com/", AppConfig.ApiUrls.STAGING_CDN_URL)
    }

    @Test
    fun `prod base URL is properly formatted`() {
        assertEquals("https://api.pecunia.com/v1/", AppConfig.ApiUrls.PROD_BASE_URL)
    }

    @Test
    fun `prod auth URL is properly formatted`() {
        assertEquals("https://auth.pecunia.com/", AppConfig.ApiUrls.PROD_AUTH_URL)
    }

    @Test
    fun `prod CDN URL is properly formatted`() {
        assertEquals("https://cdn.pecunia.com/", AppConfig.ApiUrls.PROD_CDN_URL)
    }

    @Test
    fun `all API URLs use HTTPS`() {
        assertTrue(AppConfig.ApiUrls.DEV_BASE_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.DEV_AUTH_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.DEV_CDN_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.STAGING_BASE_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.STAGING_AUTH_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.STAGING_CDN_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.PROD_BASE_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.PROD_AUTH_URL.startsWith("https://"))
        assertTrue(AppConfig.ApiUrls.PROD_CDN_URL.startsWith("https://"))
    }

    @Test
    fun `all API URLs end with slash`() {
        assertTrue(AppConfig.ApiUrls.DEV_BASE_URL.endsWith("/"))
        assertTrue(AppConfig.ApiUrls.DEV_AUTH_URL.endsWith("/"))
        assertTrue(AppConfig.ApiUrls.PROD_BASE_URL.endsWith("/"))
        assertTrue(AppConfig.ApiUrls.PROD_AUTH_URL.endsWith("/"))
    }

    // ============================================
    // Timeout Tests
    // ============================================

    @Test
    fun `connect timeout is 30 seconds`() {
        assertEquals(30L, AppConfig.Timeouts.CONNECT_TIMEOUT_SECONDS)
    }

    @Test
    fun `read timeout is 30 seconds`() {
        assertEquals(30L, AppConfig.Timeouts.READ_TIMEOUT_SECONDS)
    }

    @Test
    fun `write timeout is 30 seconds`() {
        assertEquals(30L, AppConfig.Timeouts.WRITE_TIMEOUT_SECONDS)
    }

    @Test
    fun `call timeout is 60 seconds`() {
        assertEquals(60L, AppConfig.Timeouts.CALL_TIMEOUT_SECONDS)
    }

    @Test
    fun `auth timeout is 15 seconds`() {
        assertEquals(15L, AppConfig.Timeouts.AUTH_TIMEOUT_SECONDS)
    }

    @Test
    fun `upload timeout is 120 seconds`() {
        assertEquals(120L, AppConfig.Timeouts.UPLOAD_TIMEOUT_SECONDS)
    }

    @Test
    fun `download timeout is 300 seconds`() {
        assertEquals(300L, AppConfig.Timeouts.DOWNLOAD_TIMEOUT_SECONDS)
    }

    @Test
    fun `max retries is 3`() {
        assertEquals(3, AppConfig.Timeouts.MAX_RETRIES)
    }

    @Test
    fun `retry delay is 1000ms`() {
        assertEquals(1000L, AppConfig.Timeouts.RETRY_DELAY_MS)
    }

    @Test
    fun `retry multiplier is 2`() {
        assertEquals(2.0, AppConfig.Timeouts.RETRY_MULTIPLIER, 0.001)
    }

    @Test
    fun `call timeout is greater than connect timeout`() {
        assertTrue(AppConfig.Timeouts.CALL_TIMEOUT_SECONDS > AppConfig.Timeouts.CONNECT_TIMEOUT_SECONDS)
    }

    @Test
    fun `upload timeout is greater than standard timeouts`() {
        assertTrue(AppConfig.Timeouts.UPLOAD_TIMEOUT_SECONDS > AppConfig.Timeouts.READ_TIMEOUT_SECONDS)
        assertTrue(AppConfig.Timeouts.UPLOAD_TIMEOUT_SECONDS > AppConfig.Timeouts.WRITE_TIMEOUT_SECONDS)
    }

    // ============================================
    // Cache Configuration Tests
    // ============================================

    @Test
    fun `HTTP cache size is 50 MB`() {
        assertEquals(50L, AppConfig.Cache.HTTP_CACHE_SIZE_MB)
    }

    @Test
    fun `image cache size is 100 MB`() {
        assertEquals(100L, AppConfig.Cache.IMAGE_CACHE_SIZE_MB)
    }

    @Test
    fun `database cache size is 25 MB`() {
        assertEquals(25L, AppConfig.Cache.DATABASE_CACHE_SIZE_MB)
    }

    @Test
    fun `transactions cache duration is 5 minutes`() {
        assertEquals(5 * 60 * 1000L, AppConfig.Cache.TRANSACTIONS_CACHE_DURATION_MS)
    }

    @Test
    fun `accounts cache duration is 10 minutes`() {
        assertEquals(10 * 60 * 1000L, AppConfig.Cache.ACCOUNTS_CACHE_DURATION_MS)
    }

    @Test
    fun `categories cache duration is 1 hour`() {
        assertEquals(60 * 60 * 1000L, AppConfig.Cache.CATEGORIES_CACHE_DURATION_MS)
    }

    @Test
    fun `user profile cache duration is 30 minutes`() {
        assertEquals(30 * 60 * 1000L, AppConfig.Cache.USER_PROFILE_CACHE_DURATION_MS)
    }

    @Test
    fun `categories cache duration is longest`() {
        assertTrue(AppConfig.Cache.CATEGORIES_CACHE_DURATION_MS > AppConfig.Cache.TRANSACTIONS_CACHE_DURATION_MS)
        assertTrue(AppConfig.Cache.CATEGORIES_CACHE_DURATION_MS > AppConfig.Cache.ACCOUNTS_CACHE_DURATION_MS)
        assertTrue(AppConfig.Cache.CATEGORIES_CACHE_DURATION_MS > AppConfig.Cache.USER_PROFILE_CACHE_DURATION_MS)
    }

    // ============================================
    // Pagination Configuration Tests
    // ============================================

    @Test
    fun `default page size is 20`() {
        assertEquals(20, AppConfig.Pagination.DEFAULT_PAGE_SIZE)
    }

    @Test
    fun `transactions page size is 30`() {
        assertEquals(30, AppConfig.Pagination.TRANSACTIONS_PAGE_SIZE)
    }

    @Test
    fun `search page size is 25`() {
        assertEquals(25, AppConfig.Pagination.SEARCH_PAGE_SIZE)
    }

    @Test
    fun `notifications page size is 15`() {
        assertEquals(15, AppConfig.Pagination.NOTIFICATIONS_PAGE_SIZE)
    }

    @Test
    fun `prefetch distance is 5`() {
        assertEquals(5, AppConfig.Pagination.PREFETCH_DISTANCE)
    }

    @Test
    fun `prefetch distance is less than default page size`() {
        assertTrue(AppConfig.Pagination.PREFETCH_DISTANCE < AppConfig.Pagination.DEFAULT_PAGE_SIZE)
    }

    // ============================================
    // Security Configuration Tests
    // ============================================

    @Test
    fun `token refresh threshold is 300 seconds`() {
        assertEquals(300, AppConfig.Security.TOKEN_REFRESH_THRESHOLD_SECONDS)
    }

    @Test
    fun `session timeout is 30 minutes`() {
        assertEquals(30, AppConfig.Security.SESSION_TIMEOUT_MINUTES)
    }

    @Test
    fun `max login attempts is 5`() {
        assertEquals(5, AppConfig.Security.MAX_LOGIN_ATTEMPTS)
    }

    @Test
    fun `lockout duration is 15 minutes`() {
        assertEquals(15, AppConfig.Security.LOCKOUT_DURATION_MINUTES)
    }

    @Test
    fun `PIN length is 6`() {
        assertEquals(6, AppConfig.Security.PIN_LENGTH)
    }

    @Test
    fun `biometric timeout is 30 seconds`() {
        assertEquals(30, AppConfig.Security.BIOMETRIC_TIMEOUT_SECONDS)
    }

    @Test
    fun `key alias is pecunia_key`() {
        assertEquals("pecunia_key", AppConfig.Security.KEY_ALIAS)
    }

    @Test
    fun `key store type is AndroidKeyStore`() {
        assertEquals("AndroidKeyStore", AppConfig.Security.KEY_STORE_TYPE)
    }

    // ============================================
    // Deep Link Configuration Tests
    // ============================================

    @Test
    fun `deep link scheme is pecunia`() {
        assertEquals("pecunia", AppConfig.DeepLinks.SCHEME)
    }

    @Test
    fun `deep link host is app`() {
        assertEquals("app", AppConfig.DeepLinks.HOST)
    }

    @Test
    fun `deep link web host is correct`() {
        assertEquals("www.pecunia.com", AppConfig.DeepLinks.WEB_HOST)
    }

    @Test
    fun `deep link https scheme is https`() {
        assertEquals("https", AppConfig.DeepLinks.HTTPS_SCHEME)
    }

    @Test
    fun `deep link paths are defined`() {
        assertEquals("transaction", AppConfig.DeepLinks.PATH_TRANSACTION)
        assertEquals("budget", AppConfig.DeepLinks.PATH_BUDGET)
        assertEquals("account", AppConfig.DeepLinks.PATH_ACCOUNT)
        assertEquals("auth", AppConfig.DeepLinks.PATH_AUTH)
        assertEquals("settings", AppConfig.DeepLinks.PATH_SETTINGS)
    }

    // ============================================
    // Analytics Configuration Tests
    // ============================================

    @Test
    fun `screen view event name is correct`() {
        assertEquals("screen_view", AppConfig.Analytics.SCREEN_VIEW)
    }

    @Test
    fun `screen name param is correct`() {
        assertEquals("screen_name", AppConfig.Analytics.SCREEN_NAME_PARAM)
    }

    @Test
    fun `user events are defined`() {
        assertEquals("user_login", AppConfig.Analytics.USER_LOGIN)
        assertEquals("user_register", AppConfig.Analytics.USER_REGISTER)
        assertEquals("user_logout", AppConfig.Analytics.USER_LOGOUT)
    }

    @Test
    fun `transaction events are defined`() {
        assertEquals("transaction_created", AppConfig.Analytics.TRANSACTION_CREATED)
        assertEquals("transaction_updated", AppConfig.Analytics.TRANSACTION_UPDATED)
        assertEquals("transaction_deleted", AppConfig.Analytics.TRANSACTION_DELETED)
        assertEquals("receipt_scanned", AppConfig.Analytics.RECEIPT_SCANNED)
    }

    @Test
    fun `budget events are defined`() {
        assertEquals("budget_created", AppConfig.Analytics.BUDGET_CREATED)
        assertEquals("budget_updated", AppConfig.Analytics.BUDGET_UPDATED)
        assertEquals("budget_alert_triggered", AppConfig.Analytics.BUDGET_ALERT_TRIGGERED)
    }

    @Test
    fun `export events are defined`() {
        assertEquals("export_started", AppConfig.Analytics.EXPORT_STARTED)
        assertEquals("export_completed", AppConfig.Analytics.EXPORT_COMPLETED)
    }

    // ============================================
    // Feature Flag Tests
    // ============================================

    @Test
    fun `biometric auth is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isBiometricAuthEnabled)
    }

    @Test
    fun `social login is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isSocialLoginEnabled)
    }

    @Test
    fun `Google sign in is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isGoogleSignInEnabled)
    }

    @Test
    fun `Apple sign in is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isAppleSignInEnabled)
    }

    @Test
    fun `receipt scanner is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isReceiptScannerEnabled)
    }

    @Test
    fun `multi currency is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isMultiCurrencyEnabled)
    }

    @Test
    fun `budget alerts is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isBudgetAlertsEnabled)
    }

    @Test
    fun `recurring transactions is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isRecurringTransactionsEnabled)
    }

    @Test
    fun `bank sync is enabled by default`() {
        assertTrue(AppConfig.FeatureFlags.isBankSyncEnabled)
    }

    @Test
    fun `open banking is disabled by default`() {
        assertFalse(AppConfig.FeatureFlags.isOpenBankingEnabled)
    }

    @Test
    fun `custom themes is disabled by default`() {
        assertFalse(AppConfig.FeatureFlags.isCustomThemesEnabled)
    }

    @Test
    fun `AI categorization is disabled by default`() {
        assertFalse(AppConfig.FeatureFlags.isAiCategorizationEnabled)
    }

    @Test
    fun `smart budget suggestions is disabled by default`() {
        assertFalse(AppConfig.FeatureFlags.isSmartBudgetSuggestionsEnabled)
    }

    @Test
    fun `feature flags can be toggled`() {
        val original = AppConfig.FeatureFlags.isOpenBankingEnabled
        AppConfig.FeatureFlags.isOpenBankingEnabled = !original
        assertEquals(!original, AppConfig.FeatureFlags.isOpenBankingEnabled)
        // Reset
        AppConfig.FeatureFlags.isOpenBankingEnabled = original
    }

    // ============================================
    // isFeatureEnabled Tests
    // ============================================

    @Test
    fun `isFeatureEnabled returns correct value for BIOMETRIC_AUTH`() {
        assertEquals(
            AppConfig.FeatureFlags.isBiometricAuthEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.BIOMETRIC_AUTH)
        )
    }

    @Test
    fun `isFeatureEnabled returns correct value for RECEIPT_SCANNER`() {
        assertEquals(
            AppConfig.FeatureFlags.isReceiptScannerEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.RECEIPT_SCANNER)
        )
    }

    @Test
    fun `isFeatureEnabled returns correct value for MULTI_CURRENCY`() {
        assertEquals(
            AppConfig.FeatureFlags.isMultiCurrencyEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.MULTI_CURRENCY)
        )
    }

    @Test
    fun `isFeatureEnabled returns correct value for BANK_SYNC`() {
        assertEquals(
            AppConfig.FeatureFlags.isBankSyncEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.BANK_SYNC)
        )
    }

    @Test
    fun `isFeatureEnabled returns correct value for ADVANCED_ANALYTICS`() {
        assertEquals(
            AppConfig.FeatureFlags.isAdvancedAnalyticsEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.ADVANCED_ANALYTICS)
        )
    }

    @Test
    fun `isFeatureEnabled returns correct value for DARK_MODE`() {
        assertEquals(
            AppConfig.FeatureFlags.isDarkModeEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.DARK_MODE)
        )
    }

    @Test
    fun `isFeatureEnabled returns correct value for WIDGETS`() {
        assertEquals(
            AppConfig.FeatureFlags.isWidgetsEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.WIDGETS)
        )
    }

    @Test
    fun `isFeatureEnabled returns correct value for AI_CATEGORIZATION`() {
        assertEquals(
            AppConfig.FeatureFlags.isAiCategorizationEnabled,
            appConfig.isFeatureEnabled(AppConfig.Feature.AI_CATEGORIZATION)
        )
    }

    @Test
    fun `isFeatureEnabled reflects runtime changes`() {
        val original = AppConfig.FeatureFlags.isAiCategorizationEnabled
        AppConfig.FeatureFlags.isAiCategorizationEnabled = true
        assertTrue(appConfig.isFeatureEnabled(AppConfig.Feature.AI_CATEGORIZATION))
        AppConfig.FeatureFlags.isAiCategorizationEnabled = false
        assertFalse(appConfig.isFeatureEnabled(AppConfig.Feature.AI_CATEGORIZATION))
        // Reset
        AppConfig.FeatureFlags.isAiCategorizationEnabled = original
    }

    // ============================================
    // Feature Enum Tests
    // ============================================

    @Test
    fun `Feature enum has all expected values`() {
        val features = AppConfig.Feature.entries
        assertEquals(8, features.size)
        assertTrue(features.contains(AppConfig.Feature.BIOMETRIC_AUTH))
        assertTrue(features.contains(AppConfig.Feature.RECEIPT_SCANNER))
        assertTrue(features.contains(AppConfig.Feature.MULTI_CURRENCY))
        assertTrue(features.contains(AppConfig.Feature.BANK_SYNC))
        assertTrue(features.contains(AppConfig.Feature.ADVANCED_ANALYTICS))
        assertTrue(features.contains(AppConfig.Feature.DARK_MODE))
        assertTrue(features.contains(AppConfig.Feature.WIDGETS))
        assertTrue(features.contains(AppConfig.Feature.AI_CATEGORIZATION))
    }
}
