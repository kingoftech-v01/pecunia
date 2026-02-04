package com.pecunia.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for authentication screens
 * Handles login, registration, and password reset logic
 */
@HiltViewModel
class AuthViewModel @Inject constructor(
    // Inject repositories here when available
    // private val authRepository: AuthRepository,
    // private val biometricManager: BiometricManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    private val _navigationEvents = Channel<AuthNavigationEvent>()
    val navigationEvents = _navigationEvents.receiveAsFlow()

    init {
        checkBiometricAvailability()
    }

    // ==================== Field Updates ====================

    fun updateEmail(email: String) {
        _uiState.update { it.copy(email = email, emailError = null, errorMessage = null) }
    }

    fun updatePassword(password: String) {
        _uiState.update { it.copy(password = password, passwordError = null, errorMessage = null) }
    }

    fun updateConfirmPassword(confirmPassword: String) {
        _uiState.update { it.copy(confirmPassword = confirmPassword, confirmPasswordError = null, errorMessage = null) }
    }

    fun updateFirstName(firstName: String) {
        _uiState.update { it.copy(firstName = firstName, firstNameError = null, errorMessage = null) }
    }

    fun updateLastName(lastName: String) {
        _uiState.update { it.copy(lastName = lastName, lastNameError = null, errorMessage = null) }
    }

    fun togglePasswordVisibility() {
        _uiState.update { it.copy(isPasswordVisible = !it.isPasswordVisible) }
    }

    fun toggleConfirmPasswordVisibility() {
        _uiState.update { it.copy(isConfirmPasswordVisible = !it.isConfirmPasswordVisible) }
    }

    fun toggleRememberMe() {
        _uiState.update { it.copy(rememberMe = !it.rememberMe) }
    }

    fun toggleTermsAcceptance() {
        _uiState.update { it.copy(acceptedTerms = !it.acceptedTerms, termsError = null) }
    }

    // ==================== Login ====================

    fun login() {
        val currentState = _uiState.value

        // Validate fields
        val emailValidation = EmailValidator.validate(currentState.email)
        if (!emailValidation.isValid) {
            _uiState.update { it.copy(emailError = emailValidation.errorMessage) }
            return
        }

        if (currentState.password.isBlank()) {
            _uiState.update { it.copy(passwordError = "Password is required") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, authResult = AuthResult.Loading, errorMessage = null) }

            try {
                // Simulate API call - Replace with actual repository call
                delay(1500)

                // Simulated success
                // val result = authRepository.login(currentState.email, currentState.password, currentState.rememberMe)

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Success,
                        successMessage = "Login successful!"
                    )
                }

                _navigationEvents.send(AuthNavigationEvent.NavigateToHome)

            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Error(e.message ?: "Login failed"),
                        errorMessage = e.message ?: "An error occurred during login"
                    )
                }
            }
        }
    }

    fun loginWithBiometric() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, authResult = AuthResult.Loading) }

            try {
                // Simulate biometric authentication
                delay(1000)

                // val result = biometricManager.authenticate()

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Success,
                        successMessage = "Biometric login successful!"
                    )
                }

                _navigationEvents.send(AuthNavigationEvent.NavigateToHome)

            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Error(e.message ?: "Biometric authentication failed"),
                        errorMessage = e.message ?: "Biometric authentication failed"
                    )
                }
            }
        }
    }

    fun loginWithGoogle() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, authResult = AuthResult.Loading) }

            try {
                delay(1500)
                // val result = authRepository.loginWithGoogle()

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Success
                    )
                }

                _navigationEvents.send(AuthNavigationEvent.NavigateToHome)

            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Error(e.message ?: "Google login failed"),
                        errorMessage = "Google sign-in failed. Please try again."
                    )
                }
            }
        }
    }

    fun loginWithApple() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, authResult = AuthResult.Loading) }

            try {
                delay(1500)
                // val result = authRepository.loginWithApple()

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Success
                    )
                }

                _navigationEvents.send(AuthNavigationEvent.NavigateToHome)

            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Error(e.message ?: "Apple login failed"),
                        errorMessage = "Apple sign-in failed. Please try again."
                    )
                }
            }
        }
    }

    // ==================== Registration ====================

    fun register() {
        val currentState = _uiState.value

        when (currentState.registrationStep) {
            RegistrationStep.CREDENTIALS -> validateAndProceedToPersonalInfo()
            RegistrationStep.PERSONAL_INFO -> validateAndProceedToTerms()
            RegistrationStep.TERMS_ACCEPTANCE -> submitRegistration()
        }
    }

    private fun validateAndProceedToPersonalInfo() {
        val currentState = _uiState.value
        var hasError = false

        val emailValidation = EmailValidator.validate(currentState.email)
        if (!emailValidation.isValid) {
            _uiState.update { it.copy(emailError = emailValidation.errorMessage) }
            hasError = true
        }

        val passwordValidation = PasswordValidator.validate(currentState.password)
        if (!passwordValidation.isValid) {
            _uiState.update { it.copy(passwordError = passwordValidation.errorMessage) }
            hasError = true
        }

        val confirmValidation = PasswordValidator.validateConfirmation(currentState.password, currentState.confirmPassword)
        if (!confirmValidation.isValid) {
            _uiState.update { it.copy(confirmPasswordError = confirmValidation.errorMessage) }
            hasError = true
        }

        if (!hasError) {
            _uiState.update { it.copy(registrationStep = RegistrationStep.PERSONAL_INFO) }
        }
    }

    private fun validateAndProceedToTerms() {
        val currentState = _uiState.value
        var hasError = false

        val firstNameValidation = NameValidator.validate(currentState.firstName, "First name")
        if (!firstNameValidation.isValid) {
            _uiState.update { it.copy(firstNameError = firstNameValidation.errorMessage) }
            hasError = true
        }

        val lastNameValidation = NameValidator.validate(currentState.lastName, "Last name")
        if (!lastNameValidation.isValid) {
            _uiState.update { it.copy(lastNameError = lastNameValidation.errorMessage) }
            hasError = true
        }

        if (!hasError) {
            _uiState.update { it.copy(registrationStep = RegistrationStep.TERMS_ACCEPTANCE) }
        }
    }

    private fun submitRegistration() {
        val currentState = _uiState.value

        if (!currentState.acceptedTerms) {
            _uiState.update { it.copy(termsError = "You must accept the terms and conditions") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, authResult = AuthResult.Loading, errorMessage = null) }

            try {
                // Simulate API call
                delay(2000)

                // val result = authRepository.register(
                //     email = currentState.email,
                //     password = currentState.password,
                //     firstName = currentState.firstName,
                //     lastName = currentState.lastName
                // )

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Success,
                        successMessage = "Registration successful! Please check your email to verify your account."
                    )
                }

                _navigationEvents.send(AuthNavigationEvent.NavigateToLogin)

            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Error(e.message ?: "Registration failed"),
                        errorMessage = e.message ?: "An error occurred during registration"
                    )
                }
            }
        }
    }

    fun goToPreviousStep() {
        val currentState = _uiState.value

        when (currentState.registrationStep) {
            RegistrationStep.PERSONAL_INFO -> {
                _uiState.update { it.copy(registrationStep = RegistrationStep.CREDENTIALS) }
            }
            RegistrationStep.TERMS_ACCEPTANCE -> {
                _uiState.update { it.copy(registrationStep = RegistrationStep.PERSONAL_INFO) }
            }
            else -> {
                viewModelScope.launch {
                    _navigationEvents.send(AuthNavigationEvent.NavigateBack)
                }
            }
        }
    }

    // ==================== Forgot Password ====================

    fun forgotPassword() {
        val currentState = _uiState.value

        val emailValidation = EmailValidator.validate(currentState.email)
        if (!emailValidation.isValid) {
            _uiState.update { it.copy(emailError = emailValidation.errorMessage) }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, authResult = AuthResult.Loading, errorMessage = null) }

            try {
                // Simulate API call
                delay(1500)

                // val result = authRepository.sendPasswordResetEmail(currentState.email)

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Success,
                        successMessage = "Password reset link sent to ${currentState.email}. Please check your inbox."
                    )
                }

            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        authResult = AuthResult.Error(e.message ?: "Failed to send reset email"),
                        errorMessage = e.message ?: "Failed to send password reset email"
                    )
                }
            }
        }
    }

    // ==================== Navigation ====================

    fun navigateToRegister() {
        viewModelScope.launch {
            resetState()
            _navigationEvents.send(AuthNavigationEvent.NavigateToRegister)
        }
    }

    fun navigateToLogin() {
        viewModelScope.launch {
            resetState()
            _navigationEvents.send(AuthNavigationEvent.NavigateToLogin)
        }
    }

    fun navigateToForgotPassword() {
        viewModelScope.launch {
            _uiState.update { it.copy(errorMessage = null, successMessage = null) }
            _navigationEvents.send(AuthNavigationEvent.NavigateToForgotPassword)
        }
    }

    fun navigateBack() {
        viewModelScope.launch {
            _navigationEvents.send(AuthNavigationEvent.NavigateBack)
        }
    }

    // ==================== Utility ====================

    private fun checkBiometricAvailability() {
        // Check if device supports biometric authentication
        // val isAvailable = biometricManager.isBiometricAvailable()
        val isAvailable = true // Simulated
        _uiState.update { it.copy(isBiometricAvailable = isAvailable) }
    }

    fun resetState() {
        _uiState.value = AuthUiState(
            isBiometricAvailable = _uiState.value.isBiometricAvailable
        )
    }

    fun clearError() {
        _uiState.update { it.copy(errorMessage = null, authResult = AuthResult.Idle) }
    }

    fun clearSuccess() {
        _uiState.update { it.copy(successMessage = null) }
    }
}
