"""
Accounts API Views.

DRF ViewSets and APIViews for user authentication and profile management.

This module provides the authentication endpoints for the Pecunia:

Authentication Flow:
--------------------
1. Registration:
   POST /api/v1/accounts/register/
   - Creates user account
   - Returns JWT access + refresh tokens
   - Access token valid for 60 minutes (configurable)
   - Refresh token valid for 7 days (configurable)

2. Login:
   POST /api/v1/accounts/login/
   - Validates email/password
   - Returns new JWT token pair
   - Previous tokens remain valid until expiry

3. Token Refresh:
   POST /api/v1/accounts/token/refresh/
   - Exchanges refresh token for new access token
   - Implements token rotation (new refresh token issued)

4. Logout:
   POST /api/v1/accounts/logout/
   - Blacklists the refresh token
   - Access token remains valid until expiry
   - Client should discard both tokens

Security Considerations:
------------------------
- Passwords hashed with Argon2 (Django default)
- JWT tokens signed with HS256 (configurable)
- Token blacklisting enabled for secure logout
- Account lockout after 5 failed attempts (configured in settings)

Rate Limiting (TODO):
--------------------
Auth endpoints should have stricter rate limits:
- Register: 3/hour per IP
- Login: 5/minute per IP
- Token refresh: 10/minute per user

See SECURITY_GUIDELINES.md for complete auth requirements.

Related:
- Simple JWT configuration in settings.py
- Token storage requirements in SECURITY_GUIDELINES.md
- Client implementations in desktop/mobile apps
"""
import logging

from rest_framework import viewsets, status, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import logout

from .models import User, UserProfile
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)
from .totp import TOTPService

logger = logging.getLogger(__name__)


class RegisterAPIView(APIView):
    """
    API endpoint for user registration.

    POST /api/v1/accounts/register/
    Creates a new user account and returns JWT tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Create a new user account."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Do not issue full JWT tokens until email is verified.
        # Return user data with a message to verify email.
        return Response({
            'user': UserSerializer(user).data,
            'detail': 'Account created. Please verify your email address before logging in.',
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """
    API endpoint for user login.

    POST /api/v1/accounts/login/
    Authenticates user and returns JWT tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Authenticate user and return tokens."""
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Check if 2FA is enabled for this user
        totp_service = TOTPService()
        if totp_service.is_2fa_enabled(user):
            totp_code = request.data.get('totp_code')
            if not totp_code:
                # 2FA is required but no code provided - return partial auth
                return Response({
                    'requires_2fa': True,
                    'detail': 'Two-factor authentication code required.',
                }, status=status.HTTP_200_OK)

            if not totp_service.verify_token(user, totp_code):
                return Response({
                    'detail': 'Invalid two-factor authentication code.',
                }, status=status.HTTP_401_UNAUTHORIZED)

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class LogoutAPIView(APIView):
    """
    API endpoint for user logout.

    POST /api/v1/accounts/logout/
    Blacklists the refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Logout user by blacklisting refresh token."""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                # Validate that the token belongs to the authenticated user
                user_id = token.payload.get('user_id')
                if str(user_id) != str(request.user.id):
                    return Response(
                        {'detail': 'Token does not belong to the authenticated user.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                token.blacklist()
            return Response({'detail': 'Successfully logged out.'})
        except TokenError:
            return Response(
                {'detail': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet for user read/update operations.

    Endpoints:
    - GET /api/v1/accounts/users/me/ - Current user details
    - PATCH /api/v1/accounts/users/me/ - Update current user
    - POST /api/v1/accounts/users/me/change-password/ - Change password
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def get_queryset(self):
        """Return only the current user."""
        return User.objects.filter(id=self.request.user.id)

    def get_object(self):
        """Return the current user."""
        return self.request.user

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get or update current user details."""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='me/change-password')
    def change_password(self, request):
        """Change user password and invalidate existing tokens."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        # Invalidate all existing refresh tokens for this user
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        OutstandingToken.objects.filter(user=request.user).delete()

        # Issue new tokens
        refresh = RefreshToken.for_user(request.user)

        return Response({
            'detail': 'Password changed successfully. All sessions invalidated.',
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user profile operations.

    Endpoints:
    - GET /api/v1/accounts/profile/ - Get profile
    - PATCH /api/v1/accounts/profile/ - Update profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return the current user's profile."""
        return UserProfile.objects.filter(user=self.request.user)

    def get_object(self):
        """Return the current user's profile."""
        return self.request.user.profile

    def list(self, request):
        """Get current user's profile."""
        serializer = self.get_serializer(request.user.profile)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Update current user's profile."""
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(
            request.user.profile,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
