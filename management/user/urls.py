from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "user"

urlpatterns = [
    path("login/", views.PanelLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password/", views.PanelPasswordChangeView.as_view(), name="password_change"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/password/", views.user_set_password, name="user_set_password"),
]
