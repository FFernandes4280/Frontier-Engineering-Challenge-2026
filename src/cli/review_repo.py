"""CLI for reviewing custom web git repositories."""

import asyncio

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from src.agents.orchestrator_fsm import HolisticVettingOrchestrator
from src.baseline.runner import BaselineVettingRunner
from src.tools.git_importer import GitRepoImporter

app = typer.Typer(help="Review custom Git repositories and PRs.")
console = Console()


async def evaluate_custom_repo(repo_url: str, commit: str, runner_type: str, mode: str = "diff"):
    console.print(f"\n[bold cyan]📥 Cloning and analyzing AST for {repo_url}...[/bold cyan]")
    
    importer = GitRepoImporter(repo_url=repo_url, target_commit=commit, mode=mode)
    spec, submission = importer.ingest()
    
    console.print(f"✅ Ingestion complete. Found {len(spec.existing_codebase_map)} modules in AST tree.")
    console.print(f"✅ Extracted diff for commit: [yellow]{submission.commit_messages[0][:50]}...[/yellow]")
    
    runners_to_run = ["baseline", "advanced"] if runner_type == "both" else [runner_type]
    results = {}

    for r_type in runners_to_run:
        console.print(f"\n[bold magenta]🚀 Executing {r_type.upper()} Evaluation...[/bold magenta]")
        if r_type == "baseline":
            runner = BaselineVettingRunner()
        else:
            runner = HolisticVettingOrchestrator()
            
        dossier, logger = await runner.evaluate_submission(submission, spec)
        results[r_type] = dossier
        
        console.print(f"\n[bold]⚖️ {r_type.upper()} Dossier Result:[/bold]")
        console.print(f"Score: {dossier.overall_vetting_score}/100")
        console.print(f"Recommendation: {dossier.recommendation.value}")
        console.print(f"Flaws Flagged: {len(dossier.primary_flaws_flagged)}")
        
        # Render the executive summary nicely
        console.print(Markdown(dossier.executive_summary))

    if runner_type == "both":
        table = Table(title=f"🏆 Live Comparative Review: {repo_url.split('/')[-1]}", header_style="bold green")
        table.add_column("Metric", style="cyan")
        table.add_column("Baseline (Single-Prompt)", justify="right")
        table.add_column("Advanced (FSM Squad)", justify="right")
        
        table.add_row("Overall Score", str(results["baseline"].overall_vetting_score), str(results["advanced"].overall_vetting_score))
        table.add_row("Recommendation", results["baseline"].recommendation.value, results["advanced"].recommendation.value)
        table.add_row("Flaws Flagged", str(len(results["baseline"].primary_flaws_flagged)), str(len(results["advanced"].primary_flaws_flagged)))
        
        console.print("\n")
        console.print(table)


@app.command()
def review(
    repo: str = typer.Option(..., "--repo", "-g", help="URL of the Git repository to review"),
    commit: str = typer.Option("HEAD", "--commit", "-c", help="Target commit hash or HEAD"),
    runner: str = typer.Option("both", "--runner", "-r", help="Runner: baseline, advanced, or both"),
    mode: str = typer.Option("diff", "--mode", "-m", help="Ingestion mode: diff or full_repo")
):
    """Run a live review on a custom Git repository."""
    asyncio.run(evaluate_custom_repo(repo, commit, runner, mode))


if __name__ == "__main__":
    app()
