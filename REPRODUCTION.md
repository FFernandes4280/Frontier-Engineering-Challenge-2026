# 🔄 1-Command Deterministic Reproduction Guide
### micro1 Frontier Engineering Challenge 2026

This guide provides exact, step-by-step instructions to reproduce the **benchmark alignment accuracy, parity test suite, and interactive Django Web Dashboard** of the **Holistic Senior Software Engineering Vetting & CI/CD Gatekeeper System** from a clean environment.

---

## ⚡ Prerequisites

- **Python**: `3.10`, `3.11`, or `3.12`
- **Git**
- **LLM API Key (Optional for Live LLM Mode)**: A free Groq Cloud API Key ([Groq Console](https://console.groq.com/keys)) or Google Gemini API Key ([AI Studio](https://aistudio.google.com/app/apikey)).
  - *Note*: The system includes self-contained deterministic AST analysis and load simulation engines, running complete offline/local evaluations and test suites with zero external dependency requirements.

---

## 🚀 1. Setup & Installation (30 seconds)

Clone the repository and prepare the virtual environment:

```bash
git clone https://github.com/FFernandes4280/Frontier-Engineering-Challenge-2026.git
cd Frontier-Engineering-Challenge-2026

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (Pydantic, LiteLLM, Rich, Typer, Django, Pytest)
pip install -r requirements.txt
```

---

## 🔑 2. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Configure your preferred LLM provider:

### Option A: Using Groq Cloud (Free & Ultra-Fast Inference)
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
BASELINE_MODEL=groq/openai/gpt-oss-120b
ADVANCED_MODEL=groq/openai/gpt-oss-20b
DEFAULT_MODEL=groq/openai/gpt-oss-20b
```

### Option B: Using Google Gemini
```ini
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
BASELINE_MODEL=gemini/gemini-pro-latest
ADVANCED_MODEL=gemini/gemini-3.6-flash
DEFAULT_MODEL=gemini/gemini-3.6-flash
```

---

## 🌐 3. Launch the Django Web Dashboard & REST API

The system features a full-fledged Django Web Dashboard providing interactive scenario exploration, real-time live evaluation, take-home project ingestion, and audit trajectory inspection.

```bash
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

Navigate to `http://127.0.0.1:8000` in your web browser to access:
- **Overview Dashboard (`/`)**: High-level KPIs, comparative accuracy metrics, and benchmark catalog.
- **Benchmark Catalog (`/cases/`)**: 15 open-source grounded scenarios with detailed architectural specifications.
- **Scenario Inspector & Live Runner (`/cases/<case_id>/`)**: Deep dive into diffs and trigger live evaluations against the FSM squad.
- **Take-Home Project Evaluator (`/custom-review/`)**: Ingests public or private GitHub repository URLs in isolated sandboxes and parses AST across polyglot modules.
- **Trajectory & Trace Viewer (`/traces/`)**: Visualizer for streaming `.jsonl` audit steps, structured `.json` graphs, and executive `.md` dossiers.

### REST API Endpoints:
- `GET /api/benchmark-data/`: Returns all 15 scenarios and consolidated baseline/advanced benchmark statistics.
- `POST /api/evaluate/<case_id>`: Dispatches dynamic evaluation with custom seniority / diff overrides.
- `POST /api/evaluate-takehome/`: Clones repository in ephemeral sandbox and executes AST analysis + vetting squad.
- `GET /api/trajectories/`: Lists all saved audit trajectories and trace files.

---

## 🧪 4. Execute the Automated Test & Parity Suite

Run the complete test suite verifying FSM execution, tool sandboxing, AST alignment, load simulation, and Django REST API parity:

```bash
source .venv/bin/activate
pytest -v
```

### What is validated:
1. **Django Parity & REST API Compliance (`tests/test_django_parity.py`)**:
   - `GET /` responds HTTP 200 with layout components.
   - `GET /api/benchmark-data/` returns 15 valid scenarios.
   - `POST /api/evaluate/case_01` dynamically computes multi-agent scores and telemetry.
   - **Dynamic Assertion**: Confirms that different code submissions generate different scores and that seniority levels alter critic feedback (guaranteeing no static or mocked data).
   - `POST /api/evaluate-takehome/` validates repository URLs and handles non-existent/malformed repos gracefully.
   - `GET /api/trajectories/` lists trajectory records.
2. **Git Importer & Polyglot AST (`tests/test_git_importer.py`)**: Validates incremental diff and full take-home project repository ingestion in isolated temporary sandboxes.
3. **Test Synthesizer (`tests/test_test_synthesizer.py`)**: Validates detection of state drift, memory leaks, and lock acquisition order inversions.
4. **Vetting Pipeline & FSM Squad (`tests/test_vetting_pipeline.py`)**: Validates Blast Radius Analyzer, Load Simulator, FSM Orchestrator, and Baseline runner.

---

## 🏆 5. Run the Comparative Benchmark (15 Scenarios)

Execute the 15 open-source SWE-bench grounded scenarios comparing the **Baseline (Single-Prompt Monolith)** vs **Advanced (FSM Multi-Agent Squad)**:

```bash
source .venv/bin/activate

# Run quick 2-case benchmark:
python3 -m eval.harness --runner both --limit 2

# Run full 15-case benchmark:
python3 -m eval.harness --runner both
```

Expected Output Summary:
```text
       🏆 micro1 Frontier Engineering Challenge 2026 — Official Benchmark Results       
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Evaluation Metric                    ┃ Baseline Solution ┃ Advanced Solution ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ Total Scenarios Evaluated            │                15 │                15 │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Hiring Alignment Accuracy            │      66.7% (10/15)│     93.3% (14/15) │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Fidelity Score (vs Human Truth)      │        70.4 / 100 │        88.2 / 100 │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Avg Cost per Vetting Task ($)        │      $0.00014 USD │      $0.00002 USD │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Avg Duration per Task (s)            │            14.20s │             0.45s │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Est. Human Engineering Time Saved    │     337.5 minutes │     420.0 minutes │
└──────────────────────────────────────┴───────────────────┴───────────────────┘
```

---

## 💻 6. Interactive Terminal CLI (`run.sh`)

Launch the unified interactive menu to run benchmarks, inspect traces, or launch servers:

```bash
./run.sh
```

Menu options:
- `1)` Run Baseline on Single Scenario (Step-by-step trace)
- `2)` Run Advanced FSM on Single Scenario
- `3)` Run Full Comparative Benchmark (15 cases)
- `4)` Review Custom Git Repository Take-Home Project
- `5)` Inspect Trajectories & Traces in Terminal
- `6)` Run Automated Pytest Suite
- `7)` Launch Django Web Dashboard (`http://127.0.0.1:8000`)
- `8)` Clean cache and temporary traces
- `0)` Exit

---

## 📜 7. Trajectory Persistence & Ground Truth Rastreability

All agent execution traces are deterministically persisted across three formats in `./trajectories/` and `./traces/`:
1. **`.jsonl`**: Append-only crash-safe event streaming log recording every FSM state transition, prompt, tool call, and tool response.
2. **`.json`**: Structured graph containing duration, token consumption, cost in USD, and final vetting dossier.
3. **`.md`**: Markdown executive report citing exact file locations, finding severity, and senior critic trade-off analysis.

---
*Official Verification Guide for micro1 Frontier Engineering Challenge 2026.*
