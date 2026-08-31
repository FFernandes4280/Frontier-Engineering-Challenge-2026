from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_script_supports_groq_and_gemini_keys():
    run_script = (ROOT / "run.sh").read_text()
    env_example = (ROOT / ".env.example").read_text()

    assert "GROQ_API_KEY" in run_script
    assert "GEMINI_API_KEY" in run_script
    assert "Configure / Update" in run_script
    assert "GROQ_API_KEY" in env_example
    assert "GEMINI_API_KEY" in env_example
