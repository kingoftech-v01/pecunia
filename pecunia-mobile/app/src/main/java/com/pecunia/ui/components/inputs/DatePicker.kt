package com.pecunia.ui.components.inputs

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.time.temporal.TemporalAdjusters
import java.util.*

/**
 * Quick date selection options
 */
enum class QuickDateOption(
    val label: String,
    val getDate: () -> LocalDate
) {
    TODAY("Aujourd'hui", { LocalDate.now() }),
    YESTERDAY("Hier", { LocalDate.now().minusDays(1) }),
    LAST_WEEK("Semaine dernière", { LocalDate.now().minusWeeks(1) }),
    LAST_MONTH("Mois dernier", { LocalDate.now().minusMonths(1) })
}

/**
 * Date selector button that opens the picker
 */
@Composable
fun DateSelector(
    selectedDate: LocalDate?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    label: String = "Date",
    placeholder: String = "Sélectionner une date",
    isError: Boolean = false,
    errorMessage: String? = null
) {
    val dateFormatter = remember {
        DateTimeFormatter.ofPattern("EEEE d MMMM yyyy", Locale.FRANCE)
    }

    Column(modifier = modifier) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = if (isError) MaterialTheme.colorScheme.error
                    else MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 4.dp)
        )

        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClick = onClick),
            shape = RoundedCornerShape(12.dp),
            border = androidx.compose.foundation.BorderStroke(
                width = 1.dp,
                color = if (isError) MaterialTheme.colorScheme.error
                        else MaterialTheme.colorScheme.outline
            )
        ) {
            Row(
                modifier = Modifier
                    .padding(16.dp)
                    .fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Outlined.CalendarToday,
                        contentDescription = null,
                        tint = if (selectedDate != null) MaterialTheme.colorScheme.primary
                               else MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Spacer(modifier = Modifier.width(12.dp))

                    Text(
                        text = selectedDate?.format(dateFormatter)?.replaceFirstChar { it.uppercase() }
                               ?: placeholder,
                        style = MaterialTheme.typography.bodyLarge,
                        color = if (selectedDate != null) MaterialTheme.colorScheme.onSurface
                                else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

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
 * Date picker dialog using Material 3 DatePicker
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DatePickerDialog(
    selectedDate: LocalDate?,
    onDateSelected: (LocalDate) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    title: String = "Sélectionner une date",
    minDate: LocalDate? = null,
    maxDate: LocalDate? = null,
    showQuickOptions: Boolean = true
) {
    val datePickerState = rememberDatePickerState(
        initialSelectedDateMillis = selectedDate?.toEpochDay()?.times(86400000L)
    )

    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(
                onClick = {
                    datePickerState.selectedDateMillis?.let { millis ->
                        val date = LocalDate.ofEpochDay(millis / 86400000L)
                        onDateSelected(date)
                    }
                }
            ) {
                Text("Confirmer")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Annuler")
            }
        },
        modifier = modifier
    ) {
        Column {
            if (showQuickOptions) {
                QuickDateOptions(
                    selectedDate = selectedDate,
                    onDateSelected = { date ->
                        onDateSelected(date)
                    },
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                )
            }

            DatePicker(
                state = datePickerState,
                title = {
                    Text(
                        text = title,
                        modifier = Modifier.padding(16.dp)
                    )
                },
                showModeToggle = true
            )
        }
    }
}

/**
 * Quick date options row
 */
@Composable
fun QuickDateOptions(
    selectedDate: LocalDate?,
    onDateSelected: (LocalDate) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyRow(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(QuickDateOption.entries) { option ->
            val date = option.getDate()
            val isSelected = selectedDate == date

            FilterChip(
                selected = isSelected,
                onClick = { onDateSelected(date) },
                label = { Text(option.label) },
                leadingIcon = if (isSelected) {
                    {
                        Icon(
                            imageVector = Icons.Default.Check,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                } else null
            )
        }
    }
}

/**
 * Inline date picker (calendar view)
 */
@Composable
fun InlineDatePicker(
    selectedDate: LocalDate?,
    onDateSelected: (LocalDate) -> Unit,
    modifier: Modifier = Modifier,
    minDate: LocalDate? = null,
    maxDate: LocalDate? = null
) {
    var currentMonth by remember { mutableStateOf(YearMonth.from(selectedDate ?: LocalDate.now())) }

    Column(modifier = modifier) {
        // Month navigation
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(
                onClick = { currentMonth = currentMonth.minusMonths(1) }
            ) {
                Icon(
                    imageVector = Icons.Default.ChevronLeft,
                    contentDescription = "Mois précédent"
                )
            }

            Text(
                text = currentMonth.format(
                    DateTimeFormatter.ofPattern("MMMM yyyy", Locale.FRANCE)
                ).replaceFirstChar { it.uppercase() },
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )

            IconButton(
                onClick = { currentMonth = currentMonth.plusMonths(1) }
            ) {
                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = "Mois suivant"
                )
            }
        }

        // Day of week headers
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp)
        ) {
            val daysOfWeek = listOf(
                DayOfWeek.MONDAY,
                DayOfWeek.TUESDAY,
                DayOfWeek.WEDNESDAY,
                DayOfWeek.THURSDAY,
                DayOfWeek.FRIDAY,
                DayOfWeek.SATURDAY,
                DayOfWeek.SUNDAY
            )

            daysOfWeek.forEach { day ->
                Text(
                    text = day.getDisplayName(TextStyle.SHORT, Locale.FRANCE).take(2).uppercase(),
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Calendar grid
        CalendarGrid(
            month = currentMonth,
            selectedDate = selectedDate,
            onDateSelected = onDateSelected,
            minDate = minDate,
            maxDate = maxDate
        )
    }
}

/**
 * Calendar grid for a month
 */
@Composable
private fun CalendarGrid(
    month: YearMonth,
    selectedDate: LocalDate?,
    onDateSelected: (LocalDate) -> Unit,
    minDate: LocalDate?,
    maxDate: LocalDate?
) {
    val firstDayOfMonth = month.atDay(1)
    val lastDayOfMonth = month.atEndOfMonth()
    val firstDayOfWeek = firstDayOfMonth.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))

    val today = LocalDate.now()
    var currentDate = firstDayOfWeek

    Column(
        modifier = Modifier.padding(horizontal = 8.dp)
    ) {
        repeat(6) { weekIndex ->
            Row(modifier = Modifier.fillMaxWidth()) {
                repeat(7) { dayIndex ->
                    val date = currentDate
                    val isInCurrentMonth = date.month == month.month
                    val isSelected = date == selectedDate
                    val isToday = date == today
                    val isEnabled = (minDate == null || !date.isBefore(minDate)) &&
                                   (maxDate == null || !date.isAfter(maxDate))

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .aspectRatio(1f)
                            .padding(2.dp)
                            .clip(CircleShape)
                            .then(
                                if (isSelected) {
                                    Modifier.background(MaterialTheme.colorScheme.primary)
                                } else if (isToday) {
                                    Modifier.background(
                                        MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
                                    )
                                } else {
                                    Modifier
                                }
                            )
                            .clickable(enabled = isInCurrentMonth && isEnabled) {
                                onDateSelected(date)
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = date.dayOfMonth.toString(),
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = if (isSelected || isToday) FontWeight.Bold else FontWeight.Normal,
                            color = when {
                                isSelected -> MaterialTheme.colorScheme.onPrimary
                                !isInCurrentMonth -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                                !isEnabled -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                                isToday -> MaterialTheme.colorScheme.primary
                                else -> MaterialTheme.colorScheme.onSurface
                            }
                        )
                    }

                    currentDate = currentDate.plusDays(1)
                }
            }

            // Stop if we've passed the current month
            if (currentDate.isAfter(lastDayOfMonth) && weekIndex > 3) {
                return@Column
            }
        }
    }
}

