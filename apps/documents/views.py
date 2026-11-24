import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q

from .models import DocumentRequest, DocumentStageLog
from apps.workflows.models import WorkflowTemplate, WorkflowTemplateStep
from apps.offices.models import Office
from apps.notifications.models import Notification
from apps.audit_logs.utils import log_audit_event


def ensure_default_workflow_steps(template):
    """Guarantees that a template always has all 5 required sequential stages."""
    Office.objects.filter(code="DEAN_ENG").update(code="DEAN")

    if template.steps.count() < 5:
        off_chair, _ = Office.objects.get_or_create(code="DEPT_CHAIR", defaults={"name": "Department Chair Office", "building_location": "CS Bldg Rm 201"})
        off_dean, _ = Office.objects.get_or_create(code="DEAN", defaults={"name": "College Dean's Office", "building_location": "Main Wing Rm 302"})
        off_reg, _ = Office.objects.get_or_create(code="REGISTRAR", defaults={"name": "University Registrar", "building_location": "Admin Bldg Rm 101"})
        off_cashier, _ = Office.objects.get_or_create(code="CASHIER", defaults={"name": "Accounting & Cashier", "building_location": "Finance Bldg Rm 104"})
        off_vpaa, _ = Office.objects.get_or_create(code="VPAA", defaults={"name": "Office of Academic Affairs", "building_location": "Admin Bldg Rm 401"})

        WorkflowTemplateStep.objects.get_or_create(template=template, step_order=1, defaults={"office": off_chair, "required_action": "Initial Evaluation & Endorsement", "expected_duration_days": 1})
        WorkflowTemplateStep.objects.get_or_create(template=template, step_order=2, defaults={"office": off_dean, "required_action": "Dean Review & Signature", "expected_duration_days": 1})
        WorkflowTemplateStep.objects.get_or_create(template=template, step_order=3, defaults={"office": off_reg, "required_action": "Scholastic Record Verification", "expected_duration_days": 2})
        WorkflowTemplateStep.objects.get_or_create(template=template, step_order=4, defaults={"office": off_cashier, "required_action": "Student Account Clearance", "expected_duration_days": 1})
        WorkflowTemplateStep.objects.get_or_create(template=template, step_order=5, defaults={"office": off_vpaa, "required_action": "Final Approval & Document Release", "expected_duration_days": 1})


@login_required
def create_document_view(request):
    template = WorkflowTemplate.objects.first()
    if not template:
        template = WorkflowTemplate.objects.create(
            title="University Academic Clearance & Endorsement",
            description="5-stage sequential processing workflow across academic and administrative offices.",
            estimated_total_days=5
        )
    ensure_default_workflow_steps(template)

    templates = WorkflowTemplate.objects.filter(is_active=True)

    if request.method == "POST":
        template_id = request.POST.get("template_id")
        title = request.POST.get("document_title")
        purpose = request.POST.get("purpose")
        selected_template = get_object_or_404(WorkflowTemplate, id=template_id)
        ensure_default_workflow_steps(selected_template)

        tracking_num = f"PT-2026-{random.randint(1000, 9999)}"

        doc = DocumentRequest.objects.create(
            tracking_number=tracking_num,
            student=request.user,
            template=selected_template,
            document_title=title,
            purpose=purpose,
            current_step_order=1,
            status="Under Review"
        )

        first_step = selected_template.steps.first()
        if first_step:
            DocumentStageLog.objects.create(
                document=doc,
                step_order=1,
                office=first_step.office,
                actor=None,
                action_taken="Submitted for Review",
                remarks="Document received into department chair queue.",
                entered_at=timezone.now()
            )
            Notification.objects.create(
                user=request.user,
                document=doc,
                title=f"Request Submitted: {doc.tracking_number}",
                message=f"Your document '{doc.document_title}' has been submitted to {first_step.office.name}."
            )

        log_audit_event(request, "DOCUMENT_SUBMITTED", f"Submitted {doc.tracking_number}: {doc.document_title}")
        return redirect("documents:track", tracking_number=doc.tracking_number)

    return render(request, "documents/create_request.html", {"templates": templates})


@login_required
def tracker_view(request, tracking_number):
    document = get_object_or_404(DocumentRequest, tracking_number=tracking_number)
    ensure_default_workflow_steps(document.template)

    steps = document.template.steps.all().order_by("step_order")

    if document.stage_logs.count() == 0 and steps.exists():
        DocumentStageLog.objects.create(
            document=document,
            step_order=1,
            office=steps.first().office,
            actor=None,
            action_taken="Submitted for Review",
            remarks="Document received into department chair queue.",
            entered_at=timezone.now()
        )

    logs = document.stage_logs.all().order_by("-entered_at")
    current_step = steps.filter(step_order=document.current_step_order).first()
    next_step = steps.filter(step_order=document.current_step_order + 1).first()

    return render(request, "documents/tracker.html", {
        "document": document,
        "steps": steps,
        "logs": logs,
        "current_step": current_step,
        "next_step": next_step,
    })


