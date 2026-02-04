"""
Subscriptions Template Views (Frontend).

Django views for HTML pages with HTMX/Alpine.js support.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse

from .models import SubscriptionPlan, Subscription, SubscriptionEvent, Invoice
from .forms import (
    PlanSelectionForm,
    CancelSubscriptionForm,
    ReactivateSubscriptionForm,
    ChangePlanForm,
    BillingIntervalForm,
    ContactSupportForm,
)
from .stripe_service import stripe_service


def pricing_view(request):
    """
    Pricing page showing all subscription plans.

    Template: subscriptions/pricing.html
    URL: /subscriptions/pricing/
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')

    # Get user's current plan if logged in
    current_plan = None
    if request.user.is_authenticated and hasattr(request.user, 'subscription'):
        current_plan = request.user.subscription.plan

    context = {
        'plans': plans,
        'current_plan': current_plan,
    }
    return render(request, 'subscriptions/pricing.html', context)


@login_required
def subscription_view(request):
    """
    User subscription management page.

    Template: subscriptions/subscription.html
    URL: /subscriptions/
    """
    subscription = getattr(request.user, 'subscription', None)
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')

    context = {
        'subscription': subscription,
        'plans': plans,
    }
    return render(request, 'subscriptions/manage.html', context)


@login_required
def billing_view(request):
    """
    Billing history and payment management page.

    Template: subscriptions/billing.html
    URL: /subscriptions/billing/
    """
    subscription = getattr(request.user, 'subscription', None)
    invoices = []
    payment_methods = []
    upcoming_invoice = None

    if subscription and subscription.stripe_customer_id:
        # Get invoices
        invoices = Invoice.objects.filter(
            subscription=subscription
        ).order_by('-created_at')[:10]

        # Get payment methods from Stripe
        payment_methods_raw = stripe_service.get_payment_methods(
            subscription.stripe_customer_id
        )

        # Get default payment method
        customer = stripe_service.get_customer(subscription.stripe_customer_id)
        default_pm_id = None
        if customer and customer.get('invoice_settings'):
            default_pm_id = customer['invoice_settings'].get('default_payment_method')

        for pm in payment_methods_raw:
            card = pm.get('card', {})
            payment_methods.append({
                'id': pm.id,
                'brand': card.get('brand', '').title(),
                'last4': card.get('last4', '****'),
                'exp_month': card.get('exp_month'),
                'exp_year': card.get('exp_year'),
                'is_default': pm.id == default_pm_id,
            })

        # Get upcoming invoice
        upcoming_invoice = stripe_service.get_upcoming_invoice(
            subscription.stripe_customer_id
        )

    context = {
        'subscription': subscription,
        'invoices': invoices,
        'payment_methods': payment_methods,
        'upcoming_invoice': upcoming_invoice,
    }
    return render(request, 'subscriptions/billing_history.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def checkout_view(request, plan_id):
    """
    Checkout page for purchasing a subscription.

    Template: subscriptions/checkout.html
    URL: /subscriptions/checkout/{plan_id}/
    """
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

    # Check if user already has an active subscription
    if hasattr(request.user, 'subscription') and request.user.subscription.is_active:
        messages.warning(
            request,
            'You already have an active subscription. Please upgrade from your subscription page.'
        )
        return redirect('frontend:subscriptions:subscription')

    if request.method == 'POST':
        billing_interval = request.POST.get('billing_interval', 'month')

        # Get appropriate price ID
        if billing_interval == 'year':
            price_id = plan.stripe_price_id_yearly
        else:
            price_id = plan.stripe_price_id_monthly

        if not price_id:
            messages.error(request, 'Plan pricing not configured.')
            return redirect('frontend:subscriptions:pricing')

        # Create checkout session
        success_url = request.build_absolute_uri(
            reverse('frontend:subscriptions:success')
        ) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = request.build_absolute_uri(
            reverse('frontend:subscriptions:cancel')
        )

        result = stripe_service.create_checkout_session(
            user=request.user,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'plan_id': str(plan.id),
                'billing_interval': billing_interval,
            }
        )

        if result and result.get('url'):
            return HttpResponseRedirect(result['url'])
        else:
            messages.error(request, 'Failed to create checkout session.')
            return redirect('frontend:subscriptions:pricing')

    context = {
        'plan': plan,
        'form': BillingIntervalForm(),
    }
    return render(request, 'subscriptions/checkout.html', context)


@login_required
def checkout_success_view(request):
    """
    Checkout success page.

    Template: subscriptions/success.html
    URL: /subscriptions/success/
    """
    session_id = request.GET.get('session_id')

    context = {
        'session_id': session_id,
    }
    return render(request, 'subscriptions/success.html', context)


@login_required
def checkout_cancel_view(request):
    """
    Checkout cancelled page.

    Template: subscriptions/cancel.html
    URL: /subscriptions/cancel/
    """
    return render(request, 'subscriptions/cancel.html')


