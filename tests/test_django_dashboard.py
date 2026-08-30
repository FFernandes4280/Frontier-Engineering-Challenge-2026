"""Automated pytest suite for Django Dashboard UI & Agent Runtime Endpoints."""

import json
import os
from unittest.mock import AsyncMock, patch
import pytest
from django.test import AsyncClient, Client
from src.core.llm import LLMResponse


@pytest.fixture(autouse=True)
def setup_django_settings():
    os.environ["DJANGO_SETTINGS_MODULE"] = "web_app.settings"
    import django
    django.setup()


def test_index_view():
    client = Client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"micro1" in response.content
    assert b"Frontier" in response.content
    assert b"Vetting" in response.content


def test_cases_list_view():
    client = Client()
    response = client.get("/cases/")
    assert response.status_code == 200
    assert b"Benchmark Cases" in response.content or b"case_01" in response.content


def test_case_detail_view():
    client = Client()
    response = client.get("/cases/case_01/")
    assert response.status_code == 200
    assert b"case_01" in response.content


def test_custom_review_view():
    client = Client()
    response = client.get("/custom-review/")
    assert response.status_code == 200


def test_traces_viewer_view():
    client = Client()
    response = client.get("/traces/")
    assert response.status_code == 200


def test_benchmark_data_view():
    client = Client()
    response = client.get("/api/benchmark-data/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "cases" in data
    assert len(data["cases"]) >= 15
    assert data["cases"][0]["case_id"] == "case_01"


def test_trajectories_list_view():
    client = Client()
    response = client.get("/api/trajectories/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "trajectories" in data
    assert isinstance(data["trajectories"], list)


def test_trajectory_detail_view_json():
    client = Client()
    list_res = client.get("/api/trajectories/")
    data = list_res.json()
    json_files = [t["filename"] for t in data.get("trajectories", []) if t["filename"].endswith(".json")]

    if json_files:
        filename = json_files[0]
        res = client.get(f"/api/trajectories/{filename}/")
        assert res.status_code == 200
        res_data = res.json()
        assert res_data["status"] == "success"
        assert res_data["filename"] == filename


def test_trajectory_detail_view_404():
    client = Client()
    res = client.get("/api/trajectories/non_existent_file_9999.json/")
    assert res.status_code == 404
    data = res.json()
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_evaluate_case_view_advanced():
    client = AsyncClient()
    mock_llm_response = LLMResponse(
        content="Candidate failed due to localized in-memory caching across multi-worker pods.",
        model="groq/openai/gpt-oss-20b",
        prompt_tokens=300,
        completion_tokens=80,
        total_tokens=380,
        cost_usd=0.00005,
        latency_ms=80.0
    )

    with patch("src.core.llm.LLMClient.acomplete", new_callable=AsyncMock, return_value=mock_llm_response):
        response = await client.post(
            "/api/evaluate/case_01/",
            data=json.dumps({"runner": "advanced"}),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["case_id"] == "case_01"
        assert "dossier" in data
        assert data["dossier"]["scenario_id"] == "case_01"
        assert "tokens" in data
        assert "duration_ms" in data


@pytest.mark.asyncio
async def test_evaluate_case_view_both():
    client = AsyncClient()
    mock_llm_response = LLMResponse(
        content="Score: 85\nRecommendation: HIRE\nSummary: Code passes unit tests and architecture checks.",
        model="groq/openai/gpt-oss-120b",
        prompt_tokens=250,
        completion_tokens=60,
        total_tokens=310,
        cost_usd=0.0001,
        latency_ms=100.0
    )

    with patch("src.core.llm.LLMClient.acomplete", new_callable=AsyncMock, return_value=mock_llm_response):
        response = await client.post(
            "/api/evaluate/case_02/",
            data=json.dumps({"runner": "both"}),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data
        assert "advanced" in data["results"]
        assert "baseline" in data["results"]


@pytest.mark.asyncio
async def test_evaluate_case_view_not_found():
    client = AsyncClient()
    response = await client.post(
        "/api/evaluate/case_99999/",
        data=json.dumps({"runner": "advanced"}),
        content_type="application/json"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_evaluate_takehome_invalid_url():
    client = AsyncClient()
    response = await client.post(
        "/api/evaluate-takehome/",
        data=json.dumps({"repo_url": "invalid-url"}),
        content_type="application/json"
    )
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
