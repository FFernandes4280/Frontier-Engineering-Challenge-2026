"""Views and REST API endpoints for the micro1 Frontier Engineering Challenge Web Dashboard."""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from src.baseline.runner import BaselineVettingRunner
from src.core.domain import CandidateSubmission, FileChange, ScenarioSpec, SeniorVettingDossier
from src.tools.git_importer import GitRepoImporter

BASE_DIR = Path(settings.BASE_DIR)
DATASET_PATH = BASE_DIR / "eval" / "dataset" / "cases.json"
BENCHMARK_RESULTS_PATH = BASE_DIR / "eval" / "benchmark_results.json"
TRAJECTORIES_DIR = BASE_DIR / "trajectories"
TRACES_DIR = BASE_DIR / "traces"


def _load_cases() -> List[Dict[str, Any]]:
    """Helper to load benchmark cases from disk."""
    if DATASET_PATH.exists():
        try:
            with open(DATASET_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _load_benchmark_results() -> Dict[str, Any]:
    """Helper to load consolidated benchmark metrics results from disk."""
    if BENCHMARK_RESULTS_PATH.exists():
        try:
            with open(BENCHMARK_RESULTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def index_view(request: HttpRequest) -> HttpResponse:
    """Render the main dashboard UI."""
    cases = _load_cases()
    results = _load_benchmark_results()
    context = {
        "cases": cases,
        "total_cases": len(cases),
        "benchmark_results": results,
        "summaries": results.get("summaries", {}),
        "baseline_summary": results.get("summaries", {}).get("baseline", {}),
        "advanced_summary": results.get("summaries", {}).get("advanced", {}),
        "baseline_model": os.getenv("BASELINE_MODEL", "groq/openai/gpt-oss-120b"),
        "advanced_model": os.getenv("ADVANCED_MODEL", "groq/openai/gpt-oss-20b"),
    }
    return render(request, "dashboard_ui/index.html", context)


def cases_list_view(request: HttpRequest) -> HttpResponse:
    """List of all SWE benchmark scenarios."""
    cases = _load_cases()
    return render(request, "dashboard_ui/cases_list.html", {"cases": cases, "total_cases": len(cases)})


def case_detail_view(request: HttpRequest, case_id: str) -> HttpResponse:
    """Direct inspector for a specific scenario."""
    cases = _load_cases()
    target_case = next((c for c in cases if c.get("case_id") == case_id), None)
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


def traces_viewer(request: HttpRequest) -> HttpResponse:
    """Trajectory audit traces viewer page."""
    trace_files = []
    seen = set()
    for folder in [TRAJECTORIES_DIR, TRACES_DIR]:
        if folder.exists():
            for f in sorted(os.listdir(folder), reverse=True):
                if f not in seen and (f.endswith(".md") or f.endswith(".jsonl") or f.endswith(".json")):
                    seen.add(f)
                    path = folder / f
                    size_kb = round(os.path.getsize(path) / 1024, 1)
                    trace_files.append({
                        "name": f,
                        "size_kb": size_kb,
                        "is_md": f.endswith(".md"),
                        "is_json": f.endswith(".json"),
                        "is_jsonl": f.endswith(".jsonl")
                    })
    selected_file = request.GET.get("file", "")
    content = ""
    if selected_file:
        for folder in [TRAJECTORIES_DIR, TRACES_DIR]:
            target_path = folder / selected_file
            if target_path.exists():
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                break
    return render(request, "dashboard_ui/traces_viewer.html", {
        "files": trace_files,
        "selected_file": selected_file,
        "content": content
    })


def custom_review_view(request: HttpRequest) -> HttpResponse:
    """Take-Home Evaluator page."""
    return render(request, "dashboard_ui/custom_review.html")


def api_benchmark_data(request: HttpRequest) -> JsonResponse:
    """REST API: Returns real benchmark dataset cases (15 scenarios) and results from disk."""
    cases = _load_cases()
    results = _load_benchmark_results()
    return JsonResponse({
        "status": "success",
        "total_cases": len(cases),
        "cases": cases,
        "benchmark_results": results,
        "summaries": results.get("summaries", {})
    }, json_dumps_params={"indent": 2})


@csrf_exempt
@require_http_methods(["GET", "POST"])
async def api_evaluate_case(request: HttpRequest, case_id: str) -> JsonResponse:
    """REST API: Dynamically evaluate a benchmark case in real time."""
    cases = _load_cases()
    target_case: Optional[Dict[str, Any]] = None

    for c in cases:
        if c.get("case_id") == case_id or str(c.get("case_id")) == str(case_id):
            target_case = c
            break

    if not target_case:
        try:
            case_idx = int(case_id) - 1
            if 0 <= case_idx < len(cases):
                target_case = cases[case_idx]
        except ValueError:
            pass

    if not target_case:
        return JsonResponse({
            "status": "error",
            "message": f"Benchmark scenario '{case_id}' not found in dataset."
        }, status=404)

    payload = {}
    if request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = {}
    elif request.POST:
        payload = request.POST.dict()

    runner_type = payload.get("runner", request.GET.get("runner", "advanced")).lower()
    model_override = payload.get("model", request.GET.get("model", None))
    custom_diff = payload.get("diff") or payload.get("full_diff")
    custom_notes = payload.get("notes") or payload.get("explanation_notes")
    custom_seniority = payload.get("seniority") or payload.get("difficulty")

    spec_dict = dict(target_case.get("spec", {}))
    if "ground_truth_flaw" not in spec_dict:
        spec_dict["ground_truth_flaw"] = target_case.get("ground_truth_flaw", "Undisclosed flaw")
    if "expected_optimal_solution" not in spec_dict:
        spec_dict["expected_optimal_solution"] = target_case.get("expected_optimal_solution", "Optimal design")
    if custom_seniority:
        spec_dict["difficulty"] = custom_seniority

    try:
        spec = ScenarioSpec.model_validate(spec_dict)
        sub_dict = dict(target_case.get("submission", {}))
        if custom_diff:
            sub_dict["full_diff"] = custom_diff
            sub_dict["file_changes"] = [
                FileChange(
                    path="src/service.py",
                    diff_content=custom_diff,
                    is_new_file=False,
                    added_lines=sum(1 for line in custom_diff.splitlines() if line.startswith("+")),
                    deleted_lines=sum(1 for line in custom_diff.splitlines() if line.startswith("-"))
                )
            ]
        if custom_notes:
            sub_dict["explanation_notes"] = custom_notes

        submission = CandidateSubmission.model_validate(sub_dict)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Failed to validate scenario schema: {str(e)}"
        }, status=400)

    ground_truth = target_case.get("human_senior_verdict", {})
    results: Dict[str, Any] = {}

    try:
        if runner_type in ["baseline", "both"]:
            runner_b = BaselineVettingRunner(
                model=model_override,
                trace_dir=str(TRAJECTORIES_DIR),
                verbose=False
            )
            dossier_b, logger_b = await runner_b.evaluate_submission(submission, spec)
            results["baseline"] = {
                "dossier": dossier_b.model_dump(),
                "duration_ms": logger_b.trajectory.total_duration_ms,
                "tokens": logger_b.trajectory.total_tokens,
                "cost_usd": logger_b.trajectory.total_cost_usd,
                "model": runner_b.model,
                "trajectory_file": os.path.basename(logger_b.json_path),
                "trajectory_log": logger_b.trajectory.model_dump(),
                "agreed_with_truth": (dossier_b.overall_vetting_score >= 65.0) == ground_truth.get("should_hire", True)
            }

        if runner_type in ["advanced", "both"]:
            runner_a = HolisticVettingOrchestrator(
                trace_dir=str(TRAJECTORIES_DIR),
                verbose=False,
                interactive_human_gate=False
            )
            dossier_a, logger_a = await runner_a.evaluate_submission(submission, spec)
            adv_model = os.getenv("ADVANCED_MODEL", "groq/openai/gpt-oss-20b")
            results["advanced"] = {
                "dossier": dossier_a.model_dump(),
                "duration_ms": logger_a.trajectory.total_duration_ms,
                "tokens": logger_a.trajectory.total_tokens,
                "cost_usd": logger_a.trajectory.total_cost_usd,
                "model": adv_model,
                "trajectory_file": os.path.basename(logger_a.json_path),
                "trajectory_log": logger_a.trajectory.model_dump(),
                "agreed_with_truth": (dossier_a.overall_vetting_score >= 65.0) == ground_truth.get("should_hire", True)
            }

        primary_key = "advanced" if "advanced" in results else "baseline"
        primary_res = results.get(primary_key, {})

        return JsonResponse({
            "status": "success",
            "case_id": target_case.get("case_id"),
            "title": target_case.get("title"),
            "runner": runner_type,
            "ground_truth": ground_truth,
            "dossier": primary_res.get("dossier"),
            "tokens": primary_res.get("tokens", 0),
            "cost_usd": primary_res.get("cost_usd", 0.0),
            "duration_ms": primary_res.get("duration_ms", 0.0),
            "trajectory_file": primary_res.get("trajectory_file"),
            "results": results
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Pipeline evaluation failed: {str(e)}"
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
async def api_evaluate_takehome(request: HttpRequest) -> JsonResponse:
    """REST API: Clone full Git repo, build polyglot AST, and execute live vetting pipeline."""
    data = {}
    if request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            data = {}
    elif request.POST:
        data = request.POST.dict()

    repo_url = data.get("repo_url", "").strip()
    mode = data.get("mode", "full_repo").strip() or "full_repo"
    commit_hash = data.get("commit", data.get("commit_hash", "HEAD")).strip() or "HEAD"
    runner_type = data.get("runner", "advanced").strip().lower() or "advanced"
    model_override = data.get("model", None)

    if not repo_url:
        return JsonResponse({
            "status": "error",
            "message": "Repository URL is required.",
            "error": "Repository URL is required."
        }, status=400)

    if not (repo_url.startswith("http://") or repo_url.startswith("https://") or repo_url.startswith("git://") or repo_url.startswith("git@") or os.path.exists(repo_url)):
        return JsonResponse({
            "status": "error",
            "message": f"Invalid repository URL format: '{repo_url}'. Must be a valid HTTP(S) or Git URL.",
            "error": f"Invalid repository URL format: '{repo_url}'. Must be a valid HTTP(S) or Git URL."
        }, status=400)

    try:
        importer = GitRepoImporter(repo_url=repo_url, target_commit=commit_hash, mode=mode)
        spec, submission = await asyncio.to_thread(importer.ingest)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Git repository cloning / AST ingestion failed: {str(e)}",
            "error": f"Failed to clone or ingest git repository: {str(e)}"
        }, status=400)

    results = {}

    try:
        if runner_type in ["baseline", "both"]:
            runner_b = BaselineVettingRunner(
                model=model_override,
                trace_dir=str(TRAJECTORIES_DIR),
                verbose=False
            )
            dossier_b, logger_b = await runner_b.evaluate_submission(submission, spec)
            results["baseline"] = {
                "dossier": dossier_b.model_dump(),
                "duration_ms": logger_b.trajectory.total_duration_ms,
                "tokens": logger_b.trajectory.total_tokens,
                "cost_usd": logger_b.trajectory.total_cost_usd,
                "model": runner_b.model,
                "trajectory_file": os.path.basename(logger_b.json_path),
                "trajectory_log": logger_b.trajectory.model_dump()
            }

        if runner_type in ["advanced", "both"]:
            runner_a = HolisticVettingOrchestrator(
                trace_dir=str(TRAJECTORIES_DIR),
                verbose=False,
                interactive_human_gate=False
            )
            dossier_a, logger_a = await runner_a.evaluate_submission(submission, spec)
            adv_model = os.getenv("ADVANCED_MODEL", "groq/openai/gpt-oss-20b")
            results["advanced"] = {
                "dossier": dossier_a.model_dump(),
                "duration_ms": logger_a.trajectory.total_duration_ms,
                "tokens": logger_a.trajectory.total_tokens,
                "cost_usd": logger_a.trajectory.total_cost_usd,
                "model": adv_model,
                "trajectory_file": os.path.basename(logger_a.json_path),
                "trajectory_log": logger_a.trajectory.model_dump()
            }

        primary_key = "advanced" if "advanced" in results else "baseline"
        primary_res = results.get(primary_key, {})

        return JsonResponse({
            "status": "success",
            "success": True,
            "repo_url": repo_url,
            "mode": mode,
            "commit": commit_hash,
            "modules_analyzed": len(spec.existing_codebase_map),
            "ast_map": spec.existing_codebase_map,
            "files_changed_count": len(submission.file_changes),
            "spec": spec.model_dump(),
            "submission": submission.model_dump(),
            "dossier": primary_res.get("dossier"),
            "tokens": primary_res.get("tokens", 0),
            "cost_usd": primary_res.get("cost_usd", 0.0),
            "duration_ms": primary_res.get("duration_ms", 0.0),
            "trajectory_file": primary_res.get("trajectory_file"),
            "results": results
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Take-Home evaluation pipeline failed: {str(e)}"
        }, status=500)


