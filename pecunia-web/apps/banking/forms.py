"""
Banking Forms.

Django forms for bank connection management (frontend).
"""
from django import forms
from .models import BankConnection, BankAccount


class ConnectBankForm(forms.Form):
    """
    Form for initiating a bank connection.

    Allows users to select a provider and optionally a specific institution.
    """
    PROVIDER_CHOICES = [
        ('', 'Select a provider...'),
        ('budget_insight', 'Powens (France & Europe)'),
        ('truelayer', 'TrueLayer (UK & Europe)'),
        ('plaid', 'Plaid (International)'),
    ]

    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'provider',
            '@change': 'onProviderChange()',
        })
    )
    institution_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'x-model': 'institutionId',
        })
    )
    institution_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search for your bank...',
            'x-model': 'institutionSearch',
            '@input': 'searchInstitutions()',
            'autocomplete': 'off',
        })
    )

    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        provider = cleaned_data.get('provider')

        if not provider:
            raise forms.ValidationError("Please select a provider.")

        return cleaned_data


class InstitutionSearchForm(forms.Form):
    """
    Form for searching institutions.

    Used for HTMX-powered institution search.
    """
    provider = forms.ChoiceField(
        choices=ConnectBankForm.PROVIDER_CHOICES,
        required=True,
        widget=forms.HiddenInput()
    )
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search for your bank...',
            'hx-get': '/banking/institutions/search/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#institution-results',
            'hx-include': '[name=provider]',
            'autocomplete': 'off',
        })
    )
    country = forms.ChoiceField(
        choices=[
            ('', 'All countries'),
            ('FR', 'France'),
            ('GB', 'United Kingdom'),
            ('DE', 'Germany'),
            ('ES', 'Spain'),
            ('IT', 'Italy'),
            ('NL', 'Netherlands'),
            ('BE', 'Belgium'),
            ('US', 'United States'),
            ('CA', 'Canada'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )


class BankAccountSettingsForm(forms.ModelForm):
    """
    Form for updating bank account display settings.

    Allows users to customize account appearance.
    """

    class Meta:
        model = BankAccount
        fields = ['custom_name', 'color', 'is_hidden']
        widgets = {
            'custom_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Custom display name',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-input',
                'type': 'color',
            }),
            'is_hidden': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }
        labels = {
            'custom_name': 'Display Name',
            'color': 'Account Color',
            'is_hidden': 'Hide this account',
        }
        help_texts = {
            'custom_name': 'Override the default account name',
            'is_hidden': 'Hidden accounts are excluded from totals and views',
        }


class BankConnectionSettingsForm(forms.Form):
    """
    Form for bank connection settings.

    Allows users to manage connection preferences.
    """
    auto_sync = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='Enable automatic sync',
        help_text='Automatically sync this connection daily'
    )
    sync_transactions = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='Sync transactions',
        help_text='Import transactions from this connection'
    )
    notifications = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='Enable notifications',
        help_text='Receive alerts for sync issues'
    )


class DisconnectBankForm(forms.Form):
    """
    Form for disconnecting a bank.

    Requires confirmation before disconnection.
    """
    connection_id = forms.UUIDField(
        widget=forms.HiddenInput()
    )
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='I understand this will remove all associated data',
        help_text='This action cannot be undone'
    )

    def clean_confirm(self):
        """Ensure confirmation is checked."""
        confirm = self.cleaned_data.get('confirm')
        if not confirm:
            raise forms.ValidationError(
                "You must confirm to disconnect the bank."
            )
        return confirm


class SyncOptionsForm(forms.Form):
    """
    Form for manual sync options.

    Allows users to trigger and configure manual syncs.
    """
    SYNC_TYPE_CHOICES = [
        ('incremental', 'Quick sync (new transactions only)'),
        ('full', 'Full sync (all historical data)'),
        ('balance', 'Balance only (fastest)'),
    ]

    sync_type = forms.ChoiceField(
        choices=SYNC_TYPE_CHOICES,
        initial='incremental',
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio',
        }),
        label='Sync Type'
    )
    connection_ids = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox',
        }),
        label='Select connections to sync'
    )

    def __init__(self, *args, connections=None, **kwargs):
        """Initialize form with user's connections."""
        super().__init__(*args, **kwargs)
        if connections:
            self.fields['connection_ids'].choices = [
                (str(conn.id), conn.institution_name)
                for conn in connections
            ]
