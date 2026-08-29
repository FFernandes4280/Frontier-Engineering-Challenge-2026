"""Interactive Terminal Viewer for Agent Trajectories."""

import os
import glob
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


console = Console()


def list_available_traces(trace_dir: str = "./traces") -> list[str]:
    """List all available trajectory JSON files."""
    if not os.path.exists(trace_dir):
        return []
    return sorted(glob.glob(os.path.join(trace_dir, "*.json")), reverse=True)


def display_trace(json_path: str) -> None:
    """Render a trajectory file beautifully in the terminal."""
    if not os.path.exists(json_path):
        console.print(f"[bold red]File not found:[/bold red] {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    status_style = "green" if data.get("success") else "red"
    status_text = "SUCCESS" if data.get("success") else "FAILED"

    console.print(
        Panel.fit(
            f"[bold cyan]Task ID:[/bold cyan] {data.get('task_id')} | "
            f"[bold magenta]Runner:[/bold magenta] {data.get('runner_type')} | "
            f"[bold {status_style}]Status:[/bold {status_style}] {status_text}\n"
            f"[bold yellow]Tokens:[/bold yellow] {data.get('total_tokens')} | "
            f"[bold green]Cost:[/bold green] ${data.get('total_cost_usd', 0):.5f} | "
            f"[bold blue]Duration:[/bold blue] {data.get('total_duration_ms', 0):.1f}ms",
            title="🎯 Trajectory Overview",
            border_style="cyan"
        )
    )

    table = Table(title="Execution Steps", show_header=True, header_style="bold magenta")
    table.add_column("Step", justify="center", style="dim", width=6)
    table.add_column("Event Type", style="bold")
    table.add_column("Agent / State", style="cyan")
    table.add_column("Tokens", justify="right", style="yellow")
    table.add_column("Cost ($)", justify="right", style="green")
    table.add_column("Latency", justify="right", style="blue")

    for s in data.get("steps", []):
        table.add_row(
            str(s.get("step_id")),
            s.get("event_type", ""),
            f"{s.get('agent_name', '')} ({s.get('state', '-')})",
            str(s.get("tokens", 0)),
            f"${s.get('cost_usd', 0):.4f}",
            f"{s.get('latency_ms', 0):.1f}ms"
        )

    console.print(table)


if __name__ == "__main__":
    traces = list_available_traces()
    if traces:
        display_trace(traces[0])
    else:
        console.print("[yellow]No traces found in ./traces directory.[/yellow]")
