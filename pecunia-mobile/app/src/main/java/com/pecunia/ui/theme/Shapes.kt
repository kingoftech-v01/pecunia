package com.pecunia.ui.theme

import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Outline
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp

// ============================================
// Material 3 Shapes Configuration
// ============================================

/**
 * Material 3 Shapes for the Finance App
 * Following Material Design 3 shape scale
 */
val PecuniaShapes = Shapes(
    // Extra Small - For small components like Chips, Small Buttons
    extraSmall = RoundedCornerShape(4.dp),

    // Small - For Cards, Small FABs
    small = RoundedCornerShape(8.dp),

    // Medium - For Dialogs, FABs, Menus
    medium = RoundedCornerShape(12.dp),

    // Large - For Navigation Drawer, Bottom Sheets
    large = RoundedCornerShape(16.dp),

    // Extra Large - For Large Sheets
    extraLarge = RoundedCornerShape(28.dp)
)

// ============================================
// Common Shape Constants
// ============================================

/**
 * Common shape values used throughout the app
 */
object FinanceShapes {
    // ==========================================
    // Corner Radius Values
    // ==========================================
    val cornerRadiusNone = 0.dp
    val cornerRadiusExtraSmall = 4.dp
    val cornerRadiusSmall = 8.dp
    val cornerRadiusMedium = 12.dp
    val cornerRadiusLarge = 16.dp
    val cornerRadiusExtraLarge = 24.dp
    val cornerRadiusRound = 28.dp
    val cornerRadiusFull = 50.dp  // Percentage for pill shapes

    // ==========================================
    // Rounded Corner Shapes
    // ==========================================

    /** No rounding */
    val none = RoundedCornerShape(0.dp)

    /** Extra small rounding (4dp) - Chips, small components */
    val extraSmall = RoundedCornerShape(4.dp)

    /** Small rounding (8dp) - Cards, buttons */
    val small = RoundedCornerShape(8.dp)

    /** Medium rounding (12dp) - Dialogs, FABs */
    val medium = RoundedCornerShape(12.dp)

    /** Large rounding (16dp) - Bottom sheets, navigation */
    val large = RoundedCornerShape(16.dp)

    /** Extra large rounding (24dp) - Large sheets */
    val extraLarge = RoundedCornerShape(24.dp)

    /** Round rounding (28dp) - Very rounded elements */
    val round = RoundedCornerShape(28.dp)

    /** Full rounding - Perfect circles or pill shapes */
    val full = RoundedCornerShape(percent = 50)

    /** Circle shape */
    val circle = CircleShape

    // ==========================================
    // Component-Specific Shapes
    // ==========================================

    // Cards
    val card = RoundedCornerShape(12.dp)
    val cardSmall = RoundedCornerShape(8.dp)
    val cardLarge = RoundedCornerShape(16.dp)

    // Buttons
    val button = RoundedCornerShape(24.dp)
    val buttonSmall = RoundedCornerShape(16.dp)
    val buttonLarge = RoundedCornerShape(28.dp)
    val buttonSquared = RoundedCornerShape(8.dp)
    val buttonPill = RoundedCornerShape(percent = 50)

    // FAB (Floating Action Button)
    val fab = RoundedCornerShape(16.dp)
    val fabSmall = RoundedCornerShape(12.dp)
    val fabLarge = RoundedCornerShape(28.dp)
    val fabExtended = RoundedCornerShape(16.dp)

