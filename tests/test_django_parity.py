"""Official Parity, Compliance & Dynamic Audit Test Suite for Django Web Dashboard & Multi-Agent Squad."""

import os
import json
import tempfile
import subprocess
import pytest
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_app.settings")
django.setup()

from django.test import Client
from src.core.domain import ScenarioSpec, CandidateSubmission, FileChange
from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from src.baseline.runner import BaselineVettingRunner


@pytest.fixture
def client():
    """Provides Django test client fixture."""
    return Client()


def test_main_route_status_200(client):
    """1. Test GET / responds with HTTP 200 and main dashboard elements."""
    response = client.get("/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Holistic Senior Vetting" in content
    assert "micro1" in content

    # Check secondary pages
    resp_cases = client.get("/cases/")
    assert resp_cases.status_code == 200

    resp_detail = client.get("/cases/case_01/")
    assert resp_detail.status_code == 200
    assert "Distributed In-Memory State Drift" in resp_detail.content.decode("utf-8")

    resp_custom = client.get("/custom-review/")
    assert resp_custom.status_code == 200

    resp_traces = client.get("/traces/")
    assert resp_traces.status_code == 200


def test_api_benchmark_data_returns_15_cases(client):
    """2. Test GET /api/benchmark-data/ returns 15 valid benchmark scenarios."""
    response = client.get("/api/benchmark-data/")
    assert response.status_code == 200
    data = response.json()

    assert "total_cases" in data
    assert data["total_cases"] == 15
    assert len(data["cases"]) == 15

    # Validate essential schema on all 15 scenarios
    for case in data["cases"]:
        assert "case_id" in case
        assert "title" in case
        assert "spec" in case
        assert "submission" in case
        assert "human_senior_verdict" in case
        assert case["spec"]["github_repo"]
        assert case["spec"]["architecture_type"]


def test_api_evaluate_case_01_dynamic_execution(client):
    """3. Test POST /api/evaluate/case_01 triggers runner and returns dynamic evaluation scores."""
    payload = {"runner": "advanced"}
    response = client.post(
        "/api/evaluate/case_01",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["case_id"] == "case_01"
    assert "title" in data
    assert "ground_truth" in data
    assert "results" in data
    assert "advanced" in data["results"]

    adv = data["results"]["advanced"]
    assert "dossier" in adv
    dossier = adv["dossier"]

    assert "overall_vetting_score" in dossier
    assert isinstance(dossier["overall_vetting_score"], (int, float))
    assert 0.0 <= dossier["overall_vetting_score"] <= 100.0
    assert dossier["architecture_score"] >= 0.0
    assert dossier["concurrency_scalability_score"] >= 0.0
    assert dossier["code_quality_reusability_score"] >= 0.0
    assert dossier["recommendation"] in ["STRONG_HIRE", "HIRE", "LEAN_NO", "REJECT"]
    assert len(dossier["executive_summary"]) > 10

    # Verify telemetry metadata is populated dynamically
    assert adv["tokens"] > 0
    assert adv["duration_ms"] > 0


def test_dynamic_assertion_different_submissions_and_seniorities(client):
    """4. Test dynamic assertion: distinct submissions yield different scores & seniority alters critic feedback."""
    # Part A: Flawed diff vs Optimal diff
    flawed_diff = "---\n+++ b/src/cache.py\n@@ -10,4 +10,12 @@\n+def update_cache_without_locks(key, value):\n+    global_in_memory_cache[key] = value\n+    leak_buffer.append(bytearray(1024 * 1024 * 50))\n"
    optimal_diff = "---\n+++ b/src/cache.py\n@@ -10,4 +10,12 @@\n+async def update_cache_atomic(key, value, redis_client):\n+    async with redis_client.lock(f'lock:{key}', timeout=5):\n+        await redis_client.set(key, value, ex=3600)\n"

    # Post flawed diff
    resp_flawed = client.post(
        "/api/evaluate/case_01",
        data=json.dumps({"runner": "advanced", "diff": flawed_diff, "seniority": "Senior"}),
        content_type="application/json"
    )
    assert resp_flawed.status_code == 200
    score_flawed = resp_flawed.json()["results"]["advanced"]["dossier"]["overall_vetting_score"]

    # Post optimal diff
    resp_optimal = client.post(
        "/api/evaluate/case_01",
        data=json.dumps({"runner": "advanced", "diff": optimal_diff, "seniority": "Senior"}),
        content_type="application/json"
    )
    assert resp_optimal.status_code == 200
    score_optimal = resp_optimal.json()["results"]["advanced"]["dossier"]["overall_vetting_score"]

    # Verify scores are genuinely dynamic and reflect code quality
    assert score_flawed != score_optimal, f"Expected dynamic scores to differ, got {score_flawed} == {score_optimal}"
    assert score_optimal > score_flawed, f"Optimal score ({score_optimal}) should exceed flawed score ({score_flawed})"

    # Part B: Seniority impact on evaluation
    # Junior candidate evaluated on the flawed diff
    resp_junior = client.post(
        "/api/evaluate/case_01",
        data=json.dumps({"runner": "advanced", "diff": flawed_diff, "seniority": "Junior"}),
        content_type="application/json"
    )
    assert resp_junior.status_code == 200
    score_junior = resp_junior.json()["results"]["advanced"]["dossier"]["overall_vetting_score"]

    # Seniority multiplier in SeniorEngineeringCriticAgent reduces penalty for junior candidates
    assert score_junior >= score_flawed, f"Junior candidate score ({score_junior}) should be more forgiving than senior ({score_flawed})"


def test_api_evaluate_takehome_validation_and_error_handling(client):
    """5. Test POST /api/evaluate-takehome/ with repository validation and robust error handling."""
    # Test A: Empty repository URL
    resp_empty = client.post(
        "/api/evaluate-takehome/",
        data=json.dumps({"repo_url": ""}),
        content_type="application/json"
    )
    assert resp_empty.status_code == 400
    assert "required" in resp_empty.json()["error"].lower()

    # Test B: Invalid URL protocol
    resp_invalid = client.post(
        "/api/evaluate-takehome/",
        data=json.dumps({"repo_url": "invalid-url-not-git"}),
        content_type="application/json"
    )
    assert resp_invalid.status_code == 400
    assert "invalid" in resp_invalid.json()["error"].lower()

    # Test C: Non-existent unreachable repository URL
    resp_nonexistent = client.post(
        "/api/evaluate-takehome/",
        data=json.dumps({"repo_url": "https://github.com/micro1_nonexistent_org_404/fake_repo_9999.git"}),
        content_type="application/json"
    )
    assert resp_nonexistent.status_code == 400
    assert "failed" in resp_nonexistent.json()["error"].lower()

    # Test D: Valid local git repository ingestion in sandbox
    with tempfile.TemporaryDirectory() as temp_repo:
        subprocess.run(["git", "init"], cwd=temp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@micro1.ai"], cwd=temp_repo, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=temp_repo, check=True)
        sample_file = os.path.join(temp_repo, "main.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("def handle_request():\n    return {'status': 200}\n")
        subprocess.run(["git", "add", "main.py"], cwd=temp_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_repo, check=True, capture_output=True)

        resp_valid = client.post(
            "/api/evaluate-takehome/",
            data=json.dumps({"repo_url": temp_repo, "mode": "full_repo", "runner": "advanced"}),
            content_type="application/json"
        )
        assert resp_valid.status_code == 200
        data = resp_valid.json()
        assert data["success"] is True
        assert "spec" in data
        assert "submission" in data
        assert "results" in data
        assert "advanced" in data["results"]


def test_api_trajectories_listing(client):
    """6. Test GET /api/trajectories/ lists existing trajectories and trace files."""
    response = client.get("/api/trajectories/")
    assert response.status_code == 200
    data = response.json()

    assert "count" in data
    assert "trajectories" in data
    assert data["count"] > 0
    assert len(data["trajectories"]) == data["count"]

    # Verify trajectory record structure
    first = data["trajectories"][0]
    assert "filename" in first
    assert "format" in first
    assert "runner_type" in first
    assert "size_kb" in first
    assert "relative_path" in first
