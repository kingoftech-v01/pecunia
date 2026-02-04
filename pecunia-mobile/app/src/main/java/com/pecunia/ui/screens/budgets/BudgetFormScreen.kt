package com.pecunia.ui.screens.budgets

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Category
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import java.math.BigDecimal
import java.text.NumberFormat
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Budget Form Screen for creating and editing budgets.
 * Supports name, period type, date range, category allocation, and alert thresholds.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BudgetFormScreen(
    budgetId: String? = null,
    viewModel: BudgetFormViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(budgetId) {
        if (budgetId != null) {
            viewModel.loadBudget(budgetId)
        } else {
            viewModel.initNewBudget()
        }
    }

    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is BudgetFormEvent.SaveSuccess -> {
                    onNavigateBack()
                }
                is BudgetFormEvent.ShowError -> {
                    snackbarHostState.showSnackbar(event.message)
                }
                is BudgetFormEvent.ValidationError -> {
                    snackbarHostState.showSnackbar(event.message)
                }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(if (uiState.isEditMode) "Edit Budget" else "New Budget")
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    TextButton(
                        onClick = { viewModel.saveBudget() },
                        enabled = !uiState.isSaving && uiState.isValid
                    ) {
                        if (uiState.isSaving) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Text(
                                "Save",
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
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
            BudgetFormContent(
                uiState = uiState,
                onNameChange = viewModel::updateName,
                onAmountChange = viewModel::updateAmount,
                onPeriodTypeChange = viewModel::updatePeriodType,
                onStartDateChange = viewModel::updateStartDate,
                onEndDateChange = viewModel::updateEndDate,
                onAlertThresholdChange = viewModel::updateAlertThreshold,
                onCategoryToggle = viewModel::toggleCategory,
                onCategoryAmountChange = viewModel::updateCategoryAmount,
                modifier = modifier
                    .fillMaxSize()
                    .padding(paddingValues)
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun BudgetFormContent(
    uiState: BudgetFormState,
    onNameChange: (String) -> Unit,
    onAmountChange: (String) -> Unit,
    onPeriodTypeChange: (BudgetPeriodTypeForm) -> Unit,
    onStartDateChange: (LocalDate) -> Unit,
    onEndDateChange: (LocalDate) -> Unit,
    onAlertThresholdChange: (Int, Boolean) -> Unit,
    onCategoryToggle: (String) -> Unit,
    onCategoryAmountChange: (String, String) -> Unit,
    modifier: Modifier = Modifier
) {
    val dateFormatter = remember { DateTimeFormatter.ofPattern("MMM d, yyyy") }
    var showStartDatePicker by remember { mutableStateOf(false) }
    var showEndDatePicker by remember { mutableStateOf(false) }
    var showCategoryDialog by remember { mutableStateOf(false) }
    var periodDropdownExpanded by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Basic Information Section
        item(key = "basic_info") {
            SectionCard(title = "Basic Information") {
                // Budget Name
                OutlinedTextField(
                    value = uiState.name,
                    onValueChange = onNameChange,
                    label = { Text("Budget Name") },
                    placeholder = { Text("e.g., Monthly Groceries") },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    isError = uiState.errors.containsKey("name"),
                    supportingText = uiState.errors["name"]?.let {
                        { Text(it, color = MaterialTheme.colorScheme.error) }
                    },
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Budget Amount
                OutlinedTextField(
                    value = uiState.amount,
                    onValueChange = { value ->
                        // Only allow numbers and decimal point
                        if (value.isEmpty() || value.matches(Regex("^\\d*\\.?\\d{0,2}$"))) {
                            onAmountChange(value)
                        }
                    },
                    label = { Text("Budget Amount") },
                    placeholder = { Text("0.00") },
                    leadingIcon = { Text("$", style = MaterialTheme.typography.titleMedium) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    isError = uiState.errors.containsKey("amount"),
                    supportingText = uiState.errors["amount"]?.let {
                        { Text(it, color = MaterialTheme.colorScheme.error) }
                    },
                    singleLine = true
                )
            }
        }

        // Period Section
        item(key = "period") {
            SectionCard(title = "Budget Period") {
                // Period Type Selector
                Text(
                    text = "Period Type",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(8.dp))

                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    BudgetPeriodTypeForm.entries.forEach { periodType ->
                        FilterChip(
                            selected = uiState.periodType == periodType,
                            onClick = { onPeriodTypeChange(periodType) },
                            label = { Text(periodType.displayName) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Date Range
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // Start Date
                    DateField(
                        label = "Start Date",
                        date = uiState.startDate,
                        dateFormatter = dateFormatter,
                        onClick = { showStartDatePicker = true },
                        modifier = Modifier.weight(1f)
                    )

                    // End Date
                    DateField(
                        label = "End Date",
                        date = uiState.endDate,
                        dateFormatter = dateFormatter,
                        onClick = { showEndDatePicker = true },
                        modifier = Modifier.weight(1f),
                        enabled = uiState.periodType == BudgetPeriodTypeForm.CUSTOM
                    )
                }

                // Period summary
                val periodDays = java.time.temporal.ChronoUnit.DAYS.between(
                    uiState.startDate,
                    uiState.endDate
                )
                Text(
                    text = "$periodDays days",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
        }

        // Category Allocation Section
        item(key = "categories") {
            SectionCard(title = "Category Allocation") {
                Text(
                    text = "Allocate your budget to specific categories (optional)",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Selected Categories
                if (uiState.categoryAllocations.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        uiState.categoryAllocations.forEach { allocation ->
                            CategoryAllocationItem(
                                allocation = allocation,
                                onAmountChange = { onCategoryAmountChange(allocation.categoryId, it) },
                                onRemove = { onCategoryToggle(allocation.categoryId) }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Allocation Summary
                    AllocationSummary(
                        totalBudget = uiState.amount.toDoubleOrNull() ?: 0.0,
                        allocated = uiState.categoryAllocations.sumOf {
                            it.amount.toDoubleOrNull() ?: 0.0
                        }
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Add Category Button
                OutlinedButton(
                    onClick = { showCategoryDialog = true },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(
                        Icons.Default.Add,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Add Category")
                }
            }
        }

        // Alert Thresholds Section
        item(key = "alerts") {
            SectionCard(title = "Alert Thresholds") {
                Text(
                    text = "Get notified when you reach these spending levels",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(12.dp))

                AlertThresholdItem(
                    percentage = 50,
                    isEnabled = uiState.alertAt50,
                    onToggle = { onAlertThresholdChange(50, it) }
                )

                AlertThresholdItem(
                    percentage = 75,
                    isEnabled = uiState.alertAt75,
                    onToggle = { onAlertThresholdChange(75, it) }
                )

                AlertThresholdItem(
                    percentage = 90,
                    isEnabled = uiState.alertAt90,
                    onToggle = { onAlertThresholdChange(90, it) }
                )

                AlertThresholdItem(
                    percentage = 100,
                    isEnabled = uiState.alertAt100,
                    onToggle = { onAlertThresholdChange(100, it) },
                    label = "Over Budget"
                )
            }
        }

        // Bottom spacing
        item(key = "bottom_spacer") {
            Spacer(modifier = Modifier.height(32.dp))
        }
    }

    // Date Pickers
    if (showStartDatePicker) {
        DatePickerDialogWrapper(
            initialDate = uiState.startDate,
            onDateSelected = {
                onStartDateChange(it)
                showStartDatePicker = false
            },
            onDismiss = { showStartDatePicker = false }
        )
    }

    if (showEndDatePicker) {
        DatePickerDialogWrapper(
            initialDate = uiState.endDate,
            onDateSelected = {
                onEndDateChange(it)
                showEndDatePicker = false
            },
            onDismiss = { showEndDatePicker = false }
        )
    }

    // Category Selection Dialog
    if (showCategoryDialog) {
        CategorySelectionDialog(
            categories = uiState.availableCategories,
            selectedCategoryIds = uiState.categoryAllocations.map { it.categoryId },
            onCategoryToggle = onCategoryToggle,
            onDismiss = { showCategoryDialog = false }
        )
    }
}

@Composable
private fun SectionCard(
    title: String,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
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
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(16.dp))
            content()
        }
    }
}

@Composable
private fun DateField(
    label: String,
    date: LocalDate,
    dateFormatter: DateTimeFormatter,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true
) {
    Column(modifier = modifier) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(8.dp))

        Surface(
            onClick = if (enabled) onClick else ({}),
            shape = RoundedCornerShape(12.dp),
            color = if (enabled) {
                MaterialTheme.colorScheme.surfaceVariant
            } else {
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            }
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = date.format(dateFormatter),
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (enabled) {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
                    }
                )
                Icon(
                    Icons.Default.CalendarToday,
                    contentDescription = "Select date",
                    modifier = Modifier.size(18.dp),
                    tint = if (enabled) {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
                    }
                )
            }
        }
    }
}

@Composable
private fun CategoryAllocationItem(
    allocation: CategoryAllocationForm,
    onAmountChange: (String) -> Unit,
    onRemove: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Category Info
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.Category,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                        tint = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

                Text(
                    text = allocation.categoryName,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
            }

            // Amount Input
            OutlinedTextField(
                value = allocation.amount,
                onValueChange = { value ->
                    if (value.isEmpty() || value.matches(Regex("^\\d*\\.?\\d{0,2}$"))) {
                        onAmountChange(value)
                    }
                },
                modifier = Modifier.width(100.dp),
                leadingIcon = { Text("$", style = MaterialTheme.typography.labelMedium) },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
                textStyle = MaterialTheme.typography.bodySmall
            )

            // Remove Button
            IconButton(onClick = onRemove) {
                Icon(
                    Icons.Default.Close,
                    contentDescription = "Remove",
                    modifier = Modifier.size(18.dp),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun AllocationSummary(
    totalBudget: Double,
    allocated: Double,
    modifier: Modifier = Modifier
) {
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }
    val remaining = totalBudget - allocated
    val isOverAllocated = remaining < 0

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        color = if (isOverAllocated) {
            MaterialTheme.colorScheme.errorContainer
        } else {
            MaterialTheme.colorScheme.primaryContainer
        }
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "Allocated: ${currencyFormat.format(allocated)}",
                style = MaterialTheme.typography.labelMedium,
                color = if (isOverAllocated) {
                    MaterialTheme.colorScheme.onErrorContainer
                } else {
                    MaterialTheme.colorScheme.onPrimaryContainer
                }
            )
            Text(
                text = if (isOverAllocated) {
                    "Over by ${currencyFormat.format(-remaining)}"
                } else {
                    "${currencyFormat.format(remaining)} unallocated"
                },
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = if (isOverAllocated) {
                    MaterialTheme.colorScheme.onErrorContainer
                } else {
                    MaterialTheme.colorScheme.onPrimaryContainer
                }
            )
        }
    }
}

@Composable
private fun AlertThresholdItem(
    percentage: Int,
    isEnabled: Boolean,
    onToggle: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
    label: String? = null
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                Icons.Default.Notifications,
                contentDescription = null,
                modifier = Modifier.size(20.dp),
                tint = when (percentage) {
                    50 -> Color(0xFF4CAF50)
                    75 -> Color(0xFFFFC107)
                    90 -> Color(0xFFFF9800)
                    else -> Color(0xFFF44336)
                }
            )
            Spacer(modifier = Modifier.width(12.dp))
            Text(
                text = label ?: "At $percentage%",
                style = MaterialTheme.typography.bodyMedium
            )
        }

        Switch(
            checked = isEnabled,
            onCheckedChange = onToggle
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DatePickerDialogWrapper(
    initialDate: LocalDate,
    onDateSelected: (LocalDate) -> Unit,
    onDismiss: () -> Unit
) {
    val datePickerState = rememberDatePickerState(
        initialSelectedDateMillis = initialDate.atStartOfDay(ZoneId.systemDefault())
            .toInstant()
            .toEpochMilli()
    )

    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(
                onClick = {
                    datePickerState.selectedDateMillis?.let { millis ->
                        val date = Instant.ofEpochMilli(millis)
                            .atZone(ZoneId.systemDefault())
                            .toLocalDate()
                        onDateSelected(date)
                    }
                }
            ) {
                Text("OK")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    ) {
        DatePicker(state = datePickerState)
    }
}

@Composable
private fun CategorySelectionDialog(
    categories: List<CategoryFormItem>,
    selectedCategoryIds: List<String>,
    onCategoryToggle: (String) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Select Categories") },
        text = {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                items(categories) { category ->
                    val isSelected = selectedCategoryIds.contains(category.id)

                    Surface(
                        onClick = { onCategoryToggle(category.id) },
                        shape = RoundedCornerShape(8.dp),
                        color = if (isSelected) {
                            MaterialTheme.colorScheme.primaryContainer
                        } else {
                            Color.Transparent
                        }
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(32.dp)
                                        .clip(CircleShape)
                                        .background(
                                            if (isSelected) {
                                                MaterialTheme.colorScheme.primary
                                            } else {
                                                MaterialTheme.colorScheme.surfaceVariant
                                            }
                                        ),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        Icons.Default.Category,
                                        contentDescription = null,
                                        modifier = Modifier.size(16.dp),
                                        tint = if (isSelected) {
                                            MaterialTheme.colorScheme.onPrimary
                                        } else {
                                            MaterialTheme.colorScheme.onSurfaceVariant
                                        }
                                    )
                                }

                                Spacer(modifier = Modifier.width(12.dp))

                                Text(
                                    text = category.name,
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }

                            if (isSelected) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = "Selected",
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Done")
            }
        }
    )
}

// ==================== State & ViewModel ====================

/**
 * Form state for budget creation/editing.
 */
data class BudgetFormState(
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val isEditMode: Boolean = false,
    val name: String = "",
    val amount: String = "",
    val periodType: BudgetPeriodTypeForm = BudgetPeriodTypeForm.MONTHLY,
    val startDate: LocalDate = LocalDate.now().withDayOfMonth(1),
    val endDate: LocalDate = LocalDate.now().plusMonths(1).withDayOfMonth(1).minusDays(1),
    val categoryAllocations: List<CategoryAllocationForm> = emptyList(),
    val alertAt50: Boolean = true,
    val alertAt75: Boolean = true,
    val alertAt90: Boolean = true,
    val alertAt100: Boolean = true,
    val availableCategories: List<CategoryFormItem> = emptyList(),
    val errors: Map<String, String> = emptyMap()
) {
    val isValid: Boolean
        get() = name.isNotBlank() &&
                amount.isNotBlank() &&
                (amount.toDoubleOrNull() ?: 0.0) > 0 &&
                startDate.isBefore(endDate)
}

/**
 * Category allocation form data.
 */
data class CategoryAllocationForm(
    val categoryId: String,
    val categoryName: String,
    val amount: String = ""
)

/**
 * Category item for selection.
 */
data class CategoryFormItem(
    val id: String,
    val name: String,
    val icon: String = "category"
)

/**
 * Budget period types for the form.
 */
enum class BudgetPeriodTypeForm(val displayName: String) {
    DAILY("Daily"),
    WEEKLY("Weekly"),
    MONTHLY("Monthly"),
    QUARTERLY("Quarterly"),
    YEARLY("Yearly"),
    CUSTOM("Custom")
}

/**
 * Events emitted by the budget form.
 */
sealed class BudgetFormEvent {
    data object SaveSuccess : BudgetFormEvent()
    data class ShowError(val message: String) : BudgetFormEvent()
    data class ValidationError(val message: String) : BudgetFormEvent()
}