    // Text Fields
    val textField = RoundedCornerShape(8.dp)
    val textFieldFilled = RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp)
    val textFieldOutlined = RoundedCornerShape(4.dp)

    // Chips
    val chip = RoundedCornerShape(8.dp)
    val chipSmall = RoundedCornerShape(4.dp)
    val filterChip = RoundedCornerShape(8.dp)
    val inputChip = RoundedCornerShape(8.dp)
    val suggestionChip = RoundedCornerShape(8.dp)

    // Dialogs
    val dialog = RoundedCornerShape(28.dp)
    val dialogSmall = RoundedCornerShape(16.dp)
    val alertDialog = RoundedCornerShape(28.dp)

    // Bottom Sheets
    val bottomSheet = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
    val bottomSheetSmall = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp)
    val bottomSheetHandle = RoundedCornerShape(2.dp)

    // Navigation
    val navigationDrawer = RoundedCornerShape(topEnd = 16.dp, bottomEnd = 16.dp)
    val navigationRail = RoundedCornerShape(0.dp)
    val navigationBar = RoundedCornerShape(0.dp)
    val navigationBarItem = RoundedCornerShape(16.dp)

    // Menus
    val menu = RoundedCornerShape(4.dp)
    val dropdownMenu = RoundedCornerShape(4.dp)
    val contextMenu = RoundedCornerShape(8.dp)

    // Tooltips
    val tooltip = RoundedCornerShape(4.dp)

    // Snackbar
    val snackbar = RoundedCornerShape(4.dp)

    // Progress Indicators
    val progressLinear = RoundedCornerShape(2.dp)
    val progressCircular = CircleShape

    // Badges
    val badge = RoundedCornerShape(percent = 50)
    val badgeSmall = RoundedCornerShape(percent = 50)
    val badgeLarge = RoundedCornerShape(8.dp)

    // Images
    val imageRounded = RoundedCornerShape(8.dp)
    val imageRoundedLarge = RoundedCornerShape(16.dp)
    val imageCircle = CircleShape
    val imageThumbnail = RoundedCornerShape(4.dp)

    // Avatars
    val avatar = CircleShape
    val avatarSquared = RoundedCornerShape(8.dp)

    // Tags
    val tag = RoundedCornerShape(4.dp)
    val tagPill = RoundedCornerShape(percent = 50)

    // Dividers
    val divider = RoundedCornerShape(0.dp)

    // Search Bar
    val searchBar = RoundedCornerShape(28.dp)
    val searchBarSmall = RoundedCornerShape(20.dp)

    // Tabs
    val tabIndicator = RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp)

    // Sliders
    val sliderThumb = CircleShape
    val sliderTrack = RoundedCornerShape(2.dp)

    // Switches
    val switchThumb = CircleShape
    val switchTrack = RoundedCornerShape(percent = 50)

    // ==========================================
    // Finance App Specific Shapes
    // ==========================================

    // Transaction List Item
    val transactionItem = RoundedCornerShape(12.dp)
    val transactionIcon = CircleShape

    // Account Cards
    val accountCard = RoundedCornerShape(16.dp)
    val accountCardCompact = RoundedCornerShape(12.dp)

    // Budget Cards
    val budgetCard = RoundedCornerShape(12.dp)
    val budgetProgress = RoundedCornerShape(4.dp)

    // Goal Cards
    val goalCard = RoundedCornerShape(16.dp)
    val goalProgress = RoundedCornerShape(percent = 50)

    // Category Icons
    val categoryIcon = RoundedCornerShape(8.dp)
    val categoryIconRound = CircleShape

    // Chart Elements
    val chartContainer = RoundedCornerShape(12.dp)
    val chartBar = RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp)
    val chartLegendItem = RoundedCornerShape(4.dp)

    // Receipt Scanner
    val receiptPreview = RoundedCornerShape(12.dp)
    val receiptCapture = RoundedCornerShape(16.dp)

    // Settings Items
    val settingsItem = RoundedCornerShape(8.dp)
    val settingsSection = RoundedCornerShape(12.dp)

    // Onboarding
    val onboardingCard = RoundedCornerShape(24.dp)
    val onboardingIndicator = CircleShape

    // Empty State
    val emptyStateIcon = CircleShape
    val emptyStateCard = RoundedCornerShape(16.dp)

    // Summary Cards (Dashboard)
    val summaryCard = RoundedCornerShape(16.dp)
    val summaryCardCompact = RoundedCornerShape(12.dp)

    // Quick Actions
    val quickActionButton = RoundedCornerShape(12.dp)
    val quickActionIcon = CircleShape

    // Calendar/Date Picker
    val calendarDay = CircleShape
    val calendarMonth = RoundedCornerShape(8.dp)
    val datePicker = RoundedCornerShape(28.dp)

    // Time Picker
    val timePicker = RoundedCornerShape(28.dp)
    val timePickerInput = RoundedCornerShape(8.dp)

    // Selection
    val selectionIndicator = CircleShape
    val checkbox = RoundedCornerShape(2.dp)
    val radio = CircleShape

    // Notifications
    val notificationCard = RoundedCornerShape(12.dp)
    val notificationBadge = CircleShape

    // Filters
    val filterButton = RoundedCornerShape(20.dp)
    val filterDropdown = RoundedCornerShape(8.dp)

    // Amount Input
    val amountInput = RoundedCornerShape(12.dp)
    val amountKeypad = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp)

    // ==========================================
    // Top-Only Rounded Shapes
    // ==========================================
    fun topRounded(radius: Dp) = RoundedCornerShape(
        topStart = radius,
        topEnd = radius,
        bottomStart = 0.dp,
        bottomEnd = 0.dp
    )

    // ==========================================
    // Bottom-Only Rounded Shapes
    // ==========================================
    fun bottomRounded(radius: Dp) = RoundedCornerShape(
        topStart = 0.dp,
        topEnd = 0.dp,
        bottomStart = radius,
        bottomEnd = radius
    )

    // ==========================================
    // Start-Only Rounded Shapes
    // ==========================================
    fun startRounded(radius: Dp) = RoundedCornerShape(
        topStart = radius,
        topEnd = 0.dp,
        bottomStart = radius,
        bottomEnd = 0.dp
    )

    // ==========================================
    // End-Only Rounded Shapes
    // ==========================================
    fun endRounded(radius: Dp) = RoundedCornerShape(
        topStart = 0.dp,
        topEnd = radius,
        bottomStart = 0.dp,
        bottomEnd = radius
    )
}

// ============================================
// Custom Shapes
// ============================================

/**
 * Ticket shape with notches on the sides
 * Useful for receipt-like cards
 */