def api_trajectories(request: HttpRequest) -> JsonResponse:
    """REST API: List all audit trajectories and execution traces."""
    trajectories = []
    seen = set()

    for folder, source_name in [(TRAJECTORIES_DIR, "trajectories"), (TRACES_DIR, "traces")]:
        if folder.exists():
            for f in sorted(os.listdir(folder), reverse=True):
                if f not in seen and (f.endswith(".jsonl") or f.endswith(".json") or f.endswith(".md")):
                    seen.add(f)
                    path = folder / f
                    stat = os.stat(path)
                    size_kb = round(stat.st_size / 1024, 2)
                    ext = f.split(".")[-1]
                    parts = f.split("_")
                    runner_type = parts[0] if len(parts) > 1 else "unknown"
                    task_id = parts[1] if len(parts) > 2 else "unknown"

                    trajectories.append({
                        "filename": f,
                        "file_type": ext,
                        "format": ext,
                        "source_folder": source_name,
                        "runner": runner_type,
                        "runner_type": runner_type,
                        "task_id": task_id,
                        "size_bytes": stat.st_size,
                        "size_kb": size_kb,
                        "modified_time": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "relative_path": f"{source_name}/{f}"
                    })

    return JsonResponse({
        "status": "success",
        "count": len(trajectories),
        "total": len(trajectories),
        "trajectories": trajectories
    }, json_dumps_params={"indent": 2})


