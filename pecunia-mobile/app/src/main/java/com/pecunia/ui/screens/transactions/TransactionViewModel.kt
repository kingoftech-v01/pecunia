package com.pecunia.ui.screens.transactions

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pecunia.domain.model.Category
import com.pecunia.domain.model.Transaction
import com.pecunia.domain.model.TransactionType
import com.pecunia.domain.repository.CategoryRepository
import com.pecunia.domain.repository.TransactionRepository
import com.pecunia.domain.usecase.CreateTransactionUseCase
import com.pecunia.domain.usecase.DeleteTransactionUseCase
import com.pecunia.domain.usecase.GetTransactionsUseCase
import com.pecunia.domain.usecase.UpdateTransactionUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalDateTime
import java.util.UUID
import javax.inject.Inject

@OptIn(FlowPreview::class, ExperimentalCoroutinesApi::class)
@HiltViewModel
class TransactionViewModel @Inject constructor(
    private val savedStateHandle: SavedStateHandle,
    private val transactionRepository: TransactionRepository,
    private val categoryRepository: CategoryRepository,
    private val getTransactionsUseCase: GetTransactionsUseCase,
    private val createTransactionUseCase: CreateTransactionUseCase,
    private val updateTransactionUseCase: UpdateTransactionUseCase,
    private val deleteTransactionUseCase: DeleteTransactionUseCase
) : ViewModel() {

    companion object {
        private const val PAGE_SIZE = 20
        private const val SEARCH_DEBOUNCE_MS = 300L
    }

    // Transaction List State
    private val _listState = MutableStateFlow(TransactionListUiState())
    val listState: StateFlow<TransactionListUiState> = _listState.asStateFlow()

    // Transaction Detail State
    private val _detailState = MutableStateFlow(TransactionDetailUiState())
    val detailState: StateFlow<TransactionDetailUiState> = _detailState.asStateFlow()

    // Transaction Form State
    private val _formState = MutableStateFlow(TransactionFormUiState())
    val formState: StateFlow<TransactionFormUiState> = _formState.asStateFlow()

    // UI Events
    private val _uiEvent = Channel<TransactionUiEvent>()
    val uiEvent = _uiEvent.receiveAsFlow()

    // Search query flow for debouncing
    private val searchQueryFlow = MutableStateFlow("")

    init {
        setupSearchDebounce()
        loadTransactions()
        loadCategories()
    }

    private fun setupSearchDebounce() {
        // debounce waits for typing pause; distinctUntilChanged skips duplicate queries;
        // collectLatest cancels in-flight searches when new query arrives.
        viewModelScope.launch {
            searchQueryFlow
                .debounce(SEARCH_DEBOUNCE_MS)
                .distinctUntilChanged()
                .collectLatest { query ->
                    _listState.update { it.copy(searchQuery = query, currentPage = 0) }
                    loadTransactions(reset = true)
                }
        }
    }

    // ==================== List Operations ====================

    fun loadTransactions(reset: Boolean = false) {
        viewModelScope.launch {
            if (reset) {
                _listState.update { it.copy(currentPage = 0, transactions = emptyMap()) }
            }

            _listState.update { it.copy(isLoading = _listState.value.transactions.isEmpty()) }

            try {
                val filters = _listState.value.selectedFilters
                val searchQuery = _listState.value.searchQuery
                val page = _listState.value.currentPage

                getTransactionsUseCase(
                    searchQuery = searchQuery.takeIf { it.isNotBlank() },
                    types = filters.types.toList().takeIf { it.isNotEmpty() },
                    categoryIds = filters.categoryIds.toList().takeIf { it.isNotEmpty() },
                    startDate = filters.dateRange?.startDate,
                    endDate = filters.dateRange?.endDate,
                    minAmount = filters.minAmount,
                    maxAmount = filters.maxAmount,
                    page = page,
                    pageSize = PAGE_SIZE,
                    sortBy = filters.sortBy
                ).collect { result ->
                    result.fold(
                        onSuccess = { transactions ->
                            val grouped = groupTransactionsByDate(transactions)
                            val currentTransactions = if (reset) emptyMap() else _listState.value.transactions
                            val mergedTransactions = mergeTransactionMaps(currentTransactions, grouped)

                            val totals = calculateTotals(mergedTransactions.values.flatten())

                            _listState.update {
                                it.copy(
                                    transactions = mergedTransactions,
                                    isLoading = false,
                                    isRefreshing = false,
                                    error = null,
                                    hasMorePages = transactions.size == PAGE_SIZE,
                                    totalAmount = totals.total,
                                    incomeAmount = totals.income,
                                    expenseAmount = totals.expense
                                )
                            }
                        },
                        onFailure = { error ->
                            _listState.update {
                                it.copy(
                                    isLoading = false,
                                    isRefreshing = false,
                                    error = error.message ?: "Unknown error occurred"
                                )
                            }
                        }
                    )
                }
            } catch (e: Exception) {
                _listState.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = e.message ?: "Unknown error occurred"
                    )
                }
            }
        }
    }

    fun refreshTransactions() {
        _listState.update { it.copy(isRefreshing = true) }
        loadTransactions(reset = true)
    }

    fun loadMoreTransactions() {
        if (_listState.value.isLoading || !_listState.value.hasMorePages) return

        _listState.update { it.copy(currentPage = it.currentPage + 1) }
        loadTransactions()
    }

    fun onSearchQueryChange(query: String) {
        searchQueryFlow.value = query
    }

    fun updateFilters(filters: TransactionFilters) {
        _listState.update { it.copy(selectedFilters = filters, currentPage = 0) }
        loadTransactions(reset = true)
    }

    fun clearFilters() {
        updateFilters(TransactionFilters())
    }

    fun toggleTypeFilter(type: TransactionType) {
        val currentFilters = _listState.value.selectedFilters
        val newTypes = if (currentFilters.types.contains(type)) {
            currentFilters.types - type
        } else {
            currentFilters.types + type
        }
        updateFilters(currentFilters.copy(types = newTypes))
    }

    fun toggleCategoryFilter(categoryId: String) {
        val currentFilters = _listState.value.selectedFilters
        val newCategories = if (currentFilters.categoryIds.contains(categoryId)) {
            currentFilters.categoryIds - categoryId
        } else {
            currentFilters.categoryIds + categoryId
        }
        updateFilters(currentFilters.copy(categoryIds = newCategories))
    }

    fun setDateRangeFilter(dateRange: DateRange?) {
        val currentFilters = _listState.value.selectedFilters
        updateFilters(currentFilters.copy(dateRange = dateRange))
    }

    fun setSortBy(sortBy: TransactionSortBy) {
        val currentFilters = _listState.value.selectedFilters
        updateFilters(currentFilters.copy(sortBy = sortBy))
    }

    fun deleteTransaction(transactionId: String) {
        viewModelScope.launch {
            try {
                deleteTransactionUseCase(transactionId).collect { result ->
                    result.fold(
                        onSuccess = {
                            // Remove from local list
                            val updatedTransactions = _listState.value.transactions.mapValues { (_, transactions) ->
                                transactions.filter { it.id != transactionId }
                            }.filterValues { it.isNotEmpty() }

                            _listState.update { it.copy(transactions = updatedTransactions) }
                            _uiEvent.send(TransactionUiEvent.ShowSnackbar("Transaction deleted"))
                        },
                        onFailure = { error ->
                            _uiEvent.send(TransactionUiEvent.ShowSnackbar(error.message ?: "Failed to delete"))
                        }
                    )
                }
            } catch (e: Exception) {
                _uiEvent.send(TransactionUiEvent.ShowSnackbar(e.message ?: "Failed to delete"))
            }
        }
    }

    // ==================== Detail Operations ====================

    fun loadTransactionDetail(transactionId: String) {
        viewModelScope.launch {
            _detailState.update { it.copy(isLoading = true, error = null) }

            try {
                transactionRepository.getTransactionById(transactionId).collect { result ->
                    result.fold(
                        onSuccess = { transaction ->
                            _detailState.update {
                                it.copy(
                                    transaction = transaction,
                                    isLoading = false,
                                    error = null
                                )
                            }
                        },
                        onFailure = { error ->
                            _detailState.update {
                                it.copy(
                                    isLoading = false,
                                    error = error.message ?: "Failed to load transaction"
                                )
                            }
                        }
                    )
                }
            } catch (e: Exception) {
                _detailState.update {
                    it.copy(
                        isLoading = false,
                        error = e.message ?: "Failed to load transaction"
                    )
                }
            }
        }
    }

    fun showDeleteConfirmation() {
        _detailState.update { it.copy(showDeleteConfirmation = true) }
    }

    fun hideDeleteConfirmation() {
        _detailState.update { it.copy(showDeleteConfirmation = false) }
    }

    fun confirmDeleteTransaction() {
        val transactionId = _detailState.value.transaction?.id ?: return

        viewModelScope.launch {
            _detailState.update { it.copy(isDeleting = true, showDeleteConfirmation = false) }

            try {
                deleteTransactionUseCase(transactionId).collect { result ->
                    result.fold(
                        onSuccess = {
                            _detailState.update { it.copy(isDeleting = false, isDeleted = true) }
                            _uiEvent.send(TransactionUiEvent.TransactionDeleted)
                        },
                        onFailure = { error ->
                            _detailState.update {
                                it.copy(
                                    isDeleting = false,
                                    error = error.message ?: "Failed to delete"
                                )
                            }
                        }
                    )
                }
            } catch (e: Exception) {
                _detailState.update {
                    it.copy(
                        isDeleting = false,
                        error = e.message ?: "Failed to delete"
                    )
                }
            }
        }
    }

    // ==================== Form Operations ====================

    fun initFormForCreate() {
        _formState.update {
            TransactionFormUiState(
                isEditMode = false,
                date = LocalDate.now(),
                time = LocalDateTime.now(),
                availableCategories = it.availableCategories
            )
        }
    }

    fun initFormForEdit(transactionId: String) {
        viewModelScope.launch {
            _formState.update { it.copy(isLoading = true, isEditMode = true, transactionId = transactionId) }

            try {
                transactionRepository.getTransactionById(transactionId).collect { result ->
                    result.fold(
                        onSuccess = { transaction ->
                            _formState.update {
                                it.copy(
                                    isLoading = false,
                                    amount = transaction.amount.toString(),
                                    type = transaction.type,
                                    categoryId = transaction.categoryId,
                                    description = transaction.description,
                                    date = transaction.date.toLocalDate(),
                                    time = transaction.date,
                                    notes = transaction.notes ?: "",
                                    tags = transaction.tags,
                                    isRecurring = transaction.isRecurring,
                                    recurringInterval = transaction.recurringInterval?.let { interval ->
                                        RecurringInterval.valueOf(interval)
                                    }
                                )
                            }
                        },
                        onFailure = { error ->
                            _formState.update {
                                it.copy(
                                    isLoading = false,
                                    error = error.message ?: "Failed to load transaction"
                                )
                            }
                        }
                    )
                }
            } catch (e: Exception) {
                _formState.update {
                    it.copy(
                        isLoading = false,
                        error = e.message ?: "Failed to load transaction"
                    )
                }
            }
        }
    }

    private fun loadCategories() {
        viewModelScope.launch {
            try {
                categoryRepository.getAllCategories().collect { result ->
                    result.fold(
                        onSuccess = { categories ->
                            _formState.update { it.copy(availableCategories = categories) }
                        },
                        onFailure = { /* Ignore category loading errors */ }
                    )
                }
            } catch (e: Exception) {
                // Ignore category loading errors
            }
        }
    }

    fun onAmountChange(amount: String) {
        // Only allow valid numeric input
        val filtered = amount.filter { it.isDigit() || it == '.' }
        val dotCount = filtered.count { it == '.' }
        if (dotCount <= 1) {
            _formState.update { it.copy(amount = filtered, amountError = null) }
        }
    }

    fun onTypeChange(type: TransactionType) {
        _formState.update { it.copy(type = type) }
    }

    fun onCategorySelect(categoryId: String) {
        _formState.update { it.copy(categoryId = categoryId, categoryError = null, showCategoryPicker = false) }
    }

    fun onDescriptionChange(description: String) {
        _formState.update { it.copy(description = description, descriptionError = null) }
    }

    fun onDateChange(date: LocalDate) {
        _formState.update { it.copy(date = date, showDatePicker = false) }
    }

    fun onTimeChange(time: LocalDateTime) {
        _formState.update { it.copy(time = time, showTimePicker = false) }
    }

    fun onNotesChange(notes: String) {
        _formState.update { it.copy(notes = notes) }
    }

    fun onRecurringChange(isRecurring: Boolean) {
        _formState.update {
            it.copy(
                isRecurring = isRecurring,
                recurringInterval = if (isRecurring) RecurringInterval.MONTHLY else null
            )
        }
    }

    fun onRecurringIntervalChange(interval: RecurringInterval) {
        _formState.update { it.copy(recurringInterval = interval) }
    }

    fun addAttachment(attachment: AttachmentUiModel) {
        _formState.update { it.copy(attachments = it.attachments + attachment) }
    }

    fun removeAttachment(attachmentId: String) {
        _formState.update { it.copy(attachments = it.attachments.filter { a -> a.id != attachmentId }) }
    }

    fun addTag(tag: String) {
        if (tag.isNotBlank() && !_formState.value.tags.contains(tag)) {
            _formState.update { it.copy(tags = it.tags + tag.trim()) }
        }
    }

    fun removeTag(tag: String) {
        _formState.update { it.copy(tags = it.tags - tag) }
    }

    fun showCategoryPicker() {
        _formState.update { it.copy(showCategoryPicker = true) }
    }

    fun hideCategoryPicker() {
        _formState.update { it.copy(showCategoryPicker = false) }
    }

    fun showDatePicker() {
        _formState.update { it.copy(showDatePicker = true) }
    }

    fun hideDatePicker() {
        _formState.update { it.copy(showDatePicker = false) }
    }

    fun showTimePicker() {
        _formState.update { it.copy(showTimePicker = true) }
    }

    fun hideTimePicker() {
        _formState.update { it.copy(showTimePicker = false) }
    }

    fun validateAndSave() {
        val state = _formState.value
        val validation = validateForm(state)

        if (!validation.isValid) {
            _formState.update {
                it.copy(
                    amountError = validation.amountError,
                    categoryError = validation.categoryError,
                    descriptionError = validation.descriptionError
                )
            }
            return
        }

        saveTransaction()
    }

    private fun validateForm(state: TransactionFormUiState): FormValidationResult {
        var amountError: String? = null
        var categoryError: String? = null
        var descriptionError: String? = null

        // Validate amount
        val amount = state.amount.toDoubleOrNull()
        if (amount == null || amount <= 0) {
            amountError = "Please enter a valid amount"
        }

        // Validate category
        if (state.categoryId.isNullOrBlank()) {
            categoryError = "Please select a category"
        }

        // Validate description
        if (state.description.isBlank()) {
            descriptionError = "Please enter a description"
        }

        val isValid = amountError == null && categoryError == null && descriptionError == null

        return FormValidationResult(isValid, amountError, categoryError, descriptionError)
    }

    private fun saveTransaction() {
        val state = _formState.value

        viewModelScope.launch {
            _formState.update { it.copy(isSaving = true, error = null) }

            try {
                val amount = state.amount.toDouble()
                val dateTime = LocalDateTime.of(
                    state.date,
                    state.time.toLocalTime()
                )

                val transaction = Transaction(
                    id = state.transactionId ?: UUID.randomUUID().toString(),
                    amount = amount,
                    type = state.type,
                    categoryId = state.categoryId!!,
                    description = state.description,
                    date = dateTime,
                    notes = state.notes.takeIf { it.isNotBlank() },
                    tags = state.tags,
                    isRecurring = state.isRecurring,
                    recurringInterval = state.recurringInterval?.name,
                    attachmentUrls = state.attachments.map { it.uri },
                    createdAt = LocalDateTime.now(),
                    updatedAt = LocalDateTime.now()
                )

                val result = if (state.isEditMode) {
                    updateTransactionUseCase(transaction)
                } else {
                    createTransactionUseCase(transaction)
                }

                result.collect { saveResult ->
                    saveResult.fold(
                        onSuccess = {
                            _formState.update { it.copy(isSaving = false, isSaved = true) }
                            _uiEvent.send(TransactionUiEvent.TransactionSaved)
                        },
                        onFailure = { error ->
                            _formState.update {
                                it.copy(
                                    isSaving = false,
                                    error = error.message ?: "Failed to save transaction"
                                )
                            }
                        }
                    )
                }
            } catch (e: Exception) {
                _formState.update {
                    it.copy(
                        isSaving = false,
                        error = e.message ?: "Failed to save transaction"
                    )
                }
            }
        }
    }

    fun clearFormError() {
        _formState.update { it.copy(error = null) }
    }

    // ==================== Helper Functions ====================

    private fun groupTransactionsByDate(transactions: List<Transaction>): Map<LocalDate, List<Transaction>> {
        return transactions.groupBy { it.date.toLocalDate() }
            .toSortedMap(compareByDescending { it })
    }

    private fun mergeTransactionMaps(
        existing: Map<LocalDate, List<Transaction>>,
        new: Map<LocalDate, List<Transaction>>
    ): Map<LocalDate, List<Transaction>> {
        val merged = existing.toMutableMap()
        new.forEach { (date, transactions) ->
            val existingTransactions = merged[date] ?: emptyList()
            val existingIds = existingTransactions.map { it.id }.toSet()
            val newTransactions = transactions.filter { it.id !in existingIds }
            merged[date] = existingTransactions + newTransactions
        }
        return merged.toSortedMap(compareByDescending { it })
    }

    private data class TransactionTotals(
        val total: Double,
        val income: Double,
        val expense: Double
    )

    private fun calculateTotals(transactions: List<Transaction>): TransactionTotals {
        var income = 0.0
        var expense = 0.0

        transactions.forEach { transaction ->
            when (transaction.type) {
                TransactionType.INCOME -> income += transaction.amount
                TransactionType.EXPENSE -> expense += transaction.amount
                TransactionType.TRANSFER -> { /* Transfers don't affect totals */ }
            }
        }

        return TransactionTotals(
            total = income - expense,
            income = income,
            expense = expense
        )
    }
}
