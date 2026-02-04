package com.pecunia.ui.components.inputs

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

/**
 * Category UI model
 */
data class CategoryUiModel(
    val id: String,
    val name: String,
    val icon: ImageVector,
    val color: Color,
    val isExpense: Boolean = true,
    val parentId: String? = null,
    val transactionCount: Int = 0
)

/**
 * Category picker display mode
 */
enum class CategoryPickerMode {
    LIST,
    GRID
}

/**
 * Category selector button that opens the picker
 */
@Composable
fun CategorySelector(
    selectedCategory: CategoryUiModel?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    label: String = "Catégorie",
    isError: Boolean = false,
    errorMessage: String? = null
) {
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
                if (selectedCategory != null) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(selectedCategory.color.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = selectedCategory.icon,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp),
                                tint = selectedCategory.color
                            )
                        }

                        Spacer(modifier = Modifier.width(12.dp))

                        Text(
                            text = selectedCategory.name,
                            style = MaterialTheme.typography.bodyLarge
                        )
                    }
                } else {
                    Text(
                        text = "Sélectionner une catégorie",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
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
 * Category picker bottom sheet content
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CategoryPickerSheet(
    categories: List<CategoryUiModel>,
    selectedCategory: CategoryUiModel?,
    onCategorySelected: (CategoryUiModel) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    title: String = "Choisir une catégorie",
    showSearch: Boolean = true,
    mode: CategoryPickerMode = CategoryPickerMode.GRID
) {
    var searchQuery by remember { mutableStateOf("") }

    val filteredCategories = remember(searchQuery, categories) {
        if (searchQuery.isBlank()) {
            categories
        } else {
            categories.filter {
                it.name.contains(searchQuery, ignoreCase = true)
            }
        }
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(bottom = 16.dp)
    ) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold
            )

            IconButton(onClick = onDismiss) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "Fermer"
                )
            }
        }

        // Search bar
        if (showSearch) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                placeholder = { Text("Rechercher une catégorie...") },
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Search,
                        contentDescription = null
                    )
                },
                trailingIcon = {
                    AnimatedVisibility(
                        visible = searchQuery.isNotEmpty(),
                        enter = fadeIn(),
                        exit = fadeOut()
                    ) {
                        IconButton(onClick = { searchQuery = "" }) {
                            Icon(
                                imageVector = Icons.Default.Clear,
                                contentDescription = "Effacer"
                            )
                        }
                    }
                },
                singleLine = true,
                shape = RoundedCornerShape(12.dp)
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Categories
        when (mode) {
            CategoryPickerMode.GRID -> {
                CategoryGrid(
                    categories = filteredCategories,
                    selectedCategory = selectedCategory,
                    onCategorySelected = onCategorySelected,
                    modifier = Modifier.weight(1f, fill = false)
                )
            }
            CategoryPickerMode.LIST -> {
                CategoryList(
                    categories = filteredCategories,
                    selectedCategory = selectedCategory,
                    onCategorySelected = onCategorySelected,
                    modifier = Modifier.weight(1f, fill = false)
                )
            }
        }

        // Empty state
        if (filteredCategories.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(32.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = Icons.Outlined.SearchOff,
                        contentDescription = null,
                        modifier = Modifier.size(48.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Aucune catégorie trouvée",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

/**
 * Category grid display
 */
@Composable
fun CategoryGrid(
    categories: List<CategoryUiModel>,
    selectedCategory: CategoryUiModel?,
    onCategorySelected: (CategoryUiModel) -> Unit,
    modifier: Modifier = Modifier,
    columns: Int = 4
) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(columns),
        modifier = modifier.padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(vertical = 8.dp)
    ) {
        items(categories, key = { it.id }) { category ->
            CategoryGridItem(
                category = category,
                isSelected = category.id == selectedCategory?.id,
                onClick = { onCategorySelected(category) }
            )
        }
    }
}

/**
 * Single category item in grid
 */
@Composable
fun CategoryGridItem(
    category: CategoryUiModel,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .then(
                if (isSelected) {
                    Modifier.border(
                        width = 2.dp,
                        color = category.color,
                        shape = RoundedCornerShape(12.dp)
                    )
                } else Modifier
            )
            .padding(8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .clip(CircleShape)
                .background(
                    if (isSelected) category.color
                    else category.color.copy(alpha = 0.15f)
                ),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = category.icon,
                contentDescription = null,
                modifier = Modifier.size(24.dp),
                tint = if (isSelected) Color.White else category.color
            )
        }

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = category.name,
            style = MaterialTheme.typography.labelSmall,
            textAlign = TextAlign.Center,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

/**
 * Category list display
 */
@Composable
fun CategoryList(
    categories: List<CategoryUiModel>,
    selectedCategory: CategoryUiModel?,
    onCategorySelected: (CategoryUiModel) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(vertical = 8.dp)
    ) {
        items(categories, key = { it.id }) { category ->
            CategoryListItem(
                category = category,
                isSelected = category.id == selectedCategory?.id,
                onClick = { onCategorySelected(category) }
            )
        }
    }
}

/**
 * Single category item in list
 */
