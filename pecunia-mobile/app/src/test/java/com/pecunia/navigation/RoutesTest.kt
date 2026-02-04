package com.pecunia.navigation

import org.junit.Assert.*
import org.junit.Test

/**
 * Comprehensive unit tests for navigation Routes.
 * Tests route strings, createRoute functions, deep links,
 * requiresAuth/parentGraph extensions, and BottomNavItem enum.
 */
class RoutesTest {

    // ============================================
    // Auth Routes - Route Strings
    // ============================================

    @Test
    fun `Auth Graph route is auth_graph`() {
        assertEquals("auth_graph", Route.Auth.Graph.route)
    }

    @Test
    fun `Auth Login route is login`() {
        assertEquals("login", Route.Auth.Login.route)
    }

    @Test
    fun `Auth Register route is register`() {
        assertEquals("register", Route.Auth.Register.route)
    }

    @Test
    fun `Auth ForgotPassword route is forgot_password`() {
        assertEquals("forgot_password", Route.Auth.ForgotPassword.route)
    }

    @Test
    fun `Auth ResetPassword route contains token parameter`() {
        assertEquals("reset_password/{token}", Route.Auth.ResetPassword.route)
    }

    @Test
    fun `Auth VerifyEmail route contains email parameter`() {
        assertEquals("verify_email/{email}", Route.Auth.VerifyEmail.route)
    }

    // ============================================
    // Auth Routes - Deep Links
    // ============================================

    @Test
    fun `Auth Login has correct deep link URI`() {
        assertEquals("pecunia://auth/login", Route.Auth.Login.deepLinkUri)
    }

    @Test
    fun `Auth Register has correct deep link URI`() {
        assertEquals("pecunia://auth/register", Route.Auth.Register.deepLinkUri)
    }

    @Test
    fun `Auth ForgotPassword has correct deep link URI`() {
        assertEquals("pecunia://auth/forgot-password", Route.Auth.ForgotPassword.deepLinkUri)
    }

    @Test
    fun `Auth ResetPassword has correct deep link URI`() {
        assertEquals("pecunia://auth/reset-password/{token}", Route.Auth.ResetPassword.deepLinkUri)
    }

    @Test
    fun `Auth Graph has no deep link URI`() {
        assertNull(Route.Auth.Graph.deepLinkUri)
    }

    // ============================================
    // Auth Routes - createRoute functions
    // ============================================

    @Test
    fun `ResetPassword createRoute replaces token`() {
        val result = Route.Auth.ResetPassword.createRoute("abc123")
        assertEquals("reset_password/abc123", result)
    }

    @Test
    fun `ResetPassword createRoute with special characters`() {
        val result = Route.Auth.ResetPassword.createRoute("token-with-dashes")
        assertEquals("reset_password/token-with-dashes", result)
    }

    @Test
    fun `VerifyEmail createRoute replaces email`() {
        val result = Route.Auth.VerifyEmail.createRoute("user@example.com")
        assertEquals("verify_email/user@example.com", result)
    }

    // ============================================
    // Auth Routes - Argument Names
    // ============================================

    @Test
    fun `ResetPassword ARG_TOKEN is token`() {
        assertEquals("token", Route.Auth.ResetPassword.ARG_TOKEN)
    }

    @Test
    fun `VerifyEmail ARG_EMAIL is email`() {
        assertEquals("email", Route.Auth.VerifyEmail.ARG_EMAIL)
    }

    // ============================================
    // Main Routes - Route Strings
    // ============================================

    @Test
    fun `Main Graph route is main_graph`() {
        assertEquals("main_graph", Route.Main.Graph.route)
    }

    @Test
    fun `Main Dashboard route is dashboard`() {
        assertEquals("dashboard", Route.Main.Dashboard.route)
    }

    @Test
    fun `Main Transactions route is transactions`() {
        assertEquals("transactions", Route.Main.Transactions.route)
    }

    @Test
    fun `Main Budgets route is budgets`() {
        assertEquals("budgets", Route.Main.Budgets.route)
    }

    @Test
    fun `Main Banking route is banking`() {
        assertEquals("banking", Route.Main.Banking.route)
    }

    @Test
    fun `Main Settings route is settings`() {
        assertEquals("settings", Route.Main.Settings.route)
    }

    // ============================================
    // Main Routes - Deep Links
    // ============================================

    @Test
    fun `Main Dashboard has correct deep link URI`() {
        assertEquals("pecunia://main/dashboard", Route.Main.Dashboard.deepLinkUri)
    }

