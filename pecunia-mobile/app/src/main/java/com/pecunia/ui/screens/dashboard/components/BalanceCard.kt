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
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.TrendingDown
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

/**
 * Balance card component displaying total balance, income, and expenses.
 * Features a gradient background, animated values, and expandable details.
 */
@Composable
fun BalanceCard(
    totalBalance: BigDecimal,
    monthlyIncome: BigDecimal,
    monthlyExpenses: BigDecimal,
    modifier: Modifier = Modifier,
    isBalanceVisible: Boolean = true,
    onToggleBalanceVisibility: () -> Unit = {},
    showTrend: Boolean = true,
    previousMonthBalance: BigDecimal? = null
) {
    var isExpanded by rememberSaveable { mutableStateOf(true) }
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    // Calculate trend
    val trend = previousMonthBalance?.let {
        if (it > BigDecimal.ZERO) {
            ((totalBalance - it).toFloat() / it.toFloat() * 100)
        } else null
    }

    val trendIsPositive = trend != null && trend >= 0

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = Color.Transparent
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
        shape = RoundedCornerShape(24.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primary,
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.8f),
                            MaterialTheme.colorScheme.tertiary.copy(alpha = 0.6f)
                        )
                    )
                )
        ) {
            // Decorative circles in background
            Box(
                modifier = Modifier
                    .size(150.dp)
                    .align(Alignment.TopEnd)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.05f))
            )
            Box(
                modifier = Modifier
                    .size(100.dp)
                    .align(Alignment.BottomStart)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.03f))
            )

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp)
            ) {
                // Header row with label and visibility toggle
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Total Balance",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
                    )

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(
                            onClick = onToggleBalanceVisibility,
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                imageVector = if (isBalanceVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                                contentDescription = if (isBalanceVisible) "Hide balance" else "Show balance",
                                tint = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f),
                                modifier = Modifier.size(20.dp)
                            )
                        }

                        IconButton(
                            onClick = { isExpanded = !isExpanded },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                                contentDescription = if (isExpanded) "Collapse" else "Expand",
                                tint = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f),
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Main balance amount
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (isBalanceVisible) {
                            currencyFormat.format(totalBalance)
                        } else {
                            "$***,***.**"
                        },
                        style = MaterialTheme.typography.headlineLarge,
                        color = MaterialTheme.colorScheme.onPrimary,
                        fontWeight = FontWeight.Bold
                    )

                    // Trend indicator
                    if (showTrend && trend != null && isBalanceVisible) {
                        Spacer(modifier = Modifier.width(12.dp))
                        TrendBadge(
                            trendPercentage = trend,
                            isPositive = trendIsPositive
                        )
                    }
                }

                // Expandable income/expenses section
                AnimatedVisibility(
                    visible = isExpanded,
                    enter = expandVertically(animationSpec = tween(300)) + fadeIn(),
                    exit = shrinkVertically(animationSpec = tween(300)) + fadeOut()
                ) {
                    Column {
                        Spacer(modifier = Modifier.height(24.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            BalanceDetailItem(
                                label = "Income",
                                amount = monthlyIncome,
                                icon = Icons.Default.ArrowUpward,
                                iconBackgroundColor = IncomeGreen.copy(alpha = 0.2f),
                                iconTint = IncomeGreen,
                                isVisible = isBalanceVisible
                            )
                            BalanceDetailItem(
                                label = "Expenses",
                                amount = monthlyExpenses,
                                icon = Icons.Default.ArrowDownward,
                                iconBackgroundColor = ExpenseRed.copy(alpha = 0.2f),
                                iconTint = ExpenseRed,
                                isVisible = isBalanceVisible
                            )
                        }

                        // Savings indicator
                        Spacer(modifier = Modifier.height(16.dp))
                        SavingsIndicator(
                            income = monthlyIncome,
                            expenses = monthlyExpenses,
                            isVisible = isBalanceVisible
                        )
                    }
                }
            }
        }
    }
}

