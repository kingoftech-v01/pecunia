package com.pecunia.ui.theme

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.Spacer
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

// ============================================
// Spacing Values Class
// ============================================

/**
 * Spacing values following Material 3 design guidelines
 * Base unit is 4dp for consistency
 */
@Immutable
data class Spacing(
    // ==========================================
    // Base Spacing Values (4dp increments)
    // ==========================================
    val none: Dp = 0.dp,
    val extraSmall: Dp = 4.dp,      // 1 unit
    val small: Dp = 8.dp,           // 2 units
    val medium: Dp = 16.dp,         // 4 units
    val large: Dp = 24.dp,          // 6 units
    val extraLarge: Dp = 32.dp,     // 8 units
    val huge: Dp = 48.dp,           // 12 units
    val massive: Dp = 64.dp,        // 16 units

    // ==========================================
    // Specific Named Spacing Values
    // ==========================================

    // Padding values
    val contentPadding: Dp = 16.dp,
    val screenPadding: Dp = 16.dp,
    val cardPadding: Dp = 16.dp,
    val listItemPadding: Dp = 16.dp,
    val dialogPadding: Dp = 24.dp,
    val bottomSheetPadding: Dp = 16.dp,

    // Horizontal padding
    val horizontalSmall: Dp = 8.dp,
    val horizontalMedium: Dp = 16.dp,
    val horizontalLarge: Dp = 24.dp,

    // Vertical padding
    val verticalSmall: Dp = 8.dp,
    val verticalMedium: Dp = 16.dp,
    val verticalLarge: Dp = 24.dp,

    // Gap values (space between items)
    val gapTiny: Dp = 2.dp,
    val gapSmall: Dp = 4.dp,
    val gapMedium: Dp = 8.dp,
    val gapLarge: Dp = 12.dp,
    val gapExtraLarge: Dp = 16.dp,

    // Section spacing
    val sectionSpacing: Dp = 24.dp,
    val sectionTitleSpacing: Dp = 16.dp,

    // List spacing
    val listItemVerticalPadding: Dp = 12.dp,
    val listItemHorizontalPadding: Dp = 16.dp,
    val listItemSpacing: Dp = 8.dp,
    val listSectionSpacing: Dp = 16.dp,

    // Card spacing
    val cardContentPadding: Dp = 16.dp,
    val cardSpacing: Dp = 12.dp,

    // Button spacing
    val buttonPadding: Dp = 16.dp,
    val buttonSpacing: Dp = 8.dp,

    // Icon spacing
    val iconPadding: Dp = 8.dp,
    val iconTextSpacing: Dp = 8.dp,

    // FAB margins
    val fabMargin: Dp = 16.dp,
    val fabExtendedPadding: Dp = 16.dp,

    // Bottom navigation
    val bottomNavHeight: Dp = 80.dp,
    val bottomNavIconSize: Dp = 24.dp,

    // App bar
    val appBarHeight: Dp = 64.dp,
    val appBarIconSize: Dp = 24.dp,
    val appBarTitleSpacing: Dp = 16.dp,

    // Divider
    val dividerVerticalPadding: Dp = 8.dp,

    // Chip spacing
    val chipSpacing: Dp = 8.dp,
    val chipPadding: Dp = 12.dp,

    // Avatar/Icon sizes
    val avatarSmall: Dp = 32.dp,
    val avatarMedium: Dp = 40.dp,
    val avatarLarge: Dp = 56.dp,

    // Category icon sizes
    val categoryIconSmall: Dp = 24.dp,
    val categoryIconMedium: Dp = 32.dp,
    val categoryIconLarge: Dp = 40.dp,

    // Transaction row
    val transactionRowHeight: Dp = 72.dp,
    val transactionIconSize: Dp = 40.dp,

    // Account card
    val accountCardHeight: Dp = 120.dp,

    // Budget progress
    val budgetProgressHeight: Dp = 8.dp,

    // Chart dimensions
    val chartHeight: Dp = 200.dp,
    val pieChartSize: Dp = 240.dp,
    val barChartBarWidth: Dp = 24.dp,

    // Input fields
    val inputFieldHeight: Dp = 56.dp,
    val inputFieldMinHeight: Dp = 48.dp,

    // Touch targets (minimum 48dp for accessibility)
    val minTouchTarget: Dp = 48.dp,

    // Border widths
    val borderThin: Dp = 1.dp,
    val borderMedium: Dp = 2.dp,
    val borderThick: Dp = 4.dp,

    // Elevation (for reference, use material elevation in Compose)
    val elevationNone: Dp = 0.dp,
    val elevationSmall: Dp = 1.dp,
    val elevationMedium: Dp = 4.dp,
    val elevationLarge: Dp = 8.dp
)