    @Test
    fun `Main Transactions has correct deep link URI`() {
        assertEquals("pecunia://main/transactions", Route.Main.Transactions.deepLinkUri)
    }

    @Test
    fun `Main Budgets has correct deep link URI`() {
        assertEquals("pecunia://main/budgets", Route.Main.Budgets.deepLinkUri)
    }

    @Test
    fun `Main Banking has correct deep link URI`() {
        assertEquals("pecunia://main/banking", Route.Main.Banking.deepLinkUri)
    }

    @Test
    fun `Main Settings has correct deep link URI`() {
        assertEquals("pecunia://main/settings", Route.Main.Settings.deepLinkUri)
    }

    @Test
    fun `Main Graph has no deep link URI`() {
        assertNull(Route.Main.Graph.deepLinkUri)
    }

    // ============================================
    // Detail Routes - Route Strings
    // ============================================

    @Test
    fun `TransactionDetail route contains transactionId parameter`() {
        assertEquals("transaction/{transactionId}", Route.Detail.TransactionDetail.route)
    }

    @Test
    fun `TransactionCreate route contains optional categoryId`() {
        assertEquals("transaction/create?categoryId={categoryId}", Route.Detail.TransactionCreate.route)
    }

    @Test
    fun `TransactionEdit route contains transactionId parameter`() {
        assertEquals("transaction/{transactionId}/edit", Route.Detail.TransactionEdit.route)
    }

    @Test
    fun `BudgetDetail route contains budgetId parameter`() {
        assertEquals("budget/{budgetId}", Route.Detail.BudgetDetail.route)
    }

    @Test
    fun `BudgetCreate route is budget_create`() {
        assertEquals("budget/create", Route.Detail.BudgetCreate.route)
    }

    @Test
    fun `BudgetEdit route contains budgetId parameter`() {
        assertEquals("budget/{budgetId}/edit", Route.Detail.BudgetEdit.route)
    }

    @Test
    fun `AccountDetail route contains accountId parameter`() {
        assertEquals("account/{accountId}", Route.Detail.AccountDetail.route)
    }

    @Test
    fun `AccountLink route contains optional bankId`() {
        assertEquals("account/link?bankId={bankId}", Route.Detail.AccountLink.route)
    }

    @Test
    fun `CategoryDetail route contains categoryId parameter`() {
        assertEquals("category/{categoryId}", Route.Detail.CategoryDetail.route)
    }

    @Test
    fun `Profile route is profile`() {
        assertEquals("profile", Route.Detail.Profile.route)
    }

    @Test
    fun `Notifications route is notifications`() {
        assertEquals("notifications", Route.Detail.Notifications.route)
    }

    @Test
    fun `Export route contains format, startDate, endDate`() {
        assertEquals("export?format={format}&startDate={startDate}&endDate={endDate}", Route.Detail.Export.route)
    }

    @Test
    fun `Search route contains optional query`() {
        assertEquals("search?query={query}", Route.Detail.Search.route)
    }

    // ============================================
    // Detail Routes - createRoute functions
    // ============================================

    @Test
    fun `TransactionDetail createRoute replaces transactionId`() {
        assertEquals("transaction/tx123", Route.Detail.TransactionDetail.createRoute("tx123"))
    }

    @Test
    fun `TransactionCreate createRoute without categoryId`() {
        assertEquals("transaction/create", Route.Detail.TransactionCreate.createRoute())
    }

    @Test
    fun `TransactionCreate createRoute with categoryId`() {
        assertEquals(
            "transaction/create?categoryId=cat1",
            Route.Detail.TransactionCreate.createRoute("cat1")
        )
    }

    @Test
    fun `TransactionCreate createRoute with null categoryId`() {
        assertEquals("transaction/create", Route.Detail.TransactionCreate.createRoute(null))
    }

    @Test
    fun `TransactionEdit createRoute replaces transactionId`() {
        assertEquals("transaction/tx456/edit", Route.Detail.TransactionEdit.createRoute("tx456"))
    }

    @Test
    fun `BudgetDetail createRoute replaces budgetId`() {
        assertEquals("budget/b123", Route.Detail.BudgetDetail.createRoute("b123"))
    }

    @Test
    fun `BudgetEdit createRoute replaces budgetId`() {
        assertEquals("budget/b123/edit", Route.Detail.BudgetEdit.createRoute("b123"))
    }

    @Test
    fun `AccountDetail createRoute replaces accountId`() {
        assertEquals("account/acc1", Route.Detail.AccountDetail.createRoute("acc1"))
    }

