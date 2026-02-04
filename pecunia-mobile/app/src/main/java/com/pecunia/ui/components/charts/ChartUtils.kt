package com.pecunia.ui.components.charts

import androidx.compose.animation.core.AnimationSpec
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.TweenSpec
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.Spring
import androidx.compose.ui.graphics.Color
import java.text.DecimalFormat
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.log10
import kotlin.math.pow

/**
 * Chart data point for various chart types
 */
data class ChartDataPoint(
    val value: Float,
    val label: String,
    val color: Color? = null,
    val metadata: Map<String, Any> = emptyMap()
)

/**
 * Time series data point for line charts
 */
data class TimeSeriesDataPoint(
    val timestamp: Long,
    val value: Float,
    val label: String? = null
)

/**
 * Line series for multi-line charts
 */
data class LineSeries(
    val id: String,
    val name: String,
    val dataPoints: List<TimeSeriesDataPoint>,
    val color: Color,
    val strokeWidth: Float = 3f,
    val showPoints: Boolean = true
)

/**
 * Bar group for grouped/stacked bar charts
 */
data class BarGroup(
    val label: String,
    val values: List<BarValue>
)

data class BarValue(
    val value: Float,
    val label: String,
    val color: Color
)

/**
 * Predefined color schemes for charts
 */
object ChartColorSchemes {

    val Default = listOf(
        Color(0xFF6366F1), // Indigo
        Color(0xFF22C55E), // Green
        Color(0xFFF59E0B), // Amber
        Color(0xFFEF4444), // Red
        Color(0xFF8B5CF6), // Violet
        Color(0xFF06B6D4), // Cyan
        Color(0xFFF97316), // Orange
        Color(0xFFEC4899), // Pink
        Color(0xFF14B8A6), // Teal
        Color(0xFF84CC16)  // Lime
    )

    val Finance = listOf(
        Color(0xFF10B981), // Emerald (income)
        Color(0xFFEF4444), // Red (expense)
        Color(0xFF3B82F6), // Blue (investment)
        Color(0xFFF59E0B), // Amber (savings)
        Color(0xFF8B5CF6), // Violet (other)
        Color(0xFF6366F1), // Indigo
        Color(0xFF14B8A6), // Teal
        Color(0xFFEC4899)  // Pink
    )

    val Monochrome = listOf(
        Color(0xFF1F2937),
        Color(0xFF374151),
        Color(0xFF4B5563),
        Color(0xFF6B7280),
        Color(0xFF9CA3AF),
        Color(0xFFD1D5DB),
        Color(0xFFE5E7EB),
        Color(0xFFF3F4F6)
    )

    val Gradient = listOf(
        Color(0xFF667EEA),
        Color(0xFF764BA2),
        Color(0xFFF093FB),
        Color(0xFFF5576C),
        Color(0xFF4FACFE),
        Color(0xFF00F2FE),
        Color(0xFF43E97B),
        Color(0xFF38F9D7)
    )

    val Pastel = listOf(
        Color(0xFFA5B4FC), // Indigo pastel
        Color(0xFF86EFAC), // Green pastel
        Color(0xFFFCD34D), // Amber pastel
        Color(0xFFFCA5A5), // Red pastel
        Color(0xFFC4B5FD), // Violet pastel
        Color(0xFF67E8F9), // Cyan pastel
        Color(0xFFFDBA74), // Orange pastel
        Color(0xFFF9A8D4)  // Pink pastel
    )

    /**
     * Get color from scheme with cycling for large datasets
     */
    fun getColor(scheme: List<Color>, index: Int): Color {
        return scheme[index % scheme.size]
    }

    /**
     * Generate gradient colors between two colors
     */
    fun generateGradient(startColor: Color, endColor: Color, steps: Int): List<Color> {
        return (0 until steps).map { i ->
            val fraction = i.toFloat() / (steps - 1).coerceAtLeast(1)
            Color(
                red = lerp(startColor.red, endColor.red, fraction),
                green = lerp(startColor.green, endColor.green, fraction),
                blue = lerp(startColor.blue, endColor.blue, fraction),
                alpha = lerp(startColor.alpha, endColor.alpha, fraction)
            )
        }
    }

    private fun lerp(start: Float, end: Float, fraction: Float): Float {
        return start + (end - start) * fraction
    }
}

/**
 * Animation specifications for charts
 */
object ChartAnimations {

    val DefaultDuration = 800
    val FastDuration = 400
    val SlowDuration = 1200

    /**
     * Standard tween animation for chart values
     */
    fun <T> tweenSpec(
        durationMillis: Int = DefaultDuration,
        delayMillis: Int = 0
    ): AnimationSpec<T> = TweenSpec(
        durationMillis = durationMillis,
        delay = delayMillis,
        easing = FastOutSlowInEasing
    )

    /**
     * Spring animation for bouncy effects
     */
    fun <T> springSpec(
        dampingRatio: Float = Spring.DampingRatioMediumBouncy,
        stiffness: Float = Spring.StiffnessLow
    ): AnimationSpec<T> = spring(
        dampingRatio = dampingRatio,
        stiffness = stiffness
    )