/**
 * Trend badge showing percentage change.
 */
@Composable
private fun TrendBadge(
    trendPercentage: Float,
    isPositive: Boolean,
    modifier: Modifier = Modifier
) {
    val backgroundColor by animateColorAsState(
        targetValue = if (isPositive) IncomeGreen.copy(alpha = 0.2f) else ExpenseRed.copy(alpha = 0.2f),
        label = "trendBackgroundColor"
    )
    val contentColor by animateColorAsState(
        targetValue = if (isPositive) IncomeGreen else ExpenseRed,
        label = "trendContentColor"
    )

    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        color = backgroundColor
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = if (isPositive) Icons.Default.TrendingUp else Icons.Default.TrendingDown,
                contentDescription = null,
                tint = contentColor,
                modifier = Modifier.size(14.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "${if (isPositive) "+" else ""}${String.format("%.1f", trendPercentage)}%",
                style = MaterialTheme.typography.labelSmall,
                color = contentColor,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

/**
 * Individual balance detail item (income/expense).
 */
@Composable
private fun BalanceDetailItem(
    label: String,
    amount: BigDecimal,
    icon: ImageVector,
    iconBackgroundColor: Color,
    iconTint: Color,
    isVisible: Boolean,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(iconBackgroundColor),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = iconTint,
                modifier = Modifier.size(22.dp)
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f)
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = if (isVisible) currencyFormat.format(amount) else "$***.**",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onPrimary,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

/**
 * Savings indicator showing how much was saved this month.
 */
@Composable
private fun SavingsIndicator(
    income: BigDecimal,
    expenses: BigDecimal,
    isVisible: Boolean,
    modifier: Modifier = Modifier
) {
    val savings = income - expenses
    val savingsRate = if (income > BigDecimal.ZERO) {
        (savings.toFloat() / income.toFloat() * 100).coerceIn(-100f, 100f)
    } else 0f

    val animatedProgress by animateFloatAsState(
        targetValue = (savingsRate / 100f).coerceIn(0f, 1f),
        animationSpec = tween(1000),
        label = "savingsProgress"
    )

    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }
    val isPositiveSavings = savings >= BigDecimal.ZERO

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        color = Color.White.copy(alpha = 0.1f)
    ) {
        Column(
            modifier = Modifier.padding(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Monthly Savings",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
                )
                Text(
                    text = if (isVisible) {
                        "${if (isPositiveSavings) "+" else ""}${currencyFormat.format(savings)}"
                    } else {
                        "$***.**"
                    },
                    style = MaterialTheme.typography.titleSmall,
                    color = if (isPositiveSavings) IncomeGreen else ExpenseRed,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Progress bar
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(Color.White.copy(alpha = 0.2f))
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(animatedProgress)
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .background(if (isPositiveSavings) IncomeGreen else ExpenseRed)
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = if (isVisible) {
                    "Savings rate: ${String.format("%.1f", savingsRate)}%"
                } else {
                    "Savings rate: **%"
                },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.6f)
            )
        }
    }
}

/**
 * Simple balance summary card for compact layouts.
 */
@Composable
fun CompactBalanceCard(
    totalBalance: BigDecimal,
    modifier: Modifier = Modifier,
    isBalanceVisible: Boolean = true,
    onClick: () -> Unit = {}
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        ),
        onClick = onClick
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Balance",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                )
                Text(
                    text = if (isBalanceVisible) currencyFormat.format(totalBalance) else "$***,***.**",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    fontWeight = FontWeight.Bold
                )
            }
            Icon(
                imageVector = Icons.Default.ExpandMore,
                contentDescription = "View details",
                tint = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.5f)
            )
        }
    }
}

// Color constants
private val IncomeGreen = Color(0xFF4CAF50)
private val ExpenseRed = Color(0xFFF44336)
