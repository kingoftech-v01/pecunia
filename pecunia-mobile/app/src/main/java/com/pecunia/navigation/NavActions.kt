package com.pecunia.navigation

import androidx.navigation.NavController
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavOptions
import androidx.navigation.NavOptionsBuilder
import androidx.navigation.navOptions

/**
 * Navigation actions class that provides type-safe navigation methods.
 * This class encapsulates all navigation logic and provides a clean API
 * for navigating throughout the app.
 *
 * @param navController The NavController to use for navigation
 */
class NavActions(private val navController: NavController) {

    // ============================================
    // CURRENT STATE PROPERTIES
    // ============================================

    /**
     * Returns the current route as a string.
     */
    val currentRoute: String?
        get() = navController.currentDestination?.route

    /**
     * Returns true if we can navigate back.
     */
    val canNavigateBack: Boolean
        get() = navController.previousBackStackEntry != null

    // ============================================
    // GENERIC NAVIGATION
    // ============================================

    /**
     * Navigate back to the previous screen.
     * @return True if navigation was successful, false otherwise.
     */
    fun navigateBack(): Boolean {
        return navController.popBackStack()
    }

    /**
     * Navigate back to a specific route, popping all screens above it.
     * @param route The route to navigate back to
     * @param inclusive Whether to also pop the target route
     * @return True if navigation was successful, false otherwise.
     */
    fun navigateBackTo(route: String, inclusive: Boolean = false): Boolean {
        return navController.popBackStack(route, inclusive)
    }

    /**
     * Navigate back to the root of the current navigation graph.
     * @return True if navigation was successful, false otherwise.
     */
    fun popToRoot(): Boolean {
        val startDestination = navController.graph.findStartDestination()
        return navController.popBackStack(startDestination.id, inclusive = false)
    }

    /**
     * Navigate to a route with custom options.
     * @param route The destination route
     * @param builder Optional NavOptionsBuilder for customizing navigation behavior
     */
    fun navigateTo(route: String, builder: NavOptionsBuilder.() -> Unit = {}) {
        navController.navigate(route, navOptions(builder))
    }

    // ============================================
    // AUTH NAVIGATION
    // ============================================

