package com.pecunia.ui.screens.banking

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Savings
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.pecunia.ui.screens.banking.components.BankAccountCard
import com.pecunia.ui.screens.banking.components.SyncStatusIndicator
import java.text.NumberFormat
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BankAccountsScreen(
    onNavigateBack: () -> Unit,
    onAddBank: () -> Unit,
    onAccountClick: (String) -> Unit,
    viewModel: BankingViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    var balanceVisible by remember { mutableStateOf(true) }

    val pullToRefreshState = rememberPullToRefreshState()
    val currencyFormat = remember { NumberFormat.getCurrencyInstance(Locale.US) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Connected Accounts") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { balanceVisible = !balanceVisible }) {
                        Icon(
                            imageVector = if (balanceVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                            contentDescription = if (balanceVisible) "Hide balances" else "Show balances"
                        )
                    }
                    IconButton(onClick = { viewModel.syncAllAccounts() }) {
                        val rotation by animateFloatAsState(
                            targetValue = if (uiState.isSyncing) 360f else 0f,
                            label = "syncRotation"
                        )
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Sync all",
                            modifier = Modifier.rotate(rotation)
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onAddBank,
                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                text = { Text("Add Bank") },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary
            )
        }
    ) { paddingValues ->
        PullToRefreshBox(
            isRefreshing = uiState.isSyncing,
            onRefresh = { viewModel.syncAllAccounts() },
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            state = pullToRefreshState
        ) {
            if (uiState.accounts.isEmpty() && !uiState.isLoading) {
                EmptyAccountsState(onAddBank = onAddBank)
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Total balance card
                    item {
                        TotalBalanceCard(
                            totalBalance = uiState.totalBalance,
                            accountCount = uiState.accounts.size,
                            lastSyncTime = uiState.lastSyncTime,
                            syncStatus = uiState.syncStatus,
                            balanceVisible = balanceVisible,
                            currencyFormat = currencyFormat
                        )
                    }

                    // Sync status banner
                    item {
                        AnimatedVisibility(
                            visible = uiState.syncStatus == SyncStatus.ERROR || uiState.syncStatus == SyncStatus.PARTIAL,
                            enter = fadeIn() + expandVertically(),
                            exit = fadeOut() + shrinkVertically()
                        ) {
                            SyncErrorBanner(
                                status = uiState.syncStatus,
                                onRetry = { viewModel.syncAllAccounts() }
                            )
                        }
                    }

                    // Group accounts by institution
                    val groupedAccounts = uiState.accounts.groupBy { it.institutionName }

                    groupedAccounts.forEach { (institutionName, accounts) ->
                        item {
                            Text(
                                text = institutionName,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(vertical = 8.dp)
                            )
                        }

                        items(
                            items = accounts,
                            key = { it.id }
                        ) { account ->
                            BankAccountCard(
                                account = account,
                                balanceVisible = balanceVisible,
                                onClick = { onAccountClick(account.id) },
                                onDisconnect = { viewModel.disconnectAccount(account.id) }
                            )
                        }
                    }

                    // Bottom spacing for FAB
                    item {
                        Spacer(modifier = Modifier.height(80.dp))
                    }
                }
            }

            // Loading overlay
            if (uiState.isLoading) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.8f)),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
        }
    }
}

@Composable
private fun TotalBalanceCard(
    totalBalance: Double,
    accountCount: Int,
    lastSyncTime: String?,
    syncStatus: SyncStatus,
    balanceVisible: Boolean,
    currencyFormat: NumberFormat
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primary,
                            MaterialTheme.colorScheme.tertiary
                        )
                    )
                )
                .padding(24.dp)
        ) {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Total Balance",
                        style = MaterialTheme.typography.titleMedium,
                        color = Color.White.copy(alpha = 0.9f)
                    )

                    SyncStatusIndicator(
                        status = syncStatus,
                        lastSyncTime = lastSyncTime
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = if (balanceVisible) currencyFormat.format(totalBalance) else "****",
                    style = MaterialTheme.typography.headlineLarge,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "$accountCount connected account${if (accountCount != 1) "s" else ""}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.8f)
                )

                Spacer(modifier = Modifier.height(16.dp))

                Row(
                    horizontalArrangement = Arrangement.spacedBy(24.dp)
                ) {
                    BalanceQuickStat(
                        icon = Icons.Default.TrendingUp,
                        label = "Assets",
                        value = if (balanceVisible) currencyFormat.format(totalBalance * 0.85) else "****"
                    )
                    BalanceQuickStat(
                        icon = Icons.Default.CreditCard,
                        label = "Liabilities",
                        value = if (balanceVisible) currencyFormat.format(totalBalance * 0.15) else "****"
                    )
                }
            }
        }
    }
}

