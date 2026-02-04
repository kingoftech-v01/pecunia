package com.pecunia.navigation

import androidx.navigation.NavType
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink

/**
 * Sealed class defining all navigation routes in Pecunia.
 * Provides type-safe navigation with argument support and deep links.
 */
sealed class Route(
    val route: String,
    val deepLinkUri: String? = null
) {
    // ============================================
    // AUTH ROUTES
    // ============================================
    sealed class Auth(route: String, deepLinkUri: String? = null) : Route(route, deepLinkUri) {

        data object Graph : Auth("auth_graph")

        data object Login : Auth(
            route = "login",
            deepLinkUri = "pecunia://auth/login"
        )

        data object Register : Auth(
            route = "register",
            deepLinkUri = "pecunia://auth/register"
        )

        data object ForgotPassword : Auth(
            route = "forgot_password",
            deepLinkUri = "pecunia://auth/forgot-password"
        )

        data object ResetPassword : Auth(
            route = "reset_password/{token}",
            deepLinkUri = "pecunia://auth/reset-password/{token}"
        ) {
            const val ARG_TOKEN = "token"

            fun createRoute(token: String): String = "reset_password/$token"

            val arguments = listOf(
                navArgument(ARG_TOKEN) {
                    type = NavType.StringType
                    nullable = false
                }
            )

            val deepLinks = listOf(
                navDeepLink { uriPattern = deepLinkUri }
            )
        }

        data object VerifyEmail : Auth(
            route = "verify_email/{email}",
            deepLinkUri = "pecunia://auth/verify-email/{email}"
        ) {
            const val ARG_EMAIL = "email"

            fun createRoute(email: String): String = "verify_email/$email"

            val arguments = listOf(
                navArgument(ARG_EMAIL) {
                    type = NavType.StringType
                    nullable = false
                }
            )
        }
    }

    // ============================================
    // MAIN ROUTES
    // ============================================
    sealed class Main(route: String, deepLinkUri: String? = null) : Route(route, deepLinkUri) {

        data object Graph : Main("main_graph")

        data object Dashboard : Main(
            route = "dashboard",
            deepLinkUri = "pecunia://main/dashboard"
        )

        data object Transactions : Main(
            route = "transactions",
            deepLinkUri = "pecunia://main/transactions"
        )

        data object Budgets : Main(
            route = "budgets",
            deepLinkUri = "pecunia://main/budgets"
        )

        data object Banking : Main(
            route = "banking",
            deepLinkUri = "pecunia://main/banking"
        )

        data object Settings : Main(
            route = "settings",
            deepLinkUri = "pecunia://main/settings"
        )
    }

    // ============================================
    // DETAIL ROUTES
    // ============================================
    sealed class Detail(route: String, deepLinkUri: String? = null) : Route(route, deepLinkUri) {

        data object TransactionDetail : Detail(
            route = "transaction/{transactionId}",
            deepLinkUri = "pecunia://transaction/{transactionId}"
        ) {
            const val ARG_TRANSACTION_ID = "transactionId"

            fun createRoute(transactionId: String): String = "transaction/$transactionId"

            val arguments = listOf(
                navArgument(ARG_TRANSACTION_ID) {
                    type = NavType.StringType
                    nullable = false
                }
            )

            val deepLinks = listOf(
                navDeepLink { uriPattern = deepLinkUri }
            )
        }

        data object TransactionCreate : Detail(
            route = "transaction/create?categoryId={categoryId}",
            deepLinkUri = "pecunia://transaction/create"
        ) {
            const val ARG_CATEGORY_ID = "categoryId"

            fun createRoute(categoryId: String? = null): String {
                return if (categoryId != null) {
                    "transaction/create?categoryId=$categoryId"
                } else {
                    "transaction/create"
                }
            }

            val arguments = listOf(
                navArgument(ARG_CATEGORY_ID) {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                }
            )
        }

        data object TransactionEdit : Detail(
            route = "transaction/{transactionId}/edit"
        ) {
            const val ARG_TRANSACTION_ID = "transactionId"

            fun createRoute(transactionId: String): String = "transaction/$transactionId/edit"

            val arguments = listOf(
                navArgument(ARG_TRANSACTION_ID) {
                    type = NavType.StringType
                    nullable = false
                }
            )
        }

        data object BudgetDetail : Detail(
            route = "budget/{budgetId}",
            deepLinkUri = "pecunia://budget/{budgetId}"
        ) {
            const val ARG_BUDGET_ID = "budgetId"

            fun createRoute(budgetId: String): String = "budget/$budgetId"

            val arguments = listOf(
                navArgument(ARG_BUDGET_ID) {
                    type = NavType.StringType
                    nullable = false
                }
            )

            val deepLinks = listOf(
                navDeepLink { uriPattern = deepLinkUri }
            )
        }

        data object BudgetCreate : Detail(route = "budget/create")

        data object BudgetEdit : Detail(
            route = "budget/{budgetId}/edit"
        ) {
            const val ARG_BUDGET_ID = "budgetId"

            fun createRoute(budgetId: String): String = "budget/$budgetId/edit"

            val arguments = listOf(
                navArgument(ARG_BUDGET_ID) {
                    type = NavType.StringType
                    nullable = false
                }
            )
        }

        data object AccountDetail : Detail(
            route = "account/{accountId}",
            deepLinkUri = "pecunia://account/{accountId}"
        ) {
            const val ARG_ACCOUNT_ID = "accountId"

            fun createRoute(accountId: String): String = "account/$accountId"

            val arguments = listOf(
                navArgument(ARG_ACCOUNT_ID) {
                    type = NavType.StringType
                    nullable = false
                }
            )

            val deepLinks = listOf(
                navDeepLink { uriPattern = deepLinkUri }
            )
        }

        data object AccountLink : Detail(
            route = "account/link?bankId={bankId}"
        ) {
            const val ARG_BANK_ID = "bankId"

            fun createRoute(bankId: String? = null): String {
                return if (bankId != null) {
                    "account/link?bankId=$bankId"
                } else {
                    "account/link"
                }
            }

            val arguments = listOf(
                navArgument(ARG_BANK_ID) {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                }
            )
        }

        data object CategoryDetail : Detail(
            route = "category/{categoryId}"
        ) {
            const val ARG_CATEGORY_ID = "categoryId"

            fun createRoute(categoryId: String): String = "category/$categoryId"

            val arguments = listOf(
                navArgument(ARG_CATEGORY_ID) {
                    type = NavType.StringType
                    nullable = false
                }
            )
        }

        data object Profile : Detail(
            route = "profile",
            deepLinkUri = "pecunia://profile"
        )

        data object Notifications : Detail(
            route = "notifications",
            deepLinkUri = "pecunia://notifications"
        )

        data object Export : Detail(
            route = "export?format={format}&startDate={startDate}&endDate={endDate}"
        ) {
            const val ARG_FORMAT = "format"
            const val ARG_START_DATE = "startDate"
            const val ARG_END_DATE = "endDate"

            fun createRoute(
                format: String = "pdf",
                startDate: String? = null,
                endDate: String? = null
            ): String {
                val builder = StringBuilder("export?format=$format")
                startDate?.let { builder.append("&startDate=$it") }
                endDate?.let { builder.append("&endDate=$it") }
                return builder.toString()
            }

            val arguments = listOf(
                navArgument(ARG_FORMAT) {
                    type = NavType.StringType
                    defaultValue = "pdf"
                },
                navArgument(ARG_START_DATE) {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                },
                navArgument(ARG_END_DATE) {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                }
            )
        }

        data object Search : Detail(
            route = "search?query={query}"
        ) {
            const val ARG_QUERY = "query"

            fun createRoute(query: String? = null): String {
                return if (query != null) {
                    "search?query=$query"
                } else {
                    "search"
                }
            }

            val arguments = listOf(
                navArgument(ARG_QUERY) {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                }
            )
        }
    }

    // ============================================
    // SETTINGS ROUTES
    // ============================================
    sealed class SettingsDetail(route: String) : Route(route) {

        data object Security : SettingsDetail("settings/security")

        data object Appearance : SettingsDetail("settings/appearance")

        data object Notifications : SettingsDetail("settings/notifications")

        data object Currency : SettingsDetail("settings/currency")

        data object Language : SettingsDetail("settings/language")

        data object Privacy : SettingsDetail("settings/privacy")

        data object Help : SettingsDetail("settings/help")

        data object About : SettingsDetail("settings/about")
    }
}

/**
 * Enum representing bottom navigation items for easy iteration.
 */
enum class BottomNavItem(
    val route: Route.Main,
    val titleResId: Int,
    val icon: String // Using icon name, replace with actual drawable/vector resource
) {
    DASHBOARD(Route.Main.Dashboard, 0, "dashboard"),
    TRANSACTIONS(Route.Main.Transactions, 0, "receipt_long"),
    BUDGETS(Route.Main.Budgets, 0, "savings"),
    SETTINGS(Route.Main.Settings, 0, "settings")
}

/**
 * Extension to check if a route requires authentication.
 */
fun Route.requiresAuth(): Boolean {
    return when (this) {
        is Route.Auth -> false
        else -> true
    }
}

/**
 * Extension to get the parent graph of a route.
 */
fun Route.parentGraph(): Route {
    return when (this) {
        is Route.Auth -> Route.Auth.Graph
        is Route.Main -> Route.Main.Graph
        else -> Route.Main.Graph
    }
}
