"""Git Repository Importer for Live Web Code Review (Polyglot: Python, JS/TS, React, Go, etc.)."""

import os
import re
import ast
import tempfile
import subprocess
from typing import Tuple, Dict, List
from src.core.domain import ScenarioSpec, CandidateSubmission, FileChange, NonFunctionalRequirements, ArchitectureType


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
    """Clones a web git repository, builds a polyglot AST/Symbol tree map, and extracts the target diff."""

    def __init__(self, repo_url: str, target_commit: str = "HEAD"):
        self.repo_url = repo_url
        self.target_commit = target_commit

    def run_cmd(self, cmd: List[str], cwd: str) -> str:
        """Run a shell command and return stdout."""
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def parse_python_ast(self, file_path: str, rel_path: str) -> str:
        """Parses Python AST for classes and functions."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        tree = ast.parse(content)
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        summary = f"Python Module {rel_path}."
        if classes:
            summary += f" Classes: {', '.join(classes)}."
        if functions:
            summary += f" Functions: {', '.join(functions)}."
        return summary

    def parse_js_ts_symbols(self, file_path: str, rel_path: str, lang: str) -> str:
        """Extracts components, functions, classes and exports from JavaScript/TypeScript/JSX files."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Find classes
        classes = re.findall(r"class\s+([A-Za-z0-9_]+)", content)
        # Find functions and arrow functions / components
        functions = re.findall(r"(?:export\s+)?(?:default\s+)?function\s+([A-Za-z0-9_]+)", content)
        const_funcs = re.findall(r"(?:export\s+)?const\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>", content)
        all_funcs = list(dict.fromkeys(functions + const_funcs))

        # Find exports
        exports = re.findall(r"export\s+(?:default\s+)?(?:const|let|var|class|function)?\s*([A-Za-z0-9_]+)", content)
        exports = [e for e in exports if e]

        summary = f"{lang} Module `{rel_path}`."
        if classes:
            summary += f" Classes: {', '.join(classes)}."
        if all_funcs:
            summary += f" Components/Functions: {', '.join(all_funcs[:8])}."
        if exports:
            summary += f" Exports: {', '.join(exports[:5])}."
        return summary

    def build_ast_map(self, repo_path: str) -> Dict[str, str]:
        """Scans the repository and builds a structural AST/Symbol map across languages."""
        codebase_map = {}
        for root, _, files in os.walk(repo_path):
            if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "dist", "build", ".venv"]):
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

    def extract_diff(self, repo_path: str) -> Tuple[str, List[FileChange], List[str]]:
        """Extracts the diff for the target commit."""
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

    def ingest(self) -> Tuple[ScenarioSpec, CandidateSubmission]:
        """Main ingestion entrypoint. Returns the Scenario and Submission objects."""
        repo_name = self.repo_url.split("/")[-1].replace(".git", "")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = os.path.join(temp_dir, repo_name)
            self.run_cmd(["git", "clone", "--depth", "10", self.repo_url, repo_path], cwd=temp_dir)
            ast_map = self.build_ast_map(repo_path)
            full_diff, file_changes, commit_messages = self.extract_diff(repo_path)

        spec = ScenarioSpec(
            scenario_id=f"custom-{repo_name}",
            title=f"Custom Git Review: {repo_name}",
            github_repo=self.repo_url,
            difficulty="Senior",
            architecture_type=ArchitectureType.MODULAR_MONOLITH,
            description=f"Live architectural review of GitHub repository {repo_name}.",
            requirements=NonFunctionalRequirements(),
            existing_codebase_map=ast_map,
            ground_truth_flaw="Unknown (Live Evaluation)",
            expected_optimal_solution="Unknown (Live Evaluation)"
        )

        submission = CandidateSubmission(
            candidate_id="custom-candidate",
            scenario_id=spec.scenario_id,
            commit_messages=commit_messages,
            file_changes=file_changes,
            full_diff=full_diff,
            explanation_notes="Automatically extracted via Polyglot GitImporter."
        )

        return spec, submission
