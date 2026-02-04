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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Donut chart configuration
 */
data class DonutChartConfig(
    val strokeWidth: Dp = 40.dp,
    val startAngle: Float = -90f,
    val gapAngle: Float = 3f,
    val animateOnLoad: Boolean = true,
    val enableTouch: Boolean = true,
    val selectedScaleFactor: Float = 1.1f,
    val showCenterText: Boolean = true,
    val colorScheme: List<Color> = ChartColorSchemes.Default
)

/**
 * Center text configuration for donut chart
 */
data class DonutCenterText(
    val title: String,
    val value: String,
    val subtitle: String? = null
)

/**
 * Animated donut chart with center text
 */
@Composable
fun DonutChart(
    dataPoints: List<ChartDataPoint>,
    modifier: Modifier = Modifier,
    config: DonutChartConfig = DonutChartConfig(),
    centerText: DonutCenterText? = null,
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
                animationSpec = ChartAnimations.tweenSpec(durationMillis = 1200)
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

    // Dynamic center text based on selection
    val displayCenterText = remember(selectedIndex, centerText, dataPoints) {
        when {
            selectedIndex != null && selectedIndex in dataPoints.indices -> {
                val point = dataPoints[selectedIndex!!]
                DonutCenterText(
                    title = point.label,
                    value = ChartFormatters.formatCurrency(point.value),
                    subtitle = ChartFormatters.formatPercent(point.value / total)
                )
            }
            centerText != null -> centerText
            else -> DonutCenterText(
                title = "Total",
                value = ChartFormatters.formatCurrency(total),
                subtitle = "${dataPoints.size} items"
            )
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
                    .padding(8.dp)
                    .pointerInput(config.enableTouch) {
                        if (config.enableTouch) {
                            detectTapGestures { offset ->
                                val center = Offset(size.width / 2f, size.height / 2f)
                                val outerRadius = min(size.width, size.height) / 2f
                                val innerRadius = outerRadius - config.strokeWidth.toPx()

                                val tappedIndex = findTappedDonutSegment(
                                    offset = offset,
                                    center = center,
                                    innerRadius = innerRadius,
                                    outerRadius = outerRadius,
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
                val outerRadius = min(canvasSize.width, canvasSize.height) / 2f * 0.9f
                val strokeWidthPx = config.strokeWidth.toPx()

                drawDonutSegments(
                    center = center,
                    radius = outerRadius - strokeWidthPx / 2f,
                    strokeWidth = strokeWidthPx,
                    sweepAngles = sweepAngles,
                    colors = colors,
                    startAngle = config.startAngle,
                    gapAngle = config.gapAngle,
                    animationProgress = animationProgress.value,
                    selectedIndex = selectedIndex,
                    selectedScaleFactor = config.selectedScaleFactor
                )
            }

            // Center text
            if (config.showCenterText) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                    modifier = Modifier.padding(config.strokeWidth + 16.dp)
                ) {
                    Text(
                        text = displayCenterText.title,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )

                    Text(
                        text = displayCenterText.value,
                        style = MaterialTheme.typography.headlineSmall.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = if (selectedIndex != null) {
                            colors.getOrNull(selectedIndex!!) ?: MaterialTheme.colorScheme.onSurface
                        } else {
                            MaterialTheme.colorScheme.onSurface
                        },
                        textAlign = TextAlign.Center
                    )

                    displayCenterText.subtitle?.let { subtitle ->
                        Text(
                            text = subtitle,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = TextAlign.Center
                        )
                    }
                }
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
                style = LegendStyle.Full,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

/**
 * Draw donut segments with animation
 */
private fun DrawScope.drawDonutSegments(
    center: Offset,
    radius: Float,
    strokeWidth: Float,
    sweepAngles: List<Float>,
    colors: List<Color>,
    startAngle: Float,
    gapAngle: Float,
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

        if (adjustedSweep > 0.1f) {
            val isSelected = selectedIndex == index
            val segmentStrokeWidth = if (isSelected) strokeWidth * selectedScaleFactor else strokeWidth
            val segmentRadius = if (isSelected) radius * 1.02f else radius

            // Calculate offset for selected segment
            val midAngle = currentAngle + adjustedSweep / 2f
            val offsetDistance = if (isSelected) radius * 0.03f else 0f
            val offsetX = cos(midAngle * PI.toFloat() / 180f) * offsetDistance
            val offsetY = sin(midAngle * PI.toFloat() / 180f) * offsetDistance
            val segmentCenter = Offset(center.x + offsetX, center.y + offsetY)

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
                    width = segmentStrokeWidth,
                    cap = StrokeCap.Butt
                )
            )
        }

        currentAngle += adjustedSweep + gapAngle
    }
}

/**
 * Find which donut segment was tapped
 */
private fun findTappedDonutSegment(
    offset: Offset,
    center: Offset,
    innerRadius: Float,
    outerRadius: Float,
    sweepAngles: List<Float>,
    startAngle: Float,
    gapAngle: Float
): Int? {
    val dx = offset.x - center.x
    val dy = offset.y - center.y
    val distance = sqrt(dx * dx + dy * dy)

    // Check if tap is within the donut ring
    if (distance > outerRadius * 1.1f || distance < innerRadius * 0.9f) {
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
 * Progress donut chart for showing a single value as progress
 */
@Composable
fun ProgressDonutChart(
    progress: Float, // 0.0 to 1.0
    modifier: Modifier = Modifier,
    progressColor: Color = MaterialTheme.colorScheme.primary,
    trackColor: Color = MaterialTheme.colorScheme.surfaceVariant,
    strokeWidth: Dp = 24.dp,
    centerText: DonutCenterText? = null,
    animate: Boolean = true
) {
    val animatedProgress = remember { Animatable(0f) }

    LaunchedEffect(progress) {
        if (animate) {
            animatedProgress.animateTo(
                targetValue = progress.coerceIn(0f, 1f),
                animationSpec = ChartAnimations.tweenSpec(durationMillis = 1000)
            )
        } else {
            animatedProgress.snapTo(progress.coerceIn(0f, 1f))
        }
    }

    Box(
        modifier = modifier.aspectRatio(1f),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .padding(8.dp)
        ) {
            val canvasSize = size
            val center = Offset(canvasSize.width / 2f, canvasSize.height / 2f)
            val radius = min(canvasSize.width, canvasSize.height) / 2f - strokeWidth.toPx() / 2f
            val strokeWidthPx = strokeWidth.toPx()

            // Draw track
            drawArc(
                color = trackColor,
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                topLeft = Offset(center.x - radius, center.y - radius),
                size = Size(radius * 2, radius * 2),
                style = Stroke(width = strokeWidthPx, cap = StrokeCap.Round)
            )

            // Draw progress
            drawArc(
                color = progressColor,
                startAngle = -90f,
                sweepAngle = 360f * animatedProgress.value,
                useCenter = false,
                topLeft = Offset(center.x - radius, center.y - radius),
                size = Size(radius * 2, radius * 2),
                style = Stroke(width = strokeWidthPx, cap = StrokeCap.Round)
            )
        }

        // Center text
        centerText?.let { text ->
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier.padding(strokeWidth + 16.dp)
            ) {
                Text(
                    text = text.title,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Text(
                    text = text.value,
                    style = MaterialTheme.typography.headlineMedium.copy(
                        fontWeight = FontWeight.Bold
                    ),
                    color = progressColor
                )

                text.subtitle?.let { subtitle ->
                    Text(
                        text = subtitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

/**
 * Multi-ring donut chart for comparing multiple values
 */
@Composable
fun MultiRingDonutChart(
    rings: List<DonutRingData>,
    modifier: Modifier = Modifier,
    strokeWidth: Dp = 16.dp,
    ringSpacing: Dp = 6.dp,
    animate: Boolean = true
) {
    val animationProgress = remember { Animatable(0f) }

    LaunchedEffect(rings) {
        if (animate) {
            animationProgress.snapTo(0f)
            animationProgress.animateTo(
                targetValue = 1f,
                animationSpec = ChartAnimations.tweenSpec(durationMillis = 1000)
            )
        } else {
            animationProgress.snapTo(1f)
        }
    }

    Canvas(
        modifier = modifier
            .aspectRatio(1f)
            .padding(8.dp)
    ) {
        val canvasSize = size
        val center = Offset(canvasSize.width / 2f, canvasSize.height / 2f)
        val maxRadius = min(canvasSize.width, canvasSize.height) / 2f
        val strokeWidthPx = strokeWidth.toPx()
        val spacingPx = ringSpacing.toPx()
        val ringStep = strokeWidthPx + spacingPx

        rings.forEachIndexed { index, ring ->
            val radius = maxRadius - (index * ringStep) - strokeWidthPx / 2f

            if (radius > 0) {
                // Draw track
                drawArc(
                    color = ring.trackColor,
                    startAngle = -90f,
                    sweepAngle = 360f,
                    useCenter = false,
                    topLeft = Offset(center.x - radius, center.y - radius),
                    size = Size(radius * 2, radius * 2),
                    style = Stroke(width = strokeWidthPx, cap = StrokeCap.Round)
                )

                // Draw progress
                val progress = ring.progress.coerceIn(0f, 1f) * animationProgress.value
                drawArc(
                    color = ring.progressColor,
                    startAngle = -90f,
                    sweepAngle = 360f * progress,
                    useCenter = false,
                    topLeft = Offset(center.x - radius, center.y - radius),
                    size = Size(radius * 2, radius * 2),
                    style = Stroke(width = strokeWidthPx, cap = StrokeCap.Round)
                )
            }
        }
    }
}

/**
 * Data for a single ring in multi-ring donut chart
 */
data class DonutRingData(
    val label: String,
    val progress: Float, // 0.0 to 1.0
    val progressColor: Color,
    val trackColor: Color = Color.LightGray.copy(alpha = 0.3f)
)

/**
 * Compact donut chart for dashboard widgets
 */
@Composable
fun CompactDonutChart(
    dataPoints: List<ChartDataPoint>,
    modifier: Modifier = Modifier,
    strokeWidth: Dp = 24.dp,
    colorScheme: List<Color> = ChartColorSchemes.Default,
    showTotal: Boolean = true
) {
    val total = dataPoints.sumOf { it.value.toDouble() }.toFloat()

    DonutChart(
        dataPoints = dataPoints,
        modifier = modifier,
        config = DonutChartConfig(
            strokeWidth = strokeWidth,
            gapAngle = 2f,
            enableTouch = false,
            showCenterText = showTotal,
            colorScheme = colorScheme
        ),
        centerText = if (showTotal) {
            DonutCenterText(
                title = "Total",
                value = ChartFormatters.formatCompact(total)
            )
        } else null,
        showLegend = false
    )
}
