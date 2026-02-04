package com.pecunia

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.view.WindowCompat
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.pecunia.navigation.Route
import com.pecunia.ui.theme.PecuniaTheme
import com.google.accompanist.systemuicontroller.SystemUiController
import com.google.accompanist.systemuicontroller.rememberSystemUiController
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber
import javax.inject.Inject

/**
 * Main Activity for Pecunia.
 * Handles:
 * - Jetpack Compose UI setup
 * - Navigation host configuration
 * - System UI (status bar, navigation bar) customization
 * - Deep link processing
 * - Splash screen
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var appConfig: AppConfig

    private var isAppReady = false

    override fun onCreate(savedInstanceState: Bundle?) {
        // Install splash screen before super.onCreate()
        val splashScreen = installSplashScreen()

        super.onCreate(savedInstanceState)

        // Keep splash screen visible until app is ready
        splashScreen.setKeepOnScreenCondition { !isAppReady }

        // Enable edge-to-edge display
        enableEdgeToEdge()

        // Allow drawing behind system bars
        WindowCompat.setDecorFitsSystemWindows(window, false)

        // Process initial deep link
        val initialDeepLink = intent?.data?.toString()
        Timber.d("Initial deep link: $initialDeepLink")

        setContent {
            val navController = rememberNavController()
            var darkTheme by remember { mutableStateOf(false) }
            val systemInDarkTheme = isSystemInDarkTheme()

            // Determine theme based on system settings and user preference
            val useDarkTheme = if (appConfig.isFeatureEnabled(AppConfig.Feature.DARK_MODE)) {
                darkTheme || systemInDarkTheme
            } else {
                systemInDarkTheme
            }

            PecuniaTheme(darkTheme = useDarkTheme) {
                // Configure system UI
                ConfigureSystemUi(
                    systemUiController = rememberSystemUiController(),
                    useDarkIcons = !useDarkTheme
                )

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    PecuniaNavHost(
                        navController = navController,
                        startDestination = determineStartDestination(),
                        onAppReady = { isAppReady = true }
                    )
                }
            }

            // Handle deep link navigation
            HandleDeepLinks(
                navController = navController,
                initialDeepLink = initialDeepLink
            )
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // Handle deep links when app is already running
        intent.data?.let { uri ->
            Timber.d("New intent deep link: $uri")
            handleDeepLink(uri.toString())
        }
    }

    /**
     * Determine the start destination based on user authentication state.
     */
    private fun determineStartDestination(): String {
        // TODO: Check if user is authenticated
        // For now, always start at the main graph
        return Route.Main.Graph.route
    }

    /**
     * Handle deep link navigation.
     */
    private fun handleDeepLink(deepLink: String) {
        Timber.d("Handling deep link: $deepLink")
        // Deep link handling is done in the NavHost
    }
}

/**
 * Configure system UI (status bar and navigation bar) appearance.
 */
@Composable
private fun ConfigureSystemUi(
    systemUiController: SystemUiController,
    useDarkIcons: Boolean
) {
    val backgroundColor = MaterialTheme.colorScheme.background

    DisposableEffect(systemUiController, useDarkIcons, backgroundColor) {
        // Configure status bar
        systemUiController.setStatusBarColor(
            color = Color.Transparent,
            darkIcons = useDarkIcons
        )

        // Configure navigation bar
        systemUiController.setNavigationBarColor(
            color = Color.Transparent,
            darkIcons = useDarkIcons,
            navigationBarContrastEnforced = false
        )

        // Enable system bar behavior
        systemUiController.isStatusBarVisible = true
        systemUiController.isNavigationBarVisible = true

        onDispose { }
    }
}

/**
 * Main navigation host for the application.
 */
@Composable
private fun PecuniaNavHost(
    navController: NavHostController,
    startDestination: String,
    onAppReady: () -> Unit
) {
    // Signal that app is ready after first composition
    LaunchedEffect(Unit) {
        onAppReady()
    }

    NavHost(
        navController = navController,
        startDestination = startDestination,
        modifier = Modifier.fillMaxSize()
    ) {
        // Auth navigation graph
        authNavGraph(navController)

        // Main navigation graph
        mainNavGraph(navController)

        // Detail screens
        detailNavGraph(navController)

        // Settings navigation graph
        settingsNavGraph(navController)
    }
}

