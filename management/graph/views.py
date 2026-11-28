from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from user.permissions import is_panel_admin

from . import services
from .models import GraphRun
from .workflow import SERVICE_CONFIG


def _visible_runs(user):
    runs = GraphRun.objects.select_related("user")
    return runs if is_panel_admin(user) else runs.filter(user=user)


@login_required
def dashboard(request):
    return render(
        request,
        "graph/dashboard.html",
        {"stats": services.dashboard_stats(), "recent_runs": _visible_runs(request.user)[:6]},
    )


@login_required
def runner(request):
    return render(
        request,
        "graph/runner.html",
        {
            "service_choices": services.service_choices(),
            "blueprint": services.blueprint(),
            "recent_runs": _visible_runs(request.user)[:5],
        },
    )


@login_required
@require_POST
def execute(request):
    selected = [s for s in request.POST.getlist("service") if s in SERVICE_CONFIG]
    if not selected:
        return JsonResponse({"error": "En az bir servis türü seçmelisiniz."}, status=400)

    runs = [services.run_and_record(service, request.user) for service in selected]
    html = render_to_string("graph/_run_card.html", {"runs": runs, "animate": True}, request=request)
    return JsonResponse({"html": html, "count": len(runs)})


@login_required
def run_history(request):
    runs = _visible_runs(request.user)
    service = request.GET.get("service", "")
    decision = request.GET.get("decision", "")
    status = request.GET.get("status", "")
    if service in SERVICE_CONFIG:
        runs = runs.filter(service_type=service)
    if decision in dict(GraphRun.DECISION_CHOICES):
        runs = runs.filter(decision=decision)
    if status in dict(GraphRun.STATUS_CHOICES):
        runs = runs.filter(status=status)
    page = Paginator(runs, 15).get_page(request.GET.get("page"))
    return render(
        request,
        "graph/run_history.html",
        {
            "page": page,
            "service": service,
            "decision": decision,
            "status": status,
            "service_choices": services.service_choices(),
            "decision_choices": GraphRun.DECISION_CHOICES,
            "status_choices": GraphRun.STATUS_CHOICES,
        },
    )


@login_required
def run_detail(request, pk):
    run = get_object_or_404(_visible_runs(request.user), pk=pk)
    return render(request, "graph/run_detail.html", {"run": run, "runs": [run]})