def api_trajectory_detail(request: HttpRequest, filename: str) -> HttpResponse:
    """REST API: Read and return specific trajectory content safely."""
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name in (".", ".."):
        return JsonResponse({"status": "error", "message": "Invalid filename."}, status=400)

    target_path = None
    for folder in [TRAJECTORIES_DIR, TRACES_DIR]:
        candidate = folder / safe_name
        if candidate.exists() and candidate.is_file():
            target_path = candidate
            break

    if not target_path:
        return JsonResponse({
            "status": "error",
            "message": f"Trajectory file '{safe_name}' not found."
        }, status=404)

    try:
        if safe_name.endswith(".json"):
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return JsonResponse({"status": "success", "filename": safe_name, "file_type": "json", "data": data})

        elif safe_name.endswith(".jsonl"):
            lines = []
            with open(target_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        lines.append(json.loads(line))
            return JsonResponse({"status": "success", "filename": safe_name, "file_type": "jsonl", "data": lines})

        elif safe_name.endswith(".md"):
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            raw = request.GET.get("raw", "false").lower() in ("true", "1")
            if raw:
                return HttpResponse(content, content_type="text/markdown; charset=utf-8")
            return JsonResponse({"status": "success", "filename": safe_name, "file_type": "md", "content": content})

        else:
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return HttpResponse(content, content_type="text/plain; charset=utf-8")

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Failed to read trajectory file: {str(e)}"
        }, status=500)