/**
 * Date range picker for period selection
 */
@Composable
fun DateRangePicker(
    startDate: LocalDate?,
    endDate: LocalDate?,
    onRangeSelected: (LocalDate?, LocalDate?) -> Unit,
    modifier: Modifier = Modifier,
    label: String = "Période"
) {
    var isStartDatePickerVisible by remember { mutableStateOf(false) }
    var isEndDatePickerVisible by remember { mutableStateOf(false) }

    val dateFormatter = remember {
        DateTimeFormatter.ofPattern("d MMM yyyy", Locale.FRANCE)
    }

    Column(modifier = modifier) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 4.dp)
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Start date
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .clickable { isStartDatePickerVisible = true },
                shape = RoundedCornerShape(12.dp),
                border = androidx.compose.foundation.BorderStroke(
                    width = 1.dp,
                    color = MaterialTheme.colorScheme.outline
                )
            ) {
                Column(
                    modifier = Modifier.padding(12.dp)
                ) {
                    Text(
                        text = "Début",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = startDate?.format(dateFormatter) ?: "Sélectionner",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            Icon(
                imageVector = Icons.Default.ArrowForward,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )

            // End date
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .clickable { isEndDatePickerVisible = true },
                shape = RoundedCornerShape(12.dp),
                border = androidx.compose.foundation.BorderStroke(
                    width = 1.dp,
                    color = MaterialTheme.colorScheme.outline
                )
            ) {
                Column(
                    modifier = Modifier.padding(12.dp)
                ) {
                    Text(
                        text = "Fin",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = endDate?.format(dateFormatter) ?: "Sélectionner",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }

    // Date picker dialogs
    if (isStartDatePickerVisible) {
        DatePickerDialog(
            selectedDate = startDate,
            onDateSelected = { date ->
                onRangeSelected(date, endDate)
                isStartDatePickerVisible = false
            },
            onDismiss = { isStartDatePickerVisible = false },
            title = "Date de début",
            maxDate = endDate
        )
    }

    if (isEndDatePickerVisible) {
        DatePickerDialog(
            selectedDate = endDate,
            onDateSelected = { date ->
                onRangeSelected(startDate, date)
                isEndDatePickerVisible = false
            },
            onDismiss = { isEndDatePickerVisible = false },
            title = "Date de fin",
            minDate = startDate
        )
    }
}

/**
 * Period quick selection chips
 */
enum class PeriodOption(
    val label: String,
    val getRange: () -> Pair<LocalDate, LocalDate>
) {
    THIS_WEEK("Cette semaine", {
        val now = LocalDate.now()
        val start = now.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
        start to now
    }),
    THIS_MONTH("Ce mois", {
        val now = LocalDate.now()
        val start = now.withDayOfMonth(1)
        start to now
    }),
    LAST_MONTH("Mois dernier", {
        val now = LocalDate.now()
        val lastMonth = now.minusMonths(1)
        lastMonth.withDayOfMonth(1) to lastMonth.with(TemporalAdjusters.lastDayOfMonth())
    }),
    LAST_3_MONTHS("3 derniers mois", {
        val now = LocalDate.now()
        now.minusMonths(3) to now
    }),
    THIS_YEAR("Cette année", {
        val now = LocalDate.now()
        now.withDayOfYear(1) to now
    })
}

@Composable
fun PeriodSelector(
    selectedPeriod: PeriodOption?,
    onPeriodSelected: (PeriodOption) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyRow(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(PeriodOption.entries) { period ->
            FilterChip(
                selected = period == selectedPeriod,
                onClick = { onPeriodSelected(period) },
                label = { Text(period.label) }
            )
        }
    }
}

// Previews

@Preview(showBackground = true)
@Composable
private fun DateSelectorPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            DateSelector(
                selectedDate = LocalDate.now(),
                onClick = {}
            )

            DateSelector(
                selectedDate = null,
                onClick = {},
                isError = true,
                errorMessage = "Veuillez sélectionner une date"
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun QuickDateOptionsPreview() {
    MaterialTheme {
        QuickDateOptions(
            selectedDate = LocalDate.now(),
            onDateSelected = {},
            modifier = Modifier.padding(16.dp)
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun InlineDatePickerPreview() {
    MaterialTheme {
        var selectedDate by remember { mutableStateOf<LocalDate?>(LocalDate.now()) }

        InlineDatePicker(
            selectedDate = selectedDate,
            onDateSelected = { selectedDate = it },
            modifier = Modifier.padding(16.dp)
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun DateRangePickerPreview() {
    MaterialTheme {
        DateRangePicker(
            startDate = LocalDate.now().minusDays(7),
            endDate = LocalDate.now(),
            onRangeSelected = { _, _ -> },
            modifier = Modifier.padding(16.dp)
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun PeriodSelectorPreview() {
    MaterialTheme {
        PeriodSelector(
            selectedPeriod = PeriodOption.THIS_MONTH,
            onPeriodSelected = {},
            modifier = Modifier.padding(16.dp)
        )
    }
}
