"""
Subscriptions Forms.

Django forms for subscription management (frontend).
"""
from django import forms
from .models import SubscriptionPlan


class PlanSelectionForm(forms.Form):
    """
    Form for selecting a subscription plan.

    Used on the pricing page for plan selection.
    """
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        widget=forms.RadioSelect(attrs={
            'class': 'plan-radio',
        }),
        empty_label=None,
    )
    billing_interval = forms.ChoiceField(
        choices=[
            ('month', 'Monthly'),
            ('year', 'Yearly'),
        ],
        initial='month',
        widget=forms.RadioSelect(attrs={
            'class': 'billing-radio',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order plans by display order
        self.fields['plan'].queryset = SubscriptionPlan.objects.filter(
            is_active=True
        ).order_by('display_order')


class BillingIntervalForm(forms.Form):
    """
    Form for changing billing interval.

    Used when switching between monthly and yearly billing.
    """
    billing_interval = forms.ChoiceField(
        choices=[
            ('month', 'Monthly'),
            ('year', 'Yearly (Save up to 20%)'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )


class CancelSubscriptionForm(forms.Form):
    """
    Form for subscription cancellation.

    Collects cancellation feedback.
    """
    CANCEL_REASONS = [
        ('too_expensive', 'Too expensive'),
        ('not_using', 'Not using the features'),
        ('missing_features', 'Missing features I need'),
        ('switching', 'Switching to another service'),
        ('temporary', 'Only need it temporarily'),
        ('other', 'Other reason'),
    ]

    cancel_at_period_end = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='Cancel at the end of current billing period',
        help_text='If unchecked, your subscription will be canceled immediately.'
    )
    reason = forms.ChoiceField(
        choices=CANCEL_REASONS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='Reason for canceling (optional)',
    )
    feedback = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Any additional feedback? (optional)',
        }),
        label='Additional feedback',
    )
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='I understand that canceling will remove access to premium features',
    )


class ReactivateSubscriptionForm(forms.Form):
    """
    Form for reactivating a canceled subscription.

    Simple confirmation form.
    """
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='I want to reactivate my subscription',
    )


class ChangePlanForm(forms.Form):
    """
    Form for changing subscription plan.

    Used for upgrades and downgrades.
    """
    new_plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        widget=forms.RadioSelect(attrs={
            'class': 'plan-radio',
        }),
        empty_label=None,
        label='Select new plan',
    )
    billing_interval = forms.ChoiceField(
        choices=[
            ('month', 'Monthly'),
            ('year', 'Yearly'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'billing-radio',
        }),
        label='Billing frequency',
    )
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='I understand the price difference will be prorated',
    )

    def __init__(self, current_plan=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_plan = current_plan
        # Exclude current plan from choices
        if current_plan:
            self.fields['new_plan'].queryset = SubscriptionPlan.objects.filter(
                is_active=True
            ).exclude(id=current_plan.id).order_by('display_order')

    def clean_new_plan(self):
        """Validate that the new plan is different from current."""
        new_plan = self.cleaned_data['new_plan']
        if self.current_plan and new_plan.id == self.current_plan.id:
            raise forms.ValidationError("Please select a different plan.")
        return new_plan


class UpdatePaymentMethodForm(forms.Form):
    """
    Form for updating payment method.

    Redirects to Stripe for actual card input.
    """
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='I want to update my payment method',
        help_text='You will be redirected to our secure payment provider.',
    )


class ContactSupportForm(forms.Form):
    """
    Form for contacting support about billing.

    Used for billing inquiries.
    """
    INQUIRY_TYPES = [
        ('billing_question', 'Billing question'),
        ('refund_request', 'Refund request'),
        ('payment_issue', 'Payment issue'),
        ('invoice_request', 'Invoice request'),
        ('plan_question', 'Plan/pricing question'),
        ('other', 'Other'),
    ]

    inquiry_type = forms.ChoiceField(
        choices=INQUIRY_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='Type of inquiry',
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Brief description of your inquiry',
        }),
        label='Subject',
    )
    message = forms.CharField(
        max_length=5000,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 5,
            'placeholder': 'Please describe your inquiry in detail...',
        }),
        label='Message',
    )
    invoice_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'If applicable',
        }),
        label='Invoice number (optional)',
    )
