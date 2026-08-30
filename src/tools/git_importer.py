"""Git Repository Importer for Live Web Code Review (Take-Home Full Repo & Polyglot AST)."""

import ast
import os
import re
import subprocess
import tempfile

from src.core.domain import (
    ArchitectureType,
    CandidateSubmission,
    FileChange,
    NonFunctionalRequirements,
    ScenarioSpec,
)

CODE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "React JSX",
    ".ts": "TypeScript",
    ".tsx": "React TSX",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".json": "JSON Config",
    ".html": "HTML",
    ".css": "CSS",
    ".sh": "Shell"
}


class GitRepoImporter:
    """Clones a web git repository, builds a polyglot AST/Symbol tree map, and extracts either the full codebase (Take-Home mode) or a specific commit diff."""

    def __init__(self, repo_url: str, target_commit: str = "HEAD", mode: str = "full_repo"):
        self.repo_url = repo_url.strip()
        self.target_commit = target_commit
        self.mode = mode  # "full_repo" (Take-Home assignment) or "diff" (Incremental PR)

    def run_cmd(self, cmd: list[str], cwd: str) -> str:
        """Run a shell command and return stdout."""
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def parse_python_ast(self, file_path: str, rel_path: str) -> str:
        """Parses Python AST for classes, methods, and functions."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        try:
            tree = ast.parse(content)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            summary = f"Python Module `{rel_path}`."
            if classes:
                summary += f" Classes: {', '.join(classes[:5])}."
            if functions:
                summary += f" Functions: {', '.join(functions[:8])}."
            return summary
        except Exception:
            return f"Python Module `{rel_path}` (Raw Source)."

    def parse_js_ts_symbols(self, file_path: str, rel_path: str, lang: str) -> str:
        """Extracts components, functions, classes and exports from JavaScript/TypeScript/JSX files."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        classes = re.findall(r"class\s+([A-Za-z0-9_]+)", content)
        functions = re.findall(r"(?:export\s+)?(?:default\s+)?function\s+([A-Za-z0-9_]+)", content)
        const_funcs = re.findall(r"(?:export\s+)?const\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>", content)
        all_funcs = list(dict.fromkeys(functions + const_funcs))
        exports = re.findall(r"export\s+(?:default\s+)?(?:const|let|var|class|function)?\s*([A-Za-z0-9_]+)", content)
        exports = [e for e in exports if e]

        summary = f"{lang} Module `{rel_path}`."
        if classes:
            summary += f" Classes: {', '.join(classes[:4])}."
        if all_funcs:
            summary += f" Components/Functions: {', '.join(all_funcs[:6])}."
        if exports:
            summary += f" Exports: {', '.join(exports[:4])}."
        return summary

    def build_ast_map(self, repo_path: str) -> dict[str, str]:
        """Scans the repository and builds a structural AST/Symbol map across languages."""
        codebase_map = {}
        for root, _, files in os.walk(repo_path):
            if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "dist", "build", ".venv", ".pytest_cache"]):
                continue
            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext in CODE_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    try:
                        if ext == ".py":
                            codebase_map[rel_path] = self.parse_python_ast(file_path, rel_path)
                        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
                            codebase_map[rel_path] = self.parse_js_ts_symbols(file_path, rel_path, CODE_EXTENSIONS[ext])
                        else:
                            codebase_map[rel_path] = f"{CODE_EXTENSIONS[ext]} Source File `{rel_path}`."
                    except Exception:
                        codebase_map[rel_path] = f"Source File `{rel_path}` (Raw Inspection)."
        return codebase_map

    def extract_full_codebase(self, repo_path: str) -> tuple[str, list[FileChange], list[str]]:
        """Extracts the entire codebase across all files for Take-Home project assessment."""
        file_changes = []
        diff_blocks = []

        for root, _, files in os.walk(repo_path):
            if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "dist", "build", ".venv", ".pytest_cache"]):
                continue
            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext in CODE_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        lines = content.splitlines()
                        diff_content = "\n".join(f"+{line}" for line in lines[:300])  # Cap per file to maintain responsiveness
                        full_file_block = f"--- /dev/null\n+++ b/{rel_path}\n@@ -0,0 +1,{min(300, len(lines))} @@\n{diff_content}"
                        diff_blocks.append(full_file_block)

                        file_changes.append(FileChange(
                            path=rel_path,
                            diff_content=diff_content,
                            is_new_file=True,
                            added_lines=len(lines),
                            deleted_lines=0
                        ))
                    except Exception:
                        continue

        full_diff = "\n\n".join(diff_blocks)
        commit_messages = [f"Take-Home Project Assessment: Full Repository Ingestion ({len(file_changes)} files)"]
        return full_diff, file_changes, commit_messages

    def extract_diff(self, repo_path: str) -> tuple[str, list[FileChange], list[str]]:
        """Extracts the diff for the target commit (Incremental mode)."""
        try:
            self.run_cmd(["git", "fetch", "--depth=5"], cwd=repo_path)
        except subprocess.CalledProcessError:
            pass

        try:
            full_diff = self.run_cmd(["git", "show", self.target_commit], cwd=repo_path)
            commit_msg = self.run_cmd(["git", "log", "-1", "--pretty=%B", self.target_commit], cwd=repo_path)
        except subprocess.CalledProcessError:
            full_diff = "No diff available."
            commit_msg = "Initial or unknown commit."

        file_changes = []
        try:
            status_output = self.run_cmd(["git", "diff", "--name-status", f"{self.target_commit}~1", self.target_commit], cwd=repo_path)
            for line in status_output.split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    status, path = parts[0], parts[1]
                    try:
                        file_diff = self.run_cmd(["git", "diff", f"{self.target_commit}~1", self.target_commit, "--", path], cwd=repo_path)
                    except subprocess.CalledProcessError:
                        file_diff = ""

                    file_changes.append(FileChange(
                        path=path,
                        diff_content=file_diff,
                        is_new_file=(status == "A")
                    ))
        except subprocess.CalledProcessError:
            pass

        return full_diff, file_changes, [commit_msg]

    def ingest(self) -> tuple[ScenarioSpec, CandidateSubmission]:
        """Main ingestion entrypoint. Supports full take-home project or incremental diff."""
        repo_name = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = os.path.join(temp_dir, repo_name)
            self.run_cmd(["git", "clone", "--depth", "5", self.repo_url, repo_path], cwd=temp_dir)
            ast_map = self.build_ast_map(repo_path)

            if self.mode == "full_repo":
                full_diff, file_changes, commit_messages = self.extract_full_codebase(repo_path)
                spec_title = f"Take-Home Project Assessment: {repo_name}"
                spec_desc = f"Comprehensive Take-Home Project Architecture & Code Review for repository `{repo_name}` across {len(ast_map)} modules."
            else:
                full_diff, file_changes, commit_messages = self.extract_diff(repo_path)
                spec_title = f"Custom Git Review: {repo_name}"
                spec_desc = f"Live architectural review of GitHub repository {repo_name}."

        spec = ScenarioSpec(
            scenario_id=f"takehome-{repo_name}" if self.mode == "full_repo" else f"custom-{repo_name}",
            title=spec_title,
            github_repo=self.repo_url,
            difficulty="Senior",
            architecture_type=ArchitectureType.MODULAR_MONOLITH,
            description=spec_desc,
            requirements=NonFunctionalRequirements(
                latency_p95_sla_ms=50.0,
                concurrency_target_rps=1000,
                max_memory_mb=256.0
            ),
            existing_codebase_map=ast_map,
            ground_truth_flaw="UNKNOWN (You MUST identify any architectural flaws, security vulnerabilities, or anti-patterns)",
            expected_optimal_solution="Identify and enumerate any critical vulnerabilities or architectural anti-patterns in the candidate diff."
        )

        submission = CandidateSubmission(
            candidate_id=f"cand-{repo_name}",
            scenario_id=spec.scenario_id,
            commit_messages=commit_messages,
            file_changes=file_changes,
            full_diff=full_diff,
            explanation_notes="Full repository codebase ingested and analyzed across all modules for Take-Home assessment."
        )

        return spec, submission
