from django.urls import path

from operations import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("summary/", views.database_summary_page, name="database-summary-page"),
    path("predictions/", views.predictions_page, name="predictions-page"),
    path("api/dashboard-data/", views.dashboard_data, name="dashboard-data"),
    path("api/database-summary/", views.database_summary_data, name="database-summary-data"),
    path("api/data/generate/", views.generate_random_trip_events, name="generate-random-trip-events"),
    path("api/preview-event/", views.preview_event, name="preview-event"),
    path("api/trips/publish/", views.publish_trip_events, name="publish-trip-events"),
]
