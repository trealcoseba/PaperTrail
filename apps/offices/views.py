from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Office

@login_required
def office_directory_view(request):
    error = None
    success = None

    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        name = request.POST.get("name", "").strip()
        building_location = request.POST.get("building_location", "").strip()

        if Office.objects.filter(code=code).exists():
            error = f"An office with code '{code}' already exists."
        elif code and name:
            Office.objects.create(
                code=code,
                name=name,
                building_location=building_location
            )
            success = f"Office '{code} - {name}' added successfully!"

    offices = Office.objects.all().order_by("code")
    return render(request, "offices/directory.html", {
        "offices": offices,
        "error": error,
        "success": success,
    })