@login_required
@require_http_methods(['GET', 'POST'])
def cancel_subscription_view(request):
    """
    Subscription cancellation page.

    Template: subscriptions/cancel_subscription.html
    URL: /subscriptions/cancel-subscription/
    """
    subscription = getattr(request.user, 'subscription', None)

    if not subscription or not subscription.is_active:
        messages.info(request, 'No active subscription to cancel.')
        return redirect('frontend:subscriptions:subscription')

    if request.method == 'POST':
        form = CancelSubscriptionForm(request.POST)
        if form.is_valid():
            cancel_at_period_end = form.cleaned_data['cancel_at_period_end']
            reason = form.cleaned_data.get('reason', '')
            feedback = form.cleaned_data.get('feedback', '')

            success, error = stripe_service.cancel_subscription(
                subscription.stripe_subscription_id,
                at_period_end=cancel_at_period_end
            )

            if success:
                subscription.cancel_at_period_end = cancel_at_period_end
                if not cancel_at_period_end:
                    subscription.status = 'canceled'
                subscription.save()

                # Log event
                SubscriptionEvent.objects.create(
                    subscription=subscription,
                    event_type='canceled',
                    description=f'Subscription canceled. Reason: {reason}. Feedback: {feedback}',
                    metadata={
                        'reason': reason,
                        'feedback': feedback,
                        'at_period_end': cancel_at_period_end,
                    }
                )

                messages.success(request, 'Your subscription has been canceled.')
                return redirect('frontend:subscriptions:subscription')
            else:
                messages.error(request, f'Failed to cancel subscription: {error}')
    else:
        form = CancelSubscriptionForm()

    context = {
        'subscription': subscription,
        'form': form,
    }
    return render(request, 'subscriptions/cancel_subscription.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def reactivate_subscription_view(request):
    """
    Subscription reactivation page.

    Template: subscriptions/reactivate.html
    URL: /subscriptions/reactivate/
    """
    subscription = getattr(request.user, 'subscription', None)

    if not subscription or not subscription.cancel_at_period_end:
        messages.info(request, 'No subscription to reactivate.')
        return redirect('frontend:subscriptions:subscription')

    if request.method == 'POST':
        form = ReactivateSubscriptionForm(request.POST)
        if form.is_valid():
            success, error = stripe_service.reactivate_subscription(
                subscription.stripe_subscription_id
            )

            if success:
                subscription.cancel_at_period_end = False
                subscription.save()

                SubscriptionEvent.objects.create(
                    subscription=subscription,
                    event_type='reactivated',
                    description='Subscription reactivated',
                )

                messages.success(request, 'Your subscription has been reactivated!')
                return redirect('frontend:subscriptions:subscription')
            else:
                messages.error(request, f'Failed to reactivate subscription: {error}')
    else:
        form = ReactivateSubscriptionForm()

    context = {
        'subscription': subscription,
        'form': form,
    }
    return render(request, 'subscriptions/reactivate.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def change_plan_view(request):
    """
    Change subscription plan page.

    Template: subscriptions/change_plan.html
    URL: /subscriptions/change-plan/
    """
    subscription = getattr(request.user, 'subscription', None)

    if not subscription or not subscription.is_active:
        messages.info(request, 'No active subscription to change.')
        return redirect('frontend:subscriptions:pricing')

    if request.method == 'POST':
        form = ChangePlanForm(subscription.plan, request.POST)
        if form.is_valid():
            new_plan = form.cleaned_data['new_plan']
            billing_interval = form.cleaned_data['billing_interval']

            # Get appropriate price ID
            if billing_interval == 'year':
                price_id = new_plan.stripe_price_id_yearly
            else:
                price_id = new_plan.stripe_price_id_monthly

            if not price_id:
                messages.error(request, 'Plan pricing not configured.')
                return redirect('frontend:subscriptions:change-plan')

            success, error = stripe_service.update_subscription(
                subscription.stripe_subscription_id,
                price_id
            )

            if success:
                # Determine if upgrade or downgrade
                tier_order = ['free', 'premium', 'pro', 'business']
                old_index = tier_order.index(subscription.plan.tier) if subscription.plan.tier in tier_order else 0
                new_index = tier_order.index(new_plan.tier) if new_plan.tier in tier_order else 0
                event_type = 'upgraded' if new_index > old_index else 'downgraded'

                old_plan_name = subscription.plan.name
                subscription.plan = new_plan
                subscription.billing_interval = billing_interval
                subscription.save()

                request.user.subscription_tier = new_plan.tier
                request.user.save(update_fields=['subscription_tier'])

                SubscriptionEvent.objects.create(
                    subscription=subscription,
                    event_type=event_type,
                    description=f'Plan changed from {old_plan_name} to {new_plan.name}',
                    metadata={
                        'old_plan': old_plan_name,
                        'new_plan': new_plan.name,
                        'billing_interval': billing_interval,
                    }
                )

                messages.success(request, f'Your plan has been changed to {new_plan.name}!')
                return redirect('frontend:subscriptions:subscription')
            else:
                messages.error(request, f'Failed to change plan: {error}')
    else:
        form = ChangePlanForm(subscription.plan)

    plans = SubscriptionPlan.objects.filter(is_active=True).exclude(
        id=subscription.plan.id
    ).order_by('display_order')

    context = {
        'subscription': subscription,
        'form': form,
        'plans': plans,
    }
    return render(request, 'subscriptions/change_plan.html', context)


@login_required
def billing_portal_view(request):
    """
    Redirect to Stripe Billing Portal.

    URL: /subscriptions/billing-portal/
    """
    subscription = getattr(request.user, 'subscription', None)

    customer_id = None
    if subscription:
        customer_id = subscription.stripe_customer_id
    if not customer_id and hasattr(request.user, 'stripe_customer_id'):
        customer_id = request.user.stripe_customer_id

    if not customer_id:
        messages.error(request, 'No billing information found.')
        return redirect('frontend:subscriptions:subscription')

    return_url = request.build_absolute_uri(
        reverse('frontend:subscriptions:billing')
    )

    portal_url = stripe_service.create_billing_portal_session(
        customer_id=customer_id,
        return_url=return_url,
    )

    if portal_url:
        return HttpResponseRedirect(portal_url)
    else:
        messages.error(request, 'Failed to open billing portal.')
        return redirect('frontend:subscriptions:billing')


@login_required
def invoice_detail_view(request, invoice_id):
    """
    Invoice detail page.

    Template: subscriptions/invoice_detail.html
    URL: /subscriptions/invoices/{invoice_id}/
    """
    subscription = getattr(request.user, 'subscription', None)
    if not subscription:
        messages.error(request, 'No subscription found.')
        return redirect('frontend:subscriptions:subscription')

    invoice = get_object_or_404(Invoice, id=invoice_id, subscription=subscription)

    context = {
        'invoice': invoice,
        'subscription': subscription,
    }
    return render(request, 'subscriptions/invoice_detail.html', context)


@login_required
def subscription_events_view(request):
    """
    Subscription event history page.

    Template: subscriptions/events.html
    URL: /subscriptions/events/
    """
    subscription = getattr(request.user, 'subscription', None)
    events = []

    if subscription:
        events = subscription.events.all()[:50]

    context = {
        'subscription': subscription,
        'events': events,
    }
    return render(request, 'subscriptions/events.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def contact_support_view(request):
    """
    Contact support for billing inquiries.

    Template: subscriptions/contact_support.html
    URL: /subscriptions/support/
    """
    subscription = getattr(request.user, 'subscription', None)

    if request.method == 'POST':
        form = ContactSupportForm(request.POST)
        if form.is_valid():
            # In production, this would send an email or create a support ticket
            # For now, just show a success message
            messages.success(
                request,
                'Your inquiry has been submitted. We will respond within 24 hours.'
            )
            return redirect('frontend:subscriptions:billing')
    else:
        form = ContactSupportForm()

    context = {
        'subscription': subscription,
        'form': form,
    }
    return render(request, 'subscriptions/contact_support.html', context)


# HTMX Partial Views

@login_required
def htmx_subscription_status(request):
    """
    HTMX partial for subscription status display.

    Template: subscriptions/partials/subscription_status.html
    URL: /subscriptions/htmx/status/
    """
    subscription = getattr(request.user, 'subscription', None)
    context = {'subscription': subscription}
    return render(request, 'subscriptions/partials/subscription_status.html', context)


@login_required
def htmx_billing_summary(request):
    """
    HTMX partial for billing summary display.

    Template: subscriptions/partials/billing_summary.html
    URL: /subscriptions/htmx/billing-summary/
    """
    subscription = getattr(request.user, 'subscription', None)
    upcoming_invoice = None

    if subscription and subscription.stripe_customer_id:
        upcoming_invoice = stripe_service.get_upcoming_invoice(
            subscription.stripe_customer_id
        )

    context = {
        'subscription': subscription,
        'upcoming_invoice': upcoming_invoice,
    }
    return render(request, 'subscriptions/partials/billing_summary.html', context)


@login_required
def htmx_plan_comparison(request):
    """
    HTMX partial for plan comparison display.

    Template: subscriptions/partials/plan_comparison.html
    URL: /subscriptions/htmx/plan-comparison/
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
    current_plan = None

    if hasattr(request.user, 'subscription'):
        current_plan = request.user.subscription.plan

    context = {
        'plans': plans,
        'current_plan': current_plan,
    }
    return render(request, 'subscriptions/partials/plan_comparison.html', context)
