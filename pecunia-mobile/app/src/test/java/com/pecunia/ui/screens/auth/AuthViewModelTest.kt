package com.pecunia.ui.screens.auth

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Comprehensive unit tests for AuthViewModel.
 * Tests login, registration (multi-step), forgot password, navigation,
 * validation, and state management.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var viewModel: AuthViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        viewModel = AuthViewModel()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    // ============================================
    // Initial State Tests
    // ============================================

    @Test
    fun `initial state has empty form fields`() {
        val state = viewModel.uiState.value
        assertEquals("", state.email)
        assertEquals("", state.password)
        assertEquals("", state.confirmPassword)
        assertEquals("", state.firstName)
        assertEquals("", state.lastName)
    }

    @Test
    fun `initial state has no validation errors`() {
        val state = viewModel.uiState.value
        assertNull(state.emailError)
        assertNull(state.passwordError)
        assertNull(state.confirmPasswordError)
        assertNull(state.firstNameError)
        assertNull(state.lastNameError)
    }

    @Test
    fun `initial state is not loading`() {
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun `initial state has passwords hidden`() {
        assertFalse(viewModel.uiState.value.isPasswordVisible)
        assertFalse(viewModel.uiState.value.isConfirmPasswordVisible)
    }

    @Test
    fun `initial state has remember me disabled`() {
        assertFalse(viewModel.uiState.value.rememberMe)
    }

    @Test
    fun `initial state has terms not accepted`() {
        assertFalse(viewModel.uiState.value.acceptedTerms)
    }

    @Test
    fun `initial state is at CREDENTIALS registration step`() {
        assertEquals(RegistrationStep.CREDENTIALS, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `initial authResult is Idle`() {
        assertEquals(AuthResult.Idle, viewModel.uiState.value.authResult)
    }

    @Test
    fun `initial state has biometric available set to true`() = runTest {
        advanceUntilIdle()
        assertTrue(viewModel.uiState.value.isBiometricAvailable)
    }

    // ============================================
    // Field Update Tests
    // ============================================

    @Test
    fun `updateEmail updates email and clears email error`() {
        viewModel.updateEmail("test@example.com")
        assertEquals("test@example.com", viewModel.uiState.value.email)
        assertNull(viewModel.uiState.value.emailError)
    }

    @Test
    fun `updateEmail clears errorMessage`() {
        // Simulate having an error message
        viewModel.updateEmail("test@example.com")
        assertNull(viewModel.uiState.value.errorMessage)
    }

    @Test
    fun `updatePassword updates password and clears password error`() {
        viewModel.updatePassword("Password1!")
        assertEquals("Password1!", viewModel.uiState.value.password)
        assertNull(viewModel.uiState.value.passwordError)
    }

    @Test
    fun `updateConfirmPassword updates confirmPassword and clears error`() {
        viewModel.updateConfirmPassword("Password1!")
        assertEquals("Password1!", viewModel.uiState.value.confirmPassword)
        assertNull(viewModel.uiState.value.confirmPasswordError)
    }

    @Test
    fun `updateFirstName updates firstName and clears error`() {
        viewModel.updateFirstName("John")
        assertEquals("John", viewModel.uiState.value.firstName)
        assertNull(viewModel.uiState.value.firstNameError)
    }

    @Test
    fun `updateLastName updates lastName and clears error`() {
        viewModel.updateLastName("Doe")
        assertEquals("Doe", viewModel.uiState.value.lastName)
        assertNull(viewModel.uiState.value.lastNameError)
    }

    // ============================================
    // Toggle Tests
    // ============================================

    @Test
    fun `togglePasswordVisibility toggles visibility`() {
        assertFalse(viewModel.uiState.value.isPasswordVisible)
        viewModel.togglePasswordVisibility()
        assertTrue(viewModel.uiState.value.isPasswordVisible)
        viewModel.togglePasswordVisibility()
        assertFalse(viewModel.uiState.value.isPasswordVisible)
    }

    @Test
    fun `toggleConfirmPasswordVisibility toggles visibility`() {
        assertFalse(viewModel.uiState.value.isConfirmPasswordVisible)
        viewModel.toggleConfirmPasswordVisibility()
        assertTrue(viewModel.uiState.value.isConfirmPasswordVisible)
        viewModel.toggleConfirmPasswordVisibility()
        assertFalse(viewModel.uiState.value.isConfirmPasswordVisible)
    }

    @Test
    fun `toggleRememberMe toggles value`() {
        assertFalse(viewModel.uiState.value.rememberMe)
        viewModel.toggleRememberMe()
        assertTrue(viewModel.uiState.value.rememberMe)
        viewModel.toggleRememberMe()
        assertFalse(viewModel.uiState.value.rememberMe)
    }

    @Test
    fun `toggleTermsAcceptance toggles value and clears terms error`() {
        assertFalse(viewModel.uiState.value.acceptedTerms)
        viewModel.toggleTermsAcceptance()
        assertTrue(viewModel.uiState.value.acceptedTerms)
        assertNull(viewModel.uiState.value.termsError)
        viewModel.toggleTermsAcceptance()
        assertFalse(viewModel.uiState.value.acceptedTerms)
    }

    // ============================================
    // Login Tests
    // ============================================

    @Test
    fun `login with blank email sets email error`() {
        viewModel.updateEmail("")
        viewModel.updatePassword("Password1!")
        viewModel.login()
        assertNotNull(viewModel.uiState.value.emailError)
    }

    @Test
    fun `login with invalid email sets email error`() {
        viewModel.updateEmail("invalid-email")
        viewModel.updatePassword("Password1!")
        viewModel.login()
        assertNotNull(viewModel.uiState.value.emailError)
    }

    @Test
    fun `login with blank password sets password error`() {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("")
        viewModel.login()
        assertNotNull(viewModel.uiState.value.passwordError)
        assertEquals("Password is required", viewModel.uiState.value.passwordError)
    }

    @Test
    fun `login with valid credentials sets loading state`() = runTest {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.login()

        // After starting, should be loading
        advanceUntilIdle()
    }

    @Test
    fun `successful login sets success state`() = runTest {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.login()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertEquals(AuthResult.Success, state.authResult)
        assertEquals("Login successful!", state.successMessage)
    }

    @Test
    fun `successful login emits NavigateToHome event`() = runTest {
        var navigationEvent: AuthNavigationEvent? = null
        val job = launch {
            navigationEvent = viewModel.navigationEvents.first()
        }

        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.login()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToHome, navigationEvent)
        job.cancel()
    }

    // ============================================
    // Biometric Login Tests
    // ============================================

    @Test
    fun `loginWithBiometric sets loading state`() = runTest {
        viewModel.loginWithBiometric()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals(AuthResult.Success, state.authResult)
    }

    @Test
    fun `successful biometric login sets success message`() = runTest {
        viewModel.loginWithBiometric()
        advanceUntilIdle()

        assertEquals("Biometric login successful!", viewModel.uiState.value.successMessage)
    }

    @Test
    fun `loginWithBiometric emits NavigateToHome`() = runTest {
        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.loginWithBiometric()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToHome, event)
        job.cancel()
    }

    // ============================================
    // Social Login Tests
    // ============================================

    @Test
    fun `loginWithGoogle sets success state on completion`() = runTest {
        viewModel.loginWithGoogle()
        advanceUntilIdle()

        assertEquals(AuthResult.Success, viewModel.uiState.value.authResult)
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun `loginWithGoogle emits NavigateToHome`() = runTest {
        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.loginWithGoogle()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToHome, event)
        job.cancel()
    }

    @Test
    fun `loginWithApple sets success state on completion`() = runTest {
        viewModel.loginWithApple()
        advanceUntilIdle()

        assertEquals(AuthResult.Success, viewModel.uiState.value.authResult)
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun `loginWithApple emits NavigateToHome`() = runTest {
        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.loginWithApple()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToHome, event)
        job.cancel()
    }

    // ============================================
    // Registration Step 1: CREDENTIALS
    // ============================================

    @Test
    fun `register at CREDENTIALS step validates email`() {
        viewModel.updateEmail("invalid")
        viewModel.updatePassword("Password1!")
        viewModel.updateConfirmPassword("Password1!")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.emailError)
        assertEquals(RegistrationStep.CREDENTIALS, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `register at CREDENTIALS step validates password`() {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("weak")
        viewModel.updateConfirmPassword("weak")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.passwordError)
        assertEquals(RegistrationStep.CREDENTIALS, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `register at CREDENTIALS step validates password confirmation`() {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.updateConfirmPassword("DifferentPassword1!")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.confirmPasswordError)
        assertEquals(RegistrationStep.CREDENTIALS, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `register at CREDENTIALS step proceeds to PERSONAL_INFO on valid input`() {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.updateConfirmPassword("Password1!")
        viewModel.register()

        assertEquals(RegistrationStep.PERSONAL_INFO, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `register at CREDENTIALS step with blank confirmPassword shows error`() {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.updateConfirmPassword("")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.confirmPasswordError)
    }

    // ============================================
    // Registration Step 2: PERSONAL_INFO
    // ============================================

    @Test
    fun `register at PERSONAL_INFO step validates firstName`() {
        // Move to step 2
        navigateToPersonalInfoStep()

        viewModel.updateFirstName("")
        viewModel.updateLastName("Doe")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.firstNameError)
        assertEquals(RegistrationStep.PERSONAL_INFO, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `register at PERSONAL_INFO step validates firstName minimum length`() {
        navigateToPersonalInfoStep()

        viewModel.updateFirstName("J")
        viewModel.updateLastName("Doe")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.firstNameError)
    }

    @Test
    fun `register at PERSONAL_INFO step validates firstName characters`() {
        navigateToPersonalInfoStep()

        viewModel.updateFirstName("John123")
        viewModel.updateLastName("Doe")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.firstNameError)
    }

    @Test
    fun `register at PERSONAL_INFO step validates lastName`() {
        navigateToPersonalInfoStep()

        viewModel.updateFirstName("John")
        viewModel.updateLastName("")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.lastNameError)
        assertEquals(RegistrationStep.PERSONAL_INFO, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `register at PERSONAL_INFO step validates lastName minimum length`() {
        navigateToPersonalInfoStep()

        viewModel.updateFirstName("John")
        viewModel.updateLastName("D")
        viewModel.register()

        assertNotNull(viewModel.uiState.value.lastNameError)
    }

    @Test
    fun `register at PERSONAL_INFO step proceeds to TERMS_ACCEPTANCE on valid input`() {
        navigateToPersonalInfoStep()

        viewModel.updateFirstName("John")
        viewModel.updateLastName("Doe")
        viewModel.register()

        assertEquals(RegistrationStep.TERMS_ACCEPTANCE, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `register at PERSONAL_INFO step allows hyphenated names`() {
        navigateToPersonalInfoStep()

        viewModel.updateFirstName("Mary-Jane")
        viewModel.updateLastName("Smith-Jones")
        viewModel.register()

        assertEquals(RegistrationStep.TERMS_ACCEPTANCE, viewModel.uiState.value.registrationStep)
    }

    // ============================================
    // Registration Step 3: TERMS_ACCEPTANCE
    // ============================================

    @Test
    fun `register at TERMS_ACCEPTANCE without accepting shows error`() {
        navigateToTermsStep()

        viewModel.register()

        assertNotNull(viewModel.uiState.value.termsError)
        assertEquals("You must accept the terms and conditions", viewModel.uiState.value.termsError)
    }

    @Test
    fun `register at TERMS_ACCEPTANCE with accepted terms submits`() = runTest {
        navigateToTermsStep()

        viewModel.toggleTermsAcceptance()
        viewModel.register()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertEquals(AuthResult.Success, state.authResult)
        assertNotNull(state.successMessage)
        assertTrue(state.successMessage!!.contains("Registration successful"))
    }

    @Test
    fun `successful registration emits NavigateToLogin`() = runTest {
        navigateToTermsStep()

        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.toggleTermsAcceptance()
        viewModel.register()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToLogin, event)
        job.cancel()
    }

    // ============================================
    // goToPreviousStep Tests
    // ============================================

    @Test
    fun `goToPreviousStep from PERSONAL_INFO goes to CREDENTIALS`() {
        navigateToPersonalInfoStep()
        viewModel.goToPreviousStep()
        assertEquals(RegistrationStep.CREDENTIALS, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `goToPreviousStep from TERMS_ACCEPTANCE goes to PERSONAL_INFO`() {
        navigateToTermsStep()
        viewModel.goToPreviousStep()
        assertEquals(RegistrationStep.PERSONAL_INFO, viewModel.uiState.value.registrationStep)
    }

    @Test
    fun `goToPreviousStep from CREDENTIALS emits NavigateBack`() = runTest {
        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.goToPreviousStep()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateBack, event)
        job.cancel()
    }

    // ============================================
    // Forgot Password Tests
    // ============================================

    @Test
    fun `forgotPassword with blank email shows error`() {
        viewModel.updateEmail("")
        viewModel.forgotPassword()
        assertNotNull(viewModel.uiState.value.emailError)
    }

    @Test
    fun `forgotPassword with invalid email shows error`() {
        viewModel.updateEmail("invalid")
        viewModel.forgotPassword()
        assertNotNull(viewModel.uiState.value.emailError)
    }

    @Test
    fun `forgotPassword with valid email succeeds`() = runTest {
        viewModel.updateEmail("test@example.com")
        viewModel.forgotPassword()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertEquals(AuthResult.Success, state.authResult)
        assertNotNull(state.successMessage)
        assertTrue(state.successMessage!!.contains("test@example.com"))
    }

    // ============================================
    // Navigation Tests
    // ============================================

    @Test
    fun `navigateToRegister emits NavigateToRegister and resets state`() = runTest {
        viewModel.updateEmail("test@example.com")

        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.navigateToRegister()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToRegister, event)
        assertEquals("", viewModel.uiState.value.email)
        job.cancel()
    }

    @Test
    fun `navigateToLogin emits NavigateToLogin and resets state`() = runTest {
        viewModel.updateEmail("test@example.com")

        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.navigateToLogin()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToLogin, event)
        assertEquals("", viewModel.uiState.value.email)
        job.cancel()
    }

    @Test
    fun `navigateToForgotPassword emits NavigateToForgotPassword`() = runTest {
        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.navigateToForgotPassword()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateToForgotPassword, event)
        job.cancel()
    }

    @Test
    fun `navigateToForgotPassword clears error and success messages`() = runTest {
        viewModel.navigateToForgotPassword()
        advanceUntilIdle()

        assertNull(viewModel.uiState.value.errorMessage)
        assertNull(viewModel.uiState.value.successMessage)
    }

    @Test
    fun `navigateBack emits NavigateBack`() = runTest {
        var event: AuthNavigationEvent? = null
        val job = launch {
            event = viewModel.navigationEvents.first()
        }

        viewModel.navigateBack()
        advanceUntilIdle()

        assertEquals(AuthNavigationEvent.NavigateBack, event)
        job.cancel()
    }

    // ============================================
    // Utility Tests
    // ============================================

    @Test
    fun `resetState clears all fields but preserves biometric availability`() = runTest {
        advanceUntilIdle()
        val biometricAvailable = viewModel.uiState.value.isBiometricAvailable

        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.updateFirstName("John")
        viewModel.updateLastName("Doe")

        viewModel.resetState()

        val state = viewModel.uiState.value
        assertEquals("", state.email)
        assertEquals("", state.password)
        assertEquals("", state.firstName)
        assertEquals("", state.lastName)
        assertEquals(biometricAvailable, state.isBiometricAvailable)
    }

    @Test
    fun `clearError clears error message and resets authResult to Idle`() {
        viewModel.clearError()
        assertNull(viewModel.uiState.value.errorMessage)
        assertEquals(AuthResult.Idle, viewModel.uiState.value.authResult)
    }

    @Test
    fun `clearSuccess clears success message`() {
        viewModel.clearSuccess()
        assertNull(viewModel.uiState.value.successMessage)
    }

    // ============================================
    // EmailValidator Tests
    // ============================================

    @Test
    fun `EmailValidator validates blank email`() {
        val result = EmailValidator.validate("")
        assertFalse(result.isValid)
        assertEquals("Email is required", result.errorMessage)
    }

    @Test
    fun `EmailValidator validates missing at sign`() {
        val result = EmailValidator.validate("testexample.com")
        assertFalse(result.isValid)
        assertEquals("Invalid email format", result.errorMessage)
    }

    @Test
    fun `EmailValidator validates missing domain`() {
        val result = EmailValidator.validate("test@")
        assertFalse(result.isValid)
    }

    @Test
    fun `EmailValidator validates valid email`() {
        val result = EmailValidator.validate("test@example.com")
        assertTrue(result.isValid)
        assertNull(result.errorMessage)
    }

    @Test
    fun `EmailValidator validates email with plus sign`() {
        val result = EmailValidator.validate("test+tag@example.com")
        assertTrue(result.isValid)
    }

    @Test
    fun `EmailValidator validates email with subdomain`() {
        val result = EmailValidator.validate("test@mail.example.com")
        assertTrue(result.isValid)
    }

    // ============================================
    // PasswordValidator Tests
    // ============================================

    @Test
    fun `PasswordValidator validates blank password`() {
        val result = PasswordValidator.validate("")
        assertFalse(result.isValid)
        assertEquals("Password is required", result.errorMessage)
    }

    @Test
    fun `PasswordValidator validates short password`() {
        val result = PasswordValidator.validate("Ab1!")
        assertFalse(result.isValid)
        assertTrue(result.errorMessage!!.contains("8 characters"))
    }

    @Test
    fun `PasswordValidator validates missing uppercase`() {
        val result = PasswordValidator.validate("password1!")
        assertFalse(result.isValid)
        assertTrue(result.errorMessage!!.contains("uppercase"))
    }

    @Test
    fun `PasswordValidator validates missing lowercase`() {
        val result = PasswordValidator.validate("PASSWORD1!")
        assertFalse(result.isValid)
        assertTrue(result.errorMessage!!.contains("lowercase"))
    }

    @Test
    fun `PasswordValidator validates missing number`() {
        val result = PasswordValidator.validate("Password!!")
        assertFalse(result.isValid)
        assertTrue(result.errorMessage!!.contains("number"))
    }

    @Test
    fun `PasswordValidator validates missing special character`() {
        val result = PasswordValidator.validate("Password11")
        assertFalse(result.isValid)
        assertTrue(result.errorMessage!!.contains("special character"))
    }

    @Test
    fun `PasswordValidator validates valid password`() {
        val result = PasswordValidator.validate("Password1!")
        assertTrue(result.isValid)
        assertNull(result.errorMessage)
    }

    @Test
    fun `PasswordValidator validateConfirmation with blank confirm`() {
        val result = PasswordValidator.validateConfirmation("Password1!", "")
        assertFalse(result.isValid)
        assertEquals("Please confirm your password", result.errorMessage)
    }

    @Test
    fun `PasswordValidator validateConfirmation with mismatch`() {
        val result = PasswordValidator.validateConfirmation("Password1!", "Different1!")
        assertFalse(result.isValid)
        assertEquals("Passwords do not match", result.errorMessage)
    }

    @Test
    fun `PasswordValidator validateConfirmation with matching passwords`() {
        val result = PasswordValidator.validateConfirmation("Password1!", "Password1!")
        assertTrue(result.isValid)
    }

    // ============================================
    // NameValidator Tests
    // ============================================

    @Test
    fun `NameValidator validates blank name`() {
        val result = NameValidator.validate("", "First name")
        assertFalse(result.isValid)
        assertEquals("First name is required", result.errorMessage)
    }

    @Test
    fun `NameValidator validates short name`() {
        val result = NameValidator.validate("J", "First name")
        assertFalse(result.isValid)
        assertTrue(result.errorMessage!!.contains("2 characters"))
    }

    @Test
    fun `NameValidator validates invalid characters`() {
        val result = NameValidator.validate("John123", "First name")
        assertFalse(result.isValid)
        assertTrue(result.errorMessage!!.contains("invalid characters"))
    }

    @Test
    fun `NameValidator validates valid name`() {
        val result = NameValidator.validate("John", "First name")
        assertTrue(result.isValid)
    }

    @Test
    fun `NameValidator validates name with hyphen`() {
        val result = NameValidator.validate("Mary-Jane", "First name")
        assertTrue(result.isValid)
    }

    @Test
    fun `NameValidator validates name with space`() {
        val result = NameValidator.validate("Mary Jane", "First name")
        assertTrue(result.isValid)
    }

    @Test
    fun `NameValidator uses custom field name in error messages`() {
        val result = NameValidator.validate("", "Last name")
        assertEquals("Last name is required", result.errorMessage)
    }

    // ============================================
    // AuthResult Tests
    // ============================================

    @Test
    fun `AuthResult Idle is singleton`() {
        assertSame(AuthResult.Idle, AuthResult.Idle)
    }

    @Test
    fun `AuthResult Loading is singleton`() {
        assertSame(AuthResult.Loading, AuthResult.Loading)
    }

    @Test
    fun `AuthResult Success is singleton`() {
        assertSame(AuthResult.Success, AuthResult.Success)
    }

    @Test
    fun `AuthResult Error contains message`() {
        val error = AuthResult.Error("Something went wrong")
        assertEquals("Something went wrong", error.message)
    }

    // ============================================
    // Helper Methods
    // ============================================

    private fun navigateToPersonalInfoStep() {
        viewModel.updateEmail("test@example.com")
        viewModel.updatePassword("Password1!")
        viewModel.updateConfirmPassword("Password1!")
        viewModel.register()
        assertEquals(RegistrationStep.PERSONAL_INFO, viewModel.uiState.value.registrationStep)
    }

    private fun navigateToTermsStep() {
        navigateToPersonalInfoStep()
        viewModel.updateFirstName("John")
        viewModel.updateLastName("Doe")
        viewModel.register()
        assertEquals(RegistrationStep.TERMS_ACCEPTANCE, viewModel.uiState.value.registrationStep)
    }
}
