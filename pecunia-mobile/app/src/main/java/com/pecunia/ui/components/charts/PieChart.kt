package com.pecunia.ui.components.charts

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Pie chart configuration
 */
data class PieChartConfig(
    val showLabels: Boolean = false,
    val showPercentages: Boolean = true,
    val startAngle: Float = -90f,
    val animateOnLoad: Boolean = true,
    val enableTouch: Boolean = true,
    val selectedScaleFactor: Float = 1.08f,
    val gapAngle: Float = 2f,
    val strokeWidth: Float = 0f, // 0 for filled, > 0 for stroke
    val colorScheme: List<Color> = ChartColorSchemes.Default
)

/**
 * Interactive animated pie chart
 */
@Composable
fun PieChart(
    dataPoints: List<ChartDataPoint>,
    modifier: Modifier = Modifier,
    config: PieChartConfig = PieChartConfig(),
    onSegmentSelected: ((Int?) -> Unit)? = null,
    showLegend: Boolean = true,
    legendOrientation: LegendOrientation = LegendOrientation.Horizontal
) {
    if (dataPoints.isEmpty()) return

    val total = dataPoints.sumOf { it.value.toDouble() }.toFloat()
    if (total <= 0f) return

    // Animation progress
    val animationProgress = remember { Animatable(0f) }

    LaunchedEffect(dataPoints) {
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

    // Selected segment state
    var selectedIndex by remember { mutableStateOf<Int?>(null) }

    // Calculate sweep angles
    val sweepAngles = remember(dataPoints) {
        dataPoints.map { (it.value / total) * 360f }
    }

    // Colors for each segment
    val colors = remember(dataPoints, config.colorScheme) {
        dataPoints.mapIndexed { index, point ->
            point.color ?: ChartColorSchemes.getColor(config.colorScheme, index)
        }
    }

    Column(modifier = modifier) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f),
            contentAlignment = Alignment.Center
        ) {
            Canvas(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp)
                    .pointerInput(config.enableTouch) {
                        if (config.enableTouch) {
                            detectTapGestures { offset ->
                                val center = Offset(size.width / 2f, size.height / 2f)
                                val radius = min(size.width, size.height) / 2f

                                val tappedIndex = findTappedSegment(
                                    offset = offset,
                                    center = center,
                                    radius = radius,
                                    sweepAngles = sweepAngles,
                                    startAngle = config.startAngle,
                                    gapAngle = config.gapAngle
                                )

                                selectedIndex = if (selectedIndex == tappedIndex) null else tappedIndex
                                onSegmentSelected?.invoke(selectedIndex)
                            }
                        }
                    }
            ) {
                val canvasSize = size
                val center = Offset(canvasSize.width / 2f, canvasSize.height / 2f)
                val radius = min(canvasSize.width, canvasSize.height) / 2f * 0.85f

                drawPieSegments(
                    center = center,
                    radius = radius,
                    sweepAngles = sweepAngles,
                    colors = colors,
                    startAngle = config.startAngle,
                    gapAngle = config.gapAngle,
                    strokeWidth = config.strokeWidth,
                    animationProgress = animationProgress.value,
                    selectedIndex = selectedIndex,
                    selectedScaleFactor = config.selectedScaleFactor
                )
            }
        }

        // Legend
        if (showLegend) {
            Spacer(modifier = Modifier.height(16.dp))

            val legendItems = remember(dataPoints, colors) {
                dataPoints.mapIndexed { index, point ->
                    LegendItem(
                        id = "${point.label}_$index",
                        label = point.label,
                        color = colors[index],
                        value = ChartFormatters.formatCurrency(point.value),
                        percentage = point.value / total
                    )
                }
            }

            ChartLegend(
                items = legendItems,
                orientation = legendOrientation,
                style = if (config.showPercentages) LegendStyle.Full else LegendStyle.Detailed,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

/**
 * Draw pie segments with animation and selection support
 */
private fun DrawScope.drawPieSegments(
    center: Offset,
    radius: Float,
    sweepAngles: List<Float>,
    colors: List<Color>,
    startAngle: Float,
    gapAngle: Float,
    strokeWidth: Float,
    animationProgress: Float,
    selectedIndex: Int?,
    selectedScaleFactor: Float
) {
    var currentAngle = startAngle
    val totalGap = gapAngle * sweepAngles.size
    val availableSweep = 360f - totalGap
    val scaleFactor = availableSweep / 360f

    sweepAngles.forEachIndexed { index, sweep ->
        val adjustedSweep = sweep * scaleFactor * animationProgress

        if (adjustedSweep > 0f) {
            val isSelected = selectedIndex == index
            val segmentRadius = if (isSelected) radius * selectedScaleFactor else radius

            // Calculate offset for selected segment
            val midAngle = currentAngle + adjustedSweep / 2f
            val offsetDistance = if (isSelected) radius * 0.05f else 0f
            val offsetX = cos(midAngle * PI.toFloat() / 180f) * offsetDistance
            val offsetY = sin(midAngle * PI.toFloat() / 180f) * offsetDistance
            val segmentCenter = Offset(center.x + offsetX, center.y + offsetY)

            if (strokeWidth > 0f) {
                // Stroke style
                drawArc(
                    color = colors[index],
                    startAngle = currentAngle,
                    sweepAngle = adjustedSweep,
                    useCenter = false,
                    topLeft = Offset(
                        segmentCenter.x - segmentRadius,
                        segmentCenter.y - segmentRadius
                    ),
                    size = Size(segmentRadius * 2, segmentRadius * 2),
                    style = Stroke(
                        width = strokeWidth,
                        cap = StrokeCap.Round
                    )
                )
            } else {
                // Filled style
                drawArc(
                    color = colors[index],
                    startAngle = currentAngle,
                    sweepAngle = adjustedSweep,
                    useCenter = true,
                    topLeft = Offset(
                        segmentCenter.x - segmentRadius,
                        segmentCenter.y - segmentRadius
                    ),
                    size = Size(segmentRadius * 2, segmentRadius * 2)
                )
            }
        }

        currentAngle += adjustedSweep + gapAngle
    }
}

/**
 * Find which segment was tapped
 */
private fun findTappedSegment(
    offset: Offset,
    center: Offset,
    radius: Float,
    sweepAngles: List<Float>,
    startAngle: Float,
    gapAngle: Float
): Int? {
    // Check if tap is within the pie
    val dx = offset.x - center.x
    val dy = offset.y - center.y
    val distance = sqrt(dx * dx + dy * dy)

    if (distance > radius * 1.1f || distance < radius * 0.1f) {
        return null
    }

    // Calculate angle of tap
    var angle = atan2(dy, dx) * 180f / PI.toFloat()
    angle = (angle - startAngle + 360f) % 360f

    // Find segment
    var currentAngle = 0f
    val totalGap = gapAngle * sweepAngles.size
    val availableSweep = 360f - totalGap
    val scaleFactor = availableSweep / 360f

    sweepAngles.forEachIndexed { index, sweep ->
        val adjustedSweep = sweep * scaleFactor
        if (angle >= currentAngle && angle < currentAngle + adjustedSweep) {
            return index
        }
        currentAngle += adjustedSweep + gapAngle
    }

    return null
}

/**
 * Pie chart with controlled selection state
 */
@Composable
fun ControlledPieChart(
    dataPoints: List<ChartDataPoint>,
    selectedIndex: Int?,
    onSegmentSelected: (Int?) -> Unit,
    modifier: Modifier = Modifier,
    config: PieChartConfig = PieChartConfig()
) {
    if (dataPoints.isEmpty()) return

    val total = dataPoints.sumOf { it.value.toDouble() }.toFloat()
    if (total <= 0f) return

    val animationProgress = remember { Animatable(0f) }

    LaunchedEffect(dataPoints) {
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

    val sweepAngles = remember(dataPoints) {
        dataPoints.map { (it.value / total) * 360f }
    }

    val colors = remember(dataPoints, config.colorScheme) {
        dataPoints.mapIndexed { index, point ->
            point.color ?: ChartColorSchemes.getColor(config.colorScheme, index)
        }
    }

    Canvas(
        modifier = modifier
            .aspectRatio(1f)
            .pointerInput(config.enableTouch) {
                if (config.enableTouch) {
                    detectTapGestures { offset ->
                        val center = Offset(size.width / 2f, size.height / 2f)
                        val radius = min(size.width, size.height) / 2f

                        val tappedIndex = findTappedSegment(
                            offset = offset,
                            center = center,
                            radius = radius,
                            sweepAngles = sweepAngles,
                            startAngle = config.startAngle,
                            gapAngle = config.gapAngle
                        )

                        onSegmentSelected(if (selectedIndex == tappedIndex) null else tappedIndex)
                    }
                }
            }
    ) {
        val canvasSize = size
        val center = Offset(canvasSize.width / 2f, canvasSize.height / 2f)
        val radius = min(canvasSize.width, canvasSize.height) / 2f * 0.85f

        drawPieSegments(
            center = center,
            radius = radius,
            sweepAngles = sweepAngles,
            colors = colors,
            startAngle = config.startAngle,
            gapAngle = config.gapAngle,
            strokeWidth = config.strokeWidth,
            animationProgress = animationProgress.value,
            selectedIndex = selectedIndex,
            selectedScaleFactor = config.selectedScaleFactor
        )
    }
}

/**
 * Simple pie chart without legend for compact display
 */
@Composable
fun CompactPieChart(
    dataPoints: List<ChartDataPoint>,
    modifier: Modifier = Modifier,
    colorScheme: List<Color> = ChartColorSchemes.Default,
    animate: Boolean = true
) {
    PieChart(
        dataPoints = dataPoints,
        modifier = modifier,
        config = PieChartConfig(
            showLabels = false,
            showPercentages = false,
            animateOnLoad = animate,
            enableTouch = false,
            gapAngle = 1f,
            colorScheme = colorScheme
        ),
        showLegend = false
    )
}
