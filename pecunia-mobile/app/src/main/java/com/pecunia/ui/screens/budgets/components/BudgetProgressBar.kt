package com.pecunia.ui.screens.budgets.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pecunia.ui.screens.budgets.AlertLevel

/**
 * Get color based on progress percentage
 */
@Composable
fun getProgressColor(percentage: Float, alertLevel: AlertLevel = AlertLevel.NONE): Color {
    return when {
        percentage >= 100 -> MaterialTheme.colorScheme.error
        alertLevel == AlertLevel.CRITICAL -> MaterialTheme.colorScheme.error
        alertLevel == AlertLevel.HIGH -> Color(0xFFFF6B35) // Orange
        alertLevel == AlertLevel.MEDIUM -> Color(0xFFFFB347) // Light Orange
        percentage >= 75 -> Color(0xFFFFB347)
        percentage >= 50 -> Color(0xFFFFC107) // Amber
        else -> MaterialTheme.colorScheme.primary
    }
}

/**
 * Get gradient colors for progress bar
 */
@Composable
fun getProgressGradient(percentage: Float): List<Color> {
    return when {
        percentage >= 100 -> listOf(
            Color(0xFFFF5252),
            Color(0xFFD32F2F)
        )
        percentage >= 75 -> listOf(
            Color(0xFFFF9800),
            Color(0xFFFF5722)
        )
        percentage >= 50 -> listOf(
            Color(0xFFFFC107),
            Color(0xFFFF9800)
        )
        else -> listOf(
            MaterialTheme.colorScheme.primary,
            MaterialTheme.colorScheme.tertiary
        )
    }
}

/**
 * Animated Linear Progress Bar for budgets
 */
@Composable
fun BudgetProgressBar(
    progress: Float,
    modifier: Modifier = Modifier,
    height: Dp = 8.dp,
    showPercentage: Boolean = true,
    alertLevel: AlertLevel = AlertLevel.NONE,
    animationDuration: Int = 1000
) {
    var animationPlayed by remember { mutableStateOf(false) }
    val animatedProgress by animateFloatAsState(
        targetValue = if (animationPlayed) progress.coerceIn(0f, 100f) / 100f else 0f,
        animationSpec = tween(
            durationMillis = animationDuration,
            easing = FastOutSlowInEasing
        ),
        label = "progress_animation"
    )

    LaunchedEffect(key1 = true) {
        animationPlayed = true
    }

    val progressColor = getProgressColor(progress, alertLevel)
    val trackColor = MaterialTheme.colorScheme.surfaceVariant

    Column(modifier = modifier) {
        if (showPercentage) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${String.format("%.1f", progress)}%",
                    style = MaterialTheme.typography.labelMedium,
                    color = progressColor,
                    fontWeight = FontWeight.SemiBold
                )
                if (progress >= 100) {
                    Text(
                        text = "Over budget!",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.error
                    )
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(height)
                .clip(RoundedCornerShape(height / 2))
                .background(trackColor)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(animatedProgress.coerceIn(0f, 1f))
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(height / 2))
                    .background(
                        brush = Brush.horizontalGradient(
                            colors = getProgressGradient(progress)
                        )
                    )
            )

            // Overflow indicator for over-budget
            if (progress > 100) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .fillMaxHeight()
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(
                                    Color.Transparent,
                                    MaterialTheme.colorScheme.error.copy(alpha = 0.3f)
                                )
                            )
                        )
                )
            }
        }
    }
}

/**
 * Segmented Progress Bar showing multiple categories
 */
@Composable
fun SegmentedBudgetProgressBar(
    segments: List<ProgressSegment>,
    modifier: Modifier = Modifier,
    height: Dp = 12.dp,
    animationDuration: Int = 1000
) {
    var animationPlayed by remember { mutableStateOf(false) }

    LaunchedEffect(key1 = true) {
        animationPlayed = true
    }

    val totalProgress = segments.sumOf { it.progress.toDouble() }.toFloat()

    Column(modifier = modifier) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(height)
                .clip(RoundedCornerShape(height / 2))
                .background(MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Row(modifier = Modifier.fillMaxHeight()) {
                segments.forEachIndexed { index, segment ->
                    val animatedWidth by animateFloatAsState(
                        targetValue = if (animationPlayed) segment.progress / 100f else 0f,
                        animationSpec = tween(
                            durationMillis = animationDuration,
                            delayMillis = index * 100,
                            easing = FastOutSlowInEasing
                        ),
                        label = "segment_animation_$index"
                    )

                    Box(
                        modifier = Modifier
                            .fillMaxWidth(animatedWidth.coerceIn(0f, 1f - segments.take(index).sumOf { it.progress.toDouble() / 100 }.toFloat()))
                            .fillMaxHeight()
                            .background(segment.color)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Legend
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            segments.forEach { segment ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(RoundedCornerShape(2.dp))
                            .background(segment.color)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = segment.label,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

/**
 * Circular Progress Indicator for budget
 */
@Composable
fun CircularBudgetProgress(
    progress: Float,
    modifier: Modifier = Modifier,
    size: Dp = 120.dp,
    strokeWidth: Dp = 12.dp,
    alertLevel: AlertLevel = AlertLevel.NONE,
    animationDuration: Int = 1000
) {
    var animationPlayed by remember { mutableStateOf(false) }
    val animatedProgress by animateFloatAsState(
        targetValue = if (animationPlayed) progress.coerceIn(0f, 100f) / 100f else 0f,
        animationSpec = tween(
            durationMillis = animationDuration,
            easing = FastOutSlowInEasing
        ),
        label = "circular_progress_animation"
    )

    LaunchedEffect(key1 = true) {
        animationPlayed = true
    }

    val progressColor = getProgressColor(progress, alertLevel)
    val trackColor = MaterialTheme.colorScheme.surfaceVariant

    Box(
        modifier = modifier.size(size),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.size(size)) {
            val strokeWidthPx = strokeWidth.toPx()
            val arcSize = Size(size.toPx() - strokeWidthPx, size.toPx() - strokeWidthPx)
            val topLeft = Offset(strokeWidthPx / 2, strokeWidthPx / 2)

            // Track
            drawArc(
                color = trackColor,
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                topLeft = topLeft,
                size = arcSize,
                style = Stroke(width = strokeWidthPx, cap = StrokeCap.Round)
            )

            // Progress
            drawArc(
                color = progressColor,
                startAngle = -90f,
                sweepAngle = animatedProgress * 360f,
                useCenter = false,
                topLeft = topLeft,
                size = arcSize,
                style = Stroke(width = strokeWidthPx, cap = StrokeCap.Round)
            )
        }

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "${String.format("%.0f", progress)}%",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = progressColor
            )
            Text(
                text = if (progress >= 100) "Over Budget" else "Used",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * Compact progress indicator with amount
 */
@Composable
fun CompactBudgetProgress(
    spent: Double,
    total: Double,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$"
) {
    val progress = if (total > 0) (spent / total * 100).toFloat() else 0f
    val remaining = total - spent

    Column(modifier = modifier) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(
                    text = "Spent",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "$currencySymbol${String.format("%.2f", spent)}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = getProgressColor(progress)
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "Remaining",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "$currencySymbol${String.format("%.2f", remaining.coerceAtLeast(0.0))}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = if (remaining < 0) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        BudgetProgressBar(
            progress = progress,
            showPercentage = false
        )

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = "of $currencySymbol${String.format("%.2f", total)}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.align(Alignment.End)
        )
    }
}

/**
 * Data class for progress segment
 */
data class ProgressSegment(
    val label: String,
    val progress: Float,
    val color: Color
)
