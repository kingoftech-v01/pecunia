"""
Sync Models.

Models for tracking synchronization operations between clients and server.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class SyncLog(models.Model):
    """
    Tracks synchronization events between client and server.

    Records each sync operation with status, timestamps, and metadata.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]

    DIRECTION_CHOICES = [
        ('push', 'Client to Server'),
        ('pull', 'Server to Client'),
        ('bidirectional', 'Bidirectional'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_logs'
    )

    # Sync details
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Device information
    device_id = models.CharField(max_length=255, blank=True, null=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    client_version = models.CharField(max_length=50, blank=True, null=True)

    # Sync statistics
    items_pushed = models.PositiveIntegerField(default=0)
    items_pulled = models.PositiveIntegerField(default=0)
    items_failed = models.PositiveIntegerField(default=0)

    # Timestamps
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)

    # Last sync checkpoint for incremental sync
    last_sync_timestamp = models.DateTimeField(blank=True, null=True)

    # Error tracking
    error_message = models.TextField(blank=True, null=True)
    error_details = models.JSONField(blank=True, null=True)

    # Metadata
    sync_metadata = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = 'sync log'
        verbose_name_plural = 'sync logs'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['device_id', '-started_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Sync {self.id} - {self.user.email} - {self.status}"

    def mark_completed(self):
        """Mark the sync as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, error_message, error_details=None):
        """Mark the sync as failed with error info."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_details = error_details
        self.save()

    @property
    def duration(self):
        """Calculate sync duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class SyncQueue(models.Model):
    """
    Queue for pending sync operations.

    Stores changes that need to be synced from the server to clients.
    """
    OPERATION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Normal'),
        (3, 'High'),
        (4, 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_queue'
    )

    # Operation details
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=255)

    # Change data
    payload = models.JSONField(help_text="The data to be synced")

    # Sync metadata
    client_timestamp = models.DateTimeField(
        help_text="Timestamp when the change was made on the client"
    )
    server_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the change was received on the server"
    )

    # Processing status
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(blank=True, null=True)

    # Priority for ordering
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES, default=2)

    # Error tracking
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)

    # Device tracking
    source_device_id = models.CharField(max_length=255, blank=True, null=True)

    # Conflict resolution
    is_conflict = models.BooleanField(default=False)
    conflict_resolution = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = 'sync queue item'
        verbose_name_plural = 'sync queue items'
        ordering = ['-priority', 'client_timestamp']
        indexes = [
            models.Index(fields=['user', 'is_processed']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['-priority', 'client_timestamp']),
        ]

    def __str__(self):
        return f"{self.operation} {self.model_name}:{self.object_id}"

    def mark_processed(self):
        """Mark the queue item as processed."""
        self.is_processed = True
        self.processed_at = timezone.now()
        self.save()

    def increment_retry(self, error_message):
        """Increment retry count and record error."""
        self.retry_count += 1
        self.last_error = error_message
        self.save()

    @property
    def can_retry(self):
        """Check if the item can be retried."""
        return self.retry_count < self.max_retries


class SyncConflict(models.Model):
    """
    Records sync conflicts that require resolution.

    When the same data is modified on multiple devices, conflicts are stored here.
    """
    RESOLUTION_CHOICES = [
        ('pending', 'Pending'),
        ('server_wins', 'Server Version Kept'),
        ('client_wins', 'Client Version Kept'),
        ('merged', 'Merged'),
        ('manual', 'Manual Resolution'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_conflicts'
    )

    # Related objects
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=255)

    # Conflict data
    server_version = models.JSONField(help_text="Data as it exists on the server")
    client_version = models.JSONField(help_text="Data from the client")

    # Resolution
    resolution_status = models.CharField(
        max_length=20,
        choices=RESOLUTION_CHOICES,
        default='pending'
    )
    resolved_version = models.JSONField(blank=True, null=True)

    # Timestamps
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    # Device info
    conflicting_device_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'sync conflict'
        verbose_name_plural = 'sync conflicts'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['user', 'resolution_status']),
            models.Index(fields=['model_name', 'object_id']),
        ]

    def __str__(self):
        return f"Conflict {self.model_name}:{self.object_id} - {self.resolution_status}"

    def resolve(self, resolution_status, resolved_version=None):
        """Resolve the conflict."""
        self.resolution_status = resolution_status
        self.resolved_version = resolved_version
        self.resolved_at = timezone.now()
        self.save()
