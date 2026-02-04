package com.pecunia.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.outlined.Fastfood
import androidx.compose.material.icons.outlined.DirectionsCar
import androidx.compose.material.icons.outlined.ShoppingBag
import androidx.compose.material.icons.outlined.Movie
import androidx.compose.material.icons.outlined.Receipt
import androidx.compose.material.icons.outlined.LocalHospital
import androidx.compose.material.icons.outlined.School
import androidx.compose.material.icons.outlined.Flight
import androidx.compose.material.icons.outlined.AttachMoney
import androidx.compose.material.icons.outlined.TrendingUp
import androidx.compose.material.icons.outlined.CardGiftcard
import androidx.compose.material.icons.outlined.MoreHoriz
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
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
import com.pecunia.ui.theme.PecuniaTheme
import com.pecunia.ui.theme.getCategoryColor
import java.math.BigDecimal
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Transaction type enum
 */
enum class TransactionType {
    INCOME,
    EXPENSE
}

/**
 * Data class representing a transaction
 */
data class Transaction(
    val id: String,
    val description: String,
    val amount: BigDecimal,
    val type: TransactionType,
    val category: String,
    val date: Date,
    val merchant: String? = null,
    val notes: String? = null
)

/**
 * Transaction card component displaying transaction details
 *
 * @param transaction The transaction to display
 * @param onClick Callback when the card is clicked
 * @param modifier Modifier for the card
 * @param showDate Whether to show the date
 * @param currencySymbol Currency symbol to use
 */
@Composable
fun TransactionCard(
    transaction: Transaction,
    onClick: () -> Unit = {},
    modifier: Modifier = Modifier,
    showDate: Boolean = true,
    currencySymbol: String = "$"
) {
    val financeColors = PecuniaTheme.financeColors
    val categoryColor = getCategoryColor(transaction.category)

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(
            defaultElevation = 1.dp
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Category Icon
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(categoryColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = getCategoryIcon(transaction.category),
                    contentDescription = transaction.category,
                    tint = categoryColor,
                    modifier = Modifier.size(24.dp)
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Transaction Details
            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = transaction.description,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = transaction.category,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    if (showDate) {
                        Text(
                            text = "\u2022",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = formatTransactionDate(transaction.date),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.width(8.dp))

            // Amount
            Column(
                horizontalAlignment = Alignment.End
            ) {
                val amountColor = when (transaction.type) {
                    TransactionType.INCOME -> financeColors.income
                    TransactionType.EXPENSE -> financeColors.expense
                }
                val prefix = when (transaction.type) {
                    TransactionType.INCOME -> "+"
                    TransactionType.EXPENSE -> "-"
                }

                AmountText(
                    amount = transaction.amount,
                    currencySymbol = currencySymbol,
                    prefix = prefix,
                    color = amountColor,
                    size = AmountSize.MEDIUM
                )

                // Small type indicator
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = when (transaction.type) {
                            TransactionType.INCOME -> Icons.Default.ArrowDownward
                            TransactionType.EXPENSE -> Icons.Default.ArrowUpward
                        },
                        contentDescription = null,
                        modifier = Modifier.size(12.dp),
                        tint = amountColor.copy(alpha = 0.7f)
                    )
                    Text(
                        text = when (transaction.type) {
                            TransactionType.INCOME -> "Income"
                            TransactionType.EXPENSE -> "Expense"
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = amountColor.copy(alpha = 0.7f)
                    )
                }
            }
        }
    }
}

/**
 * Compact version of the transaction card for lists
 */
@Composable
fun TransactionCardCompact(
    transaction: Transaction,
    onClick: () -> Unit = {},
    modifier: Modifier = Modifier,
    currencySymbol: String = "$"
) {
    val financeColors = PecuniaTheme.financeColors
    val categoryColor = getCategoryColor(transaction.category)

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        color = Color.Transparent
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Small category indicator
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(categoryColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = getCategoryIcon(transaction.category),
                    contentDescription = transaction.category,
                    tint = categoryColor,
                    modifier = Modifier.size(20.dp)
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Description
            Text(
                text = transaction.description,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )

            Spacer(modifier = Modifier.width(8.dp))

            // Amount
            val amountColor = when (transaction.type) {
                TransactionType.INCOME -> financeColors.income
                TransactionType.EXPENSE -> financeColors.expense
            }
            val prefix = when (transaction.type) {
                TransactionType.INCOME -> "+"
                TransactionType.EXPENSE -> "-"
            }

            AmountText(
                amount = transaction.amount,
                currencySymbol = currencySymbol,
                prefix = prefix,
                color = amountColor,
                size = AmountSize.SMALL
            )
        }
    }
}

/**
 * Get icon for category
 */
private fun getCategoryIcon(category: String): ImageVector {
    return when (category.lowercase()) {
        "food", "dining", "restaurants", "groceries" -> Icons.Outlined.Fastfood
        "transport", "transportation", "gas", "fuel" -> Icons.Outlined.DirectionsCar
        "shopping", "retail" -> Icons.Outlined.ShoppingBag
        "entertainment", "movies", "games" -> Icons.Outlined.Movie
        "bills", "utilities", "rent" -> Icons.Outlined.Receipt
        "health", "medical", "pharmacy" -> Icons.Outlined.LocalHospital
        "education", "books", "courses" -> Icons.Outlined.School
        "travel", "vacation", "hotel" -> Icons.Outlined.Flight
        "salary", "income", "wages" -> Icons.Outlined.AttachMoney
        "investment", "stocks", "crypto" -> Icons.Outlined.TrendingUp
        "gift", "donation" -> Icons.Outlined.CardGiftcard
        else -> Icons.Outlined.MoreHoriz
    }
}

/**
 * Format date for display in transaction card
 */
private fun formatTransactionDate(date: Date): String {
    val today = Date()
    val diffInDays = ((today.time - date.time) / (1000 * 60 * 60 * 24)).toInt()

    return when {
        diffInDays == 0 -> "Today"
        diffInDays == 1 -> "Yesterday"
        diffInDays < 7 -> SimpleDateFormat("EEEE", Locale.getDefault()).format(date)
        else -> SimpleDateFormat("MMM d", Locale.getDefault()).format(date)
    }
}

@Preview(showBackground = true)
@Composable
private fun TransactionCardPreview() {
    PecuniaTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            TransactionCard(
                transaction = Transaction(
                    id = "1",
                    description = "Coffee Shop",
                    amount = BigDecimal("4.50"),
                    type = TransactionType.EXPENSE,
                    category = "Food",
                    date = Date()
                )
            )

            TransactionCard(
                transaction = Transaction(
                    id = "2",
                    description = "Monthly Salary",
                    amount = BigDecimal("3500.00"),
                    type = TransactionType.INCOME,
                    category = "Salary",
                    date = Date()
                )
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun TransactionCardCompactPreview() {
    PecuniaTheme {
        Column {
            TransactionCardCompact(
                transaction = Transaction(
                    id = "1",
                    description = "Uber Ride",
                    amount = BigDecimal("15.00"),
                    type = TransactionType.EXPENSE,
                    category = "Transport",
                    date = Date()
                )
            )
        }
    }
}
