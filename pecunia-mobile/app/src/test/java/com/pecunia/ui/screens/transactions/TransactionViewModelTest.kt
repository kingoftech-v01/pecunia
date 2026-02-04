package com.pecunia.ui.screens.transactions

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * Comprehensive unit tests for TransactionViewModel UI state models and types.
 * Since TransactionViewModel requires injected dependencies (SavedStateHandle,
 * TransactionRepository, CategoryRepository, use cases), we test the state
 * models, filter/sort types, validation logic, and form state.
 */
class TransactionViewModelTest {

    // ============================================
    // TransactionListUiState Tests
    // ============================================

    @Test
    fun `default TransactionListUiState has correct values`() {
        val state = TransactionListUiState()
        assertTrue(state.transactions.isEmpty())
        assertFalse(state.isLoading)
        assertFalse(state.isRefreshing)
        assertNull(state.error)
        assertEquals("", state.searchQuery)
        assertTrue(state.hasMorePages)
        assertEquals(0, state.currentPage)
        assertEquals(0.0, state.totalAmount, 0.01)
        assertEquals(0.0, state.incomeAmount, 0.01)
        assertEquals(0.0, state.expenseAmount, 0.01)
    }

    @Test
    fun `TransactionListUiState copy preserves unmodified fields`() {
        val state = TransactionListUiState(
            isLoading = true,
            searchQuery = "groceries",
            currentPage = 2
        )
        val updated = state.copy(isLoading = false)
        assertFalse(updated.isLoading)
        assertEquals("groceries", updated.searchQuery)
        assertEquals(2, updated.currentPage)
    }

    // ============================================
    // TransactionFilters Tests
    // ============================================

    @Test
    fun `default TransactionFilters has empty values`() {
        val filters = TransactionFilters()
        assertTrue(filters.types.isEmpty())
        assertTrue(filters.categoryIds.isEmpty())
        assertNull(filters.dateRange)
        assertNull(filters.minAmount)
        assertNull(filters.maxAmount)
        assertEquals(TransactionSortBy.DATE_DESC, filters.sortBy)
    }

    @Test
    fun `TransactionFilters with specific types`() {
        val filters = TransactionFilters(
            types = setOf(
                com.pecunia.domain.model.TransactionType.EXPENSE,
                com.pecunia.domain.model.TransactionType.INCOME
            )
        )
        assertEquals(2, filters.types.size)
    }

    @Test
    fun `TransactionFilters with amount range`() {
        val filters = TransactionFilters(
            minAmount = 10.0,
            maxAmount = 100.0
        )
        assertEquals(10.0, filters.minAmount!!, 0.01)
        assertEquals(100.0, filters.maxAmount!!, 0.01)
    }