    @Test
    fun `AccountLink createRoute without bankId`() {
        assertEquals("account/link", Route.Detail.AccountLink.createRoute())
    }

    @Test
    fun `AccountLink createRoute with bankId`() {
        assertEquals("account/link?bankId=bank1", Route.Detail.AccountLink.createRoute("bank1"))
    }

    @Test
    fun `AccountLink createRoute with null bankId`() {
        assertEquals("account/link", Route.Detail.AccountLink.createRoute(null))
    }

    @Test
    fun `CategoryDetail createRoute replaces categoryId`() {
        assertEquals("category/cat1", Route.Detail.CategoryDetail.createRoute("cat1"))
    }

    @Test
    fun `Export createRoute with default format`() {
        val result = Route.Detail.Export.createRoute()
        assertEquals("export?format=pdf", result)
    }

    @Test
    fun `Export createRoute with custom format`() {
        val result = Route.Detail.Export.createRoute("csv")
        assertEquals("export?format=csv", result)
    }

    @Test
    fun `Export createRoute with all parameters`() {
        val result = Route.Detail.Export.createRoute("pdf", "2024-01-01", "2024-12-31")
        assertEquals("export?format=pdf&startDate=2024-01-01&endDate=2024-12-31", result)
    }

    @Test
    fun `Export createRoute with startDate only`() {
        val result = Route.Detail.Export.createRoute("pdf", "2024-01-01", null)
        assertEquals("export?format=pdf&startDate=2024-01-01", result)
    }

    @Test
    fun `Export createRoute with endDate only`() {
        val result = Route.Detail.Export.createRoute("pdf", null, "2024-12-31")
        assertEquals("export?format=pdf&endDate=2024-12-31", result)
    }

    @Test
    fun `Search createRoute without query`() {
        assertEquals("search", Route.Detail.Search.createRoute())
    }

    @Test
    fun `Search createRoute with query`() {
        assertEquals("search?query=groceries", Route.Detail.Search.createRoute("groceries"))
    }

    @Test
    fun `Search createRoute with null query`() {
        assertEquals("search", Route.Detail.Search.createRoute(null))
    }

    // ============================================
    // Detail Routes - Argument Names
    // ============================================

    @Test
    fun `TransactionDetail ARG_TRANSACTION_ID is correct`() {
        assertEquals("transactionId", Route.Detail.TransactionDetail.ARG_TRANSACTION_ID)
    }

    @Test
    fun `TransactionCreate ARG_CATEGORY_ID is correct`() {
        assertEquals("categoryId", Route.Detail.TransactionCreate.ARG_CATEGORY_ID)
    }

    @Test
    fun `TransactionEdit ARG_TRANSACTION_ID is correct`() {
        assertEquals("transactionId", Route.Detail.TransactionEdit.ARG_TRANSACTION_ID)
    }

    @Test
    fun `BudgetDetail ARG_BUDGET_ID is correct`() {
        assertEquals("budgetId", Route.Detail.BudgetDetail.ARG_BUDGET_ID)
    }

    @Test
    fun `BudgetEdit ARG_BUDGET_ID is correct`() {
        assertEquals("budgetId", Route.Detail.BudgetEdit.ARG_BUDGET_ID)
    }

    @Test
    fun `AccountDetail ARG_ACCOUNT_ID is correct`() {
        assertEquals("accountId", Route.Detail.AccountDetail.ARG_ACCOUNT_ID)
    }

    @Test
    fun `AccountLink ARG_BANK_ID is correct`() {
        assertEquals("bankId", Route.Detail.AccountLink.ARG_BANK_ID)
    }

    @Test
    fun `CategoryDetail ARG_CATEGORY_ID is correct`() {
        assertEquals("categoryId", Route.Detail.CategoryDetail.ARG_CATEGORY_ID)
    }

    @Test
    fun `Export ARG_FORMAT is correct`() {
        assertEquals("format", Route.Detail.Export.ARG_FORMAT)
    }

    @Test
    fun `Export ARG_START_DATE is correct`() {
        assertEquals("startDate", Route.Detail.Export.ARG_START_DATE)
    }

    @Test
    fun `Export ARG_END_DATE is correct`() {
        assertEquals("endDate", Route.Detail.Export.ARG_END_DATE)
    }

    @Test
    fun `Search ARG_QUERY is correct`() {
        assertEquals("query", Route.Detail.Search.ARG_QUERY)
    }

    // ============================================
    // Detail Routes - Deep Links
    // ============================================

