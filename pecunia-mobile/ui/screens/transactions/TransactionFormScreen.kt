package com.pecunia.ui.screens.transactions

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.pecunia.R
import com.pecunia.domain.models.RecurringFrequency
import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionCategory
import com.pecunia.domain.models.TransactionType
import java.math.BigDecimal
import java.time.LocalDate
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionFormScreen(
    existingTransaction: Transaction? = null,
    isLoading: Boolean = false,
    onSave: (TransactionFormData) -> Unit,
    onDelete: ((String) -> Unit)? = null,
    onNavigateBack: () -> Unit,
    onScanReceipt: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isEditing = existingTransaction != null

    var transactionType by remember {
        mutableStateOf(existingTransaction?.type ?: TransactionType.EXPENSE)
    }
    var amount by remember {
        mutableStateOf(existingTransaction?.amount?.toPlainString() ?: "")
    }
    var description by remember {
        mutableStateOf(existingTransaction?.description ?: "")
    }
    var merchant by remember {
        mutableStateOf(existingTransaction?.merchant ?: "")
    }
    var selectedCategory by remember {
        mutableStateOf(existingTransaction?.category ?: TransactionCategory.OTHER_EXPENSE)
    }
    var selectedDate by remember {
        mutableStateOf(existingTransaction?.date ?: LocalDate.now())
    }
    var isRecurring by remember {
        mutableStateOf(existingTransaction?.isRecurring ?: false)
    }
    var recurringFrequency by remember {
        mutableStateOf(existingTransaction?.recurringDetails?.frequency ?: RecurringFrequency.MONTHLY)
    }
    var tags by remember {
        mutableStateOf(existingTransaction?.tags?.joinToString(", ") ?: "")
    }

    var showDatePicker by remember { mutableStateOf(false) }
    var showCategoryPicker by remember { mutableStateOf(false) }
    var showDeleteConfirmation by remember { mutableStateOf(false) }

    val scrollState = rememberScrollState()

    // Validation
    val isFormValid = amount.isNotBlank() &&
            amount.toBigDecimalOrNull() != null &&
            description.isNotBlank()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        if (isEditing)
                            stringResource(R.string.edit_transaction)
                        else
                            stringResource(R.string.add_transaction)
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.Close, contentDescription = stringResource(R.string.cancel))
                    }
                },
                actions = {
                    if (isEditing && onDelete != null) {
                        IconButton(onClick = { showDeleteConfirmation = true }) {
                            Icon(
                                Icons.Default.Delete,
                                contentDescription = stringResource(R.string.delete),
                                tint = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                    TextButton(
                        onClick = {
                            onSave(
                                TransactionFormData(
                                    id = existingTransaction?.id,
                                    type = transactionType,
                                    amount = amount.toBigDecimal(),
                                    description = description,
                                    merchant = merchant.takeIf { it.isNotBlank() },
                                    category = selectedCategory,
                                    date = selectedDate,
                                    isRecurring = isRecurring,
                                    recurringFrequency = if (isRecurring) recurringFrequency else null,
                                    tags = tags.split(",").map { it.trim() }.filter { it.isNotBlank() }
                                )
                            )
                        },
                        enabled = isFormValid && !isLoading
                    ) {
                        Text(stringResource(R.string.save))
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Transaction Type Selector
            TransactionTypeSelector(
                selectedType = transactionType,
                onTypeSelected = { transactionType = it }
            )

            // Amount Input
            OutlinedTextField(
                value = amount,
                onValueChange = { newValue ->
                    // Allow only valid decimal input
                    if (newValue.isEmpty() || newValue.matches(Regex("^\\d*\\.?\\d{0,2}\$"))) {
                        amount = newValue
                    }
                },
                label = { Text(stringResource(R.string.amount)) },
                placeholder = { Text("0.00") },
                leadingIcon = {
                    Icon(Icons.Default.AttachMoney, contentDescription = null)
                },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                isError = amount.isNotBlank() && amount.toBigDecimalOrNull() == null
            )

            // Description Input
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text(stringResource(R.string.description)) },
                placeholder = { Text(stringResource(R.string.description_placeholder)) },
                leadingIcon = {
                    Icon(Icons.Default.Description, contentDescription = null)
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            // Merchant Input
            OutlinedTextField(
                value = merchant,
                onValueChange = { merchant = it },
                label = { Text(stringResource(R.string.merchant_optional)) },
                placeholder = { Text(stringResource(R.string.merchant_placeholder)) },
                leadingIcon = {
                    Icon(Icons.Default.Store, contentDescription = null)
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            // Category Selector
            OutlinedTextField(
                value = selectedCategory.displayName,
                onValueChange = { },
                label = { Text(stringResource(R.string.category)) },
                leadingIcon = {
                    Icon(Icons.Default.Category, contentDescription = null)
                },
                trailingIcon = {
                    Icon(Icons.Default.ArrowDropDown, contentDescription = null)
                },
                readOnly = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showCategoryPicker = true }
            )

            // Date Selector
            OutlinedTextField(
                value = selectedDate.format(DateTimeFormatter.ofPattern("MMM d, yyyy")),
                onValueChange = { },
                label = { Text(stringResource(R.string.date)) },
                leadingIcon = {
                    Icon(Icons.Default.CalendarToday, contentDescription = null)
                },
                trailingIcon = {
                    Icon(Icons.Default.ArrowDropDown, contentDescription = null)
                },
                readOnly = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showDatePicker = true }
            )

            // Recurring Transaction Toggle
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = stringResource(R.string.recurring_transaction),
                                style = MaterialTheme.typography.titleSmall
                            )
                            Text(
                                text = stringResource(R.string.recurring_description),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(
                            checked = isRecurring,
                            onCheckedChange = { isRecurring = it }
                        )
                    }

                    if (isRecurring) {
                        Spacer(modifier = Modifier.height(16.dp))
                        RecurringFrequencySelector(
                            selectedFrequency = recurringFrequency,
                            onFrequencySelected = { recurringFrequency = it }
                        )
                    }
                }
            }

            // Tags Input
            OutlinedTextField(
                value = tags,
                onValueChange = { tags = it },
                label = { Text(stringResource(R.string.tags_optional)) },
                placeholder = { Text(stringResource(R.string.tags_placeholder)) },
                leadingIcon = {
                    Icon(Icons.Default.Label, contentDescription = null)
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                supportingText = {
                    Text(stringResource(R.string.tags_helper))
                }
            )

            // Scan Receipt Button
            OutlinedButton(
                onClick = onScanReceipt,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Default.CameraAlt, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(stringResource(R.string.scan_receipt))
            }

            // Loading Indicator
            if (isLoading) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }
        }

        // Category Picker Dialog
        if (showCategoryPicker) {
            CategoryPickerDialog(
                selectedCategory = selectedCategory,
                transactionType = transactionType,
                onCategorySelected = {
                    selectedCategory = it
                    showCategoryPicker = false
                },
                onDismiss = { showCategoryPicker = false }
            )
        }

        // Date Picker Dialog
        if (showDatePicker) {
            val datePickerState = rememberDatePickerState(
                initialSelectedDateMillis = selectedDate.toEpochDay() * 24 * 60 * 60 * 1000
            )
            DatePickerDialog(
                onDismissRequest = { showDatePicker = false },
                confirmButton = {
                    TextButton(
                        onClick = {
                            datePickerState.selectedDateMillis?.let { millis ->
                                selectedDate = LocalDate.ofEpochDay(millis / (24 * 60 * 60 * 1000))
                            }
                            showDatePicker = false
                        }
                    ) {
                        Text(stringResource(R.string.confirm))
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDatePicker = false }) {
                        Text(stringResource(R.string.cancel))
                    }
                }
            ) {
                DatePicker(state = datePickerState)
            }
        }

        // Delete Confirmation Dialog
        if (showDeleteConfirmation) {
            AlertDialog(
                onDismissRequest = { showDeleteConfirmation = false },
                title = { Text(stringResource(R.string.delete_transaction)) },
                text = { Text(stringResource(R.string.delete_transaction_confirmation)) },
                confirmButton = {
                    TextButton(
                        onClick = {
                            existingTransaction?.let { onDelete?.invoke(it.id) }
                            showDeleteConfirmation = false
                        },
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text(stringResource(R.string.delete))
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDeleteConfirmation = false }) {
                        Text(stringResource(R.string.cancel))
                    }
                }
            )
        }
    }
}

