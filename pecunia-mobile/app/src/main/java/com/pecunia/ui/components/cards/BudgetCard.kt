package com.pecunia.ui.components.cards

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import java.text.NumberFormat
import java.util.*

/**
 * Budget status based on spending percentage
 */
enum class BudgetStatus(
    val color: Color,
    val icon: ImageVector,
    val label: String
) {
    GOOD(
        color = Color(0xFF4CAF50),
        icon = Icons.Outlined.CheckCircle,
        label = "Dans le budget"
    ),
    WARNING(
        color = Color(0xFFFF9800),
        icon = Icons.Outlined.Warning,
        label = "Attention"
    ),
    CRITICAL(
        color = Color(0xFFF44336),
        icon = Icons.Outlined.Error,
        label = "Limite atteinte"
    ),
    EXCEEDED(
        color = Color(0xFFB71C1C),
        icon = Icons.Filled.ErrorOutline,
        label = "Budget dépassé"
    )
}

/**
 * Budget UI model
 */
data class BudgetUiModel(
    val id: String,
    val name: String,
    val categoryName: String,
    val categoryIcon: ImageVector,
    val categoryColor: Color,
    val spent: Double,
    val limit: Double,
    val period: String = "Ce mois",
    val transactionCount: Int = 0
) {
    val remaining: Double get() = limit - spent
    val percentage: Float get() = (spent / limit).toFloat().coerceIn(0f, 1.5f)
    val displayPercentage: Int get() = (percentage * 100).toInt()

    val status: BudgetStatus get() = when {
        percentage >= 1.0f -> BudgetStatus.EXCEEDED
        percentage >= 0.9f -> BudgetStatus.CRITICAL
        percentage >= 0.75f -> BudgetStatus.WARNING
        else -> BudgetStatus.GOOD
    }
}

/**
 * Standard budget card with progress bar
 */
@Composable
fun BudgetCard(
    budget: BudgetUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(budget.categoryColor.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = budget.categoryIcon,
                            contentDescription = null,
                            modifier = Modifier.size(20.dp),
                            tint = budget.categoryColor
                        )
                    }

                    Spacer(modifier = Modifier.width(12.dp))

                    Column {
                        Text(
                            text = budget.name,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            text = budget.period,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                // Status badge
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = budget.status.color.copy(alpha = 0.15f)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = budget.status.icon,
                            contentDescription = null,
                            modifier = Modifier.size(14.dp),
                            tint = budget.status.color
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "${budget.displayPercentage}%",
                            style = MaterialTheme.typography.labelSmall,
                            color = budget.status.color,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Progress bar
            BudgetProgressBar(
                progress = budget.percentage.coerceAtMost(1f),
                color = budget.status.color,
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Amounts row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "Dépensé",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = formatCurrency(budget.spent),
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = budget.status.color
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "Restant",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = formatCurrency(budget.remaining.coerceAtLeast(0.0)),
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "Limite",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = formatCurrency(budget.limit),
                        style = MaterialTheme.typography.bodyLarge
                    )
                }
            }
        }
    }
}

/**
 * Compact budget card for lists
 */