    /**
     * Staggered delay calculation for sequential animations
     */
    fun staggeredDelay(index: Int, baseDelay: Int = 50): Int {
        return index * baseDelay
    }
}

/**
 * Utility functions for data formatting
 */
object ChartFormatters {

    private val currencyFormat = NumberFormat.getCurrencyInstance(Locale.getDefault())
    private val percentFormat = DecimalFormat("0.0%")
    private val compactFormat = DecimalFormat("#.##")

    /**
     * Format value as currency
     */
    fun formatCurrency(value: Float): String {
        return currencyFormat.format(value.toDouble())
    }

    /**
     * Format value as percentage
     */
    fun formatPercent(value: Float): String {
        return percentFormat.format(value.toDouble())
    }

    /**
     * Format large numbers in compact form (1K, 1M, etc.)
     */
    fun formatCompact(value: Float): String {
        return when {
            abs(value) >= 1_000_000_000 -> "${compactFormat.format(value / 1_000_000_000)}B"
            abs(value) >= 1_000_000 -> "${compactFormat.format(value / 1_000_000)}M"
            abs(value) >= 1_000 -> "${compactFormat.format(value / 1_000)}K"
            else -> compactFormat.format(value)
        }
    }

    /**
     * Format value with specified decimal places
     */
    fun formatDecimal(value: Float, decimals: Int = 2): String {
        val pattern = if (decimals > 0) {
            "#,##0." + "0".repeat(decimals)
        } else {
            "#,##0"
        }
        return DecimalFormat(pattern).format(value.toDouble())
    }
}

/**
 * Utility functions for chart calculations
 */
object ChartCalculations {

    /**
     * Calculate nice axis bounds with round numbers
     */
    fun calculateAxisBounds(
        minValue: Float,
        maxValue: Float,
        preferredSteps: Int = 5
    ): AxisBounds {
        val range = maxValue - minValue
        if (range == 0f) {
            return AxisBounds(minValue - 1f, maxValue + 1f, 1f)
        }

        val roughStep = range / preferredSteps
        val magnitude = 10.0.pow(floor(log10(roughStep.toDouble()))).toFloat()

        val niceStep = when {
            roughStep / magnitude < 1.5 -> magnitude
            roughStep / magnitude < 3 -> 2 * magnitude
            roughStep / magnitude < 7 -> 5 * magnitude
            else -> 10 * magnitude
        }

        val niceMin = floor(minValue / niceStep) * niceStep
        val niceMax = ceil(maxValue / niceStep) * niceStep

        return AxisBounds(niceMin, niceMax, niceStep)
    }

    /**
     * Calculate percentage of total for each data point
     */
    fun calculatePercentages(values: List<Float>): List<Float> {
        val total = values.sum()
        return if (total > 0f) {
            values.map { it / total }
        } else {
            values.map { 0f }
        }
    }

    /**
     * Normalize values to 0-1 range
     */
    fun normalizeValues(values: List<Float>): List<Float> {
        if (values.isEmpty()) return emptyList()

        val min = values.minOrNull() ?: 0f
        val max = values.maxOrNull() ?: 0f
        val range = max - min

        return if (range > 0f) {
            values.map { (it - min) / range }
        } else {
            values.map { 0.5f }
        }
    }

    /**
     * Calculate cumulative sums for stacked charts
     */
    fun cumulativeSum(values: List<Float>): List<Float> {
        var sum = 0f
        return values.map { value ->
            sum += value
            sum
        }
    }

    /**
     * Find optimal grid line positions
     */
    fun calculateGridLines(bounds: AxisBounds): List<Float> {
        val lines = mutableListOf<Float>()
        var current = bounds.min
        while (current <= bounds.max) {
            lines.add(current)
            current += bounds.step
        }
        return lines
    }
}

/**
 * Axis bounds with calculated step
 */
data class AxisBounds(
    val min: Float,
    val max: Float,
    val step: Float
) {
    val range: Float get() = max - min
    val stepCount: Int get() = ((max - min) / step).toInt()
}

/**
 * Touch event data for chart interactions
 */
data class ChartTouchEvent(
    val x: Float,
    val y: Float,
    val dataIndex: Int?,
    val seriesIndex: Int? = null
)

/**
 * Tooltip data for display
 */
data class TooltipData(
    val title: String,
    val value: String,
    val subtitle: String? = null,
    val color: Color? = null,
    val x: Float,
    val y: Float
)

/**
 * Chart configuration options
 */
data class ChartConfig(
    val showGrid: Boolean = true,
    val showLabels: Boolean = true,
    val showLegend: Boolean = true,
    val showTooltip: Boolean = true,
    val animateOnLoad: Boolean = true,
    val enableTouch: Boolean = true,
    val gridColor: Color = Color(0xFFE5E7EB),
    val labelColor: Color = Color(0xFF6B7280),
    val backgroundColor: Color = Color.Transparent
)
