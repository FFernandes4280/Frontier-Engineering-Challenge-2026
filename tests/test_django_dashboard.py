"""Unit tests for Django Web Dashboard views."""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_app.settings")
django.setup()

from django.test import Client


def test_dashboard_index_view():
    """Test dashboard index view returns 200 and renders benchmark cards."""
    client = Client()
    response = client.get("/")
    assert response.status_code == 200
    assert "Holistic Senior Vetting" in response.content.decode("utf-8")


def test_cases_list_view():
    """Test benchmark cases catalog view returns 200."""
    client = Client()
    response = client.get("/cases/")
    assert response.status_code == 200
    assert "Benchmark Scenarios Catalog" in response.content.decode("utf-8")


def test_case_detail_view():
    """Test single case detail view returns 200."""
    client = Client()
    response = client.get("/cases/case_01/")
    assert response.status_code == 200
    assert "Distributed In-Memory State Drift" in response.content.decode("utf-8")


def test_custom_review_view():
    """Test take-home project repository review view returns 200."""
    client = Client()
    response = client.get("/custom-review/")
    assert response.status_code == 200
    assert "Take-Home Project" in response.content.decode("utf-8")


def test_traces_viewer_view():
    """Test traces viewer view returns 200."""
    client = Client()
    response = client.get("/traces/")
    assert response.status_code == 200
    assert "Audit Trajectories" in response.content.decode("utf-8")
