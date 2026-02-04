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
import androidx.compose.material.icons.filled.Category
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Flight
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.Restaurant
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.ShoppingBag
import androidx.compose.material.icons.filled.Spa
import androidx.compose.material.icons.filled.Warning
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.pecunia.ui.screens.budgets.CategoryAllocation

/**
 * Budget category item row for detail screen
 */
@Composable
fun BudgetItemRow(
    allocation: CategoryAllocation,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$",
    onClick: (() -> Unit)? = null,
    showProgressBar: Boolean = true,
    isExpanded: Boolean = false
) {
    var expanded by remember { mutableStateOf(isExpanded) }

    val progressColor = when {
        allocation.progressPercentage >= 100 -> MaterialTheme.colorScheme.error
        allocation.progressPercentage >= 75 -> Color(0xFFFF6B35)
        allocation.progressPercentage >= 50 -> Color(0xFFFFC107)
        else -> MaterialTheme.colorScheme.primary
    }

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .then(
                if (onClick != null) Modifier.clickable { onClick() }
                else Modifier.clickable { expanded = !expanded }
            ),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Category icon and name
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    // Icon container
                    Box(
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(
                                if (allocation.isOverAllocated) {
                                    MaterialTheme.colorScheme.errorContainer
                                } else {
                                    MaterialTheme.colorScheme.primaryContainer
                                }
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = getCategoryIcon(allocation.categoryIcon),
                            contentDescription = allocation.categoryName,
                            modifier = Modifier.size(20.dp),
                            tint = if (allocation.isOverAllocated) {
                                MaterialTheme.colorScheme.onErrorContainer
                            } else {
                                MaterialTheme.colorScheme.onPrimaryContainer
                            }
                        )
                    }

                    Spacer(modifier = Modifier.width(12.dp))

                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = allocation.categoryName,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Medium,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )

                            if (allocation.isOverAllocated) {
                                Spacer(modifier = Modifier.width(4.dp))
                                Icon(
                                    imageVector = Icons.Default.Warning,
                                    contentDescription = "Over budget",
                                    modifier = Modifier.size(14.dp),
                                    tint = MaterialTheme.colorScheme.error
                                )
                            }
                        }

                        Text(
                            text = "${String.format("%.1f", allocation.progressPercentage)}% used",
                            style = MaterialTheme.typography.labelSmall,
                            color = progressColor
                        )
                    }
                }

                // Amounts
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "$currencySymbol${String.format("%,.2f", allocation.spentAmount)}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = progressColor
                    )
                    Text(
                        text = "of $currencySymbol${String.format("%,.2f", allocation.allocatedAmount)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Progress bar
            if (showProgressBar) {
                Spacer(modifier = Modifier.height(12.dp))

                BudgetProgressBar(
                    progress = allocation.progressPercentage,
                    height = 6.dp,
                    showPercentage = false
                )
            }

            // Expanded details
            AnimatedVisibility(
                visible = expanded,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        DetailItem(
                            label = "Remaining",
                            value = "$currencySymbol${String.format("%,.2f", allocation.remainingAmount.coerceAtLeast(0.0))}",
                            valueColor = if (allocation.remainingAmount < 0) {
                                MaterialTheme.colorScheme.error
                            } else {
                                MaterialTheme.colorScheme.onSurface
                            }
                        )
                        DetailItem(
                            label = "Overspent",
                            value = if (allocation.isOverAllocated) {
                                "$currencySymbol${String.format("%,.2f", -allocation.remainingAmount)}"
                            } else "-",
                            valueColor = MaterialTheme.colorScheme.error
                        )
                    }
                }
            }
        }
    }
}

/**
 * Detail item for expanded view
 */
@Composable
private fun DetailItem(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    valueColor: Color = MaterialTheme.colorScheme.onSurface
) {
    Column(modifier = modifier) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Medium,
            color = valueColor
        )
    }
}

/**
 * Compact budget item row
 */
@Composable
fun CompactBudgetItemRow(
    allocation: CategoryAllocation,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$",
    onClick: (() -> Unit)? = null
) {
    val progressColor = when {
        allocation.progressPercentage >= 100 -> MaterialTheme.colorScheme.error
        allocation.progressPercentage >= 75 -> Color(0xFFFF6B35)
        else -> MaterialTheme.colorScheme.primary
    }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable { onClick() } else Modifier)
            .padding(vertical = 8.dp, horizontal = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.weight(1f)
        ) {
            // Small icon
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = getCategoryIcon(allocation.categoryIcon),
                    contentDescription = null,
                    modifier = Modifier.size(16.dp),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            Text(
                text = allocation.categoryName,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            // Mini progress bar
            Box(
                modifier = Modifier
                    .width(40.dp)
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(allocation.progressPercentage.coerceIn(0f, 100f) / 100f)
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(progressColor)
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            Text(
                text = "${String.format("%.0f", allocation.progressPercentage)}%",
                style = MaterialTheme.typography.labelSmall,
                color = progressColor,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

/**
 * Budget allocation summary header
 */
@Composable
fun BudgetAllocationSummary(
    totalAllocated: Double,
    totalSpent: Double,
    budgetTotal: Double,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$"
) {
    val allocationPercentage = if (budgetTotal > 0) (totalAllocated / budgetTotal * 100) else 0.0
    val spentPercentage = if (totalAllocated > 0) (totalSpent / totalAllocated * 100) else 0.0

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.primaryContainer
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Category Allocations",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "Total Allocated",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                    Text(
                        text = "$currencySymbol${String.format("%,.2f", totalAllocated)}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Text(
                        text = "${String.format("%.1f", allocationPercentage)}% of budget",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "Category Spending",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                    Text(
                        text = "$currencySymbol${String.format("%,.2f", totalSpent)}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Text(
                        text = "${String.format("%.1f", spentPercentage)}% of allocated",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                }
            }

            // Unallocated warning if applicable
            val unallocated = budgetTotal - totalAllocated
            if (unallocated > 0) {
                Spacer(modifier = Modifier.height(8.dp))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f)
                ) {
                    Text(
                        text = "$currencySymbol${String.format("%,.2f", unallocated)} unallocated",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }
        }
    }
}

/**
 * Get icon for category
 */
@Composable
fun getCategoryIcon(iconName: String): ImageVector {
    return when (iconName.lowercase()) {
        "restaurant", "food" -> Icons.Default.Restaurant
        "directions_car", "transportation" -> Icons.Default.DirectionsCar
        "shopping_bag", "shopping" -> Icons.Default.ShoppingBag
        "movie", "entertainment" -> Icons.Default.Movie
        "receipt", "bills" -> Icons.Default.Receipt
        "medical_services", "healthcare" -> Icons.Default.LocalHospital
        "school", "education" -> Icons.Default.School
        "flight", "travel" -> Icons.Default.Flight
        "spa", "personal" -> Icons.Default.Spa
        "more_horiz", "other" -> Icons.Default.MoreHoriz
        else -> Icons.Default.Category
    }
}