@Composable
private fun TransactionTypeSelector(
    selectedType: TransactionType,
    onTypeSelected: (TransactionType) -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        TransactionType.values().forEach { type ->
            FilterChip(
                selected = selectedType == type,
                onClick = { onTypeSelected(type) },
                label = {
                    Text(
                        when (type) {
                            TransactionType.INCOME -> stringResource(R.string.income)
                            TransactionType.EXPENSE -> stringResource(R.string.expense)
                            TransactionType.TRANSFER -> stringResource(R.string.transfer)
                        }
                    )
                },
                leadingIcon = if (selectedType == type) {
                    {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                } else null,
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun RecurringFrequencySelector(
    selectedFrequency: RecurringFrequency,
    onFrequencySelected: (RecurringFrequency) -> Unit,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = it },
        modifier = modifier.fillMaxWidth()
    ) {
        OutlinedTextField(
            value = selectedFrequency.name.lowercase().replaceFirstChar { it.uppercase() },
            onValueChange = { },
            label = { Text(stringResource(R.string.frequency)) },
            trailingIcon = {
                ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
            },
            readOnly = true,
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor()
        )

        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false }
        ) {
            RecurringFrequency.values().forEach { frequency ->
                DropdownMenuItem(
                    text = {
                        Text(frequency.name.lowercase().replaceFirstChar { it.uppercase() })
                    },
                    onClick = {
                        onFrequencySelected(frequency)
                        expanded = false
                    }
                )
            }
        }
    }
}

@Composable
private fun CategoryPickerDialog(
    selectedCategory: TransactionCategory,
    transactionType: TransactionType,
    onCategorySelected: (TransactionCategory) -> Unit,
    onDismiss: () -> Unit
) {
    val categories = when (transactionType) {
        TransactionType.INCOME -> TransactionCategory.incomeCategories()
        else -> TransactionCategory.expenseCategories()
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.select_category)) },
        text = {
            Column {
                categories.forEach { category ->
                    ListItem(
                        headlineContent = { Text(category.displayName) },
                        leadingContent = {
                            RadioButton(
                                selected = selectedCategory == category,
                                onClick = { onCategorySelected(category) }
                            )
                        },
                        modifier = Modifier.clickable { onCategorySelected(category) }
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.close))
            }
        }
    )
}

/**
 * Data class for transaction form submission.
 */
data class TransactionFormData(
    val id: String? = null,
    val type: TransactionType,
    val amount: BigDecimal,
    val description: String,
    val merchant: String? = null,
    val category: TransactionCategory,
    val date: LocalDate,
    val isRecurring: Boolean = false,
    val recurringFrequency: RecurringFrequency? = null,
    val tags: List<String> = emptyList()
)