@Composable
fun CategoryListItem(
    category: CategoryUiModel,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    showTransactionCount: Boolean = false
) {
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        color = if (isSelected) category.color.copy(alpha = 0.1f) else Color.Transparent
    ) {
        Row(
            modifier = Modifier
                .padding(horizontal = 16.dp, vertical = 12.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(category.color.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = category.icon,
                    contentDescription = null,
                    modifier = Modifier.size(22.dp),
                    tint = category.color
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = category.name,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal
                )

                if (showTransactionCount && category.transactionCount > 0) {
                    Text(
                        text = "${category.transactionCount} transactions",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (isSelected) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription = "Sélectionné",
                    tint = category.color
                )
            }
        }
    }
}

/**
 * Inline category chips for filtering
 */
@Composable
fun CategoryChips(
    categories: List<CategoryUiModel>,
    selectedCategories: Set<String>,
    onCategoryToggle: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyVerticalGrid(
        columns = GridCells.Adaptive(100.dp),
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(categories, key = { it.id }) { category ->
            val isSelected = category.id in selectedCategories

            FilterChip(
                selected = isSelected,
                onClick = { onCategoryToggle(category.id) },
                label = { Text(category.name) },
                leadingIcon = {
                    Icon(
                        imageVector = category.icon,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                        tint = if (isSelected) MaterialTheme.colorScheme.onSecondaryContainer
                               else category.color
                    )
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = category.color.copy(alpha = 0.2f)
                )
            )
        }
    }
}

/**
 * Quick category selector (horizontal row)
 */
@Composable
fun QuickCategorySelector(
    categories: List<CategoryUiModel>,
    selectedCategory: CategoryUiModel?,
    onCategorySelected: (CategoryUiModel) -> Unit,
    modifier: Modifier = Modifier,
    showMoreButton: Boolean = true,
    onMoreClick: (() -> Unit)? = null
) {
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        categories.take(5).forEach { category ->
            val isSelected = category.id == selectedCategory?.id

            Column(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { onCategorySelected(category) }
                    .padding(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(
                            if (isSelected) category.color
                            else category.color.copy(alpha = 0.15f)
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = category.icon,
                        contentDescription = null,
                        modifier = Modifier.size(22.dp),
                        tint = if (isSelected) Color.White else category.color
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = category.name,
                    style = MaterialTheme.typography.labelSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }

        if (showMoreButton && onMoreClick != null && categories.size > 5) {
            Column(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .clickable(onClick = onMoreClick)
                    .padding(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.MoreHoriz,
                        contentDescription = "Plus",
                        modifier = Modifier.size(22.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "Plus",
                    style = MaterialTheme.typography.labelSmall
                )
            }
        }
    }
}

// Sample data for previews

private val sampleCategories = listOf(
    CategoryUiModel("1", "Alimentation", Icons.Outlined.ShoppingCart, Color(0xFF4CAF50)),
    CategoryUiModel("2", "Transport", Icons.Outlined.DirectionsCar, Color(0xFF2196F3)),
    CategoryUiModel("3", "Restaurants", Icons.Outlined.Restaurant, Color(0xFFFF9800)),
    CategoryUiModel("4", "Shopping", Icons.Outlined.ShoppingBag, Color(0xFFE91E63)),
    CategoryUiModel("5", "Loisirs", Icons.Outlined.SportsEsports, Color(0xFF9C27B0)),
    CategoryUiModel("6", "Santé", Icons.Outlined.LocalHospital, Color(0xFFF44336)),
    CategoryUiModel("7", "Logement", Icons.Outlined.Home, Color(0xFF795548)),
    CategoryUiModel("8", "Services", Icons.Outlined.Build, Color(0xFF607D8B))
)

// Previews

@Preview(showBackground = true)
@Composable
private fun CategorySelectorPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            CategorySelector(
                selectedCategory = sampleCategories[0],
                onClick = {}
            )

            CategorySelector(
                selectedCategory = null,
                onClick = {},
                isError = true,
                errorMessage = "Veuillez sélectionner une catégorie"
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun CategoryGridPreview() {
    MaterialTheme {
        CategoryGrid(
            categories = sampleCategories,
            selectedCategory = sampleCategories[2],
            onCategorySelected = {},
            modifier = Modifier.height(300.dp)
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun CategoryListItemPreview() {
    MaterialTheme {
        Column {
            CategoryListItem(
                category = sampleCategories[0],
                isSelected = false,
                onClick = {}
            )
            CategoryListItem(
                category = sampleCategories[1],
                isSelected = true,
                onClick = {}
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun QuickCategorySelectorPreview() {
    MaterialTheme {
        QuickCategorySelector(
            categories = sampleCategories,
            selectedCategory = sampleCategories[1],
            onCategorySelected = {},
            onMoreClick = {},
            modifier = Modifier.padding(16.dp)
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun CategoryPickerSheetPreview() {
    MaterialTheme {
        CategoryPickerSheet(
            categories = sampleCategories,
            selectedCategory = sampleCategories[2],
            onCategorySelected = {},
            onDismiss = {},
            modifier = Modifier.height(500.dp)
        )
    }
}
