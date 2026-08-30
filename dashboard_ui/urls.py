"""URLs for dashboard_ui app."""

from django.urls import path, re_path
from . import views

urlpatterns = [
    # Main Dashboard Page
    path("", views.index_view, name="index"),
    path("cases/", views.cases_list_view, name="cases_list"),
    path("cases/<str:case_id>/", views.case_detail_view, name="case_detail"),
    path("custom-review/", views.custom_review_view, name="custom_review"),
    path("traces/", views.traces_viewer, name="traces_viewer"),

    # REST API Endpoints
    path("api/benchmark-data/", views.api_benchmark_data, name="api_benchmark_data"),
    path("api/benchmark-data", views.api_benchmark_data, name="api_benchmark_data_noslash"),

    path("api/evaluate/<str:case_id>/", views.api_evaluate_case, name="api_evaluate_case"),
    path("api/evaluate/<str:case_id>", views.api_evaluate_case, name="api_evaluate_case_noslash"),
    path("api/run-case/<str:case_id>/", views.api_evaluate_case, name="run_case_api"),
    path("api/run-case/<str:case_id>", views.api_evaluate_case, name="run_case_api_noslash"),

    path("api/evaluate-takehome/", views.api_evaluate_takehome, name="api_evaluate_takehome"),
    path("api/evaluate-takehome", views.api_evaluate_takehome, name="api_evaluate_takehome_noslash"),

    path("api/trajectories/", views.api_trajectories, name="api_trajectories"),
    path("api/trajectories", views.api_trajectories, name="api_trajectories_noslash"),
    re_path(r"^api/trajectories/(?P<filename>[^/]+)/?$", views.api_trajectory_detail, name="api_trajectory_detail"),
]
