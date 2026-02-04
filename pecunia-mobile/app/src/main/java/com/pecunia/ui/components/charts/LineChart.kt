package com.pecunia.ui.components.charts

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.PointMode
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * Line chart configuration
 */
data class LineChartConfig(
    val showGrid: Boolean = true,
    val showXLabels: Boolean = true,
    val showYLabels: Boolean = true,
    val showPoints: Boolean = true,
    val showGradient: Boolean = true,
    val animateOnLoad: Boolean = true,
    val enableTouch: Boolean = true,
    val gridColor: Color = Color(0xFFE5E7EB),
    val labelColor: Color = Color(0xFF6B7280),
    val pointRadius: Float = 4f,
    val lineStrokeWidth: Float = 3f,
    val gridLineCount: Int = 5
)

/**
 * Interactive animated line chart for time series data
 */
@Composable
fun LineChart(
    series: List<LineSeries>,
    modifier: Modifier = Modifier,
    config: LineChartConfig = LineChartConfig(),
    onPointSelected: ((seriesIndex: Int, pointIndex: Int, value: TimeSeriesDataPoint) -> Unit)? = null,
    showLegend: Boolean = true,
    dateFormat: String = "MMM dd"
) {
    if (series.isEmpty() || series.all { it.dataPoints.isEmpty() }) return

    // Find data bounds
    val allPoints = series.flatMap { it.dataPoints }
    val minTimestamp = allPoints.minOfOrNull { it.timestamp } ?: 0L
    val maxTimestamp = allPoints.maxOfOrNull { it.timestamp } ?: 0L
    val minValue = allPoints.minOfOrNull { it.value } ?: 0f
    val maxValue = allPoints.maxOfOrNull { it.value } ?: 0f

    val axisBounds = ChartCalculations.calculateAxisBounds(minValue, maxValue)

    // Animation progress
    val animationProgress = remember { Animatable(0f) }

    LaunchedEffect(series) {
        if (config.animateOnLoad) {
            animationProgress.snapTo(0f)
            animationProgress.animateTo(
                targetValue = 1f,
                animationSpec = ChartAnimations.tweenSpec(durationMillis = 1000)
            )
        } else {
            animationProgress.snapTo(1f)
        }
    }

    // Touch state
    var touchX by remember { mutableFloatStateOf(-1f) }
    var selectedPointInfo by remember { mutableStateOf<SelectedPointInfo?>(null) }

    val textMeasurer = rememberTextMeasurer()
    val dateFormatter = remember(dateFormat) { SimpleDateFormat(dateFormat, Locale.getDefault()) }

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
                        top = 8.dp,
                        bottom = if (config.showXLabels) 32.dp else 8.dp
                    )
                    .pointerInput(config.enableTouch) {
                        if (config.enableTouch) {
                            detectDragGestures(
                                onDragStart = { offset -> touchX = offset.x },
                                onDrag = { change, _ ->
                                    touchX = change.position.x
                                },
                                onDragEnd = { touchX = -1f },
                                onDragCancel = { touchX = -1f }
                            )
                        }
                    }
                    .pointerInput(config.enableTouch) {
                        if (config.enableTouch) {
                            detectTapGestures { offset ->
                                touchX = offset.x
                            }
                        }
                    }
            ) {
                val chartWidth = size.width
                val chartHeight = size.height

                // Draw grid
                if (config.showGrid) {
                    drawGrid(
                        chartWidth = chartWidth,
                        chartHeight = chartHeight,
                        gridColor = config.gridColor,
                        horizontalLines = config.gridLineCount,
                        verticalLines = 5
                    )
                }

                // Draw Y axis labels
                if (config.showYLabels) {
                    drawYAxisLabels(
                        textMeasurer = textMeasurer,
                        axisBounds = axisBounds,
                        chartHeight = chartHeight,
                        labelColor = config.labelColor,
                        gridLineCount = config.gridLineCount
                    )
                }

                // Draw each series
                series.forEachIndexed { seriesIndex, lineSeries ->
                    if (lineSeries.dataPoints.isNotEmpty()) {
                        drawLineSeries(
                            series = lineSeries,
                            chartWidth = chartWidth,
                            chartHeight = chartHeight,
                            minTimestamp = minTimestamp,
                            maxTimestamp = maxTimestamp,
                            axisBounds = axisBounds,
                            animationProgress = animationProgress.value,
                            showPoints = config.showPoints && lineSeries.showPoints,
                            showGradient = config.showGradient,
                            pointRadius = config.pointRadius
                        )
                    }
                }

                // Draw touch indicator
                if (touchX >= 0 && touchX <= chartWidth) {
                    val timestamp = minTimestamp + ((touchX / chartWidth) * (maxTimestamp - minTimestamp)).toLong()

                    // Find closest point in each series
                    val closestPoints = series.mapIndexed { seriesIndex, lineSeries ->
                        val closest = lineSeries.dataPoints.minByOrNull {
                            abs(it.timestamp - timestamp)
                        }
                        if (closest != null) {
                            val x = if (maxTimestamp == minTimestamp) {
                                chartWidth / 2
                            } else {
                                ((closest.timestamp - minTimestamp).toFloat() / (maxTimestamp - minTimestamp)) * chartWidth
                            }
                            val y = chartHeight - ((closest.value - axisBounds.min) / axisBounds.range) * chartHeight
                            Triple(seriesIndex, closest, Offset(x, y))
                        } else null
                    }.filterNotNull()

                    // Draw vertical line
                    drawLine(
                        color = config.gridColor.copy(alpha = 0.8f),
                        start = Offset(touchX, 0f),
                        end = Offset(touchX, chartHeight),
                        strokeWidth = 1.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 10f))
                    )

                    // Draw highlight circles
                    closestPoints.forEach { (_, point, offset) ->
                        val color = series[closestPoints.indexOf(Triple(closestPoints.indexOfFirst { it.second == point }, point, offset))].color
                        drawCircle(
                            color = Color.White,
                            radius = config.pointRadius * 2,
                            center = offset
                        )
                        drawCircle(
                            color = series.find { it.dataPoints.contains(point) }?.color ?: Color.Gray,
                            radius = config.pointRadius * 1.5f,
                            center = offset
                        )
                    }

                    // Update selected point info
                    if (closestPoints.isNotEmpty()) {
                        val first = closestPoints.first()
                        selectedPointInfo = SelectedPointInfo(
                            x = touchX,
                            y = first.third.y,
                            points = closestPoints.map { (si, pt, _) ->
                                Pair(series[si], pt)
                            }
                        )
                    }
                }

                // Draw X axis labels
                if (config.showXLabels && maxTimestamp > minTimestamp) {
                    drawXAxisLabels(
                        textMeasurer = textMeasurer,
                        minTimestamp = minTimestamp,
                        maxTimestamp = maxTimestamp,
                        chartWidth = chartWidth,
                        chartHeight = chartHeight,
                        labelColor = config.labelColor,
                        dateFormatter = dateFormatter
                    )
                }
            }

            // Tooltip
            selectedPointInfo?.let { info ->
                if (touchX >= 0) {
                    LineChartTooltip(
                        info = info,
                        dateFormatter = dateFormatter,
                        modifier = Modifier
                            .offset {
                                val xOffset = (info.x - 80).coerceIn(0f, 200f).roundToInt()
                                val yOffset = (info.y - 80).coerceAtLeast(0f).roundToInt()
                                IntOffset(xOffset, yOffset)
                            }
                    )
                }
            }
        }

        // Legend
        if (showLegend && series.size > 1) {
            Spacer(modifier = Modifier.height(8.dp))

            val legendItems = createLegendItemsFromSeries(series)

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
 * Selected point information for tooltip
 */
private data class SelectedPointInfo(
    val x: Float,
    val y: Float,
    val points: List<Pair<LineSeries, TimeSeriesDataPoint>>
)

/**
 * Tooltip component for line chart
 */
@Composable
private fun LineChartTooltip(
    info: SelectedPointInfo,
    dateFormatter: SimpleDateFormat,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 4.dp
    ) {
        Column(
            modifier = Modifier.padding(8.dp)
        ) {
            info.points.firstOrNull()?.let { (_, point) ->
                Text(
                    text = dateFormatter.format(Date(point.timestamp)),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            info.points.forEach { (series, point) ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(vertical = 2.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .width(8.dp)
                            .height(8.dp)
                            .background(series.color, RoundedCornerShape(2.dp))
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = series.name,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = ChartFormatters.formatCurrency(point.value),
                        style = MaterialTheme.typography.bodySmall.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

/**
 * Draw grid lines
 */
private fun DrawScope.drawGrid(
    chartWidth: Float,
    chartHeight: Float,
    gridColor: Color,
    horizontalLines: Int,
    verticalLines: Int
) {
    // Horizontal grid lines
    for (i in 0..horizontalLines) {
        val y = (chartHeight / horizontalLines) * i
        drawLine(
            color = gridColor,
            start = Offset(0f, y),
            end = Offset(chartWidth, y),
            strokeWidth = 1f
        )
    }

    // Vertical grid lines
    for (i in 0..verticalLines) {
        val x = (chartWidth / verticalLines) * i
        drawLine(
            color = gridColor,
            start = Offset(x, 0f),
            end = Offset(x, chartHeight),
            strokeWidth = 1f,
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(5f, 5f))
        )
    }
}

/**
 * Draw Y axis labels
 */
private fun DrawScope.drawYAxisLabels(
    textMeasurer: TextMeasurer,
    axisBounds: AxisBounds,
    chartHeight: Float,
    labelColor: Color,
    gridLineCount: Int
) {
    for (i in 0..gridLineCount) {
        val value = axisBounds.min + (axisBounds.range / gridLineCount) * i
        val y = chartHeight - (chartHeight / gridLineCount) * i

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
 * Draw X axis labels
 */
private fun DrawScope.drawXAxisLabels(
    textMeasurer: TextMeasurer,
    minTimestamp: Long,
    maxTimestamp: Long,
    chartWidth: Float,
    chartHeight: Float,
    labelColor: Color,
    dateFormatter: SimpleDateFormat
) {
    val labelCount = 5
    for (i in 0 until labelCount) {
        val timestamp = minTimestamp + ((maxTimestamp - minTimestamp) / (labelCount - 1)) * i
        val x = (chartWidth / (labelCount - 1)) * i

        val labelText = dateFormatter.format(Date(timestamp))
        val textLayout = textMeasurer.measure(
            text = labelText,
            style = TextStyle(
                fontSize = 10.sp,
                color = labelColor
            )
        )

        drawText(
            textLayoutResult = textLayout,
            topLeft = Offset(x - textLayout.size.width / 2, chartHeight + 8f)
        )
    }
}

/**
 * Draw a single line series
 */
private fun DrawScope.drawLineSeries(
    series: LineSeries,
    chartWidth: Float,
    chartHeight: Float,
    minTimestamp: Long,
    maxTimestamp: Long,
    axisBounds: AxisBounds,
    animationProgress: Float,
    showPoints: Boolean,
    showGradient: Boolean,
    pointRadius: Float
) {
    val points = series.dataPoints
    if (points.isEmpty()) return

    val timeRange = (maxTimestamp - minTimestamp).coerceAtLeast(1)

    val pathPoints = points.mapIndexed { index, point ->
        val x = ((point.timestamp - minTimestamp).toFloat() / timeRange) * chartWidth
        val normalizedValue = (point.value - axisBounds.min) / axisBounds.range
        val animatedY = chartHeight - (normalizedValue * chartHeight * animationProgress)
        Offset(x, animatedY)
    }

    // Draw gradient fill
    if (showGradient && pathPoints.size >= 2) {
        val gradientPath = Path().apply {
            moveTo(pathPoints.first().x, chartHeight)
            pathPoints.forEach { lineTo(it.x, it.y) }
            lineTo(pathPoints.last().x, chartHeight)
            close()
        }

        drawPath(
            path = gradientPath,
            brush = Brush.verticalGradient(
                colors = listOf(
                    series.color.copy(alpha = 0.3f),
                    series.color.copy(alpha = 0f)
                )
            )
        )
    }

    // Draw line
    if (pathPoints.size >= 2) {
        val linePath = Path().apply {
            moveTo(pathPoints.first().x, pathPoints.first().y)
            for (i in 1 until pathPoints.size) {
                lineTo(pathPoints[i].x, pathPoints[i].y)
            }
        }

        drawPath(
            path = linePath,
            color = series.color,
            style = Stroke(
                width = series.strokeWidth,
                cap = StrokeCap.Round
            )
        )
    }

    // Draw points
    if (showPoints) {
        pathPoints.forEach { point ->
            drawCircle(
                color = Color.White,
                radius = pointRadius + 2f,
                center = point
            )
            drawCircle(
                color = series.color,
                radius = pointRadius,
                center = point
            )
        }
    }
}

/**
 * Simple line chart for single series data
 */
@Composable
fun SimpleLineChart(
    dataPoints: List<TimeSeriesDataPoint>,
    modifier: Modifier = Modifier,
    lineColor: Color = MaterialTheme.colorScheme.primary,
    config: LineChartConfig = LineChartConfig()
) {
    val series = remember(dataPoints, lineColor) {
        listOf(
            LineSeries(
                id = "main",
                name = "Value",
                dataPoints = dataPoints,
                color = lineColor
            )
        )
    }

    LineChart(
        series = series,
        modifier = modifier,
        config = config,
        showLegend = false
    )
}

/**
 * Sparkline - minimal line chart for inline display
 */
@Composable
fun Sparkline(
    values: List<Float>,
    modifier: Modifier = Modifier,
    lineColor: Color = MaterialTheme.colorScheme.primary,
    strokeWidth: Float = 2f,
    showFill: Boolean = true
) {
    if (values.isEmpty()) return

    val minValue = values.minOrNull() ?: 0f
    val maxValue = values.maxOrNull() ?: 0f
    val range = (maxValue - minValue).coerceAtLeast(0.001f)

    Canvas(modifier = modifier) {
        val width = size.width
        val height = size.height
        val stepX = width / (values.size - 1).coerceAtLeast(1)

        val points = values.mapIndexed { index, value ->
            val x = stepX * index
            val normalizedY = (value - minValue) / range
            val y = height - (normalizedY * height)
            Offset(x, y)
        }

        if (points.size >= 2) {
            // Draw fill
            if (showFill) {
                val fillPath = Path().apply {
                    moveTo(points.first().x, height)
                    points.forEach { lineTo(it.x, it.y) }
                    lineTo(points.last().x, height)
                    close()
                }

                drawPath(
                    path = fillPath,
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            lineColor.copy(alpha = 0.2f),
                            lineColor.copy(alpha = 0f)
                        )
                    )
                )
            }

            // Draw line
            val linePath = Path().apply {
                moveTo(points.first().x, points.first().y)
                for (i in 1 until points.size) {
                    lineTo(points[i].x, points[i].y)
                }
            }

            drawPath(
                path = linePath,
                color = lineColor,
                style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
            )
        }
    }
}

/**
 * Comparison line chart with area between two lines
 */
@Composable
fun ComparisonLineChart(
    series1: LineSeries,
    series2: LineSeries,
    modifier: Modifier = Modifier,
    config: LineChartConfig = LineChartConfig(),
    showDifference: Boolean = true
) {
    LineChart(
        series = listOf(series1, series2),
        modifier = modifier,
        config = config.copy(showGradient = false),
        showLegend = true
    )
}
