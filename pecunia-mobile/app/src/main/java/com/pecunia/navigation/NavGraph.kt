package com.pecunia.navigation

import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavBackStackEntry
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.navigation

/**
 * Animation duration constants for navigation transitions.
 */
private object NavAnimationDefaults {
    const val DURATION_MEDIUM = 300
    const val DURATION_SHORT = 200
    const val DURATION_LONG = 400
    const val INITIAL_SCALE = 0.92f
    const val TARGET_SCALE = 1.0f
}

/**
 * Main navigation graph composable that sets up the entire navigation structure.
 *
 * @param navController The NavHostController for managing navigation
 * @param startDestination The initial destination route
 * @param paddingValues Padding to apply to the NavHost content
 * @param isAuthenticated Whether the user is currently authenticated
 * @param onAuthStateChange Callback when authentication state changes
 */
@Composable
fun PecuniaNavGraph(
    navController: NavHostController,
    startDestination: String = Route.Auth.Graph.route,
    paddingValues: PaddingValues = PaddingValues(),
    isAuthenticated: Boolean = false,
    onAuthStateChange: (Boolean) -> Unit = {}
) {
    NavHost(
        navController = navController,
        startDestination = if (isAuthenticated) Route.Main.Graph.route else Route.Auth.Graph.route,
        modifier = Modifier.padding(paddingValues),
        enterTransition = { defaultEnterTransition() },
        exitTransition = { defaultExitTransition() },
        popEnterTransition = { defaultPopEnterTransition() },
        popExitTransition = { defaultPopExitTransition() }
    ) {
        // Auth navigation graph
        authNavGraph(
            navController = navController,
            onLoginSuccess = {
                onAuthStateChange(true)
                navController.navigate(Route.Main.Graph.route) {
                    popUpTo(Route.Auth.Graph.route) { inclusive = true }
                }
            }
        )

        // Main navigation graph
        mainNavGraph(
            navController = navController,
            onLogout = {
                onAuthStateChange(false)
                navController.navigate(Route.Auth.Graph.route) {
                    popUpTo(Route.Main.Graph.route) { inclusive = true }
                }
            }
        )

        // Detail screens (outside of nested graphs for easier deep linking)
        detailNavGraph(navController = navController)

        // Settings detail screens
        settingsDetailNavGraph(navController = navController)
    }
}

/**
 * Authentication navigation graph containing login, register, and password recovery screens.
 */
private fun NavGraphBuilder.authNavGraph(
    navController: NavHostController,
    onLoginSuccess: () -> Unit
) {
    navigation(
        startDestination = Route.Auth.Login.route,
        route = Route.Auth.Graph.route
    ) {
        // Login Screen
        composable(
            route = Route.Auth.Login.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Auth.Login.deepLinkUri
                }
            ),
            enterTransition = { fadeIn(animationSpec = tween(NavAnimationDefaults.DURATION_MEDIUM)) },
            exitTransition = { fadeOut(animationSpec = tween(NavAnimationDefaults.DURATION_SHORT)) }
        ) {
            // TODO: Replace with actual LoginScreen composable
            // LoginScreen(
            //     onLoginSuccess = onLoginSuccess,
            //     onNavigateToRegister = { navController.navigate(Route.Auth.Register.route) },
            //     onNavigateToForgotPassword = { navController.navigate(Route.Auth.ForgotPassword.route) }
            // )
            PlaceholderScreen(screenName = "Login")
        }

        // Register Screen
        composable(
            route = Route.Auth.Register.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Auth.Register.deepLinkUri
                }
            ),
            enterTransition = { slideInFromRight() },
            exitTransition = { slideOutToRight() },
            popEnterTransition = { slideInFromLeft() },
            popExitTransition = { slideOutToLeft() }
        ) {
            // TODO: Replace with actual RegisterScreen composable
            // RegisterScreen(
            //     onRegisterSuccess = { email ->
            //         navController.navigate(Route.Auth.VerifyEmail.createRoute(email))
            //     },
            //     onNavigateToLogin = { navController.popBackStack() }
            // )
            PlaceholderScreen(screenName = "Register")
        }

        // Forgot Password Screen
        composable(
            route = Route.Auth.ForgotPassword.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Auth.ForgotPassword.deepLinkUri
                }
            ),
            enterTransition = { slideInFromRight() },
            exitTransition = { slideOutToRight() },
            popEnterTransition = { slideInFromLeft() },
            popExitTransition = { slideOutToLeft() }
        ) {
            // TODO: Replace with actual ForgotPasswordScreen composable
            // ForgotPasswordScreen(
            //     onResetLinkSent = { navController.popBackStack() },
            //     onNavigateBack = { navController.popBackStack() }
            // )
            PlaceholderScreen(screenName = "Forgot Password")
        }

        // Reset Password Screen (with token argument)
        composable(
            route = Route.Auth.ResetPassword.route,
            arguments = Route.Auth.ResetPassword.arguments,
            deepLinks = Route.Auth.ResetPassword.deepLinks,
            enterTransition = { slideInFromBottom() },
            exitTransition = { slideOutToBottom() }
        ) { backStackEntry ->
            val token = backStackEntry.arguments?.getString(Route.Auth.ResetPassword.ARG_TOKEN) ?: ""
            // TODO: Replace with actual ResetPasswordScreen composable
            // ResetPasswordScreen(
            //     token = token,
            //     onPasswordReset = {
            //         navController.navigate(Route.Auth.Login.route) {
            //             popUpTo(Route.Auth.Graph.route) { inclusive = false }
            //         }
            //     }
            // )
            PlaceholderScreen(screenName = "Reset Password (Token: $token)")
        }

        // Verify Email Screen
        composable(
            route = Route.Auth.VerifyEmail.route,
            arguments = Route.Auth.VerifyEmail.arguments,
            enterTransition = { slideInFromRight() },
            exitTransition = { fadeOut() }
        ) { backStackEntry ->
            val email = backStackEntry.arguments?.getString(Route.Auth.VerifyEmail.ARG_EMAIL) ?: ""
            // TODO: Replace with actual VerifyEmailScreen composable
            // VerifyEmailScreen(
            //     email = email,
            //     onVerified = onLoginSuccess,
            //     onResendCode = { /* resend verification code */ }
            // )
            PlaceholderScreen(screenName = "Verify Email ($email)")
        }
    }
}

