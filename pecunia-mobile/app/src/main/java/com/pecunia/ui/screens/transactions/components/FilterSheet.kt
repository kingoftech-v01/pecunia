package com.pecunia.ui.screens.transactions.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.pecunia.domain.model.Category
import com.pecunia.domain.model.TransactionType
import com.pecunia.ui.screens.transactions.DateRange
import com.pecunia.ui.screens.transactions.TransactionFilters
import com.pecunia.ui.screens.transactions.TransactionSortBy
import java.time.LocalDate
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FilterBottomSheet(
    filters: TransactionFilters,
    categories: List<Category>,
    onFiltersChanged: (TransactionFilters) -> Unit,
    onClearFilters: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    var localFilters by remember(filters) { mutableStateOf(filters) }
    var showDateRangePicker by remember { mutableStateOf(false) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        modifier = modifier,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 32.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Filters",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )

                TextButton(onClick = {
                    localFilters = TransactionFilters()
                    onClearFilters()
                }) {
                    Text("Clear All")
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Transaction Type Filter
            Text(
                text = "Transaction Type",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TransactionType.values().forEach { type ->
                    val isSelected = localFilters.types.contains(type)
                    FilterChip(
                        selected = isSelected,
                        onClick = {
                            val newTypes = if (isSelected) {
                                localFilters.types - type
                            } else {
                                localFilters.types + type
                            }
                            localFilters = localFilters.copy(types = newTypes)
                        },
                        label = { Text(type.name.lowercase().replaceFirstChar { it.uppercase() }) },
                        leadingIcon = if (isSelected) {
                            { Icon(Icons.Default.Check, contentDescription = null, Modifier.size(18.dp)) }
                        } else null,
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = when (type) {
                                TransactionType.INCOME -> MaterialTheme.colorScheme.primaryContainer
                                TransactionType.EXPENSE -> MaterialTheme.colorScheme.errorContainer
                                TransactionType.TRANSFER -> MaterialTheme.colorScheme.tertiaryContainer
                            }
                        )
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Date Range Filter
            Text(
                text = "Date Range",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(12.dp))

            DateRangeSelector(
                selectedRange = localFilters.dateRange,
                onRangeSelected = { range ->
                    localFilters = localFilters.copy(dateRange = range)
                },
                onCustomRangeClick = { showDateRangePicker = true }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Amount Range Filter
            Text(
                text = "Amount Range",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(12.dp))

            AmountRangeSelector(
                minAmount = localFilters.minAmount,
                maxAmount = localFilters.maxAmount,
                onMinAmountChanged = { amount ->
                    localFilters = localFilters.copy(minAmount = amount)
                },
                onMaxAmountChanged = { amount ->
                    localFilters = localFilters.copy(maxAmount = amount)
                }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Category Filter
            Text(
                text = "Categories",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(12.dp))

            CategoryFilterGrid(
                categories = categories,
                selectedCategoryIds = localFilters.categoryIds,
                onCategoryToggle = { categoryId ->
                    val newCategories = if (localFilters.categoryIds.contains(categoryId)) {
                        localFilters.categoryIds - categoryId
                    } else {
                        localFilters.categoryIds + categoryId
                    }
                    localFilters = localFilters.copy(categoryIds = newCategories)
                }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Sort By
            Text(
                text = "Sort By",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(12.dp))

            SortBySelector(
                selectedSortBy = localFilters.sortBy,
                onSortBySelected = { sortBy ->
                    localFilters = localFilters.copy(sortBy = sortBy)
                }
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Apply Button
            Button(
                onClick = {
                    onFiltersChanged(localFilters)
                    onDismiss()
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text(
                    text = "Apply Filters",
                    modifier = Modifier.padding(vertical = 8.dp)
                )
            }
        }
    }

    if (showDateRangePicker) {
        DateRangePickerDialog(
            initialRange = localFilters.dateRange,
            onRangeSelected = { range ->
                localFilters = localFilters.copy(dateRange = range)
                showDateRangePicker = false
            },
            onDismiss = { showDateRangePicker = false }
        )
    }
}

@Composable
private fun DateRangeSelector(
    selectedRange: DateRange?,
    onRangeSelected: (DateRange?) -> Unit,
    onCustomRangeClick: () -> Unit
) {
    val today = LocalDate.now()
    val presetRanges = listOf(
        "Today" to DateRange(today, today),
        "This Week" to DateRange(today.minusDays(today.dayOfWeek.value.toLong() - 1), today),
        "This Month" to DateRange(today.withDayOfMonth(1), today),
        "Last 30 Days" to DateRange(today.minusDays(30), today),
        "Last 3 Months" to DateRange(today.minusMonths(3), today),
        "This Year" to DateRange(today.withDayOfYear(1), today)
    )

    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(presetRanges) { (label, range) ->
            val isSelected = selectedRange == range
            FilterChip(
                selected = isSelected,
                onClick = {
                    onRangeSelected(if (isSelected) null else range)
                },
                label = { Text(label) },
                leadingIcon = if (isSelected) {
                    { Icon(Icons.Default.Check, contentDescription = null, Modifier.size(18.dp)) }
                } else null
            )
        }

        item {
            FilterChip(
                selected = selectedRange != null && presetRanges.none { it.second == selectedRange },
                onClick = onCustomRangeClick,
                label = { Text("Custom") },
                leadingIcon = { Icon(Icons.Outlined.DateRange, contentDescription = null, Modifier.size(18.dp)) }
            )
        }
    }
}

@Composable
private fun AmountRangeSelector(
    minAmount: Double?,
    maxAmount: Double?,
    onMinAmountChanged: (Double?) -> Unit,
    onMaxAmountChanged: (Double?) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        OutlinedTextField(
            value = minAmount?.toString() ?: "",
            onValueChange = { value ->
                onMinAmountChanged(value.toDoubleOrNull())
            },
            label = { Text("Min") },
            leadingIcon = { Text("$", style = MaterialTheme.typography.bodyLarge) },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.weight(1f),
            shape = RoundedCornerShape(12.dp),
            singleLine = true
        )

        OutlinedTextField(
            value = maxAmount?.toString() ?: "",
            onValueChange = { value ->
                onMaxAmountChanged(value.toDoubleOrNull())
            },
            label = { Text("Max") },
            leadingIcon = { Text("$", style = MaterialTheme.typography.bodyLarge) },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.weight(1f),
            shape = RoundedCornerShape(12.dp),
            singleLine = true
        )
    }
}

@Composable
private fun CategoryFilterGrid(
    categories: List<Category>,
    selectedCategoryIds: Set<String>,
    onCategoryToggle: (String) -> Unit
) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(3),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.height(200.dp)
    ) {
        items(categories) { category ->
            val isSelected = selectedCategoryIds.contains(category.id)
            CategoryFilterItem(
                category = category,
                isSelected = isSelected,
                onClick = { onCategoryToggle(category.id) }
            )
        }
    }
}

@Composable
private fun CategoryFilterItem(
    category: Category,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    val backgroundColor = if (isSelected) {
        MaterialTheme.colorScheme.primaryContainer
    } else {
        MaterialTheme.colorScheme.surface
    }

    val borderColor = if (isSelected) {
        MaterialTheme.colorScheme.primary
    } else {
        MaterialTheme.colorScheme.outline
    }

    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(backgroundColor)
            .border(1.dp, borderColor, RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .clip(CircleShape)
                .background(Color(android.graphics.Color.parseColor(category.color))),
            contentAlignment = Alignment.Center
        ) {
            if (isSelected) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(18.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = category.name,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 1
        )
    }
}

@Composable
private fun SortBySelector(
    selectedSortBy: TransactionSortBy,
    onSortBySelected: (TransactionSortBy) -> Unit
) {
    val sortOptions = listOf(
        TransactionSortBy.DATE_DESC to "Newest First",
        TransactionSortBy.DATE_ASC to "Oldest First",
        TransactionSortBy.AMOUNT_DESC to "Highest Amount",
        TransactionSortBy.AMOUNT_ASC to "Lowest Amount",
        TransactionSortBy.CATEGORY to "By Category"
    )

    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        sortOptions.forEach { (sortBy, label) ->
            val isSelected = selectedSortBy == sortBy

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .clickable { onSortBySelected(sortBy) }
                    .padding(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                RadioButton(
                    selected = isSelected,
                    onClick = { onSortBySelected(sortBy) }
                )

                Spacer(modifier = Modifier.width(8.dp))

                Text(
                    text = label,
                    style = MaterialTheme.typography.bodyLarge
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DateRangePickerDialog(
    initialRange: DateRange?,
    onRangeSelected: (DateRange) -> Unit,
    onDismiss: () -> Unit
) {
    val dateRangePickerState = rememberDateRangePickerState(
        initialSelectedStartDateMillis = initialRange?.startDate?.toEpochDay()?.times(86400000),
        initialSelectedEndDateMillis = initialRange?.endDate?.toEpochDay()?.times(86400000)
    )

    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(
                onClick = {
                    val startMillis = dateRangePickerState.selectedStartDateMillis
                    val endMillis = dateRangePickerState.selectedEndDateMillis

                    if (startMillis != null && endMillis != null) {
                        val startDate = LocalDate.ofEpochDay(startMillis / 86400000)
                        val endDate = LocalDate.ofEpochDay(endMillis / 86400000)
                        onRangeSelected(DateRange(startDate, endDate))
                    }
                }
            ) {
                Text("Confirm")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    ) {
        DateRangePicker(
            state = dateRangePickerState,
            modifier = Modifier.height(500.dp)
        )
    }
}

@Composable
fun QuickFilterChips(
    selectedFilters: TransactionFilters,
    onTypeToggle: (TransactionType) -> Unit,
    onShowAllFilters: () -> Unit,
    modifier: Modifier = Modifier
) {
    val dateFormatter = remember { DateTimeFormatter.ofPattern("MMM d") }
    val hasActiveFilters = selectedFilters.types.isNotEmpty() ||
            selectedFilters.categoryIds.isNotEmpty() ||
            selectedFilters.dateRange != null ||
            selectedFilters.minAmount != null ||
            selectedFilters.maxAmount != null

    LazyRow(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(horizontal = 16.dp)
    ) {
        // Filter button
        item {
            FilterChip(
                selected = hasActiveFilters,
                onClick = onShowAllFilters,
                label = { Text("Filters") },
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Outlined.FilterList,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                },
                trailingIcon = if (hasActiveFilters) {
                    {
                        val activeCount = listOfNotNull(
                            selectedFilters.types.takeIf { it.isNotEmpty() },
                            selectedFilters.categoryIds.takeIf { it.isNotEmpty() },
                            selectedFilters.dateRange,
                            selectedFilters.minAmount,
                            selectedFilters.maxAmount
                        ).size

                        Badge { Text(activeCount.toString()) }
                    }
                } else null
            )
        }

        // Quick type filters
        items(TransactionType.values()) { type ->
            val isSelected = selectedFilters.types.contains(type)
            FilterChip(
                selected = isSelected,
                onClick = { onTypeToggle(type) },
                label = { Text(type.name.lowercase().replaceFirstChar { it.uppercase() }) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = when (type) {
                        TransactionType.INCOME -> MaterialTheme.colorScheme.primaryContainer
                        TransactionType.EXPENSE -> MaterialTheme.colorScheme.errorContainer
                        TransactionType.TRANSFER -> MaterialTheme.colorScheme.tertiaryContainer
                    }
                )
            )
        }

        // Date range chip if selected
        if (selectedFilters.dateRange != null) {
            item {
                val range = selectedFilters.dateRange
                InputChip(
                    selected = true,
                    onClick = onShowAllFilters,
                    label = {
                        Text("${range.startDate.format(dateFormatter)} - ${range.endDate.format(dateFormatter)}")
                    },
                    trailingIcon = {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "Clear",
                            modifier = Modifier.size(18.dp)
                        )
                    }
                )
            }
        }
    }
}
