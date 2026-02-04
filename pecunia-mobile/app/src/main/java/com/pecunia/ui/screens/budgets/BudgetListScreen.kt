package com.pecunia.ui.screens.budgets

import androidx.compose.animation.animateContentSize
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
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.math.BigDecimal
import java.text.NumberFormat
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.*

/**
 * Budget list screen displaying all user budgets with summary and filtering.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BudgetListScreen(
    viewModel: BudgetsViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onNavigateToBudgetDetail: (String) -> Unit,
    onNavigateToCreateBudget: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val pullToRefreshState = rememberPullToRefreshState()

    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is BudgetsEvent.NavigateToDetail -> {
                    onNavigateToBudgetDetail(event.budgetId)
                }
                is BudgetsEvent.ShowError -> {
                    // Show error snackbar
                }
                else -> {}
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Budgets") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { /* Open settings */ }) {
                        Icon(Icons.Outlined.Settings, contentDescription = "Settings")
                    }
                }
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onNavigateToCreateBudget,
                containerColor = MaterialTheme.colorScheme.primary,
                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                text = { Text("New Budget") }
            )
        }
    ) { paddingValues ->
        PullToRefreshBox(
            isRefreshing = uiState.isRefreshing,
            onRefresh = { viewModel.refreshBudgets() },
            state = pullToRefreshState,
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when {
                uiState.isLoading && !uiState.isRefreshing -> {
                    LoadingState(modifier = Modifier.fillMaxSize())
                }
                uiState.error != null && uiState.budgets.isEmpty() -> {
                    ErrorState(
                        error = uiState.error!!,
                        onRetry = { viewModel.loadBudgets() },
                        modifier = Modifier.fillMaxSize()
                    )
                }
                else -> {
                    BudgetListContent(
                        uiState = uiState,
                        onPeriodChange = { viewModel.onPeriodChanged(it) },
                        onBudgetClick = { viewModel.onBudgetClicked(it) },
                        onCreateBudget = onNavigateToCreateBudget,
                        modifier = modifier.fillMaxSize()
                    )
                }
            }
        }
    }
}

@Composable
private fun BudgetListContent(
    uiState: BudgetsUiState,
    onPeriodChange: (YearMonth) -> Unit,
    onBudgetClick: (String) -> Unit,
    onCreateBudget: () -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Period Selector
        item(key = "period_selector") {
            PeriodSelector(
                selectedPeriod = uiState.selectedPeriod,
                onPeriodChange = onPeriodChange
            )
        }

        // Budget Summary Card
        item(key = "summary_card") {
            BudgetSummaryCard(
                totalBudgeted = uiState.totalBudgeted,
                totalSpent = uiState.totalSpent,
                totalRemaining = uiState.totalRemaining,
                percentageUsed = uiState.overallPercentageUsed
            )
        }

        // Status Overview
        item(key = "status_overview") {
            BudgetStatusOverview(
                onTrackCount = uiState.onTrackCount,
                nearLimitCount = uiState.nearLimitCount,
                overLimitCount = uiState.overLimitCount
            )
        }

        // Section Header
        item(key = "section_header") {
            Text(
                text = "Your Budgets",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = 8.dp)
            )
        }

        // Budget List
        if (uiState.budgets.isEmpty()) {
            item(key = "empty_state") {
                EmptyBudgetsState(onCreateBudget = onCreateBudget)
            }
        } else {
            items(
                items = uiState.budgets,
                key = { it.id }
            ) { budget ->
                BudgetCard(
                    budget = budget,
                    onClick = { onBudgetClick(budget.id) }
                )
            }
        }

        // Bottom spacing for FAB
        item(key = "bottom_spacer") {
            Spacer(modifier = Modifier.height(80.dp))
        }
    }
}

@Composable
private fun PeriodSelector(
    selectedPeriod: YearMonth,
    onPeriodChange: (YearMonth) -> Unit,
    modifier: Modifier = Modifier
) {
    val formatter = remember { DateTimeFormatter.ofPattern("MMMM yyyy") }
    val currentPeriod = YearMonth.now()

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = { onPeriodChange(selectedPeriod.minusMonths(1)) }) {
            Icon(Icons.Default.ChevronLeft, contentDescription = "Previous month")
        }

        TextButton(onClick = { onPeriodChange(currentPeriod) }) {
            Text(
                text = selectedPeriod.format(formatter),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
        }

        IconButton(
            onClick = { onPeriodChange(selectedPeriod.plusMonths(1)) },
            enabled = selectedPeriod < currentPeriod
        ) {
            Icon(
                Icons.Default.ChevronRight,
                contentDescription = "Next month",
                tint = if (selectedPeriod < currentPeriod)
                    MaterialTheme.colorScheme.onSurface
                else
                    MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
            )
        }
    }
}