/**
 * Main navigation graph containing the primary app screens accessed via bottom navigation.
 */
private fun NavGraphBuilder.mainNavGraph(
    navController: NavHostController,
    onLogout: () -> Unit
) {
    navigation(
        startDestination = Route.Main.Dashboard.route,
        route = Route.Main.Graph.route
    ) {
        // Dashboard Screen
        composable(
            route = Route.Main.Dashboard.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Main.Dashboard.deepLinkUri
                }
            ),
            enterTransition = { fadeIn(tween(NavAnimationDefaults.DURATION_SHORT)) },
            exitTransition = { fadeOut(tween(NavAnimationDefaults.DURATION_SHORT)) }
        ) {
            // TODO: Replace with actual DashboardScreen composable
            // DashboardScreen(
            //     onNavigateToTransactionDetail = { id ->
            //         navController.navigate(Route.Detail.TransactionDetail.createRoute(id))
            //     },
            //     onNavigateToNotifications = {
            //         navController.navigate(Route.Detail.Notifications.route)
            //     },
            //     onNavigateToSearch = {
            //         navController.navigate(Route.Detail.Search.createRoute())
            //     }
            // )
            PlaceholderScreen(screenName = "Dashboard")
        }

        // Transactions Screen
        composable(
            route = Route.Main.Transactions.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Main.Transactions.deepLinkUri
                }
            ),
            enterTransition = { fadeIn(tween(NavAnimationDefaults.DURATION_SHORT)) },
            exitTransition = { fadeOut(tween(NavAnimationDefaults.DURATION_SHORT)) }
        ) {
            // TODO: Replace with actual TransactionsScreen composable
            // TransactionsScreen(
            //     onNavigateToTransactionDetail = { id ->
            //         navController.navigate(Route.Detail.TransactionDetail.createRoute(id))
            //     },
            //     onNavigateToCreateTransaction = {
            //         navController.navigate(Route.Detail.TransactionCreate.createRoute())
            //     },
            //     onNavigateToSearch = { query ->
            //         navController.navigate(Route.Detail.Search.createRoute(query))
            //     }
            // )
            PlaceholderScreen(screenName = "Transactions")
        }

        // Budgets Screen
        composable(
            route = Route.Main.Budgets.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Main.Budgets.deepLinkUri
                }
            ),
            enterTransition = { fadeIn(tween(NavAnimationDefaults.DURATION_SHORT)) },
            exitTransition = { fadeOut(tween(NavAnimationDefaults.DURATION_SHORT)) }
        ) {
            // TODO: Replace with actual BudgetsScreen composable
            // BudgetsScreen(
            //     onNavigateToBudgetDetail = { id ->
            //         navController.navigate(Route.Detail.BudgetDetail.createRoute(id))
            //     },
            //     onNavigateToCreateBudget = {
            //         navController.navigate(Route.Detail.BudgetCreate.route)
            //     }
            // )
            PlaceholderScreen(screenName = "Budgets")
        }

        // Banking Screen
        composable(
            route = Route.Main.Banking.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Main.Banking.deepLinkUri
                }
            ),
            enterTransition = { fadeIn(tween(NavAnimationDefaults.DURATION_SHORT)) },
            exitTransition = { fadeOut(tween(NavAnimationDefaults.DURATION_SHORT)) }
        ) {
            // TODO: Replace with actual BankingScreen composable
            // BankingScreen(
            //     onNavigateToAccountDetail = { id ->
            //         navController.navigate(Route.Detail.AccountDetail.createRoute(id))
            //     },
            //     onNavigateToLinkAccount = {
            //         navController.navigate(Route.Detail.AccountLink.createRoute())
            //     }
            // )
            PlaceholderScreen(screenName = "Banking")
        }

        // Settings Screen
        composable(
            route = Route.Main.Settings.route,
            deepLinks = listOf(
                androidx.navigation.navDeepLink {
                    uriPattern = Route.Main.Settings.deepLinkUri
                }
            ),
            enterTransition = { fadeIn(tween(NavAnimationDefaults.DURATION_SHORT)) },
            exitTransition = { fadeOut(tween(NavAnimationDefaults.DURATION_SHORT)) }
        ) {
            // TODO: Replace with actual SettingsScreen composable
            // SettingsScreen(
            //     onNavigateToProfile = { navController.navigate(Route.Detail.Profile.route) },
            //     onNavigateToSecurity = { navController.navigate(Route.SettingsDetail.Security.route) },
            //     onNavigateToAppearance = { navController.navigate(Route.SettingsDetail.Appearance.route) },
            //     onNavigateToNotifications = { navController.navigate(Route.SettingsDetail.Notifications.route) },
            //     onNavigateToCurrency = { navController.navigate(Route.SettingsDetail.Currency.route) },
            //     onNavigateToLanguage = { navController.navigate(Route.SettingsDetail.Language.route) },
            //     onNavigateToPrivacy = { navController.navigate(Route.SettingsDetail.Privacy.route) },
            //     onNavigateToHelp = { navController.navigate(Route.SettingsDetail.Help.route) },
            //     onNavigateToAbout = { navController.navigate(Route.SettingsDetail.About.route) },
            //     onLogout = onLogout
            // )
            PlaceholderScreen(screenName = "Settings")
        }
    }
}

