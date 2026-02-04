package com.pecunia.ui.components.common

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
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
 * Types of errors with specific icons and colors
 */
enum class ErrorType(
    val icon: ImageVector,
    val defaultTitle: String,
    val defaultMessage: String
) {
    NETWORK(
        icon = Icons.Default.WifiOff,
        defaultTitle = "Erreur de connexion",
        defaultMessage = "Impossible de se connecter au serveur. Vérifiez votre connexion internet."
    ),
    SERVER(
        icon = Icons.Default.Cloud,
        defaultTitle = "Erreur serveur",
        defaultMessage = "Une erreur s'est produite sur le serveur. Veuillez réessayer plus tard."
    ),
    NOT_FOUND(
        icon = Icons.Default.SearchOff,
        defaultTitle = "Non trouvé",
        defaultMessage = "L'élément demandé n'existe pas ou a été supprimé."
    ),
    AUTHENTICATION(
        icon = Icons.Default.Lock,
        defaultTitle = "Non autorisé",
        defaultMessage = "Votre session a expiré. Veuillez vous reconnecter."
    ),
    PERMISSION(
        icon = Icons.Default.Block,
        defaultTitle = "Accès refusé",
        defaultMessage = "Vous n'avez pas les permissions nécessaires pour cette action."
    ),
    VALIDATION(
        icon = Icons.Default.ErrorOutline,
        defaultTitle = "Erreur de validation",
        defaultMessage = "Les données saisies sont invalides."
    ),
    GENERIC(
        icon = Icons.Default.Warning,
        defaultTitle = "Erreur",
        defaultMessage = "Une erreur inattendue s'est produite."
    )
}

/**
 * Full screen error message with icon, title, message and retry button
 */
@Composable
fun FullScreenError(
    errorType: ErrorType = ErrorType.GENERIC,
    title: String? = null,
    message: String? = null,
    onRetry: (() -> Unit)? = null,
    onSecondaryAction: (() -> Unit)? = null,
    secondaryActionLabel: String? = null,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .padding(32.dp)
                .widthIn(max = 300.dp)
        ) {
            Icon(
                imageVector = errorType.icon,
                contentDescription = null,
                modifier = Modifier.size(64.dp),
                tint = MaterialTheme.colorScheme.error
            )

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = title ?: errorType.defaultTitle,
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = message ?: errorType.defaultMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(24.dp))

            if (onRetry != null) {
                Button(
                    onClick = onRetry,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Réessayer")
                }
            }

            if (onSecondaryAction != null && secondaryActionLabel != null) {
                Spacer(modifier = Modifier.height(8.dp))
                TextButton(
                    onClick = onSecondaryAction,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(secondaryActionLabel)
                }
            }
        }
    }
}

/**
 * Inline error card for displaying errors within content
 */
@Composable
fun ErrorCard(
    message: String,
    errorType: ErrorType = ErrorType.GENERIC,
    onRetry: (() -> Unit)? = null,
    onDismiss: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer
        )
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = errorType.icon,
                contentDescription = null,
                modifier = Modifier.size(24.dp),
                tint = MaterialTheme.colorScheme.error
            )

            Spacer(modifier = Modifier.width(12.dp))

            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onErrorContainer,
                modifier = Modifier.weight(1f)
            )

            if (onRetry != null) {
                IconButton(onClick = onRetry) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Réessayer",
                        tint = MaterialTheme.colorScheme.error
                    )
                }
            }

            if (onDismiss != null) {
                IconButton(onClick = onDismiss) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Fermer",
                        tint = MaterialTheme.colorScheme.onErrorContainer
                    )
                }
            }
        }
    }
}

/**
 * Snackbar-style error banner
 */
@Composable
fun ErrorBanner(
    message: String,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.error
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.ErrorOutline,
                contentDescription = null,
                modifier = Modifier.size(20.dp),
                tint = MaterialTheme.colorScheme.onError
            )

            Spacer(modifier = Modifier.width(12.dp))

            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onError,
                modifier = Modifier.weight(1f)
            )

            if (onRetry != null) {
                TextButton(
                    onClick = onRetry,
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.onError
                    )
                ) {
                    Text("Réessayer")
                }
            }
        }
    }
}

/**
 * Inline error text for form fields
 */
@Composable
fun ErrorText(
    message: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = Icons.Default.Error,
            contentDescription = null,
            modifier = Modifier.size(16.dp),
            tint = MaterialTheme.colorScheme.error
        )
        Spacer(modifier = Modifier.width(4.dp))
        Text(
            text = message,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.error
        )
    }
}

/**
 * Retry button component
 */
@Composable
fun RetryButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    text: String = "Réessayer",
    isLoading: Boolean = false
) {
    Button(
        onClick = onClick,
        modifier = modifier,
        enabled = !isLoading
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.size(18.dp),
                color = MaterialTheme.colorScheme.onPrimary,
                strokeWidth = 2.dp
            )
        } else {
            Icon(
                imageVector = Icons.Default.Refresh,
                contentDescription = null,
                modifier = Modifier.size(18.dp)
            )
        }
        Spacer(modifier = Modifier.width(8.dp))
        Text(text)
    }
}

/**
 * Dialog for critical errors
 */
@Composable
fun ErrorDialog(
    errorType: ErrorType = ErrorType.GENERIC,
    title: String? = null,
    message: String? = null,
    onDismiss: () -> Unit,
    onRetry: (() -> Unit)? = null,
    dismissText: String = "Fermer",
    retryText: String = "Réessayer"
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {
            Icon(
                imageVector = errorType.icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.error
            )
        },
        title = {
            Text(text = title ?: errorType.defaultTitle)
        },
        text = {
            Text(text = message ?: errorType.defaultMessage)
        },
        confirmButton = {
            if (onRetry != null) {
                TextButton(onClick = onRetry) {
                    Text(retryText)
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(dismissText)
            }
        }
    )
}

// Previews

@Preview(showBackground = true)
@Composable
private fun FullScreenErrorPreview() {
    MaterialTheme {
        FullScreenError(
            errorType = ErrorType.NETWORK,
            onRetry = {},
            onSecondaryAction = {},
            secondaryActionLabel = "Paramètres Wi-Fi"
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun ErrorCardPreview() {
    MaterialTheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            ErrorCard(
                message = "Impossible de charger les transactions",
                errorType = ErrorType.NETWORK,
                onRetry = {}
            )
            ErrorCard(
                message = "Une erreur s'est produite",
                onDismiss = {}
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun ErrorBannerPreview() {
    MaterialTheme {
        ErrorBanner(
            message = "Connexion perdue",
            onRetry = {}
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun ErrorTextPreview() {
    MaterialTheme {
        Column(modifier = Modifier.padding(16.dp)) {
            ErrorText(message = "Ce champ est requis")
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun RetryButtonPreview() {
    MaterialTheme {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            RetryButton(onClick = {})
            RetryButton(onClick = {}, isLoading = true)
        }
    }
}
