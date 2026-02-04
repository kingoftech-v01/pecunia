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
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import logout

from .models import User, UserProfile
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)


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

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
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
                token.blacklist()
            return Response({'detail': 'Successfully logged out.'})
        except Exception:
            return Response(
                {'detail': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user CRUD operations.

    Endpoints:
    - GET /api/v1/accounts/users/me/ - Current user details
    - PATCH /api/v1/accounts/users/me/ - Update current user
    - POST /api/v1/accounts/users/me/change-password/ - Change password
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

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
        """Change user password."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response({'detail': 'Password changed successfully.'})


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
