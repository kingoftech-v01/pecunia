package com.pecunia.ui.screens.transactions

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.time.LocalDate

/**
 * Comprehensive unit tests for TransactionsViewModel UI state models and types.
 * Since TransactionsViewModel requires injected DAOs (TransactionDao, CategoryDao,
 * BankAccountDao, UserPreferences), we test the state models, filtering types,
 * date range computation, and validation logic as defined in the ViewModel.
 */
class TransactionsViewModelTest {

    // ============================================
    // TransactionListUiState Default Values
    // ============================================

    @Test
    fun `default TransactionListUiState values are correct`() {
        val state = TransactionListUiState()
        assertTrue(state.transactions.isEmpty())
        assertFalse(state.isLoading)
        assertFalse(state.isRefreshing)
        assertNull(state.error)
        assertEquals("", state.searchQuery)
        assertTrue(state.hasMorePages)
        assertEquals(0, state.currentPage)
    }

    @Test
    fun `TransactionListUiState with data`() {
        val state = TransactionListUiState(
            isLoading = false,
            searchQuery = "coffee",
            currentPage = 3,
            hasMorePages = false,
            totalAmount = 500.0,
            incomeAmount = 1000.0,
            expenseAmount = 500.0
        )
        assertEquals("coffee", state.searchQuery)
        assertEquals(3, state.currentPage)
        assertFalse(state.hasMorePages)
        assertEquals(500.0, state.totalAmount, 0.01)
    }

    // ============================================
    // Filter and Sort Types
    // ============================================

    @Test
    fun `TransactionSortBy DATE_DESC is default`() {
        val filters = TransactionFilters()
        assertEquals(TransactionSortBy.DATE_DESC, filters.sortBy)
    }

    @Test
    fun `TransactionSortBy all values exist`() {
        assertEquals(5, TransactionSortBy.entries.size)
    }

    @Test
    fun `TransactionFilters with category filter`() {
        val filters = TransactionFilters(
            categoryIds = setOf("cat-1", "cat-2", "cat-3")
        )
        assertEquals(3, filters.categoryIds.size)
        assertTrue(filters.categoryIds.contains("cat-1"))
        assertTrue(filters.categoryIds.contains("cat-2"))
        assertTrue(filters.categoryIds.contains("cat-3"))
    }

    @Test
    fun `TransactionFilters with all properties set`() {
        val filters = TransactionFilters(
            types = setOf(com.pecunia.domain.model.TransactionType.EXPENSE),
            categoryIds = setOf("cat-1"),
            dateRange = DateRange(LocalDate.of(2025, 1, 1), LocalDate.of(2025, 6, 30)),
            minAmount = 5.0,
            maxAmount = 500.0,
            sortBy = TransactionSortBy.AMOUNT_DESC
        )
        assertEquals(1, filters.types.size)
        assertEquals(1, filters.categoryIds.size)
        assertNotNull(filters.dateRange)
        assertEquals(5.0, filters.minAmount!!, 0.01)
        assertEquals(500.0, filters.maxAmount!!, 0.01)
        assertEquals(TransactionSortBy.AMOUNT_DESC, filters.sortBy)
    }

    // ============================================
    // DateRange Tests
    // ============================================

