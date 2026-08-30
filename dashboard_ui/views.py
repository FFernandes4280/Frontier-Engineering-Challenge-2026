"""Django View Handlers for the micro1 Senior Vetting Benchmark Web Dashboard."""

import os
import json
import asyncio
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from src.core.domain import ScenarioSpec, CandidateSubmission
from src.baseline.runner import BaselineVettingRunner
from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from src.tools.git_importer import GitRepoImporter

DATASET_PATH = "eval/dataset/cases.json"
BENCHMARK_RESULTS_PATH = "eval/benchmark_results.json"
TRACES_DIR = "traces"


def _load_cases():
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _load_benchmark_results():
    if os.path.exists(BENCHMARK_RESULTS_PATH):
        with open(BENCHMARK_RESULTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def index_view(request):
    """Main Overview Dashboard with benchmark stats, KPIs, and case distribution."""
    cases = _load_cases()
    results = _load_benchmark_results()

    total_cases = len(cases)
    summaries = results.get("summaries", {}) if results else {}

    baseline_summary = summaries.get("baseline", {})
    advanced_summary = summaries.get("advanced", {})

    context = {
        "total_cases": total_cases,
        "cases": cases,
        "benchmark_results": results,
        "baseline_summary": baseline_summary,
        "advanced_summary": advanced_summary,
        "delta_accuracy": round((advanced_summary.get("success_rate_pct", 0) - baseline_summary.get("success_rate_pct", 0)), 1),
        "delta_fidelity": round((advanced_summary.get("average_score", 0) - baseline_summary.get("average_score", 0)) * 100, 1),
    }
    return render(request, "dashboard_ui/index.html", context)


def cases_list_view(request):
    """List of all 15 SWE-bench grounded scenarios with filter by status/difficulty."""
    cases = _load_cases()
    return render(request, "dashboard_ui/cases_list.html", {"cases": cases})


def case_detail_view(request, case_id):
    """Deep-dive inspector for a single scenario with live interactive evaluation runner."""
    cases = _load_cases()
    target_case = next((c for c in cases if c["case_id"] == case_id), None)
    if not target_case:
        raise Http404(f"Scenario {case_id} not found.")

    spec = target_case.get("spec", {})
    full_diff = target_case.get("submission", {}).get("full_diff", "")
    ground_truth = target_case.get("human_senior_verdict", {})

    context = {
        "case": target_case,
        "spec": spec,
        "full_diff": full_diff,
        "ground_truth": ground_truth,
    }
    return render(request, "dashboard_ui/case_detail.html", context)


@csrf_exempt
def run_case_api(request, case_id):
    """Async API endpoint to execute either Baseline or Advanced runner against a case."""
    cases = _load_cases()
    target_case = next((c for c in cases if c["case_id"] == case_id), None)
    if not target_case:
        return JsonResponse({"error": f"Scenario {case_id} not found."}, status=404)

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            data = {}
    else:
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
                "agreed_with_truth": (dossier_b.overall_vetting_score >= 65.0) == ground_truth.get("should_hire", True)
            }

        if runner_type in ["advanced", "both"]:
            runner_a = HolisticVettingOrchestrator()
            dossier_a, logger_a = await runner_a.evaluate_submission(submission, spec)
            results["advanced"] = {
                "dossier": dossier_a.model_dump(),
                "duration_ms": logger_a.trajectory.total_duration_ms,
                "tokens": logger_a.trajectory.total_tokens,
                "cost_usd": logger_a.trajectory.total_cost_usd,
                "agreed_with_truth": (dossier_a.overall_vetting_score >= 65.0) == ground_truth.get("should_hire", True)
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
    """Take-Home Assignment & Full Git Repository Evaluator."""
    if request.method == "POST":
        repo_url = request.POST.get("repo_url", "").strip()
        mode = request.POST.get("mode", "full_repo").strip()
        commit_hash = request.POST.get("commit_hash", "HEAD").strip() or "HEAD"
        runner_type = request.POST.get("runner", "both")

        if not repo_url:
            return render(request, "dashboard_ui/custom_review.html", {"error": "Repository URL is required."})

        try:
            importer = GitRepoImporter(repo_url=repo_url, target_commit=commit_hash, mode=mode)
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
                "mode": mode,
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

    return render(request, "dashboard_ui/traces_viewer.html", {
        "trace_files": trace_files,
        "selected_file": selected_file,
        "content": content
    })
