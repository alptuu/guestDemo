from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Profile


def get_profile(user):
    """Profili olmayan (sinyalden önce oluşturulmuş) kullanıcılar için profili tembel oluşturur."""
    role = Profile.ROLE_ADMIN if user.is_superuser else Profile.ROLE_PERSONNEL
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"role": role})
    return profile


def is_panel_admin(user):
    return user.is_authenticated and (user.is_superuser or get_profile(user).is_admin)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_panel_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