/**
 * Handle deep links and navigate accordingly.
 */
@Composable
private fun HandleDeepLinks(
    navController: NavHostController,
    initialDeepLink: String?
) {
    LaunchedEffect(initialDeepLink) {
        initialDeepLink?.let { deepLink ->
            Timber.d("Processing deep link: $deepLink")

            // Parse deep link and navigate
            when {
                deepLink.contains("transaction/") -> {
                    val transactionId = extractIdFromDeepLink(deepLink, "transaction")
                    transactionId?.let {
                        navController.navigate(Route.Detail.TransactionDetail.createRoute(it))
                    }
                }
                deepLink.contains("budget/") -> {
                    val budgetId = extractIdFromDeepLink(deepLink, "budget")
                    budgetId?.let {
                        navController.navigate(Route.Detail.BudgetDetail.createRoute(it))
                    }
                }
                deepLink.contains("account/") -> {
                    val accountId = extractIdFromDeepLink(deepLink, "account")
                    accountId?.let {
                        navController.navigate(Route.Detail.AccountDetail.createRoute(it))
                    }
                }
                deepLink.contains("auth/login") -> {
                    navController.navigate(Route.Auth.Login.route)
                }
                deepLink.contains("auth/register") -> {
                    navController.navigate(Route.Auth.Register.route)
                }
                deepLink.contains("dashboard") -> {
                    navController.navigate(Route.Main.Dashboard.route)
                }
                deepLink.contains("transactions") -> {
                    navController.navigate(Route.Main.Transactions.route)
                }
                deepLink.contains("budgets") -> {
                    navController.navigate(Route.Main.Budgets.route)
                }
                deepLink.contains("settings") -> {
                    navController.navigate(Route.Main.Settings.route)
                }
            }
        }
    }
}

/**
 * Extract ID from deep link URL.
 */
private fun extractIdFromDeepLink(deepLink: String, prefix: String): String? {
    val regex = Regex("$prefix/([^/]+)")
    return regex.find(deepLink)?.groupValues?.getOrNull(1)
}

// ============================================
// NAVIGATION GRAPH BUILDERS
// ============================================

/**
 * Auth navigation graph.
 */
private fun androidx.navigation.NavGraphBuilder.authNavGraph(
    navController: NavHostController
) {
    composable(route = Route.Auth.Login.route) {
        // TODO: LoginScreen(navController = navController)
        PlaceholderScreen("Login Screen")
    }

    composable(route = Route.Auth.Register.route) {
        // TODO: RegisterScreen(navController = navController)
        PlaceholderScreen("Register Screen")
    }

    composable(route = Route.Auth.ForgotPassword.route) {
        // TODO: ForgotPasswordScreen(navController = navController)
        PlaceholderScreen("Forgot Password Screen")
    }

    composable(
        route = Route.Auth.ResetPassword.route,
        arguments = Route.Auth.ResetPassword.arguments,
        deepLinks = Route.Auth.ResetPassword.deepLinks
    ) { backStackEntry ->
        val token = backStackEntry.arguments?.getString(Route.Auth.ResetPassword.ARG_TOKEN)
        // TODO: ResetPasswordScreen(token = token, navController = navController)
        PlaceholderScreen("Reset Password Screen - Token: $token")
    }

    composable(
        route = Route.Auth.VerifyEmail.route,
        arguments = Route.Auth.VerifyEmail.arguments
    ) { backStackEntry ->
        val email = backStackEntry.arguments?.getString(Route.Auth.VerifyEmail.ARG_EMAIL)
        // TODO: VerifyEmailScreen(email = email, navController = navController)
        PlaceholderScreen("Verify Email Screen - Email: $email")
    }
}

/**
 * Main navigation graph (bottom navigation destinations).
 */
