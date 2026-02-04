"""
Login/Register Pages Module

Authentication pages for user login and registration.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QLineEdit, QCheckBox,
    QStackedWidget, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QFont, QRegularExpressionValidator, QPixmap
from typing import Optional, Dict, Any
import re


class PasswordStrengthIndicator(QWidget):
    """Widget showing password strength."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the indicator UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(5)

        # Strength bars
        bars_layout = QHBoxLayout()
        bars_layout.setSpacing(3)

        self.bars = []
        for _ in range(4):
            bar = QFrame()
            bar.setFixedHeight(4)
            bar.setStyleSheet("background-color: #E0E0E0; border-radius: 2px;")
            self.bars.append(bar)
            bars_layout.addWidget(bar)

        layout.addLayout(bars_layout)

        # Strength label
        self.strength_label = QLabel("")
        self.strength_label.setFont(QFont("Segoe UI", 9))
        self.strength_label.setObjectName("passwordStrengthLabel")
        layout.addWidget(self.strength_label)

    def update_strength(self, password: str):
        """Update the strength indicator based on password."""
        strength = self._calculate_strength(password)

        # Define colors and labels
        colors = ["#F44336", "#FF9800", "#FFC107", "#4CAF50"]
        labels = ["Weak", "Fair", "Good", "Strong"]

        # Reset bars
        for bar in self.bars:
            bar.setStyleSheet("background-color: #E0E0E0; border-radius: 2px;")

        if not password:
            self.strength_label.setText("")
            return

        # Update bars based on strength
        for i in range(strength):
            self.bars[i].setStyleSheet(f"background-color: {colors[strength - 1]}; border-radius: 2px;")

        self.strength_label.setText(labels[strength - 1])
        self.strength_label.setStyleSheet(f"color: {colors[strength - 1]};")

    def _calculate_strength(self, password: str) -> int:
        """Calculate password strength (1-4)."""
        if len(password) < 6:
            return 1

        strength = 1

        # Length bonus
        if len(password) >= 8:
            strength += 1

        # Complexity checks
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

        complexity = sum([has_lower, has_upper, has_digit, has_special])

        if complexity >= 3:
            strength += 1
        if complexity >= 4 and len(password) >= 12:
            strength += 1

        return min(strength, 4)


