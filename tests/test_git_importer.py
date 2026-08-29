"""Unit tests for GitRepoImporter."""

import os
from unittest.mock import patch, MagicMock
from src.tools.git_importer import GitRepoImporter


@patch("src.tools.git_importer.subprocess.run")
def test_git_importer_ingest(mock_run):
    """Test that git importer calls git commands and builds domain models."""
    # Setup mock subprocess returns
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
    
    importer = GitRepoImporter(repo_url="https://github.com/mock/repo.git")
    
    # We also need to mock build_ast_map so we don't depend on actual filesystem traversal of a temp dir
    with patch.object(importer, "build_ast_map", return_value={"main.py": "Module main.py. Classes: App."}):
        spec, submission = importer.ingest()
        
    # Assert Domain Models generated correctly
    assert spec.scenario_id == "custom-repo"
    assert spec.github_repo == "https://github.com/mock/repo.git"
    assert spec.existing_codebase_map["main.py"] == "Module main.py. Classes: App."
    
    assert submission.commit_messages[0] == "Fix major concurrency bug"
    assert len(submission.file_changes) == 2
    assert submission.file_changes[0].path == "main.py"
    assert submission.file_changes[0].is_new_file is False
    assert submission.file_changes[1].path == "utils.py"
    assert submission.file_changes[1].is_new_file is True
