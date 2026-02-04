package com.pecunia.ui.screens.transactions

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.pecunia.R
import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionCategory
import com.pecunia.domain.models.TransactionType
import com.pecunia.ui.theme.FinanceColors
import java.math.BigDecimal
import java.text.NumberFormat
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionListScreen(
    transactions: List<Transaction>,
    isLoading: Boolean,
    selectedFilter: TransactionFilter,
    searchQuery: String,
    onSearchQueryChange: (String) -> Unit,
    onFilterChange: (TransactionFilter) -> Unit,
    onTransactionClick: (String) -> Unit,
    onAddTransaction: () -> Unit,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    var showSearchBar by remember { mutableStateOf(false) }
    var showFilterBottomSheet by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            if (showSearchBar) {
                SearchTopBar(
                    query = searchQuery,
                    onQueryChange = onSearchQueryChange,
                    onClose = {
                        showSearchBar = false
                        onSearchQueryChange("")
                    }
                )
            } else {
                TopAppBar(
                    title = { Text(stringResource(R.string.transactions)) },
                    navigationIcon = {
                        IconButton(onClick = onNavigateBack) {
                            Icon(Icons.Default.ArrowBack, contentDescription = stringResource(R.string.back))
                        }
                    },
                    actions = {
                        IconButton(onClick = { showSearchBar = true }) {
                            Icon(Icons.Default.Search, contentDescription = stringResource(R.string.search))
                        }
                        IconButton(onClick = { showFilterBottomSheet = true }) {
                            Badge(
                                modifier = Modifier.offset(x = 8.dp, y = (-8).dp),
                                containerColor = if (selectedFilter != TransactionFilter.All)
                                    MaterialTheme.colorScheme.primary
                                else
                                    Color.Transparent
                            ) {
                                if (selectedFilter != TransactionFilter.All) {
                                    Text("1")
                                }
                            }
                            Icon(Icons.Default.FilterList, contentDescription = stringResource(R.string.filter))
                        }
                    }
                )
            }
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onAddTransaction,
                containerColor = MaterialTheme.colorScheme.primary
            ) {
                Icon(Icons.Default.Add, contentDescription = stringResource(R.string.add_transaction))
            }
        }
    ) { paddingValues ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Filter Chips
            FilterChipsRow(
                selectedFilter = selectedFilter,
                onFilterChange = onFilterChange
            )

            // Transaction Summary
            TransactionSummaryCard(
                transactions = transactions,
                modifier = Modifier.padding(horizontal = 16.dp)
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Transaction List
            if (isLoading) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            } else if (transactions.isEmpty()) {
                EmptyTransactionsState(
                    onAddTransaction = onAddTransaction
                )
            } else {
                TransactionsList(
                    transactions = transactions,
                    onTransactionClick = onTransactionClick
                )
            }
        }

        // Filter Bottom Sheet
        if (showFilterBottomSheet) {
            FilterBottomSheet(
                currentFilter = selectedFilter,
                onFilterSelected = {
                    onFilterChange(it)
                    showFilterBottomSheet = false
                },
                onDismiss = { showFilterBottomSheet = false }
            )
        }
    }
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
                placeholder = { Text(stringResource(R.string.search_transactions)) },
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
                Icon(Icons.Default.ArrowBack, contentDescription = stringResource(R.string.close))
            }
        },
        actions = {
            if (query.isNotEmpty()) {
                IconButton(onClick = { onQueryChange("") }) {
                    Icon(Icons.Default.Clear, contentDescription = stringResource(R.string.clear))
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
        items(TransactionFilter.values().toList()) { filter ->
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
    transactions: List<Transaction>,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val income = transactions
        .filter { it.type == TransactionType.INCOME }
        .sumOf { it.amount }
    val expenses = transactions
        .filter { it.type == TransactionType.EXPENSE }
        .sumOf { it.amount }

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
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            SummaryItem(
                label = stringResource(R.string.income),
                amount = income,
                color = FinanceColors.Income
            )
            VerticalDivider(
                modifier = Modifier
                    .height(40.dp)
                    .width(1.dp)
            )
            SummaryItem(
                label = stringResource(R.string.expenses),
                amount = expenses,
                color = FinanceColors.Expense
            )
        }
    }
}

@Composable
private fun SummaryItem(
    label: String,
    amount: BigDecimal,
    color: Color
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = currencyFormat.format(amount),
            style = MaterialTheme.typography.titleMedium,
            color = color,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun TransactionsList(
    transactions: List<Transaction>,
    onTransactionClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val groupedTransactions = remember(transactions) {
        transactions.groupBy { it.date }
            .toSortedMap(compareByDescending { it })
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
    ) {
        groupedTransactions.forEach { (date, dateTransactions) ->
            item(key = date.toString()) {
                DateHeader(date = date)
            }

            items(
                items = dateTransactions,
                key = { it.id }
            ) { transaction ->
                TransactionItem(
                    transaction = transaction,
                    onClick = { onTransactionClick(transaction.id) }
                )
            }
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
        today -> stringResource(R.string.today)
        yesterday -> stringResource(R.string.yesterday)
        else -> date.format(formatter)
    }

    Text(
        text = displayText,
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier.padding(vertical = 12.dp)
    )
}

@Composable
private fun TransactionItem(
    transaction: Transaction,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    val (amountColor, amountPrefix) = when (transaction.type) {
        TransactionType.INCOME -> FinanceColors.Income to "+"
        TransactionType.EXPENSE -> FinanceColors.Expense to "-"
        TransactionType.TRANSFER -> FinanceColors.Transfer to ""
    }

    val categoryColor = getCategoryColor(transaction.category)

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
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
            // Category Icon
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(categoryColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = getCategoryIcon(transaction.category),
                    contentDescription = null,
                    tint = categoryColor,
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
                        text = transaction.category.displayName,
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
                if (transaction.syncStatus != com.pecunia.domain.models.SyncStatus.SYNCED) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Icon(
                        imageVector = Icons.Outlined.CloudOff,
                        contentDescription = stringResource(R.string.pending_sync),
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@Composable
private fun EmptyTransactionsState(
    onAddTransaction: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(32.dp),
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
            text = stringResource(R.string.no_transactions),
            style = MaterialTheme.typography.titleLarge
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.no_transactions_description),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(24.dp))
        Button(onClick = onAddTransaction) {
            Icon(Icons.Default.Add, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text(stringResource(R.string.add_transaction))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FilterBottomSheet(
    currentFilter: TransactionFilter,
    onFilterSelected: (TransactionFilter) -> Unit,
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
            Text(
                text = stringResource(R.string.filter_by),
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.padding(bottom = 16.dp)
            )

            TransactionFilter.values().forEach { filter ->
                ListItem(
                    headlineContent = { Text(filter.displayName) },
                    leadingContent = {
                        RadioButton(
                            selected = currentFilter == filter,
                            onClick = { onFilterSelected(filter) }
                        )
                    },
                    modifier = Modifier.clickable { onFilterSelected(filter) }
                )
            }

            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

/**
 * Filter options for transactions.
 */
enum class TransactionFilter(val displayName: String) {
    All("All"),
    Income("Income"),
    Expenses("Expenses"),
    Transfers("Transfers"),
    ThisWeek("This Week"),
    ThisMonth("This Month")
}

/**
 * Get the icon for a transaction category.
 */
private fun getCategoryIcon(category: TransactionCategory): androidx.compose.ui.graphics.vector.ImageVector {
    return when (category) {
        TransactionCategory.SALARY -> Icons.Default.Work
        TransactionCategory.FREELANCE -> Icons.Default.Computer
        TransactionCategory.INVESTMENT -> Icons.Default.TrendingUp
        TransactionCategory.GIFT -> Icons.Default.CardGiftcard
        TransactionCategory.OTHER_INCOME -> Icons.Default.AttachMoney
        TransactionCategory.FOOD -> Icons.Default.Restaurant
        TransactionCategory.GROCERIES -> Icons.Default.ShoppingCart
        TransactionCategory.TRANSPORTATION -> Icons.Default.DirectionsCar
        TransactionCategory.UTILITIES -> Icons.Default.Power
        TransactionCategory.ENTERTAINMENT -> Icons.Default.Movie
        TransactionCategory.SHOPPING -> Icons.Default.ShoppingBag
        TransactionCategory.HEALTHCARE -> Icons.Default.LocalHospital
        TransactionCategory.EDUCATION -> Icons.Default.School
        TransactionCategory.TRAVEL -> Icons.Default.Flight
        TransactionCategory.HOUSING -> Icons.Default.Home
        TransactionCategory.INSURANCE -> Icons.Default.Security
        TransactionCategory.SUBSCRIPTIONS -> Icons.Default.Subscriptions
        TransactionCategory.OTHER_EXPENSE -> Icons.Default.Receipt
    }
}

/**
 * Get the color for a transaction category.
 */
private fun getCategoryColor(category: TransactionCategory): Color {
    return when (category) {
        TransactionCategory.FOOD -> FinanceColors.CategoryFood
        TransactionCategory.GROCERIES -> FinanceColors.CategoryGroceries
        TransactionCategory.TRANSPORTATION -> FinanceColors.CategoryTransportation
        TransactionCategory.UTILITIES -> FinanceColors.CategoryUtilities
        TransactionCategory.ENTERTAINMENT -> FinanceColors.CategoryEntertainment
        TransactionCategory.SHOPPING -> FinanceColors.CategoryShopping
        TransactionCategory.HEALTHCARE -> FinanceColors.CategoryHealthcare
        TransactionCategory.EDUCATION -> FinanceColors.CategoryEducation
        TransactionCategory.TRAVEL -> FinanceColors.CategoryTravel
        TransactionCategory.HOUSING -> FinanceColors.CategoryHousing
        else -> FinanceColors.Income
    }
}
