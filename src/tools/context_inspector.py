"""Tool: Context & Architectural Reusability Inspector (Broadened Pattern Detection)."""

import re

from src.core.domain import CandidateSubmission, ContextAlignmentMetrics, ScenarioSpec

MODULE_KEYWORD_MAP = {
    "validator": {"validate", "validation", "re.compile", "pattern", "regex", "check", "verify", "sanitize"},
    "cache": {"lru_cache", "cache", "memoize", "ttl", "expire", "invalidate", "redis"},
    "db": {"cursor", "execute", "query", "session", "orm", "select", "insert", "transaction", "commit"},
    "auth": {"authenticate", "token", "jwt", "bearer", "credentials", "login", "password"},
    "serializer": {"serialize", "deserialize", "schema", "dump", "load", "marshal", "json"},
    "util": {"helper", "utility", "format", "parse", "convert", "transform"},
    "middleware": {"middleware", "interceptor", "handler", "hook", "before_request", "after_request"},
    "rate_limit": {"rate_limit", "throttle", "bucket", "limiter", "quota"},
}


class ContextInspector:
    """Evaluates whether the candidate respected existing codebase abstractions.
    
    Uses semantic keyword overlap analysis to detect when diff introduces
    logic that could be served by existing modules in the codebase AST map.
    """

    @staticmethod
    def _extract_diff_keywords(diff_text: str) -> set[str]:
        """Extract meaningful keywords from diff (added lines only)."""
        keywords = set()
        for line in diff_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                clean = line[1:].strip().lower()
                tokens = re.findall(r'[a-z_][a-z0-9_]*', clean)
                keywords.update(tokens)
        return keywords

    @staticmethod
    def _compute_module_overlap(module_path: str, module_desc: str, diff_keywords: set[str]) -> float:
        """Compute semantic overlap score between an existing module and the diff keywords."""
        path_lower = module_path.lower()
        desc_lower = module_desc.lower()
        
        overlap_score = 0.0
        
        for category, category_keywords in MODULE_KEYWORD_MAP.items():
            module_matches_category = any(k in path_lower or k in desc_lower for k in [category])
            if not module_matches_category:
                module_matches_category = any(k in desc_lower for k in category_keywords)
            
            if module_matches_category:
                diff_hits = diff_keywords.intersection(category_keywords)
                if diff_hits:
                    overlap_score = max(overlap_score, len(diff_hits) / max(3, len(category_keywords)))
        
        return min(1.0, overlap_score)

    @staticmethod
    def inspect(submission: CandidateSubmission, spec: ScenarioSpec) -> ContextAlignmentMetrics:
        ignored_modules = []
        duplicated_logic = False
        api_contract_preserved = True
        alignment_score = 1.0

        full_diff = submission.full_diff or "\n".join(fc.diff_content for fc in submission.file_changes)
        diff_keywords = ContextInspector._extract_diff_keywords(full_diff)

        # Strategy 1: Semantic keyword overlap with existing modules
        for existing_path, description in spec.existing_codebase_map.items():
            module_name = existing_path.split("/")[-1].replace(".py", "")
            
            if module_name not in full_diff:
                overlap = ContextInspector._compute_module_overlap(existing_path, description, diff_keywords)
                if overlap >= 0.3:
                    ignored_modules.append(existing_path)
                    duplicated_logic = True
                    alignment_score -= min(0.35, overlap * 0.5)

        # Strategy 2: Direct pattern matching
        for existing_path, description in spec.existing_codebase_map.items():
            module_name = existing_path.split("/")[-1].replace(".py", "")
            if module_name in full_diff:
                continue

            if "validator" in existing_path and "re.compile" in full_diff:
                if existing_path not in ignored_modules:
                    ignored_modules.append(existing_path)
                    duplicated_logic = True
                    alignment_score -= 0.3

            if "cache" in existing_path and "@lru_cache" in full_diff:
                if existing_path not in ignored_modules:
                    ignored_modules.append(existing_path)
                    duplicated_logic = True
                    alignment_score -= 0.35

            if "db" in existing_path and "cursor.execute" in full_diff:
                if "Session" in description or "ORM" in description:
                    if existing_path not in ignored_modules:
                        ignored_modules.append(existing_path)
                        alignment_score -= 0.2

        # Strategy 3: API contract preservation checks
        if "del response[" in full_diff or ("status_code=400" in full_diff and "status_code=422" in full_diff):
            api_contract_preserved = False
            alignment_score = min(0.40, alignment_score - 0.40)

        # Strategy 4: Check for removed/renamed public function signatures
        removed_defs = re.findall(r'^-\s*def\s+([a-z_][a-z0-9_]*)', full_diff, re.MULTILINE)
        if removed_defs:
            api_contract_preserved = False
            alignment_score = min(0.40, alignment_score - 0.25)

        alignment_score = max(0.1, min(1.0, alignment_score))

        return ContextAlignmentMetrics(
            reused_existing_utilities=len(ignored_modules) == 0,
            ignored_existing_modules=ignored_modules,
            duplicated_logic_detected=duplicated_logic,
            api_contract_preserved=api_contract_preserved,
            alignment_score=round(alignment_score, 2)
        )
