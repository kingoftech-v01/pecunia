package com.pecunia.ui.screens.budgets.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.pecunia.ui.screens.budgets.AlertLevel
import com.pecunia.ui.screens.budgets.Budget
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

/**
 * Budget card for list display
 */
@Composable
fun BudgetCard(
    budget: Budget,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$",
    showCategoryPreview: Boolean = true
) {
    val alertColor = when (budget.currentAlertLevel) {
        AlertLevel.CRITICAL -> MaterialTheme.colorScheme.error
        AlertLevel.HIGH -> Color(0xFFFF6B35)
        AlertLevel.MEDIUM -> Color(0xFFFFB347)
        AlertLevel.LOW -> Color(0xFFFFC107)
        AlertLevel.NONE -> MaterialTheme.colorScheme.primary
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // Header row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    // Status indicator
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .clip(CircleShape)
                            .background(
                                if (budget.isActive) alertColor else MaterialTheme.colorScheme.outline
                            )
                    )
                    Spacer(modifier = Modifier.width(12.dp))

                    Column {
                        Text(
                            text = budget.name,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = budget.periodType.displayName,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = "View details",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Amount row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Column {
                    Text(
                        text = "Spent",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "$currencySymbol${String.format("%,.2f", budget.spentAmount)}",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = alertColor
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "Budget",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "$currencySymbol${String.format("%,.2f", budget.totalAmount)}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Progress bar
            BudgetProgressBar(
                progress = budget.progressPercentage,
                alertLevel = budget.currentAlertLevel,
                showPercentage = true
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Footer info
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Date range
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.AccessTime,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = getDaysRemainingText(budget),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                // Remaining amount
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = if (budget.remainingAmount >= 0) {
                        MaterialTheme.colorScheme.primaryContainer
                    } else {
                        MaterialTheme.colorScheme.errorContainer
                    }
                ) {
                    Text(
                        text = if (budget.remainingAmount >= 0) {
                            "$currencySymbol${String.format("%,.2f", budget.remainingAmount)} left"
                        } else {
                            "$currencySymbol${String.format("%,.2f", -budget.remainingAmount)} over"
                        },
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Medium,
                        color = if (budget.remainingAmount >= 0) {
                            MaterialTheme.colorScheme.onPrimaryContainer
                        } else {
                            MaterialTheme.colorScheme.onErrorContainer
                        },
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            // Category preview
            if (showCategoryPreview && budget.categoryAllocations.isNotEmpty()) {
                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    budget.categoryAllocations.take(3).forEach { allocation ->
                        CategoryChip(
                            name = allocation.categoryName,
                            progress = allocation.progressPercentage
                        )
                    }

                    if (budget.categoryAllocations.size > 3) {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant
                        ) {
                            Text(
                                text = "+${budget.categoryAllocations.size - 3}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
            }

            // Alert indicator
            AnimatedVisibility(
                visible = budget.currentAlertLevel != AlertLevel.NONE,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Spacer(modifier = Modifier.height(8.dp))
                AlertBanner(alertLevel = budget.currentAlertLevel)
            }
        }
    }
}

/**
 * Category chip for preview
 */
@Composable
private fun CategoryChip(
    name: String,
    progress: Float,
    modifier: Modifier = Modifier
) {
    val chipColor = when {
        progress >= 100 -> MaterialTheme.colorScheme.errorContainer
        progress >= 75 -> Color(0xFFFFF3E0) // Orange tint
        else -> MaterialTheme.colorScheme.surfaceVariant
    }

    val textColor = when {
        progress >= 100 -> MaterialTheme.colorScheme.onErrorContainer
        progress >= 75 -> Color(0xFFE65100)
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = chipColor
    ) {
        Text(
            text = name,
            style = MaterialTheme.typography.labelSmall,
            color = textColor,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

/**
 * Alert banner component
 */
@Composable
private fun AlertBanner(
    alertLevel: AlertLevel,
    modifier: Modifier = Modifier
) {
    val (backgroundColor, textColor, icon, message) = when (alertLevel) {
        AlertLevel.CRITICAL -> Quadruple(
            MaterialTheme.colorScheme.errorContainer,
            MaterialTheme.colorScheme.onErrorContainer,
            Icons.Default.Warning,
            "Budget exceeded!"
        )
        AlertLevel.HIGH -> Quadruple(
            Color(0xFFFFF3E0),
            Color(0xFFE65100),
            Icons.Default.Warning,
            "Approaching limit (90%+)"
        )
        AlertLevel.MEDIUM -> Quadruple(
            Color(0xFFFFF8E1),
            Color(0xFFF57F17),
            Icons.Default.Warning,
            "75% of budget used"
        )
        AlertLevel.LOW -> Quadruple(
            Color(0xFFFFFDE7),
            Color(0xFFF9A825),
            Icons.Default.Check,
            "Halfway point reached"
        )
        AlertLevel.NONE -> Quadruple(
            Color.Transparent,
            Color.Transparent,
            Icons.Default.Check,
            ""
        )
    }

    if (alertLevel != AlertLevel.NONE) {
        Surface(
            modifier = modifier.fillMaxWidth(),
            shape = RoundedCornerShape(8.dp),
            color = backgroundColor
        ) {
            Row(
                modifier = Modifier.padding(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp),
                    tint = textColor
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = message,
                    style = MaterialTheme.typography.labelSmall,
                    color = textColor,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}

/**
 * Get days remaining text
 */
private fun getDaysRemainingText(budget: Budget): String {
    val today = java.time.LocalDate.now()
    return when {
        today.isAfter(budget.endDate) -> "Ended"
        today.isBefore(budget.startDate) -> {
            val days = ChronoUnit.DAYS.between(today, budget.startDate)
            "Starts in $days days"
        }
        else -> {
            val days = ChronoUnit.DAYS.between(today, budget.endDate)
            when {
                days == 0L -> "Last day"
                days == 1L -> "1 day left"
                else -> "$days days left"
            }
        }
    }
}

/**
 * Compact budget card for smaller displays
 */
@Composable
fun CompactBudgetCard(
    budget: Budget,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$"
) {
    val alertColor = getProgressColor(budget.progressPercentage, budget.currentAlertLevel)

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Progress circle
            Box(
                modifier = Modifier.size(48.dp),
                contentAlignment = Alignment.Center
            ) {
                CircularBudgetProgress(
                    progress = budget.progressPercentage,
                    size = 48.dp,
                    strokeWidth = 4.dp,
                    alertLevel = budget.currentAlertLevel
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = budget.name,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = "$currencySymbol${String.format("%,.2f", budget.spentAmount)} / $currencySymbol${String.format("%,.2f", budget.totalAmount)}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = "View details",
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

/**
 * Helper data class for alert banner
 */
private data class Quadruple<A, B, C, D>(
    val first: A,
    val second: B,
    val third: C,
    val fourth: D
)
