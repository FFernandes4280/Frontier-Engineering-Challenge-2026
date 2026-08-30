"""Django views for micro1 Frontier Engineering Challenge Web Dashboard."""

import os
import json
import asyncio
from typing import List, Dict, Any
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from src.core.domain import ScenarioSpec, CandidateSubmission, SeniorVettingDossier, RecommendationType
from src.baseline.runner import BaselineVettingRunner
from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from src.tools.git_importer import GitRepoImporter
from eval.metrics import compute_benchmark_summary, EvaluationResult


DATASET_PATH = "eval/dataset/cases.json"
TRACES_DIR = "./traces"


def load_dataset() -> List[Dict[str, Any]]:
    """Loads benchmark test cases from JSON file."""
    if not os.path.exists(DATASET_PATH):
        return []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def index(request):
    """Main Dashboard Overview."""
    cases = load_dataset()
    baseline_model = os.getenv("BASELINE_MODEL", "groq/openai/gpt-oss-120b")
    advanced_model = os.getenv("ADVANCED_MODEL", "groq/qwen/qwen3.8-27b")

    # Load latest benchmark results if available
    benchmark_data = {}
    if os.path.exists("eval/benchmark_results.json"):
        try:
            with open("eval/benchmark_results.json", "r", encoding="utf-8") as f:
                benchmark_data = json.load(f)
        except Exception:
            pass

    context = {
        "cases_count": len(cases),
        "cases": cases,
        "baseline_model": baseline_model,
        "advanced_model": advanced_model,
        "benchmark": benchmark_data.get("summaries", {}),
    }
    return render(request, "dashboard_ui/index.html", context)


def cases_list(request):
    """Catalog of all 10 SWE-bench open source cases."""
    cases = load_dataset()
    return render(request, "dashboard_ui/cases_list.html", {"cases": cases})


def case_detail(request, case_id):
    """Detailed view of a single benchmark test case."""
    cases = load_dataset()
    target_case = next((c for c in cases if c["case_id"] == case_id), None)
    if not target_case:
        return redirect("cases_list")

    # Determine diff text
    sub = target_case.get("submission", {})
    full_diff = sub.get("full_diff", "")
    if not full_diff and "file_changes" in sub:
        full_diff = "\n".join([fc.get("diff_content", "") for fc in sub["file_changes"]])

    context = {
        "case": target_case,
        "spec": target_case.get("spec", {}),
        "submission": sub,
        "full_diff": full_diff,
        "ground_truth": target_case.get("human_senior_verdict", {}),
        "baseline_model": os.getenv("BASELINE_MODEL", "groq/openai/gpt-oss-120b"),
        "advanced_model": os.getenv("ADVANCED_MODEL", "groq/qwen/qwen3.8-27b"),
    }
    return render(request, "dashboard_ui/case_detail.html", context)


