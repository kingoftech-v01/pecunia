package com.pecunia.ui.screens.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.pecunia.R
import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionType
import com.pecunia.ui.theme.FinanceColors
import com.pecunia.ui.theme.FinanceTypography
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel,
    onNavigateToTransactions: () -> Unit,
    onNavigateToBudgets: () -> Unit,
    onNavigateToScanner: () -> Unit,
    onNavigateToTransactionDetail: (String) -> Unit,
    onNavigateToBudgetDetail: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = stringResource(R.string.welcome_back),
                            style = MaterialTheme.typography.labelMedium
                        )
                        Text(
                            text = uiState.userName,
                            style = MaterialTheme.typography.titleLarge
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.refreshData() }) {
                        Icon(Icons.Default.Refresh, contentDescription = stringResource(R.string.refresh))
                    }
                    IconButton(onClick = { /* Open notifications */ }) {
                        Badge(
                            modifier = Modifier.offset(x = 8.dp, y = (-8).dp)
                        ) {
                            Text("${uiState.notificationCount}")
                        }
                        Icon(Icons.Outlined.Notifications, contentDescription = stringResource(R.string.notifications))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onNavigateToScanner,
                containerColor = MaterialTheme.colorScheme.primary
            ) {
                Icon(Icons.Default.CameraAlt, contentDescription = stringResource(R.string.scan_receipt))
            }
        }
    ) { paddingValues ->
        if (uiState.isLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        } else {
            LazyColumn(
                modifier = modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Balance Card
                item {
                    BalanceCard(
                        totalBalance = uiState.totalBalance,
                        income = uiState.monthlyIncome,
                        expenses = uiState.monthlyExpenses
                    )
                }

                // Quick Actions
                item {
                    QuickActionsRow(
                        onAddTransaction = onNavigateToTransactions,
                        onViewBudgets = onNavigateToBudgets,
                        onScanReceipt = onNavigateToScanner
                    )
                }

                // Budget Overview
                item {
                    SectionHeader(
                        title = stringResource(R.string.budget_overview),
                        onViewAll = onNavigateToBudgets
                    )
                }

                item {
                    BudgetOverviewRow(
                        budgets = uiState.budgets,
                        onBudgetClick = onNavigateToBudgetDetail
                    )
                }

                // Recent Transactions
                item {
                    SectionHeader(
                        title = stringResource(R.string.recent_transactions),
                        onViewAll = onNavigateToTransactions
                    )
                }

                items(uiState.recentTransactions) { transaction ->
                    TransactionListItem(
                        transaction = transaction,
                        onClick = { onNavigateToTransactionDetail(transaction.id) }
                    )
                }

                // Empty state for transactions
                if (uiState.recentTransactions.isEmpty()) {
                    item {
                        EmptyStateCard(
                            icon = Icons.Outlined.Receipt,
                            title = stringResource(R.string.no_transactions),
                            description = stringResource(R.string.no_transactions_description),
                            actionLabel = stringResource(R.string.add_transaction),
                            onAction = onNavigateToTransactions
                        )
                    }
                }
            }
        }

        // Error handling
        uiState.error?.let { error ->
            LaunchedEffect(error) {
                // Show snackbar or error dialog
            }
        }
    }
}

@Composable
private fun BalanceCard(
    totalBalance: BigDecimal,
    income: BigDecimal,
    expenses: BigDecimal,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primary
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp)
        ) {
            Text(
                text = stringResource(R.string.total_balance),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = currencyFormat.format(totalBalance),
                style = FinanceTypography.currencyLarge,
                color = MaterialTheme.colorScheme.onPrimary,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(24.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                BalanceItem(
                    label = stringResource(R.string.income),
                    amount = income,
                    icon = Icons.Default.ArrowUpward,
                    color = FinanceColors.IncomeLight
                )
                BalanceItem(
                    label = stringResource(R.string.expenses),
                    amount = expenses,
                    icon = Icons.Default.ArrowDownward,
                    color = FinanceColors.ExpenseLight
                )
            }
        }
    }
}

