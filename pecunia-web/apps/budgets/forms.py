"""
Budgets Forms.

Django forms for budget management (frontend).
"""
from django import forms
from django.utils import timezone
from apps.transactions.models import TransactionCategory
from .models import Budget, BudgetItem


class BudgetForm(forms.ModelForm):
    """
    Form for creating/editing budgets.

    Used in frontend budget management.
    """

    class Meta:
        model = Budget
        fields = [
            'name', 'description', 'period_type',
            'start_date', 'end_date',
            'is_active', 'is_rollover',
            'alert_threshold', 'notify_on_exceed'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Budget name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Budget description (optional)'
            }),
            'period_type': forms.Select(attrs={
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
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'is_rollover': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
                'max': 100,
                'placeholder': '80'
            }),
            'notify_on_exceed': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }

    def clean(self):
        """Validate budget dates."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date <= start_date:
                raise forms.ValidationError({
                    'end_date': 'End date must be after start date.'
                })

        return cleaned_data


class BudgetItemForm(forms.ModelForm):
    """
    Form for creating/editing budget items.

    Used in frontend budget item management.
    """

    class Meta:
        model = BudgetItem
        fields = ['category', 'name', 'planned_amount', 'notes', 'is_active']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Custom name (optional)'
            }),
            'planned_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Notes (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['category'].queryset = TransactionCategory.objects.filter(
            user=user,
            type='expense'
        )
        self.fields['category'].empty_label = 'Select a category'


class BudgetItemInlineForm(forms.ModelForm):
    """
    Inline form for budget items (used in formsets).

    Simplified form for adding multiple items at once.
    """

    class Meta:
        model = BudgetItem
        fields = ['category', 'planned_amount']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'planned_amount': forms.NumberInput(attrs={
                'class': 'form-input form-input-sm',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
        }


class BudgetFilterForm(forms.Form):
    """
    Form for filtering budgets.

    Used in budget list view.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search budgets...'
        })
    )
    period_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All periods')] + Budget.PERIOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All statuses'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('over_budget', 'Over Budget'),
            ('on_track', 'On Track'),
        ],
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


class QuickBudgetForm(forms.Form):
    """
    Quick budget creation form.

    Simplified form for creating budgets with common presets.
    """
    PRESET_CHOICES = [
        ('monthly', 'Monthly Budget'),
        ('weekly', 'Weekly Budget'),
        ('custom', 'Custom Period'),
    ]

    preset = forms.ChoiceField(
        choices=PRESET_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio'
        })
    )
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Budget name'
        })
    )
    total_amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        })
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )

    def clean(self):
        """Set dates based on preset."""
        cleaned_data = super().clean()
        preset = cleaned_data.get('preset')
        start_date = cleaned_data.get('start_date')

        if not start_date:
            start_date = timezone.now().date()
            cleaned_data['start_date'] = start_date

        if preset == 'monthly':
            # Set to first and last day of current month
            from calendar import monthrange
            last_day = monthrange(start_date.year, start_date.month)[1]
            cleaned_data['start_date'] = start_date.replace(day=1)
            cleaned_data['end_date'] = start_date.replace(day=last_day)
            cleaned_data['period_type'] = 'monthly'
        elif preset == 'weekly':
            # Set to Monday-Sunday of current week
            from datetime import timedelta
            days_since_monday = start_date.weekday()
            monday = start_date - timedelta(days=days_since_monday)
            sunday = monday + timedelta(days=6)
            cleaned_data['start_date'] = monday
            cleaned_data['end_date'] = sunday
            cleaned_data['period_type'] = 'weekly'
        else:
            # Custom - require end date
            cleaned_data['period_type'] = 'custom'
            if 'end_date' not in cleaned_data:
                raise forms.ValidationError({
                    'start_date': 'For custom periods, please also set end date.'
                })

        return cleaned_data
