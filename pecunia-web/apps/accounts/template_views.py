"""
Accounts Template Views (Frontend).

Django views for HTML pages with HTMX/Alpine.js support.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserUpdateForm,
    UserProfileForm,
    ChangePasswordForm,
)


def register_view(request):
    """
    User registration page.

    Template: accounts/register.html
    URL: /register/
    """
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('frontend:dashboard')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    User login page.

    Template: accounts/login.html
    URL: /login/
    """
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'frontend:dashboard')
            return redirect(next_url)
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """
    User logout.

    URL: /logout/
    """
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('frontend:login')


@login_required
def profile_view(request):
    """
    User profile page.

    Template: accounts/profile.html
    URL: /profile/
    """
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'profile': request.user.profile,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def profile_edit_view(request):
    """
    Edit user profile page.

    Template: accounts/profile_edit.html
    URL: /profile/edit/
    """
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')

            # HTMX support
            if request.headers.get('HX-Request'):
                return render(request, 'accounts/partials/profile_success.html')
            return redirect('frontend:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)

    return render(request, 'accounts/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def change_password_view(request):
    """
    Change password page.

    Template: accounts/change_password.html
    URL: /profile/change-password/
    """
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('frontend:profile')
    else:
        form = ChangePasswordForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def settings_view(request):
    """
    User settings page.

    Template: accounts/settings.html
    URL: /settings/
    """
    return render(request, 'accounts/settings.html', {
        'user': request.user,
        'profile': request.user.profile,
    })


def dashboard_view(request):
    """
    Main dashboard page.

    Template: accounts/dashboard.html
    URL: /dashboard/
    """
    if not request.user.is_authenticated:
        return redirect('frontend:login')

    context = {
        'user': request.user,
    }
    return render(request, 'accounts/dashboard.html', context)