    @Test
    fun `TransactionFilters with date range`() {
        val dateRange = DateRange(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 12, 31)
        )
        val filters = TransactionFilters(dateRange = dateRange)
        assertNotNull(filters.dateRange)
        assertEquals(LocalDate.of(2025, 1, 1), filters.dateRange!!.startDate)
        assertEquals(LocalDate.of(2025, 12, 31), filters.dateRange!!.endDate)
    }

    // ============================================
    // DateRange Tests
    // ============================================

    @Test
    fun `DateRange holds correct dates`() {
        val range = DateRange(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 6, 30)
        )
        assertEquals(LocalDate.of(2025, 1, 1), range.startDate)
        assertEquals(LocalDate.of(2025, 6, 30), range.endDate)
    }

    @Test
    fun `DateRange equality works`() {
        val range1 = DateRange(LocalDate.of(2025, 1, 1), LocalDate.of(2025, 12, 31))
        val range2 = DateRange(LocalDate.of(2025, 1, 1), LocalDate.of(2025, 12, 31))
        assertEquals(range1, range2)
    }

    // ============================================
    // TransactionSortBy Tests
    // ============================================

    @Test
    fun `TransactionSortBy has all expected values`() {
        val values = TransactionSortBy.entries
        assertEquals(5, values.size)
        assertTrue(values.contains(TransactionSortBy.DATE_DESC))
        assertTrue(values.contains(TransactionSortBy.DATE_ASC))
        assertTrue(values.contains(TransactionSortBy.AMOUNT_DESC))
        assertTrue(values.contains(TransactionSortBy.AMOUNT_ASC))
        assertTrue(values.contains(TransactionSortBy.CATEGORY))
    }

    // ============================================
    // TransactionDetailUiState Tests
    // ============================================

    @Test
    fun `default TransactionDetailUiState has correct values`() {
        val state = TransactionDetailUiState()
        assertNull(state.transaction)
        assertFalse(state.isLoading)
        assertNull(state.error)
        assertFalse(state.isDeleting)
        assertFalse(state.isDeleted)
        assertFalse(state.showDeleteConfirmation)
    }

    // ============================================
    // TransactionFormUiState Tests
    // ============================================

    @Test
    fun `default TransactionFormUiState has correct values`() {
        val state = TransactionFormUiState()
        assertNull(state.transactionId)
        assertFalse(state.isEditMode)
        assertEquals("", state.amount)
        assertNull(state.amountError)
        assertEquals(com.pecunia.domain.model.TransactionType.EXPENSE, state.type)
        assertNull(state.categoryId)
        assertNull(state.categoryError)
        assertEquals("", state.description)
        assertNull(state.descriptionError)
        assertEquals("", state.notes)
        assertTrue(state.attachments.isEmpty())
        assertTrue(state.tags.isEmpty())
        assertFalse(state.isRecurring)
        assertNull(state.recurringInterval)
        assertTrue(state.availableCategories.isEmpty())
        assertFalse(state.isLoading)
        assertFalse(state.isSaving)
        assertNull(state.error)
        assertFalse(state.isSaved)
        assertFalse(state.showCategoryPicker)
        assertFalse(state.showDatePicker)
        assertFalse(state.showTimePicker)
    }

    @Test
    fun `TransactionFormUiState in edit mode`() {
        val state = TransactionFormUiState(
            transactionId = "tx-123",
            isEditMode = true,
            amount = "50.00",
            description = "Grocery shopping"
        )
        assertEquals("tx-123", state.transactionId)
        assertTrue(state.isEditMode)
        assertEquals("50.00", state.amount)
        assertEquals("Grocery shopping", state.description)
    }

    @Test
    fun `TransactionFormUiState with validation errors`() {
        val state = TransactionFormUiState(
            amountError = "Amount is required",
            categoryError = "Category is required",
            descriptionError = "Description is required"
        )
        assertEquals("Amount is required", state.amountError)
        assertEquals("Category is required", state.categoryError)
        assertEquals("Description is required", state.descriptionError)
    }

    // ============================================
    // AttachmentUiModel Tests
    // ============================================

    @Test
    fun `AttachmentUiModel holds correct data`() {
        val attachment = AttachmentUiModel(
            id = "att-1",
            uri = "content://images/photo1",
            name = "receipt.jpg",
            type = AttachmentType.IMAGE,
            size = 1024L,
            thumbnailUri = "content://thumbs/photo1"
        )
        assertEquals("att-1", attachment.id)
        assertEquals("receipt.jpg", attachment.name)
        assertEquals(AttachmentType.IMAGE, attachment.type)
        assertEquals(1024L, attachment.size)
        assertNotNull(attachment.thumbnailUri)
    }

    @Test
    fun `AttachmentUiModel with null thumbnail`() {
        val attachment = AttachmentUiModel(
            id = "att-2",
            uri = "content://docs/doc1",
            name = "document.pdf",
            type = AttachmentType.PDF,
            size = 2048L
        )
        assertNull(attachment.thumbnailUri)
    }

    // ============================================
    // AttachmentType Tests
    // ============================================

    @Test
    fun `AttachmentType has all expected values`() {
        val values = AttachmentType.entries
        assertEquals(4, values.size)
        assertTrue(values.contains(AttachmentType.IMAGE))
        assertTrue(values.contains(AttachmentType.PDF))
        assertTrue(values.contains(AttachmentType.DOCUMENT))
        assertTrue(values.contains(AttachmentType.OTHER))
    }

    // ============================================
    // RecurringInterval Tests
    // ============================================

    @Test
    fun `RecurringInterval has all expected values`() {
        val values = RecurringInterval.entries
        assertEquals(6, values.size)
        assertTrue(values.contains(RecurringInterval.DAILY))
        assertTrue(values.contains(RecurringInterval.WEEKLY))
        assertTrue(values.contains(RecurringInterval.BIWEEKLY))
        assertTrue(values.contains(RecurringInterval.MONTHLY))
        assertTrue(values.contains(RecurringInterval.QUARTERLY))
        assertTrue(values.contains(RecurringInterval.YEARLY))
    }

    // ============================================
    // TransactionUiEvent Tests
    // ============================================

    @Test
    fun `TransactionUiEvent ShowSnackbar carries message`() {
        val event = TransactionUiEvent.ShowSnackbar("Transaction saved")
        assertEquals("Transaction saved", event.message)
    }

    @Test
    fun `TransactionUiEvent NavigateToDetail carries id`() {
        val event = TransactionUiEvent.NavigateToDetail("tx-1")
        assertEquals("tx-1", event.transactionId)
    }

    @Test
    fun `TransactionUiEvent NavigateToEdit carries id`() {
        val event = TransactionUiEvent.NavigateToEdit("tx-2")
        assertEquals("tx-2", event.transactionId)
    }

    // ============================================
    // FormValidationResult Tests
    // ============================================

    @Test
    fun `FormValidationResult valid with no errors`() {
        val result = FormValidationResult(isValid = true)
        assertTrue(result.isValid)
        assertNull(result.amountError)
        assertNull(result.categoryError)
        assertNull(result.descriptionError)
    }

    @Test
    fun `FormValidationResult invalid with all errors`() {
        val result = FormValidationResult(
            isValid = false,
            amountError = "Invalid amount",
            categoryError = "Category required",
            descriptionError = "Description required"
        )
        assertFalse(result.isValid)
        assertEquals("Invalid amount", result.amountError)
        assertEquals("Category required", result.categoryError)
        assertEquals("Description required", result.descriptionError)
    }

    @Test
    fun `FormValidationResult with partial errors`() {
        val result = FormValidationResult(
            isValid = false,
            amountError = "Invalid amount"
        )
        assertFalse(result.isValid)
        assertEquals("Invalid amount", result.amountError)
        assertNull(result.categoryError)
        assertNull(result.descriptionError)
    }
}
