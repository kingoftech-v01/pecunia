package com.pecunia.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pecunia.ui.theme.BudgetDanger
import com.pecunia.ui.theme.BudgetExceeded
import com.pecunia.ui.theme.BudgetSafe
import com.pecunia.ui.theme.BudgetWarning
import com.pecunia.ui.theme.PecuniaTheme
import java.math.BigDecimal
import java.math.RoundingMode

/**
 * Budget status enum based on percentage spent
 */
enum class BudgetStatus {
    SAFE,       // 0-50%
    WARNING,    // 50-80%
    DANGER,     // 80-100%
    EXCEEDED    // >100%
}

/**
 * Get budget status from percentage
 */
fun getBudgetStatus(percentage: Float): BudgetStatus {
    return when {
        percentage <= 0.5f -> BudgetStatus.SAFE
        percentage <= 0.8f -> BudgetStatus.WARNING
        percentage <= 1.0f -> BudgetStatus.DANGER
        else -> BudgetStatus.EXCEEDED
    }
}

/**
 * Get color for budget status
 */
@Composable
fun getBudgetStatusColor(status: BudgetStatus): Color {
    return when (status) {
        BudgetStatus.SAFE -> BudgetSafe
        BudgetStatus.WARNING -> BudgetWarning
        BudgetStatus.DANGER -> BudgetDanger
        BudgetStatus.EXCEEDED -> BudgetExceeded
    }
}

/**
 * Budget progress bar component with animated progress and color
 *
 * @param spent Amount spent
 * @param budget Total budget amount
 * @param modifier Modifier for the component
 * @param height Height of the progress bar
 * @param showLabels Whether to show spent/remaining labels
 * @param showPercentage Whether to show percentage text
 * @param currencySymbol Currency symbol for formatting
 * @param animate Whether to animate the progress
 */
@Composable
fun BudgetProgressBar(
    spent: BigDecimal,
    budget: BigDecimal,
    modifier: Modifier = Modifier,
    height: Dp = 8.dp,
    showLabels: Boolean = true,
    showPercentage: Boolean = true,
    currencySymbol: String = "$",
    animate: Boolean = true
) {
    val percentage = if (budget > BigDecimal.ZERO) {
        spent.divide(budget, 4, RoundingMode.HALF_UP).toFloat()
    } else {
        0f
    }

    val status = getBudgetStatus(percentage)
    val remaining = (budget - spent).coerceAtLeast(BigDecimal.ZERO)

    // Animation
    var targetProgress by remember { mutableFloatStateOf(0f) }
    LaunchedEffect(percentage) {
        targetProgress = percentage.coerceIn(0f, 1f)
    }

    val animatedProgress by animateFloatAsState(
        targetValue = if (animate) targetProgress else percentage.coerceIn(0f, 1f),
        animationSpec = tween(
            durationMillis = 1000,
            easing = FastOutSlowInEasing
        ),
        label = "progress"
    )

    val animatedColor by animateColorAsState(
        targetValue = getBudgetStatusColor(status),
        animationSpec = tween(durationMillis = 300),
        label = "color"
    )

    Column(modifier = modifier.fillMaxWidth()) {
        // Labels row
        if (showLabels) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Spent amount
                Column {
                    Text(
                        text = "Spent",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "$currencySymbol${formatBudgetAmount(spent)}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = animatedColor
                    )
                }

                // Percentage in center
                if (showPercentage) {
                    Text(
                        text = "${(percentage * 100).toInt()}%",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = animatedColor
                    )
                }

                // Remaining/Budget amount
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = if (status == BudgetStatus.EXCEEDED) "Over budget" else "Remaining",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = if (status == BudgetStatus.EXCEEDED) {
                            "$currencySymbol${formatBudgetAmount(spent - budget)}"
                        } else {
                            "$currencySymbol${formatBudgetAmount(remaining)}"
                        },
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = if (status == BudgetStatus.EXCEEDED) {
                            BudgetExceeded
                        } else {
                            MaterialTheme.colorScheme.onSurface
                        }
                    )
                }
            }
        }

        // Progress bar
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(height)
                .clip(RoundedCornerShape(height / 2))
                .background(MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(animatedProgress)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(height / 2))
                    .background(animatedColor)
            )
        }

        // Budget total label
        if (showLabels) {
            Text(
                text = "of $currencySymbol${formatBudgetAmount(budget)} budget",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp)
            )
        }
    }
}