@Composable
private fun BalanceItem(
    label: String,
    amount: BigDecimal,
    icon: ImageVector,
    color: Color,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(color.copy(alpha = 0.2f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(20.dp)
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f)
            )
            Text(
                text = currencyFormat.format(amount),
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onPrimary,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
private fun QuickActionsRow(
    onAddTransaction: () -> Unit,
    onViewBudgets: () -> Unit,
    onScanReceipt: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceEvenly
    ) {
        QuickActionButton(
            icon = Icons.Outlined.Add,
            label = stringResource(R.string.add),
            onClick = onAddTransaction
        )
        QuickActionButton(
            icon = Icons.Outlined.AccountBalanceWallet,
            label = stringResource(R.string.budgets),
            onClick = onViewBudgets
        )
        QuickActionButton(
            icon = Icons.Outlined.CameraAlt,
            label = stringResource(R.string.scan),
            onClick = onScanReceipt
        )
        QuickActionButton(
            icon = Icons.Outlined.BarChart,
            label = stringResource(R.string.reports),
            onClick = { /* Navigate to reports */ }
        )
    }
}

@Composable
private fun QuickActionButton(
    icon: ImageVector,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .clickable(onClick = onClick)
            .padding(8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Surface(
            shape = CircleShape,
            color = MaterialTheme.colorScheme.primaryContainer,
            modifier = Modifier.size(56.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = icon,
                    contentDescription = label,
                    tint = MaterialTheme.colorScheme.onPrimaryContainer,
                    modifier = Modifier.size(24.dp)
                )
            }
        }
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
private fun SectionHeader(
    title: String,
    onViewAll: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold
        )
        TextButton(onClick = onViewAll) {
            Text(stringResource(R.string.view_all))
        }
    }
}

@Composable
private fun BudgetOverviewRow(
    budgets: List<Budget>,
    onBudgetClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    if (budgets.isEmpty()) {
        Card(
            modifier = modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = stringResource(R.string.no_budgets_set),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    } else {
        LazyRow(
            modifier = modifier,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(budgets) { budget ->
                BudgetCard(
                    budget = budget,
                    onClick = { onBudgetClick(budget.id) }
                )
            }
        }
    }
}

@Composable
private fun BudgetCard(
    budget: Budget,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }
    val progressColor = when {
        budget.isOverBudget -> FinanceColors.BudgetOverLimit
        budget.isNearLimit -> FinanceColors.BudgetWarning
        else -> FinanceColors.BudgetOnTrack
    }

    Card(
        modifier = modifier
            .width(160.dp)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = budget.name,
                style = MaterialTheme.typography.titleSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(modifier = Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { budget.percentageUsed.coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp)
                    .clip(MaterialTheme.shapes.small),
                color = progressColor,
                trackColor = progressColor.copy(alpha = 0.2f)
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "${(budget.percentageUsed * 100).toInt()}%",
                style = MaterialTheme.typography.labelMedium,
                color = progressColor
            )
            Text(
                text = "${currencyFormat.format(budget.remaining)} left",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun TransactionListItem(
    transaction: Transaction,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }
    val amountColor = when (transaction.type) {
        TransactionType.INCOME -> FinanceColors.Income
        TransactionType.EXPENSE -> FinanceColors.Expense
        TransactionType.TRANSFER -> FinanceColors.Transfer
    }
    val amountPrefix = when (transaction.type) {
        TransactionType.INCOME -> "+"
        TransactionType.EXPENSE -> "-"
        TransactionType.TRANSFER -> ""
    }

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
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                shape = CircleShape,
                color = MaterialTheme.colorScheme.secondaryContainer,
                modifier = Modifier.size(48.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Default.Receipt,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSecondaryContainer
                    )
                }
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = transaction.description,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = transaction.category.displayName,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "$amountPrefix${currencyFormat.format(transaction.amount)}",
                    style = MaterialTheme.typography.titleSmall,
                    color = amountColor,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = transaction.date.toString(),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun EmptyStateCard(
    icon: ImageVector,
    title: String,
    description: String,
    actionLabel: String,
    onAction: () -> Unit,
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
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(48.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(16.dp))
            Button(onClick = onAction) {
                Text(actionLabel)
            }
        }
    }
}
