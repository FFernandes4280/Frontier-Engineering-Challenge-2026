"""Unit tests for GitRepoImporter (Take-Home Full Repo & Incremental Diff)."""

import os
from unittest.mock import patch, MagicMock
from src.tools.git_importer import GitRepoImporter


@patch("src.tools.git_importer.subprocess.run")
def test_git_importer_ingest_diff_mode(mock_run):
    """Test that git importer calls git commands and builds domain models in diff mode."""
    def mock_run_side_effect(cmd, **kwargs):
        mock = MagicMock()
        mock.stdout = ""

        if cmd[0] == "git" and cmd[1] == "log":
            mock.stdout = "Fix major concurrency bug"
        elif cmd[0] == "git" and cmd[1] == "show":
            mock.stdout = "@@ -1,3 +1,4 @@\n+print('hello')"
        elif cmd[0] == "git" and cmd[1] == "diff" and "--name-status" in cmd:
            mock.stdout = "M\tmain.py\nA\tutils.py"
        elif cmd[0] == "git" and cmd[1] == "diff" and "--" in cmd:
            mock.stdout = "+new code"

        return mock

    mock_run.side_effect = mock_run_side_effect

    importer = GitRepoImporter(repo_url="https://github.com/mock/repo.git", mode="diff")

    with patch.object(importer, "build_ast_map", return_value={"main.py": "Module main.py. Classes: App."}):
        spec, submission = importer.ingest()

    assert spec.scenario_id == "custom-repo"
    assert spec.github_repo == "https://github.com/mock/repo.git"
    assert spec.existing_codebase_map["main.py"] == "Module main.py. Classes: App."
    assert submission.commit_messages[0] == "Fix major concurrency bug"
    assert len(submission.file_changes) == 2


@patch("src.tools.git_importer.subprocess.run")
def test_git_importer_ingest_take_home_mode(mock_run):
    """Test that git importer extracts full repository codebase in take_home mode."""
    mock = MagicMock()
    mock.stdout = "cloned"
    mock_run.return_value = mock

    importer = GitRepoImporter(repo_url="https://github.com/mock/repo.git", mode="full_repo")

    with patch.object(importer, "build_ast_map", return_value={"main.py": "Python Module", "api.py": "API Module"}):
        with patch.object(importer, "extract_full_codebase", return_value=("full_diff_code", [], ["Take-Home Project: Full Repository Codebase Ingestion"])):
            spec, submission = importer.ingest()

    assert spec.scenario_id == "takehome-repo"
    assert "Take-Home Project Assessment" in spec.title
    assert len(spec.existing_codebase_map) == 2
    assert submission.full_diff == "full_diff_code"