/**
 * Detail navigation graph containing all detail/form screens.
 */
private fun NavGraphBuilder.detailNavGraph(
    navController: NavHostController
) {
    // Transaction Detail
    composable(
        route = Route.Detail.TransactionDetail.route,
        arguments = Route.Detail.TransactionDetail.arguments,
        deepLinks = Route.Detail.TransactionDetail.deepLinks,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() },
        popEnterTransition = { slideInFromLeft() },
        popExitTransition = { slideOutToLeft() }
    ) { backStackEntry ->
        val transactionId = backStackEntry.arguments
            ?.getString(Route.Detail.TransactionDetail.ARG_TRANSACTION_ID) ?: ""
        // TODO: Replace with actual TransactionDetailScreen composable
        // TransactionDetailScreen(
        //     transactionId = transactionId,
        //     onNavigateBack = { navController.popBackStack() },
        //     onNavigateToEdit = {
        //         navController.navigate(Route.Detail.TransactionEdit.createRoute(transactionId))
        //     }
        // )
        PlaceholderScreen(screenName = "Transaction Detail ($transactionId)")
    }

    // Transaction Create
    composable(
        route = Route.Detail.TransactionCreate.route,
        arguments = Route.Detail.TransactionCreate.arguments,
        enterTransition = { slideInFromBottom() },
        exitTransition = { slideOutToBottom() }
    ) { backStackEntry ->
        val categoryId = backStackEntry.arguments
            ?.getString(Route.Detail.TransactionCreate.ARG_CATEGORY_ID)
        // TODO: Replace with actual TransactionFormScreen composable
        // TransactionFormScreen(
        //     transactionId = null,
        //     preselectedCategoryId = categoryId,
        //     onNavigateBack = { navController.popBackStack() },
        //     onSaveSuccess = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Create Transaction (Category: ${categoryId ?: "None"})")
    }

    // Transaction Edit
    composable(
        route = Route.Detail.TransactionEdit.route,
        arguments = Route.Detail.TransactionEdit.arguments,
        enterTransition = { slideInFromBottom() },
        exitTransition = { slideOutToBottom() }
    ) { backStackEntry ->
        val transactionId = backStackEntry.arguments
            ?.getString(Route.Detail.TransactionEdit.ARG_TRANSACTION_ID) ?: ""
        // TODO: Replace with actual TransactionFormScreen composable
        // TransactionFormScreen(
        //     transactionId = transactionId,
        //     preselectedCategoryId = null,
        //     onNavigateBack = { navController.popBackStack() },
        //     onSaveSuccess = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Edit Transaction ($transactionId)")
    }

    // Budget Detail
    composable(
        route = Route.Detail.BudgetDetail.route,
        arguments = Route.Detail.BudgetDetail.arguments,
        deepLinks = Route.Detail.BudgetDetail.deepLinks,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() },
        popEnterTransition = { slideInFromLeft() },
        popExitTransition = { slideOutToLeft() }
    ) { backStackEntry ->
        val budgetId = backStackEntry.arguments
            ?.getString(Route.Detail.BudgetDetail.ARG_BUDGET_ID) ?: ""
        // TODO: Replace with actual BudgetDetailScreen composable
        // BudgetDetailScreen(
        //     budgetId = budgetId,
        //     onNavigateBack = { navController.popBackStack() },
        //     onNavigateToEdit = {
        //         navController.navigate(Route.Detail.BudgetEdit.createRoute(budgetId))
        //     }
        // )
        PlaceholderScreen(screenName = "Budget Detail ($budgetId)")
    }

    // Budget Create
    composable(
        route = Route.Detail.BudgetCreate.route,
        enterTransition = { slideInFromBottom() },
        exitTransition = { slideOutToBottom() }
    ) {
        // TODO: Replace with actual BudgetFormScreen composable
        // BudgetFormScreen(
        //     budgetId = null,
        //     onNavigateBack = { navController.popBackStack() },
        //     onSaveSuccess = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Create Budget")
    }

    // Budget Edit
    composable(
        route = Route.Detail.BudgetEdit.route,
        arguments = Route.Detail.BudgetEdit.arguments,
        enterTransition = { slideInFromBottom() },
        exitTransition = { slideOutToBottom() }
    ) { backStackEntry ->
        val budgetId = backStackEntry.arguments
            ?.getString(Route.Detail.BudgetEdit.ARG_BUDGET_ID) ?: ""
        // TODO: Replace with actual BudgetFormScreen composable
        // BudgetFormScreen(
        //     budgetId = budgetId,
        //     onNavigateBack = { navController.popBackStack() },
        //     onSaveSuccess = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Edit Budget ($budgetId)")
    }

    // Account Detail
    composable(
        route = Route.Detail.AccountDetail.route,
        arguments = Route.Detail.AccountDetail.arguments,
        deepLinks = Route.Detail.AccountDetail.deepLinks,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() },
        popEnterTransition = { slideInFromLeft() },
        popExitTransition = { slideOutToLeft() }
    ) { backStackEntry ->
        val accountId = backStackEntry.arguments
            ?.getString(Route.Detail.AccountDetail.ARG_ACCOUNT_ID) ?: ""
        // TODO: Replace with actual AccountDetailScreen composable
        // AccountDetailScreen(
        //     accountId = accountId,
        //     onNavigateBack = { navController.popBackStack() },
        //     onNavigateToTransaction = { txId ->
        //         navController.navigate(Route.Detail.TransactionDetail.createRoute(txId))
        //     }
        // )
        PlaceholderScreen(screenName = "Account Detail ($accountId)")
    }

    // Account Link
    composable(
        route = Route.Detail.AccountLink.route,
        arguments = Route.Detail.AccountLink.arguments,
        enterTransition = { slideInFromBottom() },
        exitTransition = { slideOutToBottom() }
    ) { backStackEntry ->
        val bankId = backStackEntry.arguments
            ?.getString(Route.Detail.AccountLink.ARG_BANK_ID)
        // TODO: Replace with actual AccountLinkScreen composable
        // AccountLinkScreen(
        //     preselectedBankId = bankId,
        //     onNavigateBack = { navController.popBackStack() },
        //     onLinkSuccess = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Link Account (Bank: ${bankId ?: "Select"})")
    }

    // Category Detail
    composable(
        route = Route.Detail.CategoryDetail.route,
        arguments = Route.Detail.CategoryDetail.arguments,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) { backStackEntry ->
        val categoryId = backStackEntry.arguments
            ?.getString(Route.Detail.CategoryDetail.ARG_CATEGORY_ID) ?: ""
        // TODO: Replace with actual CategoryDetailScreen composable
        // CategoryDetailScreen(
        //     categoryId = categoryId,
        //     onNavigateBack = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Category Detail ($categoryId)")
    }

    // Profile
    composable(
        route = Route.Detail.Profile.route,
        deepLinks = listOf(
            androidx.navigation.navDeepLink {
                uriPattern = Route.Detail.Profile.deepLinkUri
            }
        ),
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        // TODO: Replace with actual ProfileScreen composable
        // ProfileScreen(
        //     onNavigateBack = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Profile")
    }

    // Notifications
    composable(
        route = Route.Detail.Notifications.route,
        deepLinks = listOf(
            androidx.navigation.navDeepLink {
                uriPattern = Route.Detail.Notifications.deepLinkUri
            }
        ),
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        // TODO: Replace with actual NotificationsScreen composable
        // NotificationsScreen(
        //     onNavigateBack = { navController.popBackStack() },
        //     onNavigateToTransaction = { txId ->
        //         navController.navigate(Route.Detail.TransactionDetail.createRoute(txId))
        //     }
        // )
        PlaceholderScreen(screenName = "Notifications")
    }

    // Export
    composable(
        route = Route.Detail.Export.route,
        arguments = Route.Detail.Export.arguments,
        enterTransition = { slideInFromBottom() },
        exitTransition = { slideOutToBottom() }
    ) { backStackEntry ->
        val format = backStackEntry.arguments
            ?.getString(Route.Detail.Export.ARG_FORMAT) ?: "pdf"
        val startDate = backStackEntry.arguments
            ?.getString(Route.Detail.Export.ARG_START_DATE)
        val endDate = backStackEntry.arguments
            ?.getString(Route.Detail.Export.ARG_END_DATE)
        // TODO: Replace with actual ExportScreen composable
        // ExportScreen(
        //     initialFormat = format,
        //     initialStartDate = startDate,
        //     initialEndDate = endDate,
        //     onNavigateBack = { navController.popBackStack() },
        //     onExportComplete = { navController.popBackStack() }
        // )
        PlaceholderScreen(screenName = "Export (Format: $format)")
    }

    // Search
    composable(
        route = Route.Detail.Search.route,
        arguments = Route.Detail.Search.arguments,
        enterTransition = {
            fadeIn(tween(NavAnimationDefaults.DURATION_SHORT)) +
            scaleIn(
                initialScale = NavAnimationDefaults.INITIAL_SCALE,
                animationSpec = tween(NavAnimationDefaults.DURATION_SHORT)
            )
        },
        exitTransition = {
            fadeOut(tween(NavAnimationDefaults.DURATION_SHORT)) +
            scaleOut(
                targetScale = NavAnimationDefaults.INITIAL_SCALE,
                animationSpec = tween(NavAnimationDefaults.DURATION_SHORT)
            )
        }
    ) { backStackEntry ->
        val query = backStackEntry.arguments
            ?.getString(Route.Detail.Search.ARG_QUERY)
        // TODO: Replace with actual SearchScreen composable
        // SearchScreen(
        //     initialQuery = query,
        //     onNavigateBack = { navController.popBackStack() },
        //     onNavigateToTransaction = { txId ->
        //         navController.navigate(Route.Detail.TransactionDetail.createRoute(txId))
        //     },
        //     onNavigateToBudget = { budgetId ->
        //         navController.navigate(Route.Detail.BudgetDetail.createRoute(budgetId))
        //     }
        // )
        PlaceholderScreen(screenName = "Search (Query: ${query ?: ""})")
    }
}

