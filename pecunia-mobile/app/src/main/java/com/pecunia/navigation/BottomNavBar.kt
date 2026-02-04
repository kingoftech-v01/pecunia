package com.pecunia.navigation

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.currentBackStackEntryAsState

/**
 * Data class representing a bottom navigation item.
 */
data class BottomNavItemData(
    val route: String,
    val label: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector,
    val badgeCount: Int = 0,
    val hasNews: Boolean = false
)

/**
 * Sealed class for bottom navigation destinations.
 */
sealed class BottomNavDestination(
    val route: String,
    val labelResId: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector
) {
    data object Dashboard : BottomNavDestination(
        route = Route.Main.Dashboard.route,
        labelResId = "Dashboard",
        selectedIcon = Icons.Filled.Home,
        unselectedIcon = Icons.Outlined.Home
    )

    data object Transactions : BottomNavDestination(
        route = Route.Main.Transactions.route,
        labelResId = "Transactions",
        selectedIcon = ReceiptIcon,
        unselectedIcon = ReceiptOutlinedIcon
    )

    data object Budgets : BottomNavDestination(
        route = Route.Main.Budgets.route,
        labelResId = "Budgets",
        selectedIcon = SavingsIcon,
        unselectedIcon = SavingsOutlinedIcon
    )

    data object Settings : BottomNavDestination(
        route = Route.Main.Settings.route,
        labelResId = "Settings",
        selectedIcon = Icons.Filled.Settings,
        unselectedIcon = Icons.Outlined.Settings
    )

    companion object {
        val items = listOf(Dashboard, Transactions, Budgets, Settings)
    }
}

// Placeholder icons - in a real app, these would be actual Material icons
private val ReceiptIcon: ImageVector = Icons.Filled.Notifications // Placeholder
private val ReceiptOutlinedIcon: ImageVector = Icons.Filled.Notifications // Placeholder
private val SavingsIcon: ImageVector = Icons.Filled.Notifications // Placeholder
private val SavingsOutlinedIcon: ImageVector = Icons.Filled.Notifications // Placeholder

/**
 * Main Bottom Navigation Bar composable.
 * Provides navigation between main app sections with badges and selection state.
 *
 * @param navController The NavController for handling navigation
 * @param modifier Optional modifier for the navigation bar
 * @param notificationCounts Map of route to notification/badge count
 * @param onItemClick Optional callback when an item is clicked
 */
@Composable
fun BottomNavBar(
    navController: NavController,
    modifier: Modifier = Modifier,
    notificationCounts: Map<String, Int> = emptyMap(),
    onItemClick: ((String) -> Unit)? = null
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    NavigationBar(
        modifier = modifier
            .fillMaxWidth()
            .shadow(
                elevation = 8.dp,
                shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp)
            ),
        containerColor = MaterialTheme.colorScheme.surface,
        contentColor = MaterialTheme.colorScheme.onSurface,
        tonalElevation = 0.dp
    ) {
        BottomNavDestination.items.forEach { destination ->
            val isSelected = currentDestination?.hierarchy?.any {
                it.route == destination.route
            } == true

            val badgeCount = notificationCounts[destination.route] ?: 0

            NavigationBarItem(
                selected = isSelected,
                onClick = {
                    onItemClick?.invoke(destination.route)

                    navController.navigate(destination.route) {
                        // Pop up to the start destination of the graph to
                        // avoid building up a large stack of destinations
                        popUpTo(navController.graph.findStartDestination().id) {
                            saveState = true
                        }
                        // Avoid multiple copies of the same destination
                        launchSingleTop = true
                        // Restore state when reselecting a previously selected item
                        restoreState = true
                    }
                },
                icon = {
                    BottomNavIcon(
                        isSelected = isSelected,
                        selectedIcon = destination.selectedIcon,
                        unselectedIcon = destination.unselectedIcon,
                        contentDescription = destination.labelResId,
                        badgeCount = badgeCount
                    )
                },
                label = {
                    BottomNavLabel(
                        label = destination.labelResId,
                        isSelected = isSelected
                    )
                },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MaterialTheme.colorScheme.primary,
                    selectedTextColor = MaterialTheme.colorScheme.primary,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer
                ),
                alwaysShowLabel = true
            )
        }
    }
}

/**
 * Custom Bottom Navigation Bar with enhanced styling and animations.
 */
