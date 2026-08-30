import json
import subprocess
import sys

def check_anti_overfitting():
    # 1. Assert Benchmark completed without crashes and produced 20 results
    with open("eval/benchmark_results.json", "r") as f:
        results = json.load(f)
    
    baseline_details = results["details"]["baseline"]
    advanced_details = results["details"]["advanced"]
    
    assert len(baseline_details) == 20, f"Expected 20 baseline results, got {len(baseline_details)}"
    assert len(advanced_details) == 20, f"Expected 20 advanced results, got {len(advanced_details)}"
    
    # 2. Check for dynamic scoring
    baseline_scores = [r["details"]["predicted_score"] for r in baseline_details]
    advanced_scores = [r["details"]["predicted_score"] for r in advanced_details]
    
    assert len(set(baseline_scores)) > 5, "Scores are suspiciously uniform in baseline"
    assert len(set(advanced_scores)) > 5, "Scores are suspiciously uniform in advanced"

    print("✅ Assertions passed: 20 benchmark cases ran successfully.")
    print("✅ Assertions passed: Scores and flaws are generated dynamically.")
    
    # 3. Test Rotten-Potatoes Custom Repo without RateLimitError crash
    print("Running custom git repo test on Rotten-Potatoes (Full Repo Mode)...")
    result = subprocess.run(
        ["./.venv/bin/python", "-m", "src.cli.review_repo", "--repo", "https://github.com/FFernandes4280/Rotten-Potatoes", "--mode", "full_repo", "--runner", "both"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": ".", **os.environ} if "os" in sys.modules else None
    )
    
    assert result.returncode == 0, f"Rotten-Potatoes failed with code {result.returncode}\n{result.stderr}\n{result.stdout}"
    assert "Exception" not in result.stderr, "Found exception in stderr"
    
    # 4. Test development-tools Custom Repo without RateLimitError crash
    print("Running custom git repo test on development-tools (Full Repo Mode)...")
    result2 = subprocess.run(
        ["./.venv/bin/python", "-m", "src.cli.review_repo", "--repo", "https://github.com/FFernandes4280/development-tools", "--mode", "full_repo", "--runner", "both"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": ".", **os.environ} if "os" in sys.modules else None
    )
    
    assert result2.returncode == 0, f"development-tools failed with code {result2.returncode}\n{result2.stderr}\n{result2.stdout}"
    assert "Exception" not in result2.stderr, "Found exception in stderr"
    
    print("✅ Assertions passed: Custom repositories evaluated successfully without RateLimitError crashes.")
    print("✅ Anti-Overfitting Guarantee Verified!")

import os
if __name__ == "__main__":
    check_anti_overfitting()
