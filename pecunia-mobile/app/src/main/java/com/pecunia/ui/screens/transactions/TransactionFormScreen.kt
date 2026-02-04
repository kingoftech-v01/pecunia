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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.math.BigDecimal
import java.time.LocalDate
import java.time.format.DateTimeFormatter

/**
 * Transaction form screen for adding or editing transactions.
 * Supports all transaction types, categories, recurring transactions, and receipt scanning.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionFormScreen(
    transactionId: String? = null,
    viewModel: TransactionsViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onScanReceipt: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.formState.collectAsStateWithLifecycle()
    val isEditing = transactionId != null

    // Load existing transaction if editing
    LaunchedEffect(transactionId) {
        transactionId?.let { viewModel.loadTransactionForEdit(it) }
    }

    LaunchedEffect(Unit) {
        viewModel.formEvents.collect { event ->
            when (event) {
                is TransactionFormEvent.SaveSuccess -> onNavigateBack()
                is TransactionFormEvent.DeleteSuccess -> onNavigateBack()
                is TransactionFormEvent.ShowError -> {
                    // Show error snackbar
                }
            }
        }
    }

    var showDatePicker by remember { mutableStateOf(false) }
    var showCategoryPicker by remember { mutableStateOf(false) }
    var showDeleteConfirmation by remember { mutableStateOf(false) }
    var showAccountPicker by remember { mutableStateOf(false) }

    val scrollState = rememberScrollState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(if (isEditing) "Edit Transaction" else "Add Transaction")
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.Close, contentDescription = "Close")
                    }
                },
                actions = {
                    if (isEditing) {
                        IconButton(onClick = { showDeleteConfirmation = true }) {
                            Icon(
                                Icons.Default.Delete,
                                contentDescription = "Delete",
                                tint = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                    TextButton(
                        onClick = { viewModel.saveTransaction() },
                        enabled = uiState.isValid && !uiState.isSaving
                    ) {
                        if (uiState.isSaving) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Text("Save")
                        }
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
                selectedType = uiState.transactionType,
                onTypeSelected = { viewModel.updateTransactionType(it) }
            )

            // Amount Input
            AmountInputField(
                amount = uiState.amount,
                onAmountChange = { viewModel.updateAmount(it) },
                isError = uiState.amountError != null,
                errorMessage = uiState.amountError
            )

            // Description Input
            OutlinedTextField(
                value = uiState.description,
                onValueChange = { viewModel.updateDescription(it) },
                label = { Text("Description") },
                placeholder = { Text("What was this for?") },
                leadingIcon = {
                    Icon(Icons.Default.Description, contentDescription = null)
                },
                singleLine = true,
                isError = uiState.descriptionError != null,
                supportingText = uiState.descriptionError?.let { { Text(it) } },
                modifier = Modifier.fillMaxWidth()
            )

            // Merchant Input (optional)
            OutlinedTextField(
                value = uiState.merchant,
                onValueChange = { viewModel.updateMerchant(it) },
                label = { Text("Merchant (optional)") },
                placeholder = { Text("Where did you spend?") },
                leadingIcon = {
                    Icon(Icons.Default.Store, contentDescription = null)
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            // Category Selector
            CategorySelectorField(
                selectedCategory = uiState.selectedCategory,
                onClick = { showCategoryPicker = true }
            )

            // Account Selector
            AccountSelectorField(
                selectedAccount = uiState.selectedAccount,
                onClick = { showAccountPicker = true }
            )

            // Date Selector
            DateSelectorField(
                selectedDate = uiState.date,
                onClick = { showDatePicker = true }
            )

            // Recurring Transaction Section
            RecurringTransactionCard(
                isRecurring = uiState.isRecurring,
                onRecurringChange = { viewModel.updateIsRecurring(it) },
                frequency = uiState.recurringFrequency,
                onFrequencyChange = { viewModel.updateRecurringFrequency(it) },
                endDate = uiState.recurringEndDate,
                onEndDateChange = { viewModel.updateRecurringEndDate(it) }
            )

            // Tags Input
            OutlinedTextField(
                value = uiState.tags,
                onValueChange = { viewModel.updateTags(it) },
                label = { Text("Tags (optional)") },
                placeholder = { Text("work, personal, vacation...") },
                leadingIcon = {
                    Icon(Icons.Default.Label, contentDescription = null)
                },
                supportingText = { Text("Separate tags with commas") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            // Notes Input
            OutlinedTextField(
                value = uiState.notes,
                onValueChange = { viewModel.updateNotes(it) },
                label = { Text("Notes (optional)") },
                placeholder = { Text("Add any additional notes...") },
                leadingIcon = {
                    Icon(Icons.Default.Notes, contentDescription = null)
                },
                minLines = 3,
                maxLines = 5,
                modifier = Modifier.fillMaxWidth()
            )

            // Scan Receipt Button
            OutlinedButton(
                onClick = onScanReceipt,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Default.CameraAlt, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Scan Receipt")
            }

            // Saving Progress
            if (uiState.isSaving) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }

            // Bottom Spacing
            Spacer(modifier = Modifier.height(32.dp))
        }

        // Date Picker Dialog
        if (showDatePicker) {
            val datePickerState = rememberDatePickerState(
                initialSelectedDateMillis = uiState.date.toEpochDay() * 24 * 60 * 60 * 1000
            )
            DatePickerDialog(
                onDismissRequest = { showDatePicker = false },
                confirmButton = {
                    TextButton(
                        onClick = {
                            datePickerState.selectedDateMillis?.let { millis ->
                                viewModel.updateDate(
                                    LocalDate.ofEpochDay(millis / (24 * 60 * 60 * 1000))
                                )
                            }
                            showDatePicker = false
                        }
                    ) {
                        Text("Confirm")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDatePicker = false }) {
                        Text("Cancel")
                    }
                }
            ) {
                DatePicker(state = datePickerState)
            }
        }

        // Category Picker Dialog
        if (showCategoryPicker) {
            CategoryPickerDialog(
                selectedCategory = uiState.selectedCategory,
                transactionType = uiState.transactionType,
                categories = uiState.availableCategories,
                onCategorySelected = {
                    viewModel.updateCategory(it)
                    showCategoryPicker = false
                },
                onDismiss = { showCategoryPicker = false }
            )
        }

        // Account Picker Dialog
        if (showAccountPicker) {
            AccountPickerDialog(
                selectedAccount = uiState.selectedAccount,
                accounts = uiState.availableAccounts,
                onAccountSelected = {
                    viewModel.updateAccount(it)
                    showAccountPicker = false
                },
                onDismiss = { showAccountPicker = false }
            )
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
                title = { Text("Delete Transaction") },
                text = { Text("Are you sure you want to delete this transaction? This action cannot be undone.") },
                confirmButton = {
                    TextButton(
                        onClick = {
                            transactionId?.let { viewModel.deleteTransaction(it) }
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
private fun TransactionTypeSelector(
    selectedType: FormTransactionType,
    onTypeSelected: (FormTransactionType) -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        FormTransactionType.entries.forEach { type ->
            FilterChip(
                selected = selectedType == type,
                onClick = { onTypeSelected(type) },
                label = { Text(type.displayName) },
                leadingIcon = if (selectedType == type) {
                    {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                } else {
                    {
                        Icon(
                            imageVector = type.icon,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun AmountInputField(
    amount: String,
    onAmountChange: (String) -> Unit,
    isError: Boolean,
    errorMessage: String?,
    modifier: Modifier = Modifier
) {
    OutlinedTextField(
        value = amount,
        onValueChange = { newValue ->
            // Only allow valid decimal input
            if (newValue.isEmpty() || newValue.matches(Regex("^\\d*\\.?\\d{0,2}\$"))) {
                onAmountChange(newValue)
            }
        },
        label = { Text("Amount") },
        placeholder = { Text("0.00") },
        leadingIcon = {
            Icon(Icons.Default.AttachMoney, contentDescription = null)
        },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        singleLine = true,
        isError = isError,
        supportingText = errorMessage?.let { { Text(it) } },
        modifier = modifier.fillMaxWidth()
    )
}

@Composable
private fun CategorySelectorField(
    selectedCategory: CategoryUiModel?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedTextField(
        value = selectedCategory?.name ?: "",
        onValueChange = { },
        label = { Text("Category") },
        placeholder = { Text("Select a category") },
        leadingIcon = {
            Icon(
                imageVector = selectedCategory?.icon ?: Icons.Default.Category,
                contentDescription = null
            )
        },
        trailingIcon = {
            Icon(Icons.Default.ArrowDropDown, contentDescription = null)
        },
        readOnly = true,
        enabled = false,
        colors = OutlinedTextFieldDefaults.colors(
            disabledTextColor = MaterialTheme.colorScheme.onSurface,
            disabledBorderColor = MaterialTheme.colorScheme.outline,
            disabledLeadingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
            disabledTrailingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
            disabledLabelColor = MaterialTheme.colorScheme.onSurfaceVariant
        ),
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    )
}

@Composable
private fun AccountSelectorField(
    selectedAccount: AccountUiModel?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedTextField(
        value = selectedAccount?.name ?: "",
        onValueChange = { },
        label = { Text("Account") },
        placeholder = { Text("Select an account") },
        leadingIcon = {
            Icon(Icons.Default.AccountBalance, contentDescription = null)
        },
        trailingIcon = {
            Icon(Icons.Default.ArrowDropDown, contentDescription = null)
        },
        readOnly = true,
        enabled = false,
        colors = OutlinedTextFieldDefaults.colors(
            disabledTextColor = MaterialTheme.colorScheme.onSurface,
            disabledBorderColor = MaterialTheme.colorScheme.outline,
            disabledLeadingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
            disabledTrailingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
            disabledLabelColor = MaterialTheme.colorScheme.onSurfaceVariant
        ),
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    )
}

@Composable
private fun DateSelectorField(
    selectedDate: LocalDate,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val formatter = remember { DateTimeFormatter.ofPattern("EEEE, MMM d, yyyy") }

    OutlinedTextField(
        value = selectedDate.format(formatter),
        onValueChange = { },
        label = { Text("Date") },
        leadingIcon = {
            Icon(Icons.Default.CalendarToday, contentDescription = null)
        },
        trailingIcon = {
            Icon(Icons.Default.ArrowDropDown, contentDescription = null)
        },
        readOnly = true,
        enabled = false,
        colors = OutlinedTextFieldDefaults.colors(
            disabledTextColor = MaterialTheme.colorScheme.onSurface,
            disabledBorderColor = MaterialTheme.colorScheme.outline,
            disabledLeadingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
            disabledTrailingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
            disabledLabelColor = MaterialTheme.colorScheme.onSurfaceVariant
        ),
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    )
}

@Composable
private fun RecurringTransactionCard(
    isRecurring: Boolean,
    onRecurringChange: (Boolean) -> Unit,
    frequency: RecurringFrequency,
    onFrequencyChange: (RecurringFrequency) -> Unit,
    endDate: LocalDate?,
    onEndDateChange: (LocalDate?) -> Unit,
    modifier: Modifier = Modifier
) {
    var showEndDatePicker by remember { mutableStateOf(false) }

    Card(
        modifier = modifier.fillMaxWidth(),
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
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Recurring Transaction",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Medium
                    )
                    Text(
                        text = "Repeat this transaction automatically",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = isRecurring,
                    onCheckedChange = onRecurringChange
                )
            }

            if (isRecurring) {
                Spacer(modifier = Modifier.height(16.dp))

                // Frequency Selector
                Text(
                    text = "Frequency",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(8.dp))

                var expanded by remember { mutableStateOf(false) }
                ExposedDropdownMenuBox(
                    expanded = expanded,
                    onExpandedChange = { expanded = it },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    OutlinedTextField(
                        value = frequency.displayName,
                        onValueChange = { },
                        readOnly = true,
                        trailingIcon = {
                            ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )

                    ExposedDropdownMenu(
                        expanded = expanded,
                        onDismissRequest = { expanded = false }
                    ) {
                        RecurringFrequency.entries.forEach { freq ->
                            DropdownMenuItem(
                                text = { Text(freq.displayName) },
                                onClick = {
                                    onFrequencyChange(freq)
                                    expanded = false
                                }
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // End Date (optional)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "End Date (optional)",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = endDate?.format(DateTimeFormatter.ofPattern("MMM d, yyyy"))
                                ?: "No end date",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                    Row {
                        if (endDate != null) {
                            IconButton(onClick = { onEndDateChange(null) }) {
                                Icon(Icons.Default.Clear, contentDescription = "Clear")
                            }
                        }
                        IconButton(onClick = { showEndDatePicker = true }) {
                            Icon(Icons.Default.CalendarToday, contentDescription = "Select date")
                        }
                    }
                }
            }
        }
    }

    // End Date Picker
    if (showEndDatePicker) {
        val datePickerState = rememberDatePickerState(
            initialSelectedDateMillis = (endDate ?: LocalDate.now().plusMonths(1))
                .toEpochDay() * 24 * 60 * 60 * 1000
        )
        DatePickerDialog(
            onDismissRequest = { showEndDatePicker = false },
            confirmButton = {
                TextButton(
                    onClick = {
                        datePickerState.selectedDateMillis?.let { millis ->
                            onEndDateChange(
                                LocalDate.ofEpochDay(millis / (24 * 60 * 60 * 1000))
                            )
                        }
                        showEndDatePicker = false
                    }
                ) {
                    Text("Confirm")
                }
            },
            dismissButton = {
                TextButton(onClick = { showEndDatePicker = false }) {
                    Text("Cancel")
                }
            }
        ) {
            DatePicker(state = datePickerState)
        }
    }
}

@Composable
private fun CategoryPickerDialog(
    selectedCategory: CategoryUiModel?,
    transactionType: FormTransactionType,
    categories: List<CategoryUiModel>,
    onCategorySelected: (CategoryUiModel) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Select Category") },
        text = {
            Column {
                categories.forEach { category ->
                    ListItem(
                        headlineContent = { Text(category.name) },
                        leadingContent = {
                            Icon(
                                imageVector = category.icon,
                                contentDescription = null,
                                tint = category.color
                            )
                        },
                        trailingContent = {
                            if (selectedCategory?.id == category.id) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        },
                        modifier = Modifier.clickable { onCategorySelected(category) }
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}

@Composable
private fun AccountPickerDialog(
    selectedAccount: AccountUiModel?,
    accounts: List<AccountUiModel>,
    onAccountSelected: (AccountUiModel) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Select Account") },
        text = {
            Column {
                accounts.forEach { account ->
                    ListItem(
                        headlineContent = { Text(account.name) },
                        supportingContent = { Text(account.type) },
                        leadingContent = {
                            Icon(
                                imageVector = Icons.Default.AccountBalance,
                                contentDescription = null
                            )
                        },
                        trailingContent = {
                            if (selectedAccount?.id == account.id) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        },
                        modifier = Modifier.clickable { onAccountSelected(account) }
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}

/**
 * Transaction type enum for the form.
 */
enum class FormTransactionType(val displayName: String, val icon: ImageVector) {
    EXPENSE("Expense", Icons.Default.ArrowDownward),
    INCOME("Income", Icons.Default.ArrowUpward),
    TRANSFER("Transfer", Icons.Default.SwapHoriz)
}

/**
 * Recurring frequency options.
 */
enum class RecurringFrequency(val displayName: String) {
    DAILY("Daily"),
    WEEKLY("Weekly"),
    BIWEEKLY("Bi-weekly"),
    MONTHLY("Monthly"),
    QUARTERLY("Quarterly"),
    YEARLY("Yearly")
}

/**
 * UI model for category selection.
 */
data class CategoryUiModel(
    val id: String,
    val name: String,
    val icon: ImageVector,
    val color: androidx.compose.ui.graphics.Color,
    val type: FormTransactionType
)

/**
 * UI model for account selection.
 */
data class AccountUiModel(
    val id: String,
    val name: String,
    val type: String,
    val balance: BigDecimal
)

/**
 * Events emitted by the transaction form.
 */
sealed class TransactionFormEvent {
    data object SaveSuccess : TransactionFormEvent()
    data object DeleteSuccess : TransactionFormEvent()
    data class ShowError(val message: String) : TransactionFormEvent()
}
