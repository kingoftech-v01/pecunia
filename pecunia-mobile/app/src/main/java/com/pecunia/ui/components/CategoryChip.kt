package com.pecunia.ui.components

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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.outlined.AttachMoney
import androidx.compose.material.icons.outlined.CardGiftcard
import androidx.compose.material.icons.outlined.DirectionsCar
import androidx.compose.material.icons.outlined.Fastfood
import androidx.compose.material.icons.outlined.Flight
import androidx.compose.material.icons.outlined.LocalHospital
import androidx.compose.material.icons.outlined.MoreHoriz
import androidx.compose.material.icons.outlined.Movie
import androidx.compose.material.icons.outlined.Receipt
import androidx.compose.material.icons.outlined.School
import androidx.compose.material.icons.outlined.ShoppingBag
import androidx.compose.material.icons.outlined.TrendingUp
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.pecunia.ui.theme.PecuniaTheme
import com.pecunia.ui.theme.getCategoryColor

/**
 * Category data class
 */
data class Category(
    val name: String,
    val icon: ImageVector? = null,
    val color: Color? = null
)

/**
 * Category chip component for displaying and selecting categories
 *
 * @param category The category to display
 * @param modifier Modifier for the chip
 * @param selected Whether the chip is selected
 * @param onClick Callback when the chip is clicked
 * @param showIcon Whether to show the category icon
 */
@Composable
fun CategoryChip(
    category: String,
    modifier: Modifier = Modifier,
    selected: Boolean = false,
    onClick: (() -> Unit)? = null,
    showIcon: Boolean = true
) {
    val categoryColor = getCategoryColor(category)
    val icon = getCategoryIcon(category)

    FilterChip(
        selected = selected,
        onClick = { onClick?.invoke() },
        label = {
            Text(
                text = category,
                style = MaterialTheme.typography.labelMedium
            )
        },
        modifier = modifier,
        enabled = onClick != null,
        leadingIcon = if (showIcon) {
            {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
            }
        } else null,
        colors = FilterChipDefaults.filterChipColors(
            containerColor = categoryColor.copy(alpha = 0.1f),
            labelColor = categoryColor,
            iconColor = categoryColor,
            selectedContainerColor = categoryColor,
            selectedLabelColor = Color.White,
            selectedLeadingIconColor = Color.White
        ),
        border = FilterChipDefaults.filterChipBorder(
            borderColor = categoryColor.copy(alpha = 0.3f),
            selectedBorderColor = categoryColor,
            enabled = true,
            selected = selected
        )
    )
}

/**
 * Compact category badge (smaller, for tight spaces)
 */
@Composable
fun CategoryBadge(
    category: String,
    modifier: Modifier = Modifier,
    showIcon: Boolean = false
) {
    val categoryColor = getCategoryColor(category)

    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(4.dp),
        color = categoryColor.copy(alpha = 0.15f)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            if (showIcon) {
                Icon(
                    imageVector = getCategoryIcon(category),
                    contentDescription = null,
                    modifier = Modifier.size(12.dp),
                    tint = categoryColor
                )
            }
            Text(
                text = category,
                style = MaterialTheme.typography.labelSmall,
                color = categoryColor
            )
        }
    }
}

/**
 * Category pill with colored dot indicator
 */
@Composable
fun CategoryPill(
    category: String,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null
) {
    val categoryColor = getCategoryColor(category)

    Surface(
        modifier = modifier
            .then(
                if (onClick != null) Modifier.clickable(onClick = onClick)
                else Modifier
            ),
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceVariant
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Color dot
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(categoryColor)
            )

            Text(
                text = category,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * Selectable category icon button
 */
@Composable
fun CategoryIconButton(
    category: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val categoryColor = getCategoryColor(category)
    val backgroundColor = if (selected) {
        categoryColor
    } else {
        categoryColor.copy(alpha = 0.1f)
    }
    val contentColor = if (selected) Color.White else categoryColor

    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .clip(CircleShape)
                .background(backgroundColor)
                .then(
                    if (selected) Modifier
                    else Modifier.border(1.dp, categoryColor.copy(alpha = 0.3f), CircleShape)
                )
                .clickable(onClick = onClick),
            contentAlignment = Alignment.Center
        ) {
            if (selected) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription = "Selected",
                    tint = contentColor,
                    modifier = Modifier.size(24.dp)
                )
            } else {
                Icon(
                    imageVector = getCategoryIcon(category),
                    contentDescription = category,
                    tint = contentColor,
                    modifier = Modifier.size(24.dp)
                )
            }
        }

        Text(
            text = category,
            style = MaterialTheme.typography.labelSmall,
            color = if (selected) categoryColor else MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 4.dp)
        )
    }
}