/**
 * Simple progress bar without labels (for compact displays)
 */
@Composable
fun BudgetProgressBarSimple(
    spent: BigDecimal,
    budget: BigDecimal,
    modifier: Modifier = Modifier,
    height: Dp = 6.dp,
    animate: Boolean = true
) {
    val percentage = if (budget > BigDecimal.ZERO) {
        spent.divide(budget, 4, RoundingMode.HALF_UP).toFloat()
    } else {
        0f
    }

    val status = getBudgetStatus(percentage)

    var targetProgress by remember { mutableFloatStateOf(0f) }
    LaunchedEffect(percentage) {
        targetProgress = percentage.coerceIn(0f, 1f)
    }

    val animatedProgress by animateFloatAsState(
        targetValue = if (animate) targetProgress else percentage.coerceIn(0f, 1f),
        animationSpec = tween(
            durationMillis = 800,
            easing = FastOutSlowInEasing
        ),
        label = "progress"
    )

    val animatedColor by animateColorAsState(
        targetValue = getBudgetStatusColor(status),
        animationSpec = tween(durationMillis = 300),
        label = "color"
    )

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(height)
            .clip(RoundedCornerShape(height / 2))
            .background(MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(animatedProgress)
                .fillMaxHeight()
                .clip(RoundedCornerShape(height / 2))
                .background(animatedColor)
        )
    }
}

/**
 * Material3 styled linear progress indicator
 */
@Composable
fun BudgetLinearIndicator(
    spent: BigDecimal,
    budget: BigDecimal,
    modifier: Modifier = Modifier
) {
    val percentage = if (budget > BigDecimal.ZERO) {
        spent.divide(budget, 4, RoundingMode.HALF_UP).toFloat().coerceIn(0f, 1f)
    } else {
        0f
    }

    val status = getBudgetStatus(percentage)
    val color = getBudgetStatusColor(status)

    LinearProgressIndicator(
        progress = { percentage },
        modifier = modifier
            .fillMaxWidth()
            .height(8.dp),
        color = color,
        trackColor = MaterialTheme.colorScheme.surfaceVariant,
        strokeCap = StrokeCap.Round
    )
}

/**
 * Format budget amount for display
 */
private fun formatBudgetAmount(amount: BigDecimal): String {
    return when {
        amount >= BigDecimal(1000000) -> {
            "${amount.divide(BigDecimal(1000000), 1, RoundingMode.HALF_UP)}M"
        }
        amount >= BigDecimal(1000) -> {
            "${amount.divide(BigDecimal(1000), 1, RoundingMode.HALF_UP)}K"
        }
        else -> {
            amount.setScale(2, RoundingMode.HALF_UP).toString()
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun BudgetProgressBarPreview() {
    PecuniaTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            // Safe (30%)
            BudgetProgressBar(
                spent = BigDecimal("300"),
                budget = BigDecimal("1000")
            )

            // Warning (65%)
            BudgetProgressBar(
                spent = BigDecimal("650"),
                budget = BigDecimal("1000")
            )

            // Danger (90%)
            BudgetProgressBar(
                spent = BigDecimal("900"),
                budget = BigDecimal("1000")
            )

            // Exceeded (120%)
            BudgetProgressBar(
                spent = BigDecimal("1200"),
                budget = BigDecimal("1000")
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun BudgetProgressBarSimplePreview() {
    PecuniaTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            BudgetProgressBarSimple(
                spent = BigDecimal("400"),
                budget = BigDecimal("1000")
            )

            BudgetProgressBarSimple(
                spent = BigDecimal("750"),
                budget = BigDecimal("1000")
            )

            BudgetProgressBarSimple(
                spent = BigDecimal("950"),
                budget = BigDecimal("1000")
            )
        }
    }
}
