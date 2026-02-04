package com.pecunia.ui.screens.auth

/**
 * Represents the UI state for authentication screens
 */
data class AuthUiState(
    // Form fields
    val email: String = "",
    val password: String = "",
    val confirmPassword: String = "",
    val firstName: String = "",
    val lastName: String = "",

    // Validation states
    val emailError: String? = null,
    val passwordError: String? = null,
    val confirmPasswordError: String? = null,
    val firstNameError: String? = null,
    val lastNameError: String? = null,

    // UI states
    val isLoading: Boolean = false,
    val isPasswordVisible: Boolean = false,
    val isConfirmPasswordVisible: Boolean = false,
    val rememberMe: Boolean = false,
    val acceptedTerms: Boolean = false,
    val termsError: String? = null,

    // Multi-step registration
    val registrationStep: RegistrationStep = RegistrationStep.CREDENTIALS,

    // Biometric
    val isBiometricAvailable: Boolean = false,
    val isBiometricEnabled: Boolean = false,

    // Result states
    val authResult: AuthResult = AuthResult.Idle,
    val errorMessage: String? = null,
    val successMessage: String? = null
)

/**
 * Registration steps for multi-step form
 */
enum class RegistrationStep {
    CREDENTIALS,
    PERSONAL_INFO,
    TERMS_ACCEPTANCE
}

/**
 * Sealed class representing authentication results
 */
sealed class AuthResult {
    object Idle : AuthResult()
    object Loading : AuthResult()
    object Success : AuthResult()
    data class Error(val message: String) : AuthResult()
}

/**
 * Navigation events from auth screens
 */
sealed class AuthNavigationEvent {
    object NavigateToHome : AuthNavigationEvent()
    object NavigateToLogin : AuthNavigationEvent()
    object NavigateToRegister : AuthNavigationEvent()
    object NavigateToForgotPassword : AuthNavigationEvent()
    object NavigateBack : AuthNavigationEvent()
}

/**
 * Form validation result
 */
data class ValidationResult(
    val isValid: Boolean,
    val errorMessage: String? = null
)

/**
 * Email validation utility
 */
object EmailValidator {
    private val EMAIL_REGEX = Regex(
        "[a-zA-Z0-9+._%\\-]{1,256}" +
                "@" +
                "[a-zA-Z0-9][a-zA-Z0-9\\-]{0,64}" +
                "(" +
                "\\." +
                "[a-zA-Z0-9][a-zA-Z0-9\\-]{0,25}" +
                ")+"
    )

    fun validate(email: String): ValidationResult {
        return when {
            email.isBlank() -> ValidationResult(false, "Email is required")
            !EMAIL_REGEX.matches(email) -> ValidationResult(false, "Invalid email format")
            else -> ValidationResult(true)
        }
    }
}

/**
 * Password validation utility
 */
object PasswordValidator {
    private const val MIN_LENGTH = 8

    fun validate(password: String): ValidationResult {
        return when {
            password.isBlank() -> ValidationResult(false, "Password is required")
            password.length < MIN_LENGTH -> ValidationResult(false, "Password must be at least $MIN_LENGTH characters")
            !password.any { it.isUpperCase() } -> ValidationResult(false, "Password must contain an uppercase letter")
            !password.any { it.isLowerCase() } -> ValidationResult(false, "Password must contain a lowercase letter")
            !password.any { it.isDigit() } -> ValidationResult(false, "Password must contain a number")
            !password.any { !it.isLetterOrDigit() } -> ValidationResult(false, "Password must contain a special character")
            else -> ValidationResult(true)
        }
    }

    fun validateConfirmation(password: String, confirmPassword: String): ValidationResult {
        return when {
            confirmPassword.isBlank() -> ValidationResult(false, "Please confirm your password")
            password != confirmPassword -> ValidationResult(false, "Passwords do not match")
            else -> ValidationResult(true)
        }
    }
}

/**
 * Name validation utility
 */
object NameValidator {
    fun validate(name: String, fieldName: String): ValidationResult {
        return when {
            name.isBlank() -> ValidationResult(false, "$fieldName is required")
            name.length < 2 -> ValidationResult(false, "$fieldName must be at least 2 characters")
            !name.all { it.isLetter() || it.isWhitespace() || it == '-' } ->
                ValidationResult(false, "$fieldName contains invalid characters")
            else -> ValidationResult(true)
        }
    }
}