@Composable
fun EnhancedBottomNavBar(
    navController: NavController,
    modifier: Modifier = Modifier,
    notificationCounts: Map<String, Int> = emptyMap(),
    backgroundColor: Color = MaterialTheme.colorScheme.surface,
    selectedColor: Color = MaterialTheme.colorScheme.primary,
    unselectedColor: Color = MaterialTheme.colorScheme.onSurfaceVariant
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .windowInsetsPadding(WindowInsets.navigationBars),
        color = backgroundColor,
        shadowElevation = 16.dp,
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(72.dp)
                .padding(horizontal = 8.dp),
            horizontalArrangement = Arrangement.SpaceAround,
            verticalAlignment = Alignment.CenterVertically
        ) {
            BottomNavDestination.items.forEach { destination ->
                val isSelected = currentRoute == destination.route
                val badgeCount = notificationCounts[destination.route] ?: 0

                EnhancedNavItem(
                    destination = destination,
                    isSelected = isSelected,
                    badgeCount = badgeCount,
                    selectedColor = selectedColor,
                    unselectedColor = unselectedColor,
                    onClick = {
                        navController.navigate(destination.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }
        }
    }
}

/**
 * Enhanced navigation item with animations.
 */
@Composable
private fun RowScope.EnhancedNavItem(
    destination: BottomNavDestination,
    isSelected: Boolean,
    badgeCount: Int,
    selectedColor: Color,
    unselectedColor: Color,
    onClick: () -> Unit
) {
    val scale by animateFloatAsState(
        targetValue = if (isSelected) 1.1f else 1f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "scale"
    )

    val iconColor by animateColorAsState(
        targetValue = if (isSelected) selectedColor else unselectedColor,
        animationSpec = tween(
            durationMillis = 200,
            easing = FastOutSlowInEasing
        ),
        label = "iconColor"
    )

    val interactionSource = remember { MutableInteractionSource() }

    Column(
        modifier = Modifier
            .weight(1f)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            )
            .padding(vertical = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .scale(scale)
                .then(
                    if (isSelected) {
                        Modifier
                            .background(
                                color = selectedColor.copy(alpha = 0.1f),
                                shape = CircleShape
                            )
                            .padding(8.dp)
                    } else {
                        Modifier.padding(8.dp)
                    }
                ),
            contentAlignment = Alignment.Center
        ) {
            BadgedBox(
                badge = {
                    if (badgeCount > 0) {
                        Badge(
                            containerColor = MaterialTheme.colorScheme.error,
                            contentColor = MaterialTheme.colorScheme.onError
                        ) {
                            Text(
                                text = if (badgeCount > 99) "99+" else badgeCount.toString(),
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            ) {
                Icon(
                    imageVector = if (isSelected) destination.selectedIcon else destination.unselectedIcon,
                    contentDescription = destination.labelResId,
                    tint = iconColor,
                    modifier = Modifier.size(24.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = destination.labelResId,
            color = iconColor,
            fontSize = 12.sp,
            fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

/**
 * Bottom navigation icon with badge support.
 */
@Composable
private fun BottomNavIcon(
    isSelected: Boolean,
    selectedIcon: ImageVector,
    unselectedIcon: ImageVector,
    contentDescription: String,
    badgeCount: Int = 0
) {
    val scale by animateFloatAsState(
        targetValue = if (isSelected) 1.15f else 1f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium
        ),
        label = "iconScale"
    )

    BadgedBox(
        badge = {
            when {
                badgeCount > 0 -> {
                    Badge(
                        containerColor = MaterialTheme.colorScheme.error,
                        contentColor = MaterialTheme.colorScheme.onError
                    ) {
                        Text(
                            text = if (badgeCount > 99) "99+" else badgeCount.toString(),
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    ) {
        Icon(
            imageVector = if (isSelected) selectedIcon else unselectedIcon,
            contentDescription = contentDescription,
            modifier = Modifier
                .size(24.dp)
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                }
        )
    }
}

/**
 * Bottom navigation label with animation.
 */
@Composable
private fun BottomNavLabel(
    label: String,
    isSelected: Boolean
) {
    Text(
        text = label,
        fontSize = 12.sp,
        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis
    )
}

/**
 * Floating Action Button style Bottom Navigation for adding new items.
 * Can be used in conjunction with the main bottom nav for quick actions.
 */
@Composable
fun BottomNavWithFab(
    navController: NavController,
    onFabClick: () -> Unit,
    modifier: Modifier = Modifier,
    notificationCounts: Map<String, Int> = emptyMap(),
    fabIcon: ImageVector = Icons.Filled.Home // Placeholder for Add icon
) {
    Box(
        modifier = modifier.fillMaxWidth()
    ) {
        // Main bottom navigation
        BottomNavBar(
            navController = navController,
            notificationCounts = notificationCounts,
            modifier = Modifier.align(Alignment.BottomCenter)
        )

        // Floating action button overlaid on top
        Surface(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = (-28).dp)
                .size(56.dp)
                .clip(CircleShape)
                .clickable(onClick = onFabClick),
            color = MaterialTheme.colorScheme.primary,
            shadowElevation = 8.dp,
            shape = CircleShape
        ) {
            Box(
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = fabIcon,
                    contentDescription = "Add",
                    tint = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(28.dp)
                )
            }
        }
    }
}

/**
 * State holder for bottom navigation badge counts.
 * Useful for observing notification/badge updates.
 */
data class BottomNavBadgeState(
    val dashboardBadge: Int = 0,
    val transactionsBadge: Int = 0,
    val budgetsBadge: Int = 0,
    val settingsBadge: Int = 0
) {
    fun toMap(): Map<String, Int> = mapOf(
        Route.Main.Dashboard.route to dashboardBadge,
        Route.Main.Transactions.route to transactionsBadge,
        Route.Main.Budgets.route to budgetsBadge,
        Route.Main.Settings.route to settingsBadge
    )
}

/**
 * Helper function to check if current destination is a main bottom nav destination.
 */
fun isMainDestination(route: String?): Boolean {
    return BottomNavDestination.items.any { it.route == route }
}

/**
 * Helper function to get the current selected bottom nav item.
 */
@Composable
fun currentBottomNavDestination(navController: NavController): BottomNavDestination? {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    return BottomNavDestination.items.find { it.route == currentRoute }
}
