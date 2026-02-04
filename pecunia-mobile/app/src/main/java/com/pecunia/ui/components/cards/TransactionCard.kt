package com.pecunia.ui.components.cards

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import java.text.NumberFormat
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.*

/**
 * Transaction type enum
 */
enum class TransactionType {
    EXPENSE,
    INCOME,
    TRANSFER
}

/**
 * Transaction data model for UI
 */
data class TransactionUiModel(
    val id: String,
    val title: String,
    val description: String? = null,
    val amount: Double,
    val type: TransactionType,
    val categoryName: String,
    val categoryIcon: ImageVector,
    val categoryColor: Color,
    val date: LocalDateTime,
    val accountName: String? = null,
    val isPending: Boolean = false,
    val isRecurring: Boolean = false
)

/**
 * Standard transaction card
 */
@Composable
fun TransactionCard(
    transaction: TransactionUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    showAccount: Boolean = false
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Category icon with colored background
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(transaction.categoryColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = transaction.categoryIcon,
                    contentDescription = transaction.categoryName,
                    modifier = Modifier.size(24.dp),
                    tint = transaction.categoryColor
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Title and details
            Column(
                modifier = Modifier.weight(1f)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = transaction.title,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false)
                    )

                    if (transaction.isPending) {
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(
                            imageVector = Icons.Outlined.Schedule,
                            contentDescription = "En attente",
                            modifier = Modifier.size(16.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    if (transaction.isRecurring) {
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(
                            imageVector = Icons.Outlined.Repeat,
                            contentDescription = "Récurrent",
                            modifier = Modifier.size(16.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Spacer(modifier = Modifier.height(2.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = transaction.categoryName,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    if (showAccount && transaction.accountName != null) {
                        Text(
                            text = " • ${transaction.accountName}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Amount and date
            Column(
                horizontalAlignment = Alignment.End
            ) {
                Text(
                    text = formatAmount(transaction.amount, transaction.type),
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.SemiBold,
                    color = when (transaction.type) {
                        TransactionType.EXPENSE -> MaterialTheme.colorScheme.error
                        TransactionType.INCOME -> Color(0xFF2E7D32)
                        TransactionType.TRANSFER -> MaterialTheme.colorScheme.onSurface
                    }
                )

                Spacer(modifier = Modifier.height(2.dp))

                Text(
                    text = formatDate(transaction.date),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

/**
 * Compact transaction item for lists
 */
@Composable
fun TransactionItem(
    transaction: TransactionUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Small category indicator
        Box(
            modifier = Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(transaction.categoryColor.copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = transaction.categoryIcon,
                contentDescription = null,
                modifier = Modifier.size(20.dp),
                tint = transaction.categoryColor
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = transaction.title,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = transaction.categoryName,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Text(
            text = formatAmount(transaction.amount, transaction.type),
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium,
            color = when (transaction.type) {
                TransactionType.EXPENSE -> MaterialTheme.colorScheme.error
                TransactionType.INCOME -> Color(0xFF2E7D32)
                TransactionType.TRANSFER -> MaterialTheme.colorScheme.onSurface
            }
        )
    }
}

/**
 * Transaction card with swipe actions
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SwipeableTransactionCard(
    transaction: TransactionUiModel,
    onClick: () -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    modifier: Modifier = Modifier
) {
    val dismissState = rememberSwipeToDismissBoxState()

    SwipeToDismissBox(
        state = dismissState,
        modifier = modifier,
        backgroundContent = {
            val direction = dismissState.dismissDirection

            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        when (direction) {
                            SwipeToDismissBoxValue.EndToStart -> MaterialTheme.colorScheme.error
                            SwipeToDismissBoxValue.StartToEnd -> MaterialTheme.colorScheme.primary
                            else -> Color.Transparent
                        }
                    )
                    .padding(horizontal = 20.dp),
                horizontalArrangement = when (direction) {
                    SwipeToDismissBoxValue.StartToEnd -> Arrangement.Start
                    else -> Arrangement.End
                },
                verticalAlignment = Alignment.CenterVertically
            ) {
                when (direction) {
                    SwipeToDismissBoxValue.StartToEnd -> {
                        Icon(
                            imageVector = Icons.Default.Edit,
                            contentDescription = "Modifier",
                            tint = MaterialTheme.colorScheme.onPrimary
                        )
                    }
                    SwipeToDismissBoxValue.EndToStart -> {
                        Icon(
                            imageVector = Icons.Default.Delete,
                            contentDescription = "Supprimer",
                            tint = MaterialTheme.colorScheme.onError
                        )
                    }
                    else -> {}
                }
            }
        }
    ) {
        TransactionCard(
            transaction = transaction,
            onClick = onClick
        )
    }
}

/**
 * Transaction group header with date
 */
@Composable
fun TransactionGroupHeader(
    date: LocalDate,
    totalAmount: Double? = null,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = formatGroupDate(date),
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        if (totalAmount != null) {
            Text(
                text = formatCurrency(totalAmount),
                style = MaterialTheme.typography.titleSmall,
                color = if (totalAmount >= 0) Color(0xFF2E7D32) else MaterialTheme.colorScheme.error
            )
        }
    }
}

/**
 * Mini transaction preview for dashboard
 */
@Composable
fun TransactionMiniCard(
    transaction: TransactionUiModel,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier
            .width(160.dp)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
    ) {
        Column(
            modifier = Modifier.padding(12.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(32.dp)
                        .clip(CircleShape)
                        .background(transaction.categoryColor.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = transaction.categoryIcon,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = transaction.categoryColor
                    )
                }

                Spacer(modifier = Modifier.width(8.dp))

                Text(
                    text = transaction.title,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = formatAmount(transaction.amount, transaction.type),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = when (transaction.type) {
                    TransactionType.EXPENSE -> MaterialTheme.colorScheme.error
                    TransactionType.INCOME -> Color(0xFF2E7D32)
                    TransactionType.TRANSFER -> MaterialTheme.colorScheme.onSurface
                }
            )
        }
    }
}

// Helper functions

private fun formatAmount(amount: Double, type: TransactionType): String {
    val formatter = NumberFormat.getCurrencyInstance(Locale.FRANCE)
    val formatted = formatter.format(kotlin.math.abs(amount))
    return when (type) {
        TransactionType.EXPENSE -> "-$formatted"
        TransactionType.INCOME -> "+$formatted"
        TransactionType.TRANSFER -> formatted
    }
}

private fun formatCurrency(amount: Double): String {
    val formatter = NumberFormat.getCurrencyInstance(Locale.FRANCE)
    val prefix = if (amount >= 0) "+" else ""
    return prefix + formatter.format(amount)
}

private fun formatDate(dateTime: LocalDateTime): String {
    val formatter = DateTimeFormatter.ofPattern("d MMM", Locale.FRANCE)
    return dateTime.format(formatter)
}

private fun formatGroupDate(date: LocalDate): String {
    val today = LocalDate.now()
    val yesterday = today.minusDays(1)

    return when (date) {
        today -> "Aujourd'hui"
        yesterday -> "Hier"
        else -> {
            val formatter = DateTimeFormatter.ofPattern("EEEE d MMMM", Locale.FRANCE)
            date.format(formatter).replaceFirstChar { it.uppercase() }
        }
    }
}

// Previews

@Preview(showBackground = true)
@Composable
private fun TransactionCardPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            TransactionCard(
                transaction = TransactionUiModel(
                    id = "1",
                    title = "Carrefour",
                    amount = 85.50,
                    type = TransactionType.EXPENSE,
                    categoryName = "Alimentation",
                    categoryIcon = Icons.Outlined.ShoppingCart,
                    categoryColor = Color(0xFF4CAF50),
                    date = LocalDateTime.now(),
                    accountName = "Compte courant"
                ),
                onClick = {},
                showAccount = true
            )

            TransactionCard(
                transaction = TransactionUiModel(
                    id = "2",
                    title = "Salaire",
                    amount = 2500.00,
                    type = TransactionType.INCOME,
                    categoryName = "Revenus",
                    categoryIcon = Icons.Outlined.AccountBalance,
                    categoryColor = Color(0xFF2196F3),
                    date = LocalDateTime.now(),
                    isPending = true
                ),
                onClick = {}
            )

            TransactionCard(
                transaction = TransactionUiModel(
                    id = "3",
                    title = "Netflix",
                    amount = 15.99,
                    type = TransactionType.EXPENSE,
                    categoryName = "Abonnements",
                    categoryIcon = Icons.Outlined.Subscriptions,
                    categoryColor = Color(0xFFE91E63),
                    date = LocalDateTime.now(),
                    isRecurring = true
                ),
                onClick = {}
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun TransactionItemPreview() {
    MaterialTheme {
        Column {
            TransactionGroupHeader(
                date = LocalDate.now(),
                totalAmount = -125.50
            )
            TransactionItem(
                transaction = TransactionUiModel(
                    id = "1",
                    title = "Restaurant Le Petit Bistrot",
                    amount = 45.00,
                    type = TransactionType.EXPENSE,
                    categoryName = "Restaurants",
                    categoryIcon = Icons.Outlined.Restaurant,
                    categoryColor = Color(0xFFFF9800),
                    date = LocalDateTime.now()
                ),
                onClick = {}
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun TransactionMiniCardPreview() {
    MaterialTheme {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            TransactionMiniCard(
                transaction = TransactionUiModel(
                    id = "1",
                    title = "Uber",
                    amount = 12.50,
                    type = TransactionType.EXPENSE,
                    categoryName = "Transport",
                    categoryIcon = Icons.Outlined.DirectionsCar,
                    categoryColor = Color(0xFF9C27B0),
                    date = LocalDateTime.now()
                ),
                onClick = {}
            )
        }
    }
}
