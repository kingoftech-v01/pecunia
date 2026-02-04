package com.pecunia.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pecunia.ui.theme.PecuniaTheme
import com.pecunia.ui.theme.FinanceTextStyles
import java.math.BigDecimal
import java.math.RoundingMode
import java.text.NumberFormat
import java.util.Currency
import java.util.Locale

/**
 * Size variants for amount text
 */
enum class AmountSize {
    SMALL,
    MEDIUM,
    LARGE,
    EXTRA_LARGE
}

/**
 * Formatted currency text component
 *
 * @param amount The amount to display
 * @param modifier Modifier for the text
 * @param currencySymbol Currency symbol to display
 * @param currencyCode ISO currency code for proper formatting
 * @param prefix Optional prefix (e.g., "+" or "-")
 * @param size Size variant
 * @param color Text color (defaults to onSurface)
 * @param showDecimals Whether to show decimal places
 * @param textAlign Text alignment
 */
@Composable
fun AmountText(
    amount: BigDecimal,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$",
    currencyCode: String? = null,
    prefix: String = "",
    size: AmountSize = AmountSize.MEDIUM,
    color: Color = MaterialTheme.colorScheme.onSurface,
    showDecimals: Boolean = true,
    textAlign: TextAlign = TextAlign.Start
) {
    val formattedAmount = formatAmount(amount, currencyCode, showDecimals)
    val displayText = "$prefix$currencySymbol$formattedAmount"

    val textStyle = when (size) {
        AmountSize.SMALL -> FinanceTextStyles.amountSmall
        AmountSize.MEDIUM -> FinanceTextStyles.amountMedium
        AmountSize.LARGE -> FinanceTextStyles.amountLarge
        AmountSize.EXTRA_LARGE -> TextStyle(
            fontWeight = FontWeight.Bold,
            fontSize = 40.sp,
            lineHeight = 48.sp
        )
    }

    Text(
        text = displayText,
        style = textStyle,
        color = color,
        textAlign = textAlign,
        modifier = modifier
    )
}

/**
 * Amount text with currency symbol as superscript
 */
@Composable
fun AmountTextWithSymbol(
    amount: BigDecimal,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$",
    prefix: String = "",
    size: AmountSize = AmountSize.LARGE,
    color: Color = MaterialTheme.colorScheme.onSurface,
    showDecimals: Boolean = true
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.Top
    ) {
        // Currency symbol (smaller)
        Text(
            text = "$prefix$currencySymbol",
            style = FinanceTextStyles.currencySymbol.copy(
                fontSize = when (size) {
                    AmountSize.SMALL -> 10.sp
                    AmountSize.MEDIUM -> 12.sp
                    AmountSize.LARGE -> 16.sp
                    AmountSize.EXTRA_LARGE -> 20.sp
                }
            ),
            color = color.copy(alpha = 0.8f),
            modifier = Modifier.padding(top = when (size) {
                AmountSize.SMALL -> 2.dp
                AmountSize.MEDIUM -> 3.dp
                AmountSize.LARGE -> 4.dp
                AmountSize.EXTRA_LARGE -> 6.dp
            })
        )

        // Amount
        val formattedAmount = formatAmount(amount, null, showDecimals)
        val textStyle = when (size) {
            AmountSize.SMALL -> FinanceTextStyles.amountSmall
            AmountSize.MEDIUM -> FinanceTextStyles.amountMedium
            AmountSize.LARGE -> FinanceTextStyles.amountLarge
            AmountSize.EXTRA_LARGE -> TextStyle(
                fontWeight = FontWeight.Bold,
                fontSize = 40.sp,
                lineHeight = 48.sp
            )
        }

        Text(
            text = formattedAmount,
            style = textStyle,
            color = color
        )
    }
}

/**
 * Compact amount display with optional sign indicator
 */
@Composable
fun AmountTextCompact(
    amount: BigDecimal,
    isPositive: Boolean,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$",
    showSign: Boolean = true
) {
    val financeColors = PecuniaTheme.financeColors
    val color = if (isPositive) financeColors.income else financeColors.expense
    val sign = if (showSign) {
        if (isPositive) "+" else "-"
    } else ""

    Text(
        text = "$sign$currencySymbol${formatAmount(amount.abs(), null, true)}",
        style = MaterialTheme.typography.bodyMedium.copy(
            fontWeight = FontWeight.Medium
        ),
        color = color,
        modifier = modifier
    )
}

/**
 * Balance display with label
 */
