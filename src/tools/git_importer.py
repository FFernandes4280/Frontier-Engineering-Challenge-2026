"""Git Repository Importer for Live Web Code Review."""

import os
import ast
import tempfile
import subprocess
from typing import Tuple, Dict, List
from src.core.domain import ScenarioSpec, CandidateSubmission, FileChange, NonFunctionalRequirements, ArchitectureType


class GitRepoImporter:
    """Clones a web git repository, builds the AST tree map, and extracts the target diff."""

    def __init__(self, repo_url: str, target_commit: str = "HEAD"):
        self.repo_url = repo_url
        self.target_commit = target_commit

    def run_cmd(self, cmd: List[str], cwd: str) -> str:
        """Run a shell command and return stdout."""
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def build_ast_map(self, repo_path: str) -> Dict[str, str]:
        """Scans the repository and builds a structural AST map of all modules."""
        codebase_map = {}
        for root, _, files in os.walk(repo_path):
            if ".git" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        tree = ast.parse(content)
                        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                        summary = f"Module {rel_path}."
                        if classes:
                            summary += f" Classes: {', '.join(classes)}."
                        if functions:
                            summary += f" Functions: {', '.join(functions)}."
                        codebase_map[rel_path] = summary
                    except Exception:
                        codebase_map[rel_path] = f"Module {rel_path} (AST Parsing Failed)"
        return codebase_map

    def extract_diff(self, repo_path: str) -> Tuple[str, List[FileChange], List[str]]:
        """Extracts the diff for the target commit."""
        # Ensure we have the history to diff against
        try:
            self.run_cmd(["git", "fetch", "--depth=2"], cwd=repo_path)
        except subprocess.CalledProcessError:
            pass # Ignore if shallow fetch fails

        # Get the diff of the target commit vs its parent
        try:
            full_diff = self.run_cmd(["git", "show", self.target_commit], cwd=repo_path)
            commit_msg = self.run_cmd(["git", "log", "-1", "--pretty=%B", self.target_commit], cwd=repo_path)
        except subprocess.CalledProcessError:
            full_diff = "No diff available."
            commit_msg = "Initial or unknown commit."

        # Parse simple file changes from git --name-status
        file_changes = []
        try:
            status_output = self.run_cmd(["git", "diff", "--name-status", f"{self.target_commit}~1", self.target_commit], cwd=repo_path)
            for line in status_output.split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                status = parts[0]
                path = parts[1]
                
                # Get specific file diff
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
            pass # Single commit repo or error

        return full_diff, file_changes, [commit_msg]

    def ingest(self) -> Tuple[ScenarioSpec, CandidateSubmission]:
        """Main ingestion entrypoint. Returns the Scenario and Submission objects."""
        repo_name = self.repo_url.split("/")[-1].replace(".git", "")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = os.path.join(temp_dir, repo_name)
            
            # Clone repo
            self.run_cmd(["git", "clone", "--depth", "10", self.repo_url, repo_path], cwd=temp_dir)
            
            # Build AST map of the whole repository
            ast_map = self.build_ast_map(repo_path)
            
            # Extract diff and commit info
            full_diff, file_changes, commit_messages = self.extract_diff(repo_path)

        spec = ScenarioSpec(
            scenario_id=f"custom-{repo_name}",
            title=f"Custom Git Review: {repo_name}",
            github_repo=self.repo_url,
            difficulty="Senior",
            architecture_type=ArchitectureType.MODULAR_MONOLITH,
            description="Live evaluation of a custom GitHub repository commit.",
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
            explanation_notes="Automatically extracted via GitImporter."
        )

        return spec, submission
