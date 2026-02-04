package com.pecunia.ui.screens.transactions

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pecunia.data.local.dao.TransactionDao
import com.pecunia.data.local.dao.CategoryDao
import com.pecunia.data.local.dao.BankAccountDao
import com.pecunia.data.local.entities.TransactionEntity
import com.pecunia.data.local.preferences.UserPreferences
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.time.LocalDate
import java.time.ZoneId
import java.util.UUID
import javax.inject.Inject

/**
 * ViewModel for the Transactions screens (list and form).
 * Handles transaction loading, filtering, sorting, and CRUD operations.
 */
@HiltViewModel
class TransactionsViewModel @Inject constructor(
    private val transactionDao: TransactionDao,
    private val categoryDao: CategoryDao,
    private val bankAccountDao: BankAccountDao,
    private val userPreferences: UserPreferences
) : ViewModel() {

    // List Screen State
    private val _uiState = MutableStateFlow(TransactionsUiState())
    val uiState: StateFlow<TransactionsUiState> = _uiState.asStateFlow()

    private val _events = MutableSharedFlow<TransactionsEvent>()
    val events: SharedFlow<TransactionsEvent> = _events.asSharedFlow()

    // Form Screen State
    private val _formState = MutableStateFlow(TransactionFormState())
    val formState: StateFlow<TransactionFormState> = _formState.asStateFlow()

    private val _formEvents = MutableSharedFlow<TransactionFormEvent>()
    val formEvents: SharedFlow<TransactionFormEvent> = _formEvents.asSharedFlow()

    // All transactions (unfiltered)
    private var allTransactions: List<TransactionItemUiModel> = emptyList()

    init {
        loadTransactions()
        loadCategories()
        loadAccounts()
    }

    // ==================== List Screen Functions ====================

    /**
     * Load all transactions for the current user.
     */
    fun loadTransactions() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            try {
                val userId = userPreferences.getCurrentUserId() ?: return@launch

                transactionDao.getTransactions(userId)
                    .catch { e ->
                        _uiState.update { it.copy(isLoading = false, error = e.message) }
                    }
                    .collect { entities ->
                        allTransactions = entities.map { entity ->
                            mapEntityToUiModel(entity)
                        }

                        applyFiltersAndSort()
                        _uiState.update { it.copy(isLoading = false) }
                    }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(isLoading = false, error = e.message ?: "Failed to load transactions")
                }
            }
        }
    }

    /**
     * Refresh transactions with pull-to-refresh.
     */
    fun refreshTransactions() {
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }

            try {
                loadTransactions()
            } finally {
                _uiState.update { it.copy(isRefreshing = false) }
            }
        }
    }

    /**
     * Update search query and apply filters.
     */
    fun onSearchQueryChanged(query: String) {
        _uiState.update { it.copy(searchQuery = query) }
        applyFiltersAndSort()
    }

    /**
     * Update selected filter and apply filters.
     */
    fun onFilterChanged(filter: TransactionFilter) {
        _uiState.update { it.copy(selectedFilter = filter) }
        applyFiltersAndSort()
    }

    /**
     * Update sort option and apply sorting.
     */
    fun onSortOptionChanged(option: TransactionSortOption) {
        _uiState.update { it.copy(sortOption = option) }
        applyFiltersAndSort()
    }

    /**
     * Update date range filter.
     */
    fun onDateRangeChanged(dateRange: DateRange?) {
        _uiState.update { it.copy(dateRange = dateRange) }
        applyFiltersAndSort()
    }

    /**
     * Update selected categories filter.
     */
    fun onCategoriesChanged(categories: Set<String>) {
        _uiState.update { it.copy(selectedCategories = categories) }
        applyFiltersAndSort()
    }

    /**
     * Update amount range filter.
     */
    fun onAmountRangeChanged(range: AmountRange?) {
        _uiState.update { it.copy(amountRange = range) }
        applyFiltersAndSort()
    }

    /**
     * Clear all filters.
     */
    fun clearFilters() {
        _uiState.update {
            it.copy(
                selectedFilter = TransactionFilter.ALL,
                searchQuery = "",
                dateRange = null,
                selectedCategories = emptySet(),
                amountRange = null
            )
        }
        applyFiltersAndSort()
    }

    /**
     * Handle transaction item click.
     */
    fun onTransactionClicked(transactionId: String) {
        viewModelScope.launch {
            _events.emit(TransactionsEvent.NavigateToDetail(transactionId))
        }
    }

    private fun applyFiltersAndSort() {
        var filtered = allTransactions

        // Apply type filter
        filtered = when (_uiState.value.selectedFilter) {
            TransactionFilter.ALL -> filtered
            TransactionFilter.INCOME -> filtered.filter { it.type == TransactionTypeFilter.INCOME }
            TransactionFilter.EXPENSES -> filtered.filter { it.type == TransactionTypeFilter.EXPENSE }
            TransactionFilter.TRANSFERS -> filtered.filter { it.type == TransactionTypeFilter.TRANSFER }
            TransactionFilter.THIS_WEEK -> {
                val startOfWeek = LocalDate.now().minusDays(LocalDate.now().dayOfWeek.value.toLong() - 1)
                filtered.filter { it.date >= startOfWeek }
            }
            TransactionFilter.THIS_MONTH -> {
                val startOfMonth = LocalDate.now().withDayOfMonth(1)
                filtered.filter { it.date >= startOfMonth }
            }
        }

        // Apply search query
        val query = _uiState.value.searchQuery.lowercase()
        if (query.isNotEmpty()) {
            filtered = filtered.filter { transaction ->
                transaction.description.lowercase().contains(query) ||
                transaction.categoryName.lowercase().contains(query) ||
                (transaction.merchant?.lowercase()?.contains(query) == true)
            }
        }

        // Apply date range
        _uiState.value.dateRange?.let { range ->
            val (startDate, endDate) = getDateRangeBounds(range)
            filtered = filtered.filter { it.date in startDate..endDate }
        }

        // Apply category filter
        if (_uiState.value.selectedCategories.isNotEmpty()) {
            filtered = filtered.filter { it.categoryName in _uiState.value.selectedCategories }
        }

        // Apply amount range
        _uiState.value.amountRange?.let { range ->
            filtered = filtered.filter { transaction ->
                val amount = transaction.amount
                (range.min == null || amount >= range.min) &&
                (range.max == null || amount <= range.max)
            }
        }

        // Apply sorting
        val sorted = when (_uiState.value.sortOption) {
            TransactionSortOption.DATE_DESC -> filtered.sortedByDescending { it.date }
            TransactionSortOption.DATE_ASC -> filtered.sortedBy { it.date }
            TransactionSortOption.AMOUNT_DESC -> filtered.sortedByDescending { it.amount }
            TransactionSortOption.AMOUNT_ASC -> filtered.sortedBy { it.amount }
            TransactionSortOption.CATEGORY -> filtered.sortedBy { it.categoryName }
        }

        // Group by date
        val grouped = sorted.groupBy { it.date }
            .toSortedMap(compareByDescending { it })

        // Calculate totals
        val totalIncome = filtered
            .filter { it.type == TransactionTypeFilter.INCOME }
            .sumOf { it.amount }
        val totalExpenses = filtered
            .filter { it.type == TransactionTypeFilter.EXPENSE }
            .sumOf { it.amount }

        _uiState.update {
            it.copy(
                filteredTransactions = sorted,
                groupedTransactions = grouped,
                totalIncome = totalIncome,
                totalExpenses = totalExpenses
            )
        }
    }

    private fun getDateRangeBounds(range: DateRange): Pair<LocalDate, LocalDate> {
        val today = LocalDate.now()
        return when (range) {
            DateRange.THIS_WEEK -> {
                val startOfWeek = today.minusDays(today.dayOfWeek.value.toLong() - 1)
                startOfWeek to today
            }
            DateRange.THIS_MONTH -> {
                today.withDayOfMonth(1) to today
            }
            DateRange.LAST_30_DAYS -> {
                today.minusDays(30) to today
            }
            DateRange.LAST_90_DAYS -> {
                today.minusDays(90) to today
            }
            DateRange.THIS_YEAR -> {
                today.withDayOfYear(1) to today
            }
            DateRange.CUSTOM -> {
                today.minusDays(30) to today // Default for custom
            }
        }
    }

    private fun mapEntityToUiModel(entity: TransactionEntity): TransactionItemUiModel {
        val type = when (entity.type.toString()) {
            "INCOME" -> TransactionTypeFilter.INCOME
            "EXPENSE" -> TransactionTypeFilter.EXPENSE
            else -> TransactionTypeFilter.TRANSFER
        }

        return TransactionItemUiModel(
            id = entity.id.toString(),
            description = entity.description,
            amount = entity.amount,
            type = type,
            categoryName = entity.categoryId?.toString() ?: "Uncategorized",
            categoryIcon = getCategoryIcon(entity.categoryId?.toString()),
            categoryColor = getCategoryColor(entity.categoryId?.toString()),
            merchant = entity.merchant,
            date = LocalDate.ofEpochDay(entity.transactionDate / (24 * 60 * 60 * 1000)),
            isSynced = entity.syncStatus == TransactionEntity.SyncStatus.SYNCED,
            isRecurring = entity.isRecurring
        )
    }

    // ==================== Form Screen Functions ====================

    /**
     * Load an existing transaction for editing.
     */
    fun loadTransactionForEdit(transactionId: String) {
        viewModelScope.launch {
            try {
                val transaction = transactionDao.getTransactionByIdSync(transactionId)
                transaction?.let { entity ->
                    _formState.update {
                        it.copy(
                            transactionId = entity.id.toString(),
                            transactionType = when (entity.type.toString()) {
                                "INCOME" -> FormTransactionType.INCOME
                                "EXPENSE" -> FormTransactionType.EXPENSE
                                else -> FormTransactionType.TRANSFER
                            },
                            amount = entity.amount.toPlainString(),
                            description = entity.description,
                            merchant = entity.merchant ?: "",
                            date = LocalDate.ofEpochDay(entity.transactionDate / (24 * 60 * 60 * 1000)),
                            isRecurring = entity.isRecurring,
                            tags = entity.tags ?: "",
                            isEditing = true
                        )
                    }
                }
            } catch (e: Exception) {
                _formEvents.emit(TransactionFormEvent.ShowError(e.message ?: "Failed to load transaction"))
            }
        }
    }

    /**
     * Load available categories.
     */
    private fun loadCategories() {
        viewModelScope.launch {
            try {
                val userId = userPreferences.getCurrentUserId() ?: return@launch

                categoryDao.getCategoriesByUserId(userId)
                    .collect { categories ->
                        val categoryModels = categories.map { entity ->
                            CategoryUiModel(
                                id = entity.id.toString(),
                                name = entity.name,
                                icon = getCategoryIcon(entity.name),
                                color = Color(android.graphics.Color.parseColor(entity.color)),
                                type = when (entity.type.toString()) {
                                    "INCOME" -> FormTransactionType.INCOME
                                    else -> FormTransactionType.EXPENSE
                                }
                            )
                        }
                        _formState.update { it.copy(availableCategories = categoryModels) }
                    }
            } catch (e: Exception) {
                // Use default categories if loading fails
            }
        }
    }

    /**
     * Load available accounts.
     */
    private fun loadAccounts() {
        viewModelScope.launch {
            try {
                val userId = userPreferences.getCurrentUserId() ?: return@launch

                bankAccountDao.getBankAccounts(userId)
                    .collect { accounts ->
                        val accountModels = accounts.map { entity ->
                            AccountUiModel(
                                id = entity.id.toString(),
                                name = entity.name,
                                type = entity.accountType,
                                balance = BigDecimal(entity.balance)
                            )
                        }
                        _formState.update { it.copy(availableAccounts = accountModels) }
                    }
            } catch (e: Exception) {
                // Continue without accounts
            }
        }
    }

    /**
     * Update transaction type in form.
     */
    fun updateTransactionType(type: FormTransactionType) {
        _formState.update { it.copy(transactionType = type) }
        validateForm()
    }

    /**
     * Update amount in form.
     */
    fun updateAmount(amount: String) {
        _formState.update { it.copy(amount = amount, amountError = null) }
        validateForm()
    }

    /**
     * Update description in form.
     */
    fun updateDescription(description: String) {
        _formState.update { it.copy(description = description, descriptionError = null) }
        validateForm()
    }

    /**
     * Update merchant in form.
     */
    fun updateMerchant(merchant: String) {
        _formState.update { it.copy(merchant = merchant) }
    }

    /**
     * Update category in form.
     */
    fun updateCategory(category: CategoryUiModel) {
        _formState.update { it.copy(selectedCategory = category) }
        validateForm()
    }

    /**
     * Update account in form.
     */
    fun updateAccount(account: AccountUiModel) {
        _formState.update { it.copy(selectedAccount = account) }
    }

    /**
     * Update date in form.
     */
    fun updateDate(date: LocalDate) {
        _formState.update { it.copy(date = date) }
    }

    /**
     * Update recurring status in form.
     */
    fun updateIsRecurring(isRecurring: Boolean) {
        _formState.update { it.copy(isRecurring = isRecurring) }
    }

    /**
     * Update recurring frequency in form.
     */
    fun updateRecurringFrequency(frequency: RecurringFrequency) {
        _formState.update { it.copy(recurringFrequency = frequency) }
    }

    /**
     * Update recurring end date in form.
     */
    fun updateRecurringEndDate(date: LocalDate?) {
        _formState.update { it.copy(recurringEndDate = date) }
    }

    /**
     * Update tags in form.
     */
    fun updateTags(tags: String) {
        _formState.update { it.copy(tags = tags) }
    }

    /**
     * Update notes in form.
     */
    fun updateNotes(notes: String) {
        _formState.update { it.copy(notes = notes) }
    }

    private fun validateForm() {
        val state = _formState.value
        var isValid = true
        var amountError: String? = null
        var descriptionError: String? = null

        // Validate amount
        if (state.amount.isBlank()) {
            amountError = "Amount is required"
            isValid = false
        } else if (state.amount.toBigDecimalOrNull() == null || state.amount.toBigDecimal() <= BigDecimal.ZERO) {
            amountError = "Please enter a valid amount"
            isValid = false
        }

        // Validate description
        if (state.description.isBlank()) {
            descriptionError = "Description is required"
            isValid = false
        }

        _formState.update {
            it.copy(
                isValid = isValid,
                amountError = amountError,
                descriptionError = descriptionError
            )
        }
    }

    /**
     * Save the transaction.
     */
    fun saveTransaction() {
        viewModelScope.launch {
            validateForm()

            val state = _formState.value
            if (!state.isValid) return@launch

            _formState.update { it.copy(isSaving = true) }

            try {
                val userId = userPreferences.getCurrentUserId() ?: throw Exception("User not logged in")

                val transactionType = when (state.transactionType) {
                    FormTransactionType.INCOME -> TransactionEntity.TransactionType.INCOME
                    FormTransactionType.EXPENSE -> TransactionEntity.TransactionType.EXPENSE
                    FormTransactionType.TRANSFER -> TransactionEntity.TransactionType.TRANSFER
                }

                val entity = TransactionEntity(
                    id = if (state.isEditing) UUID.fromString(state.transactionId) else UUID.randomUUID(),
                    userId = UUID.fromString(userId),
                    amount = state.amount.toBigDecimal(),
                    type = transactionType,
                    description = state.description,
                    merchant = state.merchant.takeIf { it.isNotBlank() },
                    categoryId = state.selectedCategory?.let { UUID.fromString(it.id) },
                    bankAccountId = state.selectedAccount?.let { UUID.fromString(it.id) },
                    transactionDate = state.date.atStartOfDay(ZoneId.systemDefault()).toInstant().toEpochMilli(),
                    isRecurring = state.isRecurring,
                    tags = state.tags.takeIf { it.isNotBlank() },
                    syncStatus = TransactionEntity.SyncStatus.PENDING
                )

                transactionDao.insert(entity)

                _formState.update { it.copy(isSaving = false) }
                _formEvents.emit(TransactionFormEvent.SaveSuccess)
            } catch (e: Exception) {
                _formState.update { it.copy(isSaving = false) }
                _formEvents.emit(TransactionFormEvent.ShowError(e.message ?: "Failed to save transaction"))
            }
        }
    }

    /**
     * Delete a transaction.
     */
    fun deleteTransaction(transactionId: String) {
        viewModelScope.launch {
            try {
                transactionDao.deleteByIds(listOf(transactionId))
                _events.emit(TransactionsEvent.TransactionDeleted(transactionId))
                _formEvents.emit(TransactionFormEvent.DeleteSuccess)
            } catch (e: Exception) {
                _formEvents.emit(TransactionFormEvent.ShowError(e.message ?: "Failed to delete transaction"))
            }
        }
    }

    /**
     * Reset form state for new transaction.
     */
    fun resetForm() {
        _formState.value = TransactionFormState()
        loadCategories()
        loadAccounts()
    }

    private fun getCategoryIcon(categoryId: String?): ImageVector {
        return when (categoryId?.lowercase()) {
            "food", "dining", "restaurant" -> Icons.Default.Restaurant
            "groceries", "grocery" -> Icons.Default.ShoppingCart
            "transportation", "transport", "car" -> Icons.Default.DirectionsCar
            "utilities", "bills" -> Icons.Default.Power
            "entertainment" -> Icons.Default.Movie
            "shopping" -> Icons.Default.ShoppingBag
            "healthcare", "health", "medical" -> Icons.Default.LocalHospital
            "education" -> Icons.Default.School
            "travel" -> Icons.Default.Flight
            "housing", "home", "rent" -> Icons.Default.Home
            "salary", "income", "work" -> Icons.Default.Work
            "investment", "investments" -> Icons.Default.TrendingUp
            "gift", "gifts" -> Icons.Default.CardGiftcard
            "subscription", "subscriptions" -> Icons.Default.Subscriptions
            else -> Icons.Default.Receipt
        }
    }

    private fun getCategoryColor(categoryId: String?): Color {
        return when (categoryId?.lowercase()) {
            "food", "dining", "restaurant" -> Color(0xFFFF5722)
            "groceries", "grocery" -> Color(0xFF8BC34A)
            "transportation", "transport", "car" -> Color(0xFF2196F3)
            "utilities", "bills" -> Color(0xFF607D8B)
            "entertainment" -> Color(0xFF9C27B0)
            "shopping" -> Color(0xFFE91E63)
            "healthcare", "health", "medical" -> Color(0xFF4CAF50)
            "education" -> Color(0xFFFF9800)
            "travel" -> Color(0xFF00BCD4)
            "housing", "home", "rent" -> Color(0xFF795548)
            "salary", "income", "work" -> Color(0xFF4CAF50)
            "investment", "investments" -> Color(0xFF009688)
            else -> Color(0xFF9E9E9E)
        }
    }
}

