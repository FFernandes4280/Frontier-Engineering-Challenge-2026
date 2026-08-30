"""URLs for the Dashboard UI app."""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.index_view, name="index"),
    path("cases/", views.cases_list_view, name="cases_list"),
    path("cases/<str:case_id>/", views.case_detail_view, name="case_detail"),
    path("api/cases/<str:case_id>/run/", views.run_case_api, name="run_case_api"),
    path("custom-review/", views.custom_review_view, name="custom_review"),
    path("traces/", views.traces_viewer, name="traces_viewer"),
]