@Composable
private fun BudgetSummaryCard(
    totalBudgeted: BigDecimal,
    totalSpent: BigDecimal,
    totalRemaining: BigDecimal,
    percentageUsed: Float,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val progressColor = when {
        percentageUsed >= 1f -> Color(0xFFF44336)
        percentageUsed >= 0.8f -> Color(0xFFFF9800)
        else -> Color(0xFF4CAF50)
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp)
        ) {
            Text(
                text = "Total Budget",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = currencyFormat.format(totalBudgeted),
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Progress Section
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "${(percentageUsed * 100).toInt()}% used",
                    style = MaterialTheme.typography.labelMedium,
                    color = progressColor
                )
                Text(
                    text = "${currencyFormat.format(totalRemaining)} remaining",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            LinearProgressIndicator(
                progress = { percentageUsed.coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(12.dp)
                    .clip(MaterialTheme.shapes.small),
                color = progressColor,
                trackColor = progressColor.copy(alpha = 0.2f)
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Stats Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                StatColumn(
                    label = "Spent",
                    value = currencyFormat.format(totalSpent),
                    color = Color(0xFFF44336)
                )
                StatColumn(
                    label = "Remaining",
                    value = currencyFormat.format(totalRemaining),
                    color = Color(0xFF4CAF50)
                )
            }
        }
    }
}

@Composable
private fun StatColumn(
    label: String,
    value: String,
    color: Color
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.6f)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
            color = color,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun BudgetStatusOverview(
    onTrackCount: Int,
    nearLimitCount: Int,
    overLimitCount: Int,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        StatusChip(
            label = "On Track",
            count = onTrackCount,
            color = Color(0xFF4CAF50),
            modifier = Modifier.weight(1f)
        )
        StatusChip(
            label = "Near Limit",
            count = nearLimitCount,
            color = Color(0xFFFF9800),
            modifier = Modifier.weight(1f)
        )
        StatusChip(
            label = "Over",
            count = overLimitCount,
            color = Color(0xFFF44336),
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun StatusChip(
    label: String,
    count: Int,
    color: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = MaterialTheme.shapes.small,
        color = color.copy(alpha = 0.15f)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(color)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "$count $label",
                style = MaterialTheme.typography.labelSmall,
                color = color,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

@Composable
private fun BudgetCard(
    budget: BudgetListItemUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val progressColor = when {
        budget.isOverBudget -> Color(0xFFF44336)
        budget.isNearLimit -> Color(0xFFFF9800)
        else -> Color(0xFF4CAF50)
    }

    val statusIcon = when {
        budget.isOverBudget -> Icons.Default.Warning
        budget.isNearLimit -> Icons.Default.Info
        else -> Icons.Default.CheckCircle
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .animateContentSize(),
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
            // Header Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    // Budget Icon
                    Surface(
                        shape = CircleShape,
                        color = budget.color.copy(alpha = 0.15f),
                        modifier = Modifier.size(40.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                imageVector = Icons.Default.AccountBalanceWallet,
                                contentDescription = null,
                                tint = budget.color,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.width(12.dp))

                    Column {
                        Text(
                            text = budget.name,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = budget.periodType,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                // Status Icon
                Icon(
                    imageVector = statusIcon,
                    contentDescription = null,
                    tint = progressColor,
                    modifier = Modifier.size(24.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Progress Section
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = currencyFormat.format(budget.spentAmount),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "of ${currencyFormat.format(budget.totalAmount)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

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

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "${(budget.percentageUsed * 100).toInt()}% used",
                    style = MaterialTheme.typography.labelSmall,
                    color = progressColor
                )
                Text(
                    text = "${currencyFormat.format(budget.remainingAmount)} left",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Category tag if present
            budget.categoryName?.let { category ->
                Spacer(modifier = Modifier.height(12.dp))
                AssistChip(
                    onClick = { },
                    label = { Text(category) },
                    leadingIcon = {
                        Icon(
                            Icons.Default.Category,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                )
            }
        }
    }
}

@Composable
private fun EmptyBudgetsState(
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
            Icon(
                imageVector = Icons.Outlined.AccountBalanceWallet,
                contentDescription = null,
                modifier = Modifier.size(64.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "No budgets yet",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Create a budget to start tracking your spending and reach your financial goals",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(24.dp))
            Button(onClick = onCreateBudget) {
                Icon(Icons.Default.Add, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Create Budget")
            }
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
            text = "Failed to load budgets",
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
 * UI model for budget list items.
 */
data class BudgetListItemUiModel(
    val id: String,
    val name: String,
    val totalAmount: BigDecimal,
    val spentAmount: BigDecimal,
    val remainingAmount: BigDecimal,
    val percentageUsed: Float,
    val isOverBudget: Boolean,
    val isNearLimit: Boolean,
    val periodType: String,
    val categoryName: String?,
    val color: Color
)
