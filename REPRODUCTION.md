# 🔄 Frontier Engineering Challenge 2026 — Reproduction Guide

> This guide provides deterministic, step-by-step instructions to reproduce the Baseline, Advanced FSM Multi-Agent Solution, and Benchmark Results from a **completely clean environment** (Docker or Linux/macOS).

---

## 📋 Prerequisites & System Requirements

- **Python:** `3.10` or higher
- **OS:** Linux (Ubuntu 20.04+), macOS, or WSL2
- **LLM API Key:** At least one provider key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`)

---

## ⚡ Quick Start (1-Command Interactive CLI)

Clone the repository and launch the interactive runner:

```bash
git clone https://github.com/FFernandes4280/Frontier-Engineering-Challenge-2026.git
cd Frontier-Engineering-Challenge-2026
./run.sh
```

---

## 🛠️ Step-by-Step Manual Execution

### 1. Environment Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API Keys
cp .env.example .env
# Edit .env with your favorite editor and paste your API key
```

### 2. Run the Baseline Solution (Single-Prompt / Naive)

```bash
python3 -m eval.harness --runner baseline
```

### 3. Run the Advanced Solution (FSM Multi-Agent + Verifier)

```bash
python3 -m eval.harness --runner advanced
```

### 4. Run the Full Comparative Benchmark (10+ Cases)

```bash
python3 -m eval.harness --runner both
```

### 5. Inspect Agent Trajectories & Traces

```bash
# View in Rich terminal
python3 -m src.tracing.viewer

# Or inspect the generated JSONL / Markdown logs in ./traces/
cat traces/*.md
```