@Composable
fun CompactBudgetCard(
    budget: BudgetUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Row(
            modifier = Modifier
                .padding(12.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(CircleShape)
                    .background(budget.categoryColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = budget.categoryIcon,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                    tint = budget.categoryColor
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = budget.name,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(4.dp))

                LinearProgressIndicator(
                    progress = { budget.percentage.coerceAtMost(1f) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp)),
                    color = budget.status.color,
                    trackColor = MaterialTheme.colorScheme.surfaceVariant
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = formatCurrency(budget.spent),
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = budget.status.color
                )
                Text(
                    text = "/ ${formatCurrency(budget.limit)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

/**
 * Expandable budget card with details
 */
@Composable
fun ExpandableBudgetCard(
    budget: BudgetUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    var isExpanded by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable { isExpanded = !isExpanded },
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            // Main content (always visible)
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(budget.categoryColor.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = budget.categoryIcon,
                        contentDescription = null,
                        modifier = Modifier.size(24.dp),
                        tint = budget.categoryColor
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = budget.name,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Medium
                    )
                    Text(
                        text = "${budget.displayPercentage}% utilisé",
                        style = MaterialTheme.typography.bodySmall,
                        color = budget.status.color
                    )
                }

                Icon(
                    imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = if (isExpanded) "Réduire" else "Agrandir",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Progress bar
            BudgetProgressBar(
                progress = budget.percentage.coerceAtMost(1f),
                color = budget.status.color,
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )

            // Expandable details
            AnimatedVisibility(
                visible = isExpanded,
                enter = expandVertically(),
                exit = shrinkVertically()
            ) {
                Column {
                    Spacer(modifier = Modifier.height(16.dp))

                    HorizontalDivider()

                    Spacer(modifier = Modifier.height(16.dp))

                    // Detailed stats
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        BudgetStatItem(
                            label = "Dépensé",
                            value = formatCurrency(budget.spent),
                            color = budget.status.color
                        )
                        BudgetStatItem(
                            label = "Restant",
                            value = formatCurrency(budget.remaining.coerceAtLeast(0.0)),
                            color = if (budget.remaining > 0) Color(0xFF4CAF50) else MaterialTheme.colorScheme.error
                        )
                        BudgetStatItem(
                            label = "Limite",
                            value = formatCurrency(budget.limit)
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Transaction count and action
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "${budget.transactionCount} transactions",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        TextButton(onClick = onClick) {
                            Text("Voir les détails")
                            Spacer(modifier = Modifier.width(4.dp))
                            Icon(
                                imageVector = Icons.Default.ArrowForward,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * Budget stat item for expanded card
 */
@Composable
private fun BudgetStatItem(
    label: String,
    value: String,
    color: Color = MaterialTheme.colorScheme.onSurface
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = color
        )
    }
}

/**
 * Custom budget progress bar with rounded corners
 */
@Composable
fun BudgetProgressBar(
    progress: Float,
    color: Color,
    trackColor: Color,
    modifier: Modifier = Modifier,
    height: Float = 8f
) {
    val animatedProgress by animateFloatAsState(
        targetValue = progress,
        animationSpec = tween(durationMillis = 500, easing = FastOutSlowInEasing),
        label = "progress"
    )

    LinearProgressIndicator(
        progress = { animatedProgress },
        modifier = modifier
            .fillMaxWidth()
            .height(height.dp)
            .clip(RoundedCornerShape(height.dp / 2)),
        color = color,
        trackColor = trackColor,
        strokeCap = StrokeCap.Round
    )
}

/**
 * Budget overview card for dashboard
 */
@Composable
fun BudgetOverviewCard(
    totalBudget: Double,
    totalSpent: Double,
    budgetCount: Int,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val percentage = (totalSpent / totalBudget).toFloat().coerceIn(0f, 1f)
    val status = when {
        percentage >= 1.0f -> BudgetStatus.EXCEEDED
        percentage >= 0.9f -> BudgetStatus.CRITICAL
        percentage >= 0.75f -> BudgetStatus.WARNING
        else -> BudgetStatus.GOOD
    }

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
                    text = "Budgets du mois",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )

                Text(
                    text = "$budgetCount budgets",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Column {
                    Text(
                        text = formatCurrency(totalSpent),
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Text(
                        text = "sur ${formatCurrency(totalBudget)}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                }

                CircularProgressIndicator(
                    progress = { percentage },
                    modifier = Modifier.size(56.dp),
                    color = status.color,
                    trackColor = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.2f),
                    strokeWidth = 6.dp,
                    strokeCap = StrokeCap.Round
                )
            }
        }
    }
}

// Helper function

private fun formatCurrency(amount: Double): String {
    val formatter = NumberFormat.getCurrencyInstance(Locale.FRANCE)
    return formatter.format(amount)
}

// Previews

@Preview(showBackground = true)
@Composable
private fun BudgetCardPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            BudgetCard(
                budget = BudgetUiModel(
                    id = "1",
                    name = "Alimentation",
                    categoryName = "Alimentation",
                    categoryIcon = Icons.Outlined.ShoppingCart,
                    categoryColor = Color(0xFF4CAF50),
                    spent = 250.0,
                    limit = 400.0,
                    transactionCount = 15
                ),
                onClick = {}
            )

            BudgetCard(
                budget = BudgetUiModel(
                    id = "2",
                    name = "Restaurants",
                    categoryName = "Restaurants",
                    categoryIcon = Icons.Outlined.Restaurant,
                    categoryColor = Color(0xFFFF9800),
                    spent = 180.0,
                    limit = 200.0,
                    transactionCount = 8
                ),
                onClick = {}
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun CompactBudgetCardPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            CompactBudgetCard(
                budget = BudgetUiModel(
                    id = "1",
                    name = "Transport",
                    categoryName = "Transport",
                    categoryIcon = Icons.Outlined.DirectionsCar,
                    categoryColor = Color(0xFF9C27B0),
                    spent = 75.0,
                    limit = 150.0
                ),
                onClick = {}
            )
            CompactBudgetCard(
                budget = BudgetUiModel(
                    id = "2",
                    name = "Loisirs",
                    categoryName = "Loisirs",
                    categoryIcon = Icons.Outlined.SportsEsports,
                    categoryColor = Color(0xFF2196F3),
                    spent = 220.0,
                    limit = 200.0
                ),
                onClick = {}
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun ExpandableBudgetCardPreview() {
    MaterialTheme {
        ExpandableBudgetCard(
            budget = BudgetUiModel(
                id = "1",
                name = "Shopping",
                categoryName = "Shopping",
                categoryIcon = Icons.Outlined.ShoppingBag,
                categoryColor = Color(0xFFE91E63),
                spent = 320.0,
                limit = 350.0,
                transactionCount = 12
            ),
            onClick = {},
            modifier = Modifier.padding(16.dp)
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun BudgetOverviewCardPreview() {
    MaterialTheme {
        BudgetOverviewCard(
            totalBudget = 2000.0,
            totalSpent = 1450.0,
            budgetCount = 6,
            onClick = {},
            modifier = Modifier.padding(16.dp)
        )
    }
}
