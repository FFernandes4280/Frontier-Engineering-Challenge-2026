"""Tool: Context & Architectural Reusability Inspector."""

import re
from typing import List, Dict
from src.core.domain import CandidateSubmission, ScenarioSpec, ContextAlignmentMetrics


class ContextInspector:
    """Evaluates whether the candidate respected existing codebase abstractions."""

    @staticmethod
    def inspect(submission: CandidateSubmission, spec: ScenarioSpec) -> ContextAlignmentMetrics:
        ignored_modules = []
        duplicated_logic = False
        api_contract_preserved = True
        alignment_score = 1.0

        full_diff = submission.full_diff or "\n".join(fc.diff_content for fc in submission.file_changes)

        # Check for reinventing existing utilities
        for existing_path, description in spec.existing_codebase_map.items():
            module_name = existing_path.split("/")[-1].replace(".py", "")
            # If the scenario has an existing helper and the diff does not import it, but implements similar logic
            if "validator" in existing_path and "re.compile" in full_diff:
                if module_name not in full_diff:
                    ignored_modules.append(existing_path)
                    duplicated_logic = True
                    alignment_score -= 0.3

            if "cache" in existing_path and "@lru_cache" in full_diff:
                if module_name not in full_diff:
                    ignored_modules.append(existing_path)
                    duplicated_logic = True
                    alignment_score -= 0.35

            if "db" in existing_path and "cursor.execute" in full_diff:
                if "Session" in description or "ORM" in description:
                    ignored_modules.append(existing_path)
                    alignment_score -= 0.2

        # Check for API contract preservation (e.g. modifying response status codes or removing fields)
        if "del response[" in full_diff or "status_code=400" in full_diff and "status_code=422" in full_diff:
            # Subtle contract change
            api_contract_preserved = False
            alignment_score -= 0.25

        alignment_score = max(0.1, min(1.0, alignment_score))

        return ContextAlignmentMetrics(
            reused_existing_utilities=len(ignored_modules) == 0,
            ignored_existing_modules=ignored_modules,
            duplicated_logic_detected=duplicated_logic,
            api_contract_preserved=api_contract_preserved,
            alignment_score=round(alignment_score, 2)
        )