    @Test
    fun `TransactionDetail has correct deep link URI`() {
        assertEquals("pecunia://transaction/{transactionId}", Route.Detail.TransactionDetail.deepLinkUri)
    }

    @Test
    fun `TransactionCreate has correct deep link URI`() {
        assertEquals("pecunia://transaction/create", Route.Detail.TransactionCreate.deepLinkUri)
    }

    @Test
    fun `BudgetDetail has correct deep link URI`() {
        assertEquals("pecunia://budget/{budgetId}", Route.Detail.BudgetDetail.deepLinkUri)
    }

    @Test
    fun `AccountDetail has correct deep link URI`() {
        assertEquals("pecunia://account/{accountId}", Route.Detail.AccountDetail.deepLinkUri)
    }

    @Test
    fun `Profile has correct deep link URI`() {
        assertEquals("pecunia://profile", Route.Detail.Profile.deepLinkUri)
    }

    @Test
    fun `Notifications has correct deep link URI`() {
        assertEquals("pecunia://notifications", Route.Detail.Notifications.deepLinkUri)
    }

    @Test
    fun `BudgetCreate has no deep link URI`() {
        assertNull(Route.Detail.BudgetCreate.deepLinkUri)
    }

    // ============================================
    // Settings Routes
    // ============================================

    @Test
    fun `SettingsDetail Security route is correct`() {
        assertEquals("settings/security", Route.SettingsDetail.Security.route)
    }

    @Test
    fun `SettingsDetail Appearance route is correct`() {
        assertEquals("settings/appearance", Route.SettingsDetail.Appearance.route)
    }

    @Test
    fun `SettingsDetail Notifications route is correct`() {
        assertEquals("settings/notifications", Route.SettingsDetail.Notifications.route)
    }

    @Test
    fun `SettingsDetail Currency route is correct`() {
        assertEquals("settings/currency", Route.SettingsDetail.Currency.route)
    }

    @Test
    fun `SettingsDetail Language route is correct`() {
        assertEquals("settings/language", Route.SettingsDetail.Language.route)
    }

    @Test
    fun `SettingsDetail Privacy route is correct`() {
        assertEquals("settings/privacy", Route.SettingsDetail.Privacy.route)
    }

    @Test
    fun `SettingsDetail Help route is correct`() {
        assertEquals("settings/help", Route.SettingsDetail.Help.route)
    }

    @Test
    fun `SettingsDetail About route is correct`() {
        assertEquals("settings/about", Route.SettingsDetail.About.route)
    }

    @Test
    fun `SettingsDetail routes have no deep link URIs`() {
        assertNull(Route.SettingsDetail.Security.deepLinkUri)
        assertNull(Route.SettingsDetail.Appearance.deepLinkUri)
        assertNull(Route.SettingsDetail.Notifications.deepLinkUri)
        assertNull(Route.SettingsDetail.Currency.deepLinkUri)
        assertNull(Route.SettingsDetail.Language.deepLinkUri)
        assertNull(Route.SettingsDetail.Privacy.deepLinkUri)
        assertNull(Route.SettingsDetail.Help.deepLinkUri)
        assertNull(Route.SettingsDetail.About.deepLinkUri)
    }

    // ============================================
    // requiresAuth Extension Tests
    // ============================================

    @Test
    fun `Auth routes do not require authentication`() {
        assertFalse(Route.Auth.Login.requiresAuth())
        assertFalse(Route.Auth.Register.requiresAuth())
        assertFalse(Route.Auth.ForgotPassword.requiresAuth())
        assertFalse(Route.Auth.ResetPassword.requiresAuth())
        assertFalse(Route.Auth.VerifyEmail.requiresAuth())
        assertFalse(Route.Auth.Graph.requiresAuth())
    }

    @Test
    fun `Main routes require authentication`() {
        assertTrue(Route.Main.Dashboard.requiresAuth())
        assertTrue(Route.Main.Transactions.requiresAuth())
        assertTrue(Route.Main.Budgets.requiresAuth())
        assertTrue(Route.Main.Banking.requiresAuth())
        assertTrue(Route.Main.Settings.requiresAuth())
    }

    @Test
    fun `Detail routes require authentication`() {
        assertTrue(Route.Detail.TransactionDetail.requiresAuth())
        assertTrue(Route.Detail.TransactionCreate.requiresAuth())
        assertTrue(Route.Detail.BudgetDetail.requiresAuth())
        assertTrue(Route.Detail.BudgetCreate.requiresAuth())
        assertTrue(Route.Detail.Profile.requiresAuth())
        assertTrue(Route.Detail.Notifications.requiresAuth())
    }

