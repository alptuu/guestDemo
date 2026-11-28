from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=get_user_model())
def create_profile(sender, instance, created, **kwargs):
    if created:
        role = Profile.ROLE_ADMIN if instance.is_superuser else Profile.ROLE_PERSONNEL
        Profile.objects.get_or_create(user=instance, defaults={"role": role})
