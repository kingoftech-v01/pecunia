"""
Accounts Signals.

Signal handlers for user-related events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    """Save the UserProfile when the User is saved (only on creation)."""
    # Avoid cascading saves on every user save - only needed on creation
    # Profile updates should be saved explicitly through their own serializer
    if created and hasattr(instance, 'profile'):
        instance.profile.save()
