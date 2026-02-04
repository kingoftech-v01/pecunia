package com.pecunia.ui.components.charts

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Legend item data
 */
data class LegendItem(
    val id: String,
    val label: String,
    val color: Color,
    val value: String? = null,
    val percentage: Float? = null,
    val isSelected: Boolean = true
)

/**
 * Legend orientation
 */
enum class LegendOrientation {
    Horizontal,
    Vertical
}

/**
 * Legend style
 */
enum class LegendStyle {
    Compact,     // Just color dot and label
    Detailed,    // Color dot, label, and value
    Full         // Color dot, label, value, and percentage
}

/**
 * Reusable chart legend component
 */
@Composable
fun ChartLegend(
    items: List<LegendItem>,
    modifier: Modifier = Modifier,
    orientation: LegendOrientation = LegendOrientation.Horizontal,
    style: LegendStyle = LegendStyle.Compact,
    onItemClick: ((LegendItem) -> Unit)? = null,
    selectedItems: Set<String>? = null,
    maxItemsPerRow: Int = 4,
    itemSpacing: Dp = 16.dp,
    showBorder: Boolean = false
) {
    val containerModifier = if (showBorder) {
        modifier
            .border(
                width = 1.dp,
                color = MaterialTheme.colorScheme.outlineVariant,
                shape = RoundedCornerShape(8.dp)
            )
            .padding(12.dp)
    } else {
        modifier
    }

    when (orientation) {
        LegendOrientation.Horizontal -> {
            HorizontalLegend(
                items = items,
                modifier = containerModifier,
                style = style,
                onItemClick = onItemClick,
                selectedItems = selectedItems,
                maxItemsPerRow = maxItemsPerRow,
                itemSpacing = itemSpacing
            )
        }
        LegendOrientation.Vertical -> {
            VerticalLegend(
                items = items,
                modifier = containerModifier,
                style = style,
                onItemClick = onItemClick,
                selectedItems = selectedItems,
                itemSpacing = itemSpacing
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun HorizontalLegend(
    items: List<LegendItem>,
    modifier: Modifier = Modifier,
    style: LegendStyle,
    onItemClick: ((LegendItem) -> Unit)?,
    selectedItems: Set<String>?,
    maxItemsPerRow: Int,
    itemSpacing: Dp
) {
    if (items.size <= maxItemsPerRow) {
        // Single row with horizontal scroll if needed
        Row(
            modifier = modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(itemSpacing),
            verticalAlignment = Alignment.CenterVertically
        ) {
            items.forEach { item ->
                LegendItemView(
                    item = item,
                    style = style,
                    isSelected = selectedItems?.contains(item.id) ?: true,
                    onClick = onItemClick?.let { { it(item) } }
                )
            }
        }
    } else {
        // Multi-row flow layout
        FlowRow(
            modifier = modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(itemSpacing),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items.forEach { item ->
                LegendItemView(
                    item = item,
                    style = style,
                    isSelected = selectedItems?.contains(item.id) ?: true,
                    onClick = onItemClick?.let { { it(item) } }
                )
            }
        }
    }
}

@Composable
private fun VerticalLegend(
    items: List<LegendItem>,
    modifier: Modifier = Modifier,
    style: LegendStyle,
    onItemClick: ((LegendItem) -> Unit)?,
    selectedItems: Set<String>?,
    itemSpacing: Dp
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(itemSpacing)
    ) {
        items.forEach { item ->
            LegendItemView(
                item = item,
                style = style,
                isSelected = selectedItems?.contains(item.id) ?: true,
                onClick = onItemClick?.let { { it(item) } },
                expanded = true
            )
        }
    }
}

@Composable
private fun LegendItemView(
    item: LegendItem,
    style: LegendStyle,
    isSelected: Boolean,
    onClick: (() -> Unit)?,
    expanded: Boolean = false
) {
    val alpha by animateFloatAsState(
        targetValue = if (isSelected) 1f else 0.4f,
        label = "legend_alpha"
    )

    val clickableModifier = if (onClick != null) {
        Modifier.clickable { onClick() }
    } else {
        Modifier
    }

    Row(
        modifier = clickableModifier
            .alpha(alpha)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Color indicator
        Box(
            modifier = Modifier
                .size(12.dp)
                .clip(CircleShape)
                .background(item.color)
        )

        Spacer(modifier = Modifier.width(8.dp))

        // Label
        Text(
            text = item.label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = if (expanded) Modifier.weight(1f) else Modifier
        )

        // Value (for Detailed and Full styles)
        if (style != LegendStyle.Compact && item.value != null) {
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = item.value,
                style = MaterialTheme.typography.bodySmall.copy(
                    fontWeight = FontWeight.SemiBold
                ),
                color = MaterialTheme.colorScheme.onSurface
            )
        }

        // Percentage (for Full style only)
        if (style == LegendStyle.Full && item.percentage != null) {
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "(${ChartFormatters.formatPercent(item.percentage)})",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * Interactive legend with selection state management
 */
@Composable
fun InteractiveLegend(
    items: List<LegendItem>,
    modifier: Modifier = Modifier,
    orientation: LegendOrientation = LegendOrientation.Horizontal,
    style: LegendStyle = LegendStyle.Compact,
    onSelectionChanged: (Set<String>) -> Unit
) {
    var selectedIds by remember {
        mutableStateOf(items.map { it.id }.toSet())
    }

    ChartLegend(
        items = items,
        modifier = modifier,
        orientation = orientation,
        style = style,
        onItemClick = { item ->
            selectedIds = if (selectedIds.contains(item.id)) {
                // Don't allow deselecting if it's the last selected item
                if (selectedIds.size > 1) {
                    selectedIds - item.id
                } else {
                    selectedIds
                }
            } else {
                selectedIds + item.id
            }
            onSelectionChanged(selectedIds)
        },
        selectedItems = selectedIds
    )
}

/**
 * Scrollable legend for charts with many items
 */
@Composable
fun ScrollableLegend(
    items: List<LegendItem>,
    modifier: Modifier = Modifier,
    style: LegendStyle = LegendStyle.Detailed,
    maxHeight: Dp = 150.dp,
    onItemClick: ((LegendItem) -> Unit)? = null
) {
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .height(maxHeight),
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
    ) {
        Column(
            modifier = Modifier
                .padding(12.dp)
        ) {
            items.forEach { item ->
                LegendItemView(
                    item = item,
                    style = style,
                    isSelected = true,
                    onClick = onItemClick?.let { { it(item) } },
                    expanded = true
                )
            }
        }
    }
}

/**
 * Tooltip-style floating legend
 */
@Composable
fun FloatingLegend(
    item: LegendItem?,
    modifier: Modifier = Modifier,
    visible: Boolean = item != null
) {
    AnimatedVisibility(
        visible = visible && item != null,
        enter = fadeIn(),
        exit = fadeOut(),
        modifier = modifier
    ) {
        item?.let {
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 4.dp
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(it.color)
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    Column {
                        Text(
                            text = it.label,
                            style = MaterialTheme.typography.bodySmall.copy(
                                fontWeight = FontWeight.Medium
                            ),
                            color = MaterialTheme.colorScheme.onSurface
                        )

                        it.value?.let { value ->
                            Text(
                                text = value,
                                style = MaterialTheme.typography.titleSmall.copy(
                                    fontWeight = FontWeight.Bold
                                ),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }

                        it.percentage?.let { pct ->
                            Text(
                                text = ChartFormatters.formatPercent(pct),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 11.sp
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * Create legend items from chart data points
 */
fun createLegendItems(
    dataPoints: List<ChartDataPoint>,
    colorScheme: List<Color> = ChartColorSchemes.Default,
    showValues: Boolean = true,
    showPercentages: Boolean = false
): List<LegendItem> {
    val total = dataPoints.sumOf { it.value.toDouble() }.toFloat()

    return dataPoints.mapIndexed { index, point ->
        LegendItem(
            id = "${point.label}_$index",
            label = point.label,
            color = point.color ?: ChartColorSchemes.getColor(colorScheme, index),
            value = if (showValues) ChartFormatters.formatCurrency(point.value) else null,
            percentage = if (showPercentages && total > 0) point.value / total else null
        )
    }
}

/**
 * Create legend items from line series
 */
fun createLegendItemsFromSeries(
    series: List<LineSeries>,
    showLatestValue: Boolean = true
): List<LegendItem> {
    return series.map { s ->
        val latestValue = s.dataPoints.lastOrNull()?.value
        LegendItem(
            id = s.id,
            label = s.name,
            color = s.color,
            value = if (showLatestValue && latestValue != null) {
                ChartFormatters.formatCurrency(latestValue)
            } else null
        )
    }
}
