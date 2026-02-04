package com.pecunia.ui.screens.dashboard

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Insights
import androidx.compose.material.icons.outlined.Lightbulb
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.TipsAndUpdates
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.pecunia.ui.screens.dashboard.components.BalanceCard
import com.pecunia.ui.screens.dashboard.components.BudgetOverviewRow
import com.pecunia.ui.screens.dashboard.components.BudgetOverviewSection
import com.pecunia.ui.screens.dashboard.components.EmptyBudgetCard
import com.pecunia.ui.screens.dashboard.components.EmptyTransactionsCard
import com.pecunia.ui.screens.dashboard.components.ExpandableQuickActionsFab
import com.pecunia.ui.screens.dashboard.components.QuickActionsSection
import com.pecunia.ui.screens.dashboard.components.RecentTransactionsList
import com.pecunia.ui.screens.dashboard.components.SectionHeader
import com.pecunia.ui.screens.dashboard.components.SpeedDialFab
import com.pecunia.ui.screens.dashboard.components.SpeedDialItem
import com.pecunia.ui.screens.dashboard.components.SpendingInsightsCard
import com.pecunia.ui.screens.dashboard.components.TransactionListItem
import kotlinx.coroutines.launch
import java.math.BigDecimal

/**
 * Dashboard screen composable that displays financial summary, recent transactions,
 * budget overview, and AI-powered insights with pull-to-refresh functionality.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel = hiltViewModel(),
    onNavigateToTransactions: () -> Unit,
    onNavigateToBudgets: () -> Unit,
    onNavigateToScanner: () -> Unit,
    onNavigateToTransactionDetail: (String) -> Unit,
    onNavigateToBudgetDetail: (String) -> Unit,
    onNavigateToAddTransaction: () -> Unit,
    onNavigateToReports: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val pullToRefreshState = rememberPullToRefreshState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    // Balance visibility state
    var isBalanceVisible by rememberSaveable { mutableStateOf(true) }

    // FAB expanded state
    var isFabExpanded by rememberSaveable { mutableStateOf(false) }

    // Show/hide FAB based on scroll
    val showFab by remember {
        derivedStateOf {
            listState.firstVisibleItemIndex < 3
        }
    }

    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is DashboardEvent.NavigateToTransactionDetail -> {
                    onNavigateToTransactionDetail(event.transactionId)
                }
                is DashboardEvent.NavigateToBudgetDetail -> {
                    onNavigateToBudgetDetail(event.budgetId)
                }
                is DashboardEvent.ShowError -> {
                    scope.launch {
                        snackbarHostState.showSnackbar(event.message)
                    }
                }
                is DashboardEvent.ShowSnackbar -> {
                    scope.launch {
                        snackbarHostState.showSnackbar(event.message)
                    }
                }
                is DashboardEvent.SyncCompleted -> {
                    scope.launch {
                        snackbarHostState.showSnackbar("Data synced successfully")
                    }
                }
                else -> {}
            }
        }
    }

    Scaffold(
        topBar = {
            DashboardTopBar(
                userName = uiState.userName,
                notificationCount = uiState.notificationCount,
                onRefresh = { viewModel.refreshData() },
                onNotificationsClick = { viewModel.markNotificationsAsRead() }
            )
        },
        floatingActionButton = {
            AnimatedVisibility(
                visible = showFab,
                enter = slideInVertically(initialOffsetY = { it * 2 }) + fadeIn(),
                exit = slideOutVertically(targetOffsetY = { it * 2 }) + fadeOut()
            ) {
                ExpandableQuickActionsFab(
                    onAddTransaction = onNavigateToAddTransaction,
                    onScanReceipt = onNavigateToScanner,
                    onTransfer = onNavigateToTransactions,
                    expanded = isFabExpanded,
                    onExpandedChange = { isFabExpanded = it }
                )
            }
        },
        snackbarHost = {
            SnackbarHost(hostState = snackbarHostState)
        }
    ) { paddingValues ->
        PullToRefreshBox(
            isRefreshing = uiState.isRefreshing,
            onRefresh = { viewModel.refreshData() },
            state = pullToRefreshState,
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when {
                uiState.isLoading && !uiState.isRefreshing -> {
                    DashboardLoadingState(modifier = Modifier.fillMaxSize())
                }
                uiState.error != null && uiState.recentTransactions.isEmpty() -> {
                    DashboardErrorState(
                        error = uiState.error!!,
                        onRetry = { viewModel.loadDashboardData() },
                        modifier = Modifier.fillMaxSize()
                    )
                }
                else -> {
                    DashboardContent(
                        uiState = uiState,
                        listState = listState,
                        isBalanceVisible = isBalanceVisible,
                        onToggleBalanceVisibility = { isBalanceVisible = !isBalanceVisible },
                        onTransactionClick = { viewModel.onTransactionClicked(it) },
                        onBudgetClick = { viewModel.onBudgetClicked(it) },
                        onViewAllTransactions = onNavigateToTransactions,
                        onViewAllBudgets = onNavigateToBudgets,
                        onScanReceipt = onNavigateToScanner,
                        onAddTransaction = onNavigateToAddTransaction,
                        onViewReports = onNavigateToReports,
                        onInsightClick = { viewModel.onInsightClicked(it) },
                        onDismissRecommendation = { viewModel.dismissRecommendation(it) },
                        modifier = modifier.fillMaxSize()
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DashboardTopBar(
    userName: String,
    notificationCount: Int,
    onRefresh: () -> Unit,
    onNotificationsClick: () -> Unit
) {
    TopAppBar(
        title = {
            Column {
                Text(
                    text = getGreeting(),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = userName,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )
            }
        },
        actions = {
            IconButton(onClick = onRefresh) {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = "Refresh"
                )
            }
            BadgedBox(
                badge = {
                    if (notificationCount > 0) {
                        Badge {
                            Text(
                                text = if (notificationCount > 99) "99+" else notificationCount.toString()
                            )
                        }
                    }
                }
            ) {
                IconButton(onClick = onNotificationsClick) {
                    Icon(
                        imageVector = Icons.Outlined.Notifications,
                        contentDescription = "Notifications"
                    )
                }
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    )
}

/**
 * Returns appropriate greeting based on time of day.
 */
