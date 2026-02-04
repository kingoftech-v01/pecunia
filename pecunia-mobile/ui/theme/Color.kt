package com.pecunia.ui.theme

import androidx.compose.ui.graphics.Color

// Primary colors - Green theme for finance app
val Primary = Color(0xFF2E7D32)
val OnPrimary = Color(0xFFFFFFFF)
val PrimaryContainer = Color(0xFFA5D6A7)
val OnPrimaryContainer = Color(0xFF1B5E20)

// Secondary colors - Teal accent
val Secondary = Color(0xFF00897B)
val OnSecondary = Color(0xFFFFFFFF)
val SecondaryContainer = Color(0xFF80CBC4)
val OnSecondaryContainer = Color(0xFF004D40)

// Tertiary colors - Amber for highlights
val Tertiary = Color(0xFFFFA000)
val OnTertiary = Color(0xFF000000)
val TertiaryContainer = Color(0xFFFFE082)
val OnTertiaryContainer = Color(0xFFE65100)

// Error colors
val Error = Color(0xFFD32F2F)
val OnError = Color(0xFFFFFFFF)
val ErrorContainer = Color(0xFFFFCDD2)
val OnErrorContainer = Color(0xFFB71C1C)

// Background and Surface colors - Light theme
val Background = Color(0xFFF5F5F5)
val OnBackground = Color(0xFF212121)
val Surface = Color(0xFFFFFFFF)
val OnSurface = Color(0xFF212121)
val SurfaceVariant = Color(0xFFE8F5E9)
val OnSurfaceVariant = Color(0xFF424242)
val Outline = Color(0xFFBDBDBD)
val OutlineVariant = Color(0xFFE0E0E0)

// Background and Surface colors - Dark theme
val BackgroundDark = Color(0xFF121212)
val OnBackgroundDark = Color(0xFFE0E0E0)
val SurfaceDark = Color(0xFF1E1E1E)
val OnSurfaceDark = Color(0xFFE0E0E0)
val SurfaceVariantDark = Color(0xFF2C2C2C)
val OnSurfaceVariantDark = Color(0xFFBDBDBD)
val OutlineDark = Color(0xFF616161)
val OutlineVariantDark = Color(0xFF424242)

// Dark theme specific primary colors
val PrimaryDark = Color(0xFF81C784)
val OnPrimaryDark = Color(0xFF1B5E20)
val PrimaryContainerDark = Color(0xFF2E7D32)
val OnPrimaryContainerDark = Color(0xFFC8E6C9)

val SecondaryDark = Color(0xFF4DB6AC)
val OnSecondaryDark = Color(0xFF00695C)
val SecondaryContainerDark = Color(0xFF00897B)
val OnSecondaryContainerDark = Color(0xFFB2DFDB)

val TertiaryDark = Color(0xFFFFCA28)
val OnTertiaryDark = Color(0xFF5D4037)
val TertiaryContainerDark = Color(0xFFFFA000)
val OnTertiaryContainerDark = Color(0xFFFFF8E1)

val ErrorDark = Color(0xFFEF5350)
val OnErrorDark = Color(0xFF000000)
val ErrorContainerDark = Color(0xFFD32F2F)
val OnErrorContainerDark = Color(0xFFFFEBEE)

// Semantic colors for finance app
object FinanceColors {
    // Income - Green shades
    val Income = Color(0xFF4CAF50)
    val IncomeLight = Color(0xFFC8E6C9)
    val IncomeDark = Color(0xFF2E7D32)

    // Expense - Red shades
    val Expense = Color(0xFFF44336)
    val ExpenseLight = Color(0xFFFFCDD2)
    val ExpenseDark = Color(0xFFC62828)

    // Transfer - Blue shades
    val Transfer = Color(0xFF2196F3)
    val TransferLight = Color(0xFFBBDEFB)
    val TransferDark = Color(0xFF1565C0)

    // Budget status colors
    val BudgetOnTrack = Color(0xFF4CAF50)
    val BudgetWarning = Color(0xFFFFC107)
    val BudgetOverLimit = Color(0xFFF44336)

    // Chart colors
    val ChartColors = listOf(
        Color(0xFF4CAF50),
        Color(0xFF2196F3),
        Color(0xFFFFC107),
        Color(0xFFE91E63),
        Color(0xFF9C27B0),
        Color(0xFF00BCD4),
        Color(0xFFFF5722),
        Color(0xFF795548),
        Color(0xFF607D8B),
        Color(0xFF8BC34A)
    )

    // Category colors
    val CategoryFood = Color(0xFFFF9800)
    val CategoryGroceries = Color(0xFF8BC34A)
    val CategoryTransportation = Color(0xFF03A9F4)
    val CategoryUtilities = Color(0xFF9E9E9E)
    val CategoryEntertainment = Color(0xFFE91E63)
    val CategoryShopping = Color(0xFF9C27B0)
    val CategoryHealthcare = Color(0xFFF44336)
    val CategoryEducation = Color(0xFF3F51B5)
    val CategoryTravel = Color(0xFF00BCD4)
    val CategoryHousing = Color(0xFF795548)
}
