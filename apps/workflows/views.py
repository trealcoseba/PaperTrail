from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import WorkflowTemplate, WorkflowTemplateStep
from apps.offices.models import Office

@login_required
def workflow_builder_view(request):
    success = None
    error = None

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        estimated_days = int(request.POST.get("estimated_total_days", 5))

        step_offices = [
            request.POST.get("step1_office"),
            request.POST.get("step2_office"),
            request.POST.get("step3_office"),
            request.POST.get("step4_office"),
            request.POST.get("step5_office"),
        ]
        step_actions = [
            request.POST.get("step1_action", "Initial Review"),
            request.POST.get("step2_action", "Endorsement"),
            request.POST.get("step3_action", "Verification"),
            request.POST.get("step4_action", "Signature"),
            request.POST.get("step5_action", "Final Approval & Release"),
        ]

        if title and all(step_offices):
            wf = WorkflowTemplate.objects.create(
                title=title,
                description=description,
                estimated_total_days=estimated_days,
                is_active=True
            )
            for idx, (off_id, action) in enumerate(zip(step_offices, step_actions), start=1):
                office_obj = Office.objects.get(id=off_id)
                WorkflowTemplateStep.objects.create(
                    template=wf,
                    step_order=idx,
                    office=office_obj,
                    required_action=action,
                    expected_duration_days=1
                )
            success = f"5-Stage Workflow '{title}' created! It is now available in + New Request."
        else:
            error = "Please provide a workflow title and select offices for all 5 stages."

    workflows = WorkflowTemplate.objects.prefetch_related("steps__office").all().order_by("-created_at")
    offices = Office.objects.all().order_by("code")

    return render(request, "workflows/builder.html", {
        "workflows": workflows,
        "offices": offices,
        "success": success,
        "error": error,
    })