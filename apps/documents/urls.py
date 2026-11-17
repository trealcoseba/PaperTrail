from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("new/", views.create_document_view, name="create"),
    path("track/<str:tracking_number>/", views.tracker_view, name="track"),
    path("queue/", views.office_queue_view, name="queue"),                    
    path("process/<str:tracking_number>/", views.process_document_view, name="process"), 
]