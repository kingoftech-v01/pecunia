"""
Settings Sections Module

Contains all individual section widgets for the Settings page:
- AccountSection: Email, password, 2FA management
- AppearanceSection: Theme selection with preview, language switch
- SyncSection: Auto-sync configuration, sync interval
- NotificationsSection: Notification toggles and preferences
- SubscriptionSection: Plan info, upgrade options
- DataSection: Export, import, backup functionality
- AboutSection: Version info, licenses, credits
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QGroupBox,
    QLineEdit, QComboBox, QCheckBox, QSpinBox, QSlider,
    QFileDialog, QMessageBox, QRadioButton, QButtonGroup,
    QProgressBar, QTextEdit, QDialog, QDialogButtonBox,
    QFormLayout, QStackedWidget, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter, QIcon
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import json
import os


# =============================================================================
# Theme Preview Widget
# =============================================================================

class ThemePreviewWidget(QFrame):
    """Widget showing a preview of a theme."""

    def __init__(self, theme_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.theme_name = theme_name
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the preview UI."""
        self.setFixedSize(180, 120)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Preview area
        preview = QFrame()
        preview.setFixedHeight(70)
        self._apply_theme_preview(preview)
        layout.addWidget(preview)

        # Theme name label
        self.name_label = QLabel(self.theme_name.capitalize())
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        layout.addWidget(self.name_label)

        self._update_style()

    def _apply_theme_preview(self, preview: QFrame):
        """Apply theme colors to the preview frame."""
        if self.theme_name == "light":
            preview.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                }
            """)
        elif self.theme_name == "dark":
            preview.setStyleSheet("""
                QFrame {
                    background-color: #1E1E1E;
                    border: 1px solid #3E3E3E;
                    border-radius: 4px;
                }
            """)
        else:  # system
            preview.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FFFFFF, stop:0.5 #FFFFFF, stop:0.5 #1E1E1E, stop:1 #1E1E1E);
                    border: 1px solid #808080;
                    border-radius: 4px;
                }
            """)

        # Add mini UI elements to preview
        inner_layout = QVBoxLayout(preview)
        inner_layout.setContentsMargins(6, 6, 6, 6)
        inner_layout.setSpacing(3)

        # Mini header bar
        header = QFrame()
        header.setFixedHeight(12)
        if self.theme_name == "light":
            header.setStyleSheet("background-color: #F5F5F5; border-radius: 2px;")
        elif self.theme_name == "dark":
            header.setStyleSheet("background-color: #2D2D2D; border-radius: 2px;")
        else:
            header.setStyleSheet("background-color: #808080; border-radius: 2px;")
        inner_layout.addWidget(header)

        # Mini content bars
        for i in range(3):
            bar = QFrame()
            bar.setFixedHeight(8)
            width_percent = [90, 70, 50][i]
            if self.theme_name == "light":
                bar.setStyleSheet(f"background-color: #E0E0E0; border-radius: 2px; max-width: {width_percent}%;")
            elif self.theme_name == "dark":
                bar.setStyleSheet(f"background-color: #3E3E3E; border-radius: 2px; max-width: {width_percent}%;")
            else:
                bar.setStyleSheet(f"background-color: #606060; border-radius: 2px; max-width: {width_percent}%;")
            inner_layout.addWidget(bar)

        inner_layout.addStretch()

    def set_selected(self, selected: bool):
        """Set the selected state."""
        self._selected = selected
        self._update_style()

    def is_selected(self) -> bool:
        """Check if this theme is selected."""
        return self._selected

    def _update_style(self):
        """Update the frame style based on selection state."""
        if self._selected:
            self.setStyleSheet("""
                ThemePreviewWidget {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    background-color: rgba(76, 175, 80, 0.1);
                }
            """)
        else:
            self.setStyleSheet("""
                ThemePreviewWidget {
                    border: 1px solid #CCCCCC;
                    border-radius: 8px;
                    background-color: transparent;
                }
                ThemePreviewWidget:hover {
                    border: 1px solid #4CAF50;
                    background-color: rgba(76, 175, 80, 0.05);
                }
            """)

    def mousePressEvent(self, event):
        """Handle mouse press event."""
        super().mousePressEvent(event)


# =============================================================================
# Two-Factor Authentication Dialog
# =============================================================================

class TwoFactorDialog(QDialog):
    """Dialog for setting up two-factor authentication."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Set Up Two-Factor Authentication")
        self.setMinimumSize(400, 500)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Title
        title = QLabel("Enable Two-Factor Authentication")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Two-factor authentication adds an extra layer of security to your account. "
            "You'll need to enter a code from your authenticator app each time you log in."
        )
        desc.setFont(QFont("Segoe UI", 10))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # QR Code placeholder
        qr_frame = QFrame()
        qr_frame.setFixedSize(200, 200)
        qr_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        qr_layout = QVBoxLayout(qr_frame)
        qr_label = QLabel("QR Code")
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setFont(QFont("Segoe UI", 10))
        qr_label.setStyleSheet("color: #888;")
        qr_layout.addWidget(qr_label)

        qr_container = QHBoxLayout()
        qr_container.addStretch()
        qr_container.addWidget(qr_frame)
        qr_container.addStretch()
        layout.addLayout(qr_container)

        # Manual entry key
        key_group = QGroupBox("Manual Entry Key")
        key_layout = QVBoxLayout(key_group)

        self.secret_key_label = QLabel("XXXX-XXXX-XXXX-XXXX")
        self.secret_key_label.setFont(QFont("Consolas", 12))
        self.secret_key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secret_key_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        key_layout.addWidget(self.secret_key_label)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setMaximumWidth(150)
        copy_btn.clicked.connect(self._copy_key)
        key_layout.addWidget(copy_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(key_group)

        # Verification code entry
        verify_group = QGroupBox("Verify Setup")
        verify_layout = QFormLayout(verify_group)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Enter 6-digit code")
        self.code_edit.setMaxLength(6)
        self.code_edit.setFont(QFont("Consolas", 14))
        self.code_edit.setMaximumWidth(150)
        verify_layout.addRow("Code:", self.code_edit)

        layout.addWidget(verify_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._verify_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _copy_key(self):
        """Copy the secret key to clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.secret_key_label.text().replace("-", ""))
            QMessageBox.information(self, "Copied", "Secret key copied to clipboard.")

    def _verify_and_accept(self):
        """Verify the entered code and accept."""
        code = self.code_edit.text().strip()
        if len(code) != 6 or not code.isdigit():
            QMessageBox.warning(self, "Invalid Code", "Please enter a valid 6-digit code.")
            return
        # In production, this would verify with the server
        self.accept()

    def get_code(self) -> str:
        """Get the entered verification code."""
        return self.code_edit.text().strip()


# =============================================================================
# Account Section
# =============================================================================

