package com.pecunia.ui.screens.banking

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import javax.inject.Inject

@HiltViewModel
class BankingViewModel @Inject constructor(
    // TODO: Inject actual repositories
    // private val bankingRepository: BankingRepository,
    // private val plaidService: PlaidService
) : ViewModel() {

    private val _uiState = MutableStateFlow(BankingUiState())
    val uiState: StateFlow<BankingUiState> = _uiState.asStateFlow()

    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.SelectingInstitution)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private var selectedInstitution: Institution? = null

    init {
        loadAccounts()
        loadInstitutions()
    }

    private fun loadAccounts() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }

            try {
                // TODO: Replace with actual repository call
                // val accounts = bankingRepository.getLinkedAccounts()
                delay(500) // Simulated network delay

                // Mock data
                val mockAccounts = listOf(
                    BankAccount(
                        id = "1",
                        institutionId = "chase",
                        institutionName = "Chase",
                        institutionLogo = null,
                        accountName = "Total Checking",
                        accountNumber = "****4567",
                        accountType = AccountType.CHECKING,
                        balance = 5432.10,
                        availableBalance = 5232.10,
                        lastSynced = System.currentTimeMillis() - 3600000,
                        syncStatus = SyncStatus.SYNCED
                    ),
                    BankAccount(
                        id = "2",
                        institutionId = "chase",
                        institutionName = "Chase",
                        institutionLogo = null,
                        accountName = "Sapphire Reserve",
                        accountNumber = "****8901",
                        accountType = AccountType.CREDIT_CARD,
                        balance = -1250.00,
                        availableBalance = 23750.00,
                        lastSynced = System.currentTimeMillis() - 3600000,
                        syncStatus = SyncStatus.SYNCED
                    ),
                    BankAccount(
                        id = "3",
                        institutionId = "bofa",
                        institutionName = "Bank of America",
                        institutionLogo = null,
                        accountName = "Advantage Savings",
                        accountNumber = "****2345",
                        accountType = AccountType.SAVINGS,
                        balance = 15000.00,
                        availableBalance = 15000.00,
                        lastSynced = System.currentTimeMillis() - 7200000,
                        syncStatus = SyncStatus.SYNCED
                    )
                )

                // Credit cards are liabilities; negate their balance in net worth calculation.
                val totalBalance = mockAccounts.sumOf {
                    if (it.accountType == AccountType.CREDIT_CARD) -it.balance else it.balance
                }

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        accounts = mockAccounts,
                        totalBalance = totalBalance,
                        lastSyncTime = formatLastSyncTime(mockAccounts.minOfOrNull { acc -> acc.lastSynced }),
                        syncStatus = SyncStatus.SYNCED
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error loading accounts", e)
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = "Failed to load accounts: ${e.message}"
                    )
                }
            }
        }
    }

    private fun loadInstitutions() {
        viewModelScope.launch {
            // Mock popular institutions
            val popularInstitutions = listOf(
                Institution("chase", "Chase", null, "#0A7ACA", "chase.com"),
                Institution("bofa", "Bank of America", null, "#012169", "bankofamerica.com"),
                Institution("wells", "Wells Fargo", null, "#D71E28", "wellsfargo.com"),
                Institution("citi", "Citibank", null, "#003B70", "citi.com"),
                Institution("usbank", "US Bank", null, "#0032A0", "usbank.com"),
                Institution("pnc", "PNC Bank", null, "#FF5F00", "pnc.com"),
                Institution("capital", "Capital One", null, "#D03027", "capitalone.com"),
                Institution("td", "TD Bank", null, "#34B233", "td.com"),
                Institution("schwab", "Charles Schwab", null, "#00A3E0", "schwab.com")
            )

            _uiState.update {
                it.copy(
                    popularInstitutions = popularInstitutions,
                    institutions = popularInstitutions
                )
            }
        }
    }

    fun syncAllAccounts() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSyncing = true, syncStatus = SyncStatus.SYNCING) }

            try {
                // TODO: Replace with actual sync call
                // bankingRepository.syncAllAccounts()
                delay(2000) // Simulated network delay

                val updatedAccounts = _uiState.value.accounts.map { account ->
                    account.copy(
                        lastSynced = System.currentTimeMillis(),
                        syncStatus = SyncStatus.SYNCED
                    )
                }

                _uiState.update {
                    it.copy(
                        isSyncing = false,
                        accounts = updatedAccounts,
                        lastSyncTime = formatLastSyncTime(System.currentTimeMillis()),
                        syncStatus = SyncStatus.SYNCED
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error syncing accounts", e)
                _uiState.update {
                    it.copy(
                        isSyncing = false,
                        syncStatus = SyncStatus.ERROR,
                        error = "Failed to sync accounts: ${e.message}"
                    )
                }
            }
        }
    }

    fun disconnectAccount(accountId: String) {
        viewModelScope.launch {
            try {
                // TODO: Replace with actual disconnect call
                // bankingRepository.disconnectAccount(accountId)
                delay(500)

                val updatedAccounts = _uiState.value.accounts.filterNot { it.id == accountId }
                val totalBalance = updatedAccounts.sumOf {
                    if (it.accountType == AccountType.CREDIT_CARD) -it.balance else it.balance
                }

                _uiState.update {
                    it.copy(
                        accounts = updatedAccounts,
                        totalBalance = totalBalance
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error disconnecting account", e)
                _uiState.update {
                    it.copy(error = "Failed to disconnect account: ${e.message}")
                }
            }
        }
    }

    fun searchInstitutions(query: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(searchQuery = query, isSearchingInstitutions = true) }

            if (query.isBlank()) {
                _uiState.update {
                    it.copy(
                        institutions = it.popularInstitutions,
                        isSearchingInstitutions = false
                    )
                }
                return@launch
            }

            delay(300) // Debounce

            // TODO: Replace with actual search
            // val results = plaidService.searchInstitutions(query)
            val results = _uiState.value.popularInstitutions.filter {
                it.name.contains(query, ignoreCase = true)
            }

            _uiState.update {
                it.copy(
                    institutions = results,
                    isSearchingInstitutions = false
                )
            }
        }
    }

    fun selectInstitution(institution: Institution) {
        selectedInstitution = institution
        viewModelScope.launch {
            try {
                // TODO: Get actual OAuth URL from Plaid
                // val linkToken = plaidService.createLinkToken(institution.id)
                // val authUrl = plaidService.getOAuthUrl(linkToken)

                val authUrl = "https://auth.plaid.com/oauth/${institution.id}?client=pecunia"

                _connectionState.value = ConnectionState.Authenticating(authUrl)
            } catch (e: Exception) {
                Log.e(TAG, "Error starting OAuth flow", e)
                _connectionState.value = ConnectionState.Error("Failed to start authentication: ${e.message}")
            }
        }
    }

    fun handleOAuthCallback(code: String) {
        viewModelScope.launch {
            try {
                // TODO: Exchange code for access token
                // val accessToken = plaidService.exchangeToken(code)
                // val accounts = plaidService.getAccounts(accessToken)

                delay(500) // Simulated network delay

                // Mock available accounts
                val availableAccounts = listOf(
                    AvailableAccount(
                        id = "new_1",
                        name = "Checking Account",
                        maskedNumber = "****1234",
                        type = AccountType.CHECKING,
                        balance = 3500.00
                    ),
                    AvailableAccount(
                        id = "new_2",
                        name = "Savings Account",
                        maskedNumber = "****5678",
                        type = AccountType.SAVINGS,
                        balance = 10000.00
                    ),
                    AvailableAccount(
                        id = "new_3",
                        name = "Credit Card",
                        maskedNumber = "****9012",
                        type = AccountType.CREDIT_CARD,
                        balance = -500.00
                    )
                )

                _connectionState.value = ConnectionState.SelectingAccounts(
                    availableAccounts = availableAccounts,
                    selectedAccountIds = availableAccounts.map { it.id }.toSet()
                )
            } catch (e: Exception) {
                Log.e(TAG, "Error handling OAuth callback", e)
                _connectionState.value = ConnectionState.Error("Authentication failed: ${e.message}")
            }
        }
    }

    fun handleAuthError(error: String) {
        _connectionState.value = ConnectionState.Error("Authentication error: $error")
    }

    fun toggleAccountSelection(accountId: String) {
        val currentState = _connectionState.value
        if (currentState is ConnectionState.SelectingAccounts) {
            val newSelection = if (currentState.selectedAccountIds.contains(accountId)) {
                currentState.selectedAccountIds - accountId
            } else {
                currentState.selectedAccountIds + accountId
            }
            _connectionState.value = currentState.copy(selectedAccountIds = newSelection)
        }
    }

    fun linkSelectedAccounts() {
        val currentState = _connectionState.value
        if (currentState !is ConnectionState.SelectingAccounts) return

        val institution = selectedInstitution ?: return

        viewModelScope.launch {
            _connectionState.value = ConnectionState.Linking(
                institutionName = institution.name,
                progress = 0f
            )

            try {
                // Simulate linking progress
                for (i in 1..10) {
                    delay(200)
                    _connectionState.value = ConnectionState.Linking(
                        institutionName = institution.name,
                        progress = i / 10f
                    )
                }

                // TODO: Actually link accounts
                // val linkedAccounts = bankingRepository.linkAccounts(
                //     institutionId = institution.id,
                //     accountIds = currentState.selectedAccountIds.toList()
                // )

                // Mock linked accounts
                val linkedAccounts = currentState.availableAccounts
                    .filter { currentState.selectedAccountIds.contains(it.id) }
                    .map { available ->
                        BankAccount(
                            id = UUID.randomUUID().toString(),
                            institutionId = institution.id,
                            institutionName = institution.name,
                            institutionLogo = institution.logoUrl,
                            accountName = available.name,
                            accountNumber = available.maskedNumber,
                            accountType = available.type,
                            balance = available.balance ?: 0.0,
                            availableBalance = available.balance,
                            lastSynced = System.currentTimeMillis(),
                            syncStatus = SyncStatus.SYNCED
                        )
                    }

                // Update accounts list
                val updatedAccounts = _uiState.value.accounts + linkedAccounts
                val totalBalance = updatedAccounts.sumOf {
                    if (it.accountType == AccountType.CREDIT_CARD) -it.balance else it.balance
                }

                _uiState.update {
                    it.copy(
                        accounts = updatedAccounts,
                        totalBalance = totalBalance
                    )
                }

                _connectionState.value = ConnectionState.Success(linkedAccounts)
            } catch (e: Exception) {
                Log.e(TAG, "Error linking accounts", e)
                _connectionState.value = ConnectionState.Error("Failed to link accounts: ${e.message}")
            }
        }
    }

    fun resetConnectionState() {
        selectedInstitution = null
        _connectionState.value = ConnectionState.SelectingInstitution
    }

    fun retryConnection() {
        selectedInstitution?.let { selectInstitution(it) }
            ?: run { resetConnectionState() }
    }

    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }

    private fun formatLastSyncTime(timestamp: Long?): String? {
        if (timestamp == null) return null

        val now = System.currentTimeMillis()
        val diff = now - timestamp

        return when {
            diff < 60000 -> "Just now"
            diff < 3600000 -> "${diff / 60000} min ago"
            diff < 86400000 -> "${diff / 3600000} hours ago"
            else -> SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()).format(Date(timestamp))
        }
    }

    companion object {
        private const val TAG = "BankingViewModel"
    }
}

data class BankingUiState(
    val isLoading: Boolean = false,
    val isSyncing: Boolean = false,
    val accounts: List<BankAccount> = emptyList(),
    val totalBalance: Double = 0.0,
    val lastSyncTime: String? = null,
    val syncStatus: SyncStatus = SyncStatus.PENDING,
    val error: String? = null,

    // Institution search
    val searchQuery: String = "",
    val institutions: List<Institution> = emptyList(),
    val popularInstitutions: List<Institution> = emptyList(),
    val recentInstitutions: List<Institution> = emptyList(),
    val isSearchingInstitutions: Boolean = false
)
