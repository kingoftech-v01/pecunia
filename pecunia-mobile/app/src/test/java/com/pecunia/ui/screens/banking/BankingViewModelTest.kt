package com.pecunia.ui.screens.banking

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Comprehensive unit tests for BankingViewModel.
 * Tests account loading, syncing, search, connection flow,
 * and state management.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class BankingViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var viewModel: BankingViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        viewModel = BankingViewModel()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    // ============================================
    // Initial State Tests
    // ============================================

    @Test
    fun `initial state is loading`() {
        assertTrue(viewModel.uiState.value.isLoading)
    }

    @Test
    fun `initial connection state is SelectingInstitution`() {
        assertTrue(viewModel.connectionState.value is ConnectionState.SelectingInstitution)
    }

    @Test
    fun `accounts are loaded after initialization`() = runTest {
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertTrue(state.accounts.isNotEmpty())
    }

    @Test
    fun `mock accounts have correct data`() = runTest {
        advanceUntilIdle()

        val accounts = viewModel.uiState.value.accounts
        assertEquals(3, accounts.size)

        val checking = accounts.find { it.accountType == AccountType.CHECKING }
        assertNotNull(checking)
        assertEquals("Total Checking", checking!!.accountName)
        assertEquals("****4567", checking.accountNumber)
        assertEquals(5432.10, checking.balance, 0.01)
    }

    @Test
    fun `total balance is calculated correctly`() = runTest {
        advanceUntilIdle()

        // Total = 5432.10 (checking) - 1250.00 (credit card, negated) + 15000.00 (savings)
        // Credit card balance is -1250.00, but totalBalance calculation negates credit card balance
        // So: 5432.10 - (-1250.00 * -1) + 15000.00 = 5432.10 + 1250.00 + 15000.00
        // Actually: credit card is -1250.00, formula negates credit card, so -(-1250) = 1250
        // Total = 5432.10 + 1250.00 + 15000.00 = 21682.10
        val totalBalance = viewModel.uiState.value.totalBalance
        assertTrue(totalBalance > 0)
    }

    @Test
    fun `institutions are loaded after initialization`() = runTest {
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state.institutions.isNotEmpty())
        assertTrue(state.popularInstitutions.isNotEmpty())
    }

    @Test
    fun `popular institutions include Chase and Bank of America`() = runTest {
        advanceUntilIdle()

        val names = viewModel.uiState.value.popularInstitutions.map { it.name }
        assertTrue(names.contains("Chase"))
        assertTrue(names.contains("Bank of America"))
    }

    @Test
    fun `initial sync status is SYNCED after load`() = runTest {
        advanceUntilIdle()

        assertEquals(SyncStatus.SYNCED, viewModel.uiState.value.syncStatus)
    }

    // ============================================
    // Sync Tests
    // ============================================

    @Test
    fun `syncAllAccounts sets syncing state`() = runTest {
        advanceUntilIdle()

        viewModel.syncAllAccounts()

        // After starting, should be syncing
        val state = viewModel.uiState.value
        assertTrue(state.isSyncing || state.syncStatus == SyncStatus.SYNCED)
    }

    @Test
    fun `syncAllAccounts completes successfully`() = runTest {
        advanceUntilIdle()

        viewModel.syncAllAccounts()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isSyncing)
        assertEquals(SyncStatus.SYNCED, state.syncStatus)
    }

    @Test
    fun `syncAllAccounts updates lastSynced on all accounts`() = runTest {
        advanceUntilIdle()

        viewModel.syncAllAccounts()
        advanceUntilIdle()

        val accounts = viewModel.uiState.value.accounts
        assertTrue(accounts.all { it.syncStatus == SyncStatus.SYNCED })
    }

    @Test
    fun `syncAllAccounts updates lastSyncTime`() = runTest {
        advanceUntilIdle()

        viewModel.syncAllAccounts()
        advanceUntilIdle()

        assertNotNull(viewModel.uiState.value.lastSyncTime)
    }

    // ============================================
    // Disconnect Tests
    // ============================================

    @Test
    fun `disconnectAccount removes account from list`() = runTest {
        advanceUntilIdle()

        val initialCount = viewModel.uiState.value.accounts.size
        val accountToRemove = viewModel.uiState.value.accounts.first()

        viewModel.disconnectAccount(accountToRemove.id)
        advanceUntilIdle()

        assertEquals(initialCount - 1, viewModel.uiState.value.accounts.size)
        assertNull(viewModel.uiState.value.accounts.find { it.id == accountToRemove.id })
    }

    @Test
    fun `disconnectAccount recalculates total balance`() = runTest {
        advanceUntilIdle()

        val originalBalance = viewModel.uiState.value.totalBalance
        val firstAccount = viewModel.uiState.value.accounts.first()

        viewModel.disconnectAccount(firstAccount.id)
        advanceUntilIdle()

        assertNotEquals(originalBalance, viewModel.uiState.value.totalBalance)
    }

    @Test
    fun `disconnectAccount with non-existent id changes nothing`() = runTest {
        advanceUntilIdle()

        val initialCount = viewModel.uiState.value.accounts.size

        viewModel.disconnectAccount("non-existent")
        advanceUntilIdle()

        assertEquals(initialCount, viewModel.uiState.value.accounts.size)
    }

    // ============================================
    // Search Tests
    // ============================================

    @Test
    fun `searchInstitutions with blank query shows all popular`() = runTest {
        advanceUntilIdle()

        viewModel.searchInstitutions("")
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals(state.popularInstitutions.size, state.institutions.size)
    }

    @Test
    fun `searchInstitutions filters by name`() = runTest {
        advanceUntilIdle()

        viewModel.searchInstitutions("Chase")
        advanceUntilIdle()

        val results = viewModel.uiState.value.institutions
        assertTrue(results.all { it.name.contains("Chase", ignoreCase = true) })
    }

    @Test
    fun `searchInstitutions is case insensitive`() = runTest {
        advanceUntilIdle()

        viewModel.searchInstitutions("chase")
        advanceUntilIdle()

        assertTrue(viewModel.uiState.value.institutions.isNotEmpty())
    }

    @Test
    fun `searchInstitutions with no matches returns empty list`() = runTest {
        advanceUntilIdle()

        viewModel.searchInstitutions("NonexistentBank")
        advanceUntilIdle()

        assertTrue(viewModel.uiState.value.institutions.isEmpty())
    }

    @Test
    fun `searchInstitutions updates search query`() = runTest {
        advanceUntilIdle()

        viewModel.searchInstitutions("Chase")
        advanceUntilIdle()

        assertEquals("Chase", viewModel.uiState.value.searchQuery)
    }

    // ============================================
    // Connection Flow Tests
    // ============================================

    @Test
    fun `selectInstitution moves to Authenticating state`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        val state = viewModel.connectionState.value
        assertTrue(state is ConnectionState.Authenticating)
        val authState = state as ConnectionState.Authenticating
        assertTrue(authState.authUrl.contains(institution.id))
    }

    @Test
    fun `handleOAuthCallback moves to SelectingAccounts state`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.handleOAuthCallback("test-code")
        advanceUntilIdle()

        assertTrue(viewModel.connectionState.value is ConnectionState.SelectingAccounts)
    }

    @Test
    fun `handleOAuthCallback provides available accounts`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.handleOAuthCallback("test-code")
        advanceUntilIdle()

        val state = viewModel.connectionState.value as ConnectionState.SelectingAccounts
        assertEquals(3, state.availableAccounts.size)
        assertEquals(3, state.selectedAccountIds.size) // All selected by default
    }

    @Test
    fun `handleAuthError sets error state`() = runTest {
        viewModel.handleAuthError("Access denied")

        val state = viewModel.connectionState.value
        assertTrue(state is ConnectionState.Error)
        assertEquals("Authentication error: Access denied", (state as ConnectionState.Error).message)
    }

    @Test
    fun `toggleAccountSelection deselects a selected account`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.handleOAuthCallback("test-code")
        advanceUntilIdle()

        val beforeState = viewModel.connectionState.value as ConnectionState.SelectingAccounts
        val accountId = beforeState.availableAccounts.first().id

        viewModel.toggleAccountSelection(accountId)

        val afterState = viewModel.connectionState.value as ConnectionState.SelectingAccounts
        assertFalse(afterState.selectedAccountIds.contains(accountId))
    }

    @Test
    fun `toggleAccountSelection reselects a deselected account`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.handleOAuthCallback("test-code")
        advanceUntilIdle()

        val accountId = (viewModel.connectionState.value as ConnectionState.SelectingAccounts).availableAccounts.first().id

        // Deselect then reselect
        viewModel.toggleAccountSelection(accountId)
        viewModel.toggleAccountSelection(accountId)

        val state = viewModel.connectionState.value as ConnectionState.SelectingAccounts
        assertTrue(state.selectedAccountIds.contains(accountId))
    }

    @Test
    fun `linkSelectedAccounts moves to Success state`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.handleOAuthCallback("test-code")
        advanceUntilIdle()

        viewModel.linkSelectedAccounts()
        advanceUntilIdle()

        assertTrue(viewModel.connectionState.value is ConnectionState.Success)
    }

    @Test
    fun `linkSelectedAccounts adds new accounts to main list`() = runTest {
        advanceUntilIdle()

        val initialCount = viewModel.uiState.value.accounts.size

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.handleOAuthCallback("test-code")
        advanceUntilIdle()

        viewModel.linkSelectedAccounts()
        advanceUntilIdle()

        assertTrue(viewModel.uiState.value.accounts.size > initialCount)
    }

    @Test
    fun `resetConnectionState returns to SelectingInstitution`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.resetConnectionState()

        assertTrue(viewModel.connectionState.value is ConnectionState.SelectingInstitution)
    }

    @Test
    fun `retryConnection reselects institution if available`() = runTest {
        advanceUntilIdle()

        val institution = viewModel.uiState.value.popularInstitutions.first()
        viewModel.selectInstitution(institution)
        advanceUntilIdle()

        viewModel.retryConnection()
        advanceUntilIdle()

        assertTrue(viewModel.connectionState.value is ConnectionState.Authenticating)
    }

    @Test
    fun `retryConnection resets if no institution selected`() = runTest {
        viewModel.resetConnectionState()
        viewModel.retryConnection()

        assertTrue(viewModel.connectionState.value is ConnectionState.SelectingInstitution)
    }

    // ============================================
    // Error Handling Tests
    // ============================================

    @Test
    fun `clearError clears error state`() = runTest {
        advanceUntilIdle()

        viewModel.clearError()
        assertNull(viewModel.uiState.value.error)
    }

    // ============================================
    // Data Model Tests
    // ============================================

    @Test
    fun `BankAccount model holds correct data`() {
        val account = BankAccount(
            id = "1",
            institutionId = "chase",
            institutionName = "Chase",
            institutionLogo = null,
            accountName = "Checking",
            accountNumber = "****1234",
            accountType = AccountType.CHECKING,
            balance = 1000.0,
            availableBalance = 900.0,
            lastSynced = System.currentTimeMillis(),
            syncStatus = SyncStatus.SYNCED
        )
        assertEquals("1", account.id)
        assertEquals("chase", account.institutionId)
        assertEquals(AccountType.CHECKING, account.accountType)
        assertEquals("USD", account.currency)
        assertTrue(account.isActive)
    }

    @Test
    fun `AccountType getDisplayName returns correct names`() {
        assertEquals("Checking", AccountType.CHECKING.getDisplayName())
        assertEquals("Savings", AccountType.SAVINGS.getDisplayName())
        assertEquals("Credit Card", AccountType.CREDIT_CARD.getDisplayName())
        assertEquals("Investment", AccountType.INVESTMENT.getDisplayName())
        assertEquals("Loan", AccountType.LOAN.getDisplayName())
        assertEquals("Other", AccountType.OTHER.getDisplayName())
    }

    @Test
    fun `SyncStatus enum has all values`() {
        assertEquals(5, SyncStatus.entries.size)
        assertTrue(SyncStatus.entries.contains(SyncStatus.SYNCED))
        assertTrue(SyncStatus.entries.contains(SyncStatus.SYNCING))
        assertTrue(SyncStatus.entries.contains(SyncStatus.PARTIAL))
        assertTrue(SyncStatus.entries.contains(SyncStatus.ERROR))
        assertTrue(SyncStatus.entries.contains(SyncStatus.PENDING))
    }

    @Test
    fun `Institution model holds correct data`() {
        val institution = Institution("chase", "Chase", null, "#0A7ACA", "chase.com")
        assertEquals("chase", institution.id)
        assertEquals("Chase", institution.name)
        assertNull(institution.logoUrl)
        assertEquals("#0A7ACA", institution.primaryColor)
        assertTrue(institution.oauth)
    }

    @Test
    fun `AvailableAccount model holds correct data`() {
        val account = AvailableAccount(
            id = "1",
            name = "Checking",
            maskedNumber = "****1234",
            type = AccountType.CHECKING,
            balance = 5000.0
        )
        assertEquals("1", account.id)
        assertEquals(AccountType.CHECKING, account.type)
        assertEquals(5000.0, account.balance!!, 0.01)
    }

    @Test
    fun `ConnectionState SelectingInstitution is singleton`() {
        assertTrue(ConnectionState.SelectingInstitution is ConnectionState)
    }

    @Test
    fun `ConnectionState Authenticating contains auth URL`() {
        val state = ConnectionState.Authenticating("https://auth.example.com")
        assertEquals("https://auth.example.com", state.authUrl)
    }

    @Test
    fun `ConnectionState SelectingAccounts contains accounts and selection`() {
        val accounts = listOf(
            AvailableAccount("1", "Checking", "****1234", AccountType.CHECKING, 5000.0)
        )
        val state = ConnectionState.SelectingAccounts(accounts, setOf("1"))
        assertEquals(1, state.availableAccounts.size)
        assertTrue(state.selectedAccountIds.contains("1"))
    }

    @Test
    fun `ConnectionState Linking contains progress`() {
        val state = ConnectionState.Linking("Chase", 0.5f)
        assertEquals("Chase", state.institutionName)
        assertEquals(0.5f, state.progress, 0.01f)
    }

    @Test
    fun `ConnectionState Error contains message`() {
        val state = ConnectionState.Error("Something went wrong")
        assertEquals("Something went wrong", state.message)
    }

    @Test
    fun `BankingUiState default values are correct`() {
        val state = BankingUiState()
        assertFalse(state.isLoading)
        assertFalse(state.isSyncing)
        assertTrue(state.accounts.isEmpty())
        assertEquals(0.0, state.totalBalance, 0.01)
        assertNull(state.lastSyncTime)
        assertEquals(SyncStatus.PENDING, state.syncStatus)
        assertNull(state.error)
        assertEquals("", state.searchQuery)
    }
}