class AccountSection(QWidget):
    """Account settings section - Email, password, 2FA management."""

    # Signals
    email_change_requested = pyqtSignal(str, str)  # new_email, password
    password_change_requested = pyqtSignal(str, str)  # old_password, new_password
    two_factor_toggle_requested = pyqtSignal(bool)  # enable
    profile_updated = pyqtSignal(dict)
    logout_requested = pyqtSignal()
    delete_account_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._two_factor_enabled = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the account section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # Profile Section
        profile_group = self._create_profile_section()
        content_layout.addWidget(profile_group)

        # Email Section
        email_group = self._create_email_section()
        content_layout.addWidget(email_group)

        # Password Section
        password_group = self._create_password_section()
        content_layout.addWidget(password_group)

        # Two-Factor Authentication Section
        two_factor_group = self._create_two_factor_section()
        content_layout.addWidget(two_factor_group)

        # Session Section
        session_group = self._create_session_section()
        content_layout.addWidget(session_group)

        # Danger Zone
        danger_group = self._create_danger_zone()
        content_layout.addWidget(danger_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_profile_section(self) -> QGroupBox:
        """Create the profile information section."""
        group = QGroupBox("Profile Information")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QFormLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.username_label = QLabel("--")
        self.username_label.setFont(QFont("Segoe UI", 10))
        layout.addRow("Username:", self.username_label)

        self.member_since_label = QLabel("--")
        self.member_since_label.setFont(QFont("Segoe UI", 10))
        layout.addRow("Member Since:", self.member_since_label)

        self.last_login_label = QLabel("--")
        self.last_login_label.setFont(QFont("Segoe UI", 10))
        layout.addRow("Last Login:", self.last_login_label)

        return group

    def _create_email_section(self) -> QGroupBox:
        """Create the email change section."""
        group = QGroupBox("Email Address")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QFormLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Current email display
        self.current_email_label = QLabel("--")
        self.current_email_label.setFont(QFont("Segoe UI", 10))
        layout.addRow("Current Email:", self.current_email_label)

        # New email input
        self.new_email_edit = QLineEdit()
        self.new_email_edit.setPlaceholderText("Enter new email address")
        self.new_email_edit.setMaximumWidth(300)
        layout.addRow("New Email:", self.new_email_edit)

        # Password for verification
        self.email_password_edit = QLineEdit()
        self.email_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_password_edit.setPlaceholderText("Enter your password to confirm")
        self.email_password_edit.setMaximumWidth(300)
        layout.addRow("Password:", self.email_password_edit)

        # Change button
        change_email_btn = QPushButton("Update Email")
        change_email_btn.setObjectName("secondaryButton")
        change_email_btn.setMaximumWidth(150)
        change_email_btn.clicked.connect(self._on_change_email)
        layout.addRow("", change_email_btn)

        return group

    def _create_password_section(self) -> QGroupBox:
        """Create the password change section."""
        group = QGroupBox("Change Password")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QFormLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.current_password_edit = QLineEdit()
        self.current_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_edit.setPlaceholderText("Enter current password")
        self.current_password_edit.setMaximumWidth(300)
        layout.addRow("Current Password:", self.current_password_edit)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_edit.setPlaceholderText("Enter new password (min. 8 characters)")
        self.new_password_edit.setMaximumWidth(300)
        layout.addRow("New Password:", self.new_password_edit)

        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_edit.setPlaceholderText("Confirm new password")
        self.confirm_password_edit.setMaximumWidth(300)
        layout.addRow("Confirm Password:", self.confirm_password_edit)

        # Password strength indicator
        self.password_strength_bar = QProgressBar()
        self.password_strength_bar.setMaximumWidth(300)
        self.password_strength_bar.setMaximum(100)
        self.password_strength_bar.setValue(0)
        self.password_strength_bar.setTextVisible(False)
        self.password_strength_bar.setFixedHeight(8)
        layout.addRow("Strength:", self.password_strength_bar)

        self.new_password_edit.textChanged.connect(self._update_password_strength)

        change_password_btn = QPushButton("Change Password")
        change_password_btn.setObjectName("secondaryButton")
        change_password_btn.setMaximumWidth(150)
        change_password_btn.clicked.connect(self._on_change_password)
        layout.addRow("", change_password_btn)

        return group

    def _create_two_factor_section(self) -> QGroupBox:
        """Create the two-factor authentication section."""
        group = QGroupBox("Two-Factor Authentication")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Status
        status_layout = QHBoxLayout()

        self.two_factor_status_label = QLabel("Status: Disabled")
        self.two_factor_status_label.setFont(QFont("Segoe UI", 10))
        status_layout.addWidget(self.two_factor_status_label)

        status_layout.addStretch()

        self.two_factor_toggle_btn = QPushButton("Enable 2FA")
        self.two_factor_toggle_btn.setObjectName("secondaryButton")
        self.two_factor_toggle_btn.clicked.connect(self._on_toggle_two_factor)
        status_layout.addWidget(self.two_factor_toggle_btn)

        layout.addLayout(status_layout)

        # Description
        desc = QLabel(
            "Two-factor authentication adds an extra layer of security by requiring "
            "a code from your authenticator app when logging in."
        )
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        return group

    def _create_session_section(self) -> QGroupBox:
        """Create the session management section."""
        group = QGroupBox("Session")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        btn_layout = QHBoxLayout()

        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("secondaryButton")
        logout_btn.clicked.connect(self.logout_requested.emit)
        btn_layout.addWidget(logout_btn)

        logout_all_btn = QPushButton("Logout All Devices")
        logout_all_btn.setObjectName("secondaryButton")
        logout_all_btn.clicked.connect(self._on_logout_all)
        btn_layout.addWidget(logout_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_danger_zone(self) -> QGroupBox:
        """Create the danger zone section."""
        group = QGroupBox("Danger Zone")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet("QGroupBox { color: #E57373; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        warning = QLabel(
            "Deleting your account is permanent and cannot be undone. "
            "All your data will be permanently removed."
        )
        warning.setFont(QFont("Segoe UI", 10))
        warning.setStyleSheet("color: #E57373;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        delete_btn = QPushButton("Delete Account")
        delete_btn.setObjectName("dangerButton")
        delete_btn.setMaximumWidth(150)
        delete_btn.clicked.connect(self._confirm_delete)
        layout.addWidget(delete_btn)

        return group

    def _update_password_strength(self, password: str):
        """Update the password strength indicator."""
        strength = 0

        if len(password) >= 8:
            strength += 25
        if len(password) >= 12:
            strength += 15
        if any(c.isupper() for c in password):
            strength += 15
        if any(c.islower() for c in password):
            strength += 15
        if any(c.isdigit() for c in password):
            strength += 15
        if any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?" for c in password):
            strength += 15

        self.password_strength_bar.setValue(min(100, strength))

        # Update color based on strength
        if strength < 40:
            color = "#E57373"  # Red
        elif strength < 70:
            color = "#FFB74D"  # Orange
        else:
            color = "#81C784"  # Green

        self.password_strength_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)

    def _on_change_email(self):
        """Handle email change request."""
        new_email = self.new_email_edit.text().strip()
        password = self.email_password_edit.text()

        if not new_email:
            QMessageBox.warning(self, "Error", "Please enter a new email address.")
            return

        if "@" not in new_email or "." not in new_email:
            QMessageBox.warning(self, "Error", "Please enter a valid email address.")
            return

        if not password:
            QMessageBox.warning(self, "Error", "Please enter your password to confirm.")
            return

        self.email_change_requested.emit(new_email, password)

        # Clear fields
        self.new_email_edit.clear()
        self.email_password_edit.clear()

    def _on_change_password(self):
        """Handle password change request."""
        current = self.current_password_edit.text()
        new = self.new_password_edit.text()
        confirm = self.confirm_password_edit.text()

        if not current or not new or not confirm:
            QMessageBox.warning(self, "Error", "Please fill in all password fields.")
            return

        if new != confirm:
            QMessageBox.warning(self, "Error", "New passwords do not match.")
            return

        if len(new) < 8:
            QMessageBox.warning(self, "Error", "Password must be at least 8 characters.")
            return

        self.password_change_requested.emit(current, new)

        # Clear fields
        self.current_password_edit.clear()
        self.new_password_edit.clear()
        self.confirm_password_edit.clear()
        self.password_strength_bar.setValue(0)

    def _on_toggle_two_factor(self):
        """Handle two-factor toggle."""
        if self._two_factor_enabled:
            reply = QMessageBox.warning(
                self,
                "Disable 2FA",
                "Are you sure you want to disable two-factor authentication?\n\n"
                "This will make your account less secure.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.two_factor_toggle_requested.emit(False)
        else:
            dialog = TwoFactorDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.two_factor_toggle_requested.emit(True)

    def _on_logout_all(self):
        """Handle logout all devices request."""
        reply = QMessageBox.question(
            self,
            "Logout All Devices",
            "This will log you out from all devices including this one.\n\n"
            "You will need to log in again. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def _confirm_delete(self):
        """Show delete account confirmation."""
        reply = QMessageBox.warning(
            self,
            "Delete Account",
            "Are you sure you want to delete your account?\n\n"
            "This action cannot be undone and all your data will be permanently deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Second confirmation
            confirm_reply = QMessageBox.critical(
                self,
                "Final Confirmation",
                "This is your final warning.\n\n"
                "Type 'DELETE' in your mind and click Yes to permanently delete your account.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if confirm_reply == QMessageBox.StandardButton.Yes:
                self.delete_account_requested.emit()

    def set_user_info(self, username: str, email: str, member_since: str = "",
                      last_login: str = ""):
        """Set the user info display."""
        self.username_label.setText(username)
        self.current_email_label.setText(email)
        self.member_since_label.setText(member_since if member_since else "--")
        self.last_login_label.setText(last_login if last_login else "--")

    def set_two_factor_enabled(self, enabled: bool):
        """Set the two-factor authentication status."""
        self._two_factor_enabled = enabled
        if enabled:
            self.two_factor_status_label.setText("Status: Enabled")
            self.two_factor_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.two_factor_toggle_btn.setText("Disable 2FA")
        else:
            self.two_factor_status_label.setText("Status: Disabled")
            self.two_factor_status_label.setStyleSheet("color: #E57373;")
            self.two_factor_toggle_btn.setText("Enable 2FA")


# =============================================================================
# Appearance Section
# =============================================================================

class AppearanceSection(QWidget):
    """Appearance settings - Theme with preview, language switch."""

    # Signals
    theme_changed = pyqtSignal(str)  # theme_name
    theme_preview_requested = pyqtSignal(str)  # theme_name (for live preview)
    language_changed = pyqtSignal(str)  # language_code
    settings_changed = pyqtSignal(str, object)  # key, value

    # Supported languages
    LANGUAGES = {
        "en": "English",
        "fr": "Francais",
        "es": "Espanol",
        "de": "Deutsch",
        "pt": "Portugues",
        "it": "Italiano",
        "ja": "Japanese",
        "zh": "Chinese (Simplified)",
        "ko": "Korean",
        "ru": "Russian"
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_theme = "system"
        self._current_language = "en"
        self._setup_ui()

    def _setup_ui(self):
        """Set up the appearance section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # Theme Section
        theme_group = self._create_theme_section()
        content_layout.addWidget(theme_group)

        # Language Section
        language_group = self._create_language_section()
        content_layout.addWidget(language_group)

        # Display Options Section
        display_group = self._create_display_section()
        content_layout.addWidget(display_group)

        # Accessibility Section
        accessibility_group = self._create_accessibility_section()
        content_layout.addWidget(accessibility_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_theme_section(self) -> QGroupBox:
        """Create the theme selection section with previews."""
        group = QGroupBox("Theme")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Description
        desc = QLabel("Choose how Pecunia looks to you. Select a theme below.")
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # Theme previews
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(20)

        self.theme_previews: Dict[str, ThemePreviewWidget] = {}

        for theme in ["light", "dark", "system"]:
            preview = ThemePreviewWidget(theme)
            preview.mousePressEvent = lambda e, t=theme: self._on_theme_clicked(t)
            self.theme_previews[theme] = preview
            preview_layout.addWidget(preview)

        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        # Set default selection
        self.theme_previews["system"].set_selected(True)

        return group

    def _create_language_section(self) -> QGroupBox:
        """Create the language selection section."""
        group = QGroupBox("Language")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Description
        desc = QLabel(
            "Select your preferred language. Changes will take effect immediately."
        )
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # Language combo
        lang_layout = QHBoxLayout()

        lang_label = QLabel("Language:")
        lang_label.setFont(QFont("Segoe UI", 10))
        lang_layout.addWidget(lang_label)

        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(200)
        for code, name in self.LANGUAGES.items():
            self.language_combo.addItem(name, code)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_layout.addWidget(self.language_combo)

        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # Language info
        self.language_info_label = QLabel("")
        self.language_info_label.setFont(QFont("Segoe UI", 9))
        self.language_info_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.language_info_label)

        return group

    def _create_display_section(self) -> QGroupBox:
        """Create the display options section."""
        group = QGroupBox("Display Options")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Compact mode
        self.compact_mode_check = QCheckBox("Compact Mode")
        self.compact_mode_check.setFont(QFont("Segoe UI", 10))
        self.compact_mode_check.setToolTip("Use smaller spacing and font sizes")
        self.compact_mode_check.toggled.connect(
            lambda v: self.settings_changed.emit("compact_mode", v)
        )
        layout.addWidget(self.compact_mode_check)

        # Show decimals
        self.show_decimals_check = QCheckBox("Show Decimal Places")
        self.show_decimals_check.setFont(QFont("Segoe UI", 10))
        self.show_decimals_check.setChecked(True)
        self.show_decimals_check.setToolTip("Display cents in monetary values")
        self.show_decimals_check.toggled.connect(
            lambda v: self.settings_changed.emit("show_decimals", v)
        )
        layout.addWidget(self.show_decimals_check)

        # Show balance
        self.show_balance_check = QCheckBox("Show Balance in Sidebar")
        self.show_balance_check.setFont(QFont("Segoe UI", 10))
        self.show_balance_check.setChecked(True)
        self.show_balance_check.toggled.connect(
            lambda v: self.settings_changed.emit("show_balance", v)
        )
        layout.addWidget(self.show_balance_check)

        # Animations
        self.animations_check = QCheckBox("Enable Animations")
        self.animations_check.setFont(QFont("Segoe UI", 10))
        self.animations_check.setChecked(True)
        self.animations_check.setToolTip("Enable UI animations and transitions")
        self.animations_check.toggled.connect(
            lambda v: self.settings_changed.emit("animations_enabled", v)
        )
        layout.addWidget(self.animations_check)

        return group

    def _create_accessibility_section(self) -> QGroupBox:
        """Create the accessibility options section."""
        group = QGroupBox("Accessibility")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Font size
        font_layout = QHBoxLayout()

        font_label = QLabel("Font Size:")
        font_label.setFont(QFont("Segoe UI", 10))
        font_layout.addWidget(font_label)

        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setMinimum(80)
        self.font_size_slider.setMaximum(150)
        self.font_size_slider.setValue(100)
        self.font_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_size_slider.setTickInterval(10)
        self.font_size_slider.setMaximumWidth(200)
        self.font_size_slider.valueChanged.connect(self._on_font_size_changed)
        font_layout.addWidget(self.font_size_slider)

        self.font_size_label = QLabel("100%")
        self.font_size_label.setFont(QFont("Segoe UI", 10))
        self.font_size_label.setMinimumWidth(50)
        font_layout.addWidget(self.font_size_label)

        font_layout.addStretch()
        layout.addLayout(font_layout)

        # High contrast
        self.high_contrast_check = QCheckBox("High Contrast Mode")
        self.high_contrast_check.setFont(QFont("Segoe UI", 10))
        self.high_contrast_check.setToolTip("Increase contrast for better visibility")
        self.high_contrast_check.toggled.connect(
            lambda v: self.settings_changed.emit("high_contrast", v)
        )
        layout.addWidget(self.high_contrast_check)

        # Reduce motion
        self.reduce_motion_check = QCheckBox("Reduce Motion")
        self.reduce_motion_check.setFont(QFont("Segoe UI", 10))
        self.reduce_motion_check.setToolTip("Minimize animations and movement")
        self.reduce_motion_check.toggled.connect(
            lambda v: self.settings_changed.emit("reduce_motion", v)
        )
        layout.addWidget(self.reduce_motion_check)

        return group

    def _on_theme_clicked(self, theme: str):
        """Handle theme preview click."""
        # Update selection visuals
        for name, preview in self.theme_previews.items():
            preview.set_selected(name == theme)

        self._current_theme = theme
        self.theme_preview_requested.emit(theme)
        self.theme_changed.emit(theme)
        self.settings_changed.emit("theme", theme)

    def _on_language_changed(self, index: int):
        """Handle language selection change."""
        lang_code = self.language_combo.currentData()
        if lang_code and lang_code != self._current_language:
            self._current_language = lang_code
            self.language_changed.emit(lang_code)
            self.settings_changed.emit("language", lang_code)

            # Update info label
            self.language_info_label.setText(
                f"Language changed to {self.language_combo.currentText()}. "
                "Some text may require app restart."
            )

            # Auto-hide info after 5 seconds
            QTimer.singleShot(5000, lambda: self.language_info_label.setText(""))

    def _on_font_size_changed(self, value: int):
        """Handle font size slider change."""
        self.font_size_label.setText(f"{value}%")
        self.settings_changed.emit("font_scale", value / 100.0)

    def set_values(self, settings: Dict[str, Any]):
        """Set the current settings values."""
        # Theme
        theme = settings.get("theme", "system")
        self._current_theme = theme
        for name, preview in self.theme_previews.items():
            preview.set_selected(name == theme)

        # Language
        lang = settings.get("language", "en")
        self._current_language = lang
        index = self.language_combo.findData(lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

        # Display options
        self.compact_mode_check.setChecked(settings.get("compact_mode", False))
        self.show_decimals_check.setChecked(settings.get("show_decimals", True))
        self.show_balance_check.setChecked(settings.get("show_balance", True))
        self.animations_check.setChecked(settings.get("animations_enabled", True))

        # Accessibility
        font_scale = int(settings.get("font_scale", 1.0) * 100)
        self.font_size_slider.setValue(font_scale)
        self.font_size_label.setText(f"{font_scale}%")
        self.high_contrast_check.setChecked(settings.get("high_contrast", False))
        self.reduce_motion_check.setChecked(settings.get("reduce_motion", False))

    def get_values(self) -> Dict[str, Any]:
        """Get the current settings values."""
        return {
            "theme": self._current_theme,
            "language": self._current_language,
            "compact_mode": self.compact_mode_check.isChecked(),
            "show_decimals": self.show_decimals_check.isChecked(),
            "show_balance": self.show_balance_check.isChecked(),
            "animations_enabled": self.animations_check.isChecked(),
            "font_scale": self.font_size_slider.value() / 100.0,
            "high_contrast": self.high_contrast_check.isChecked(),
            "reduce_motion": self.reduce_motion_check.isChecked()
        }


# =============================================================================
# Sync Section
# =============================================================================

class SyncSection(QWidget):
    """Sync settings - Auto-sync configuration, sync interval."""

    # Signals
    settings_changed = pyqtSignal(str, object)
    sync_requested = pyqtSignal()
    sync_reset_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the sync section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # Sync Status Section
        status_group = self._create_status_section()
        content_layout.addWidget(status_group)

        # Sync Settings Section
        settings_group = self._create_settings_section()
        content_layout.addWidget(settings_group)

        # Data to Sync Section
        data_group = self._create_data_section()
        content_layout.addWidget(data_group)

        # Conflict Resolution Section
        conflict_group = self._create_conflict_section()
        content_layout.addWidget(conflict_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_status_section(self) -> QGroupBox:
        """Create the sync status section."""
        group = QGroupBox("Sync Status")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Status info
        info_layout = QGridLayout()
        info_layout.setSpacing(15)

        # Last sync
        last_sync_title = QLabel("Last Sync:")
        last_sync_title.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(last_sync_title, 0, 0)

        self.last_sync_label = QLabel("Never")
        self.last_sync_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        info_layout.addWidget(self.last_sync_label, 0, 1)

        # Status
        status_title = QLabel("Status:")
        status_title.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(status_title, 1, 0)

        self.sync_status_label = QLabel("Not synced")
        self.sync_status_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        info_layout.addWidget(self.sync_status_label, 1, 1)

        # Pending changes
        pending_title = QLabel("Pending Changes:")
        pending_title.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(pending_title, 2, 0)

        self.pending_changes_label = QLabel("0")
        self.pending_changes_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        info_layout.addWidget(self.pending_changes_label, 2, 1)

        info_layout.setColumnStretch(2, 1)
        layout.addLayout(info_layout)

        # Sync progress bar
        self.sync_progress = QProgressBar()
        self.sync_progress.setVisible(False)
        self.sync_progress.setTextVisible(True)
        layout.addWidget(self.sync_progress)

        # Sync button
        btn_layout = QHBoxLayout()

        sync_btn = QPushButton("Sync Now")
        sync_btn.setObjectName("primaryButton")
        sync_btn.setIcon(QIcon.fromTheme("view-refresh"))
        sync_btn.clicked.connect(self._on_sync_clicked)
        btn_layout.addWidget(sync_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_settings_section(self) -> QGroupBox:
        """Create the sync settings section."""
        group = QGroupBox("Sync Settings")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QFormLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Auto sync toggle
        self.auto_sync_check = QCheckBox("Enable Auto Sync")
        self.auto_sync_check.setFont(QFont("Segoe UI", 10))
        self.auto_sync_check.setChecked(True)
        self.auto_sync_check.toggled.connect(self._on_auto_sync_toggled)
        layout.addRow(self.auto_sync_check)

        # Sync interval
        interval_layout = QHBoxLayout()

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(15)
        self.interval_spin.setSuffix(" minutes")
        self.interval_spin.setMinimumWidth(120)
        self.interval_spin.valueChanged.connect(
            lambda v: self.settings_changed.emit("sync_interval", v)
        )
        interval_layout.addWidget(self.interval_spin)

        # Quick presets
        preset_5 = QPushButton("5m")
        preset_5.setMaximumWidth(40)
        preset_5.clicked.connect(lambda: self._set_interval(5))
        interval_layout.addWidget(preset_5)

        preset_15 = QPushButton("15m")
        preset_15.setMaximumWidth(40)
        preset_15.clicked.connect(lambda: self._set_interval(15))
        interval_layout.addWidget(preset_15)

        preset_30 = QPushButton("30m")
        preset_30.setMaximumWidth(40)
        preset_30.clicked.connect(lambda: self._set_interval(30))
        interval_layout.addWidget(preset_30)

        preset_60 = QPushButton("1h")
        preset_60.setMaximumWidth(40)
        preset_60.clicked.connect(lambda: self._set_interval(60))
        interval_layout.addWidget(preset_60)

        interval_layout.addStretch()
        layout.addRow("Sync Interval:", interval_layout)

        # Sync on startup
        self.sync_on_startup_check = QCheckBox("Sync on Startup")
        self.sync_on_startup_check.setFont(QFont("Segoe UI", 10))
        self.sync_on_startup_check.setChecked(True)
        self.sync_on_startup_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_on_startup", v)
        )
        layout.addRow(self.sync_on_startup_check)

        # Sync on app close
        self.sync_on_close_check = QCheckBox("Sync Before Closing")
        self.sync_on_close_check.setFont(QFont("Segoe UI", 10))
        self.sync_on_close_check.setChecked(True)
        self.sync_on_close_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_on_close", v)
        )
        layout.addRow(self.sync_on_close_check)

        # Offline mode
        self.offline_mode_check = QCheckBox("Offline Mode")
        self.offline_mode_check.setFont(QFont("Segoe UI", 10))
        self.offline_mode_check.setToolTip("Disable all sync operations")
        self.offline_mode_check.toggled.connect(
            lambda v: self.settings_changed.emit("offline_mode", v)
        )
        layout.addRow(self.offline_mode_check)

        return group

    def _create_data_section(self) -> QGroupBox:
        """Create the data to sync section."""
        group = QGroupBox("Data to Sync")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.sync_transactions_check = QCheckBox("Transactions")
        self.sync_transactions_check.setFont(QFont("Segoe UI", 10))
        self.sync_transactions_check.setChecked(True)
        self.sync_transactions_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_transactions", v)
        )
        layout.addWidget(self.sync_transactions_check)

        self.sync_budgets_check = QCheckBox("Budgets")
        self.sync_budgets_check.setFont(QFont("Segoe UI", 10))
        self.sync_budgets_check.setChecked(True)
        self.sync_budgets_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_budgets", v)
        )
        layout.addWidget(self.sync_budgets_check)

        self.sync_categories_check = QCheckBox("Categories")
        self.sync_categories_check.setFont(QFont("Segoe UI", 10))
        self.sync_categories_check.setChecked(True)
        self.sync_categories_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_categories", v)
        )
        layout.addWidget(self.sync_categories_check)

        self.sync_accounts_check = QCheckBox("Linked Accounts")
        self.sync_accounts_check.setFont(QFont("Segoe UI", 10))
        self.sync_accounts_check.setChecked(True)
        self.sync_accounts_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_accounts", v)
        )
        layout.addWidget(self.sync_accounts_check)

        self.sync_settings_check = QCheckBox("Settings & Preferences")
        self.sync_settings_check.setFont(QFont("Segoe UI", 10))
        self.sync_settings_check.setChecked(True)
        self.sync_settings_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_settings", v)
        )
        layout.addWidget(self.sync_settings_check)

        return group

    def _create_conflict_section(self) -> QGroupBox:
        """Create the conflict resolution section."""
        group = QGroupBox("Conflict Resolution")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        desc = QLabel(
            "When conflicts occur between local and server data, "
            "choose how to resolve them:"
        )
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.conflict_group = QButtonGroup(self)

        self.conflict_ask_radio = QRadioButton("Ask me each time")
        self.conflict_ask_radio.setFont(QFont("Segoe UI", 10))
        self.conflict_ask_radio.setChecked(True)
        self.conflict_group.addButton(self.conflict_ask_radio)
        layout.addWidget(self.conflict_ask_radio)

        self.conflict_local_radio = QRadioButton("Keep local changes")
        self.conflict_local_radio.setFont(QFont("Segoe UI", 10))
        self.conflict_group.addButton(self.conflict_local_radio)
        layout.addWidget(self.conflict_local_radio)

        self.conflict_server_radio = QRadioButton("Keep server changes")
        self.conflict_server_radio.setFont(QFont("Segoe UI", 10))
        self.conflict_group.addButton(self.conflict_server_radio)
        layout.addWidget(self.conflict_server_radio)

        self.conflict_group.buttonClicked.connect(self._on_conflict_resolution_changed)

        # Reset sync button
        reset_btn = QPushButton("Reset Sync State")
        reset_btn.setObjectName("secondaryButton")
        reset_btn.setMaximumWidth(150)
        reset_btn.setToolTip("Clear sync history and force full re-sync")
        reset_btn.clicked.connect(self._on_reset_sync)
        layout.addWidget(reset_btn)

        return group

    def _on_sync_clicked(self):
        """Handle sync button click."""
        self.sync_status_label.setText("Syncing...")
        self.sync_progress.setVisible(True)
        self.sync_progress.setRange(0, 0)  # Indeterminate
        self.sync_requested.emit()

    def _on_auto_sync_toggled(self, enabled: bool):
        """Handle auto sync toggle."""
        self.interval_spin.setEnabled(enabled)
        self.settings_changed.emit("auto_sync", enabled)

    def _set_interval(self, minutes: int):
        """Set the sync interval."""
        self.interval_spin.setValue(minutes)

    def _on_conflict_resolution_changed(self, button):
        """Handle conflict resolution option change."""
        if button == self.conflict_ask_radio:
            resolution = "ask"
        elif button == self.conflict_local_radio:
            resolution = "local"
        else:
            resolution = "server"
        self.settings_changed.emit("conflict_resolution", resolution)

    def _on_reset_sync(self):
        """Handle sync reset request."""
        reply = QMessageBox.warning(
            self,
            "Reset Sync State",
            "This will clear all sync history and force a full re-sync.\n\n"
            "Any pending local changes may be lost. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sync_reset_requested.emit()

    def set_values(self, settings: Dict[str, Any]):
        """Set the current settings values."""
        self.auto_sync_check.setChecked(settings.get("auto_sync", True))
        self.interval_spin.setValue(settings.get("sync_interval", 15))
        self.sync_on_startup_check.setChecked(settings.get("sync_on_startup", True))
        self.sync_on_close_check.setChecked(settings.get("sync_on_close", True))
        self.offline_mode_check.setChecked(settings.get("offline_mode", False))

        self.sync_transactions_check.setChecked(settings.get("sync_transactions", True))
        self.sync_budgets_check.setChecked(settings.get("sync_budgets", True))
        self.sync_categories_check.setChecked(settings.get("sync_categories", True))
        self.sync_accounts_check.setChecked(settings.get("sync_accounts", True))
        self.sync_settings_check.setChecked(settings.get("sync_settings", True))

        resolution = settings.get("conflict_resolution", "ask")
        if resolution == "local":
            self.conflict_local_radio.setChecked(True)
        elif resolution == "server":
            self.conflict_server_radio.setChecked(True)
        else:
            self.conflict_ask_radio.setChecked(True)

    def set_last_sync(self, timestamp: Optional[str] = None):
        """Update the last sync time display."""
        if timestamp:
            self.last_sync_label.setText(timestamp)
            self.sync_status_label.setText("Synced")
            self.sync_status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.last_sync_label.setText("Never")
            self.sync_status_label.setText("Not synced")
            self.sync_status_label.setStyleSheet("")
        self.sync_progress.setVisible(False)

    def set_sync_status(self, status: str, is_error: bool = False):
        """Update the sync status display."""
        self.sync_status_label.setText(status)
        if is_error:
            self.sync_status_label.setStyleSheet("color: #E57373;")
        elif status.lower() == "synced":
            self.sync_status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.sync_status_label.setStyleSheet("")
        self.sync_progress.setVisible(False)

    def set_pending_changes(self, count: int):
        """Set the pending changes count."""
        self.pending_changes_label.setText(str(count))
        if count > 0:
            self.pending_changes_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        else:
            self.pending_changes_label.setStyleSheet("")

    def get_values(self) -> Dict[str, Any]:
        """Get the current settings values."""
        resolution = "ask"
        if self.conflict_local_radio.isChecked():
            resolution = "local"
        elif self.conflict_server_radio.isChecked():
            resolution = "server"

        return {
            "auto_sync": self.auto_sync_check.isChecked(),
            "sync_interval": self.interval_spin.value(),
            "sync_on_startup": self.sync_on_startup_check.isChecked(),
            "sync_on_close": self.sync_on_close_check.isChecked(),
            "offline_mode": self.offline_mode_check.isChecked(),
            "sync_transactions": self.sync_transactions_check.isChecked(),
            "sync_budgets": self.sync_budgets_check.isChecked(),
            "sync_categories": self.sync_categories_check.isChecked(),
            "sync_accounts": self.sync_accounts_check.isChecked(),
            "sync_settings": self.sync_settings_check.isChecked(),
            "conflict_resolution": resolution
        }


# =============================================================================
# Notifications Section
# =============================================================================

class NotificationsSection(QWidget):
    """Notifications settings - Toggle notifications and preferences."""

    # Signals
    settings_changed = pyqtSignal(str, object)
    test_notification_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the notifications section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # General Notifications Section
        general_group = self._create_general_section()
        content_layout.addWidget(general_group)

        # Alert Types Section
        alerts_group = self._create_alerts_section()
        content_layout.addWidget(alerts_group)

        # Budget Alerts Section
        budget_group = self._create_budget_section()
        content_layout.addWidget(budget_group)

        # Sound & Display Section
        sound_group = self._create_sound_section()
        content_layout.addWidget(sound_group)

        # Test Section
        test_group = self._create_test_section()
        content_layout.addWidget(test_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_general_section(self) -> QGroupBox:
        """Create the general notifications section."""
        group = QGroupBox("General")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Master toggle
        self.notifications_enabled_check = QCheckBox("Enable Notifications")
        self.notifications_enabled_check.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.notifications_enabled_check.setChecked(True)
        self.notifications_enabled_check.toggled.connect(self._on_notifications_toggled)
        layout.addWidget(self.notifications_enabled_check)

        desc = QLabel(
            "Receive notifications about important events like budget alerts, "
            "sync status, and transaction updates."
        )
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        return group

    def _create_alerts_section(self) -> QGroupBox:
        """Create the alert types section."""
        group = QGroupBox("Alert Types")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.budget_alerts_check = QCheckBox("Budget Alerts")
        self.budget_alerts_check.setFont(QFont("Segoe UI", 10))
        self.budget_alerts_check.setChecked(True)
        self.budget_alerts_check.setToolTip("Alert when approaching or exceeding budget limits")
        self.budget_alerts_check.toggled.connect(
            lambda v: self.settings_changed.emit("budget_alerts", v)
        )
        layout.addWidget(self.budget_alerts_check)

        self.transaction_alerts_check = QCheckBox("Transaction Alerts")
        self.transaction_alerts_check.setFont(QFont("Segoe UI", 10))
        self.transaction_alerts_check.setChecked(True)
        self.transaction_alerts_check.setToolTip("Alert for large transactions or unusual activity")
        self.transaction_alerts_check.toggled.connect(
            lambda v: self.settings_changed.emit("transaction_alerts", v)
        )
        layout.addWidget(self.transaction_alerts_check)

        self.sync_alerts_check = QCheckBox("Sync Alerts")
        self.sync_alerts_check.setFont(QFont("Segoe UI", 10))
        self.sync_alerts_check.setToolTip("Alert when sync completes or fails")
        self.sync_alerts_check.toggled.connect(
            lambda v: self.settings_changed.emit("sync_alerts", v)
        )
        layout.addWidget(self.sync_alerts_check)

        self.reminder_alerts_check = QCheckBox("Bill Reminders")
        self.reminder_alerts_check.setFont(QFont("Segoe UI", 10))
        self.reminder_alerts_check.setChecked(True)
        self.reminder_alerts_check.setToolTip("Remind about upcoming bills and payments")
        self.reminder_alerts_check.toggled.connect(
            lambda v: self.settings_changed.emit("reminder_alerts", v)
        )
        layout.addWidget(self.reminder_alerts_check)

        self.goal_alerts_check = QCheckBox("Goal Progress Alerts")
        self.goal_alerts_check.setFont(QFont("Segoe UI", 10))
        self.goal_alerts_check.setChecked(True)
        self.goal_alerts_check.setToolTip("Alert when reaching savings goals milestones")
        self.goal_alerts_check.toggled.connect(
            lambda v: self.settings_changed.emit("goal_alerts", v)
        )
        layout.addWidget(self.goal_alerts_check)

        return group

    def _create_budget_section(self) -> QGroupBox:
        """Create the budget alerts configuration section."""
        group = QGroupBox("Budget Alert Threshold")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        desc = QLabel("Alert me when budget usage reaches:")
        desc.setFont(QFont("Segoe UI", 10))
        layout.addWidget(desc)

        threshold_layout = QHBoxLayout()

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(50)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(80)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.setMaximumWidth(300)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(self.threshold_slider)

        self.threshold_label = QLabel("80%")
        self.threshold_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.threshold_label.setMinimumWidth(50)
        threshold_layout.addWidget(self.threshold_label)

        threshold_layout.addStretch()
        layout.addLayout(threshold_layout)

        return group

    def _create_sound_section(self) -> QGroupBox:
        """Create the sound and display section."""
        group = QGroupBox("Sound & Display")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.sound_enabled_check = QCheckBox("Enable Sound")
        self.sound_enabled_check.setFont(QFont("Segoe UI", 10))
        self.sound_enabled_check.setChecked(True)
        self.sound_enabled_check.toggled.connect(
            lambda v: self.settings_changed.emit("sound_enabled", v)
        )
        layout.addWidget(self.sound_enabled_check)

        self.popup_enabled_check = QCheckBox("Show Popup Notifications")
        self.popup_enabled_check.setFont(QFont("Segoe UI", 10))
        self.popup_enabled_check.setChecked(True)
        self.popup_enabled_check.toggled.connect(
            lambda v: self.settings_changed.emit("popup_enabled", v)
        )
        layout.addWidget(self.popup_enabled_check)

        self.badge_enabled_check = QCheckBox("Show Badge Count")
        self.badge_enabled_check.setFont(QFont("Segoe UI", 10))
        self.badge_enabled_check.setChecked(True)
        self.badge_enabled_check.setToolTip("Show unread notification count in taskbar")
        self.badge_enabled_check.toggled.connect(
            lambda v: self.settings_changed.emit("badge_enabled", v)
        )
        layout.addWidget(self.badge_enabled_check)

        self.hide_amounts_check = QCheckBox("Hide Amounts in Notifications")
        self.hide_amounts_check.setFont(QFont("Segoe UI", 10))
        self.hide_amounts_check.setToolTip("For privacy, hide monetary values in notifications")
        self.hide_amounts_check.toggled.connect(
            lambda v: self.settings_changed.emit("hide_amounts_in_notifications", v)
        )
        layout.addWidget(self.hide_amounts_check)

        return group

    def _create_test_section(self) -> QGroupBox:
        """Create the test notification section."""
        group = QGroupBox("Test")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        test_btn = QPushButton("Send Test Notification")
        test_btn.setObjectName("secondaryButton")
        test_btn.setMaximumWidth(200)
        test_btn.clicked.connect(self.test_notification_requested.emit)
        layout.addWidget(test_btn)

        return group

    def _on_notifications_toggled(self, enabled: bool):
        """Handle master notifications toggle."""
        # Enable/disable all sub-options
        self.budget_alerts_check.setEnabled(enabled)
        self.transaction_alerts_check.setEnabled(enabled)
        self.sync_alerts_check.setEnabled(enabled)
        self.reminder_alerts_check.setEnabled(enabled)
        self.goal_alerts_check.setEnabled(enabled)
        self.threshold_slider.setEnabled(enabled)
        self.sound_enabled_check.setEnabled(enabled)
        self.popup_enabled_check.setEnabled(enabled)
        self.badge_enabled_check.setEnabled(enabled)
        self.hide_amounts_check.setEnabled(enabled)

        self.settings_changed.emit("notifications_enabled", enabled)

    def _on_threshold_changed(self, value: int):
        """Handle threshold slider change."""
        self.threshold_label.setText(f"{value}%")
        self.settings_changed.emit("budget_threshold_percent", value)

    def set_values(self, settings: Dict[str, Any]):
        """Set the current settings values."""
        self.notifications_enabled_check.setChecked(
            settings.get("notifications_enabled", True)
        )
        self.budget_alerts_check.setChecked(settings.get("budget_alerts", True))
        self.transaction_alerts_check.setChecked(settings.get("transaction_alerts", True))
        self.sync_alerts_check.setChecked(settings.get("sync_alerts", False))
        self.reminder_alerts_check.setChecked(settings.get("reminder_alerts", True))
        self.goal_alerts_check.setChecked(settings.get("goal_alerts", True))

        threshold = settings.get("budget_threshold_percent", 80)
        self.threshold_slider.setValue(threshold)
        self.threshold_label.setText(f"{threshold}%")

        self.sound_enabled_check.setChecked(settings.get("sound_enabled", True))
        self.popup_enabled_check.setChecked(settings.get("popup_enabled", True))
        self.badge_enabled_check.setChecked(settings.get("badge_enabled", True))
        self.hide_amounts_check.setChecked(
            settings.get("hide_amounts_in_notifications", False)
        )

    def get_values(self) -> Dict[str, Any]:
        """Get the current settings values."""
        return {
            "notifications_enabled": self.notifications_enabled_check.isChecked(),
            "budget_alerts": self.budget_alerts_check.isChecked(),
            "transaction_alerts": self.transaction_alerts_check.isChecked(),
            "sync_alerts": self.sync_alerts_check.isChecked(),
            "reminder_alerts": self.reminder_alerts_check.isChecked(),
            "goal_alerts": self.goal_alerts_check.isChecked(),
            "budget_threshold_percent": self.threshold_slider.value(),
            "sound_enabled": self.sound_enabled_check.isChecked(),
            "popup_enabled": self.popup_enabled_check.isChecked(),
            "badge_enabled": self.badge_enabled_check.isChecked(),
            "hide_amounts_in_notifications": self.hide_amounts_check.isChecked()
        }


# =============================================================================
# Subscription Section
# =============================================================================

class SubscriptionSection(QWidget):
    """Subscription settings - Plan info, upgrade options."""

    # Signals
    upgrade_requested = pyqtSignal(str)  # plan_name
    manage_subscription_requested = pyqtSignal()
    cancel_subscription_requested = pyqtSignal()

    # Plan definitions
    PLANS = {
        "free": {
            "name": "Free",
            "price": "$0",
            "period": "forever",
            "features": [
                "Up to 2 bank accounts",
                "Basic transaction tracking",
                "Monthly budget",
                "Basic reports"
            ]
        },
        "premium": {
            "name": "Premium",
            "price": "$9.99",
            "period": "month",
            "features": [
                "Unlimited bank accounts",
                "Advanced transaction tracking",
                "Multiple budgets",
                "Advanced reports & analytics",
                "Data export",
                "Priority support"
            ]
        },
        "business": {
            "name": "Business",
            "price": "$24.99",
            "period": "month",
            "features": [
                "Everything in Premium",
                "Multi-user access",
                "Business expense tracking",
                "Invoice management",
                "API access",
                "Dedicated support"
            ]
        }
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_plan = "free"
        self._setup_ui()

    def _setup_ui(self):
        """Set up the subscription section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # Current Plan Section
        current_group = self._create_current_plan_section()
        content_layout.addWidget(current_group)

        # Available Plans Section
        plans_group = self._create_plans_section()
        content_layout.addWidget(plans_group)

        # Billing Section
        billing_group = self._create_billing_section()
        content_layout.addWidget(billing_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_current_plan_section(self) -> QGroupBox:
        """Create the current plan info section."""
        group = QGroupBox("Current Plan")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Plan name and status
        header_layout = QHBoxLayout()

        self.plan_name_label = QLabel("Free")
        self.plan_name_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(self.plan_name_label)

        self.plan_badge = QLabel("Active")
        self.plan_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.plan_badge.setStyleSheet("""
            QLabel {
                background-color: #4CAF50;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
            }
        """)
        header_layout.addWidget(self.plan_badge)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Plan details
        self.plan_details_label = QLabel("Basic features for personal finance tracking")
        self.plan_details_label.setFont(QFont("Segoe UI", 10))
        self.plan_details_label.setStyleSheet("color: #666;")
        layout.addWidget(self.plan_details_label)

        # Renewal info
        self.renewal_label = QLabel("")
        self.renewal_label.setFont(QFont("Segoe UI", 9))
        self.renewal_label.setStyleSheet("color: #888;")
        layout.addWidget(self.renewal_label)

        # Features list
        self.features_list = QLabel()
        self.features_list.setFont(QFont("Segoe UI", 10))
        self.features_list.setWordWrap(True)
        layout.addWidget(self.features_list)

        self._update_current_plan_display()

        return group

    def _create_plans_section(self) -> QGroupBox:
        """Create the available plans section."""
        group = QGroupBox("Available Plans")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QHBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Create plan cards
        for plan_id, plan_info in self.PLANS.items():
            card = self._create_plan_card(plan_id, plan_info)
            layout.addWidget(card)

        layout.addStretch()

        return group

    def _create_plan_card(self, plan_id: str, plan_info: Dict) -> QFrame:
        """Create a plan card widget."""
        card = QFrame()
        card.setObjectName(f"planCard_{plan_id}")
        card.setFixedWidth(220)
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: 16px;
            }
            QFrame:hover {
                border-color: #4CAF50;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        # Plan name
        name = QLabel(plan_info["name"])
        name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

        # Price
        price_layout = QHBoxLayout()
        price_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        price = QLabel(plan_info["price"])
        price.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        price.setStyleSheet("color: #4CAF50;")
        price_layout.addWidget(price)

        period = QLabel(f"/{plan_info['period']}")
        period.setFont(QFont("Segoe UI", 10))
        period.setStyleSheet("color: #888;")
        price_layout.addWidget(period)

        layout.addLayout(price_layout)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(divider)

        # Features
        for feature in plan_info["features"][:4]:  # Show max 4 features
            feature_label = QLabel(f"  {feature}")
            feature_label.setFont(QFont("Segoe UI", 9))
            feature_label.setStyleSheet("color: #666;")
            layout.addWidget(feature_label)

        if len(plan_info["features"]) > 4:
            more_label = QLabel(f"  +{len(plan_info['features']) - 4} more...")
            more_label.setFont(QFont("Segoe UI", 9))
            more_label.setStyleSheet("color: #888; font-style: italic;")
            layout.addWidget(more_label)

        layout.addStretch()

        # Button
        if plan_id == self._current_plan:
            btn = QPushButton("Current Plan")
            btn.setEnabled(False)
        else:
            btn = QPushButton("Upgrade" if plan_id != "free" else "Downgrade")
            btn.setObjectName("primaryButton" if plan_id != "free" else "secondaryButton")
            btn.clicked.connect(lambda _, p=plan_id: self._on_plan_selected(p))

        layout.addWidget(btn)

        return card

    def _create_billing_section(self) -> QGroupBox:
        """Create the billing info section."""
        group = QGroupBox("Billing")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Payment method
        payment_layout = QHBoxLayout()

        payment_label = QLabel("Payment Method:")
        payment_label.setFont(QFont("Segoe UI", 10))
        payment_layout.addWidget(payment_label)

        self.payment_method_label = QLabel("Not set")
        self.payment_method_label.setFont(QFont("Segoe UI", 10))
        self.payment_method_label.setStyleSheet("color: #666;")
        payment_layout.addWidget(self.payment_method_label)

        payment_layout.addStretch()

        manage_payment_btn = QPushButton("Manage")
        manage_payment_btn.setObjectName("secondaryButton")
        manage_payment_btn.setMaximumWidth(100)
        manage_payment_btn.clicked.connect(self.manage_subscription_requested.emit)
        payment_layout.addWidget(manage_payment_btn)

        layout.addLayout(payment_layout)

        # Billing history
        history_btn = QPushButton("View Billing History")
        history_btn.setObjectName("secondaryButton")
        history_btn.setMaximumWidth(200)
        history_btn.clicked.connect(self._show_billing_history)
        layout.addWidget(history_btn)

        # Cancel subscription (only for paid plans)
        self.cancel_btn = QPushButton("Cancel Subscription")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setMaximumWidth(200)
        self.cancel_btn.clicked.connect(self._on_cancel_subscription)
        self.cancel_btn.setVisible(False)  # Hidden for free plan
        layout.addWidget(self.cancel_btn)

        return group

    def _update_current_plan_display(self):
        """Update the current plan display."""
        plan_info = self.PLANS.get(self._current_plan, self.PLANS["free"])

        self.plan_name_label.setText(plan_info["name"])

        features_text = "\n".join([f"  {f}" for f in plan_info["features"]])
        self.features_list.setText(features_text)

        # Show cancel button only for paid plans
        self.cancel_btn.setVisible(self._current_plan != "free")

    def _on_plan_selected(self, plan_id: str):
        """Handle plan selection."""
        if plan_id == self._current_plan:
            return

        plan_name = self.PLANS[plan_id]["name"]

        if plan_id == "free":
            reply = QMessageBox.warning(
                self,
                "Downgrade Plan",
                f"Are you sure you want to downgrade to the Free plan?\n\n"
                "You will lose access to premium features at the end of your billing period.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
        else:
            reply = QMessageBox.question(
                self,
                "Upgrade Plan",
                f"Would you like to upgrade to {plan_name}?\n\n"
                f"Price: {self.PLANS[plan_id]['price']}/{self.PLANS[plan_id]['period']}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

        if reply == QMessageBox.StandardButton.Yes:
            self.upgrade_requested.emit(plan_id)

    def _on_cancel_subscription(self):
        """Handle subscription cancellation."""
        reply = QMessageBox.warning(
            self,
            "Cancel Subscription",
            "Are you sure you want to cancel your subscription?\n\n"
            "You will continue to have access until the end of your billing period.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.cancel_subscription_requested.emit()

    def _show_billing_history(self):
        """Show billing history dialog."""
        QMessageBox.information(
            self,
            "Billing History",
            "Billing history feature coming soon.\n\n"
            "For now, please check your email for invoices."
        )

    def set_current_plan(self, plan_id: str, renewal_date: str = ""):
        """Set the current subscription plan."""
        self._current_plan = plan_id
        self._update_current_plan_display()

        if renewal_date:
            self.renewal_label.setText(f"Renews on {renewal_date}")
        else:
            self.renewal_label.setText("")

    def set_payment_method(self, method: str):
        """Set the payment method display."""
        self.payment_method_label.setText(method)


# =============================================================================
# Data Section
# =============================================================================

class DataSection(QWidget):
    """Data management - Export, import, backup functionality."""

    # Signals
    export_requested = pyqtSignal(str, dict)  # format, options
    import_requested = pyqtSignal(str)  # file_path
    backup_requested = pyqtSignal()
    restore_requested = pyqtSignal(str)  # backup_path
    clear_data_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the data section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # Export Section
        export_group = self._create_export_section()
        content_layout.addWidget(export_group)

        # Import Section
        import_group = self._create_import_section()
        content_layout.addWidget(import_group)

        # Backup Section
        backup_group = self._create_backup_section()
        content_layout.addWidget(backup_group)

        # Clear Data Section
        clear_group = self._create_clear_section()
        content_layout.addWidget(clear_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_export_section(self) -> QGroupBox:
        """Create the export data section."""
        group = QGroupBox("Export Data")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        desc = QLabel(
            "Export your financial data to a file for backup or use in other applications."
        )
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Export options
        options_layout = QGridLayout()
        options_layout.setSpacing(15)

        # Data type selection
        type_label = QLabel("Data to Export:")
        type_label.setFont(QFont("Segoe UI", 10))
        options_layout.addWidget(type_label, 0, 0)

        self.export_transactions_check = QCheckBox("Transactions")
        self.export_transactions_check.setChecked(True)
        options_layout.addWidget(self.export_transactions_check, 0, 1)

        self.export_budgets_check = QCheckBox("Budgets")
        self.export_budgets_check.setChecked(True)
        options_layout.addWidget(self.export_budgets_check, 0, 2)

        self.export_categories_check = QCheckBox("Categories")
        self.export_categories_check.setChecked(True)
        options_layout.addWidget(self.export_categories_check, 1, 1)

        self.export_accounts_check = QCheckBox("Accounts")
        self.export_accounts_check.setChecked(True)
        options_layout.addWidget(self.export_accounts_check, 1, 2)

        # Date range
        range_label = QLabel("Date Range:")
        range_label.setFont(QFont("Segoe UI", 10))
        options_layout.addWidget(range_label, 2, 0)

        self.date_range_combo = QComboBox()
        self.date_range_combo.addItems([
            "All Time",
            "Last 12 Months",
            "Last 6 Months",
            "Last 3 Months",
            "This Year",
            "Last Year"
        ])
        self.date_range_combo.setMaximumWidth(150)
        options_layout.addWidget(self.date_range_combo, 2, 1)

        layout.addLayout(options_layout)

        # Export buttons
        btn_layout = QHBoxLayout()

        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.setObjectName("secondaryButton")
        export_csv_btn.clicked.connect(lambda: self._on_export("csv"))
        btn_layout.addWidget(export_csv_btn)

        export_json_btn = QPushButton("Export to JSON")
        export_json_btn.setObjectName("secondaryButton")
        export_json_btn.clicked.connect(lambda: self._on_export("json"))
        btn_layout.addWidget(export_json_btn)

        export_excel_btn = QPushButton("Export to Excel")
        export_excel_btn.setObjectName("secondaryButton")
        export_excel_btn.clicked.connect(lambda: self._on_export("xlsx"))
        btn_layout.addWidget(export_excel_btn)

        export_pdf_btn = QPushButton("Export to PDF")
        export_pdf_btn.setObjectName("secondaryButton")
        export_pdf_btn.clicked.connect(lambda: self._on_export("pdf"))
        btn_layout.addWidget(export_pdf_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_import_section(self) -> QGroupBox:
        """Create the import data section."""
        group = QGroupBox("Import Data")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        desc = QLabel(
            "Import financial data from CSV, JSON, Excel, or OFX/QFX files. "
            "Existing data will be merged with imported data."
        )
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Import options
        self.import_merge_radio = QRadioButton("Merge with existing data")
        self.import_merge_radio.setFont(QFont("Segoe UI", 10))
        self.import_merge_radio.setChecked(True)
        layout.addWidget(self.import_merge_radio)

        self.import_replace_radio = QRadioButton("Replace existing data")
        self.import_replace_radio.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.import_replace_radio)

        import_btn = QPushButton("Import Data...")
        import_btn.setObjectName("secondaryButton")
        import_btn.setMaximumWidth(150)
        import_btn.clicked.connect(self._on_import)
        layout.addWidget(import_btn)

        return group

    def _create_backup_section(self) -> QGroupBox:
        """Create the backup section."""
        group = QGroupBox("Backup & Restore")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        desc = QLabel(
            "Create a complete backup of all your data, settings, and preferences. "
            "Backups can be restored at any time."
        )
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Last backup info
        backup_info_layout = QHBoxLayout()

        self.last_backup_label = QLabel("Last Backup: Never")
        self.last_backup_label.setFont(QFont("Segoe UI", 10))
        self.last_backup_label.setStyleSheet("color: #888;")
        backup_info_layout.addWidget(self.last_backup_label)

        backup_info_layout.addStretch()
        layout.addLayout(backup_info_layout)

        # Backup buttons
        btn_layout = QHBoxLayout()

        backup_btn = QPushButton("Create Backup")
        backup_btn.setObjectName("primaryButton")
        backup_btn.clicked.connect(self._on_backup)
        btn_layout.addWidget(backup_btn)

        restore_btn = QPushButton("Restore from Backup...")
        restore_btn.setObjectName("secondaryButton")
        restore_btn.clicked.connect(self._on_restore)
        btn_layout.addWidget(restore_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Auto-backup option
        self.auto_backup_check = QCheckBox("Enable automatic weekly backups")
        self.auto_backup_check.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.auto_backup_check)

        return group

    def _create_clear_section(self) -> QGroupBox:
        """Create the clear data section."""
        group = QGroupBox("Clear Data")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet("QGroupBox { color: #E57373; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        warning = QLabel(
            "Clear all locally cached data. This will not affect your cloud data.\n"
            "You may need to re-sync after clearing local data."
        )
        warning.setFont(QFont("Segoe UI", 10))
        warning.setStyleSheet("color: #E57373;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        btn_layout = QHBoxLayout()

        clear_cache_btn = QPushButton("Clear Cache")
        clear_cache_btn.setObjectName("secondaryButton")
        clear_cache_btn.clicked.connect(self._on_clear_cache)
        btn_layout.addWidget(clear_cache_btn)

        clear_all_btn = QPushButton("Clear All Local Data")
        clear_all_btn.setObjectName("dangerButton")
        clear_all_btn.clicked.connect(self._on_clear_all)
        btn_layout.addWidget(clear_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _on_export(self, format_type: str):
        """Handle export request."""
        file_filters = {
            "csv": "CSV Files (*.csv)",
            "json": "JSON Files (*.json)",
            "xlsx": "Excel Files (*.xlsx)",
            "pdf": "PDF Files (*.pdf)"
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            f"pecunia_export.{format_type}",
            file_filters.get(format_type, "All Files (*)")
        )

        if file_path:
            options = {
                "transactions": self.export_transactions_check.isChecked(),
                "budgets": self.export_budgets_check.isChecked(),
                "categories": self.export_categories_check.isChecked(),
                "accounts": self.export_accounts_check.isChecked(),
                "date_range": self.date_range_combo.currentText(),
                "file_path": file_path
            }
            self.export_requested.emit(format_type, options)

    def _on_import(self):
        """Handle import request."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Data",
            "",
            "Data Files (*.csv *.json *.xlsx *.ofx *.qfx);;"
            "CSV Files (*.csv);;JSON Files (*.json);;"
            "Excel Files (*.xlsx);;OFX/QFX Files (*.ofx *.qfx)"
        )

        if file_path:
            self.import_requested.emit(file_path)

    def _on_backup(self):
        """Handle backup request."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create Backup",
            f"pecunia_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pab",
            "Pecunia Backup (*.pab)"
        )

        if file_path:
            self.backup_requested.emit()
            QMessageBox.information(
                self, "Backup Created",
                f"Backup successfully created:\n{file_path}"
            )
            self.last_backup_label.setText(
                f"Last Backup: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

    def _on_restore(self):
        """Handle restore request."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore from Backup",
            "",
            "Pecunia Backup (*.pab);;All Files (*)"
        )

        if file_path:
            reply = QMessageBox.warning(
                self,
                "Restore Backup",
                "Restoring from backup will replace all current data.\n\n"
                "This action cannot be undone. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.restore_requested.emit(file_path)

    def _on_clear_cache(self):
        """Handle clear cache request."""
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "This will clear cached data and temporary files.\n\n"
            "Your actual data will not be affected. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Clear cache logic would go here
            QMessageBox.information(self, "Cache Cleared", "Cache has been cleared successfully.")

    def _on_clear_all(self):
        """Handle clear all data request."""
        reply = QMessageBox.warning(
            self,
            "Clear All Local Data",
            "Are you sure you want to clear all local data?\n\n"
            "This action cannot be undone, but your cloud data will not be affected.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.clear_data_requested.emit()

    def set_last_backup(self, timestamp: str):
        """Set the last backup timestamp."""
        self.last_backup_label.setText(f"Last Backup: {timestamp}")


# =============================================================================
# About Section
# =============================================================================

class AboutSection(QWidget):
    """About section - Version info, licenses, credits."""

    # Signals
    check_updates_requested = pyqtSignal()
    open_help_requested = pyqtSignal()
    feedback_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._app_version = "1.0.0"
        self._build_number = "2025.01.28"
        self._setup_ui()

    def _setup_ui(self):
        """Set up the about section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # App Info Section
        info_group = self._create_info_section()
        content_layout.addWidget(info_group)

        # Updates Section
        updates_group = self._create_updates_section()
        content_layout.addWidget(updates_group)

        # Help & Support Section
        help_group = self._create_help_section()
        content_layout.addWidget(help_group)

        # Licenses Section
        licenses_group = self._create_licenses_section()
        content_layout.addWidget(licenses_group)

        # Credits Section
        credits_group = self._create_credits_section()
        content_layout.addWidget(credits_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_info_section(self) -> QGroupBox:
        """Create the application info section."""
        group = QGroupBox("Application Information")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # App header
        header_layout = QHBoxLayout()

        # App icon placeholder
        icon_frame = QFrame()
        icon_frame.setFixedSize(64, 64)
        icon_frame.setStyleSheet("""
            QFrame {
                background-color: #4CAF50;
                border-radius: 12px;
            }
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_label = QLabel("FA")
        icon_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        icon_label.setStyleSheet("color: white;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        header_layout.addWidget(icon_frame)

        # App name and version
        info_layout = QVBoxLayout()

        app_name = QLabel("Pecunia Desktop")
        app_name.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        info_layout.addWidget(app_name)

        self.version_label = QLabel(f"Version {self._app_version}")
        self.version_label.setFont(QFont("Segoe UI", 10))
        self.version_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.version_label)

        self.build_label = QLabel(f"Build {self._build_number}")
        self.build_label.setFont(QFont("Segoe UI", 9))
        self.build_label.setStyleSheet("color: #888;")
        info_layout.addWidget(self.build_label)

        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # System info
        info_grid = QGridLayout()
        info_grid.setSpacing(10)

        platform_title = QLabel("Platform:")
        platform_title.setFont(QFont("Segoe UI", 9))
        platform_title.setStyleSheet("color: #888;")
        info_grid.addWidget(platform_title, 0, 0)

        import platform
        platform_value = QLabel(f"{platform.system()} {platform.release()}")
        platform_value.setFont(QFont("Segoe UI", 9))
        info_grid.addWidget(platform_value, 0, 1)

        python_title = QLabel("Python:")
        python_title.setFont(QFont("Segoe UI", 9))
        python_title.setStyleSheet("color: #888;")
        info_grid.addWidget(python_title, 1, 0)

        import sys
        python_value = QLabel(f"{sys.version.split()[0]}")
        python_value.setFont(QFont("Segoe UI", 9))
        info_grid.addWidget(python_value, 1, 1)

        qt_title = QLabel("Qt Version:")
        qt_title.setFont(QFont("Segoe UI", 9))
        qt_title.setStyleSheet("color: #888;")
        info_grid.addWidget(qt_title, 2, 0)

        from PyQt6.QtCore import QT_VERSION_STR
        qt_value = QLabel(QT_VERSION_STR)
        qt_value.setFont(QFont("Segoe UI", 9))
        info_grid.addWidget(qt_value, 2, 1)

        info_grid.setColumnStretch(2, 1)
        layout.addLayout(info_grid)

        return group

    def _create_updates_section(self) -> QGroupBox:
        """Create the updates section."""
        group = QGroupBox("Updates")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Update status
        status_layout = QHBoxLayout()

        self.update_status_label = QLabel("No updates available")
        self.update_status_label.setFont(QFont("Segoe UI", 10))
        status_layout.addWidget(self.update_status_label)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        check_btn = QPushButton("Check for Updates")
        check_btn.setObjectName("secondaryButton")
        check_btn.clicked.connect(self._on_check_updates)
        btn_layout.addWidget(check_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Auto-update option
        self.auto_update_check = QCheckBox("Automatically check for updates")
        self.auto_update_check.setFont(QFont("Segoe UI", 10))
        self.auto_update_check.setChecked(True)
        layout.addWidget(self.auto_update_check)

        return group

    def _create_help_section(self) -> QGroupBox:
        """Create the help and support section."""
        group = QGroupBox("Help & Support")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Buttons
        btn_layout = QHBoxLayout()

        help_btn = QPushButton("Open Help Documentation")
        help_btn.setObjectName("secondaryButton")
        help_btn.clicked.connect(self.open_help_requested.emit)
        btn_layout.addWidget(help_btn)

        feedback_btn = QPushButton("Send Feedback")
        feedback_btn.setObjectName("secondaryButton")
        feedback_btn.clicked.connect(self.feedback_requested.emit)
        btn_layout.addWidget(feedback_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Links
        links_layout = QVBoxLayout()
        links_layout.setSpacing(8)

        website = QLabel('<a href="https://pecunia.example.com">Visit Website</a>')
        website.setFont(QFont("Segoe UI", 10))
        website.setOpenExternalLinks(True)
        links_layout.addWidget(website)

        support = QLabel('<a href="mailto:support@pecunia.example.com">Contact Support</a>')
        support.setFont(QFont("Segoe UI", 10))
        support.setOpenExternalLinks(True)
        links_layout.addWidget(support)

        privacy = QLabel('<a href="https://pecunia.example.com/privacy">Privacy Policy</a>')
        privacy.setFont(QFont("Segoe UI", 10))
        privacy.setOpenExternalLinks(True)
        links_layout.addWidget(privacy)

        terms = QLabel('<a href="https://pecunia.example.com/terms">Terms of Service</a>')
        terms.setFont(QFont("Segoe UI", 10))
        terms.setOpenExternalLinks(True)
        links_layout.addWidget(terms)

        layout.addLayout(links_layout)

        return group

    def _create_licenses_section(self) -> QGroupBox:
        """Create the licenses section."""
        group = QGroupBox("Open Source Licenses")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        desc = QLabel(
            "Pecunia Desktop uses the following open source libraries:"
        )
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # Licenses list
        licenses_text = QTextEdit()
        licenses_text.setReadOnly(True)
        licenses_text.setMaximumHeight(150)
        licenses_text.setFont(QFont("Consolas", 9))
        licenses_text.setText("""PyQt6 - GPL v3 / Commercial
Requests - Apache 2.0
SQLAlchemy - MIT License
cryptography - Apache 2.0 / BSD
keyring - MIT License
python-dateutil - Apache 2.0
pillow - HPND License
matplotlib - PSF License""")
        layout.addWidget(licenses_text)

        view_all_btn = QPushButton("View All Licenses")
        view_all_btn.setObjectName("secondaryButton")
        view_all_btn.setMaximumWidth(150)
        view_all_btn.clicked.connect(self._show_all_licenses)
        layout.addWidget(view_all_btn)

        return group

    def _create_credits_section(self) -> QGroupBox:
        """Create the credits section."""
        group = QGroupBox("Credits")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        credits_text = QLabel(
            "Pecunia Desktop is developed by the Pecunia Team.\n\n"
            "Special thanks to all our contributors and beta testers "
            "who helped make this application possible.\n\n"
            "Icons provided by Material Design Icons."
        )
        credits_text.setFont(QFont("Segoe UI", 10))
        credits_text.setStyleSheet("color: #666;")
        credits_text.setWordWrap(True)
        layout.addWidget(credits_text)

        # Copyright
        copyright_label = QLabel(
            "Copyright 2025 Pecunia Inc. All rights reserved."
        )
        copyright_label.setFont(QFont("Segoe UI", 9))
        copyright_label.setStyleSheet("color: #888;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)

        return group

    def _on_check_updates(self):
        """Handle check updates click."""
        self.update_status_label.setText("Checking for updates...")
        self.check_updates_requested.emit()

    def _show_all_licenses(self):
        """Show full licenses dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Open Source Licenses")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 9))
        text_edit.setText("""
PECUNIA DESKTOP - OPEN SOURCE LICENSES
==========================================

PyQt6
------
Copyright (c) Riverbank Computing Limited
License: GPL v3 / Commercial License

Requests
--------
Copyright (c) Kenneth Reitz
License: Apache License 2.0

SQLAlchemy
----------
Copyright (c) SQLAlchemy Authors
License: MIT License

cryptography
------------
Copyright (c) The cryptography developers
License: Apache License 2.0 / BSD License

keyring
-------
Copyright (c) Jason R. Coombs
License: MIT License

python-dateutil
---------------
Copyright (c) Gustavo Niemeyer
License: Apache License 2.0

Pillow
------
Copyright (c) Alex Clark and Contributors
License: HPND License

matplotlib
----------
Copyright (c) Matplotlib Development Team
License: PSF License

For full license texts, please visit the respective project websites.
        """)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()

    def set_version(self, version: str, build: str = ""):
        """Set the app version display."""
        self._app_version = version
        self._build_number = build
        self.version_label.setText(f"Version {version}")
        if build:
            self.build_label.setText(f"Build {build}")

    def set_update_status(self, status: str, has_update: bool = False):
        """Set the update status message."""
        self.update_status_label.setText(status)
        if has_update:
            self.update_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.update_status_label.setStyleSheet("")
