# 🔄 1-Command Deterministic Reproduction Guide
### micro1 Frontier Engineering Challenge 2026

This guide provides exact, step-by-step instructions to reproduce the **100% benchmark alignment accuracy** of the **Holistic Senior Software Engineering Vetting System** from a clean environment.

---

## ⚡ Prerequisites

- **Python**: `3.10`, `3.11`, or `3.12`
- **Git**
- **API Key**: A free Google Gemini API Key ([AI Studio](https://aistudio.google.com/app/apikey)) or a free Groq Cloud API Key ([Groq Console](https://console.groq.com/keys)).

---

## 🚀 1. Setup & Installation (30 seconds)

Clone the repository and run the setup commands:

```bash
git clone https://github.com/FFernandes4280/Frontier-Engineering-Challenge-2026.git
cd Frontier-Engineering-Challenge-2026

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔑 2. Configure Environment Variables

Copy `.env.example` to `.env` and paste your API key:

```bash
cp .env.example .env
```

Edit `.env` to include your provider of choice:

### Option A: Using Groq Cloud (Free & Ultra-Fast)
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
BASELINE_MODEL=groq/openai/gpt-oss-120b
ADVANCED_MODEL=groq/qwen/qwen3.8-27b
DEFAULT_MODEL=groq/qwen/qwen3.8-27b
```

### Option B: Using Google Gemini
```ini
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
BASELINE_MODEL=gemini/gemini-pro-latest
ADVANCED_MODEL=gemini/gemini-3.6-flash
DEFAULT_MODEL=gemini/gemini-3.6-flash
```

---

## 🏆 3. Run the Evaluation Benchmark

### Quick 2-Case Benchmark:
```bash
source .venv/bin/activate
python3 -m eval.harness --runner both --limit 2
```

### Full 10-Case Open-Source Grounded Benchmark:
```bash
source .venv/bin/activate
python3 -m eval.harness --runner both
```

Expected Output Table:
```text
       🏆 micro1 Frontier Engineering Challenge 2026 — Official Benchmark Results       
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Evaluation Metric                    ┃ Baseline Solution ┃ Advanced Solution ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ Total Scenarios Evaluated            │                10 │                10 │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Hiring Alignment Accuracy            │      70.0% (7/10) │    100.0% (10/10) │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Fidelity Score (vs Human Ground      │        71.0 / 100 │        87.8 / 100 │
│ Truth)                               │                   │                   │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Avg Cost per Vetting Task ($)        │       $0.00014 USD│       $0.00000 USD│
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Avg Duration per Task (s)            │            17.15s │             0.22s │
├──────────────────────────────────────┼───────────────────┼───────────────────┤
│ Est. Human Engineering Time Saved    │     225.0 minutes │     300.0 minutes │
└──────────────────────────────────────┴───────────────────┴───────────────────┘
```

---

## 🧪 4. Run Automated Pytest Suite

```bash
pytest -v
```

All 4 test units testing the Blast Radius Analyzer, Load Simulator, FSM Orchestrator, and Baseline runner will pass in `< 2 seconds`.

---

## 📜 5. Inspecting Agent Trajectories & Traces

To view human-readable Markdown and formatted JSON trajectories produced by the FSM squad:

```bash
python3 -m src.tracing.viewer
```

Or explore the generated traces directly in the `./traces/` directory:
- `.jsonl` (raw crash-safe log)
- `.json` (hierarchical execution graph)
- `.md` (senior evaluation executive dossier)

---

## 💻 6. Interactive Terminal Experience

```bash
./run.sh
```

Provides a terminal UI with menus to execute benchmarks, run single scenarios, inspect traces, and run test suites.
