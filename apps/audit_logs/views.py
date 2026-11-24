from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import AuditLog

@login_required
def audit_log_list_view(request):
    action_filter = request.GET.get("action", "").strip()
    logs = AuditLog.objects.select_related("actor").all().order_by("-timestamp")

    if action_filter:
        logs = logs.filter(action_type=action_filter)

    action_types = AuditLog.objects.values_list("action_type", flat=True).distinct()

    return render(request, "audit_logs/list.html", {
        "logs": logs[:50],
        "action_filter": action_filter,
        "action_types": action_types,
    })