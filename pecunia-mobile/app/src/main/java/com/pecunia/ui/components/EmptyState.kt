package com.pecunia.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AccountBalanceWallet
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.FilterList
import androidx.compose.material.icons.outlined.Inbox
import androidx.compose.material.icons.outlined.PieChart
import androidx.compose.material.icons.outlined.Receipt
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.TrendingUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.pecunia.ui.theme.PecuniaTheme

/**
 * Empty state types for different contexts
 */
enum class EmptyStateType {
    NO_TRANSACTIONS,
    NO_BUDGETS,
    NO_SEARCH_RESULTS,
    NO_FILTER_RESULTS,
    NO_REPORTS,
    NO_ACCOUNTS,
    GENERIC
}

/**
 * Get default configuration for empty state type
 */
private fun getEmptyStateConfig(type: EmptyStateType): EmptyStateConfig {
    return when (type) {
        EmptyStateType.NO_TRANSACTIONS -> EmptyStateConfig(
            icon = Icons.Outlined.Receipt,
            title = "No transactions yet",
            description = "Start tracking your spending by adding your first transaction.",
            actionText = "Add Transaction"
        )
        EmptyStateType.NO_BUDGETS -> EmptyStateConfig(
            icon = Icons.Outlined.PieChart,
            title = "No budgets set up",
            description = "Create budgets to track your spending in different categories.",
            actionText = "Create Budget"
        )
        EmptyStateType.NO_SEARCH_RESULTS -> EmptyStateConfig(
            icon = Icons.Outlined.Search,
            title = "No results found",
            description = "Try adjusting your search terms or check for typos.",
            actionText = "Clear Search"
        )
        EmptyStateType.NO_FILTER_RESULTS -> EmptyStateConfig(
            icon = Icons.Outlined.FilterList,
            title = "No matching transactions",
            description = "No transactions match the current filters. Try adjusting your filters.",
            actionText = "Clear Filters"
        )
        EmptyStateType.NO_REPORTS -> EmptyStateConfig(
            icon = Icons.Outlined.TrendingUp,
            title = "No reports available",
            description = "Add some transactions to generate spending reports and insights.",
            actionText = "Add Transaction"
        )
        EmptyStateType.NO_ACCOUNTS -> EmptyStateConfig(
            icon = Icons.Outlined.AccountBalanceWallet,
            title = "No accounts added",
            description = "Add your bank accounts or wallets to start tracking your finances.",
            actionText = "Add Account"
        )
        EmptyStateType.GENERIC -> EmptyStateConfig(
            icon = Icons.Outlined.Inbox,
            title = "Nothing here yet",
            description = "This section is empty. Check back later or add some content.",
            actionText = null
        )
    }
}

/**
 * Configuration data class for empty state
 */
data class EmptyStateConfig(
    val icon: ImageVector,
    val title: String,
    val description: String,
    val actionText: String?
)

/**
 * Empty state placeholder component
 *
 * @param type The type of empty state to display
 * @param modifier Modifier for the component
 * @param onActionClick Callback when the action button is clicked
 * @param customIcon Custom icon to override the default
 * @param customTitle Custom title to override the default
 * @param customDescription Custom description to override the default
 * @param customActionText Custom action text to override the default
 * @param showAction Whether to show the action button
 */
@Composable
fun EmptyState(
    type: EmptyStateType,
    modifier: Modifier = Modifier,
    onActionClick: (() -> Unit)? = null,
    customIcon: ImageVector? = null,
    customTitle: String? = null,
    customDescription: String? = null,
    customActionText: String? = null,
    showAction: Boolean = true
) {
    val config = getEmptyStateConfig(type)

    val icon = customIcon ?: config.icon
    val title = customTitle ?: config.title
    val description = customDescription ?: config.description
    val actionText = customActionText ?: config.actionText

    EmptyStateContent(
        icon = icon,
        title = title,
        description = description,
        actionText = if (showAction) actionText else null,
        onActionClick = onActionClick,
        modifier = modifier
    )
}

/**
 * Custom empty state with full control over content
 */