class LoginForm(QFrame):
    """Login form widget."""

    login_requested = pyqtSignal(str, str, bool)  # email, password, remember
    forgot_password_requested = pyqtSignal()
    switch_to_register = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("loginForm")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the login form UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(400, 450)
        self.setMaximumSize(450, 550)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Logo/Title
        title = QLabel("Welcome Back")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("authTitle")
        layout.addWidget(title)

        subtitle = QLabel("Sign in to your account")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("authSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Email field
        email_label = QLabel("Email")
        email_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setObjectName("authInput")
        self.email_input.setMinimumHeight(45)
        layout.addWidget(self.email_input)

        # Password field
        password_label = QLabel("Password")
        password_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("authInput")
        self.password_input.setMinimumHeight(45)
        self.password_input.returnPressed.connect(self._on_login)
        layout.addWidget(self.password_input)

        # Remember me and forgot password
        options_layout = QHBoxLayout()

        self.remember_check = QCheckBox("Remember me")
        self.remember_check.setFont(QFont("Segoe UI", 10))
        options_layout.addWidget(self.remember_check)

        options_layout.addStretch()

        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setObjectName("linkButton")
        forgot_btn.clicked.connect(self.forgot_password_requested.emit)
        options_layout.addWidget(forgot_btn)

        layout.addLayout(options_layout)

        # Error message
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Segoe UI", 10))
        self.error_label.setStyleSheet("color: #E57373;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("primaryButton")
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

        layout.addStretch()

        # Switch to register
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        register_label = QLabel("Don't have an account?")
        register_label.setFont(QFont("Segoe UI", 10))
        register_layout.addWidget(register_label)

        register_btn = QPushButton("Sign Up")
        register_btn.setObjectName("linkButton")
        register_btn.clicked.connect(self.switch_to_register.emit)
        register_layout.addWidget(register_btn)

        layout.addLayout(register_layout)

    def _on_login(self):
        """Handle login button click."""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        remember = self.remember_check.isChecked()

        # Basic validation
        if not email:
            self.show_error("Please enter your email address.")
            return

        if not password:
            self.show_error("Please enter your password.")
            return

        if not self._is_valid_email(email):
            self.show_error("Please enter a valid email address.")
            return

        self.clear_error()
        self.login_requested.emit(email, password, remember)

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def show_error(self, message: str):
        """Show an error message."""
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self):
        """Clear the error message."""
        self.error_label.setText("")
        self.error_label.hide()

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.login_btn.setEnabled(not loading)
        self.email_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.remember_check.setEnabled(not loading)
        self.login_btn.setText("Signing in..." if loading else "Sign In")

    def clear_form(self):
        """Clear all form fields."""
        self.email_input.clear()
        self.password_input.clear()
        self.remember_check.setChecked(False)
        self.clear_error()


class RegisterForm(QFrame):
    """Registration form widget."""

    register_requested = pyqtSignal(str, str, str, str, str, str)  # email, password, confirm, first_name, last_name
    switch_to_login = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("registerForm")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the registration form UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(400, 650)
        self.setMaximumSize(450, 750)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(12)

        # Title
        title = QLabel("Create Account")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("authTitle")
        layout.addWidget(title)

        subtitle = QLabel("Sign up to get started")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("authSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # First and Last name fields (side by side)
        name_layout = QHBoxLayout()
        name_layout.setSpacing(10)

        # First name
        first_name_container = QVBoxLayout()
        first_name_label = QLabel("First Name")
        first_name_label.setFont(QFont("Segoe UI", 10))
        first_name_container.addWidget(first_name_label)

        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("First name")
        self.first_name_input.setObjectName("authInput")
        self.first_name_input.setMinimumHeight(42)
        first_name_container.addWidget(self.first_name_input)
        name_layout.addLayout(first_name_container)

        # Last name
        last_name_container = QVBoxLayout()
        last_name_label = QLabel("Last Name")
        last_name_label.setFont(QFont("Segoe UI", 10))
        last_name_container.addWidget(last_name_label)

        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Last name")
        self.last_name_input.setObjectName("authInput")
        self.last_name_input.setMinimumHeight(42)
        last_name_container.addWidget(self.last_name_input)
        name_layout.addLayout(last_name_container)

        layout.addLayout(name_layout)

        # Email field
        email_label = QLabel("Email")
        email_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setObjectName("authInput")
        self.email_input.setMinimumHeight(42)
        layout.addWidget(self.email_input)

        # Password field
        password_label = QLabel("Password")
        password_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Create a password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("authInput")
        self.password_input.setMinimumHeight(42)
        self.password_input.textChanged.connect(self._on_password_changed)
        layout.addWidget(self.password_input)

        # Password strength indicator
        self.strength_indicator = PasswordStrengthIndicator()
        layout.addWidget(self.strength_indicator)

        # Confirm password field
        confirm_label = QLabel("Confirm Password")
        confirm_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(confirm_label)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setObjectName("authInput")
        self.confirm_input.setMinimumHeight(42)
        self.confirm_input.returnPressed.connect(self._on_register)
        layout.addWidget(self.confirm_input)

        # Terms agreement
        self.terms_check = QCheckBox("I agree to the Terms of Service and Privacy Policy")
        self.terms_check.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.terms_check)

        # Error message
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Segoe UI", 10))
        self.error_label.setStyleSheet("color: #E57373;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Register button
        self.register_btn = QPushButton("Create Account")
        self.register_btn.setObjectName("primaryButton")
        self.register_btn.setMinimumHeight(45)
        self.register_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.register_btn.clicked.connect(self._on_register)
        layout.addWidget(self.register_btn)

        layout.addStretch()

        # Switch to login
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        login_label = QLabel("Already have an account?")
        login_label.setFont(QFont("Segoe UI", 10))
        login_layout.addWidget(login_label)

        login_btn = QPushButton("Sign In")
        login_btn.setObjectName("linkButton")
        login_btn.clicked.connect(self.switch_to_login.emit)
        login_layout.addWidget(login_btn)

        layout.addLayout(login_layout)

    def _on_password_changed(self, password: str):
        """Handle password text changes."""
        self.strength_indicator.update_strength(password)

    def _on_register(self):
        """Handle register button click."""
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        # Validation
        if not first_name:
            self.show_error("Please enter your first name.")
            return

        if not last_name:
            self.show_error("Please enter your last name.")
            return

        if not email:
            self.show_error("Please enter your email address.")
            return

        if not self._is_valid_email(email):
            self.show_error("Please enter a valid email address.")
            return

        if not password:
            self.show_error("Please enter a password.")
            return

        if len(password) < 8:
            self.show_error("Password must be at least 8 characters.")
            return

        if password != confirm:
            self.show_error("Passwords do not match.")
            return

        if not self.terms_check.isChecked():
            self.show_error("Please agree to the Terms of Service.")
            return

        self.clear_error()
        self.register_requested.emit(email, password, confirm, first_name, last_name, "")

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def show_error(self, message: str):
        """Show an error message."""
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self):
        """Clear the error message."""
        self.error_label.setText("")
        self.error_label.hide()

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.register_btn.setEnabled(not loading)
        self.first_name_input.setEnabled(not loading)
        self.last_name_input.setEnabled(not loading)
        self.email_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.confirm_input.setEnabled(not loading)
        self.terms_check.setEnabled(not loading)
        self.register_btn.setText("Creating Account..." if loading else "Create Account")

    def clear_form(self):
        """Clear all form fields."""
        self.first_name_input.clear()
        self.last_name_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.terms_check.setChecked(False)
        self.strength_indicator.update_strength("")
        self.clear_error()


class ForgotPasswordForm(QFrame):
    """Forgot password form widget."""

    reset_requested = pyqtSignal(str)  # email
    back_to_login = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("forgotPasswordForm")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the forgot password form UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(400, 350)
        self.setMaximumSize(450, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("Reset Password")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("authTitle")
        layout.addWidget(title)

        subtitle = QLabel("Enter your email address and we'll send you\ninstructions to reset your password.")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("authSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Email field
        email_label = QLabel("Email")
        email_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        self.email_input.setObjectName("authInput")
        self.email_input.setMinimumHeight(45)
        self.email_input.returnPressed.connect(self._on_reset)
        layout.addWidget(self.email_input)

        # Error/Success message
        self.message_label = QLabel("")
        self.message_label.setFont(QFont("Segoe UI", 10))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.hide()
        layout.addWidget(self.message_label)

        # Reset button
        self.reset_btn = QPushButton("Send Reset Link")
        self.reset_btn.setObjectName("primaryButton")
        self.reset_btn.setMinimumHeight(45)
        self.reset_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(self.reset_btn)

        layout.addStretch()

        # Back to login
        back_layout = QHBoxLayout()
        back_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        back_btn = QPushButton("Back to Sign In")
        back_btn.setObjectName("linkButton")
        back_btn.clicked.connect(self.back_to_login.emit)
        back_layout.addWidget(back_btn)

        layout.addLayout(back_layout)

    def _on_reset(self):
        """Handle reset button click."""
        email = self.email_input.text().strip()

        # Validation
        if not email:
            self.show_error("Please enter your email address.")
            return

        if not self._is_valid_email(email):
            self.show_error("Please enter a valid email address.")
            return

        self.clear_message()
        self.reset_requested.emit(email)

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def show_error(self, message: str):
        """Show an error message."""
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #E57373;")
        self.message_label.show()

    def show_success(self, message: str):
        """Show a success message."""
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #4CAF50;")
        self.message_label.show()

    def clear_message(self):
        """Clear the message."""
        self.message_label.setText("")
        self.message_label.hide()

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.reset_btn.setEnabled(not loading)
        self.email_input.setEnabled(not loading)
        self.reset_btn.setText("Sending..." if loading else "Send Reset Link")

    def clear_form(self):
        """Clear all form fields."""
        self.email_input.clear()
        self.clear_message()


class LoginPage(QWidget):
    """
    Login page containing the login form.

    Features:
    - Email/password authentication
    - Remember me option
    - Forgot password link
    - Switch to registration

    Signals:
        login_successful: Emitted when login is successful with user data
        login_requested: Emitted when login is requested (email, password, remember)
        forgot_password_requested: Emitted when forgot password is clicked
        switch_to_register: Emitted when user wants to switch to register
    """

    login_successful = pyqtSignal(dict)  # Emitted with user data on successful login
    login_requested = pyqtSignal(str, str, bool)
    forgot_password_requested = pyqtSignal()
    switch_to_register = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("loginPage")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the login page UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Center the form
        layout.addStretch()

        # Login form
        self.login_form = LoginForm()
        self.login_form.login_requested.connect(self.login_requested.emit)
        self.login_form.forgot_password_requested.connect(self.forgot_password_requested.emit)
        self.login_form.switch_to_register.connect(self.switch_to_register.emit)
        layout.addWidget(self.login_form)

        layout.addStretch()

    def show_error(self, message: str):
        """Show an error message."""
        self.login_form.show_error(message)

    def clear_error(self):
        """Clear the error message."""
        self.login_form.clear_error()

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.login_form.set_loading(loading)

    def clear_form(self):
        """Clear the form."""
        self.login_form.clear_form()

    def on_login_success(self, user_data: dict):
        """Handle successful login."""
        self.set_loading(False)
        self.login_successful.emit(user_data)


class RegisterPage(QWidget):
    """
    Registration page containing the registration form.

    Features:
    - Email, password, confirm password fields
    - First name and last name fields
    - Password strength indicator
    - Terms acceptance
    - Switch to login

    Signals:
        register_successful: Emitted when registration is successful with user data
        register_requested: Emitted when registration is requested
        switch_to_login: Emitted when user wants to switch to login
    """

    register_successful = pyqtSignal(dict)  # Emitted with user data on successful registration
    register_requested = pyqtSignal(str, str, str, str, str, str)  # email, password, confirm, first, last, extra
    switch_to_login = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("registerPage")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the register page UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Center the form
        layout.addStretch()

        # Register form
        self.register_form = RegisterForm()
        self.register_form.register_requested.connect(self.register_requested.emit)
        self.register_form.switch_to_login.connect(self.switch_to_login.emit)
        layout.addWidget(self.register_form)

        layout.addStretch()

    def show_error(self, message: str):
        """Show an error message."""
        self.register_form.show_error(message)

    def clear_error(self):
        """Clear the error message."""
        self.register_form.clear_error()

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.register_form.set_loading(loading)

    def clear_form(self):
        """Clear the form."""
        self.register_form.clear_form()

    def on_register_success(self, user_data: dict):
        """Handle successful registration."""
        self.set_loading(False)
        self.register_successful.emit(user_data)


class ForgotPasswordPage(QWidget):
    """
    Forgot password page for password reset.

    Features:
    - Email field for password reset
    - Form validation with error messages
    - Loading state during request
    - Success message on email sent
    - Back to login link

    Signals:
        reset_successful: Emitted when reset email is sent successfully
        reset_requested: Emitted when reset is requested (email)
        back_to_login: Emitted when user wants to go back to login
    """

    reset_successful = pyqtSignal()  # Emitted when reset email sent successfully
    reset_requested = pyqtSignal(str)  # email
    back_to_login = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("forgotPasswordPage")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the forgot password page UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Center the form
        layout.addStretch()

        # Forgot password form
        self.forgot_form = ForgotPasswordForm()
        self.forgot_form.reset_requested.connect(self.reset_requested.emit)
        self.forgot_form.back_to_login.connect(self.back_to_login.emit)
        layout.addWidget(self.forgot_form)

        layout.addStretch()

    def show_error(self, message: str):
        """Show an error message."""
        self.forgot_form.show_error(message)

    def show_success(self, message: str):
        """Show a success message."""
        self.forgot_form.show_success(message)

    def clear_message(self):
        """Clear the message."""
        self.forgot_form.clear_message()

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.forgot_form.set_loading(loading)

    def clear_form(self):
        """Clear the form."""
        self.forgot_form.clear_form()

    def on_reset_success(self):
        """Handle successful reset request."""
        self.set_loading(False)
        self.show_success("Password reset instructions have been sent to your email.")
        self.reset_successful.emit()


class AuthContainer(QWidget):
    """
    Container widget managing login, registration, and forgot password pages.

    Provides seamless switching between authentication forms.

    Signals:
        login_successful: Emitted when login is successful
        register_successful: Emitted when registration is successful
        login_requested: Emitted when login is requested
        register_requested: Emitted when registration is requested
        reset_requested: Emitted when password reset is requested
    """

    login_successful = pyqtSignal(dict)
    register_successful = pyqtSignal(dict)
    login_requested = pyqtSignal(str, str, bool)
    register_requested = pyqtSignal(str, str, str, str, str, str)
    reset_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("authContainer")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the auth container UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for login/register/forgot password
        self.stack = QStackedWidget()

        # Login page
        self.login_page = LoginPage()
        self.login_page.login_requested.connect(self.login_requested.emit)
        self.login_page.login_successful.connect(self.login_successful.emit)
        self.login_page.forgot_password_requested.connect(self.show_forgot_password)
        self.login_page.switch_to_register.connect(self.show_register)
        self.stack.addWidget(self.login_page)

        # Register page
        self.register_page = RegisterPage()
        self.register_page.register_requested.connect(self.register_requested.emit)
        self.register_page.register_successful.connect(self.register_successful.emit)
        self.register_page.switch_to_login.connect(self.show_login)
        self.stack.addWidget(self.register_page)

        # Forgot password page
        self.forgot_password_page = ForgotPasswordPage()
        self.forgot_password_page.reset_requested.connect(self.reset_requested.emit)
        self.forgot_password_page.back_to_login.connect(self.show_login)
        self.stack.addWidget(self.forgot_password_page)

        layout.addWidget(self.stack)

    def show_login(self):
        """Show the login page."""
        self.stack.setCurrentWidget(self.login_page)

    def show_register(self):
        """Show the register page."""
        self.stack.setCurrentWidget(self.register_page)

    def show_forgot_password(self):
        """Show the forgot password page."""
        self.stack.setCurrentWidget(self.forgot_password_page)

    def show_login_error(self, message: str):
        """Show error on login page."""
        self.login_page.show_error(message)

    def show_register_error(self, message: str):
        """Show error on register page."""
        self.register_page.show_error(message)

    def show_reset_error(self, message: str):
        """Show error on forgot password page."""
        self.forgot_password_page.show_error(message)

    def show_reset_success(self, message: str):
        """Show success on forgot password page."""
        self.forgot_password_page.show_success(message)

    def set_login_loading(self, loading: bool):
        """Set login loading state."""
        self.login_page.set_loading(loading)

    def set_register_loading(self, loading: bool):
        """Set register loading state."""
        self.register_page.set_loading(loading)

    def set_reset_loading(self, loading: bool):
        """Set forgot password loading state."""
        self.forgot_password_page.set_loading(loading)

    def clear_forms(self):
        """Clear all forms."""
        self.login_page.clear_form()
        self.register_page.clear_form()
        self.forgot_password_page.clear_form()

    def on_login_success(self, user_data: dict):
        """Handle successful login."""
        self.login_page.on_login_success(user_data)

    def on_register_success(self, user_data: dict):
        """Handle successful registration."""
        self.register_page.on_register_success(user_data)

    def on_reset_success(self):
        """Handle successful password reset request."""
        self.forgot_password_page.on_reset_success()