@login_required
def office_queue_view(request):
    all_documents = DocumentRequest.objects.all().order_by("-submitted_at")
    pending_docs = all_documents.filter(status__in=["Submitted", "Under Review"])
    returned_docs = all_documents.filter(status="Returned")
    completed_docs = all_documents.filter(status__in=["Approved", "Released"])

    return render(request, "documents/office_queue.html", {
        "documents": all_documents,
        "pending_count": pending_docs.count(),
        "returned_count": returned_docs.count(),
        "completed_count": completed_docs.count(),
    })


@login_required
def process_document_view(request, tracking_number):
    doc = get_object_or_404(DocumentRequest, tracking_number=tracking_number)
    steps = doc.template.steps.all().order_by("step_order")
    current_step = steps.filter(step_order=doc.current_step_order).first()
    next_step = steps.filter(step_order=doc.current_step_order + 1).first()

    if request.method == "POST":
        action = request.POST.get("action")
        remarks = request.POST.get("remarks", "").strip()
        target_office = current_step.office if current_step else steps.first().office

        if action == "approve":
            if next_step:
                doc.current_step_order += 1
                doc.status = "Under Review"
                action_text = f"Approved & Forwarded to {next_step.office.code}"
            else:
                doc.status = "Released"
                action_text = "Final Approval & Released"

            doc.save()

            DocumentStageLog.objects.create(
                document=doc,
                step_order=doc.current_step_order,
                office=target_office,
                actor=request.user,
                action_taken=action_text,
                remarks=remarks if remarks else "Approved without remarks.",
                entered_at=timezone.now()
            )
            Notification.objects.create(
                user=doc.student,
                document=doc,
                title=f"Stage Approved: {doc.tracking_number}",
                message=f"Update on '{doc.document_title}': {action_text}. Remarks: {remarks or 'None'}"
            )
            log_audit_event(request, "STAGE_APPROVED", f"{doc.tracking_number} - {action_text}")

        elif action == "return":
            doc.status = "Returned"
            doc.save()

            DocumentStageLog.objects.create(
                document=doc,
                step_order=doc.current_step_order,
                office=target_office,
                actor=request.user,
                action_taken="Returned for Revision",
                remarks=remarks if remarks else "Document returned: Additional requirements needed.",
                entered_at=timezone.now()
            )
            Notification.objects.create(
                user=doc.student,
                document=doc,
                title=f"Action Required: {doc.tracking_number} Returned",
                message=f"'{doc.document_title}' was returned by {target_office.name}. Reason: {remarks or 'Additional requirements needed.'}"
            )
            log_audit_event(request, "DOCUMENT_RETURNED", f"{doc.tracking_number} returned. Reason: {remarks}")

        return redirect("documents:track", tracking_number=doc.tracking_number)

    return render(request, "documents/process_document.html", {
        "document": doc,
        "current_step": current_step,
        "next_step": next_step,
    })


@login_required
def revise_document_view(request, tracking_number):
    doc = get_object_or_404(DocumentRequest, tracking_number=tracking_number, student=request.user)
    steps = doc.template.steps.all().order_by("step_order")
    current_step = steps.filter(step_order=doc.current_step_order).first()
    return_log = doc.stage_logs.filter(action_taken="Returned for Revision").order_by("-entered_at").first()

    if request.method == "POST":
        doc.document_title = request.POST.get("document_title", doc.document_title)
        doc.purpose = request.POST.get("purpose", doc.purpose)
        revision_note = request.POST.get("revision_note", "").strip()

        doc.status = "Under Review"
        doc.save()

        target_office = current_step.office if current_step else steps.first().office

        DocumentStageLog.objects.create(
            document=doc,
            step_order=doc.current_step_order,
            office=target_office,
            actor=request.user,
            action_taken="Resubmitted after Revision",
            remarks=revision_note if revision_note else "Student updated and resubmitted the document.",
            entered_at=timezone.now()
        )
        Notification.objects.create(
            user=request.user,
            document=doc,
            title=f"Document Resubmitted: {doc.tracking_number}",
            message=f"'{doc.document_title}' has been resubmitted to {target_office.name} for review."
        )
        log_audit_event(request, "DOCUMENT_RESUBMITTED", f"Revised and resubmitted {doc.tracking_number}")

        return redirect("documents:track", tracking_number=doc.tracking_number)

    return render(request, "documents/revise.html", {
        "document": doc,
        "current_step": current_step,
        "return_log": return_log,
    })


@login_required
def search_documents_view(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    results = DocumentRequest.objects.all().order_by("-submitted_at")

    if query:
        results = results.filter(
            Q(tracking_number__icontains=query) |
            Q(document_title__icontains=query) |
            Q(purpose__icontains=query) |
            Q(student__username__icontains=query)
        )

    if status_filter:
        results = results.filter(status=status_filter)

    return render(request, "documents/search.html", {
        "results": results,
        "query": query,
        "status_filter": status_filter,
        "result_count": results.count(),
    })