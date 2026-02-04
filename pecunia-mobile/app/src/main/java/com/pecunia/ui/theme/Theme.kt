package com.pecunia.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// ============================================
// Light Color Scheme
// ============================================
private val LightColorScheme = lightColorScheme(
    primary = PrimaryLight,
    onPrimary = OnPrimaryLight,
    primaryContainer = PrimaryContainerLight,
    onPrimaryContainer = OnPrimaryContainerLight,
    secondary = SecondaryLight,
    onSecondary = OnSecondaryLight,
    secondaryContainer = SecondaryContainerLight,
    onSecondaryContainer = OnSecondaryContainerLight,
    tertiary = TertiaryLight,
    onTertiary = OnTertiaryLight,
    tertiaryContainer = TertiaryContainerLight,
    onTertiaryContainer = OnTertiaryContainerLight,
    error = ErrorLight,
    onError = OnErrorLight,
    errorContainer = ErrorContainerLight,
    onErrorContainer = OnErrorContainerLight,
    background = BackgroundLight,
    onBackground = OnBackgroundLight,
    surface = SurfaceLight,
    onSurface = OnSurfaceLight,
    surfaceVariant = SurfaceVariantLight,
    onSurfaceVariant = OnSurfaceVariantLight,
    outline = OutlineLight,
    outlineVariant = OutlineVariantLight,
    inverseSurface = InverseSurfaceLight,
    inverseOnSurface = InverseOnSurfaceLight,
    inversePrimary = InversePrimaryLight,
    scrim = ScrimLight,
    surfaceTint = SurfaceTintLight,
    surfaceBright = SurfaceBrightLight,
    surfaceDim = SurfaceDimLight,
    surfaceContainer = SurfaceContainerLight,
    surfaceContainerHigh = SurfaceContainerHighLight,
    surfaceContainerHighest = SurfaceContainerHighestLight,
    surfaceContainerLow = SurfaceContainerLowLight,
    surfaceContainerLowest = SurfaceContainerLowestLight
)

// ============================================
// Dark Color Scheme
// ============================================
private val DarkColorScheme = darkColorScheme(
    primary = PrimaryDark,
    onPrimary = OnPrimaryDark,
    primaryContainer = PrimaryContainerDark,
    onPrimaryContainer = OnPrimaryContainerDark,
    secondary = SecondaryDark,
    onSecondary = OnSecondaryDark,
    secondaryContainer = SecondaryContainerDark,
    onSecondaryContainer = OnSecondaryContainerDark,
    tertiary = TertiaryDark,
    onTertiary = OnTertiaryDark,
    tertiaryContainer = TertiaryContainerDark,
    onTertiaryContainer = OnTertiaryContainerDark,
    error = ErrorDark,
    onError = OnErrorDark,
    errorContainer = ErrorContainerDark,
    onErrorContainer = OnErrorContainerDark,
    background = BackgroundDark,
    onBackground = OnBackgroundDark,
    surface = SurfaceDark,
    onSurface = OnSurfaceDark,
    surfaceVariant = SurfaceVariantDark,
    onSurfaceVariant = OnSurfaceVariantDark,
    outline = OutlineDark,
    outlineVariant = OutlineVariantDark,
    inverseSurface = InverseSurfaceDark,
    inverseOnSurface = InverseOnSurfaceDark,
    inversePrimary = InversePrimaryDark,
    scrim = ScrimDark,
    surfaceTint = SurfaceTintDark,
    surfaceBright = SurfaceBrightDark,
    surfaceDim = SurfaceDimDark,
    surfaceContainer = SurfaceContainerDark,
    surfaceContainerHigh = SurfaceContainerHighDark,
    surfaceContainerHighest = SurfaceContainerHighestDark,
    surfaceContainerLow = SurfaceContainerLowDark,
    surfaceContainerLowest = SurfaceContainerLowestDark
)

