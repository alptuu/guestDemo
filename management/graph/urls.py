from django.urls import path

from . import views

app_name = "graph"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("graph/run/", views.runner, name="runner"),
    path("graph/run/execute/", views.execute, name="execute"),
    path("graph/runs/", views.run_history, name="run_history"),
    path("graph/runs/<int:pk>/", views.run_detail, name="run_detail"),
]