// ============================================
// Singleton Instance
// ============================================

/**
 * Default spacing instance
 */
val DefaultSpacing = Spacing()

// ============================================
// Dimension Constants
// ============================================

/**
 * Common dimension constants that can be used outside of Compose
 */
object Dimensions {
    // Base units
    val unit = 4.dp
    val unit2 = 8.dp
    val unit3 = 12.dp
    val unit4 = 16.dp
    val unit5 = 20.dp
    val unit6 = 24.dp
    val unit8 = 32.dp
    val unit10 = 40.dp
    val unit12 = 48.dp
    val unit16 = 64.dp

    // Screen padding
    val screenPaddingSmall = 8.dp
    val screenPaddingMedium = 16.dp
    val screenPaddingLarge = 24.dp

    // Card dimensions
    val cardCornerRadius = 12.dp
    val cardElevation = 2.dp
    val cardMinHeight = 80.dp

    // Button dimensions
    val buttonHeight = 48.dp
    val buttonHeightSmall = 36.dp
    val buttonHeightLarge = 56.dp
    val buttonCornerRadius = 24.dp
    val buttonMinWidth = 64.dp

    // Icon dimensions
    val iconSizeSmall = 16.dp
    val iconSizeMedium = 24.dp
    val iconSizeLarge = 32.dp
    val iconSizeExtraLarge = 48.dp

    // Avatar dimensions
    val avatarSizeSmall = 32.dp
    val avatarSizeMedium = 40.dp
    val avatarSizeLarge = 56.dp
    val avatarSizeExtraLarge = 72.dp

    // Progress indicators
    val progressIndicatorSize = 48.dp
    val progressIndicatorStroke = 4.dp
    val linearProgressHeight = 4.dp
    val linearProgressHeightLarge = 8.dp

    // Divider
    val dividerHeight = 1.dp

    // Badge
    val badgeSize = 8.dp
    val badgeSizeLarge = 16.dp

    // Bottom sheet
    val bottomSheetPeekHeight = 56.dp
    val bottomSheetHandleWidth = 32.dp
    val bottomSheetHandleHeight = 4.dp

    // Dialog
    val dialogMinWidth = 280.dp
    val dialogMaxWidth = 560.dp
    val dialogCornerRadius = 28.dp

    // Snackbar
    val snackbarMaxWidth = 600.dp

    // Image dimensions
    val imageSmall = 48.dp
    val imageMedium = 80.dp
    val imageLarge = 120.dp
    val imageThumbnail = 56.dp

    // Empty state
    val emptyStateIconSize = 96.dp
    val emptyStateMaxWidth = 280.dp

    // Touch targets
    val minTouchTarget = 48.dp
    val touchTargetSmall = 40.dp
}

// ============================================
// Padding Values Factory
// ============================================

/**
 * Factory for creating common PaddingValues
 */
object PaddingValuesFactory {
    val none = PaddingValues(0.dp)
    val extraSmall = PaddingValues(4.dp)
    val small = PaddingValues(8.dp)
    val medium = PaddingValues(16.dp)
    val large = PaddingValues(24.dp)
    val extraLarge = PaddingValues(32.dp)

    // Screen padding (horizontal only)
    val screenHorizontal = PaddingValues(horizontal = 16.dp)

    // Screen padding (all sides)
    val screen = PaddingValues(16.dp)

    // Card padding
    val card = PaddingValues(16.dp)

    // List item padding
    val listItem = PaddingValues(horizontal = 16.dp, vertical = 12.dp)

    // Button padding
    val buttonSmall = PaddingValues(horizontal = 12.dp, vertical = 8.dp)
    val buttonMedium = PaddingValues(horizontal = 16.dp, vertical = 12.dp)
    val buttonLarge = PaddingValues(horizontal = 24.dp, vertical = 16.dp)

    // Dialog padding
    val dialog = PaddingValues(24.dp)

    // Bottom bar padding (with safe area consideration)
    fun withBottomNav(bottomNavHeight: Dp = 80.dp) = PaddingValues(bottom = bottomNavHeight)

    // Custom padding
    fun horizontal(value: Dp) = PaddingValues(horizontal = value)
    fun vertical(value: Dp) = PaddingValues(vertical = value)
    fun all(value: Dp) = PaddingValues(value)
    fun custom(
        start: Dp = 0.dp,
        top: Dp = 0.dp,
        end: Dp = 0.dp,
        bottom: Dp = 0.dp
    ) = PaddingValues(start = start, top = top, end = end, bottom = bottom)
}

