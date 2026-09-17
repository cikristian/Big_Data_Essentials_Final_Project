from django.urls import path

from operations import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/dashboard-data/", views.dashboard_data, name="dashboard-data"),
    path("api/preview-event/", views.preview_event, name="preview-event"),
    path("api/trips/publish/", views.publish_trip_events, name="publish-trip-events"),
]
