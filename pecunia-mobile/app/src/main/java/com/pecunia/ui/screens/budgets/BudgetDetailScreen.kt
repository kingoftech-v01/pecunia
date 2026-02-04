package com.pecunia.ui.screens.budgets

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.math.BigDecimal
import java.text.NumberFormat
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.*

/**
 * Budget detail screen showing comprehensive budget information,
 * progress visualization, and related transactions.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BudgetDetailScreen(
    budgetId: String,
    viewModel: BudgetsViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onNavigateToEdit: (String) -> Unit,
    onNavigateToTransaction: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.detailState.collectAsStateWithLifecycle()

    var showDeleteConfirmation by remember { mutableStateOf(false) }
    var showMoreOptions by remember { mutableStateOf(false) }

    LaunchedEffect(budgetId) {
        viewModel.loadBudgetDetail(budgetId)
    }

    LaunchedEffect(Unit) {
        viewModel.detailEvents.collect { event ->
            when (event) {
                is BudgetDetailEvent.DeleteSuccess -> onNavigateBack()
                is BudgetDetailEvent.ShowError -> {
                    // Show error snackbar
                }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(uiState.budget?.name ?: "Budget") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { onNavigateToEdit(budgetId) }) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit")
                    }
                    IconButton(onClick = { showMoreOptions = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = "More options")
                    }

                    DropdownMenu(
                        expanded = showMoreOptions,
                        onDismissRequest = { showMoreOptions = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("Duplicate") },
                            onClick = {
                                showMoreOptions = false
                                viewModel.duplicateBudget(budgetId)
                            },
                            leadingIcon = {
                                Icon(Icons.Default.ContentCopy, contentDescription = null)
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Archive") },
                            onClick = {
                                showMoreOptions = false
                                viewModel.archiveBudget(budgetId)
                            },
                            leadingIcon = {
                                Icon(Icons.Default.Archive, contentDescription = null)
                            }
                        )
                        HorizontalDivider()
                        DropdownMenuItem(
                            text = {
                                Text(
                                    "Delete",
                                    color = MaterialTheme.colorScheme.error
                                )
                            },
                            onClick = {
                                showMoreOptions = false
                                showDeleteConfirmation = true
                            },
                            leadingIcon = {
                                Icon(
                                    Icons.Default.Delete,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.error
                                )
                            }
                        )
                    }
                }
            )
        }
    ) { paddingValues ->
        when {
            uiState.isLoading -> {
                LoadingState(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                )
            }
            uiState.error != null -> {
                ErrorState(
                    error = uiState.error!!,
                    onRetry = { viewModel.loadBudgetDetail(budgetId) },
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                )
            }
            uiState.budget != null -> {
                BudgetDetailContent(
                    budget = uiState.budget!!,
                    transactions = uiState.transactions,
                    onTransactionClick = onNavigateToTransaction,
                    modifier = modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                )
            }
        }

        // Delete Confirmation Dialog
        if (showDeleteConfirmation) {
            AlertDialog(
                onDismissRequest = { showDeleteConfirmation = false },
                icon = {
                    Icon(
                        Icons.Default.Warning,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error
                    )
                },
                title = { Text("Delete Budget") },
                text = {
                    Text("Are you sure you want to delete this budget? This action cannot be undone. Your transactions will not be affected.")
                },
                confirmButton = {
                    TextButton(
                        onClick = {
                            viewModel.deleteBudget(budgetId)
                            showDeleteConfirmation = false
                        },
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Delete")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDeleteConfirmation = false }) {
                        Text("Cancel")
                    }
                }
            )
        }
    }
}

@Composable
private fun BudgetDetailContent(
    budget: BudgetDetailUiModel,
    transactions: List<BudgetTransactionUiModel>,
    onTransactionClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Progress Circle Card
        item(key = "progress_circle") {
            BudgetProgressCircle(budget = budget)
        }

        // Quick Stats Row
        item(key = "quick_stats") {
            QuickStatsRow(budget = budget)
        }

        // Budget Details Card
        item(key = "details_card") {
            BudgetDetailsCard(budget = budget)
        }

        // Spending Trend Card
        item(key = "spending_trend") {
            SpendingTrendCard(
                dailySpending = budget.dailySpending,
                averageDaily = budget.averageDailySpending
            )
        }

        // Transactions Header
        item(key = "transactions_header") {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Transactions",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "${transactions.size} items",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        // Transactions List
        if (transactions.isEmpty()) {
            item(key = "empty_transactions") {
                EmptyTransactionsCard()
            }
        } else {
            items(
                items = transactions.take(10),
                key = { it.id }
            ) { transaction ->
                BudgetTransactionItem(
                    transaction = transaction,
                    onClick = { onTransactionClick(transaction.id) }
                )
            }

            if (transactions.size > 10) {
                item(key = "view_all") {
                    TextButton(
                        onClick = { /* View all transactions */ },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("View All ${transactions.size} Transactions")
                    }
                }
            }
        }

        // Bottom spacing
        item(key = "bottom_spacer") {
            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

@Composable
private fun BudgetProgressCircle(
    budget: BudgetDetailUiModel,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val progressColor = when {
        budget.isOverBudget -> Color(0xFFF44336)
        budget.isNearLimit -> Color(0xFFFF9800)
        else -> Color(0xFF4CAF50)
    }

    val animatedProgress by animateFloatAsState(
        targetValue = budget.percentageUsed.coerceIn(0f, 1f),
        animationSpec = tween(durationMillis = 1000),
        label = "progress"
    )

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier.size(200.dp),
                contentAlignment = Alignment.Center
            ) {
                // Background Circle
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val strokeWidth = 20.dp.toPx()
                    val radius = (size.minDimension - strokeWidth) / 2

                    drawCircle(
                        color = progressColor.copy(alpha = 0.2f),
                        radius = radius,
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )

                    // Progress Arc
                    drawArc(
                        color = progressColor,
                        startAngle = -90f,
                        sweepAngle = 360f * animatedProgress,
                        useCenter = false,
                        topLeft = Offset(strokeWidth / 2, strokeWidth / 2),
                        size = Size(size.width - strokeWidth, size.height - strokeWidth),
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )
                }

                // Center Content
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "${(budget.percentageUsed * 100).toInt()}%",
                        style = MaterialTheme.typography.headlineLarge,
                        fontWeight = FontWeight.Bold,
                        color = progressColor
                    )
                    Text(
                        text = "used",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Amount Summary Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                AmountColumn(
                    label = "Spent",
                    amount = currencyFormat.format(budget.spentAmount),
                    color = Color(0xFFF44336)
                )
                AmountColumn(
                    label = "Remaining",
                    amount = currencyFormat.format(budget.remainingAmount),
                    color = if (budget.remainingAmount >= BigDecimal.ZERO)
                        Color(0xFF4CAF50)
                    else
                        Color(0xFFF44336)
                )
                AmountColumn(
                    label = "Budget",
                    amount = currencyFormat.format(budget.totalAmount),
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}

@Composable
private fun AmountColumn(
    label: String,
    amount: String,
    color: Color
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = amount,
            style = MaterialTheme.typography.titleMedium,
            color = color,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun QuickStatsRow(
    budget: BudgetDetailUiModel,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        QuickStatCard(
            label = "Daily Budget",
            value = currencyFormat.format(budget.dailyBudget),
            icon = Icons.Outlined.CalendarToday,
            modifier = Modifier.weight(1f)
        )
        QuickStatCard(
            label = "Daily Average",
            value = currencyFormat.format(budget.averageDailySpending),
            icon = Icons.Outlined.TrendingUp,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun QuickStatCard(
    label: String,
    value: String,
    icon: ImageVector,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = value,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}

@Composable
private fun BudgetDetailsCard(
    budget: BudgetDetailUiModel,
    modifier: Modifier = Modifier
) {
    val dateFormatter = remember { DateTimeFormatter.ofPattern("MMM d, yyyy") }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Details",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(16.dp))

            DetailRow(label = "Period", value = budget.periodType)

            HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

            DetailRow(label = "Start Date", value = budget.startDate.format(dateFormatter))

            budget.endDate?.let { endDate ->
                HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))
                DetailRow(label = "End Date", value = endDate.format(dateFormatter))
            }

            budget.categoryName?.let { category ->
                HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))
                DetailRow(label = "Category", value = category)
            }

            HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

            DetailRow(label = "Days Remaining", value = "${budget.daysRemaining} days")

            HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

            DetailRow(
                label = "Alerts",
                value = if (budget.alertsEnabled) "Enabled at ${(budget.alertThreshold * 100).toInt()}%"
                else "Disabled"
            )
        }
    }
}

