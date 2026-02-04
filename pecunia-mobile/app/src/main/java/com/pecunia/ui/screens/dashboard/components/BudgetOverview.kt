package com.pecunia.ui.screens.dashboard.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
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
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.AccountBalanceWallet
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.TrendingDown
import androidx.compose.material.icons.outlined.TrendingUp
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.pecunia.ui.screens.dashboard.BudgetStatus
import com.pecunia.ui.screens.dashboard.BudgetUiModel
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

/**
 * Budget overview section for the dashboard.
 * Displays active budgets in a horizontal scrolling list.
 */
@Composable
fun BudgetOverviewSection(
    budgets: List<BudgetUiModel>,
    onBudgetClick: (String) -> Unit,
    onViewAllClick: () -> Unit,
    onCreateBudgetClick: () -> Unit,
    modifier: Modifier = Modifier,
    showHeader: Boolean = true
) {
    Column(modifier = modifier.fillMaxWidth()) {
        if (showHeader) {
            SectionHeader(
                title = "Budget Overview",
                onViewAll = onViewAllClick,
                showViewAll = budgets.isNotEmpty()
            )
            Spacer(modifier = Modifier.height(12.dp))
        }

        if (budgets.isEmpty()) {
            EmptyBudgetCard(onCreateBudget = onCreateBudgetClick)
        } else {
            BudgetOverviewRow(
                budgets = budgets,
                onBudgetClick = onBudgetClick
            )
        }
    }
}

/**
 * Horizontal row of budget cards.
 */
@Composable
fun BudgetOverviewRow(
    budgets: List<BudgetUiModel>,
    onBudgetClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyRow(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(horizontal = 4.dp)
    ) {
        items(
            items = budgets,
            key = { it.id }
        ) { budget ->
            BudgetOverviewCard(
                budget = budget,
                onClick = { onBudgetClick(budget.id) }
            )
        }
    }
}

/**
 * Individual budget overview card.
 */
