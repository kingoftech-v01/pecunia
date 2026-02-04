"""
Banking API Views.

DRF ViewSets and APIViews for bank connections and accounts.
"""
import secrets
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BankConnection, BankAccount, SyncLog
from .serializers import (
    BankConnectionSerializer,
    BankConnectionDetailSerializer,
    BankConnectionCreateSerializer,
    BankConnectionCallbackSerializer,
    BankAccountSerializer,
    BankAccountUpdateSerializer,
    BankAccountSummarySerializer,
    SyncLogSerializer,
    InstitutionSerializer,
    SyncRequestSerializer,
    BalanceAggregateSerializer,
    ConnectionStatusSerializer,
)
from .providers import get_provider, get_available_providers
from .providers.base import ProviderError, TokenExpiredError


class BankConnectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for bank connection operations.

    Endpoints:
    - GET /api/v1/banking/connections/ - List connections
    - POST /api/v1/banking/connections/ - Initiate connection
    - GET /api/v1/banking/connections/{id}/ - Connection details
    - DELETE /api/v1/banking/connections/{id}/ - Disconnect
    - POST /api/v1/banking/connections/{id}/sync/ - Trigger sync
    - GET /api/v1/banking/connections/{id}/status/ - Check status
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'retrieve':
            return BankConnectionDetailSerializer
        if self.action == 'create':
            return BankConnectionCreateSerializer
        return BankConnectionSerializer

    def get_queryset(self):
        """Return connections for current user."""
        return BankConnection.objects.filter(
            user=self.request.user
        ).prefetch_related('accounts')

    def create(self, request):
        """
        Initiate a new bank connection.

        Returns authorization URL for OAuth flow.
        """
        serializer = BankConnectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider_name = serializer.validated_data['provider']
        redirect_uri = serializer.validated_data['redirect_uri']
        institution_id = serializer.validated_data.get('institution_id')

        try:
            provider = get_provider(provider_name)

            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)

            # Store state in session for verification
            request.session[f'bank_oauth_state_{provider_name}'] = state
            request.session[f'bank_oauth_redirect_{provider_name}'] = redirect_uri

            # Get authorization URL
            auth_url = provider.get_authorization_url(
                redirect_uri=redirect_uri,
                state=state,
                institution_id=institution_id,
                user_id=str(request.user.id),
            )

            return Response({
                'authorization_url': auth_url,
                'state': state,
                'provider': provider_name,
            })

        except ProviderError as e:
            return Response(
                {'error': str(e), 'code': e.code},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """
        Disconnect a bank connection.

        Revokes access with provider and deletes local data.
        """
        connection = self.get_object()

        try:
            # Revoke access with provider
            provider = get_provider(connection.provider)
            provider.revoke_access(
                access_token=connection.access_token,
                connection_id=connection.provider_connection_id
            )
        except (ProviderError, Exception):
            # Continue with deletion even if revocation fails
            pass

        # Delete connection and cascade to accounts
        connection.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger a manual sync for a connection."""
        connection = self.get_object()

        serializer = SyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sync_type = serializer.validated_data.get('sync_type', 'incremental')

        # Create sync log
        sync_log = SyncLog.objects.create(
            connection=connection,
            sync_type=sync_type,
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
                        'user': request.user,
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

            # Update sync log
            sync_log.status = 'success'
            sync_log.accounts_synced = accounts_synced
            sync_log.completed_at = timezone.now()
            sync_log.save()

            # Update connection status
            connection.mark_sync_success()

            return Response({
                'status': 'success',
                'accounts_synced': accounts_synced,
                'sync_log_id': str(sync_log.id),
            })

        except TokenExpiredError:
            connection.status = 'expired'
            connection.save()
            sync_log.status = 'failed'
            sync_log.error_message = 'Token expired - reauthorization required'
            sync_log.completed_at = timezone.now()
            sync_log.save()

            return Response(
                {'error': 'Token expired', 'needs_reauthorization': True},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except ProviderError as e:
            connection.mark_sync_error(str(e))
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.completed_at = timezone.now()
            sync_log.save()

            return Response(
                {'error': str(e), 'code': e.code},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get current status of a connection."""
        connection = self.get_object()

        serializer = ConnectionStatusSerializer({
            'connection_id': connection.id,
            'status': connection.status,
            'is_healthy': connection.status == 'active',
            'needs_reauthorization': connection.needs_reauthorization,
            'last_sync_at': connection.last_sync_at,
            'error_message': connection.status_message,
        })

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def providers(self, request):
        """Get list of available providers."""
        providers = []
        for provider_name in get_available_providers():
            provider = get_provider(provider_name)
            providers.append({
                'name': provider.provider_name,
                'display_name': provider.display_name,
                'supported_countries': provider.supported_countries,
            })
        return Response(providers)


class BankConnectionCallbackView(APIView):
    """
    Handle OAuth callback from banking providers.

    POST /api/v1/banking/callback/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Process OAuth callback and complete connection."""
        serializer = BankConnectionCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        state = serializer.validated_data['state']
        redirect_uri = serializer.validated_data['redirect_uri']
        provider_name = serializer.validated_data['provider']

        # Verify state
        stored_state = request.session.get(f'bank_oauth_state_{provider_name}')
        if not stored_state or stored_state != state:
            return Response(
                {'error': 'Invalid state parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
            request.session.pop(f'bank_oauth_state_{provider_name}', None)
            request.session.pop(f'bank_oauth_redirect_{provider_name}', None)

            return Response({
                'connection': BankConnectionSerializer(connection).data,
                'created': created,
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except ProviderError as e:
            return Response(
                {'error': str(e), 'code': e.code},
                status=status.HTTP_400_BAD_REQUEST
            )


class BankAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for bank account operations.

    Endpoints:
    - GET /api/v1/banking/accounts/ - List accounts
    - GET /api/v1/banking/accounts/{id}/ - Account details
    - PATCH /api/v1/banking/accounts/{id}/ - Update settings
    - GET /api/v1/banking/accounts/summary/ - Balance summary
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['update', 'partial_update']:
            return BankAccountUpdateSerializer
        if self.action == 'summary':
            return BankAccountSummarySerializer
        return BankAccountSerializer

    def get_queryset(self):
        """Return accounts for current user."""
        queryset = BankAccount.objects.filter(
            user=self.request.user
        ).select_related('connection')

        # Filter by hidden status
        include_hidden = self.request.query_params.get('include_hidden', 'false')
        if include_hidden.lower() != 'true':
            queryset = queryset.filter(is_hidden=False)

        # Filter by account type
        account_type = self.request.query_params.get('type')
        if account_type:
            queryset = queryset.filter(account_type=account_type)

        # Filter by connection
        connection_id = self.request.query_params.get('connection')
        if connection_id:
            queryset = queryset.filter(connection_id=connection_id)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get aggregated balance summary."""
        accounts = self.get_queryset()

        # Calculate totals
        total_balance = accounts.aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0')

        total_available = accounts.aggregate(
            total=Sum('available_balance')
        )['total']

        # Group by type
        by_type = {}
        for acc in accounts:
            type_name = acc.account_type
            by_type[type_name] = by_type.get(type_name, Decimal('0')) + acc.balance

        # Group by institution
        by_institution = {}
        for acc in accounts:
            inst_name = acc.institution_name
            by_institution[inst_name] = by_institution.get(
                inst_name, Decimal('0')
            ) + acc.balance

        # Get primary currency (most common or user preference)
        currency = request.user.preferred_currency

        serializer = BalanceAggregateSerializer({
            'total_balance': total_balance,
            'total_available': total_available,
            'currency': currency,
            'accounts_count': accounts.count(),
            'by_type': by_type,
            'by_institution': by_institution,
        })

        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def refresh_balance(self, request, pk=None):
        """Refresh balance for a specific account."""
        account = self.get_object()
        connection = account.connection

        try:
            provider = get_provider(connection.provider)

            # Check if token needs refresh
            if connection.is_token_expired and connection.refresh_token:
                result = provider.refresh_access_token(connection.refresh_token)
                connection.access_token = result.access_token
                connection.save()

            # Get balance
            balance_data = provider.get_balance(
                access_token=connection.access_token,
                account_id=account.provider_account_id
            )

            account.update_balance(
                balance=balance_data['balance'],
                available_balance=balance_data.get('available_balance')
            )

            return Response(BankAccountSerializer(account).data)

        except ProviderError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class InstitutionSearchView(APIView):
    """
    Search for available banking institutions.

    GET /api/v1/banking/institutions/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Search for institutions by provider."""
        provider_name = request.query_params.get('provider')
        country = request.query_params.get('country')
        search = request.query_params.get('search')

        if not provider_name:
            return Response(
                {'error': 'Provider parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            provider = get_provider(provider_name)
            institutions = provider.get_institutions(
                country=country,
                search=search
            )

            # Limit results
            institutions = institutions[:50]

            serializer = InstitutionSerializer(institutions, many=True)
            return Response(serializer.data)

        except ProviderError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for sync log viewing.

    Endpoints:
    - GET /api/v1/banking/sync-logs/ - List sync logs
    - GET /api/v1/banking/sync-logs/{id}/ - Sync log details
    """
    serializer_class = SyncLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return sync logs for user's connections."""
        return SyncLog.objects.filter(
            connection__user=self.request.user
        ).select_related('connection').order_by('-started_at')


class SyncAllView(APIView):
    """
    Trigger sync for all user's connections.

    POST /api/v1/banking/sync-all/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Sync all active connections."""
        connections = BankConnection.objects.filter(
            user=request.user,
            status='active'
        )

        results = []
        for connection in connections:
            try:
                provider = get_provider(connection.provider)

                # Simple balance sync
                accounts = provider.get_accounts(
                    access_token=connection.access_token,
                    connection_id=connection.provider_connection_id
                )

                for acc_data in accounts:
                    BankAccount.objects.filter(
                        connection=connection,
                        provider_account_id=acc_data.provider_account_id
                    ).update(
                        balance=acc_data.balance,
                        available_balance=acc_data.available_balance,
                        balance_updated_at=timezone.now(),
                        last_sync_at=timezone.now(),
                    )

                connection.mark_sync_success()
                results.append({
                    'connection_id': str(connection.id),
                    'status': 'success',
                })

            except Exception as e:
                connection.mark_sync_error(str(e))
                results.append({
                    'connection_id': str(connection.id),
                    'status': 'error',
                    'error': str(e),
                })

        return Response({
            'synced': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] == 'error']),
            'results': results,
        })
