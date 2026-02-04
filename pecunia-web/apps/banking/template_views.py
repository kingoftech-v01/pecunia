"""
Banking Template Views (Frontend).

Django views for HTML pages with HTMX/Alpine.js support.
"""
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from .models import BankConnection, BankAccount, SyncLog
from .forms import (
    ConnectBankForm,
    InstitutionSearchForm,
    BankAccountSettingsForm,
    DisconnectBankForm,
    SyncOptionsForm,
)
from .providers import get_provider, get_available_providers
from .providers.base import ProviderError


@login_required
def connections_list_view(request):
    """
    List all bank connections.

    Template: banking/connections_list.html
    URL: /banking/
    """
    connections = BankConnection.objects.filter(
        user=request.user
    ).prefetch_related('accounts')

    # Calculate totals
    total_balance = sum(
        acc.balance for conn in connections
        for acc in conn.accounts.filter(is_hidden=False)
    )

    context = {
        'connections': connections,
        'total_balance': total_balance,
        'currency': request.user.preferred_currency,
    }

    return render(request, 'banking/connections_list.html', context)


@login_required
def connection_detail_view(request, connection_id):
    """
    View connection details and accounts.

    Template: banking/connection_detail.html
    URL: /banking/connections/<uuid:connection_id>/
    """
    connection = get_object_or_404(
        BankConnection,
        id=connection_id,
        user=request.user
    )

    accounts = connection.accounts.all()
    sync_logs = SyncLog.objects.filter(
        connection=connection
    ).order_by('-started_at')[:10]

    context = {
        'connection': connection,
        'accounts': accounts,
        'sync_logs': sync_logs,
    }

    return render(request, 'banking/connection_detail.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def connect_bank_view(request):
    """
    Initiate a new bank connection.

    Template: banking/connect_bank.html
    URL: /banking/connect/
    """
    if request.method == 'POST':
        form = ConnectBankForm(request.POST)
        if form.is_valid():
            provider_name = form.cleaned_data['provider']
            institution_id = form.cleaned_data.get('institution_id')

            try:
                provider = get_provider(provider_name)

                # Generate state for CSRF protection
                state = secrets.token_urlsafe(32)

                # Build redirect URI
                redirect_uri = request.build_absolute_uri('/banking/callback/')

                # Store state in session
                request.session['bank_oauth_state'] = state
                request.session['bank_oauth_provider'] = provider_name
                request.session['bank_oauth_redirect'] = redirect_uri

                # Get authorization URL
                auth_url = provider.get_authorization_url(
                    redirect_uri=redirect_uri,
                    state=state,
                    institution_id=institution_id,
                    user_id=str(request.user.id),
                )

                return redirect(auth_url)

            except ProviderError as e:
                messages.error(request, f'Connection error: {str(e)}')
    else:
        form = ConnectBankForm()

    # Get available providers
    providers = []
    for provider_name in get_available_providers():
        provider = get_provider(provider_name)
        providers.append({
            'name': provider.provider_name,
            'display_name': provider.display_name,
            'countries': provider.supported_countries,
        })

    context = {
        'form': form,
        'providers': providers,
    }

    return render(request, 'banking/connect_bank.html', context)


@login_required
def oauth_callback_view(request):
    """
    Handle OAuth callback from banking providers.

    URL: /banking/callback/
    """
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    # Handle error from provider
    if error:
        messages.error(request, f'Bank connection was cancelled or failed: {error}')
        return redirect('banking:connect')

    # Verify state
    stored_state = request.session.get('bank_oauth_state')
    if not stored_state or stored_state != state:
        messages.error(request, 'Invalid request. Please try again.')
        return redirect('banking:connect')

    provider_name = request.session.get('bank_oauth_provider')
    redirect_uri = request.session.get('bank_oauth_redirect')

    try:
        provider = get_provider(provider_name)

        # Exchange code for tokens
        result = provider.exchange_code(code=code, redirect_uri=redirect_uri)

        # Create or update connection
        connection, created = BankConnection.objects.update_or_create(
            user=request.user,
            provider=provider_name,
            institution_id=result.institution_id or 'unknown',
            defaults={
                'institution_name': result.institution_name or 'Unknown Bank',
                'institution_logo_url': result.institution_logo_url,
                'provider_connection_id': result.provider_connection_id or '',
                'token_expires_at': result.token_expires_at,
                'consent_expires_at': result.consent_expires_at,
                'status': 'active',
            }
        )

        # Set encrypted tokens
        connection.access_token = result.access_token
        if result.refresh_token:
            connection.refresh_token = result.refresh_token
        connection.save()

        # Clean up session
        request.session.pop('bank_oauth_state', None)
        request.session.pop('bank_oauth_provider', None)
        request.session.pop('bank_oauth_redirect', None)

        # Trigger initial sync
        _sync_connection(connection, request.user)

        if created:
            messages.success(request, f'Successfully connected to {connection.institution_name}!')
        else:
            messages.success(request, f'Reconnected to {connection.institution_name}!')

        return redirect('banking:connection-detail', connection_id=connection.id)

    except ProviderError as e:
        messages.error(request, f'Connection failed: {str(e)}')
        return redirect('banking:connect')


@login_required
@require_http_methods(['POST'])
def disconnect_bank_view(request, connection_id):
    """
    Disconnect a bank connection.

    URL: /banking/connections/<uuid:connection_id>/disconnect/
    """
    connection = get_object_or_404(
        BankConnection,
        id=connection_id,
        user=request.user
    )

    form = DisconnectBankForm(request.POST)
    if form.is_valid():
        institution_name = connection.institution_name

        try:
            # Revoke access with provider
            provider = get_provider(connection.provider)
            provider.revoke_access(
                access_token=connection.access_token,
                connection_id=connection.provider_connection_id
            )
        except (ProviderError, Exception):
            pass  # Continue with deletion

        connection.delete()
        messages.success(request, f'Disconnected from {institution_name}.')
        return redirect('banking:connections')

    messages.error(request, 'Please confirm disconnection.')
    return redirect('banking:connection-detail', connection_id=connection_id)


@login_required
def accounts_list_view(request):
    """
    List all bank accounts.

    Template: banking/accounts_list.html
    URL: /banking/accounts/
    """
    accounts = BankAccount.objects.filter(
        user=request.user
    ).select_related('connection')

    # Filter options
    show_hidden = request.GET.get('show_hidden', 'false') == 'true'
    if not show_hidden:
        accounts = accounts.filter(is_hidden=False)

    account_type = request.GET.get('type')
    if account_type:
        accounts = accounts.filter(account_type=account_type)

    # Calculate totals
    total_balance = sum(acc.balance for acc in accounts)

    # Group by type
    by_type = {}
    for acc in accounts:
        if acc.account_type not in by_type:
            by_type[acc.account_type] = []
        by_type[acc.account_type].append(acc)

    context = {
        'accounts': accounts,
        'by_type': by_type,
        'total_balance': total_balance,
        'currency': request.user.preferred_currency,
        'show_hidden': show_hidden,
        'selected_type': account_type,
    }

    return render(request, 'banking/accounts_list.html', context)


@login_required
def account_detail_view(request, account_id):
    """
    View account details.

    Template: banking/account_detail.html
    URL: /banking/accounts/<uuid:account_id>/
    """
    account = get_object_or_404(
        BankAccount,
        id=account_id,
        user=request.user
    )

    context = {
        'account': account,
        'connection': account.connection,
    }

    return render(request, 'banking/account_detail.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def account_settings_view(request, account_id):
    """
    Edit account settings.

    Template: banking/account_settings.html
    URL: /banking/accounts/<uuid:account_id>/settings/
    """
    account = get_object_or_404(
        BankAccount,
        id=account_id,
        user=request.user
    )

    if request.method == 'POST':
        form = BankAccountSettingsForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account settings updated.')

            # HTMX support
            if request.headers.get('HX-Request'):
                return render(request, 'banking/partials/account_settings_success.html')
            return redirect('banking:account-detail', account_id=account_id)
    else:
        form = BankAccountSettingsForm(instance=account)

    context = {
        'form': form,
        'account': account,
    }

    return render(request, 'banking/account_settings.html', context)


@login_required
@require_http_methods(['POST'])
def sync_connection_view(request, connection_id):
    """
    Trigger sync for a connection.

    URL: /banking/connections/<uuid:connection_id>/sync/
    """
    connection = get_object_or_404(
        BankConnection,
        id=connection_id,
        user=request.user
    )

    success = _sync_connection(connection, request.user)

    if request.headers.get('HX-Request'):
        # Return partial for HTMX
        return render(request, 'banking/partials/connection_sync_result.html', {
            'connection': connection,
            'success': success,
        })

    if success:
        messages.success(request, f'Synced {connection.institution_name} successfully.')
    else:
        messages.error(request, f'Sync failed for {connection.institution_name}.')

    return redirect('banking:connection-detail', connection_id=connection_id)


@login_required
@require_http_methods(['POST'])
def sync_all_view(request):
    """
    Sync all connections.

    URL: /banking/sync-all/
    """
    form = SyncOptionsForm(
        request.POST,
        connections=BankConnection.objects.filter(user=request.user, status='active')
    )

    if form.is_valid():
        connection_ids = form.cleaned_data.get('connection_ids')
        sync_type = form.cleaned_data.get('sync_type', 'incremental')

        if connection_ids:
            connections = BankConnection.objects.filter(
                id__in=connection_ids,
                user=request.user
            )
        else:
            connections = BankConnection.objects.filter(
                user=request.user,
                status='active'
            )

        success_count = 0
        for connection in connections:
            if _sync_connection(connection, request.user):
                success_count += 1

        messages.success(request, f'Synced {success_count} of {connections.count()} connections.')
    else:
        messages.error(request, 'Invalid sync request.')

    return redirect('banking:connections')


@login_required
def institution_search_view(request):
    """
    Search for institutions (HTMX partial).

    Template: banking/partials/institution_list.html
    URL: /banking/institutions/search/
    """
    form = InstitutionSearchForm(request.GET)

    institutions = []
    if form.is_valid():
        provider_name = form.cleaned_data.get('provider')
        search = form.cleaned_data.get('search')
        country = form.cleaned_data.get('country')

        if provider_name:
            try:
                provider = get_provider(provider_name)
                institutions = provider.get_institutions(
                    country=country,
                    search=search
                )[:20]  # Limit results
            except ProviderError:
                pass

    return render(request, 'banking/partials/institution_list.html', {
        'institutions': institutions,
    })


@login_required
def sync_logs_view(request, connection_id=None):
    """
    View sync history.

    Template: banking/sync_logs.html
    URL: /banking/sync-logs/ or /banking/connections/<uuid:connection_id>/logs/
    """
    logs = SyncLog.objects.filter(
        connection__user=request.user
    ).select_related('connection').order_by('-started_at')

    if connection_id:
        logs = logs.filter(connection_id=connection_id)
        connection = get_object_or_404(
            BankConnection,
            id=connection_id,
            user=request.user
        )
    else:
        connection = None

    logs = logs[:50]  # Limit results

    context = {
        'logs': logs,
        'connection': connection,
    }

    return render(request, 'banking/sync_logs.html', context)


def _sync_connection(connection, user):
    """
    Helper function to sync a connection.

    Returns True if sync was successful.
    """
    sync_log = SyncLog.objects.create(
        connection=connection,
        sync_type='incremental',
        status='started'
    )

    try:
        provider = get_provider(connection.provider)

        # Check if token needs refresh
        if connection.is_token_expired and connection.refresh_token:
            result = provider.refresh_access_token(connection.refresh_token)
            connection.access_token = result.access_token
            if result.refresh_token:
                connection.refresh_token = result.refresh_token
            connection.token_expires_at = result.token_expires_at
            connection.save()

        # Fetch accounts
        accounts = provider.get_accounts(
            access_token=connection.access_token,
            connection_id=connection.provider_connection_id
        )

        accounts_synced = 0
        for acc_data in accounts:
            account, created = BankAccount.objects.update_or_create(
                connection=connection,
                provider_account_id=acc_data.provider_account_id,
                defaults={
                    'user': user,
                    'name': acc_data.name,
                    'official_name': acc_data.official_name or '',
                    'account_type': acc_data.account_type,
                    'account_subtype': acc_data.account_subtype or '',
                    'account_number_masked': acc_data.account_number_masked or '',
                    'iban_masked': acc_data.iban_masked or '',
                    'balance': acc_data.balance,
                    'available_balance': acc_data.available_balance,
                    'credit_limit': acc_data.credit_limit,
                    'currency': acc_data.currency,
                    'last_sync_at': timezone.now(),
                    'balance_updated_at': timezone.now(),
                }
            )
            accounts_synced += 1

        sync_log.status = 'success'
        sync_log.accounts_synced = accounts_synced
        sync_log.completed_at = timezone.now()
        sync_log.save()

        connection.mark_sync_success()
        return True

    except Exception as e:
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        sync_log.completed_at = timezone.now()
        sync_log.save()

        connection.mark_sync_error(str(e))
        return False
