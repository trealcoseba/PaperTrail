from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    unread_count = notifications.filter(is_read=False).count()

    return render(request, "notifications/list.html", {
        "notifications": notifications,
        "unread_count": unread_count,
    })

@login_required
def mark_read_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    # If linked to a document, go straight to its tracker
    if notif.document:
        return redirect("documents:track", tracking_number=notif.document.tracking_number)
    return redirect("notifications:list")

@login_required
def mark_all_read_view(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")