// ============================================
// Extended Colors for Pecunia
// ============================================
@Immutable
data class PecuniaColors(
    // Transaction colors
    val income: Color,
    val onIncome: Color,
    val incomeContainer: Color,
    val onIncomeContainer: Color,
    val expense: Color,
    val onExpense: Color,
    val expenseContainer: Color,
    val onExpenseContainer: Color,
    val transfer: Color,
    val onTransfer: Color,
    val transferContainer: Color,
    val onTransferContainer: Color,

    // Status colors
    val success: Color,
    val onSuccess: Color,
    val successContainer: Color,
    val onSuccessContainer: Color,
    val warning: Color,
    val onWarning: Color,
    val warningContainer: Color,
    val onWarningContainer: Color,
    val info: Color,
    val onInfo: Color,
    val infoContainer: Color,
    val onInfoContainer: Color,

    // Budget status
    val budgetSafe: Color,
    val budgetWarning: Color,
    val budgetDanger: Color,
    val budgetExceeded: Color,

    // Trend indicators
    val trendUp: Color,
    val trendDown: Color,
    val trendNeutral: Color,

    // Chart colors
    val chartPrimary: Color,
    val chartSecondary: Color,
    val chartTertiary: Color
)

// ============================================
// Light Pecunia Colors
// ============================================
val LightPecuniaColors = PecuniaColors(
    // Income
    income = IncomeGreen,
    onIncome = Color.White,
    incomeContainer = IncomeGreenLight,
    onIncomeContainer = IncomeGreen,

    // Expense
    expense = ExpenseRed,
    onExpense = Color.White,
    expenseContainer = ExpenseRedLight,
    onExpenseContainer = ExpenseRed,

    // Transfer
    transfer = Color(0xFF29B6F6),
    onTransfer = Color.White,
    transferContainer = Color(0xFFE1F5FE),
    onTransferContainer = Color(0xFF0277BD),

    // Success
    success = SuccessLight,
    onSuccess = OnSuccessLight,
    successContainer = SuccessContainerLight,
    onSuccessContainer = OnSuccessContainerLight,

    // Warning
    warning = WarningOrange,
    onWarning = Color.White,
    warningContainer = WarningOrangeLight,
    onWarningContainer = WarningOrange,

    // Info
    info = InfoBlue,
    onInfo = Color.White,
    infoContainer = InfoBlueLight,
    onInfoContainer = InfoBlue,

    // Budget status
    budgetSafe = BudgetSafe,
    budgetWarning = BudgetWarning,
    budgetDanger = BudgetDanger,
    budgetExceeded = BudgetExceeded,

    // Trend
    trendUp = TrendColors.up,
    trendDown = TrendColors.down,
    trendNeutral = TrendColors.neutral,

    // Chart
    chartPrimary = ChartColors.income,
    chartSecondary = ChartColors.expense,
    chartTertiary = ChartColors.balance
)

// ============================================
// Dark Pecunia Colors
// ============================================
val DarkPecuniaColors = PecuniaColors(
    // Income
    income = IncomeGreenDark,
    onIncome = Color(0xFF1B5E20),
    incomeContainer = IncomeGreen.copy(alpha = 0.2f),
    onIncomeContainer = IncomeGreenDark,

    // Expense
    expense = ExpenseRedDark,
    onExpense = Color(0xFF7F0000),
    expenseContainer = ExpenseRed.copy(alpha = 0.2f),
    onExpenseContainer = ExpenseRedDark,

    // Transfer
    transfer = Color(0xFF81D4FA),
    onTransfer = Color(0xFF01579B),
    transferContainer = Color(0xFF29B6F6).copy(alpha = 0.2f),
    onTransferContainer = Color(0xFF81D4FA),

    // Success
    success = SuccessDark,
    onSuccess = OnSuccessDark,
    successContainer = SuccessContainerDark,
    onSuccessContainer = OnSuccessContainerDark,

    // Warning
    warning = WarningOrangeDark,
    onWarning = Color(0xFF4E2600),
    warningContainer = WarningOrange.copy(alpha = 0.2f),
    onWarningContainer = WarningOrangeDark,

    // Info
    info = InfoBlueDark,
    onInfo = Color(0xFF01579B),
    infoContainer = InfoBlue.copy(alpha = 0.2f),
    onInfoContainer = InfoBlueDark,

    // Budget status
    budgetSafe = BudgetSafe,
    budgetWarning = BudgetWarning,
    budgetDanger = BudgetDanger,
    budgetExceeded = BudgetExceeded,

    // Trend
    trendUp = Color(0xFF81C784),
    trendDown = Color(0xFFEF9A9A),
    trendNeutral = Color(0xFFBDBDBD),

    // Chart
    chartPrimary = Color(0xFF81C784),
    chartSecondary = Color(0xFFEF9A9A),
    chartTertiary = Color(0xFF90CAF9)
)

