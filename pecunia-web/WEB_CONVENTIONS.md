# Web Platform Conventions - Pecunia Django

**Version**: 2.0
**Last Updated**: 2026-01-28
**Extends**: [URL_AND_VIEW_CONVENTIONS.md](../URL_AND_VIEW_CONVENTIONS.md)
**Status**: MANDATORY for all Django development

---

## Table of Contents

1. [Django App Structure](#1-django-app-structure)
2. [Model Conventions](#2-model-conventions)
3. [Serializer Patterns](#3-serializer-patterns)
4. [View Conventions](#4-view-conventions)
5. [URL Configuration](#5-url-configuration)
6. [Form Conventions](#6-form-conventions)
7. [Admin Configuration](#7-admin-configuration)
8. [Celery Tasks](#8-celery-tasks)
9. [Signal Handlers](#9-signal-handlers)
10. [Testing Standards](#10-testing-standards)
11. [Error Handling](#11-error-handling)
12. [Logging Patterns](#12-logging-patterns)

---

## 1. Django App Structure

### Mandatory File Structure

Every Django app MUST have this structure:

```
apps/<app_name>/
├── __init__.py              # Empty or app initialization
├── admin.py                 # Admin site configuration
├── apps.py                  # App configuration class
├── forms.py                 # Django forms (ModelForms, Forms)
├── models.py                # Database models
├── serializers.py           # DRF serializers
├── signals.py               # Signal handlers
├── tasks.py                 # Celery background tasks
├── template_views.py        # Frontend HTML views
├── urls.py                  # URL routing
├── views.py                 # API views (DRF)
├── permissions.py           # Custom DRF permissions (if needed)
├── filters.py               # Custom filters (if needed)
├── exceptions.py            # Custom exceptions (if needed)
├── services.py              # Business logic services (if needed)
├── templates/
│   └── <app_name>/
│       ├── list.html
│       ├── detail.html
│       ├── form.html
│       └── confirm_delete.html
└── tests/
    ├── __init__.py
    ├── conftest.py          # pytest fixtures
    ├── factories.py         # Model factories
    ├── test_models.py
    ├── test_views.py
    ├── test_serializers.py
    └── test_tasks.py
```

### File Purposes

| File | Purpose | Required |
|------|---------|----------|
| `admin.py` | Admin site registration and customization | Yes |
| `apps.py` | App configuration and signals | Yes |
| `forms.py` | Django forms for template views | Yes |
| `models.py` | Database models | Yes |
| `serializers.py` | DRF serializers for API | Yes |
| `signals.py` | Post-save, pre-delete handlers | If needed |
| `tasks.py` | Celery background tasks | If needed |
| `template_views.py` | HTML template views | Yes |
| `urls.py` | URL patterns (API + Frontend) | Yes |
| `views.py` | DRF API views | Yes |
| `services.py` | Complex business logic | If needed |
| `permissions.py` | Custom DRF permissions | If needed |

---

## 2. Model Conventions

### Model Template

```python
"""
<App Name> Models - Database models for <description>.

This module defines:
- <Model1>: <brief description>
- <Model2>: <brief description>
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ModelName(models.Model):
    """
    <Model description>.

    <Detailed explanation of purpose and business logic.>

    Attributes:
        id: UUID primary key.
        user: Owner of this record.
        name: Display name.
        status: Current status (active, archived, deleted).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.

    Relationships:
        - user: ForeignKey to User (CASCADE)
        - category: ForeignKey to Category (SET_NULL)
    """

    # ==========================================================================
    # CHOICES
    # ==========================================================================

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')
        DELETED = 'deleted', _('Deleted')

    # ==========================================================================
    # PRIMARY KEY
    # ==========================================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier')
    )

    # ==========================================================================
    # FOREIGN KEYS
    # ==========================================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='model_names',
        help_text=_('Owner of this record')
    )

    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='model_names',
        help_text=_('Associated category')
    )

    # ==========================================================================
    # REQUIRED FIELDS
    # ==========================================================================

    name = models.CharField(
        max_length=255,
        help_text=_('Display name')
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_('Monetary amount')
    )

    # ==========================================================================
    # OPTIONAL FIELDS
    # ==========================================================================

    description = models.TextField(
        blank=True,
        default='',
        help_text=_('Optional description')
    )

    notes = models.TextField(
        blank=True,
        default='',
        help_text=_('Internal notes')
    )

    # ==========================================================================
    # STATUS AND TYPE FIELDS
    # ==========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text=_('Current status')
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_('Whether this record is active')
    )

    # ==========================================================================
    # METADATA FIELDS
    # ==========================================================================

    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of tags')
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional metadata')
    )

    # ==========================================================================
    # TIMESTAMPS
    # ==========================================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Record creation timestamp')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_('Last modification timestamp')
    )

    # ==========================================================================
    # META
    # ==========================================================================

    class Meta:
        verbose_name = _('model name')
        verbose_name_plural = _('model names')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='ix_model_user_created'),
            models.Index(fields=['user', 'status'], name='ix_model_user_status'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name='model_amount_non_negative'
            ),
        ]

    # ==========================================================================
    # STRING REPRESENTATION
    # ==========================================================================

    def __str__(self) -> str:
        return f"{self.name} ({self.user.email})"

    # ==========================================================================
    # PROPERTIES
    # ==========================================================================

    @property
    def is_archived(self) -> bool:
        """Check if record is archived."""
        return self.status == self.Status.ARCHIVED

    @property
    def display_amount(self) -> str:
        """Format amount for display."""
        return f"${self.amount:,.2f}"

    # ==========================================================================
    # INSTANCE METHODS
    # ==========================================================================

    def archive(self) -> None:
        """Archive this record."""
        self.status = self.Status.ARCHIVED
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])

    def restore(self) -> None:
        """Restore archived record."""
        self.status = self.Status.ACTIVE
        self.is_active = True
        self.save(update_fields=['status', 'is_active', 'updated_at'])

    def soft_delete(self) -> None:
        """Soft delete this record."""
        self.status = self.Status.DELETED
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])

    # ==========================================================================
    # CLASS METHODS
    # ==========================================================================

    @classmethod
    def get_active_for_user(cls, user) -> models.QuerySet:
        """Get all active records for a user."""
        return cls.objects.filter(user=user, is_active=True)

    @classmethod
    def get_summary_for_user(cls, user) -> dict:
        """Get summary statistics for a user."""
        from django.db.models import Sum, Count

        return cls.objects.filter(user=user, is_active=True).aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )

    # ==========================================================================
    # MANAGER METHODS (if needed)
    # ==========================================================================

    # Consider adding a custom manager for complex queries
```

### Model Field Order

Always order fields in this sequence:
1. Choices classes (nested)
2. Primary key
3. Foreign keys
4. Required fields
5. Optional fields
6. Status/type fields
7. Metadata fields (JSON)
8. Timestamps

---

## 3. Serializer Patterns

### Serializer Types

| Type | Purpose | Usage |
|------|---------|-------|
| `ListSerializer` | Minimal fields for lists | GET list endpoints |
| `DetailSerializer` | All fields for single item | GET detail endpoint |
| `CreateSerializer` | Write fields with validation | POST endpoints |
| `UpdateSerializer` | Updatable fields only | PUT/PATCH endpoints |

### Serializer Template

```python
"""
<App Name> Serializers - DRF serializers for API.

This module provides serializers for:
- <Model1>: List, Detail, Create, Update serializers
- <Model2>: List, Detail serializers
"""
from rest_framework import serializers
from .models import ModelName


class ModelNameListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.

    Returns minimal fields for efficient list rendering.
    """

    # Computed fields
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = ModelName
        fields = [
            'id',
            'name',
            'amount',
            'status',
            'category_name',
            'created_at',
        ]
        read_only_fields = fields


class ModelNameSerializer(serializers.ModelSerializer):
    """
    Full serializer for detail views.

    Includes all fields and nested relationships.
    """

    # Nested serializers
    category = CategorySerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)

    # Computed fields
    display_amount = serializers.CharField(read_only=True)
    is_archived = serializers.BooleanField(read_only=True)

    class Meta:
        model = ModelName
        fields = [
            'id',
            'user',
            'category',
            'name',
            'amount',
            'display_amount',
            'description',
            'notes',
            'status',
            'is_active',
            'is_archived',
            'tags',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'display_amount',
            'is_archived',
            'created_at',
            'updated_at',
        ]


class ModelNameCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new records.

    Includes validation for all writable fields.
    """

    # Write-only foreign key fields
    category_id = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = ModelName
        fields = [
            'name',
            'amount',
            'category_id',
            'description',
            'tags',
        ]

    def validate_amount(self, value):
        """Validate amount is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )
        return value

    def validate_name(self, value):
        """Validate and sanitize name."""
        import bleach
        value = bleach.clean(value.strip(), tags=[], strip=True)

        if len(value) < 2:
            raise serializers.ValidationError(
                "Name must be at least 2 characters."
            )
        return value

    def validate_category_id(self, value):
        """Validate category exists and belongs to user."""
        if value is None:
            return value

        from apps.categories.models import Category
        user = self.context['request'].user

        if not Category.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError(
                "Category not found or doesn't belong to you."
            )
        return value

    def create(self, validated_data):
        """Create record with user from context."""
        # Extract foreign key IDs
        category_id = validated_data.pop('category_id', None)

        # Get user from context
        user = self.context['request'].user

        # Create instance
        instance = ModelName.objects.create(
            user=user,
            category_id=category_id,
            **validated_data
        )
        return instance


class ModelNameUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing records.

    Only includes fields that can be updated.
    """

    category_id = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = ModelName
        fields = [
            'name',
            'amount',
            'category_id',
            'description',
            'notes',
            'tags',
        ]

    def validate_category_id(self, value):
        """Validate category belongs to user."""
        if value is None:
            return value

        from apps.categories.models import Category
        user = self.context['request'].user

        if not Category.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError(
                "Category not found."
            )
        return value

    def update(self, instance, validated_data):
        """Update instance with validated data."""
        # Handle foreign key updates
        if 'category_id' in validated_data:
            instance.category_id = validated_data.pop('category_id')

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
```

---

## 4. View Conventions

### API ViewSet Template

```python
"""
<App Name> API Views - REST API endpoints.

This module provides ViewSets for:
- ModelNameViewSet: CRUD operations for ModelName
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import ModelName
from .serializers import (
    ModelNameListSerializer,
    ModelNameSerializer,
    ModelNameCreateSerializer,
    ModelNameUpdateSerializer,
)
from .filters import ModelNameFilter
from apps.core.pagination import StandardPagination


class ModelNameViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ModelName CRUD operations.

    Endpoints:
        GET    /api/v1/<app>/model-names/           List all
        POST   /api/v1/<app>/model-names/           Create new
        GET    /api/v1/<app>/model-names/{id}/      Get one
        PUT    /api/v1/<app>/model-names/{id}/      Update (full)
        PATCH  /api/v1/<app>/model-names/{id}/      Update (partial)
        DELETE /api/v1/<app>/model-names/{id}/      Delete

    Custom actions:
        POST   /api/v1/<app>/model-names/{id}/archive/   Archive
        POST   /api/v1/<app>/model-names/{id}/restore/   Restore
        GET    /api/v1/<app>/model-names/stats/          Statistics

    Filtering:
        ?status=active
        ?category=<uuid>
        ?created_after=2026-01-01
        ?search=keyword

    Ordering:
        ?ordering=-created_at
        ?ordering=name
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ModelNameFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name', 'amount']
    ordering = ['-created_at']
    lookup_field = 'pk'

    def get_queryset(self):
        """
        Return queryset filtered to authenticated user.

        Includes optimized select_related for foreign keys.
        """
        return ModelName.objects.filter(
            user=self.request.user
        ).select_related(
            'category'
        ).order_by('-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ModelNameListSerializer
        elif self.action == 'create':
            return ModelNameCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ModelNameUpdateSerializer
        return ModelNameSerializer

    def perform_create(self, serializer):
        """Set user on create."""
        serializer.save(user=self.request.user)

    # ==========================================================================
    # CUSTOM ACTIONS
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archive a record.

        POST /api/v1/<app>/model-names/{id}/archive/

        Returns:
            200: Record archived successfully
            404: Record not found
        """
        instance = self.get_object()
        instance.archive()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restore an archived record.

        POST /api/v1/<app>/model-names/{id}/restore/

        Returns:
            200: Record restored successfully
            404: Record not found
        """
        instance = self.get_object()
        instance.restore()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get statistics for user's records.

        GET /api/v1/<app>/model-names/stats/

        Returns:
            200: Statistics object
        """
        from django.db.models import Sum, Count, Avg

        queryset = self.get_queryset()

        stats = queryset.aggregate(
            total_count=Count('id'),
            total_amount=Sum('amount'),
            average_amount=Avg('amount'),
        )

        # Add status breakdown
        status_counts = dict(
            queryset.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')
        )

        return Response({
            'total_count': stats['total_count'] or 0,
            'total_amount': stats['total_amount'] or 0,
            'average_amount': round(stats['average_amount'] or 0, 2),
            'by_status': status_counts,
        })
```

---

## 5. URL Configuration

### URL Template

See [URL_AND_VIEW_CONVENTIONS.md](../URL_AND_VIEW_CONVENTIONS.md) for the complete URL structure.

```python
"""
<App Name> URLs - Frontend and API routing.

This module configures URL patterns for:
- Frontend HTML views (template_views.py)
- REST API endpoints (views.py with DRF)

URL Namespaces:
- Frontend: frontend:<app_name>:<view_name>
- API: api:v1:<app_name>:<resource-name>
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import template_views
from . import views

# =============================================================================
# API ROUTER
# =============================================================================

api_router = DefaultRouter()
api_router.register(
    r'model-names',
    views.ModelNameViewSet,
    basename='model-name'
)

# =============================================================================
# API URLPATTERNS
# =============================================================================

api_urlpatterns = [
    path('', include(api_router.urls)),
]

# =============================================================================
# FRONTEND URLPATTERNS
# =============================================================================

frontend_urlpatterns = [
    path('', template_views.model_name_list, name='model_name_list'),
    path('create/', template_views.model_name_create, name='model_name_create'),
    path('<uuid:pk>/', template_views.model_name_detail, name='model_name_detail'),
    path('<uuid:pk>/edit/', template_views.model_name_update, name='model_name_update'),
    path('<uuid:pk>/delete/', template_views.model_name_delete, name='model_name_delete'),
]

# =============================================================================
# APP URL CONFIGURATION
# =============================================================================

app_name = 'app_name'

urlpatterns = [
    path('api/', include((api_urlpatterns, 'api'))),
    path('', include((frontend_urlpatterns, 'frontend'))),
]
```

---

## 6. Form Conventions

```python
"""
<App Name> Forms - Django forms for template views.
"""
from django import forms
from .models import ModelName


class ModelNameForm(forms.ModelForm):
    """
    Form for creating/editing ModelName.

    Used by template views for HTML form rendering.
    """

    class Meta:
        model = ModelName
        fields = ['name', 'amount', 'category', 'description', 'tags']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter name',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Filter category choices to user's categories
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)

    def clean_amount(self):
        """Validate amount is positive."""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount
```

---

## 7. Admin Configuration

```python
"""
<App Name> Admin - Admin site configuration.
"""
from django.contrib import admin
from .models import ModelName


@admin.register(ModelName)
class ModelNameAdmin(admin.ModelAdmin):
    """Admin configuration for ModelName."""

    # List view
    list_display = [
        'name',
        'user',
        'amount',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'user__email']
    date_hierarchy = 'created_at'

    # Detail view
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'user', 'name']
        }),
        ('Details', {
            'fields': ['amount', 'category', 'description']
        }),
        ('Status', {
            'fields': ['status', 'is_active']
        }),
        ('Metadata', {
            'fields': ['tags', 'metadata'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    # Performance optimization
    list_select_related = ['user', 'category']

    # Actions
    actions = ['archive_selected', 'restore_selected']

    @admin.action(description='Archive selected records')
    def archive_selected(self, request, queryset):
        count = queryset.update(status='archived', is_active=False)
        self.message_user(request, f'{count} records archived.')

    @admin.action(description='Restore selected records')
    def restore_selected(self, request, queryset):
        count = queryset.update(status='active', is_active=True)
        self.message_user(request, f'{count} records restored.')
```

---

## 8. Celery Tasks

See [SCALABILITY_GUIDELINES.md](../SCALABILITY_GUIDELINES.md) for detailed task patterns.

```python
"""
<App Name> Tasks - Celery background tasks.
"""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='apps.<app_name>.tasks.example_task',
    queue='default',
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def example_task(self, user_id: str):
    """
    Example background task.

    Args:
        user_id: UUID of the user.

    Returns:
        dict: Task result summary.
    """
    try:
        # Task implementation
        logger.info(f"Processing task for user {user_id}")

        # ... do work ...

        return {'success': True, 'processed': 10}

    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise self.retry(exc=e)
```

---

## 9. Signal Handlers

```python
"""
<App Name> Signals - Signal handlers for model events.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import ModelName
from apps.core.cache_keys import CacheKeys


@receiver(post_save, sender=ModelName)
def on_model_name_saved(sender, instance, created, **kwargs):
    """
    Handle ModelName save event.

    Actions:
    - Invalidate user caches
    - Send notification (if enabled)
    """
    user_id = str(instance.user_id)

    # Invalidate caches
    cache.delete_many([
        CacheKeys.user_dashboard(user_id),
        f"user:{user_id}:model_names:list",
    ])

    # Log event
    import logging
    logger = logging.getLogger(__name__)

    if created:
        logger.info(
            f"ModelName created",
            extra={
                'user_id': user_id,
                'instance_id': str(instance.id),
            }
        )


@receiver(post_delete, sender=ModelName)
def on_model_name_deleted(sender, instance, **kwargs):
    """Handle ModelName delete event."""
    user_id = str(instance.user_id)

    # Invalidate caches
    cache.delete_many([
        CacheKeys.user_dashboard(user_id),
        f"user:{user_id}:model_names:list",
    ])
```

---

## 10. Testing Standards

```python
"""
<App Name> Tests - Test suite for the app.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from .models import ModelName
from .factories import ModelNameFactory, UserFactory


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def user():
    """Create test user."""
    return UserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    """Create authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def model_name(user):
    """Create test ModelName."""
    return ModelNameFactory(user=user)


# =============================================================================
# MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestModelNameModel:
    """Tests for ModelName model."""

    def test_create_model_name(self, user):
        """Test creating a ModelName instance."""
        instance = ModelName.objects.create(
            user=user,
            name='Test Name',
            amount=100.00,
        )

        assert instance.id is not None
        assert instance.name == 'Test Name'
        assert instance.amount == 100.00
        assert instance.status == ModelName.Status.ACTIVE

    def test_archive_model_name(self, model_name):
        """Test archiving a ModelName."""
        model_name.archive()

        assert model_name.status == ModelName.Status.ARCHIVED
        assert model_name.is_active is False


# =============================================================================
# API TESTS
# =============================================================================

@pytest.mark.django_db
class TestModelNameAPI:
    """Tests for ModelName API endpoints."""

    def test_list_requires_authentication(self, api_client):
        """Unauthenticated requests should return 401."""
        url = reverse('app_name:api:model-name-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_returns_user_data_only(self, authenticated_client, user):
        """Users should only see their own records."""
        # Create records for this user
        ModelNameFactory.create_batch(5, user=user)

        # Create records for another user
        other_user = UserFactory()
        ModelNameFactory.create_batch(3, user=other_user)

        url = reverse('app_name:api:model-name-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pagination']['count'] == 5

    def test_create_valid_data(self, authenticated_client):
        """Create with valid data should return 201."""
        url = reverse('app_name:api:model-name-list')
        data = {
            'name': 'Test Name',
            'amount': 100.00,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Test Name'

    def test_create_invalid_amount(self, authenticated_client):
        """Create with negative amount should return 400."""
        url = reverse('app_name:api:model-name-list')
        data = {
            'name': 'Test Name',
            'amount': -100.00,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'amount' in response.data
```

---

## 11. Error Handling

```python
"""
<App Name> Exceptions - Custom exceptions.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class ModelNameError(APIException):
    """Base exception for ModelName errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An error occurred.'
    default_code = 'model_name_error'


class ModelNameNotFoundError(ModelNameError):
    """Raised when ModelName is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Record not found.'
    default_code = 'not_found'


class ModelNamePermissionError(ModelNameError):
    """Raised when user lacks permission."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this action.'
    default_code = 'permission_denied'
```

---

## 12. Logging Patterns

```python
"""
Logging patterns for the app.
"""
import logging

logger = logging.getLogger(__name__)


def log_operation(operation: str, user_id: str, **extra):
    """Log an operation with structured data."""
    logger.info(
        f"Operation: {operation}",
        extra={
            'operation': operation,
            'user_id': user_id,
            **extra
        }
    )


# Usage in views:
def create(self, request):
    # ... create logic ...
    log_operation(
        'model_name.create',
        str(request.user.id),
        instance_id=str(instance.id),
        amount=instance.amount
    )
```

---

**This document is MANDATORY for all Django development in Pecunia.**

*Last reviewed: 2026-01-28*
