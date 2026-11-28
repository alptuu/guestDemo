from django.conf import settings
from django.db import models


class GraphRun(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [(STATUS_SUCCESS, "Başarılı"), (STATUS_ERROR, "Hata")]

    DECISION_CHOICES = [("notify", "Yönetici bilgilendirildi"), ("stop", "Takip durduruldu")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="graph_runs",
    )
    service_type = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    decision = models.CharField(max_length=10, blank=True, choices=DECISION_CHOICES)
    duration_ms = models.FloatField(default=0)
    breached_floors = models.PositiveIntegerField(default=0)
    notified_count = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"#{self.pk} {self.service_label} ({self.created_at:%d.%m.%Y %H:%M})"

    @property
    def service_label(self):
        from .workflow import SERVICE_CONFIG

        return SERVICE_CONFIG.get(self.service_type, {}).get("label", self.service_type)

    
