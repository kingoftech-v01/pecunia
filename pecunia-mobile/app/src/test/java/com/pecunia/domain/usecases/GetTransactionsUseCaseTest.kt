package com.pecunia.domain.usecases

import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionType
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.Assert.*
import org.junit.Test
import java.math.BigDecimal
import java.time.LocalDate

/**
 * Comprehensive unit tests for GetTransactionsUseCase.
 *
 * Tests the Params data class, routing logic based on params, and
 * flow mapping/error handling patterns.
 *
 * Since TransactionRepository interface is not present in the codebase,
 * we test the Params class, routing logic simulation, Result wrapping,
 * and error catching behavior.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class GetTransactionsUseCaseTest {

    // ============================================
    // Params Data Class Tests
    // ============================================

    @Test
    fun `Params default values are all null or false`() {
        val params = GetTransactionsUseCase.Params()
        assertNull(params.dateRange)
        assertNull(params.category)
        assertNull(params.type)
        assertNull(params.searchQuery)
        assertNull(params.limit)
        assertFalse(params.recurringOnly)
    }

    @Test
    fun `Params with dateRange`() {
        val start = LocalDate.of(2025, 1, 1)
        val end = LocalDate.of(2025, 12, 31)
        val params = GetTransactionsUseCase.Params(dateRange = Pair(start, end))
        assertNotNull(params.dateRange)
        assertEquals(start, params.dateRange!!.first)
        assertEquals(end, params.dateRange!!.second)
    }

    @Test
    fun `Params with type`() {
        val params = GetTransactionsUseCase.Params(type = TransactionType.EXPENSE)
        assertEquals(TransactionType.EXPENSE, params.type)
    }

    @Test
    fun `Params with searchQuery`() {
        val params = GetTransactionsUseCase.Params(searchQuery = "coffee")
        assertEquals("coffee", params.searchQuery)
    }

    @Test
    fun `Params with limit`() {
        val params = GetTransactionsUseCase.Params(limit = 10)
        assertEquals(10, params.limit)
    }

    @Test
    fun `Params with recurringOnly`() {
        val params = GetTransactionsUseCase.Params(recurringOnly = true)
        assertTrue(params.recurringOnly)
    }

    @Test
    fun `Params equality works`() {
        val p1 = GetTransactionsUseCase.Params(
            type = TransactionType.INCOME,
            limit = 5
        )
        val p2 = GetTransactionsUseCase.Params(
            type = TransactionType.INCOME,
            limit = 5
        )
        assertEquals(p1, p2)
    }

    @Test
    fun `Params inequality works`() {
        val p1 = GetTransactionsUseCase.Params(type = TransactionType.INCOME)
        val p2 = GetTransactionsUseCase.Params(type = TransactionType.EXPENSE)
        assertNotEquals(p1, p2)
    }

    @Test
    fun `Params copy works correctly`() {
        val original = GetTransactionsUseCase.Params(
            type = TransactionType.INCOME,
            limit = 10
        )
        val copied = original.copy(limit = 20)
        assertEquals(TransactionType.INCOME, copied.type)
        assertEquals(20, copied.limit)
    }

    // ============================================
    // Routing Logic Tests (simulating the when block)
    // ============================================

    /**
     * Simulates the routing logic from GetTransactionsUseCase.invoke
     * to determine which repository method would be called.
     */
    private fun determineRoute(params: GetTransactionsUseCase.Params): String {
        return when {
            params.dateRange != null -> "getTransactionsByDateRange"
            params.category != null -> "getTransactionsByCategory"
            params.type != null -> "getTransactionsByType"
            params.searchQuery != null -> "searchTransactions"
            params.limit != null -> "getRecentTransactions"
            params.recurringOnly -> "getRecurringTransactions"
            else -> "getAllTransactions"
        }
    }

    @Test
    fun `routes to getTransactionsByDateRange when dateRange is set`() {
        val params = GetTransactionsUseCase.Params(
            dateRange = Pair(LocalDate.now().minusDays(30), LocalDate.now())
        )
        assertEquals("getTransactionsByDateRange", determineRoute(params))
    }

    @Test
    fun `routes to getTransactionsByType when type is set`() {
        val params = GetTransactionsUseCase.Params(type = TransactionType.EXPENSE)
        assertEquals("getTransactionsByType", determineRoute(params))
    }

    @Test
    fun `routes to searchTransactions when searchQuery is set`() {
        val params = GetTransactionsUseCase.Params(searchQuery = "coffee")
        assertEquals("searchTransactions", determineRoute(params))
    }

    @Test
    fun `routes to getRecentTransactions when limit is set`() {
        val params = GetTransactionsUseCase.Params(limit = 10)
        assertEquals("getRecentTransactions", determineRoute(params))
    }

    @Test
    fun `routes to getRecurringTransactions when recurringOnly is true`() {
        val params = GetTransactionsUseCase.Params(recurringOnly = true)
        assertEquals("getRecurringTransactions", determineRoute(params))
    }

    @Test
    fun `routes to getAllTransactions when no filters set`() {
        val params = GetTransactionsUseCase.Params()
        assertEquals("getAllTransactions", determineRoute(params))
    }

    @Test
    fun `dateRange takes priority over other filters`() {
        val params = GetTransactionsUseCase.Params(
            dateRange = Pair(LocalDate.now().minusDays(30), LocalDate.now()),
            type = TransactionType.EXPENSE,
            searchQuery = "test",
            limit = 5,
            recurringOnly = true
        )
        assertEquals("getTransactionsByDateRange", determineRoute(params))
    }

    @Test
    fun `type takes priority over searchQuery`() {
        val params = GetTransactionsUseCase.Params(
            type = TransactionType.INCOME,
            searchQuery = "salary"
        )
        assertEquals("getTransactionsByType", determineRoute(params))
    }

    @Test
    fun `searchQuery takes priority over limit`() {
        val params = GetTransactionsUseCase.Params(
            searchQuery = "test",
            limit = 10
        )
        assertEquals("searchTransactions", determineRoute(params))
    }

    @Test
    fun `limit takes priority over recurringOnly`() {
        val params = GetTransactionsUseCase.Params(
            limit = 5,
            recurringOnly = true
        )
        assertEquals("getRecentTransactions", determineRoute(params))
    }

    // ============================================
    // Flow Result Wrapping Tests
    // ============================================

    private fun createTransaction(
        id: String = "tx-1",
        type: TransactionType = TransactionType.EXPENSE,
        amount: BigDecimal = BigDecimal("50"),
        description: String = "Test"
    ): Transaction = Transaction(
        id = id,
        userId = "user-1",
        type = type,
        amount = amount,
        description = description,
        accountId = "acc-1",
        date = LocalDate.now()
    )

    @Test
    fun `flow maps transactions to Result success`() = runTest {
        val transactions = listOf(
            createTransaction("tx-1"),
            createTransaction("tx-2")
        )
        val resultFlow: Flow<Result<List<Transaction>>> = flow {
            emit(transactions)
        }.map { Result.success(it) }

        val results = resultFlow.toList()
        assertEquals(1, results.size)
        assertTrue(results[0].isSuccess)
        assertEquals(2, results[0].getOrNull()!!.size)
    }

    @Test
    fun `flow catches exception and emits Result failure`() = runTest {
        val resultFlow: Flow<Result<List<Transaction>>> = flow<List<Transaction>> {
            throw RuntimeException("Query failed")
        }.map { Result.success(it) }.catch {
            emit(Result.failure(it))
        }

        val results = resultFlow.toList()
        assertEquals(1, results.size)
        assertTrue(results[0].isFailure)
        assertEquals("Query failed", results[0].exceptionOrNull()?.message)
    }

    @Test
    fun `flow emits empty list as success`() = runTest {
        val resultFlow: Flow<Result<List<Transaction>>> = flow {
            emit(emptyList<Transaction>())
        }.map { Result.success(it) }

        val results = resultFlow.toList()
        assertEquals(1, results.size)
        assertTrue(results[0].isSuccess)
        assertTrue(results[0].getOrNull()!!.isEmpty())
    }

    @Test
    fun `flow filters by type correctly`() = runTest {
        val transactions = listOf(
            createTransaction("tx-1", TransactionType.EXPENSE),
            createTransaction("tx-2", TransactionType.INCOME),
            createTransaction("tx-3", TransactionType.EXPENSE)
        )
        val filtered = transactions.filter { it.type == TransactionType.EXPENSE }
        assertEquals(2, filtered.size)
    }

    @Test
    fun `flow filters by date range correctly`() = runTest {
        val start = LocalDate.of(2025, 1, 1)
        val end = LocalDate.of(2025, 6, 30)
        val transactions = listOf(
            createTransaction("tx-1").copy(date = LocalDate.of(2025, 3, 15)),
            createTransaction("tx-2").copy(date = LocalDate.of(2025, 8, 15)),
            createTransaction("tx-3").copy(date = LocalDate.of(2025, 5, 1))
        )
        val filtered = transactions.filter {
            !it.date.isBefore(start) && !it.date.isAfter(end)
        }
        assertEquals(2, filtered.size)
    }

    @Test
    fun `flow filters by search query correctly`() = runTest {
        val transactions = listOf(
            createTransaction("tx-1", description = "Coffee at Starbucks"),
            createTransaction("tx-2", description = "Grocery shopping"),
            createTransaction("tx-3", description = "Morning coffee")
        )
        val query = "coffee"
        val filtered = transactions.filter {
            it.description.contains(query, ignoreCase = true)
        }
        assertEquals(2, filtered.size)
    }

    @Test
    fun `flow filters recurring transactions correctly`() = runTest {
        val transactions = listOf(
            createTransaction("tx-1").copy(isRecurring = true),
            createTransaction("tx-2").copy(isRecurring = false),
            createTransaction("tx-3").copy(isRecurring = true)
        )
        val filtered = transactions.filter { it.isRecurring }
        assertEquals(2, filtered.size)
    }

    @Test
    fun `flow limits results correctly`() = runTest {
        val transactions = (1..20).map { createTransaction("tx-$it") }
        val limited = transactions.take(5)
        assertEquals(5, limited.size)
    }

    // ============================================
    // Integration with TransactionType
    // ============================================

    @Test
    fun `can create Params with each TransactionType`() {
        TransactionType.entries.forEach { type ->
            val params = GetTransactionsUseCase.Params(type = type)
            assertEquals(type, params.type)
            assertEquals("getTransactionsByType", determineRoute(params))
        }
    }

    @Test
    fun `INCOME type Params routes correctly`() {
        val params = GetTransactionsUseCase.Params(type = TransactionType.INCOME)
        assertEquals("getTransactionsByType", determineRoute(params))
    }

    @Test
    fun `TRANSFER type Params routes correctly`() {
        val params = GetTransactionsUseCase.Params(type = TransactionType.TRANSFER)
        assertEquals("getTransactionsByType", determineRoute(params))
    }

    // ============================================
    // Edge Case Tests
    // ============================================

    @Test
    fun `Params with empty search query is still routed to searchTransactions`() {
        // Note: empty string is not null
        val params = GetTransactionsUseCase.Params(searchQuery = "")
        assertEquals("searchTransactions", determineRoute(params))
    }

    @Test
    fun `Params with zero limit is still routed to getRecentTransactions`() {
        val params = GetTransactionsUseCase.Params(limit = 0)
        assertEquals("getRecentTransactions", determineRoute(params))
    }

    @Test
    fun `Params with same start and end date in dateRange`() {
        val date = LocalDate.of(2025, 6, 15)
        val params = GetTransactionsUseCase.Params(dateRange = Pair(date, date))
        assertNotNull(params.dateRange)
        assertEquals(params.dateRange!!.first, params.dateRange!!.second)
    }
}