// ============================================
// Composition Locals
// ============================================
val LocalPecuniaColors = staticCompositionLocalOf { LightPecuniaColors }
val LocalSpacing = staticCompositionLocalOf { Spacing() }

// ============================================
// Main Theme Composable
// ============================================

/**
 * Main theme composable for the Pecunia
 *
 * @param darkTheme Whether to use dark theme (follows system by default)
 * @param dynamicColor Whether to use dynamic color (Android 12+ only)
 * @param content The content to be themed
 */
@Composable
fun PecuniaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val pecuniaColors = if (darkTheme) DarkPecuniaColors else LightPecuniaColors

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.surface.toArgb()
            window.navigationBarColor = colorScheme.surface.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !darkTheme
                isAppearanceLightNavigationBars = !darkTheme
            }
        }
    }

    CompositionLocalProvider(
        LocalPecuniaColors provides pecuniaColors,
        LocalSpacing provides Spacing()
    ) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = PecuniaTypography,
            shapes = PecuniaShapes,
            content = content
        )
    }
}

// ============================================
// Theme Extensions
// ============================================

/**
 * Extension property to access pecunia-specific colors from MaterialTheme
 */
object PecuniaTheme {
    val pecuniaColors: PecuniaColors
        @Composable
        @ReadOnlyComposable
        get() = LocalPecuniaColors.current

    val spacing: Spacing
        @Composable
        @ReadOnlyComposable
        get() = LocalSpacing.current
}

/**
 * Access pecunia colors from anywhere in the composable tree
 */
val MaterialTheme.pecuniaColors: PecuniaColors
    @Composable
    @ReadOnlyComposable
    get() = LocalPecuniaColors.current

/**
 * Access spacing from anywhere in the composable tree
 */
val MaterialTheme.spacing: Spacing
    @Composable
    @ReadOnlyComposable
    get() = LocalSpacing.current

// ============================================
// Helper Functions
// ============================================

/**
 * Helper function to get category color by category name
 */