@csrf_exempt
def run_case_api(request, case_id):
    """AJAX API to evaluate a single case with Baseline, Advanced, or Both."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    cases = load_dataset()
    target_case = next((c for c in cases if c["case_id"] == case_id), None)
    if not target_case:
        return JsonResponse({"error": "Case not found"}, status=404)

    try:
        data = json.loads(request.body) if request.body else {}
    except Exception:
        data = {}

    runner_type = data.get("runner", "both")

    spec_dict = dict(target_case["spec"])
    if "ground_truth_flaw" not in spec_dict:
        spec_dict["ground_truth_flaw"] = target_case.get("ground_truth_flaw", "Undisclosed flaw")
    if "expected_optimal_solution" not in spec_dict:
        spec_dict["expected_optimal_solution"] = target_case.get("expected_optimal_solution", "Optimal design")

    spec = ScenarioSpec.model_validate(spec_dict)
    submission = CandidateSubmission.model_validate(target_case["submission"])
    ground_truth = target_case.get("human_senior_verdict", {})

    results = {}

    async def execute():
        if runner_type in ["baseline", "both"]:
            runner_b = BaselineVettingRunner()
            dossier_b, logger_b = await runner_b.evaluate_submission(submission, spec)
            results["baseline"] = {
                "dossier": dossier_b.model_dump(),
                "duration_ms": logger_b.trajectory.total_duration_ms,
                "tokens": logger_b.trajectory.total_tokens,
                "cost_usd": logger_b.trajectory.total_cost_usd,
                "model": runner_b.model,
                "agreed_with_truth": (dossier_b.overall_vetting_score >= 70.0) == ground_truth.get("should_hire", True)
            }

        if runner_type in ["advanced", "both"]:
            runner_a = HolisticVettingOrchestrator()
            dossier_a, logger_a = await runner_a.evaluate_submission(submission, spec)
            results["advanced"] = {
                "dossier": dossier_a.model_dump(),
                "duration_ms": logger_a.trajectory.total_duration_ms,
                "tokens": logger_a.trajectory.total_tokens,
                "cost_usd": logger_a.trajectory.total_cost_usd,
                "agreed_with_truth": (dossier_a.overall_vetting_score >= 70.0) == ground_truth.get("should_hire", True)
            }

    asyncio.run(execute())

    return JsonResponse({
        "case_id": case_id,
        "title": target_case["title"],
        "ground_truth": ground_truth,
        "results": results
    })


@csrf_exempt
def custom_review_view(request):
    """Web Reviewer for any Custom Web Git Repository URL."""
    if request.method == "POST":
        repo_url = request.POST.get("repo_url", "").strip()
        commit_hash = request.POST.get("commit_hash", "HEAD").strip() or "HEAD"
        runner_type = request.POST.get("runner", "both")

        if not repo_url:
            return render(request, "dashboard_ui/custom_review.html", {"error": "Repository URL is required."})

        try:
            importer = GitRepoImporter(repo_url=repo_url, target_commit=commit_hash)
            spec, submission = importer.ingest()

            results = {}

            async def execute():
                if runner_type in ["baseline", "both"]:
                    runner_b = BaselineVettingRunner()
                    dossier_b, logger_b = await runner_b.evaluate_submission(submission, spec)
                    results["baseline"] = {
                        "dossier": dossier_b.model_dump(),
                        "duration_ms": logger_b.trajectory.total_duration_ms,
                        "tokens": logger_b.trajectory.total_tokens,
                        "cost_usd": logger_b.trajectory.total_cost_usd,
                        "model": runner_b.model
                    }

                if runner_type in ["advanced", "both"]:
                    runner_a = HolisticVettingOrchestrator()
                    dossier_a, logger_a = await runner_a.evaluate_submission(submission, spec)
                    results["advanced"] = {
                        "dossier": dossier_a.model_dump(),
                        "duration_ms": logger_a.trajectory.total_duration_ms,
                        "tokens": logger_a.trajectory.total_tokens,
                        "cost_usd": logger_a.trajectory.total_cost_usd,
                    }

            asyncio.run(execute())

            return render(request, "dashboard_ui/custom_review.html", {
                "repo_url": repo_url,
                "commit_hash": commit_hash,
                "spec": spec.model_dump(),
                "submission": submission.model_dump(),
                "results": results,
                "success": True
            })
        except Exception as e:
            return render(request, "dashboard_ui/custom_review.html", {"error": f"Failed to ingest and evaluate repository: {str(e)}", "repo_url": repo_url})

    return render(request, "dashboard_ui/custom_review.html", {})


def traces_viewer(request):
    """File browser and viewer for audit trajectories (.md and .jsonl)."""
    trace_files = []
    if os.path.exists(TRACES_DIR):
        for f in sorted(os.listdir(TRACES_DIR), reverse=True):
            if f.endswith(".md") or f.endswith(".jsonl"):
                path = os.path.join(TRACES_DIR, f)
                size_kb = round(os.path.getsize(path) / 1024, 1)
                trace_files.append({"name": f, "size_kb": size_kb, "is_md": f.endswith(".md")})

    selected_file = request.GET.get("file", "")
    content = ""
    if selected_file and os.path.exists(os.path.join(TRACES_DIR, selected_file)):
        with open(os.path.join(TRACES_DIR, selected_file), "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    context = {
        "files": trace_files,
        "selected_file": selected_file,
        "content": content,
        "is_md": selected_file.endswith(".md")
    }
    return render(request, "dashboard_ui/traces_viewer.html", context)