/**
 * Horizontal scrollable category selector
 */
@Composable
fun CategorySelector(
    categories: List<String>,
    selectedCategory: String?,
    onCategorySelected: (String) -> Unit,
    modifier: Modifier = Modifier,
    showAllOption: Boolean = true
) {
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        if (showAllOption) {
            FilterChip(
                selected = selectedCategory == null,
                onClick = { onCategorySelected("") },
                label = { Text("All") },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = MaterialTheme.colorScheme.primary,
                    selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }

        categories.forEach { category ->
            CategoryChip(
                category = category,
                selected = selectedCategory == category,
                onClick = { onCategorySelected(category) }
            )
        }
    }
}

/**
 * Grid-style category selector
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun CategoryGrid(
    categories: List<String>,
    selectedCategories: Set<String>,
    onCategoryToggle: (String) -> Unit,
    modifier: Modifier = Modifier,
    multiSelect: Boolean = false
) {
    FlowRow(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        categories.forEach { category ->
            CategoryChip(
                category = category,
                selected = category in selectedCategories,
                onClick = { onCategoryToggle(category) }
            )
        }
    }
}

/**
 * Get icon for category
 */
private fun getCategoryIcon(category: String): ImageVector {
    return when (category.lowercase()) {
        "food", "dining", "restaurants", "groceries" -> Icons.Outlined.Fastfood
        "transport", "transportation", "gas", "fuel" -> Icons.Outlined.DirectionsCar
        "shopping", "retail" -> Icons.Outlined.ShoppingBag
        "entertainment", "movies", "games" -> Icons.Outlined.Movie
        "bills", "utilities", "rent" -> Icons.Outlined.Receipt
        "health", "medical", "pharmacy" -> Icons.Outlined.LocalHospital
        "education", "books", "courses" -> Icons.Outlined.School
        "travel", "vacation", "hotel" -> Icons.Outlined.Flight
        "salary", "income", "wages" -> Icons.Outlined.AttachMoney
        "investment", "stocks", "crypto" -> Icons.Outlined.TrendingUp
        "gift", "donation" -> Icons.Outlined.CardGiftcard
        else -> Icons.Outlined.MoreHoriz
    }
}

/**
 * Predefined category list
 */
val defaultCategories = listOf(
    "Food",
    "Transport",
    "Shopping",
    "Entertainment",
    "Bills",
    "Health",
    "Education",
    "Travel",
    "Salary",
    "Investment",
    "Gift",
    "Other"
)

@Preview(showBackground = true)
@Composable
private fun CategoryChipPreview() {
    PecuniaTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CategoryChip(category = "Food")
                CategoryChip(category = "Food", selected = true, onClick = {})
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CategoryChip(category = "Transport")
                CategoryChip(category = "Shopping")
                CategoryChip(category = "Entertainment")
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun CategoryBadgePreview() {
    PecuniaTheme {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            CategoryBadge(category = "Food")
            CategoryBadge(category = "Transport", showIcon = true)
            CategoryBadge(category = "Bills")
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun CategoryPillPreview() {
    PecuniaTheme {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            CategoryPill(category = "Food")
            CategoryPill(category = "Shopping")
            CategoryPill(category = "Salary")
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun CategoryIconButtonPreview() {
    PecuniaTheme {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            CategoryIconButton(
                category = "Food",
                selected = false,
                onClick = {}
            )
            CategoryIconButton(
                category = "Transport",
                selected = true,
                onClick = {}
            )
            CategoryIconButton(
                category = "Bills",
                selected = false,
                onClick = {}
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun CategorySelectorPreview() {
    PecuniaTheme {
        CategorySelector(
            categories = listOf("Food", "Transport", "Shopping", "Bills", "Entertainment"),
            selectedCategory = "Food",
            onCategorySelected = {},
            modifier = Modifier.padding(16.dp)
        )
    }
}