/**
 * UI state for the transactions list screen.
 */
data class TransactionsUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val filteredTransactions: List<TransactionItemUiModel> = emptyList(),
    val groupedTransactions: Map<LocalDate, List<TransactionItemUiModel>> = emptyMap(),
    val totalIncome: BigDecimal = BigDecimal.ZERO,
    val totalExpenses: BigDecimal = BigDecimal.ZERO,
    val searchQuery: String = "",
    val selectedFilter: TransactionFilter = TransactionFilter.ALL,
    val sortOption: TransactionSortOption = TransactionSortOption.DATE_DESC,
    val dateRange: DateRange? = null,
    val selectedCategories: Set<String> = emptySet(),
    val amountRange: AmountRange? = null
)

/**
 * UI state for the transaction form screen.
 */
data class TransactionFormState(
    val transactionId: String? = null,
    val isEditing: Boolean = false,
    val transactionType: FormTransactionType = FormTransactionType.EXPENSE,
    val amount: String = "",
    val amountError: String? = null,
    val description: String = "",
    val descriptionError: String? = null,
    val merchant: String = "",
    val selectedCategory: CategoryUiModel? = null,
    val selectedAccount: AccountUiModel? = null,
    val date: LocalDate = LocalDate.now(),
    val isRecurring: Boolean = false,
    val recurringFrequency: RecurringFrequency = RecurringFrequency.MONTHLY,
    val recurringEndDate: LocalDate? = null,
    val tags: String = "",
    val notes: String = "",
    val availableCategories: List<CategoryUiModel> = emptyList(),
    val availableAccounts: List<AccountUiModel> = emptyList(),
    val isValid: Boolean = false,
    val isSaving: Boolean = false
)

/**
 * Events emitted by the transactions list.
 */
sealed class TransactionsEvent {
    data class NavigateToDetail(val transactionId: String) : TransactionsEvent()
    data class TransactionDeleted(val transactionId: String) : TransactionsEvent()
    data class ShowError(val message: String) : TransactionsEvent()
}
