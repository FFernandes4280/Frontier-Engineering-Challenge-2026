"""Official Evaluation Harness: Runs Baseline & Advanced FSM Squad on Benchmark Dataset."""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
import typer
from rich.console import Console
from rich.table import Table

from src.core.domain import ScenarioSpec, CandidateSubmission, SeniorVettingDossier
from src.baseline.runner import BaselineVettingRunner
from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from eval.metrics import EvaluationResult, compute_benchmark_summary


console = Console()
app = typer.Typer(help="Frontier Engineering Challenge 2026 - Evaluation Harness")


def load_dataset(dataset_path: str = "eval/dataset/cases.json") -> List[Dict[str, Any]]:
    """Loads benchmark test cases from JSON file."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def execute_benchmark(runner_type: str, cases: List[Dict[str, Any]]) -> List[EvaluationResult]:
    """Executes the benchmark for a specific runner across all test cases with progress feedback."""
    results: List[EvaluationResult] = []

    if runner_type == "baseline":
        runner = BaselineVettingRunner()
    else:
        runner = HolisticVettingOrchestrator()

    for idx, item in enumerate(cases):
        spec_dict = dict(item["spec"])
        if "ground_truth_flaw" not in spec_dict:
            spec_dict["ground_truth_flaw"] = item.get("ground_truth_flaw", "Undisclosed flaw")
        if "expected_optimal_solution" not in spec_dict:
            spec_dict["expected_optimal_solution"] = item.get("expected_optimal_solution", "Optimal design")

        spec = ScenarioSpec.model_validate(spec_dict)
        submission = CandidateSubmission.model_validate(item["submission"])
        ground_truth = item.get("human_senior_verdict", {})

        console.print(f"  [dim][{idx+1:02d}/{len(cases):02d}][/dim] Evaluating [cyan]{item['title']}[/cyan] ({spec.github_repo})...")

        # Run evaluation
        dossier, logger = await runner.evaluate_submission(submission, spec)

        predicted_hire = (dossier.overall_vetting_score >= 70.0)
        expected_hire = ground_truth.get("should_hire", True)

        # Correctness: Did the system agree with human senior ground truth?
        decision_correct = (predicted_hire == expected_hire)
        score_error = abs(dossier.overall_vetting_score - ground_truth.get("ground_truth_score", 70.0))
        accuracy_score = max(0.0, 1.0 - (score_error / 100.0))

        status_emoji = "✅" if decision_correct else "❌"
        console.print(f"      {status_emoji} Score: [bold]{dossier.overall_vetting_score:.1f}[/bold] (Ground Truth: {ground_truth.get('ground_truth_score', '-')}) | Recommendation: {dossier.recommendation.value}")

        result = EvaluationResult(
            case_id=item["case_id"],
            runner_type=runner_type,
            passed=decision_correct,
            score=accuracy_score,
            latency_ms=logger.trajectory.total_duration_ms,
            tokens=logger.trajectory.total_tokens,
            cost_usd=logger.trajectory.total_cost_usd,
            human_time_estimated_sec=1800.0 if decision_correct else 300.0,
            details={
                "title": item["title"],
                "github_repo": spec.github_repo,
                "predicted_score": dossier.overall_vetting_score,
                "ground_truth_score": ground_truth.get("ground_truth_score"),
                "recommendation": dossier.recommendation.value,
                "flaws_detected": len(dossier.primary_flaws_flagged)
            }
        )
        results.append(result)
        # Courteous delay between requests
        await asyncio.sleep(1.2)

    return results


@app.command()
def run(
    runner: str = typer.Option("both", "--runner", "-r", help="Runner: baseline, advanced, or both"),
    dataset: str = typer.Option("eval/dataset/cases.json", "--dataset", "-d", help="Dataset path"),
    output: str = typer.Option("eval/benchmark_results.json", "--output", "-o", help="Output JSON path"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of test cases to evaluate (e.g. 2)")
):
    """Executes the benchmark and displays the official comparative table."""
    cases = load_dataset(dataset)
    if limit and limit > 0:
        cases = cases[:limit]
        console.print(f"[yellow]⚠️ Limiting benchmark evaluation to the first {limit} test cases.[/yellow]")

    runners_to_run = ["baseline", "advanced"] if runner == "both" else [runner]

    all_summaries = {}
    detailed_results = {}

    for r_type in runners_to_run:
        console.print(f"\n[bold cyan]🚀 Running {r_type.upper()} on {len(cases)} cases...[/bold cyan]")
        results = asyncio.run(execute_benchmark(r_type, cases))
        summary = compute_benchmark_summary(results)
        all_summaries[r_type] = summary
        detailed_results[r_type] = [r.model_dump() for r in results]

    # Save JSON results
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"summaries": {k: v.model_dump() for k, v in all_summaries.items()}, "details": detailed_results}, f, indent=2)

    # Render Comparative Table
    table = Table(
        title="🏆 micro1 Frontier Engineering Challenge 2026 — Official Benchmark Results",
        header_style="bold green",
        show_lines=True
    )
    table.add_column("Evaluation Metric", style="bold cyan")
    for r_type in runners_to_run:
        table.add_column(f"{r_type.capitalize()} Solution", justify="right")

    table.add_row("Total Scenarios Evaluated", *[str(all_summaries[r].total_cases) for r in runners_to_run])
    table.add_row("Hiring Alignment Accuracy", *[f"{all_summaries[r].success_rate_pct:.1f}% ({all_summaries[r].passed_cases}/{all_summaries[r].total_cases})" for r in runners_to_run])
    table.add_row("Fidelity Score (vs Human Ground Truth)", *[f"{all_summaries[r].average_score * 100:.1f} / 100" for r in runners_to_run])
    table.add_row("Avg Cost per Vetting Task ($)", *[f"${all_summaries[r].avg_cost_per_task_usd:.5f}" for r in runners_to_run])
    table.add_row("Avg Duration per Task (s)", *[f"{all_summaries[r].avg_latency_per_task_sec:.2f}s" for r in runners_to_run])
    table.add_row("Est. Human Engineering Time Saved", *[f"{all_summaries[r].total_human_time_saved_sec / 60.0:.1f} minutes" for r in runners_to_run])

    console.print("\n")
    console.print(table)
    console.print(f"\n[green]✅ Detailed benchmark results written to {output}[/green]")


if __name__ == "__main__":
    app()
