package com.pecunia.ui.components.charts

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.max

/**
 * Bar chart display mode
 */
enum class BarChartMode {
    Grouped,    // Bars side by side
    Stacked     // Bars stacked on top of each other
}

/**
 * Bar chart configuration
 */
data class BarChartConfig(
    val mode: BarChartMode = BarChartMode.Grouped,
    val showGrid: Boolean = true,
    val showXLabels: Boolean = true,
    val showYLabels: Boolean = true,
    val showValues: Boolean = false,
    val animateOnLoad: Boolean = true,
    val enableTouch: Boolean = true,
    val barCornerRadius: Dp = 4.dp,
    val barSpacing: Dp = 4.dp,
    val groupSpacing: Dp = 16.dp,
    val gridColor: Color = Color(0xFFE5E7EB),
    val labelColor: Color = Color(0xFF6B7280),
    val gridLineCount: Int = 5,
    val colorScheme: List<Color> = ChartColorSchemes.Default
)

/**
 * Interactive animated bar chart
 */
@Composable
fun BarChart(
    groups: List<BarGroup>,
    modifier: Modifier = Modifier,
    config: BarChartConfig = BarChartConfig(),
    onBarSelected: ((groupIndex: Int, barIndex: Int, value: BarValue) -> Unit)? = null,
    showLegend: Boolean = true
) {
    if (groups.isEmpty()) return

    // Calculate bounds
    val maxValue = when (config.mode) {
        BarChartMode.Grouped -> groups.flatMap { it.values }.maxOfOrNull { it.value } ?: 0f
        BarChartMode.Stacked -> groups.maxOfOrNull { group ->
            group.values.sumOf { it.value.toDouble() }.toFloat()
        } ?: 0f
    }

    val axisBounds = ChartCalculations.calculateAxisBounds(0f, maxValue)

    // Animation progress
    val animationProgress = remember { Animatable(0f) }

    LaunchedEffect(groups) {
        if (config.animateOnLoad) {
            animationProgress.snapTo(0f)
            animationProgress.animateTo(
                targetValue = 1f,
                animationSpec = ChartAnimations.tweenSpec(durationMillis = 800)
            )
        } else {
            animationProgress.snapTo(1f)
        }
    }

    // Selection state
    var selectedGroup by remember { mutableIntStateOf(-1) }
    var selectedBar by remember { mutableIntStateOf(-1) }

    val textMeasurer = rememberTextMeasurer()

    // Get unique bar labels for legend
    val uniqueBarLabels = remember(groups) {
        groups.flatMap { it.values }.map { it.label }.distinct()
    }

    Column(modifier = modifier) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
        ) {
            Canvas(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(
                        start = if (config.showYLabels) 48.dp else 8.dp,
                        end = 8.dp,
                        top = 16.dp,
                        bottom = if (config.showXLabels) 40.dp else 8.dp
                    )
                    .pointerInput(config.enableTouch) {
                        if (config.enableTouch) {
                            detectTapGestures { offset ->
                                // Find tapped bar
                                val result = findTappedBar(
                                    offset = offset,
                                    groups = groups,
                                    chartWidth = size.width.toFloat(),
                                    chartHeight = size.height.toFloat(),
                                    axisBounds = axisBounds,
                                    config = config
                                )

                                if (result != null) {
                                    val (gi, bi) = result
                                    if (selectedGroup == gi && selectedBar == bi) {
                                        selectedGroup = -1
                                        selectedBar = -1
                                    } else {
                                        selectedGroup = gi
                                        selectedBar = bi
                                        onBarSelected?.invoke(gi, bi, groups[gi].values[bi])
                                    }
                                } else {
                                    selectedGroup = -1
                                    selectedBar = -1
                                }
                            }
                        }
                    }
            ) {
                val chartWidth = size.width
                val chartHeight = size.height

                // Draw grid
                if (config.showGrid) {
                    drawBarChartGrid(
                        chartWidth = chartWidth,
                        chartHeight = chartHeight,
                        gridColor = config.gridColor,
                        horizontalLines = config.gridLineCount
                    )
                }

                // Draw Y axis labels
                if (config.showYLabels) {
                    drawBarChartYLabels(
                        textMeasurer = textMeasurer,
                        axisBounds = axisBounds,
                        chartHeight = chartHeight,
                        labelColor = config.labelColor,
                        gridLineCount = config.gridLineCount
                    )
                }

                // Draw bars
                when (config.mode) {
                    BarChartMode.Grouped -> {
                        drawGroupedBars(
                            groups = groups,
                            chartWidth = chartWidth,
                            chartHeight = chartHeight,
                            axisBounds = axisBounds,
                            config = config,
                            animationProgress = animationProgress.value,
                            selectedGroup = selectedGroup,
                            selectedBar = selectedBar,
                            textMeasurer = textMeasurer
                        )
                    }
                    BarChartMode.Stacked -> {
                        drawStackedBars(
                            groups = groups,
                            chartWidth = chartWidth,
                            chartHeight = chartHeight,
                            axisBounds = axisBounds,
                            config = config,
                            animationProgress = animationProgress.value,
                            selectedGroup = selectedGroup,
                            selectedBar = selectedBar,
                            textMeasurer = textMeasurer
                        )
                    }
                }

                // Draw X axis labels
                if (config.showXLabels) {
                    drawBarChartXLabels(
                        textMeasurer = textMeasurer,
                        groups = groups,
                        chartWidth = chartWidth,
                        chartHeight = chartHeight,
                        labelColor = config.labelColor,
                        config = config
                    )
                }
            }
        }

        // Legend
        if (showLegend && uniqueBarLabels.size > 1) {
            Spacer(modifier = Modifier.height(8.dp))

            val legendItems = uniqueBarLabels.mapIndexed { index, label ->
                val barValue = groups.flatMap { it.values }.find { it.label == label }
                LegendItem(
                    id = label,
                    label = label,
                    color = barValue?.color ?: ChartColorSchemes.getColor(config.colorScheme, index)
                )
            }

            ChartLegend(
                items = legendItems,
                orientation = LegendOrientation.Horizontal,
                style = LegendStyle.Compact,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

/**
 * Find which bar was tapped
 */
private fun findTappedBar(
    offset: Offset,
    groups: List<BarGroup>,
    chartWidth: Float,
    chartHeight: Float,
    axisBounds: AxisBounds,
    config: BarChartConfig
): Pair<Int, Int>? {
    val groupCount = groups.size
    val groupWidth = chartWidth / groupCount
    val groupSpacingPx = config.groupSpacing.value
    val barSpacingPx = config.barSpacing.value

    val groupIndex = (offset.x / groupWidth).toInt().coerceIn(0, groupCount - 1)
    val group = groups[groupIndex]

    val barCount = group.values.size
    val availableGroupWidth = groupWidth - groupSpacingPx
    val barWidth = (availableGroupWidth - (barSpacingPx * (barCount - 1))) / barCount

    val groupStartX = groupIndex * groupWidth + groupSpacingPx / 2

    for (barIndex in 0 until barCount) {
        val barX = groupStartX + barIndex * (barWidth + barSpacingPx)
        val barValue = group.values[barIndex]
        val barHeight = (barValue.value / axisBounds.max) * chartHeight
        val barTop = chartHeight - barHeight

        if (offset.x >= barX && offset.x <= barX + barWidth &&
            offset.y >= barTop && offset.y <= chartHeight) {
            return Pair(groupIndex, barIndex)
        }
    }

    return null
}

/**
 * Draw grid for bar chart
 */
private fun DrawScope.drawBarChartGrid(
    chartWidth: Float,
    chartHeight: Float,
    gridColor: Color,
    horizontalLines: Int
) {
    for (i in 0..horizontalLines) {
        val y = (chartHeight / horizontalLines) * i
        drawLine(
            color = gridColor,
            start = Offset(0f, y),
            end = Offset(chartWidth, y),
            strokeWidth = 1f
        )
    }
}

/**
 * Draw Y axis labels for bar chart
 */
private fun DrawScope.drawBarChartYLabels(
    textMeasurer: TextMeasurer,
    axisBounds: AxisBounds,
    chartHeight: Float,
    labelColor: Color,
    gridLineCount: Int
) {
    for (i in 0..gridLineCount) {
        val value = axisBounds.min + (axisBounds.range / gridLineCount) * (gridLineCount - i)
        val y = (chartHeight / gridLineCount) * i

        val labelText = ChartFormatters.formatCompact(value)
        val textLayout = textMeasurer.measure(
            text = labelText,
            style = TextStyle(
                fontSize = 10.sp,
                color = labelColor
            )
        )

        drawText(
            textLayoutResult = textLayout,
            topLeft = Offset(-textLayout.size.width - 8f, y - textLayout.size.height / 2)
        )
    }
}

/**
 * Draw X axis labels for bar chart
 */
private fun DrawScope.drawBarChartXLabels(
    textMeasurer: TextMeasurer,
    groups: List<BarGroup>,
    chartWidth: Float,
    chartHeight: Float,
    labelColor: Color,
    config: BarChartConfig
) {
    val groupWidth = chartWidth / groups.size

    groups.forEachIndexed { index, group ->
        val centerX = groupWidth * index + groupWidth / 2

        val textLayout = textMeasurer.measure(
            text = group.label,
            style = TextStyle(
                fontSize = 10.sp,
                color = labelColor,
                textAlign = TextAlign.Center
            ),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )

        drawText(
            textLayoutResult = textLayout,
            topLeft = Offset(centerX - textLayout.size.width / 2, chartHeight + 8f)
        )
    }
}

/**
 * Draw grouped bars
 */
private fun DrawScope.drawGroupedBars(
    groups: List<BarGroup>,
    chartWidth: Float,
    chartHeight: Float,
    axisBounds: AxisBounds,
    config: BarChartConfig,
    animationProgress: Float,
    selectedGroup: Int,
    selectedBar: Int,
    textMeasurer: TextMeasurer
) {
    val groupCount = groups.size
    val groupWidth = chartWidth / groupCount
    val groupSpacingPx = config.groupSpacing.value
    val barSpacingPx = config.barSpacing.value
    val cornerRadiusPx = config.barCornerRadius.value

    groups.forEachIndexed { groupIndex, group ->
        val barCount = group.values.size
        val availableGroupWidth = groupWidth - groupSpacingPx
        val barWidth = (availableGroupWidth - (barSpacingPx * (barCount - 1).coerceAtLeast(0))) / barCount.coerceAtLeast(1)
        val groupStartX = groupIndex * groupWidth + groupSpacingPx / 2

        group.values.forEachIndexed { barIndex, barValue ->
            val barX = groupStartX + barIndex * (barWidth + barSpacingPx)
            val normalizedHeight = barValue.value / axisBounds.max
            val barHeight = normalizedHeight * chartHeight * animationProgress
            val barTop = chartHeight - barHeight

            val isSelected = groupIndex == selectedGroup && barIndex == selectedBar
            val alpha = if (selectedGroup >= 0 && !isSelected) 0.4f else 1f

            // Draw bar with rounded top corners
            val barPath = Path().apply {
                addRoundRect(
                    RoundRect(
                        rect = Rect(
                            offset = Offset(barX, barTop),
                            size = Size(barWidth, barHeight)
                        ),
                        topLeft = CornerRadius(cornerRadiusPx, cornerRadiusPx),
                        topRight = CornerRadius(cornerRadiusPx, cornerRadiusPx),
                        bottomLeft = CornerRadius(0f, 0f),
                        bottomRight = CornerRadius(0f, 0f)
                    )
                )
            }

            drawPath(
                path = barPath,
                color = barValue.color.copy(alpha = alpha)
            )

            // Draw value on top if configured
            if (config.showValues && animationProgress > 0.9f) {
                val valueText = ChartFormatters.formatCompact(barValue.value)
                val textLayout = textMeasurer.measure(
                    text = valueText,
                    style = TextStyle(
                        fontSize = 9.sp,
                        color = config.labelColor
                    )
                )

                drawText(
                    textLayoutResult = textLayout,
                    topLeft = Offset(
                        barX + barWidth / 2 - textLayout.size.width / 2,
                        barTop - textLayout.size.height - 4f
                    )
                )
            }
        }
    }
}

/**
 * Draw stacked bars
 */
private fun DrawScope.drawStackedBars(
    groups: List<BarGroup>,
    chartWidth: Float,
    chartHeight: Float,
    axisBounds: AxisBounds,
    config: BarChartConfig,
    animationProgress: Float,
    selectedGroup: Int,
    selectedBar: Int,
    textMeasurer: TextMeasurer
) {
    val groupCount = groups.size
    val groupWidth = chartWidth / groupCount
    val groupSpacingPx = config.groupSpacing.value
    val barWidth = groupWidth - groupSpacingPx
    val cornerRadiusPx = config.barCornerRadius.value

    groups.forEachIndexed { groupIndex, group ->
        val groupStartX = groupIndex * groupWidth + groupSpacingPx / 2
        var currentBottom = chartHeight
        val totalValue = group.values.sumOf { it.value.toDouble() }.toFloat()

        group.values.forEachIndexed { barIndex, barValue ->
            val normalizedHeight = barValue.value / axisBounds.max
            val barHeight = normalizedHeight * chartHeight * animationProgress
            val barTop = currentBottom - barHeight

            val isSelected = groupIndex == selectedGroup && barIndex == selectedBar
            val alpha = if (selectedGroup >= 0 && !isSelected) 0.4f else 1f

            // Determine corner radius based on position
            val isTop = barIndex == group.values.lastIndex
            val isBottom = barIndex == 0

            val barPath = Path().apply {
                addRoundRect(
                    RoundRect(
                        rect = Rect(
                            offset = Offset(groupStartX, barTop),
                            size = Size(barWidth, barHeight)
                        ),
                        topLeft = if (isTop) CornerRadius(cornerRadiusPx, cornerRadiusPx) else CornerRadius(0f, 0f),
                        topRight = if (isTop) CornerRadius(cornerRadiusPx, cornerRadiusPx) else CornerRadius(0f, 0f),
                        bottomLeft = if (isBottom) CornerRadius(cornerRadiusPx, cornerRadiusPx) else CornerRadius(0f, 0f),
                        bottomRight = if (isBottom) CornerRadius(cornerRadiusPx, cornerRadiusPx) else CornerRadius(0f, 0f)
                    )
                )
            }

            drawPath(
                path = barPath,
                color = barValue.color.copy(alpha = alpha)
            )

            currentBottom = barTop
        }

        // Draw total value on top if configured
        if (config.showValues && animationProgress > 0.9f) {
            val totalHeight = (totalValue / axisBounds.max) * chartHeight
            val topY = chartHeight - totalHeight

            val valueText = ChartFormatters.formatCompact(totalValue)
            val textLayout = textMeasurer.measure(
                text = valueText,
                style = TextStyle(
                    fontSize = 9.sp,
                    color = config.labelColor
                )
            )

            drawText(
                textLayoutResult = textLayout,
                topLeft = Offset(
                    groupStartX + barWidth / 2 - textLayout.size.width / 2,
                    topY - textLayout.size.height - 4f
                )
            )
        }
    }
}

/**
 * Simple vertical bar chart for basic data
 */
@Composable
fun SimpleBarChart(
    dataPoints: List<ChartDataPoint>,
    modifier: Modifier = Modifier,
    barColor: Color = MaterialTheme.colorScheme.primary,
    config: BarChartConfig = BarChartConfig()
) {
    val groups = remember(dataPoints, barColor) {
        dataPoints.map { point ->
            BarGroup(
                label = point.label,
                values = listOf(
                    BarValue(
                        value = point.value,
                        label = point.label,
                        color = point.color ?: barColor
                    )
                )
            )
        }
    }

    BarChart(
        groups = groups,
        modifier = modifier,
        config = config,
        showLegend = false
    )
}

/**
 * Horizontal bar chart
 */
@Composable
fun HorizontalBarChart(
    dataPoints: List<ChartDataPoint>,
    modifier: Modifier = Modifier,
    config: BarChartConfig = BarChartConfig(),
    colorScheme: List<Color> = ChartColorSchemes.Default
) {
    if (dataPoints.isEmpty()) return

    val maxValue = dataPoints.maxOfOrNull { it.value } ?: 0f
    val axisBounds = ChartCalculations.calculateAxisBounds(0f, maxValue)

    val animationProgress = remember { Animatable(0f) }

    LaunchedEffect(dataPoints) {
        if (config.animateOnLoad) {
            animationProgress.snapTo(0f)
            animationProgress.animateTo(
                targetValue = 1f,
                animationSpec = ChartAnimations.tweenSpec(durationMillis = 800)
            )
        } else {
            animationProgress.snapTo(1f)
        }
    }

    val textMeasurer = rememberTextMeasurer()

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height((dataPoints.size * 40).dp)
            .padding(start = 80.dp, end = 16.dp, top = 8.dp, bottom = 8.dp)
    ) {
        val chartWidth = size.width
        val chartHeight = size.height
        val barHeight = chartHeight / dataPoints.size * 0.6f
        val barSpacing = chartHeight / dataPoints.size

        dataPoints.forEachIndexed { index, point ->
            val barWidth = (point.value / axisBounds.max) * chartWidth * animationProgress.value
            val barY = index * barSpacing + (barSpacing - barHeight) / 2
            val color = point.color ?: ChartColorSchemes.getColor(colorScheme, index)

            // Draw label
            val labelLayout = textMeasurer.measure(
                text = point.label,
                style = TextStyle(
                    fontSize = 11.sp,
                    color = config.labelColor
                )
            )

            drawText(
                textLayoutResult = labelLayout,
                topLeft = Offset(-labelLayout.size.width - 8f, barY + barHeight / 2 - labelLayout.size.height / 2)
            )

            // Draw bar
            val barPath = Path().apply {
                addRoundRect(
                    RoundRect(
                        rect = Rect(
                            offset = Offset(0f, barY),
                            size = Size(barWidth, barHeight)
                        ),
                        topRight = CornerRadius(config.barCornerRadius.value, config.barCornerRadius.value),
                        bottomRight = CornerRadius(config.barCornerRadius.value, config.barCornerRadius.value)
                    )
                )
            }

            drawPath(
                path = barPath,
                color = color
            )

            // Draw value
            if (config.showValues && animationProgress.value > 0.9f) {
                val valueLayout = textMeasurer.measure(
                    text = ChartFormatters.formatCompact(point.value),
                    style = TextStyle(
                        fontSize = 10.sp,
                        color = config.labelColor
                    )
                )

                drawText(
                    textLayoutResult = valueLayout,
                    topLeft = Offset(barWidth + 8f, barY + barHeight / 2 - valueLayout.size.height / 2)
                )
            }
        }
    }
}

/**
 * Comparison bar chart for showing positive and negative values
 */
@Composable
fun ComparisonBarChart(
    positiveValues: List<ChartDataPoint>,
    negativeValues: List<ChartDataPoint>,
    modifier: Modifier = Modifier,
    positiveColor: Color = Color(0xFF22C55E),
    negativeColor: Color = Color(0xFFEF4444),
    config: BarChartConfig = BarChartConfig()
) {
    require(positiveValues.size == negativeValues.size) {
        "Positive and negative value lists must have the same size"
    }

    val groups = positiveValues.mapIndexed { index, positive ->
        val negative = negativeValues[index]
        BarGroup(
            label = positive.label,
            values = listOf(
                BarValue(positive.value, "Income", positiveColor),
                BarValue(negative.value, "Expense", negativeColor)
            )
        )
    }

    BarChart(
        groups = groups,
        modifier = modifier,
        config = config.copy(mode = BarChartMode.Grouped),
        showLegend = true
    )
}