/**
 * Settings detail navigation graph.
 */
private fun NavGraphBuilder.settingsDetailNavGraph(
    navController: NavHostController
) {
    // Security Settings
    composable(
        route = Route.SettingsDetail.Security.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "Security Settings")
    }

    // Appearance Settings
    composable(
        route = Route.SettingsDetail.Appearance.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "Appearance Settings")
    }

    // Notification Settings
    composable(
        route = Route.SettingsDetail.Notifications.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "Notification Settings")
    }

    // Currency Settings
    composable(
        route = Route.SettingsDetail.Currency.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "Currency Settings")
    }

    // Language Settings
    composable(
        route = Route.SettingsDetail.Language.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "Language Settings")
    }

    // Privacy Settings
    composable(
        route = Route.SettingsDetail.Privacy.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "Privacy Settings")
    }

    // Help
    composable(
        route = Route.SettingsDetail.Help.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "Help")
    }

    // About
    composable(
        route = Route.SettingsDetail.About.route,
        enterTransition = { slideInFromRight() },
        exitTransition = { slideOutToRight() }
    ) {
        PlaceholderScreen(screenName = "About")
    }
}

// ============================================
// ANIMATION HELPER FUNCTIONS
// ============================================

private fun AnimatedContentTransitionScope<NavBackStackEntry>.defaultEnterTransition(): EnterTransition {
    return slideInHorizontally(
        initialOffsetX = { fullWidth -> fullWidth },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeIn(animationSpec = tween(NavAnimationDefaults.DURATION_MEDIUM))
}

private fun AnimatedContentTransitionScope<NavBackStackEntry>.defaultExitTransition(): ExitTransition {
    return slideOutHorizontally(
        targetOffsetX = { fullWidth -> -fullWidth / 4 },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeOut(animationSpec = tween(NavAnimationDefaults.DURATION_SHORT))
}

private fun AnimatedContentTransitionScope<NavBackStackEntry>.defaultPopEnterTransition(): EnterTransition {
    return slideInHorizontally(
        initialOffsetX = { fullWidth -> -fullWidth / 4 },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeIn(animationSpec = tween(NavAnimationDefaults.DURATION_MEDIUM))
}

private fun AnimatedContentTransitionScope<NavBackStackEntry>.defaultPopExitTransition(): ExitTransition {
    return slideOutHorizontally(
        targetOffsetX = { fullWidth -> fullWidth },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeOut(animationSpec = tween(NavAnimationDefaults.DURATION_SHORT))
}

private fun slideInFromRight(): EnterTransition {
    return slideInHorizontally(
        initialOffsetX = { fullWidth -> fullWidth },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeIn(animationSpec = tween(NavAnimationDefaults.DURATION_MEDIUM))
}

private fun slideOutToRight(): ExitTransition {
    return slideOutHorizontally(
        targetOffsetX = { fullWidth -> fullWidth },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeOut(animationSpec = tween(NavAnimationDefaults.DURATION_SHORT))
}

private fun slideInFromLeft(): EnterTransition {
    return slideInHorizontally(
        initialOffsetX = { fullWidth -> -fullWidth },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeIn(animationSpec = tween(NavAnimationDefaults.DURATION_MEDIUM))
}

private fun slideOutToLeft(): ExitTransition {
    return slideOutHorizontally(
        targetOffsetX = { fullWidth -> -fullWidth },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeOut(animationSpec = tween(NavAnimationDefaults.DURATION_SHORT))
}

private fun slideInFromBottom(): EnterTransition {
    return slideInVertically(
        initialOffsetY = { fullHeight -> fullHeight },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeIn(animationSpec = tween(NavAnimationDefaults.DURATION_MEDIUM))
}

private fun slideOutToBottom(): ExitTransition {
    return slideOutVertically(
        targetOffsetY = { fullHeight -> fullHeight },
        animationSpec = tween(
            durationMillis = NavAnimationDefaults.DURATION_MEDIUM,
            easing = FastOutSlowInEasing
        )
    ) + fadeOut(animationSpec = tween(NavAnimationDefaults.DURATION_SHORT))
}

// ============================================
// PLACEHOLDER COMPOSABLE (FOR DEVELOPMENT)
// ============================================

@Composable
private fun PlaceholderScreen(screenName: String) {
    androidx.compose.foundation.layout.Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        contentAlignment = androidx.compose.ui.Alignment.Center
    ) {
        androidx.compose.material3.Text(
            text = screenName,
            style = androidx.compose.material3.MaterialTheme.typography.headlineMedium
        )
    }
}

private fun Modifier.fillMaxSize() = this.then(
    androidx.compose.foundation.layout.fillMaxSize()
)

private val Int.dp: androidx.compose.ui.unit.Dp
    get() = androidx.compose.ui.unit.dp * this
