from django.urls import path
from . import views

app_name = "offices"

urlpatterns = [
    path("", views.office_directory_view, name="directory"),
]