@Composable
fun BudgetOverviewCard(
    budget: BudgetUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val progressColor by animateColorAsState(
        targetValue = when (budget.status) {
            BudgetStatus.OVER_BUDGET -> OverBudgetRed
            BudgetStatus.WARNING -> WarningOrange
            BudgetStatus.ON_TRACK -> OnTrackGreen
        },
        label = "progressColor"
    )

    val animatedProgress by animateFloatAsState(
        targetValue = budget.percentageUsed.coerceIn(0f, 1f),
        animationSpec = tween(1000),
        label = "budgetProgress"
    )

    Card(
        modifier = modifier
            .width(180.dp)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            // Header with status icon
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = budget.name,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )

                StatusIcon(status = budget.status)
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Circular progress indicator
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(80.dp),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(
                    progress = { animatedProgress },
                    modifier = Modifier.size(70.dp),
                    color = progressColor,
                    trackColor = progressColor.copy(alpha = 0.2f),
                    strokeWidth = 8.dp,
                    strokeCap = StrokeCap.Round
                )

                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "${(budget.percentageUsed * 100).toInt()}%",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = progressColor
                    )
                    Text(
                        text = "used",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Amount details
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
                        text = currencyFormat.format(budget.spentAmount),
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "Remaining",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = currencyFormat.format(budget.remaining),
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium,
                        color = if (budget.isOverBudget) OverBudgetRed else MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

/**
 * Status icon for budget cards.
 */
@Composable
private fun StatusIcon(
    status: BudgetStatus,
    modifier: Modifier = Modifier
) {
    val icon = when (status) {
        BudgetStatus.OVER_BUDGET -> Icons.Outlined.ErrorOutline
        BudgetStatus.WARNING -> Icons.Default.Warning
        BudgetStatus.ON_TRACK -> Icons.Outlined.CheckCircle
    }

    val tint = when (status) {
        BudgetStatus.OVER_BUDGET -> OverBudgetRed
        BudgetStatus.WARNING -> WarningOrange
        BudgetStatus.ON_TRACK -> OnTrackGreen
    }

    Icon(
        imageVector = icon,
        contentDescription = status.name,
        tint = tint,
        modifier = modifier.size(20.dp)
    )
}

/**
 * Compact budget progress card with linear indicator.
 */
@Composable
fun CompactBudgetCard(
    budget: BudgetUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val progressColor = when (budget.status) {
        BudgetStatus.OVER_BUDGET -> OverBudgetRed
        BudgetStatus.WARNING -> WarningOrange
        BudgetStatus.ON_TRACK -> OnTrackGreen
    }

    val animatedProgress by animateFloatAsState(
        targetValue = budget.percentageUsed.coerceIn(0f, 1f),
        animationSpec = tween(800),
        label = "compactBudgetProgress"
    )

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    StatusIcon(status = budget.status)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = budget.name,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Text(
                    text = "${(budget.percentageUsed * 100).toInt()}%",
                    style = MaterialTheme.typography.labelMedium,
                    color = progressColor,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            LinearProgressIndicator(
                progress = { animatedProgress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp)
                    .clip(RoundedCornerShape(4.dp)),
                color = progressColor,
                trackColor = progressColor.copy(alpha = 0.2f),
                strokeCap = StrokeCap.Round
            )

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "${currencyFormat.format(budget.spentAmount)} spent",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "${currencyFormat.format(budget.remaining)} left",
                    style = MaterialTheme.typography.labelSmall,
                    color = if (budget.isOverBudget) OverBudgetRed else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

/**
 * Budget summary card showing overall status.
 */
@Composable
fun BudgetSummaryCard(
    budgets: List<BudgetUiModel>,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val totalBudget = budgets.sumOf { it.totalAmount }
    val totalSpent = budgets.sumOf { it.spentAmount }
    val totalRemaining = budgets.sumOf { it.remaining }
    val overallPercentage = if (totalBudget > BigDecimal.ZERO) {
        (totalSpent.toFloat() / totalBudget.toFloat())
    } else 0f

    val budgetsOnTrack = budgets.count { it.status == BudgetStatus.ON_TRACK }
    val budgetsWarning = budgets.count { it.status == BudgetStatus.WARNING }
    val budgetsOverBudget = budgets.count { it.status == BudgetStatus.OVER_BUDGET }

    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(20.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Budget Summary",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
                ) {
                    Text(
                        text = "${budgets.size} active",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Overall progress
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(60.dp),
                    contentAlignment = Alignment.Center
                ) {
                    val animatedProgress by animateFloatAsState(
                        targetValue = overallPercentage.coerceIn(0f, 1f),
                        animationSpec = tween(1000),
                        label = "overallProgress"
                    )

                    CircularProgressIndicator(
                        progress = { animatedProgress },
                        modifier = Modifier.size(60.dp),
                        color = when {
                            overallPercentage >= 1f -> OverBudgetRed
                            overallPercentage >= 0.8f -> WarningOrange
                            else -> OnTrackGreen
                        },
                        trackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f),
                        strokeWidth = 6.dp,
                        strokeCap = StrokeCap.Round
                    )

                    Text(
                        text = "${(overallPercentage * 100).toInt()}%",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }

                Spacer(modifier = Modifier.width(16.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = currencyFormat.format(totalSpent),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Text(
                        text = "of ${currencyFormat.format(totalBudget)} total budget",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Status indicators
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                StatusIndicator(
                    count = budgetsOnTrack,
                    label = "On Track",
                    color = OnTrackGreen
                )
                StatusIndicator(
                    count = budgetsWarning,
                    label = "Warning",
                    color = WarningOrange
                )
                StatusIndicator(
                    count = budgetsOverBudget,
                    label = "Over",
                    color = OverBudgetRed
                )
            }
        }
    }
}

/**
 * Status indicator for budget summary.
 */
@Composable
private fun StatusIndicator(
    count: Int,
    label: String,
    color: Color,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(color)
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = "$count $label",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
        )
    }
}

/**
 * Empty state card for when there are no budgets.
 */
@Composable
fun EmptyBudgetCard(
    onCreateBudget: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Surface(
                shape = CircleShape,
                color = MaterialTheme.colorScheme.surface,
                modifier = Modifier.size(64.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Outlined.AccountBalanceWallet,
                        contentDescription = null,
                        modifier = Modifier.size(32.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "No budgets set",
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = "Create a budget to track your spending",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
            )

            Spacer(modifier = Modifier.height(20.dp))

            OutlinedButton(onClick = onCreateBudget) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Create Budget")
            }
        }
    }
}

/**
 * Spending insights card showing AI-powered recommendations.
 */
@Composable
fun SpendingInsightsCard(
    monthlyExpenses: BigDecimal,
    monthlyIncome: BigDecimal,
    budgetsNeedingAttention: Int,
    modifier: Modifier = Modifier,
    onViewDetails: () -> Unit = {}
) {
    val savingsRate = if (monthlyIncome > BigDecimal.ZERO) {
        ((monthlyIncome - monthlyExpenses).toFloat() / monthlyIncome.toFloat() * 100).coerceIn(-100f, 100f)
    } else 0f

    val isPositiveSavings = savingsRate >= 0

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer
        ),
        onClick = onViewDetails
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Monthly Insights",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )

                Spacer(modifier = Modifier.height(8.dp))

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (isPositiveSavings) Icons.Outlined.TrendingUp else Icons.Outlined.TrendingDown,
                        contentDescription = null,
                        tint = if (isPositiveSavings) OnTrackGreen else OverBudgetRed,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Savings rate: ${String.format("%.1f", savingsRate)}%",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.8f)
                    )
                }

                if (budgetsNeedingAttention > 0) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Warning,
                            contentDescription = null,
                            tint = WarningOrange,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "$budgetsNeedingAttention budget${if (budgetsNeedingAttention > 1) "s" else ""} need attention",
                            style = MaterialTheme.typography.bodySmall,
                            color = WarningOrange
                        )
                    }
                }
            }

            Surface(
                shape = CircleShape,
                color = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f),
                modifier = Modifier.size(48.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Outlined.TrendingUp,
                        contentDescription = null,
                        modifier = Modifier.size(24.dp),
                        tint = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.6f)
                    )
                }
            }
        }
    }
}

// Color constants
private val OnTrackGreen = Color(0xFF4CAF50)
private val WarningOrange = Color(0xFFFF9800)
private val OverBudgetRed = Color(0xFFF44336)
