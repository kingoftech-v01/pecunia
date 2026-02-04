package com.pecunia.ui.screens.banking.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.pecunia.ui.screens.banking.SyncStatus

@Composable
fun SyncStatusIndicator(
    status: SyncStatus,
    lastSyncTime: String?,
    modifier: Modifier = Modifier,
    showLabel: Boolean = true,
    compact: Boolean = false
) {
    val infiniteTransition = rememberInfiniteTransition(label = "syncTransition")

    // Rotation animation for syncing state
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "syncRotation"
    )

    // Pulse animation for syncing state
    val scale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.1f,
        animationSpec = infiniteRepeatable(
            animation = tween(500),
            repeatMode = RepeatMode.Reverse
        ),
        label = "syncPulse"
    )

    val (icon, iconColor, backgroundColor, label) = when (status) {
        SyncStatus.SYNCED -> SyncStatusStyle(
            icon = Icons.Default.CheckCircle,
            iconColor = Color(0xFF4CAF50),
            backgroundColor = Color(0xFF4CAF50).copy(alpha = 0.15f),
            label = lastSyncTime ?: "Synced"
        )
        SyncStatus.SYNCING -> SyncStatusStyle(
            icon = Icons.Default.Sync,
            iconColor = MaterialTheme.colorScheme.primary,
            backgroundColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f),
            label = "Syncing..."
        )
        SyncStatus.PARTIAL -> SyncStatusStyle(
            icon = Icons.Default.Warning,
            iconColor = Color(0xFFFF9800),
            backgroundColor = Color(0xFFFF9800).copy(alpha = 0.15f),
            label = "Partial sync"
        )
        SyncStatus.ERROR -> SyncStatusStyle(
            icon = Icons.Default.Error,
            iconColor = MaterialTheme.colorScheme.error,
            backgroundColor = MaterialTheme.colorScheme.error.copy(alpha = 0.15f),
            label = "Sync failed"
        )
        SyncStatus.PENDING -> SyncStatusStyle(
            icon = Icons.Default.Sync,
            iconColor = MaterialTheme.colorScheme.onSurfaceVariant,
            backgroundColor = MaterialTheme.colorScheme.surfaceVariant,
            label = "Pending"
        )
    }

    if (compact) {
        CompactSyncIndicator(
            icon = icon,
            iconColor = iconColor,
            backgroundColor = backgroundColor,
            isSyncing = status == SyncStatus.SYNCING,
            rotation = rotation,
            scale = scale,
            modifier = modifier
        )
    } else {
        FullSyncIndicator(
            icon = icon,
            iconColor = iconColor,
            backgroundColor = backgroundColor,
            label = if (showLabel) label else null,
            isSyncing = status == SyncStatus.SYNCING,
            rotation = rotation,
            scale = scale,
            modifier = modifier
        )
    }
}

@Composable
private fun CompactSyncIndicator(
    icon: ImageVector,
    iconColor: Color,
    backgroundColor: Color,
    isSyncing: Boolean,
    rotation: Float,
    scale: Float,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .size(24.dp)
            .background(backgroundColor, CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = iconColor,
            modifier = Modifier
                .size(14.dp)
                .then(
                    if (isSyncing) {
                        Modifier
                            .rotate(rotation)
                            .scale(scale)
                    } else {
                        Modifier
                    }
                )
        )
    }
}

@Composable
private fun FullSyncIndicator(
    icon: ImageVector,
    iconColor: Color,
    backgroundColor: Color,
    label: String?,
    isSyncing: Boolean,
    rotation: Float,
    scale: Float,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        color = backgroundColor,
        shape = RoundedCornerShape(16.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = iconColor,
                modifier = Modifier
                    .size(14.dp)
                    .then(
                        if (isSyncing) {
                            Modifier
                                .rotate(rotation)
                                .scale(scale)
                        } else {
                            Modifier
                        }
                    )
            )

            label?.let {
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = it,
                    style = MaterialTheme.typography.labelSmall,
                    color = iconColor,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}

@Composable
fun SyncStatusDot(
    status: SyncStatus,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "dotTransition")

    val alpha by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(700),
            repeatMode = RepeatMode.Reverse
        ),
        label = "dotPulse"
    )

    val color = when (status) {
        SyncStatus.SYNCED -> Color(0xFF4CAF50)
        SyncStatus.SYNCING -> MaterialTheme.colorScheme.primary
        SyncStatus.PARTIAL -> Color(0xFFFF9800)
        SyncStatus.ERROR -> MaterialTheme.colorScheme.error
        SyncStatus.PENDING -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    Box(
        modifier = modifier
            .size(8.dp)
            .background(
                color = if (status == SyncStatus.SYNCING) {
                    color.copy(alpha = alpha)
                } else {
                    color
                },
                shape = CircleShape
            )
    )
}

@Composable
fun SyncStatusBanner(
    status: SyncStatus,
    message: String?,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    AnimatedVisibility(
        visible = status == SyncStatus.ERROR || status == SyncStatus.PARTIAL,
        enter = fadeIn(),
        exit = fadeOut(),
        modifier = modifier
    ) {
        val (backgroundColor, contentColor) = when (status) {
            SyncStatus.ERROR -> Pair(
                MaterialTheme.colorScheme.errorContainer,
                MaterialTheme.colorScheme.onErrorContainer
            )
            SyncStatus.PARTIAL -> Pair(
                Color(0xFFFFF3E0),
                Color(0xFFE65100)
            )
            else -> Pair(
                MaterialTheme.colorScheme.surfaceVariant,
                MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Surface(
            color = backgroundColor,
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = if (status == SyncStatus.ERROR) Icons.Default.Error else Icons.Default.Warning,
                    contentDescription = null,
                    tint = contentColor,
                    modifier = Modifier.size(24.dp)
                )

                Spacer(modifier = Modifier.width(12.dp))

                Text(
                    text = message ?: when (status) {
                        SyncStatus.ERROR -> "Failed to sync accounts"
                        SyncStatus.PARTIAL -> "Some accounts could not be synced"
                        else -> ""
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = contentColor,
                    modifier = Modifier.weight(1f)
                )

                onRetry?.let {
                    Spacer(modifier = Modifier.width(8.dp))
                    Surface(
                        onClick = it,
                        color = contentColor.copy(alpha = 0.1f),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text(
                            text = "Retry",
                            style = MaterialTheme.typography.labelMedium,
                            color = contentColor,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
                        )
                    }
                }
            }
        }
    }
}

private data class SyncStatusStyle(
    val icon: ImageVector,
    val iconColor: Color,
    val backgroundColor: Color,
    val label: String
)
