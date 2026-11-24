from .models import AuditLog

def log_audit_event(request, action_type, details=""):
    """Records a system security/activity audit event in Supabase."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action_type=action_type,
        ip_address=ip,
        details=details
    )