@Composable
fun EmptyState(
    icon: ImageVector,
    title: String,
    description: String,
    modifier: Modifier = Modifier,
    actionText: String? = null,
    onActionClick: (() -> Unit)? = null,
    secondaryActionText: String? = null,
    onSecondaryActionClick: (() -> Unit)? = null
) {
    EmptyStateContent(
        icon = icon,
        title = title,
        description = description,
        actionText = actionText,
        onActionClick = onActionClick,
        secondaryActionText = secondaryActionText,
        onSecondaryActionClick = onSecondaryActionClick,
        modifier = modifier
    )
}

/**
 * Internal composable for empty state content
 */
@Composable
private fun EmptyStateContent(
    icon: ImageVector,
    title: String,
    description: String,
    modifier: Modifier = Modifier,
    actionText: String? = null,
    onActionClick: (() -> Unit)? = null,
    secondaryActionText: String? = null,
    onSecondaryActionClick: (() -> Unit)? = null
) {
    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Icon
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(80.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Title
            Text(
                text = title,
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Description
            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 16.dp)
            )

            // Action buttons
            if (actionText != null && onActionClick != null) {
                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = onActionClick,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Icon(
                        imageVector = Icons.Outlined.Add,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    Text(text = actionText)
                }
            }

            if (secondaryActionText != null && onSecondaryActionClick != null) {
                Spacer(modifier = Modifier.height(8.dp))

                TextButton(onClick = onSecondaryActionClick) {
                    Text(text = secondaryActionText)
                }
            }
        }
    }
}

/**
 * Compact empty state for smaller spaces (e.g., within cards)
 */
@Composable
fun EmptyStateCompact(
    icon: ImageVector,
    message: String,
    modifier: Modifier = Modifier,
    actionText: String? = null,
    onActionClick: (() -> Unit)? = null
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(48.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )

        if (actionText != null && onActionClick != null) {
            Spacer(modifier = Modifier.height(12.dp))

            OutlinedButton(
                onClick = onActionClick,
                modifier = Modifier.height(36.dp)
            ) {
                Text(
                    text = actionText,
                    style = MaterialTheme.typography.labelMedium
                )
            }
        }
    }
}

/**
 * Inline empty state for lists (minimal design)
 */
@Composable
fun EmptyStateInline(
    message: String,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 32.dp, horizontal = 16.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
            textAlign = TextAlign.Center
        )
    }
}

@Preview(showBackground = true, heightDp = 400)
@Composable
private fun EmptyStateNoTransactionsPreview() {
    PecuniaTheme {
        EmptyState(
            type = EmptyStateType.NO_TRANSACTIONS,
            onActionClick = {}
        )
    }
}

@Preview(showBackground = true, heightDp = 400)
@Composable
private fun EmptyStateNoBudgetsPreview() {
    PecuniaTheme {
        EmptyState(
            type = EmptyStateType.NO_BUDGETS,
            onActionClick = {}
        )
    }
}

@Preview(showBackground = true, heightDp = 400)
@Composable
private fun EmptyStateNoSearchResultsPreview() {
    PecuniaTheme {
        EmptyState(
            type = EmptyStateType.NO_SEARCH_RESULTS,
            onActionClick = {}
        )
    }
}

@Preview(showBackground = true, heightDp = 400)
@Composable
private fun EmptyStateCustomPreview() {
    PecuniaTheme {
        EmptyState(
            icon = Icons.Outlined.Description,
            title = "No documents",
            description = "Upload your receipts and invoices to keep track of your expenses.",
            actionText = "Upload Document",
            onActionClick = {},
            secondaryActionText = "Learn More",
            onSecondaryActionClick = {}
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun EmptyStateCompactPreview() {
    PecuniaTheme {
        EmptyStateCompact(
            icon = Icons.Outlined.Receipt,
            message = "No recent transactions",
            actionText = "Add One",
            onActionClick = {}
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun EmptyStateInlinePreview() {
    PecuniaTheme {
        EmptyStateInline(
            message = "No items to display"
        )
    }
}