    @Test
    fun `DateRange startDate is before endDate`() {
        val range = DateRange(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 12, 31)
        )
        assertTrue(range.startDate.isBefore(range.endDate))
    }

    @Test
    fun `DateRange same start and end date`() {
        val date = LocalDate.of(2025, 6, 15)
        val range = DateRange(startDate = date, endDate = date)
        assertEquals(range.startDate, range.endDate)
    }

    // ============================================
    // TransactionDetailUiState Tests
    // ============================================

    @Test
    fun `TransactionDetailUiState default values`() {
        val state = TransactionDetailUiState()
        assertNull(state.transaction)
        assertFalse(state.isLoading)
        assertNull(state.error)
        assertFalse(state.isDeleting)
        assertFalse(state.isDeleted)
        assertFalse(state.showDeleteConfirmation)
    }

    @Test
    fun `TransactionDetailUiState with delete confirmation shown`() {
        val state = TransactionDetailUiState(showDeleteConfirmation = true)
        assertTrue(state.showDeleteConfirmation)
    }

    @Test
    fun `TransactionDetailUiState with error`() {
        val state = TransactionDetailUiState(
            isLoading = false,
            error = "Transaction not found"
        )
        assertEquals("Transaction not found", state.error)
    }

    @Test
    fun `TransactionDetailUiState when deleted`() {
        val state = TransactionDetailUiState(isDeleted = true)
        assertTrue(state.isDeleted)
    }

    // ============================================
    // TransactionFormUiState Tests
    // ============================================

    @Test
    fun `TransactionFormUiState date defaults to today`() {
        val state = TransactionFormUiState()
        assertEquals(LocalDate.now(), state.date)
    }

    @Test
    fun `TransactionFormUiState type defaults to EXPENSE`() {
        val state = TransactionFormUiState()
        assertEquals(com.pecunia.domain.model.TransactionType.EXPENSE, state.type)
    }

    @Test
    fun `TransactionFormUiState edit mode set correctly`() {
        val state = TransactionFormUiState(
            transactionId = "tx-100",
            isEditMode = true,
            amount = "25.50",
            description = "Coffee"
        )
        assertTrue(state.isEditMode)
        assertEquals("tx-100", state.transactionId)
        assertEquals("25.50", state.amount)
        assertEquals("Coffee", state.description)
    }

    @Test
    fun `TransactionFormUiState recurring settings`() {
        val state = TransactionFormUiState(
            isRecurring = true,
            recurringInterval = RecurringInterval.MONTHLY
        )
        assertTrue(state.isRecurring)
        assertEquals(RecurringInterval.MONTHLY, state.recurringInterval)
    }

    @Test
    fun `TransactionFormUiState with attachments`() {
        val attachments = listOf(
            AttachmentUiModel("1", "uri1", "receipt.jpg", AttachmentType.IMAGE, 1024),
            AttachmentUiModel("2", "uri2", "doc.pdf", AttachmentType.PDF, 2048)
        )
        val state = TransactionFormUiState(attachments = attachments)
        assertEquals(2, state.attachments.size)
    }

    @Test
    fun `TransactionFormUiState with tags`() {
        val state = TransactionFormUiState(tags = listOf("food", "lunch", "work"))
        assertEquals(3, state.tags.size)
        assertTrue(state.tags.contains("food"))
        assertTrue(state.tags.contains("lunch"))
        assertTrue(state.tags.contains("work"))
    }

    @Test
    fun `TransactionFormUiState dialog state toggles`() {
        val state = TransactionFormUiState(
            showCategoryPicker = true,
            showDatePicker = false,
            showTimePicker = true
        )
        assertTrue(state.showCategoryPicker)
        assertFalse(state.showDatePicker)
        assertTrue(state.showTimePicker)
    }

    // ============================================
    // TransactionUiEvent Tests
    // ============================================

    @Test
    fun `TransactionUiEvent NavigateToForm is singleton`() {
        assertSame(TransactionUiEvent.NavigateToForm, TransactionUiEvent.NavigateToForm)
    }

    @Test
    fun `TransactionUiEvent NavigateBack is singleton`() {
        assertSame(TransactionUiEvent.NavigateBack, TransactionUiEvent.NavigateBack)
    }

    @Test
    fun `TransactionUiEvent TransactionSaved is singleton`() {
        assertSame(TransactionUiEvent.TransactionSaved, TransactionUiEvent.TransactionSaved)
    }

    @Test
    fun `TransactionUiEvent TransactionDeleted is singleton`() {
        assertSame(TransactionUiEvent.TransactionDeleted, TransactionUiEvent.TransactionDeleted)
    }

    // ============================================
    // FormValidationResult Tests
    // ============================================

    @Test
    fun `valid FormValidationResult`() {
        val result = FormValidationResult(isValid = true)
        assertTrue(result.isValid)
        assertNull(result.amountError)
        assertNull(result.categoryError)
        assertNull(result.descriptionError)
    }

    @Test
    fun `invalid FormValidationResult with multiple errors`() {
        val result = FormValidationResult(
            isValid = false,
            amountError = "Required",
            descriptionError = "Too short"
        )
        assertFalse(result.isValid)
        assertEquals("Required", result.amountError)
        assertNull(result.categoryError)
        assertEquals("Too short", result.descriptionError)
    }

    @Test
    fun `FormValidationResult equality works`() {
        val r1 = FormValidationResult(isValid = true)
        val r2 = FormValidationResult(isValid = true)
        assertEquals(r1, r2)
    }

    @Test
    fun `FormValidationResult inequality on isValid`() {
        val r1 = FormValidationResult(isValid = true)
        val r2 = FormValidationResult(isValid = false)
        assertNotEquals(r1, r2)
    }
}