@Composable
private fun BalanceQuickStat(
    icon: ImageVector,
    label: String,
    value: String
) {
    Row(
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(16.dp),
            tint = Color.White.copy(alpha = 0.8f)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Column {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = Color.White.copy(alpha = 0.7f)
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
        }
    }
}

@Composable
private fun SyncErrorBanner(
    status: SyncStatus,
    onRetry: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = when (status) {
            SyncStatus.ERROR -> MaterialTheme.colorScheme.errorContainer
            SyncStatus.PARTIAL -> Color(0xFFFFF3E0)
            else -> Color.Transparent
        },
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.Error,
                contentDescription = null,
                tint = when (status) {
                    SyncStatus.ERROR -> MaterialTheme.colorScheme.error
                    SyncStatus.PARTIAL -> Color(0xFFFF9800)
                    else -> Color.Transparent
                },
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = when (status) {
                        SyncStatus.ERROR -> "Sync Failed"
                        SyncStatus.PARTIAL -> "Partial Sync"
                        else -> ""
                    },
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = when (status) {
                        SyncStatus.ERROR -> "Unable to sync with your bank. Please try again."
                        SyncStatus.PARTIAL -> "Some accounts could not be synced."
                        else -> ""
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Button(
                onClick = onRetry,
                colors = ButtonDefaults.buttonColors(
                    containerColor = when (status) {
                        SyncStatus.ERROR -> MaterialTheme.colorScheme.error
                        SyncStatus.PARTIAL -> Color(0xFFFF9800)
                        else -> Color.Transparent
                    }
                ),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp)
            ) {
                Text("Retry")
            }
        }
    }
}

@Composable
private fun EmptyAccountsState(
    onAddBank: () -> Unit
) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(32.dp)
        ) {
            Surface(
                modifier = Modifier.size(100.dp),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Default.AccountBalance,
                        contentDescription = null,
                        modifier = Modifier.size(48.dp),
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "No Connected Accounts",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Connect your bank accounts to automatically track your transactions and balances.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )

            Spacer(modifier = Modifier.height(32.dp))

            Button(
                onClick = onAddBank,
                modifier = Modifier.fillMaxWidth(0.6f),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Connect Bank")
            }
        }
    }
}

// Data classes for banking
data class BankAccount(
    val id: String,
    val institutionId: String,
    val institutionName: String,
    val institutionLogo: String?,
    val accountName: String,
    val accountNumber: String, // Masked
    val accountType: AccountType,
    val balance: Double,
    val availableBalance: Double?,
    val currency: String = "USD",
    val lastSynced: Long,
    val syncStatus: SyncStatus = SyncStatus.SYNCED,
    val isActive: Boolean = true
)

enum class AccountType {
    CHECKING,
    SAVINGS,
    CREDIT_CARD,
    INVESTMENT,
    LOAN,
    OTHER;

    fun getIcon(): ImageVector = when (this) {
        CHECKING -> Icons.Default.AccountBalance
        SAVINGS -> Icons.Default.Savings
        CREDIT_CARD -> Icons.Default.CreditCard
        INVESTMENT -> Icons.Default.TrendingUp
        LOAN -> Icons.Default.AccountBalance
        OTHER -> Icons.Default.AccountBalance
    }

    fun getDisplayName(): String = when (this) {
        CHECKING -> "Checking"
        SAVINGS -> "Savings"
        CREDIT_CARD -> "Credit Card"
        INVESTMENT -> "Investment"
        LOAN -> "Loan"
        OTHER -> "Other"
    }
}

enum class SyncStatus {
    SYNCED,
    SYNCING,
    PARTIAL,
    ERROR,
    PENDING
}
