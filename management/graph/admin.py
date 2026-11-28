from django.contrib import admin

from .models import GraphRun


@admin.register(GraphRun)
class GraphRunAdmin(admin.ModelAdmin):
    list_display = ("id", "service_type", "status", "decision", "breached_floors", "notified_count", "user", "created_at")
    list_filter = ("service_type", "status", "decision")
    readonly_fields = ("payload", "created_at")