private fun androidx.navigation.NavGraphBuilder.mainNavGraph(
    navController: NavHostController
) {
    composable(route = Route.Main.Dashboard.route) {
        // TODO: DashboardScreen(navController = navController)
        PlaceholderScreen("Dashboard Screen")
    }

    composable(route = Route.Main.Transactions.route) {
        // TODO: TransactionsScreen(navController = navController)
        PlaceholderScreen("Transactions Screen")
    }

    composable(route = Route.Main.Budgets.route) {
        // TODO: BudgetsScreen(navController = navController)
        PlaceholderScreen("Budgets Screen")
    }

    composable(route = Route.Main.Banking.route) {
        // TODO: BankingScreen(navController = navController)
        PlaceholderScreen("Banking Screen")
    }

    composable(route = Route.Main.Settings.route) {
        // TODO: SettingsScreen(navController = navController)
        PlaceholderScreen("Settings Screen")
    }
}

/**
 * Detail screens navigation graph.
 */
private fun androidx.navigation.NavGraphBuilder.detailNavGraph(
    navController: NavHostController
) {
    // Transaction screens
    composable(
        route = Route.Detail.TransactionDetail.route,
        arguments = Route.Detail.TransactionDetail.arguments,
        deepLinks = Route.Detail.TransactionDetail.deepLinks
    ) { backStackEntry ->
        val transactionId = backStackEntry.arguments?.getString(Route.Detail.TransactionDetail.ARG_TRANSACTION_ID)
        // TODO: TransactionDetailScreen(transactionId = transactionId, navController = navController)
        PlaceholderScreen("Transaction Detail - ID: $transactionId")
    }

    composable(
        route = Route.Detail.TransactionCreate.route,
        arguments = Route.Detail.TransactionCreate.arguments
    ) { backStackEntry ->
        val categoryId = backStackEntry.arguments?.getString(Route.Detail.TransactionCreate.ARG_CATEGORY_ID)
        // TODO: TransactionCreateScreen(categoryId = categoryId, navController = navController)
        PlaceholderScreen("Create Transaction - Category: $categoryId")
    }

    composable(
        route = Route.Detail.TransactionEdit.route,
        arguments = Route.Detail.TransactionEdit.arguments
    ) { backStackEntry ->
        val transactionId = backStackEntry.arguments?.getString(Route.Detail.TransactionEdit.ARG_TRANSACTION_ID)
        // TODO: TransactionEditScreen(transactionId = transactionId, navController = navController)
        PlaceholderScreen("Edit Transaction - ID: $transactionId")
    }

    // Budget screens
    composable(
        route = Route.Detail.BudgetDetail.route,
        arguments = Route.Detail.BudgetDetail.arguments,
        deepLinks = Route.Detail.BudgetDetail.deepLinks
    ) { backStackEntry ->
        val budgetId = backStackEntry.arguments?.getString(Route.Detail.BudgetDetail.ARG_BUDGET_ID)
        // TODO: BudgetDetailScreen(budgetId = budgetId, navController = navController)
        PlaceholderScreen("Budget Detail - ID: $budgetId")
    }

    composable(route = Route.Detail.BudgetCreate.route) {
        // TODO: BudgetCreateScreen(navController = navController)
        PlaceholderScreen("Create Budget Screen")
    }

    composable(
        route = Route.Detail.BudgetEdit.route,
        arguments = Route.Detail.BudgetEdit.arguments
    ) { backStackEntry ->
        val budgetId = backStackEntry.arguments?.getString(Route.Detail.BudgetEdit.ARG_BUDGET_ID)
        // TODO: BudgetEditScreen(budgetId = budgetId, navController = navController)
        PlaceholderScreen("Edit Budget - ID: $budgetId")
    }

    // Account screens
    composable(
        route = Route.Detail.AccountDetail.route,
        arguments = Route.Detail.AccountDetail.arguments,
        deepLinks = Route.Detail.AccountDetail.deepLinks
    ) { backStackEntry ->
        val accountId = backStackEntry.arguments?.getString(Route.Detail.AccountDetail.ARG_ACCOUNT_ID)
        // TODO: AccountDetailScreen(accountId = accountId, navController = navController)
        PlaceholderScreen("Account Detail - ID: $accountId")
    }

    composable(
        route = Route.Detail.AccountLink.route,
        arguments = Route.Detail.AccountLink.arguments
    ) { backStackEntry ->
        val bankId = backStackEntry.arguments?.getString(Route.Detail.AccountLink.ARG_BANK_ID)
        // TODO: AccountLinkScreen(bankId = bankId, navController = navController)
        PlaceholderScreen("Link Account - Bank: $bankId")
    }

    // Other detail screens
    composable(route = Route.Detail.Profile.route) {
        // TODO: ProfileScreen(navController = navController)
        PlaceholderScreen("Profile Screen")
    }

    composable(route = Route.Detail.Notifications.route) {
        // TODO: NotificationsScreen(navController = navController)
        PlaceholderScreen("Notifications Screen")
    }

    composable(
        route = Route.Detail.Export.route,
        arguments = Route.Detail.Export.arguments
    ) { backStackEntry ->
        val format = backStackEntry.arguments?.getString(Route.Detail.Export.ARG_FORMAT)
        val startDate = backStackEntry.arguments?.getString(Route.Detail.Export.ARG_START_DATE)
        val endDate = backStackEntry.arguments?.getString(Route.Detail.Export.ARG_END_DATE)
        // TODO: ExportScreen(format = format, startDate = startDate, endDate = endDate, navController = navController)
        PlaceholderScreen("Export Screen - Format: $format")
    }

    composable(
        route = Route.Detail.Search.route,
        arguments = Route.Detail.Search.arguments
    ) { backStackEntry ->
        val query = backStackEntry.arguments?.getString(Route.Detail.Search.ARG_QUERY)
        // TODO: SearchScreen(query = query, navController = navController)
        PlaceholderScreen("Search Screen - Query: $query")
    }

    composable(
        route = Route.Detail.CategoryDetail.route,
        arguments = Route.Detail.CategoryDetail.arguments
    ) { backStackEntry ->
        val categoryId = backStackEntry.arguments?.getString(Route.Detail.CategoryDetail.ARG_CATEGORY_ID)
        // TODO: CategoryDetailScreen(categoryId = categoryId, navController = navController)
        PlaceholderScreen("Category Detail - ID: $categoryId")
    }
}