// ============================================
// Modifier Extensions
// ============================================

/**
 * Apply small padding on all sides
 */
fun Modifier.paddingSmall(): Modifier = this.padding(8.dp)

/**
 * Apply medium padding on all sides
 */
fun Modifier.paddingMedium(): Modifier = this.padding(16.dp)

/**
 * Apply large padding on all sides
 */
fun Modifier.paddingLarge(): Modifier = this.padding(24.dp)

/**
 * Apply screen-standard horizontal padding
 */
fun Modifier.screenPadding(): Modifier = this.padding(horizontal = 16.dp)

/**
 * Apply card content padding
 */
fun Modifier.cardPadding(): Modifier = this.padding(16.dp)

/**
 * Apply list item padding
 */
fun Modifier.listItemPadding(): Modifier = this.padding(horizontal = 16.dp, vertical = 12.dp)

/**
 * Apply dialog padding
 */
fun Modifier.dialogPadding(): Modifier = this.padding(24.dp)

/**
 * Apply bottom navigation safe padding
 */
fun Modifier.bottomNavPadding(): Modifier = this.padding(bottom = 80.dp)

/**
 * Apply FAB safe padding
 */
fun Modifier.fabSafePadding(): Modifier = this.padding(bottom = 88.dp)

// ============================================
// Spacer Composables
// ============================================

/**
 * Horizontal spacer with extra small width
 */
@Composable
fun HorizontalSpacerExtraSmall() = Spacer(modifier = Modifier.width(4.dp))

/**
 * Horizontal spacer with small width
 */
@Composable
fun HorizontalSpacerSmall() = Spacer(modifier = Modifier.width(8.dp))

/**
 * Horizontal spacer with medium width
 */
@Composable
fun HorizontalSpacerMedium() = Spacer(modifier = Modifier.width(16.dp))

/**
 * Horizontal spacer with large width
 */
@Composable
fun HorizontalSpacerLarge() = Spacer(modifier = Modifier.width(24.dp))

/**
 * Horizontal spacer with custom width
 */
@Composable
fun HorizontalSpacer(width: Dp) = Spacer(modifier = Modifier.width(width))

/**
 * Vertical spacer with extra small height
 */
@Composable
fun VerticalSpacerExtraSmall() = Spacer(modifier = Modifier.height(4.dp))

/**
 * Vertical spacer with small height
 */
@Composable
fun VerticalSpacerSmall() = Spacer(modifier = Modifier.height(8.dp))

/**
 * Vertical spacer with medium height
 */
@Composable
fun VerticalSpacerMedium() = Spacer(modifier = Modifier.height(16.dp))

/**
 * Vertical spacer with large height
 */
@Composable
fun VerticalSpacerLarge() = Spacer(modifier = Modifier.height(24.dp))

/**
 * Vertical spacer with extra large height
 */
@Composable
fun VerticalSpacerExtraLarge() = Spacer(modifier = Modifier.height(32.dp))

/**
 * Vertical spacer with custom height
 */
@Composable
fun VerticalSpacer(height: Dp) = Spacer(modifier = Modifier.height(height))

/**
 * Section spacer for separating content sections
 */
@Composable
fun SectionSpacer() = Spacer(modifier = Modifier.height(24.dp))

// ============================================
// Size Modifiers
// ============================================

/**
 * Set minimum touch target size for accessibility
 */
fun Modifier.minTouchTarget(): Modifier = this.size(48.dp)

/**
 * Set icon size (small)
 */
fun Modifier.iconSizeSmall(): Modifier = this.size(16.dp)

/**
 * Set icon size (medium)
 */
fun Modifier.iconSizeMedium(): Modifier = this.size(24.dp)

/**
 * Set icon size (large)
 */
fun Modifier.iconSizeLarge(): Modifier = this.size(32.dp)

/**
 * Set avatar size (small)
 */
fun Modifier.avatarSmall(): Modifier = this.size(32.dp)

/**
 * Set avatar size (medium)
 */
fun Modifier.avatarMedium(): Modifier = this.size(40.dp)

/**
 * Set avatar size (large)
 */
fun Modifier.avatarLarge(): Modifier = this.size(56.dp)

// ============================================
// Spacing Utilities
// ============================================

/**
 * Convert dp value to spacing unit (4dp base)
 */
fun Int.spacingUnits(): Dp = (this * 4).dp

/**
 * Access spacing through MaterialTheme extension
 */
val androidx.compose.material3.MaterialTheme.spacing: Spacing
    @Composable
    @ReadOnlyComposable
    get() = LocalSpacing.current
