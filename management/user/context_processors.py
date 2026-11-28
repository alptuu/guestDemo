from .permissions import get_profile, is_panel_admin


def panel(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "panel_profile": get_profile(request.user),
        "is_panel_admin": is_panel_admin(request.user),
    }
