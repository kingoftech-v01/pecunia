package com.pecunia.ui.screens.transactions

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
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
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
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
 * Transaction list screen with filtering, search, and grouping by date.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionListScreen(
    viewModel: TransactionsViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onNavigateToTransactionDetail: (String) -> Unit,
    onNavigateToAddTransaction: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val pullToRefreshState = rememberPullToRefreshState()

    var showSearchBar by remember { mutableStateOf(false) }
    var showFilterSheet by remember { mutableStateOf(false) }
    var showSortMenu by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is TransactionsEvent.NavigateToDetail -> {
                    onNavigateToTransactionDetail(event.transactionId)
                }
                is TransactionsEvent.TransactionDeleted -> {
                    // Show snackbar
                }
                is TransactionsEvent.ShowError -> {
                    // Show error snackbar
                }
            }
        }
    }

    Scaffold(
        topBar = {
            AnimatedVisibility(
                visible = !showSearchBar,
                enter = fadeIn(),
                exit = fadeOut()
            ) {
                TransactionListTopBar(
                    selectedFilter = uiState.selectedFilter,
                    onNavigateBack = onNavigateBack,
                    onSearchClick = { showSearchBar = true },
                    onFilterClick = { showFilterSheet = true },
                    onSortClick = { showSortMenu = true }
                )
            }

            AnimatedVisibility(
                visible = showSearchBar,
                enter = slideInVertically() + fadeIn(),
                exit = slideOutVertically() + fadeOut()
            ) {
                SearchTopBar(
                    query = uiState.searchQuery,
                    onQueryChange = { viewModel.onSearchQueryChanged(it) },
                    onClose = {
                        showSearchBar = false
                        viewModel.onSearchQueryChanged("")
                    }
                )
            }
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onNavigateToAddTransaction,
                containerColor = MaterialTheme.colorScheme.primary
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Transaction")
            }
        }
    ) { paddingValues ->
        PullToRefreshBox(
            isRefreshing = uiState.isRefreshing,
            onRefresh = { viewModel.refreshTransactions() },
            state = pullToRefreshState,
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            Column(modifier = modifier.fillMaxSize()) {
                // Filter Chips Row
                FilterChipsRow(
                    selectedFilter = uiState.selectedFilter,
                    onFilterChange = { viewModel.onFilterChanged(it) }
                )

                // Transaction Summary
                TransactionSummaryCard(
                    totalIncome = uiState.totalIncome,
                    totalExpenses = uiState.totalExpenses,
                    transactionCount = uiState.filteredTransactions.size,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Transaction List
                when {
                    uiState.isLoading -> {
                        LoadingState(modifier = Modifier.fillMaxSize())
                    }
                    uiState.error != null -> {
                        ErrorState(
                            error = uiState.error!!,
                            onRetry = { viewModel.loadTransactions() },
                            modifier = Modifier.fillMaxSize()
                        )
                    }
                    uiState.filteredTransactions.isEmpty() -> {
                        EmptyState(
                            hasFilters = uiState.selectedFilter != TransactionFilter.ALL || uiState.searchQuery.isNotEmpty(),
                            onClearFilters = { viewModel.clearFilters() },
                            onAddTransaction = onNavigateToAddTransaction,
                            modifier = Modifier.fillMaxSize()
                        )
                    }
                    else -> {
                        TransactionsList(
                            groupedTransactions = uiState.groupedTransactions,
                            onTransactionClick = { viewModel.onTransactionClicked(it) },
                            modifier = Modifier.fillMaxSize()
                        )
                    }
                }
            }
        }

        // Sort Menu
        DropdownMenu(
            expanded = showSortMenu,
            onDismissRequest = { showSortMenu = false }
        ) {
            TransactionSortOption.entries.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.displayName) },
                    onClick = {
                        viewModel.onSortOptionChanged(option)
                        showSortMenu = false
                    },
                    leadingIcon = {
                        if (uiState.sortOption == option) {
                            Icon(Icons.Default.Check, contentDescription = null)
                        }
                    }
                )
            }
        }

        // Filter Bottom Sheet
        if (showFilterSheet) {
            FilterBottomSheet(
                currentFilter = uiState.selectedFilter,
                dateRange = uiState.dateRange,
                selectedCategories = uiState.selectedCategories,
                amountRange = uiState.amountRange,
                onFilterSelected = { viewModel.onFilterChanged(it) },
                onDateRangeChanged = { viewModel.onDateRangeChanged(it) },
                onCategoriesChanged = { viewModel.onCategoriesChanged(it) },
                onAmountRangeChanged = { viewModel.onAmountRangeChanged(it) },
                onApply = { showFilterSheet = false },
                onClear = {
                    viewModel.clearFilters()
                    showFilterSheet = false
                },
                onDismiss = { showFilterSheet = false }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TransactionListTopBar(
    selectedFilter: TransactionFilter,
    onNavigateBack: () -> Unit,
    onSearchClick: () -> Unit,
    onFilterClick: () -> Unit,
    onSortClick: () -> Unit
) {
    val hasActiveFilter = selectedFilter != TransactionFilter.ALL

    TopAppBar(
        title = { Text("Transactions") },
        navigationIcon = {
            IconButton(onClick = onNavigateBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back")
            }
        },
        actions = {
            IconButton(onClick = onSearchClick) {
                Icon(Icons.Default.Search, contentDescription = "Search")
            }
            IconButton(onClick = onSortClick) {
                Icon(Icons.Default.Sort, contentDescription = "Sort")
            }
            BadgedBox(
                badge = {
                    if (hasActiveFilter) {
                        Badge { Text("1") }
                    }
                }
            ) {
                IconButton(onClick = onFilterClick) {
                    Icon(Icons.Default.FilterList, contentDescription = "Filter")
                }
            }
        }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SearchTopBar(
    query: String,
    onQueryChange: (String) -> Unit,
    onClose: () -> Unit
) {
    TopAppBar(
        title = {
            TextField(
                value = query,
                onValueChange = onQueryChange,
                placeholder = { Text("Search transactions...") },
                singleLine = true,
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent
                ),
                modifier = Modifier.fillMaxWidth()
            )
        },
        navigationIcon = {
            IconButton(onClick = onClose) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Close")
            }
        },
        actions = {
            if (query.isNotEmpty()) {
                IconButton(onClick = { onQueryChange("") }) {
                    Icon(Icons.Default.Clear, contentDescription = "Clear")
                }
            }
        }
    )
}

@Composable
private fun FilterChipsRow(
    selectedFilter: TransactionFilter,
    onFilterChange: (TransactionFilter) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyRow(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(TransactionFilter.entries) { filter ->
            FilterChip(
                selected = selectedFilter == filter,
                onClick = { onFilterChange(filter) },
                label = { Text(filter.displayName) },
                leadingIcon = if (selectedFilter == filter) {
                    {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                } else null
            )
        }
    }
}

@Composable
private fun TransactionSummaryCard(
    totalIncome: BigDecimal,
    totalExpenses: BigDecimal,
    transactionCount: Int,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            SummaryItem(
                label = "Income",
                amount = currencyFormat.format(totalIncome),
                color = Color(0xFF4CAF50)
            )
            VerticalDivider(
                modifier = Modifier.height(40.dp),
                thickness = 1.dp,
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
            )
            SummaryItem(
                label = "Expenses",
                amount = currencyFormat.format(totalExpenses),
                color = Color(0xFFF44336)
            )
            VerticalDivider(
                modifier = Modifier.height(40.dp),
                thickness = 1.dp,
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
            )
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "Count",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "$transactionCount",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}

@Composable
private fun SummaryItem(
    label: String,
    amount: String,
    color: Color
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = amount,
            style = MaterialTheme.typography.titleMedium,
            color = color,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun TransactionsList(
    groupedTransactions: Map<LocalDate, List<TransactionItemUiModel>>,
    onTransactionClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
    ) {
        groupedTransactions.forEach { (date, transactions) ->
            item(key = "header_$date") {
                DateHeader(date = date)
            }

            items(
                items = transactions,
                key = { it.id }
            ) { transaction ->
                TransactionItem(
                    transaction = transaction,
                    onClick = { onTransactionClick(transaction.id) }
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
private fun DateHeader(
    date: LocalDate,
    modifier: Modifier = Modifier
) {
    val formatter = remember { DateTimeFormatter.ofPattern("EEEE, MMM d") }
    val today = LocalDate.now()
    val yesterday = today.minusDays(1)

    val displayText = when (date) {
        today -> "Today"
        yesterday -> "Yesterday"
        else -> date.format(formatter)
    }

    Text(
        text = displayText,
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        fontWeight = FontWeight.Medium,
        modifier = modifier.padding(vertical = 12.dp)
    )
}

@Composable
private fun TransactionItem(
    transaction: TransactionItemUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val (amountColor, amountPrefix) = when (transaction.type) {
        TransactionTypeFilter.INCOME -> Color(0xFF4CAF50) to "+"
        TransactionTypeFilter.EXPENSE -> Color(0xFFF44336) to "-"
        TransactionTypeFilter.TRANSFER -> MaterialTheme.colorScheme.onSurface to ""
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Category Icon
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(transaction.categoryColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = transaction.categoryIcon,
                    contentDescription = null,
                    tint = transaction.categoryColor,
                    modifier = Modifier.size(24.dp)
                )
            }

            Spacer(modifier = Modifier.width(16.dp))

            // Transaction Details
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = transaction.description,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = transaction.categoryName,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    transaction.merchant?.let { merchant ->
                        Text(
                            text = " - $merchant",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }

            // Amount
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "$amountPrefix${currencyFormat.format(transaction.amount)}",
                    style = MaterialTheme.typography.titleSmall,
                    color = amountColor,
                    fontWeight = FontWeight.SemiBold
                )
                if (!transaction.isSynced) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Icon(
                        imageVector = Icons.Outlined.CloudOff,
                        contentDescription = "Pending sync",
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FilterBottomSheet(
    currentFilter: TransactionFilter,
    dateRange: DateRange?,
    selectedCategories: Set<String>,
    amountRange: AmountRange?,
    onFilterSelected: (TransactionFilter) -> Unit,
    onDateRangeChanged: (DateRange?) -> Unit,
    onCategoriesChanged: (Set<String>) -> Unit,
    onAmountRangeChanged: (AmountRange?) -> Unit,
    onApply: () -> Unit,
    onClear: () -> Unit,
    onDismiss: () -> Unit
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Filter Transactions",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )
                TextButton(onClick = onClear) {
                    Text("Clear All")
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Transaction Type Filter
            Text(
                text = "Transaction Type",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TransactionFilter.entries.take(4).forEach { filter ->
                    FilterChip(
                        selected = currentFilter == filter,
                        onClick = { onFilterSelected(filter) },
                        label = { Text(filter.displayName) },
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Date Range Filter
            Text(
                text = "Date Range",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                listOf(
                    "This Week" to DateRange.THIS_WEEK,
                    "This Month" to DateRange.THIS_MONTH,
                    "Last 30 Days" to DateRange.LAST_30_DAYS
                ).forEach { (label, range) ->
                    FilterChip(
                        selected = dateRange == range,
                        onClick = { onDateRangeChanged(if (dateRange == range) null else range) },
                        label = { Text(label) }
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Apply Button
            Button(
                onClick = onApply,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Apply Filters")
            }

            Spacer(modifier = Modifier.height(16.dp))
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
            text = "Failed to load transactions",
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

@Composable
private fun EmptyState(
    hasFilters: Boolean,
    onClearFilters: () -> Unit,
    onAddTransaction: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Outlined.Receipt,
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = if (hasFilters) "No matching transactions" else "No transactions yet",
            style = MaterialTheme.typography.titleLarge
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = if (hasFilters)
                "Try adjusting your filters"
            else
                "Add your first transaction to get started",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(24.dp))
        if (hasFilters) {
            OutlinedButton(onClick = onClearFilters) {
                Text("Clear Filters")
            }
        } else {
            Button(onClick = onAddTransaction) {
                Icon(Icons.Default.Add, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Add Transaction")
            }
        }
    }
}

/**
 * Filter options for transactions.
 */
enum class TransactionFilter(val displayName: String) {
    ALL("All"),
    INCOME("Income"),
    EXPENSES("Expenses"),
    TRANSFERS("Transfers"),
    THIS_WEEK("This Week"),
    THIS_MONTH("This Month")
}

/**
 * Transaction type filter enum.
 */
enum class TransactionTypeFilter {
    INCOME, EXPENSE, TRANSFER
}

/**
 * Sort options for transactions.
 */
enum class TransactionSortOption(val displayName: String) {
    DATE_DESC("Newest First"),
    DATE_ASC("Oldest First"),
    AMOUNT_DESC("Highest Amount"),
    AMOUNT_ASC("Lowest Amount"),
    CATEGORY("Category")
}

/**
 * Date range options for filtering.
 */
enum class DateRange {
    THIS_WEEK,
    THIS_MONTH,
    LAST_30_DAYS,
    LAST_90_DAYS,
    THIS_YEAR,
    CUSTOM
}

/**
 * Amount range for filtering.
 */
data class AmountRange(
    val min: BigDecimal? = null,
    val max: BigDecimal? = null
)

/**
 * UI model for transaction list items.
 */
data class TransactionItemUiModel(
    val id: String,
    val description: String,
    val amount: BigDecimal,
    val type: TransactionTypeFilter,
    val categoryName: String,
    val categoryIcon: ImageVector,
    val categoryColor: Color,
    val merchant: String?,
    val date: LocalDate,
    val isSynced: Boolean,
    val isRecurring: Boolean = false
)
