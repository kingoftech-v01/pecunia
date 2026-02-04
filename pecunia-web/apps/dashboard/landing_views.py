"""
Landing Page Views.

Public-facing views for the landing page and marketing pages.
These views are accessible without authentication.
"""
from django.shortcuts import render
from django.views.decorators.cache import cache_page


def landing_home(request):
    """
    Landing page home view.

    Displays the main marketing page with:
    - Hero section
    - Features overview
    - Pricing preview
    - Testimonials
    - Call to action
    """
    # If user is authenticated, redirect to dashboard
    if request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('dashboard:home')

    context = {
        'page_title': 'Smart Personal Finance Management',
    }
    return render(request, 'landing/index.html', context)


def features_page(request):
    """
    Features page view.

    Displays detailed information about all features:
    - Core features
    - Advanced features
    - Security information
    """
    context = {
        'page_title': 'Features',
    }
    return render(request, 'landing/features.html', context)


def pricing_page(request):
    """
    Pricing page view.

    Displays detailed pricing information and plan comparison.
    """
    plans = [
        {
            'name': 'Free',
            'price': 0,
            'period': 'month',
            'description': 'Perfect for getting started',
            'features': [
                '2 bank accounts',
                'Basic budgeting',
                '30-day transaction history',
                'Email support',
            ],
            'limitations': [
                'No AI insights',
                'No custom categories',
                'No data export',
            ],
            'cta': 'Get Started',
            'cta_url': '/accounts/register/',
            'highlighted': False,
        },
        {
            'name': 'Pro',
            'price': 9,
            'period': 'month',
            'description': 'For serious budgeters',
            'features': [
                'Unlimited bank accounts',
                'Advanced budgeting',
                'Full transaction history',
                'AI-powered insights',
                'Custom categories',
                'Data export (CSV, PDF)',
                'Priority email support',
            ],
            'limitations': [],
            'cta': 'Start Free Trial',
            'cta_url': '/accounts/register/?plan=pro',
            'highlighted': True,
        },
        {
            'name': 'Business',
            'price': 29,
            'period': 'month',
            'description': 'For teams and families',
            'features': [
                'Everything in Pro',
                'Up to 5 users',
                'Shared budgets',
                'Team dashboard',
                'API access',
                'Phone support',
                'Dedicated account manager',
            ],
            'limitations': [],
            'cta': 'Contact Sales',
            'cta_url': '/contact/',
            'highlighted': False,
        },
    ]

    context = {
        'page_title': 'Pricing',
        'plans': plans,
    }
    return render(request, 'landing/pricing.html', context)


def about_page(request):
    """
    About page view.

    Displays information about the company and team.
    """
    context = {
        'page_title': 'About Us',
    }
    return render(request, 'landing/about.html', context)


def contact_page(request):
    """
    Contact page view.

    Displays contact form and information.
    """
    context = {
        'page_title': 'Contact Us',
    }
    return render(request, 'landing/contact.html', context)


def privacy_page(request):
    """
    Privacy policy page view.
    """
    context = {
        'page_title': 'Privacy Policy',
    }
    return render(request, 'landing/privacy.html', context)


def terms_page(request):
    """
    Terms of service page view.
    """
    context = {
        'page_title': 'Terms of Service',
    }
    return render(request, 'landing/terms.html', context)