class TicketShape(
    private val cornerRadius: Dp = 12.dp,
    private val notchRadius: Dp = 8.dp
) : Shape {
    override fun createOutline(
        size: Size,
        layoutDirection: LayoutDirection,
        density: Density
    ): Outline {
        val cornerRadiusPx = with(density) { cornerRadius.toPx() }
        val notchRadiusPx = with(density) { notchRadius.toPx() }
        val notchY = size.height / 2

        val path = Path().apply {
            // Start from top-left corner
            moveTo(cornerRadiusPx, 0f)

            // Top edge
            lineTo(size.width - cornerRadiusPx, 0f)

            // Top-right corner
            quadraticBezierTo(size.width, 0f, size.width, cornerRadiusPx)

            // Right edge to notch
            lineTo(size.width, notchY - notchRadiusPx)

            // Right notch
            arcTo(
                rect = androidx.compose.ui.geometry.Rect(
                    left = size.width - notchRadiusPx,
                    top = notchY - notchRadiusPx,
                    right = size.width + notchRadiusPx,
                    bottom = notchY + notchRadiusPx
                ),
                startAngleDegrees = -90f,
                sweepAngleDegrees = -180f,
                forceMoveTo = false
            )

            // Right edge from notch to bottom
            lineTo(size.width, size.height - cornerRadiusPx)

            // Bottom-right corner
            quadraticBezierTo(size.width, size.height, size.width - cornerRadiusPx, size.height)

            // Bottom edge
            lineTo(cornerRadiusPx, size.height)

            // Bottom-left corner
            quadraticBezierTo(0f, size.height, 0f, size.height - cornerRadiusPx)

            // Left edge from bottom to notch
            lineTo(0f, notchY + notchRadiusPx)

            // Left notch
            arcTo(
                rect = androidx.compose.ui.geometry.Rect(
                    left = -notchRadiusPx,
                    top = notchY - notchRadiusPx,
                    right = notchRadiusPx,
                    bottom = notchY + notchRadiusPx
                ),
                startAngleDegrees = 90f,
                sweepAngleDegrees = -180f,
                forceMoveTo = false
            )

            // Left edge from notch to top
            lineTo(0f, cornerRadiusPx)

            // Top-left corner
            quadraticBezierTo(0f, 0f, cornerRadiusPx, 0f)

            close()
        }

        return Outline.Generic(path)
    }
}

/**
 * Squircle shape (super-ellipse)
 * A shape between a circle and a square
 */
class SquircleShape(
    private val cornerSmoothing: Float = 0.6f
) : Shape {
    override fun createOutline(
        size: Size,
        layoutDirection: LayoutDirection,
        density: Density
    ): Outline {
        val path = Path().apply {
            val width = size.width
            val height = size.height
            val smoothing = cornerSmoothing.coerceIn(0f, 1f)
            val radius = minOf(width, height) / 2 * smoothing

            // Create a squircle path
            moveTo(width / 2, 0f)

            // Top-right
            cubicTo(
                width - radius, 0f,
                width, radius,
                width, height / 2
            )

            // Bottom-right
            cubicTo(
                width, height - radius,
                width - radius, height,
                width / 2, height
            )

            // Bottom-left
            cubicTo(
                radius, height,
                0f, height - radius,
                0f, height / 2
            )

            // Top-left
            cubicTo(
                0f, radius,
                radius, 0f,
                width / 2, 0f
            )

            close()
        }

        return Outline.Generic(path)
    }
}

// ============================================
// Shape Extension Functions
// ============================================

/**
 * Creates a shape with cut corners
 */
fun cutCornerShape(size: Dp) = CutCornerShape(size)

/**
 * Creates a shape with different corner sizes
 */
fun asymmetricRoundedCornerShape(
    topStart: Dp = 0.dp,
    topEnd: Dp = 0.dp,
    bottomEnd: Dp = 0.dp,
    bottomStart: Dp = 0.dp
) = RoundedCornerShape(
    topStart = topStart,
    topEnd = topEnd,
    bottomEnd = bottomEnd,
    bottomStart = bottomStart
)

// ============================================
// Composition Local
// ============================================

/**
 * Extended shapes data class for custom shapes
 */
@Immutable
data class ExtendedShapes(
    val card: Shape = FinanceShapes.card,
    val button: Shape = FinanceShapes.button,
    val dialog: Shape = FinanceShapes.dialog,
    val bottomSheet: Shape = FinanceShapes.bottomSheet,
    val chip: Shape = FinanceShapes.chip,
    val avatar: Shape = FinanceShapes.avatar,
    val transactionItem: Shape = FinanceShapes.transactionItem,
    val accountCard: Shape = FinanceShapes.accountCard,
    val budgetCard: Shape = FinanceShapes.budgetCard,
    val summaryCard: Shape = FinanceShapes.summaryCard
)

val LocalExtendedShapes = staticCompositionLocalOf { ExtendedShapes() }

/**
 * Access extended shapes
 */
val androidx.compose.material3.MaterialTheme.extendedShapes: ExtendedShapes
    @Composable
    @ReadOnlyComposable
    get() = LocalExtendedShapes.current
