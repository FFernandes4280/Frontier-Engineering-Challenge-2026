"""Agent 2: Code Evolution & Context Alignment Agent."""

from src.core.domain import CandidateSubmission, ScenarioSpec, BlastRadiusMetrics, ContextAlignmentMetrics
from src.tools.blast_radius import BlastRadiusAnalyzer
from src.tools.context_inspector import ContextInspector


class CodeEvolutionAlignmentAgent:
    """Evaluates the candidate's diff surface, codebase alignment, and architectural reusability."""

    def __init__(self, name: str = "CodeEvolutionAlignmentAgent"):
        self.name = name

    def evaluate_alignment(
        self,
        submission: CandidateSubmission,
        spec: ScenarioSpec
    ) -> dict:
        """Runs blast radius and context inspection tools on the submission."""
        blast_metrics: BlastRadiusMetrics = BlastRadiusAnalyzer.analyze(submission, spec)
        context_metrics: ContextAlignmentMetrics = ContextInspector.inspect(submission, spec)

        findings = []
        if blast_metrics.blast_radius_score < 0.7:
            findings.append(f"Unfocused diff: modified {blast_metrics.files_modified_count} files with high cyclomatic complexity delta (+{blast_metrics.cyclomatic_complexity_delta}).")
        if not context_metrics.reused_existing_utilities:
            findings.append(f"Redundant code: ignored existing project modules: {', '.join(context_metrics.ignored_existing_modules)}.")
        if not context_metrics.api_contract_preserved:
            findings.append("Breaking change: altered existing public API response structure or status codes.")

        return {
            "blast_radius": blast_metrics.model_dump(),
            "context_alignment": context_metrics.model_dump(),
            "findings": findings,
            "alignment_passed": blast_metrics.blast_radius_score >= 0.6 and context_metrics.alignment_score >= 0.6
        }