private fun getGreeting(): String {
    val hour = java.time.LocalTime.now().hour
    return when {
        hour < 12 -> "Good morning,"
        hour < 17 -> "Good afternoon,"
        else -> "Good evening,"
    }
}

@Composable
private fun DashboardContent(
    uiState: DashboardUiState,
    listState: androidx.compose.foundation.lazy.LazyListState,
    isBalanceVisible: Boolean,
    onToggleBalanceVisibility: () -> Unit,
    onTransactionClick: (String) -> Unit,
    onBudgetClick: (String) -> Unit,
    onViewAllTransactions: () -> Unit,
    onViewAllBudgets: () -> Unit,
    onScanReceipt: () -> Unit,
    onAddTransaction: () -> Unit,
    onViewReports: () -> Unit,
    onInsightClick: (String) -> Unit,
    onDismissRecommendation: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier,
        state = listState,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Balance Summary Card
        item(key = "balance_card") {
            BalanceCard(
                totalBalance = uiState.totalBalance,
                monthlyIncome = uiState.monthlyIncome,
                monthlyExpenses = uiState.monthlyExpenses,
                isBalanceVisible = isBalanceVisible,
                onToggleBalanceVisibility = onToggleBalanceVisibility,
                showTrend = true
            )
        }

        // Quick Actions
        item(key = "quick_actions") {
            QuickActionsSection(
                onAddTransaction = onAddTransaction,
                onViewBudgets = onViewAllBudgets,
                onScanReceipt = onScanReceipt,
                onViewReports = onViewReports
            )
        }

        // AI Insights Section
        if (uiState.showAiInsights && uiState.aiInsights.isNotEmpty()) {
            item(key = "ai_insights_header") {
                SectionHeader(
                    title = "AI Insights",
                    onViewAll = { },
                    showViewAll = false
                )
            }

            item(key = "ai_insights") {
                AiInsightsSection(
                    insights = uiState.aiInsights,
                    onInsightClick = onInsightClick
                )
            }
        }

        // Budget Overview Section
        item(key = "budget_header") {
            SectionHeader(
                title = "Budget Overview",
                onViewAll = onViewAllBudgets,
                showViewAll = uiState.budgets.isNotEmpty()
            )
        }

        item(key = "budget_overview") {
            if (uiState.budgets.isEmpty()) {
                EmptyBudgetCard(onCreateBudget = onViewAllBudgets)
            } else {
                BudgetOverviewRow(
                    budgets = uiState.budgets,
                    onBudgetClick = onBudgetClick
                )
            }
        }

        // Spending Insights Card
        if (uiState.monthlyExpenses > BigDecimal.ZERO) {
            item(key = "spending_insights") {
                SpendingInsightsCard(
                    monthlyExpenses = uiState.monthlyExpenses,
                    monthlyIncome = uiState.monthlyIncome,
                    budgetsNeedingAttention = uiState.budgetsNeedingAttention
                )
            }
        }

        // Recommendations Section
        if (uiState.recommendations.isNotEmpty()) {
            item(key = "recommendations_header") {
                SectionHeader(
                    title = "Recommendations",
                    onViewAll = { },
                    showViewAll = false
                )
            }

            items(
                items = uiState.recommendations.filter { !it.isDismissed }.take(3),
                key = { it.id }
            ) { recommendation ->
                RecommendationCard(
                    recommendation = recommendation,
                    onDismiss = { onDismissRecommendation(recommendation.id) }
                )
            }
        }

        // Recent Transactions Section
        item(key = "transactions_header") {
            SectionHeader(
                title = "Recent Transactions",
                onViewAll = onViewAllTransactions,
                showViewAll = uiState.recentTransactions.isNotEmpty()
            )
        }

        if (uiState.recentTransactions.isEmpty()) {
            item(key = "empty_transactions") {
                EmptyTransactionsCard(onAddTransaction = onAddTransaction)
            }
        } else {
            items(
                items = uiState.recentTransactions.take(5),
                key = { it.id }
            ) { transaction ->
                TransactionListItem(
                    transaction = transaction,
                    onClick = { onTransactionClick(transaction.id) }
                )
            }

            if (uiState.recentTransactions.size > 5) {
                item(key = "view_all_transactions") {
                    TextButton(
                        onClick = onViewAllTransactions,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("View All Transactions")
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(
                            imageVector = Icons.Default.Add,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }
        }

        // Bottom spacing for FAB
        item(key = "bottom_spacer") {
            Spacer(modifier = Modifier.height(80.dp))
        }
    }
}

/**
 * AI Insights section displaying personalized financial insights.
 */
@Composable
private fun AiInsightsSection(
    insights: List<AiInsightUiModel>,
    onInsightClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        insights.take(3).forEach { insight ->
            AiInsightCard(
                insight = insight,
                onClick = { onInsightClick(insight.id) }
            )
        }
    }
}

/**
 * Individual AI insight card.
 */
@Composable
private fun AiInsightCard(
    insight: AiInsightUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val iconColor = when (insight.type) {
        InsightType.SPENDING_PATTERN -> Color(0xFF2196F3)
        InsightType.ANOMALY_DETECTION -> Color(0xFFFF9800)
        InsightType.GOAL_PROGRESS -> Color(0xFF4CAF50)
        InsightType.MARKET_UPDATE -> Color(0xFF9C27B0)
        InsightType.PERSONALIZED_TIP -> Color(0xFF00BCD4)
        InsightType.ACHIEVEMENT -> Color(0xFFFFD700)
        InsightType.WARNING -> Color(0xFFF44336)
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                shape = CircleShape,
                color = iconColor.copy(alpha = 0.1f),
                modifier = Modifier.size(44.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = insight.icon ?: Icons.Outlined.AutoAwesome,
                        contentDescription = null,
                        tint = iconColor,
                        modifier = Modifier.size(24.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = insight.title,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false)
                    )

                    if (!insight.isRead) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = insight.message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )

                if (insight.actionLabel != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = insight.actionLabel,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}

/**
 * Recommendation card with dismiss action.
 */
@Composable
private fun RecommendationCard(
    recommendation: RecommendationUiModel,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val priorityColor = when (recommendation.priority) {
        RecommendationPriority.URGENT -> Color(0xFFF44336)
        RecommendationPriority.HIGH -> Color(0xFFFF9800)
        RecommendationPriority.MEDIUM -> Color(0xFF2196F3)
        RecommendationPriority.LOW -> Color(0xFF4CAF50)
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.Top
        ) {
            // Priority indicator
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(48.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(priorityColor)
            )

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Outlined.Lightbulb,
                        contentDescription = null,
                        tint = priorityColor,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = recommendation.title,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Medium
                    )
                    if (recommendation.isNew) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = MaterialTheme.colorScheme.primary
                        ) {
                            Text(
                                text = "NEW",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onPrimary,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = recommendation.description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                if (recommendation.potentialSavings != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Potential savings: \$${recommendation.potentialSavings}",
                        style = MaterialTheme.typography.labelMedium,
                        color = Color(0xFF4CAF50),
                        fontWeight = FontWeight.SemiBold
                    )
                }

                if (recommendation.actionLabel != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    TextButton(
                        onClick = { },
                        contentPadding = PaddingValues(0.dp)
                    ) {
                        Text(recommendation.actionLabel)
                    }
                }
            }

            IconButton(
                onClick = onDismiss,
                modifier = Modifier.size(32.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "Dismiss",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(18.dp)
                )
            }
        }
    }
}

@Composable
private fun DashboardLoadingState(modifier: Modifier = Modifier) {
    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator()
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Loading your dashboard...",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun DashboardErrorState(
    error: String,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Surface(
            shape = CircleShape,
            color = MaterialTheme.colorScheme.errorContainer,
            modifier = Modifier.size(80.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Outlined.ErrorOutline,
                    contentDescription = null,
                    modifier = Modifier.size(40.dp),
                    tint = MaterialTheme.colorScheme.error
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "Something went wrong",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurface
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = error,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(32.dp))

        Button(onClick = onRetry) {
            Icon(
                imageVector = Icons.Default.Refresh,
                contentDescription = null,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text("Try Again")
        }
    }
}
