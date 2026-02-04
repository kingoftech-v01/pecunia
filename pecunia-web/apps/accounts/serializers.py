"""
Accounts Serializers.

DRF serializers for user authentication and profile management.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Handles creation of new users with password validation.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'preferred_currency'
        ]

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return attrs

    def create(self, validated_data):
        """Create a new user with the validated data."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.

    Authenticates user credentials and returns tokens.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate user credentials."""
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError({
                'detail': "Invalid email or password."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'detail': "User account is disabled."
            })

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user details.

    Read/update operations for user information.
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'subscription_tier', 'preferred_currency',
            'is_email_verified', 'date_joined', 'last_login'
        ]
        read_only_fields = [
            'id', 'email', 'subscription_tier',
            'is_email_verified', 'date_joined', 'last_login'
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile preferences.

    Handles notification and display settings.
    """

    class Meta:
        model = UserProfile
        fields = [
            'email_notifications', 'push_notifications',
            'weekly_summary', 'budget_alerts',
            'theme', 'language', 'date_format',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.

    Validates current password and new password.
    """
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate passwords."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords do not match."
            })
        return attrs

    def validate_current_password(self, value):
        """Validate current password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
