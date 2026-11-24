from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.utils import timezone
from apps.documents.models import DocumentRequest

@login_required
def home_view(request):
    user_documents = DocumentRequest.objects.select_related("template").filter(student=request.user).order_by("-submitted_at")
    
    now = timezone.now()
    overdue_count = 0

    for doc in user_documents:
        elapsed = (now - doc.submitted_at).days
        doc.elapsed_days = elapsed
        sla_days = doc.template.estimated_total_days if doc.template else 5
        doc.sla_days = sla_days
        doc.is_overdue = (elapsed > sla_days) and (doc.status not in ["Approved", "Released"])
        if doc.is_overdue:
            overdue_count += 1

    return render(request, "home/home.html", {
        "documents": user_documents,
        "total_docs": user_documents.count(),
        "active_docs": user_documents.exclude(status__in=["Approved", "Released"]).count(),
        "overdue_count": overdue_count,
    })

def logout_view(request):
    logout(request)
    return redirect("login:login")