/**
 * Settings navigation graph.
 */
private fun androidx.navigation.NavGraphBuilder.settingsNavGraph(
    navController: NavHostController
) {
    composable(route = Route.SettingsDetail.Security.route) {
        // TODO: SecuritySettingsScreen(navController = navController)
        PlaceholderScreen("Security Settings")
    }

    composable(route = Route.SettingsDetail.Appearance.route) {
        // TODO: AppearanceSettingsScreen(navController = navController)
        PlaceholderScreen("Appearance Settings")
    }

    composable(route = Route.SettingsDetail.Notifications.route) {
        // TODO: NotificationSettingsScreen(navController = navController)
        PlaceholderScreen("Notification Settings")
    }

    composable(route = Route.SettingsDetail.Currency.route) {
        // TODO: CurrencySettingsScreen(navController = navController)
        PlaceholderScreen("Currency Settings")
    }

    composable(route = Route.SettingsDetail.Language.route) {
        // TODO: LanguageSettingsScreen(navController = navController)
        PlaceholderScreen("Language Settings")
    }

    composable(route = Route.SettingsDetail.Privacy.route) {
        // TODO: PrivacySettingsScreen(navController = navController)
        PlaceholderScreen("Privacy Settings")
    }

    composable(route = Route.SettingsDetail.Help.route) {
        // TODO: HelpScreen(navController = navController)
        PlaceholderScreen("Help Screen")
    }

    composable(route = Route.SettingsDetail.About.route) {
        // TODO: AboutScreen(navController = navController)
        PlaceholderScreen("About Screen")
    }
}

/**
 * Placeholder screen for development.
 */
@Composable
private fun PlaceholderScreen(name: String) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        androidx.compose.foundation.layout.Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = androidx.compose.ui.Alignment.Center
        ) {
            androidx.compose.material3.Text(
                text = name,
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onBackground
            )
        }
    }
}