@Composable
fun BalanceDisplay(
    balance: BigDecimal,
    label: String,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$",
    size: AmountSize = AmountSize.LARGE,
    labelColor: Color = MaterialTheme.colorScheme.onSurfaceVariant
) {
    val financeColors = PecuniaTheme.financeColors
    val balanceColor = when {
        balance > BigDecimal.ZERO -> financeColors.income
        balance < BigDecimal.ZERO -> financeColors.expense
        else -> MaterialTheme.colorScheme.onSurface
    }

    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.Start
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = labelColor
        )

        val prefix = if (balance < BigDecimal.ZERO) "-" else ""
        AmountText(
            amount = balance.abs(),
            currencySymbol = currencySymbol,
            prefix = prefix,
            size = size,
            color = balanceColor
        )
    }
}

/**
 * Income/Expense summary display
 */
@Composable
fun IncomeExpenseSummary(
    income: BigDecimal,
    expense: BigDecimal,
    modifier: Modifier = Modifier,
    currencySymbol: String = "$"
) {
    val financeColors = PecuniaTheme.financeColors

    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(24.dp)
    ) {
        Column {
            Text(
                text = "Income",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            AmountText(
                amount = income,
                currencySymbol = currencySymbol,
                prefix = "+",
                size = AmountSize.MEDIUM,
                color = financeColors.income
            )
        }

        Column {
            Text(
                text = "Expense",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            AmountText(
                amount = expense,
                currencySymbol = currencySymbol,
                prefix = "-",
                size = AmountSize.MEDIUM,
                color = financeColors.expense
            )
        }
    }
}

/**
 * Format amount for display
 */
private fun formatAmount(
    amount: BigDecimal,
    currencyCode: String?,
    showDecimals: Boolean
): String {
    return if (currencyCode != null) {
        try {
            val format = NumberFormat.getCurrencyInstance(Locale.getDefault())
            format.currency = Currency.getInstance(currencyCode)
            format.format(amount).replace(Regex("^[^0-9]*"), "")
        } catch (e: Exception) {
            formatNumberWithSeparators(amount, showDecimals)
        }
    } else {
        formatNumberWithSeparators(amount, showDecimals)
    }
}

/**
 * Format number with thousand separators
 */
private fun formatNumberWithSeparators(amount: BigDecimal, showDecimals: Boolean): String {
    val format = NumberFormat.getNumberInstance(Locale.getDefault())
    format.minimumFractionDigits = if (showDecimals) 2 else 0
    format.maximumFractionDigits = if (showDecimals) 2 else 0
    return format.format(amount.setScale(if (showDecimals) 2 else 0, RoundingMode.HALF_UP))
}

/**
 * Format large amounts in compact form (e.g., 1.5K, 2.3M)
 */
fun formatCompactAmount(amount: BigDecimal): String {
    return when {
        amount >= BigDecimal(1_000_000_000) -> {
            "${amount.divide(BigDecimal(1_000_000_000), 1, RoundingMode.HALF_UP)}B"
        }
        amount >= BigDecimal(1_000_000) -> {
            "${amount.divide(BigDecimal(1_000_000), 1, RoundingMode.HALF_UP)}M"
        }
        amount >= BigDecimal(1_000) -> {
            "${amount.divide(BigDecimal(1_000), 1, RoundingMode.HALF_UP)}K"
        }
        else -> {
            amount.setScale(2, RoundingMode.HALF_UP).toString()
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun AmountTextPreview() {
    PecuniaTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            AmountText(
                amount = BigDecimal("1234.56"),
                size = AmountSize.SMALL
            )

            AmountText(
                amount = BigDecimal("1234.56"),
                size = AmountSize.MEDIUM
            )

            AmountText(
                amount = BigDecimal("1234.56"),
                size = AmountSize.LARGE
            )

            AmountText(
                amount = BigDecimal("1234.56"),
                prefix = "+",
                size = AmountSize.MEDIUM,
                color = PecuniaTheme.financeColors.income
            )

            AmountText(
                amount = BigDecimal("567.89"),
                prefix = "-",
                size = AmountSize.MEDIUM,
                color = PecuniaTheme.financeColors.expense
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun AmountTextWithSymbolPreview() {
    PecuniaTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            AmountTextWithSymbol(
                amount = BigDecimal("12345.67"),
                size = AmountSize.LARGE
            )

            AmountTextWithSymbol(
                amount = BigDecimal("12345.67"),
                size = AmountSize.EXTRA_LARGE
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun BalanceDisplayPreview() {
    PecuniaTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            BalanceDisplay(
                balance = BigDecimal("5432.10"),
                label = "Total Balance"
            )

            BalanceDisplay(
                balance = BigDecimal("-123.45"),
                label = "Monthly Balance"
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun IncomeExpenseSummaryPreview() {
    PecuniaTheme {
        IncomeExpenseSummary(
            income = BigDecimal("3500.00"),
            expense = BigDecimal("2100.50"),
            modifier = Modifier.padding(16.dp)
        )
    }
}