    @Test
    fun `SettingsDetail routes require authentication`() {
        assertTrue(Route.SettingsDetail.Security.requiresAuth())
        assertTrue(Route.SettingsDetail.Appearance.requiresAuth())
        assertTrue(Route.SettingsDetail.Privacy.requiresAuth())
    }

    // ============================================
    // parentGraph Extension Tests
    // ============================================

    @Test
    fun `Auth routes return Auth Graph as parent`() {
        assertEquals(Route.Auth.Graph, Route.Auth.Login.parentGraph())
        assertEquals(Route.Auth.Graph, Route.Auth.Register.parentGraph())
        assertEquals(Route.Auth.Graph, Route.Auth.ForgotPassword.parentGraph())
    }

    @Test
    fun `Main routes return Main Graph as parent`() {
        assertEquals(Route.Main.Graph, Route.Main.Dashboard.parentGraph())
        assertEquals(Route.Main.Graph, Route.Main.Transactions.parentGraph())
        assertEquals(Route.Main.Graph, Route.Main.Budgets.parentGraph())
    }

    @Test
    fun `Detail routes return Main Graph as parent`() {
        assertEquals(Route.Main.Graph, Route.Detail.TransactionDetail.parentGraph())
        assertEquals(Route.Main.Graph, Route.Detail.BudgetDetail.parentGraph())
        assertEquals(Route.Main.Graph, Route.Detail.Profile.parentGraph())
    }

    @Test
    fun `SettingsDetail routes return Main Graph as parent`() {
        assertEquals(Route.Main.Graph, Route.SettingsDetail.Security.parentGraph())
        assertEquals(Route.Main.Graph, Route.SettingsDetail.About.parentGraph())
    }

    // ============================================
    // BottomNavItem Tests
    // ============================================

    @Test
    fun `BottomNavItem has 4 entries`() {
        assertEquals(4, BottomNavItem.entries.size)
    }

    @Test
    fun `DASHBOARD item points to correct route`() {
        assertEquals(Route.Main.Dashboard, BottomNavItem.DASHBOARD.route)
    }

    @Test
    fun `TRANSACTIONS item points to correct route`() {
        assertEquals(Route.Main.Transactions, BottomNavItem.TRANSACTIONS.route)
    }

    @Test
    fun `BUDGETS item points to correct route`() {
        assertEquals(Route.Main.Budgets, BottomNavItem.BUDGETS.route)
    }

    @Test
    fun `SETTINGS item points to correct route`() {
        assertEquals(Route.Main.Settings, BottomNavItem.SETTINGS.route)
    }

    @Test
    fun `DASHBOARD item has correct icon`() {
        assertEquals("dashboard", BottomNavItem.DASHBOARD.icon)
    }

    @Test
    fun `TRANSACTIONS item has correct icon`() {
        assertEquals("receipt_long", BottomNavItem.TRANSACTIONS.icon)
    }

    @Test
    fun `BUDGETS item has correct icon`() {
        assertEquals("savings", BottomNavItem.BUDGETS.icon)
    }

    @Test
    fun `SETTINGS item has correct icon`() {
        assertEquals("settings", BottomNavItem.SETTINGS.icon)
    }

    // ============================================
    // Route Uniqueness Tests
    // ============================================

    @Test
    fun `all main route strings are unique`() {
        val routes = listOf(
            Route.Main.Dashboard.route,
            Route.Main.Transactions.route,
            Route.Main.Budgets.route,
            Route.Main.Banking.route,
            Route.Main.Settings.route
        )
        assertEquals(routes.size, routes.toSet().size)
    }

    @Test
    fun `all auth route strings are unique`() {
        val routes = listOf(
            Route.Auth.Login.route,
            Route.Auth.Register.route,
            Route.Auth.ForgotPassword.route,
            Route.Auth.ResetPassword.route,
            Route.Auth.VerifyEmail.route
        )
        assertEquals(routes.size, routes.toSet().size)
    }

    @Test
    fun `all settings detail route strings are unique`() {
        val routes = listOf(
            Route.SettingsDetail.Security.route,
            Route.SettingsDetail.Appearance.route,
            Route.SettingsDetail.Notifications.route,
            Route.SettingsDetail.Currency.route,
            Route.SettingsDetail.Language.route,
            Route.SettingsDetail.Privacy.route,
            Route.SettingsDetail.Help.route,
            Route.SettingsDetail.About.route
        )
        assertEquals(routes.size, routes.toSet().size)
    }
}
