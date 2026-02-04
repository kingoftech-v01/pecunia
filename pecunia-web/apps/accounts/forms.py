"""
Accounts Forms.

Django forms for user authentication and profile management (frontend).
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import password_validation
from .models import User, UserProfile


class UserRegistrationForm(UserCreationForm):
    """
    Form for user registration.

    Extended from UserCreationForm with additional fields.
    """
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email address',
            'autocomplete': 'email'
        })
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
            'autocomplete': 'given-name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
            'autocomplete': 'family-name'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']


class UserLoginForm(AuthenticationForm):
    """
    Form for user login.

    Styled authentication form with email as username.
    """
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email address',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )

    error_messages = {
        'invalid_login': "Invalid email or password.",
        'inactive': "This account is inactive.",
    }


class UserUpdateForm(forms.ModelForm):
    """
    Form for updating user information.

    Allows editing of basic user details.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'preferred_currency']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Last name'
            }),
            'preferred_currency': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class UserProfileForm(forms.ModelForm):
    """
    Form for updating user profile preferences.

    Handles notification and display settings.
    """

    class Meta:
        model = UserProfile
        fields = [
            'email_notifications', 'push_notifications',
            'weekly_summary', 'budget_alerts',
            'theme', 'language', 'date_format'
        ]
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'weekly_summary': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'budget_alerts': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'date_format': forms.Select(attrs={'class': 'form-select'}),
        }


class ChangePasswordForm(forms.Form):
    """
    Form for changing password.

    Validates current and new passwords.
    """
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current password',
            'autocomplete': 'current-password'
        })
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New password',
            'autocomplete': 'new-password'
        }),
        help_text=password_validation.password_validators_help_text_html()
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """Validate current password is correct."""
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError("Current password is incorrect.")
        return current_password

    def clean(self):
        """Validate new passwords match."""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError("New passwords do not match.")
            password_validation.validate_password(new_password1, self.user)

        return cleaned_data

    def save(self):
        """Save the new password."""
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.save()
        return self.user