fun getCategoryColor(category: String): Color {
    return when (category.lowercase()) {
        // Food & Dining
        "food", "dining", "restaurants", "cafe" -> CategoryColors.Food
        "groceries", "supermarket", "market" -> CategoryColors.Groceries

        // Transportation
        "transport", "transportation" -> CategoryColors.Transport
        "gas", "fuel", "petrol" -> CategoryColors.Fuel
        "public transport", "bus", "metro", "train" -> CategoryColors.PublicTransport

        // Shopping
        "shopping", "retail" -> CategoryColors.Shopping
        "clothing", "clothes", "fashion" -> CategoryColors.Clothing
        "electronics", "tech", "gadgets" -> CategoryColors.Electronics

        // Entertainment
        "entertainment" -> CategoryColors.Entertainment
        "movies", "cinema", "theater" -> CategoryColors.Movies
        "games", "gaming" -> CategoryColors.Games
        "music", "concerts", "streaming" -> CategoryColors.Music

        // Bills & Utilities
        "bills", "utilities" -> CategoryColors.Bills
        "electricity", "electric", "power" -> CategoryColors.Electricity
        "water" -> CategoryColors.Water
        "internet", "wifi" -> CategoryColors.Internet
        "phone", "mobile" -> CategoryColors.Phone

        // Health & Wellness
        "health", "healthcare" -> CategoryColors.Health
        "medical", "doctor", "hospital" -> CategoryColors.Medical
        "pharmacy", "medicine", "drugs" -> CategoryColors.Pharmacy
        "fitness", "gym", "sports" -> CategoryColors.Fitness

        // Education
        "education", "school", "university" -> CategoryColors.Education
        "books", "reading" -> CategoryColors.Books
        "courses", "training", "learning" -> CategoryColors.Courses

        // Travel
        "travel", "vacation", "holidays" -> CategoryColors.Travel
        "hotel", "accommodation", "lodging" -> CategoryColors.Hotel
        "flight", "airline", "airport" -> CategoryColors.Flight

        // Housing
        "housing", "home" -> CategoryColors.Housing
        "rent" -> CategoryColors.Rent
        "mortgage" -> CategoryColors.Mortgage
        "maintenance", "repairs" -> CategoryColors.Maintenance

        // Financial
        "insurance" -> CategoryColors.Insurance
        "subscription", "subscriptions" -> CategoryColors.Subscription
        "taxes", "tax" -> CategoryColors.Taxes
        "fees", "bank fees", "charges" -> CategoryColors.Fees

        // Personal
        "personal", "self-care" -> CategoryColors.Personal
        "beauty", "cosmetics", "salon" -> CategoryColors.Beauty

        // Family
        "family" -> CategoryColors.Family
        "kids", "children", "baby" -> CategoryColors.Kids
        "pets", "pet", "veterinary" -> CategoryColors.Pets

        // Charity
        "charity", "charitable" -> CategoryColors.Charity
        "donation", "donations" -> CategoryColors.Donation

        // Income categories
        "salary", "wages", "paycheck" -> CategoryColors.Salary
        "investment", "investments", "stocks", "crypto" -> CategoryColors.Investment
        "freelance", "freelancing", "contractor" -> CategoryColors.Freelance
        "gift", "gifts" -> CategoryColors.Gift
        "refund", "refunds", "return" -> CategoryColors.Refund
        "bonus", "bonuses" -> CategoryColors.Bonus
        "interest" -> CategoryColors.Interest
        "dividend", "dividends" -> CategoryColors.Dividend
        "rental", "rental income" -> CategoryColors.Rental

        // Transfer
        "transfer", "internal" -> CategoryColors.Transfer
        "savings" -> CategoryColors.Savings

        // Default
        else -> CategoryColors.OtherExpense
    }
}

/**
 * Get color for transaction type
 */
fun getTransactionTypeColor(type: String): Color {
    return when (type.lowercase()) {
        "income" -> TransactionColors.income
        "expense" -> TransactionColors.expense
        "transfer" -> TransactionColors.transfer
        "pending" -> TransactionColors.pending
        "cancelled" -> TransactionColors.cancelled
        "recurring" -> TransactionColors.recurring
        "scheduled" -> TransactionColors.scheduled
        "failed" -> TransactionColors.failed
        else -> TransactionColors.expense
    }
}

/**
 * Get color for account type
 */
fun getAccountTypeColor(type: String): Color {
    return when (type.lowercase()) {
        "checking", "current" -> AccountColors.checking
        "savings" -> AccountColors.savings
        "credit", "credit card" -> AccountColors.creditCard
        "investment", "brokerage" -> AccountColors.investment
        "cash" -> AccountColors.cash
        "loan" -> AccountColors.loan
        "crypto", "cryptocurrency" -> AccountColors.crypto
        "retirement", "401k", "ira" -> AccountColors.retirement
        "business" -> AccountColors.business
        else -> AccountColors.other
    }
}

/**
 * Get budget status color based on percentage spent
 */
fun getBudgetStatusColor(spent: Double, budget: Double): Color {
    return BudgetColors.getProgressColor(spent, budget)
}

/**
 * Get goal progress color
 */
fun getGoalProgressColor(current: Double, target: Double, isOverdue: Boolean = false): Color {
    return GoalColors.getStatusColor(current, target, isOverdue)
}

/**
 * Get trend color based on change direction
 */
fun getTrendColor(change: Double): Color {
    return when {
        change > 0 -> TrendColors.up
        change < 0 -> TrendColors.down
        else -> TrendColors.neutral
    }
}
