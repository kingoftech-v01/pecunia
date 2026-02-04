package com.pecunia.ui.components.inputs

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.*

/**
 * Currency symbol position
 */
enum class CurrencyPosition {
    PREFIX,
    SUFFIX
}

/**
 * Supported currencies
 */
enum class Currency(
    val symbol: String,
    val code: String,
    val position: CurrencyPosition,
    val decimalSeparator: Char,
    val groupingSeparator: Char
) {
    EUR("EUR", "EUR", CurrencyPosition.SUFFIX, ',', ' '),
    USD("$", "USD", CurrencyPosition.PREFIX, '.', ','),
    GBP("£", "GBP", CurrencyPosition.PREFIX, '.', ','),
    CHF("CHF", "CHF", CurrencyPosition.SUFFIX, '.', '\'')
}

/**
 * Main amount input component with currency formatting
 */
@Composable
fun AmountInput(
    value: Double?,
    onValueChange: (Double?) -> Unit,
    modifier: Modifier = Modifier,
    currency: Currency = Currency.EUR,
    label: String? = null,
    placeholder: String = "0,00",
    isExpense: Boolean = true,
    enabled: Boolean = true,
    isError: Boolean = false,
    errorMessage: String? = null,
    onDone: (() -> Unit)? = null
) {
    var textFieldValue by remember(value) {
        mutableStateOf(
            TextFieldValue(
                text = value?.let { formatAmountForDisplay(it, currency) } ?: "",
                selection = TextRange((value?.let { formatAmountForDisplay(it, currency) } ?: "").length)
            )
        )
    }
    var isFocused by remember { mutableStateOf(false) }
    val focusManager = LocalFocusManager.current

    Column(modifier = modifier) {
        if (label != null) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = if (isError) MaterialTheme.colorScheme.error
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 4.dp)
            )
        }

        OutlinedTextField(
            value = textFieldValue,
            onValueChange = { newValue ->
                val filteredText = newValue.text.filter { char ->
                    char.isDigit() || char == currency.decimalSeparator
                }

                // Ensure only one decimal separator
                val parts = filteredText.split(currency.decimalSeparator)
                val cleanText = if (parts.size > 2) {
                    parts[0] + currency.decimalSeparator + parts.drop(1).joinToString("")
                } else {
                    filteredText
                }

                // Limit decimal places to 2
                val finalText = if (cleanText.contains(currency.decimalSeparator)) {
                    val decimalParts = cleanText.split(currency.decimalSeparator)
                    decimalParts[0] + currency.decimalSeparator + decimalParts.getOrElse(1) { "" }.take(2)
                } else {
                    cleanText
                }

                textFieldValue = TextFieldValue(
                    text = finalText,
                    selection = TextRange(finalText.length)
                )

                val parsedValue = parseAmount(finalText, currency)
                onValueChange(parsedValue)
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = enabled,
            textStyle = TextStyle(
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                textAlign = TextAlign.End
            ),
            placeholder = {
                Text(
                    text = placeholder,
                    style = TextStyle(
                        fontSize = 18.sp,
                        textAlign = TextAlign.End
                    ),
                    modifier = Modifier.fillMaxWidth()
                )
            },
            leadingIcon = if (currency.position == CurrencyPosition.PREFIX) {
                {
                    Text(
                        text = currency.symbol,
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else null,
            trailingIcon = {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (currency.position == CurrencyPosition.SUFFIX) {
                        Text(
                            text = currency.symbol,
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            },
            isError = isError,
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Decimal,
                imeAction = ImeAction.Done
            ),
            keyboardActions = KeyboardActions(
                onDone = {
                    focusManager.clearFocus()
                    onDone?.invoke()
                }
            ),
            singleLine = true,
            shape = RoundedCornerShape(12.dp)
        )

        if (isError && errorMessage != null) {
            Text(
                text = errorMessage,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(start = 16.dp, top = 4.dp)
            )
        }
    }
}

/**
 * Large amount input for prominent display (e.g., transaction creation)
 */
@Composable
fun LargeAmountInput(
    value: Double?,
    onValueChange: (Double?) -> Unit,
    modifier: Modifier = Modifier,
    currency: Currency = Currency.EUR,
    isExpense: Boolean = true,
    enabled: Boolean = true
) {
    var textValue by remember(value) {
        mutableStateOf(value?.let { formatAmountForDisplay(it, currency) } ?: "")
    }
    val focusRequester = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current

    val amountColor = if (isExpense) {
        MaterialTheme.colorScheme.error
    } else {
        Color(0xFF4CAF50)
    }

    Column(
        modifier = modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            // Sign indicator
            Text(
                text = if (isExpense) "-" else "+",
                style = MaterialTheme.typography.displayMedium,
                fontWeight = FontWeight.Light,
                color = amountColor
            )

            Spacer(modifier = Modifier.width(8.dp))

            BasicTextField(
                value = textValue,
                onValueChange = { newValue ->
                    val filteredText = newValue.filter { char ->
                        char.isDigit() || char == currency.decimalSeparator
                    }

                    val parts = filteredText.split(currency.decimalSeparator)
                    val cleanText = if (parts.size > 2) {
                        parts[0] + currency.decimalSeparator + parts.drop(1).joinToString("")
                    } else {
                        filteredText
                    }

                    val finalText = if (cleanText.contains(currency.decimalSeparator)) {
                        val decimalParts = cleanText.split(currency.decimalSeparator)
                        decimalParts[0] + currency.decimalSeparator + decimalParts.getOrElse(1) { "" }.take(2)
                    } else {
                        cleanText
                    }

                    textValue = finalText
                    val parsedValue = parseAmount(finalText, currency)
                    onValueChange(parsedValue)
                },
                modifier = Modifier
                    .focusRequester(focusRequester)
                    .widthIn(min = 100.dp),
                enabled = enabled,
                textStyle = TextStyle(
                    fontSize = 48.sp,
                    fontWeight = FontWeight.Bold,
                    color = amountColor,
                    textAlign = TextAlign.Center
                ),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Decimal,
                    imeAction = ImeAction.Done
                ),
                keyboardActions = KeyboardActions(
                    onDone = { focusManager.clearFocus() }
                ),
                singleLine = true,
                cursorBrush = SolidColor(amountColor),
                decorationBox = { innerTextField ->
                    Box(contentAlignment = Alignment.Center) {
                        if (textValue.isEmpty()) {
                            Text(
                                text = "0${currency.decimalSeparator}00",
                                style = TextStyle(
                                    fontSize = 48.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = amountColor.copy(alpha = 0.3f)
                                )
                            )
                        }
                        innerTextField()
                    }
                }
            )

            Spacer(modifier = Modifier.width(8.dp))

            Text(
                text = currency.symbol,
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * Amount display (read-only formatted amount)
 */
@Composable
fun AmountDisplay(
    amount: Double,
    modifier: Modifier = Modifier,
    currency: Currency = Currency.EUR,
    isExpense: Boolean? = null,
    showSign: Boolean = true,
    style: TextStyle = MaterialTheme.typography.titleLarge
) {
    val color = when {
        isExpense == true -> MaterialTheme.colorScheme.error
        isExpense == false -> Color(0xFF4CAF50)
        amount < 0 -> MaterialTheme.colorScheme.error
        amount > 0 -> Color(0xFF4CAF50)
        else -> MaterialTheme.colorScheme.onSurface
    }

    val formattedAmount = formatAmountWithCurrency(
        amount = kotlin.math.abs(amount),
        currency = currency,
        showSign = showSign,
        isNegative = isExpense == true || amount < 0
    )

    Text(
        text = formattedAmount,
        style = style,
        fontWeight = FontWeight.SemiBold,
        color = color,
        modifier = modifier
    )
}

/**
 * Amount input with type selector (expense/income)
 */
@Composable
fun AmountInputWithType(
    value: Double?,
    onValueChange: (Double?) -> Unit,
    isExpense: Boolean,
    onTypeChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
    currency: Currency = Currency.EUR
) {
    Column(modifier = modifier) {
        // Type selector
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(MaterialTheme.colorScheme.surfaceVariant)
                .padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            // Expense button
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .clickable { onTypeChange(true) },
                shape = RoundedCornerShape(8.dp),
                color = if (isExpense) MaterialTheme.colorScheme.error
                        else Color.Transparent
            ) {
                Row(
                    modifier = Modifier.padding(vertical = 12.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowDownward,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                        tint = if (isExpense) MaterialTheme.colorScheme.onError
                               else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Dépense",
                        style = MaterialTheme.typography.labelLarge,
                        color = if (isExpense) MaterialTheme.colorScheme.onError
                                else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Income button
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .clickable { onTypeChange(false) },
                shape = RoundedCornerShape(8.dp),
                color = if (!isExpense) Color(0xFF4CAF50) else Color.Transparent
            ) {
                Row(
                    modifier = Modifier.padding(vertical = 12.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowUpward,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                        tint = if (!isExpense) Color.White
                               else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Revenu",
                        style = MaterialTheme.typography.labelLarge,
                        color = if (!isExpense) Color.White
                                else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Amount input
        LargeAmountInput(
            value = value,
            onValueChange = onValueChange,
            currency = currency,
            isExpense = isExpense
        )
    }
}

// Helper functions

private fun formatAmountForDisplay(amount: Double, currency: Currency): String {
    val symbols = DecimalFormatSymbols().apply {
        decimalSeparator = currency.decimalSeparator
        groupingSeparator = currency.groupingSeparator
    }
    val formatter = DecimalFormat("#,##0.00", symbols)
    return formatter.format(amount)
}

private fun formatAmountWithCurrency(
    amount: Double,
    currency: Currency,
    showSign: Boolean,
    isNegative: Boolean
): String {
    val symbols = DecimalFormatSymbols().apply {
        decimalSeparator = currency.decimalSeparator
        groupingSeparator = currency.groupingSeparator
    }
    val formatter = DecimalFormat("#,##0.00", symbols)
    val formattedNumber = formatter.format(amount)

    val sign = when {
        !showSign -> ""
        isNegative -> "-"
        else -> "+"
    }

    return when (currency.position) {
        CurrencyPosition.PREFIX -> "$sign${currency.symbol}$formattedNumber"
        CurrencyPosition.SUFFIX -> "$sign$formattedNumber ${currency.symbol}"
    }
}

private fun parseAmount(text: String, currency: Currency): Double? {
    if (text.isBlank()) return null

    return try {
        text.replace(currency.groupingSeparator.toString(), "")
            .replace(currency.decimalSeparator, '.')
            .toDoubleOrNull()
    } catch (e: Exception) {
        null
    }
}

// Previews

@Preview(showBackground = true)
@Composable
private fun AmountInputPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            var amount1 by remember { mutableStateOf<Double?>(125.50) }
            AmountInput(
                value = amount1,
                onValueChange = { amount1 = it },
                label = "Montant"
            )

            var amount2 by remember { mutableStateOf<Double?>(null) }
            AmountInput(
                value = amount2,
                onValueChange = { amount2 = it },
                label = "Montant (vide)",
                isError = true,
                errorMessage = "Ce champ est requis"
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun LargeAmountInputPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(32.dp),
            verticalArrangement = Arrangement.spacedBy(32.dp)
        ) {
            var amount1 by remember { mutableStateOf<Double?>(85.50) }
            LargeAmountInput(
                value = amount1,
                onValueChange = { amount1 = it },
                isExpense = true
            )

            var amount2 by remember { mutableStateOf<Double?>(2500.0) }
            LargeAmountInput(
                value = amount2,
                onValueChange = { amount2 = it },
                isExpense = false
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun AmountDisplayPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            AmountDisplay(amount = 1234.56, isExpense = false)
            AmountDisplay(amount = 85.50, isExpense = true)
            AmountDisplay(amount = 0.0)
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun AmountInputWithTypePreview() {
    MaterialTheme {
        var amount by remember { mutableStateOf<Double?>(150.0) }
        var isExpense by remember { mutableStateOf(true) }

        AmountInputWithType(
            value = amount,
            onValueChange = { amount = it },
            isExpense = isExpense,
            onTypeChange = { isExpense = it },
            modifier = Modifier.padding(16.dp)
        )
    }
}
