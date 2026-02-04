package com.pecunia.ui.screens.transactions

import com.pecunia.domain.model.Category
import com.pecunia.domain.model.Transaction
import com.pecunia.domain.model.TransactionType
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * UI State for Transaction List Screen
 */
data class TransactionListUiState(
    val transactions: Map<LocalDate, List<Transaction>> = emptyMap(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val searchQuery: String = "",
    val selectedFilters: TransactionFilters = TransactionFilters(),
    val hasMorePages: Boolean = true,
    val currentPage: Int = 0,
    val totalAmount: Double = 0.0,
    val incomeAmount: Double = 0.0,
    val expenseAmount: Double = 0.0
)

/**
 * Filter options for transactions
 */
data class TransactionFilters(
    val types: Set<TransactionType> = emptySet(),
    val categoryIds: Set<String> = emptySet(),
    val dateRange: DateRange? = null,
    val minAmount: Double? = null,
    val maxAmount: Double? = null,
    val sortBy: TransactionSortBy = TransactionSortBy.DATE_DESC
)

/**
 * Date range for filtering
 */
data class DateRange(
    val startDate: LocalDate,
    val endDate: LocalDate
)

/**
 * Sort options for transactions
 */
enum class TransactionSortBy {
    DATE_DESC,
    DATE_ASC,
    AMOUNT_DESC,
    AMOUNT_ASC,
    CATEGORY
}

/**
 * UI State for Transaction Detail Screen
 */
data class TransactionDetailUiState(
    val transaction: Transaction? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
    val isDeleting: Boolean = false,
    val isDeleted: Boolean = false,
    val showDeleteConfirmation: Boolean = false
)

/**
 * UI State for Transaction Form Screen
 */
data class TransactionFormUiState(
    val transactionId: String? = null,
    val isEditMode: Boolean = false,
    val amount: String = "",
    val amountError: String? = null,
    val type: TransactionType = TransactionType.EXPENSE,
    val categoryId: String? = null,
    val categoryError: String? = null,
    val description: String = "",
    val descriptionError: String? = null,
    val date: LocalDate = LocalDate.now(),
    val time: LocalDateTime = LocalDateTime.now(),
    val notes: String = "",
    val attachments: List<AttachmentUiModel> = emptyList(),
    val tags: List<String> = emptyList(),
    val isRecurring: Boolean = false,
    val recurringInterval: RecurringInterval? = null,
    val availableCategories: List<Category> = emptyList(),
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val error: String? = null,
    val isSaved: Boolean = false,
    val showCategoryPicker: Boolean = false,
    val showDatePicker: Boolean = false,
    val showTimePicker: Boolean = false
)

/**
 * Attachment UI model
 */
data class AttachmentUiModel(
    val id: String,
    val uri: String,
    val name: String,
    val type: AttachmentType,
    val size: Long,
    val thumbnailUri: String? = null
)

/**
 * Attachment types
 */
enum class AttachmentType {
    IMAGE,
    PDF,
    DOCUMENT,
    OTHER
}

/**
 * Recurring transaction intervals
 */
enum class RecurringInterval {
    DAILY,
    WEEKLY,
    BIWEEKLY,
    MONTHLY,
    QUARTERLY,
    YEARLY
}

/**
 * UI Events for Transaction screens
 */
sealed class TransactionUiEvent {
    data class ShowSnackbar(val message: String) : TransactionUiEvent()
    data class NavigateToDetail(val transactionId: String) : TransactionUiEvent()
    object NavigateToForm : TransactionUiEvent()
    data class NavigateToEdit(val transactionId: String) : TransactionUiEvent()
    object NavigateBack : TransactionUiEvent()
    object TransactionSaved : TransactionUiEvent()
    object TransactionDeleted : TransactionUiEvent()
}

/**
 * Form validation result
 */
data class FormValidationResult(
    val isValid: Boolean,
    val amountError: String? = null,
    val categoryError: String? = null,
    val descriptionError: String? = null
)