    /**
     * Navigate to the login screen.
     * Clears the back stack if specified.
     */
    fun navigateToLogin(clearBackStack: Boolean = false) {
        navController.navigate(Route.Auth.Login.route) {
            if (clearBackStack) {
                popUpTo(navController.graph.findStartDestination().id) {
                    inclusive = true
                }
            }
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the registration screen.
     */
    fun navigateToRegister() {
        navController.navigate(Route.Auth.Register.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the forgot password screen.
     */
    fun navigateToForgotPassword() {
        navController.navigate(Route.Auth.ForgotPassword.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the reset password screen with a token.
     * @param token The password reset token
     */
    fun navigateToResetPassword(token: String) {
        navController.navigate(Route.Auth.ResetPassword.createRoute(token)) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the email verification screen.
     * @param email The email address to verify
     */
    fun navigateToVerifyEmail(email: String) {
        navController.navigate(Route.Auth.VerifyEmail.createRoute(email)) {
            launchSingleTop = true
        }
    }

    // ============================================
    // MAIN NAVIGATION (BOTTOM NAV)
    // ============================================

    /**
     * Navigate to the dashboard screen.
     * Uses single top and saves/restores state for bottom nav behavior.
     */
    fun navigateToDashboard() {
        navigateToBottomNavDestination(Route.Main.Dashboard.route)
    }

    /**
     * Navigate to the transactions list screen.
     */
    fun navigateToTransactions() {
        navigateToBottomNavDestination(Route.Main.Transactions.route)
    }

    /**
     * Navigate to the budgets screen.
     */
    fun navigateToBudgets() {
        navigateToBottomNavDestination(Route.Main.Budgets.route)
    }

    /**
     * Navigate to the banking screen.
     */
    fun navigateToBanking() {
        navigateToBottomNavDestination(Route.Main.Banking.route)
    }

    /**
     * Navigate to the settings screen.
     */
    fun navigateToSettings() {
        navigateToBottomNavDestination(Route.Main.Settings.route)
    }

    /**
     * Helper function for bottom navigation destinations.
     * Implements proper save/restore state behavior.
     */
    private fun navigateToBottomNavDestination(route: String) {
        navController.navigate(route) {
            // Pop up to the start destination of the graph to
            // avoid building up a large stack of destinations
            popUpTo(navController.graph.findStartDestination().id) {
                saveState = true
            }
            // Avoid multiple copies of the same destination when
            // reselecting the same item
            launchSingleTop = true
            // Restore state when reselecting a previously selected item
            restoreState = true
        }
    }

    // ============================================
    // TRANSACTION NAVIGATION
    // ============================================

    /**
     * Navigate to a transaction detail screen.
     * @param transactionId The ID of the transaction to display
     */
    fun navigateToTransactionDetail(transactionId: String) {
        navController.navigate(Route.Detail.TransactionDetail.createRoute(transactionId)) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the create transaction screen.
     * @param categoryId Optional pre-selected category ID
     */
    fun navigateToCreateTransaction(categoryId: String? = null) {
        navController.navigate(Route.Detail.TransactionCreate.createRoute(categoryId)) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the edit transaction screen.
     * @param transactionId The ID of the transaction to edit
     */
    fun navigateToEditTransaction(transactionId: String) {
        navController.navigate(Route.Detail.TransactionEdit.createRoute(transactionId)) {
            launchSingleTop = true
        }
    }

    // ============================================
    // BUDGET NAVIGATION
    // ============================================

    /**
     * Navigate to a budget detail screen.
     * @param budgetId The ID of the budget to display
     */
    fun navigateToBudgetDetail(budgetId: String) {
        navController.navigate(Route.Detail.BudgetDetail.createRoute(budgetId)) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the create budget screen.
     */
    fun navigateToCreateBudget() {
        navController.navigate(Route.Detail.BudgetCreate.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the edit budget screen.
     * @param budgetId The ID of the budget to edit
     */
    fun navigateToEditBudget(budgetId: String) {
        navController.navigate(Route.Detail.BudgetEdit.createRoute(budgetId)) {
            launchSingleTop = true
        }
    }

    // ============================================
    // ACCOUNT NAVIGATION
    // ============================================

    /**
     * Navigate to an account detail screen.
     * @param accountId The ID of the account to display
     */
    fun navigateToAccountDetail(accountId: String) {
        navController.navigate(Route.Detail.AccountDetail.createRoute(accountId)) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the account linking screen.
     * @param bankId Optional pre-selected bank ID
     */
    fun navigateToLinkAccount(bankId: String? = null) {
        navController.navigate(Route.Detail.AccountLink.createRoute(bankId)) {
            launchSingleTop = true
        }
    }

    // ============================================
    // CATEGORY NAVIGATION
    // ============================================

    /**
     * Navigate to a category detail screen.
     * @param categoryId The ID of the category to display
     */
    fun navigateToCategoryDetail(categoryId: String) {
        navController.navigate(Route.Detail.CategoryDetail.createRoute(categoryId)) {
            launchSingleTop = true
        }
    }

    // ============================================
    // OTHER NAVIGATION
    // ============================================

    /**
     * Navigate to the profile screen.
     */
    fun navigateToProfile() {
        navController.navigate(Route.Detail.Profile.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the notifications screen.
     */
    fun navigateToNotifications() {
        navController.navigate(Route.Detail.Notifications.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the export screen.
     * @param format The export format (default: "pdf")
     * @param startDate Optional start date filter
     * @param endDate Optional end date filter
     */
    fun navigateToExport(
        format: String = "pdf",
        startDate: String? = null,
        endDate: String? = null
    ) {
        navController.navigate(Route.Detail.Export.createRoute(format, startDate, endDate)) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to the search screen.
     * @param query Optional initial search query
     */
    fun navigateToSearch(query: String? = null) {
        navController.navigate(Route.Detail.Search.createRoute(query)) {
            launchSingleTop = true
        }
    }

    // ============================================
    // SETTINGS DETAIL NAVIGATION
    // ============================================

    /**
     * Navigate to security settings.
     */
    fun navigateToSecuritySettings() {
        navController.navigate(Route.SettingsDetail.Security.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to appearance settings.
     */
    fun navigateToAppearanceSettings() {
        navController.navigate(Route.SettingsDetail.Appearance.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to notification settings.
     */
    fun navigateToNotificationSettings() {
        navController.navigate(Route.SettingsDetail.Notifications.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to currency settings.
     */
    fun navigateToCurrencySettings() {
        navController.navigate(Route.SettingsDetail.Currency.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to language settings.
     */
    fun navigateToLanguageSettings() {
        navController.navigate(Route.SettingsDetail.Language.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to privacy settings.
     */
    fun navigateToPrivacySettings() {
        navController.navigate(Route.SettingsDetail.Privacy.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to help screen.
     */
    fun navigateToHelp() {
        navController.navigate(Route.SettingsDetail.Help.route) {
            launchSingleTop = true
        }
    }

    /**
     * Navigate to about screen.
     */
    fun navigateToAbout() {
        navController.navigate(Route.SettingsDetail.About.route) {
            launchSingleTop = true
        }
    }

    // ============================================
    // AUTH FLOW NAVIGATION
    // ============================================

    /**
     * Handle successful login - navigate to main app.
     * Clears the entire auth back stack.
     */
    fun onLoginSuccess() {
        navController.navigate(Route.Main.Graph.route) {
            popUpTo(Route.Auth.Graph.route) {
                inclusive = true
            }
            launchSingleTop = true
        }
    }

    /**
     * Handle logout - navigate back to login.
     * Clears the entire main app back stack.
     */
    fun onLogout() {
        navController.navigate(Route.Auth.Login.route) {
            popUpTo(Route.Main.Graph.route) {
                inclusive = true
            }
            launchSingleTop = true
        }
    }

    /**
     * Handle session expiry - navigate to login with message.
     * Clears all back stack.
     */
    fun onSessionExpired() {
        navController.navigate(Route.Auth.Login.route) {
            popUpTo(navController.graph.findStartDestination().id) {
                inclusive = true
            }
            launchSingleTop = true
        }
    }
}

/**
 * Sealed class representing navigation events that can be emitted from ViewModels.
 * These events are collected by the UI layer and converted to actual navigation calls.
 */
sealed class NavigationEvent {
    // Basic navigation
    data object NavigateBack : NavigationEvent()
    data object PopToRoot : NavigationEvent()
    data class NavigateBackTo(val route: String, val inclusive: Boolean = false) : NavigationEvent()

    // Auth navigation
    data object NavigateToLogin : NavigationEvent()
    data object NavigateToRegister : NavigationEvent()
    data object NavigateToForgotPassword : NavigationEvent()
    data class NavigateToResetPassword(val token: String) : NavigationEvent()
    data class NavigateToVerifyEmail(val email: String) : NavigationEvent()

    // Main navigation
    data object NavigateToDashboard : NavigationEvent()
    data object NavigateToTransactions : NavigationEvent()
    data object NavigateToBudgets : NavigationEvent()
    data object NavigateToBanking : NavigationEvent()
    data object NavigateToSettings : NavigationEvent()

    // Transaction navigation
    data class NavigateToTransactionDetail(val transactionId: String) : NavigationEvent()
    data class NavigateToCreateTransaction(val categoryId: String? = null) : NavigationEvent()
    data class NavigateToEditTransaction(val transactionId: String) : NavigationEvent()

    // Budget navigation
    data class NavigateToBudgetDetail(val budgetId: String) : NavigationEvent()
    data object NavigateToCreateBudget : NavigationEvent()
    data class NavigateToEditBudget(val budgetId: String) : NavigationEvent()

    // Account navigation
    data class NavigateToAccountDetail(val accountId: String) : NavigationEvent()
    data class NavigateToLinkAccount(val bankId: String? = null) : NavigationEvent()

    // Other navigation
    data object NavigateToProfile : NavigationEvent()
    data object NavigateToNotifications : NavigationEvent()
    data class NavigateToSearch(val query: String? = null) : NavigationEvent()
    data class NavigateToExport(
        val format: String = "pdf",
        val startDate: String? = null,
        val endDate: String? = null
    ) : NavigationEvent()

    // Auth flow events
    data object OnLoginSuccess : NavigationEvent()
    data object OnLogout : NavigationEvent()
    data object OnSessionExpired : NavigationEvent()
}

/**
 * Extension function to handle NavigationEvents using NavActions.
 * This is typically called in a LaunchedEffect collecting from a ViewModel's navigation flow.
 */
fun NavActions.handleNavigationEvent(event: NavigationEvent) {
    when (event) {
        // Basic navigation
        is NavigationEvent.NavigateBack -> navigateBack()
        is NavigationEvent.PopToRoot -> popToRoot()
        is NavigationEvent.NavigateBackTo -> navigateBackTo(event.route, event.inclusive)

        // Auth navigation
        is NavigationEvent.NavigateToLogin -> navigateToLogin()
        is NavigationEvent.NavigateToRegister -> navigateToRegister()
        is NavigationEvent.NavigateToForgotPassword -> navigateToForgotPassword()
        is NavigationEvent.NavigateToResetPassword -> navigateToResetPassword(event.token)
        is NavigationEvent.NavigateToVerifyEmail -> navigateToVerifyEmail(event.email)

        // Main navigation
        is NavigationEvent.NavigateToDashboard -> navigateToDashboard()
        is NavigationEvent.NavigateToTransactions -> navigateToTransactions()
        is NavigationEvent.NavigateToBudgets -> navigateToBudgets()
        is NavigationEvent.NavigateToBanking -> navigateToBanking()
        is NavigationEvent.NavigateToSettings -> navigateToSettings()

        // Transaction navigation
        is NavigationEvent.NavigateToTransactionDetail -> navigateToTransactionDetail(event.transactionId)
        is NavigationEvent.NavigateToCreateTransaction -> navigateToCreateTransaction(event.categoryId)
        is NavigationEvent.NavigateToEditTransaction -> navigateToEditTransaction(event.transactionId)

        // Budget navigation
        is NavigationEvent.NavigateToBudgetDetail -> navigateToBudgetDetail(event.budgetId)
        is NavigationEvent.NavigateToCreateBudget -> navigateToCreateBudget()
        is NavigationEvent.NavigateToEditBudget -> navigateToEditBudget(event.budgetId)

        // Account navigation
        is NavigationEvent.NavigateToAccountDetail -> navigateToAccountDetail(event.accountId)
        is NavigationEvent.NavigateToLinkAccount -> navigateToLinkAccount(event.bankId)

        // Other navigation
        is NavigationEvent.NavigateToProfile -> navigateToProfile()
        is NavigationEvent.NavigateToNotifications -> navigateToNotifications()
        is NavigationEvent.NavigateToSearch -> navigateToSearch(event.query)
        is NavigationEvent.NavigateToExport -> navigateToExport(event.format, event.startDate, event.endDate)

        // Auth flow events
        is NavigationEvent.OnLoginSuccess -> onLoginSuccess()
        is NavigationEvent.OnLogout -> onLogout()
        is NavigationEvent.OnSessionExpired -> onSessionExpired()
    }
}

/**
 * Composable-friendly way to remember NavActions.
 */
@androidx.compose.runtime.Composable
fun rememberNavActions(navController: NavController): NavActions {
    return androidx.compose.runtime.remember(navController) {
        NavActions(navController)
    }
}
