"""Tool: Blast Radius & Diff Quality Analyzer."""

import re
from typing import List
from src.core.domain import CandidateSubmission, BlastRadiusMetrics, ScenarioSpec


class BlastRadiusAnalyzer:
    """Calculates diff metrics, impact surface, and focus score."""

    @staticmethod
    def analyze(submission: CandidateSubmission, spec: ScenarioSpec) -> BlastRadiusMetrics:
        files_modified = len(submission.file_changes)
        total_lines = sum(fc.added_lines + fc.deleted_lines for fc in submission.file_changes)

        # Check if modified files are in the core domain or extraneous files
        unnecessary = []
        for fc in submission.file_changes:
            # If changing test runner config or non-relevant configs
            if "conftest" in fc.path or "pytest.ini" in fc.path or "tox.ini" in fc.path:
                unnecessary.append(fc.path)

        # Estimate cyclomatic complexity change from diff
        complexity_delta = 0
        branching_keywords = ["if ", "elif ", "for ", "while ", "except ", "with ", " and ", " or "]
        for fc in submission.file_changes:
            for kw in branching_keywords:
                added_matches = len(re.findall(re.escape(kw), fc.diff_content))
                complexity_delta += added_matches

        # Calculate blast radius score (1.0 is optimal, penalize unnecessary modifications or huge diffs)
        base_score = 1.0
        if files_modified > 5:
            base_score -= 0.15 * (files_modified - 5)
        if len(unnecessary) > 0:
            base_score -= 0.25 * len(unnecessary)
        if total_lines > 300:
            base_score -= 0.10

        final_score = max(0.1, min(1.0, base_score))

        return BlastRadiusMetrics(
            files_modified_count=files_modified,
            total_lines_changed=total_lines,
            unnecessary_files_modified=unnecessary,
            cyclomatic_complexity_delta=complexity_delta,
            blast_radius_score=round(final_score, 2)
        )