@Composable
private fun DetailRow(
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun SpendingTrendCard(
    dailySpending: List<DailySpending>,
    averageDaily: BigDecimal,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Spending Trend",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(16.dp))

            if (dailySpending.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(120.dp)
                        .clip(MaterialTheme.shapes.medium)
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "No spending data available yet.\nStart tracking to see your trend.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                }
            } else {
                // Simplified bar chart representation
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(100.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly,
                    verticalAlignment = Alignment.Bottom
                ) {
                    val maxAmount = dailySpending.maxOfOrNull { it.amount } ?: BigDecimal.ONE

                    dailySpending.takeLast(7).forEach { daily ->
                        val height = if (maxAmount > BigDecimal.ZERO) {
                            (daily.amount.toFloat() / maxAmount.toFloat() * 80).coerceIn(4f, 80f)
                        } else 4f

                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Box(
                                modifier = Modifier
                                    .width(24.dp)
                                    .height(height.dp)
                                    .clip(MaterialTheme.shapes.extraSmall)
                                    .background(MaterialTheme.colorScheme.primary)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = daily.date.dayOfMonth.toString(),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun BudgetTransactionItem(
    transaction: BudgetTransactionUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }
    val dateFormatter = remember { DateTimeFormatter.ofPattern("MMM d") }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
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
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = transaction.description,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = transaction.date.format(dateFormatter),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Text(
                text = "-${currencyFormat.format(transaction.amount)}",
                style = MaterialTheme.typography.titleSmall,
                color = Color(0xFFF44336),
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
private fun EmptyTransactionsCard(
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
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Outlined.Receipt,
                contentDescription = null,
                modifier = Modifier.size(40.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = "No transactions yet",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Transactions matching this budget will appear here",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun LoadingState(modifier: Modifier = Modifier) {
    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator()
    }
}

@Composable
private fun ErrorState(
    error: String,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Outlined.ErrorOutline,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.error
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Failed to load budget",
            style = MaterialTheme.typography.titleMedium
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = error,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(24.dp))
        Button(onClick = onRetry) {
            Icon(Icons.Default.Refresh, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Retry")
        }
    }
}

/**
 * UI model for budget detail screen.
 */
data class BudgetDetailUiModel(
    val id: String,
    val name: String,
    val totalAmount: BigDecimal,
    val spentAmount: BigDecimal,
    val remainingAmount: BigDecimal,
    val percentageUsed: Float,
    val isOverBudget: Boolean,
    val isNearLimit: Boolean,
    val periodType: String,
    val startDate: LocalDate,
    val endDate: LocalDate?,
    val categoryName: String?,
    val dailyBudget: BigDecimal,
    val averageDailySpending: BigDecimal,
    val daysRemaining: Int,
    val alertsEnabled: Boolean,
    val alertThreshold: Float,
    val dailySpending: List<DailySpending>,
    val color: Color
)

/**
 * UI model for daily spending data.
 */
data class DailySpending(
    val date: LocalDate,
    val amount: BigDecimal
)

/**
 * UI model for transactions in budget detail.
 */
data class BudgetTransactionUiModel(
    val id: String,
    val description: String,
    val amount: BigDecimal,
    val date: LocalDate,
    val categoryName: String
)

/**
 * Events emitted by the budget detail screen.
 */
sealed class BudgetDetailEvent {
    data object DeleteSuccess : BudgetDetailEvent()
    data class ShowError(val message: String) : BudgetDetailEvent()
}
