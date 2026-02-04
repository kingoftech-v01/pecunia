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
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.pecunia.R
import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetPeriod
import com.pecunia.domain.models.BudgetSummary
import com.pecunia.ui.theme.FinanceColors
import com.pecunia.ui.theme.FinanceTypography
import java.math.BigDecimal
import java.text.NumberFormat
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BudgetListScreen(
    budgets: List<Budget>,
    budgetSummary: BudgetSummary?,
    isLoading: Boolean,
    selectedPeriod: YearMonth,
    onPeriodChange: (YearMonth) -> Unit,
    onBudgetClick: (String) -> Unit,
    onAddBudget: () -> Unit,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.budgets)) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = stringResource(R.string.back))
                    }
                },
                actions = {
                    IconButton(onClick = { /* Open settings */ }) {
                        Icon(Icons.Outlined.Settings, contentDescription = stringResource(R.string.settings))
                    }
                }
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onAddBudget,
                containerColor = MaterialTheme.colorScheme.primary,
                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                text = { Text(stringResource(R.string.new_budget)) }
            )
        }
    ) { paddingValues ->
        if (isLoading) {
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
                // Period Selector
                item {
                    PeriodSelector(
                        selectedPeriod = selectedPeriod,
                        onPeriodChange = onPeriodChange
                    )
                }

                // Budget Summary Card
                budgetSummary?.let { summary ->
                    item {
                        BudgetSummaryCard(summary = summary)
                    }
                }

                // Budget Status Overview
                item {
                    BudgetStatusOverview(budgets = budgets)
                }

                // Section Header
                item {
                    Text(
                        text = stringResource(R.string.your_budgets),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }

                // Budget List
                if (budgets.isEmpty()) {
                    item {
                        EmptyBudgetsState(onAddBudget = onAddBudget)
                    }
                } else {
                    items(
                        items = budgets,
                        key = { it.id }
                    ) { budget ->
                        BudgetCard(
                            budget = budget,
                            onClick = { onBudgetClick(budget.id) }
                        )
                    }
                }
            }
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

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = { onPeriodChange(selectedPeriod.minusMonths(1)) }) {
            Icon(Icons.Default.ChevronLeft, contentDescription = stringResource(R.string.previous_month))
        }

        Text(
            text = selectedPeriod.format(formatter),
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold
        )

        IconButton(
            onClick = { onPeriodChange(selectedPeriod.plusMonths(1)) },
            enabled = selectedPeriod < YearMonth.now()
        ) {
            Icon(Icons.Default.ChevronRight, contentDescription = stringResource(R.string.next_month))
        }
    }
}

@Composable
private fun BudgetSummaryCard(
    summary: BudgetSummary,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }
    val percentageUsed = if (summary.totalBudgeted > BigDecimal.ZERO) {
        (summary.totalSpent.toFloat() / summary.totalBudgeted.toFloat()).coerceIn(0f, 1f)
    } else 0f

    val progressColor = when {
        percentageUsed >= 1f -> FinanceColors.BudgetOverLimit
        percentageUsed >= 0.8f -> FinanceColors.BudgetWarning
        else -> FinanceColors.BudgetOnTrack
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
                text = stringResource(R.string.total_budget),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = currencyFormat.format(summary.totalBudgeted),
                style = FinanceTypography.currencyLarge,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Progress Bar
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "${(percentageUsed * 100).toInt()}% ${stringResource(R.string.used)}",
                        style = MaterialTheme.typography.labelMedium,
                        color = progressColor
                    )
                    Text(
                        text = "${currencyFormat.format(summary.totalRemaining)} ${stringResource(R.string.remaining)}",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                LinearProgressIndicator(
                    progress = { percentageUsed },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(12.dp)
                        .clip(MaterialTheme.shapes.small),
                    color = progressColor,
                    trackColor = progressColor.copy(alpha = 0.2f)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Stats Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                BudgetStat(
                    label = stringResource(R.string.spent),
                    value = currencyFormat.format(summary.totalSpent),
                    color = FinanceColors.Expense
                )
                BudgetStat(
                    label = stringResource(R.string.remaining),
                    value = currencyFormat.format(summary.totalRemaining),
                    color = FinanceColors.Income
                )
            }
        }
    }
}

@Composable
private fun BudgetStat(
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
    budgets: List<Budget>,
    modifier: Modifier = Modifier
) {
    val onTrack = budgets.count { !it.isNearLimit && !it.isOverBudget }
    val nearLimit = budgets.count { it.isNearLimit }
    val overLimit = budgets.count { it.isOverBudget }

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        StatusChip(
            label = stringResource(R.string.on_track),
            count = onTrack,
            color = FinanceColors.BudgetOnTrack,
            modifier = Modifier.weight(1f)
        )
        StatusChip(
            label = stringResource(R.string.near_limit),
            count = nearLimit,
            color = FinanceColors.BudgetWarning,
            modifier = Modifier.weight(1f)
        )
        StatusChip(
            label = stringResource(R.string.over_limit),
            count = overLimit,
            color = FinanceColors.BudgetOverLimit,
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
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
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
                color = color
            )
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
                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Category Icon
                    Surface(
                        shape = CircleShape,
                        color = Color(android.graphics.Color.parseColor(budget.color)).copy(alpha = 0.15f),
                        modifier = Modifier.size(40.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                imageVector = Icons.Default.AccountBalanceWallet,
                                contentDescription = null,
                                tint = Color(android.graphics.Color.parseColor(budget.color)),
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
                            text = budget.period.displayName,
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
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = currencyFormat.format(budget.currentSpent),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "of ${currencyFormat.format(budget.amount)}",
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
                        text = "${(budget.percentageUsed * 100).toInt()}% ${stringResource(R.string.used)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = progressColor
                    )
                    Text(
                        text = "${currencyFormat.format(budget.remaining)} ${stringResource(R.string.left)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Category tag if present
            budget.category?.let { category ->
                Spacer(modifier = Modifier.height(12.dp))
                AssistChip(
                    onClick = { },
                    label = { Text(category.displayName) },
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
    onAddBudget: () -> Unit,
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
                text = stringResource(R.string.no_budgets),
                style = MaterialTheme.typography.titleMedium
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.no_budgets_description),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(24.dp))
            Button(onClick = onAddBudget) {
                Icon(Icons.Default.Add, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(stringResource(R.string.create_budget))
            }
        }
    }
}
