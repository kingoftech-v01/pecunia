package com.pecunia.ui.components.common

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

/**
 * Predefined empty states for common scenarios
 */
enum class EmptyStateType(
    val icon: ImageVector,
    val title: String,
    val message: String,
    val actionLabel: String?
) {
    NO_TRANSACTIONS(
        icon = Icons.Outlined.Receipt,
        title = "Aucune transaction",
        message = "Vous n'avez pas encore de transactions. Commencez par en ajouter une!",
        actionLabel = "Ajouter une transaction"
    ),
    NO_BUDGETS(
        icon = Icons.Outlined.AccountBalance,
        title = "Aucun budget",
        message = "Créez votre premier budget pour mieux gérer vos dépenses.",
        actionLabel = "Créer un budget"
    ),
    NO_CATEGORIES(
        icon = Icons.Outlined.Category,
        title = "Aucune catégorie",
        message = "Ajoutez des catégories pour organiser vos transactions.",
        actionLabel = "Ajouter une catégorie"
    ),
    NO_ACCOUNTS(
        icon = Icons.Outlined.CreditCard,
        title = "Aucun compte",
        message = "Ajoutez vos comptes bancaires pour suivre vos finances.",
        actionLabel = "Ajouter un compte"
    ),
    NO_GOALS(
        icon = Icons.Outlined.Flag,
        title = "Aucun objectif",
        message = "Définissez des objectifs d'épargne pour atteindre vos rêves.",
        actionLabel = "Créer un objectif"
    ),
    NO_SEARCH_RESULTS(
        icon = Icons.Outlined.SearchOff,
        title = "Aucun résultat",
        message = "Aucun élément ne correspond à votre recherche.",
        actionLabel = null
    ),
    NO_NOTIFICATIONS(
        icon = Icons.Outlined.Notifications,
        title = "Aucune notification",
        message = "Vous êtes à jour! Aucune notification pour le moment.",
        actionLabel = null
    ),
    NO_FAVORITES(
        icon = Icons.Outlined.FavoriteBorder,
        title = "Aucun favori",
        message = "Marquez des éléments comme favoris pour les retrouver facilement.",
        actionLabel = null
    ),
    NO_DATA(
        icon = Icons.Outlined.Inbox,
        title = "Aucune donnée",
        message = "Il n'y a rien à afficher pour le moment.",
        actionLabel = null
    )
}

/**
 * Generic empty state component with icon, title, message and optional action
 */
@Composable
fun EmptyState(
    icon: ImageVector,
    title: String,
    message: String,
    modifier: Modifier = Modifier,
    iconTint: Color = MaterialTheme.colorScheme.primary,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
    secondaryActionLabel: String? = null,
    onSecondaryAction: (() -> Unit)? = null
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = iconTint.copy(alpha = 0.6f)
        )

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.onSurface,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.widthIn(max = 280.dp)
        )

        if (actionLabel != null && onAction != null) {
            Spacer(modifier = Modifier.height(24.dp))

            Button(onClick = onAction) {
                Text(actionLabel)
            }
        }

        if (secondaryActionLabel != null && onSecondaryAction != null) {
            Spacer(modifier = Modifier.height(8.dp))

            TextButton(onClick = onSecondaryAction) {
                Text(secondaryActionLabel)
            }
        }
    }
}

/**
 * Predefined empty state using EmptyStateType enum
 */
@Composable
fun EmptyState(
    type: EmptyStateType,
    modifier: Modifier = Modifier,
    onAction: (() -> Unit)? = null,
    customTitle: String? = null,
    customMessage: String? = null,
    customActionLabel: String? = null
) {
    EmptyState(
        icon = type.icon,
        title = customTitle ?: type.title,
        message = customMessage ?: type.message,
        modifier = modifier,
        actionLabel = customActionLabel ?: type.actionLabel,
        onAction = if ((customActionLabel ?: type.actionLabel) != null) onAction else null
    )
}

/**
 * Compact empty state for smaller areas
 */
@Composable
fun CompactEmptyState(
    icon: ImageVector,
    message: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(48.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )

        if (actionLabel != null && onAction != null) {
            Spacer(modifier = Modifier.height(12.dp))

            TextButton(onClick = onAction) {
                Text(actionLabel)
            }
        }
    }
}

/**
 * Empty state card with border
 */
@Composable
fun EmptyStateCard(
    icon: ImageVector,
    title: String,
    message: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
) {
    OutlinedCard(
        modifier = modifier.fillMaxWidth()
    ) {
        EmptyState(
            icon = icon,
            title = title,
            message = message,
            actionLabel = actionLabel,
            onAction = onAction
        )
    }
}

/**
 * Inline empty state for lists
 */
@Composable
fun InlineEmptyState(
    message: String,
    modifier: Modifier = Modifier,
    icon: ImageVector = Icons.Outlined.Inbox
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(20.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )

        Spacer(modifier = Modifier.width(8.dp))

        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

/**
 * Empty search results with suggestions
 */
@Composable
fun EmptySearchResults(
    query: String,
    modifier: Modifier = Modifier,
    suggestions: List<String> = emptyList(),
    onSuggestionClick: ((String) -> Unit)? = null,
    onClearSearch: (() -> Unit)? = null
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = Icons.Outlined.SearchOff,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Aucun résultat pour \"$query\"",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurface,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Essayez une recherche différente ou vérifiez l'orthographe",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )

        if (suggestions.isNotEmpty()) {
            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Suggestions:",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(8.dp))

            suggestions.forEach { suggestion ->
                TextButton(
                    onClick = { onSuggestionClick?.invoke(suggestion) }
                ) {
                    Text(suggestion)
                }
            }
        }

        if (onClearSearch != null) {
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedButton(onClick = onClearSearch) {
                Icon(
                    imageVector = Icons.Default.Clear,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Effacer la recherche")
            }
        }
    }
}

// Previews

@Preview(showBackground = true)
@Composable
private fun EmptyStatePreview() {
    MaterialTheme {
        EmptyState(
            type = EmptyStateType.NO_TRANSACTIONS,
            onAction = {}
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun EmptyStateNoActionPreview() {
    MaterialTheme {
        EmptyState(
            type = EmptyStateType.NO_SEARCH_RESULTS
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun CompactEmptyStatePreview() {
    MaterialTheme {
        CompactEmptyState(
            icon = Icons.Outlined.Receipt,
            message = "Aucune transaction ce mois-ci",
            actionLabel = "Voir tout",
            onAction = {}
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun EmptyStateCardPreview() {
    MaterialTheme {
        EmptyStateCard(
            icon = Icons.Outlined.AccountBalance,
            title = "Aucun budget",
            message = "Créez votre premier budget",
            actionLabel = "Créer",
            onAction = {},
            modifier = Modifier.padding(16.dp)
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun InlineEmptyStatePreview() {
    MaterialTheme {
        InlineEmptyState(
            message = "Aucun élément à afficher"
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun EmptySearchResultsPreview() {
    MaterialTheme {
        EmptySearchResults(
            query = "restaurant",
            suggestions = listOf("Alimentation", "Restaurants", "Fast-food"),
            onSuggestionClick = {},
            onClearSearch = {}
        )
    }
}
