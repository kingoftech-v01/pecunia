"""
Transactions Forms.

Django forms for transaction management (frontend).
"""
from django import forms
from .models import Transaction, TransactionCategory, RecurringTransaction


class TransactionCategoryForm(forms.ModelForm):
    """
    Form for creating/editing transaction categories.

    Used in frontend category management.
    """

    class Meta:
        model = TransactionCategory
        fields = ['name', 'type', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Category name'
            }),
            'type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Icon name (e.g., shopping-cart)'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-input',
                'type': 'color'
            }),
        }


class TransactionForm(forms.ModelForm):
    """
    Form for creating/editing transactions.

    Used in frontend transaction management.
    """

    class Meta:
        model = Transaction
        fields = [
            'category', 'amount', 'type', 'description',
            'merchant', 'transaction_date', 'tags', 'notes'
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Description'
            }),
            'merchant': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Merchant name'
            }),
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Additional notes...'
            }),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['category'].queryset = TransactionCategory.objects.filter(
            user=user
        )


class TransactionFilterForm(forms.Form):
    """
    Form for filtering transactions.

    Used in transaction list view.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search transactions...'
        })
    )
    type = forms.ChoiceField(
        required=False,
        choices=[('', 'All types')] + Transaction.TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=TransactionCategory.objects.none(),
        empty_label='All categories',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TransactionCategory.objects.filter(
            user=user
        )


class RecurringTransactionForm(forms.ModelForm):
    """
    Form for recurring transaction templates.

    Used in frontend recurring transaction management.
    """

    class Meta:
        model = RecurringTransaction
        fields = [
            'name', 'category', 'amount', 'type',
            'description', 'frequency', 'start_date', 'end_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Recurring transaction name'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Description'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['category'].queryset = TransactionCategory.objects.filter(
            user=user
        )
