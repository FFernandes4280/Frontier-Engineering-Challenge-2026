#!/usr/bin/env bash
# ==============================================================================
# Frontier Engineering Challenge 2026 - Interactive CLI & Web Runner
# ==============================================================================
# Autonomous Zero-Setup Multi-Agent Evaluation & Reproduction Platform
# ==============================================================================

set -e

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Visual Styling
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ------------------------------------------------------------------------------
# 1. Environment Bootstrap & Dependency Verification
# ------------------------------------------------------------------------------
detect_python() {
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
    elif command -v python >/dev/null 2>&1; then
        echo "python"
    else
        echo ""
    fi
}

ensure_environment() {
    local sys_python
    sys_python=$(detect_python)

    if [ -z "$sys_python" ]; then
        echo -e "${RED}[ERROR] Python is not installed. Please install Python >= 3.10.${NC}"
        exit 1
    fi

    # Check python version >= 3.10
    local major minor
    major=$($sys_python -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
    minor=$($sys_python -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo "0")

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
        echo -e "${RED}[ERROR] Python 3.10 or higher is required. Found Python $major.$minor.${NC}"
        exit 1
    fi

    # 1. Auto-create virtual environment if not present
    if [ ! -d ".venv" ] || [ ! -f ".venv/bin/activate" ]; then
        echo -e "${CYAN}${BOLD}[+] Virtual environment (.venv) not found. Creating one now with $sys_python...${NC}"
        if ! $sys_python -m venv .venv; then
            echo -e "${RED}[ERROR] Failed to create virtual environment.${NC}"
            echo -e "${YELLOW}If you are on Ubuntu/Debian, install venv support via:${NC}"
            echo -e "  sudo apt update && sudo apt install -y python3-venv python3-pip"
            exit 1
        fi
        echo -e "${GREEN}[✓] Virtual environment created successfully.${NC}"
    fi

    # 2. Activate virtual environment
    # shellcheck disable=SC1091
    source .venv/bin/activate

    # 3. Check and install missing dependencies
    local deps_missing=0
    python -c "import typer, rich, django, pydantic, litellm, pytest, tabulate, dotenv" >/dev/null 2>&1 || deps_missing=1

    if [ "$deps_missing" -eq 1 ]; then
        echo -e "${CYAN}${BOLD}[+] Installing project dependencies from requirements.txt in .venv...${NC}"
        pip install --upgrade pip --quiet 2>/dev/null || true
        if ! pip install -r requirements.txt; then
            echo -e "${RED}[ERROR] Failed to install dependencies from requirements.txt.${NC}"
            exit 1
        fi
        echo -e "${GREEN}[✓] All dependencies installed successfully.${NC}"
    fi

    # 4. Auto-create .env from .env.example if missing
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        echo -e "${YELLOW}[!] .env configuration file not found. Creating from .env.example...${NC}"
        cp .env.example .env
        echo -e "${GREEN}[✓] Created .env file.${NC}"
    fi

    # 5. Ensure required data & trace directories exist
    mkdir -p traces trajectories eval

    # 6. Apply Django migrations silently if needed
    python manage.py migrate --noinput >/dev/null 2>&1 || true

    # 7. Check if GROQ_API_KEY is configured or prompt user
    check_and_prompt_api_key
}

check_and_prompt_api_key() {
    local current_key=""
    if [ -f ".env" ]; then
        current_key=$(grep -E "^GROQ_API_KEY=" .env 2>/dev/null | head -n1 | cut -d '=' -f2- | tr -d ' "\r\n' || true)
    fi

    # Detect if key is missing, empty, or a placeholder (e.g. gsk_your_groq_api_key_here)
    if [ -z "$current_key" ] || \
       [[ "$current_key" == *"your"* ]] || \
       [[ "$current_key" == *"here"* ]] || \
       [[ "$current_key" == "gsk_"* && ${#current_key} -lt 30 ]]; then
        if [ -t 0 ]; then
            echo ""
            echo -e "${YELLOW}${BOLD}┌────────────────────────────────────────────────────────┐${NC}"
            echo -e "${YELLOW}${BOLD}│ 🔑 Configuração Inicial de Chave de API (Groq)         │${NC}"
            echo -e "${YELLOW}${BOLD}└────────────────────────────────────────────────────────┘${NC}"
            echo -e "${DIM}Para habilitar inferência semântica e avaliações ao vivo com LLM:${NC}"
            read -r -p "Insira sua GROQ_API_KEY (ou pressione [Enter] para pular): " user_api_key
            if [ -n "$user_api_key" ]; then
                if grep -q "^GROQ_API_KEY=" .env 2>/dev/null; then
                    sed -i "s|^GROQ_API_KEY=.*|GROQ_API_KEY=$user_api_key|" .env
                else
                    echo "GROQ_API_KEY=$user_api_key" >> .env
                fi
                export GROQ_API_KEY="$user_api_key"
                echo -e "${GREEN}[✓] GROQ_API_KEY salva com sucesso no .env!${NC}\n"
            else
                echo -e "${DIM}[i] Prosseguindo com fallback de contingência.${NC}\n"
            fi
        fi
    fi
}

configure_keys_action() {
    show_header
    echo -e "${BOLD}${CYAN}🔑 CONFIGURAR CHAVES DE API & MODELOS (.env)${NC}\n"
    local current_key=""
    if [ -f ".env" ]; then
        current_key=$(grep -E "^GROQ_API_KEY=" .env 2>/dev/null | head -n1 | cut -d '=' -f2- | tr -d ' "' || true)
    fi

    echo -e "Chave atual no .env: ${YELLOW}${current_key:-(não configurada)}${NC}\n"
    read -r -p "Insira a nova GROQ_API_KEY (ou Enter para manter): " new_key
    if [ -n "$new_key" ]; then
        if grep -q "^GROQ_API_KEY=" .env 2>/dev/null; then
            sed -i "s|^GROQ_API_KEY=.*|GROQ_API_KEY=$new_key|" .env
        else
            echo "GROQ_API_KEY=$new_key" >> .env
        fi
        export GROQ_API_KEY="$new_key"
        echo -e "\n${GREEN}[✓] GROQ_API_KEY atualizada com sucesso no arquivo .env!${NC}"
    else
        echo -e "\n${DIM}[i] Nenhuma alteração feita.${NC}"
    fi
}

# ------------------------------------------------------------------------------
# 2. Visual Headers & Menus
# ------------------------------------------------------------------------------
show_header() {
    clear
    echo -e "${CYAN}${BOLD}==================================================================${NC}"
    echo -e "${MAGENTA}${BOLD}   🚀 micro1 Frontier Engineering Challenge 2026 — Unified Runner   ${NC}"
    echo -e "${CYAN}${BOLD}==================================================================${NC}"
    echo -e "${DIM}  Ground-Truth SWE-bench Benchmark & Multi-Agent Vetting Squad${NC}"
    echo ""
}

show_menu() {
    echo -e "${BOLD}Select an action to execute:${NC}"
    echo -e "  ${GREEN}1)${NC} 🧪 Run Baseline on Single Repository (with full Step-by-Step trace)"
    echo -e "  ${GREEN}2)${NC} 🤖 Run Advanced Solution on Single Repository (FSM Multi-Agent Squad)"
    echo -e "  ${GREEN}3)${NC} 📊 Run Comparative Benchmark (Baseline vs Advanced on 20 Cases)"
    echo -e "  ${GREEN}4)${NC} 🌐 Review Custom Git Repository (Take-Home / GitHub URL / PR)"
    echo -e "  ${GREEN}5)${NC} 📜 Inspect Trajectories & Trace Dossiers in Terminal"
    echo -e "  ${GREEN}6)${NC} 🔑 Configure / Update GROQ_API_KEY & LLM Settings (.env)"
    echo -e "  ${GREEN}7)${NC} 🧪 Run Automated Pytest Test Suite"
    echo -e "  ${GREEN}8)${NC} 🌐 Launch Django Web Dashboard (${BLUE}http://127.0.0.1:8000${NC})"
    echo -e "  ${GREEN}9)${NC} 🔄 Reinstall / Sync Virtualenv Dependencies"
    echo -e "  ${GREEN}10)${NC} 🧹 Clean temporary files, caches and test traces"
    echo -e "  ${RED}0)${NC} 🚪 Exit"
    echo ""
}

show_cases_menu() {
    echo -e "${BOLD}Select a benchmark repository to evaluate [1-20]:${NC}"
    echo -e "  ${CYAN} 1)${NC} encode/starlette        ${DIM}Distributed In-Memory State Drift across Multi-Worker Pods${NC}"
    echo -e "  ${CYAN} 2)${NC} sqlalchemy/sqlalchemy   ${DIM}In-Memory Batch Loading RAM Exhaustion vs DB Stream${NC}"
    echo -e "  ${CYAN} 3)${NC} pydantic/pydantic       ${DIM}Redundant Custom Validation vs Core Pydantic Schemas${NC}"
    echo -e "  ${CYAN} 4)${NC} encode/httpx            ${DIM}Async Event Loop Blocking via Synchronous HTTP in Proxy${NC}"
    echo -e "  ${CYAN} 5)${NC} celery/celery           ${DIM}Distributed Task Ack & Balance Mutation Race Condition${NC}"
    echo -e "  ${CYAN} 6)${NC} redis/redis-py          ${DIM}Thundering Herd Cache Invalidation on Node Failover${NC}"
    echo -e "  ${CYAN} 7)${NC} litestar-org/litestar   ${DIM}Atomic Distributed Token Bucket Rate Limiter with Lua${NC}"
    echo -e "  ${CYAN} 8)${NC} pallets/werkzeug        ${DIM}Raw SQL Concatenation & Dynamic Parameter Injection${NC}"
    echo -e "  ${CYAN} 9)${NC} marshmallow-code/...    ${DIM}Public Response Schema Contract Breaking Drift${NC}"
    echo -e "  ${CYAN}10)${NC} encode/databases        ${DIM}The Reverse Lock Order Distributed Deadlock 🔥${NC}"
    echo -e "  ${CYAN}11)${NC} urllib3/urllib3         ${DIM}Unpooled HTTP Session Recreation File Descriptor Leak${NC}"
    echo -e "  ${CYAN}12)${NC} tiangolo/fastapi        ${DIM}Event Loop CPU Starvation via Cryptographic Hashing${NC}"
    echo -e "  ${CYAN}13)${NC} django/django           ${DIM}N+1 Database Query Cascade in Serializer Loop${NC}"
    echo -e "  ${CYAN}14)${NC} encode/uvicorn          ${DIM}Graceful Shutdown with In-Flight Request Draining${NC}"
    echo -e "  ${CYAN}15)${NC} aio-libs/aiohttp        ${DIM}Unbounded Outbound Microservice Call Cascading Failure${NC}"
    echo -e "  ${CYAN}16)${NC} encode/starlette        ${DIM}WebSocket Connection Map Race Condition${NC}"
    echo -e "  ${CYAN}17)${NC} encode/fastapi          ${DIM}Global Array Memory Leak in Webhook Handler${NC}"
    echo -e "  ${CYAN}18)${NC} django/django           ${DIM}Cyclic Dependency in Service Layer Initialization${NC}"
    echo -e "  ${CYAN}19)${NC} aio-libs/aiohttp        ${DIM}Unawaited Async Task leading to Silent Failure${NC}"
    echo -e "  ${CYAN}20)${NC} encode/starlette        ${DIM}Unpaginated API Response Overloading JSON Serialization${NC}"
    echo ""
}

# ------------------------------------------------------------------------------
# 3. Action Implementations
# ------------------------------------------------------------------------------
run_baseline_action() {
    local target_case="${1:-}"
    if [ -z "$target_case" ]; then
        show_header
        echo -e "${BOLD}${YELLOW}🧪 BASELINE EVALUATION (STEP-BY-STEP TRACE)${NC}\n"
        show_cases_menu
        read -p "Enter case number [1-20, default: 1]: " target_case
        target_case=${target_case:-1}
    fi
    echo ""
    python -m eval.harness --runner baseline --case "$target_case" --verbose
}

run_advanced_action() {
    local target_case="${1:-}"
    if [ -z "$target_case" ]; then
        show_header
        echo -e "${BOLD}${CYAN}🤖 ADVANCED FSM SQUAD EVALUATION${NC}\n"
        show_cases_menu
        read -p "Enter case number [1-20, default: 1]: " target_case
        target_case=${target_case:-1}
    fi
    echo ""
    python -m eval.harness --runner advanced --case "$target_case" --verbose
}

run_benchmark_action() {
    local runner="${1:-both}"
    local limit="${2:-}"

    if [ "$#" -eq 0 ]; then
        show_header
        echo -e "${BOLD}${CYAN}📊 BENCHMARK EVALUATION MODES${NC}\n"
        echo -e "  ${GREEN}1)${NC} Full 20-Case Comparative Benchmark (Baseline vs Advanced FSM)"
        echo -e "  ${GREEN}2)${NC} Quick 2-Case Smoke Benchmark (Fast Sanity Check)"
        echo -e "  ${GREEN}3)${NC} Advanced Solution Only (All 20 Cases)"
        echo -e "  ${GREEN}4)${NC} Baseline Solution Only (All 20 Cases)"
        echo -e "  ${GREEN}5)${NC} Custom Sample (Specify number of cases)"
        echo ""
        read -p "Select benchmark mode [1-5, default: 1]: " bench_choice
        bench_choice=${bench_choice:-1}
        echo ""

        case $bench_choice in
            1)
                python -m eval.harness --runner both
                ;;
            2)
                python -m eval.harness --runner both --limit 2
                ;;
            3)
                python -m eval.harness --runner advanced
                ;;
            4)
                python -m eval.harness --runner baseline
                ;;
            5)
                read -p "Enter number of cases to evaluate [1-20]: " num_cases
                num_cases=${num_cases:-5}
                python -m eval.harness --runner both --limit "$num_cases"
                ;;
            *)
                python -m eval.harness --runner both
                ;;
        esac
    else
        local cmd="python -m eval.harness --runner $runner"
        if [ -n "$limit" ]; then
            cmd="$cmd --limit $limit"
        fi
        $cmd
    fi
}

run_custom_review_action() {
    local repo_url="${1:-}"
    local commit_hash="${2:-HEAD}"
    local mode="${3:-diff}"

    if [ -z "$repo_url" ]; then
        show_header
        echo -e "${BOLD}${CYAN}🌐 REVIEW CUSTOM GIT REPOSITORY / TAKE-HOME${NC}\n"
        read -p "Enter Git Repository URL (e.g. https://github.com/FFernandes4280/development-tools): " repo_url
        if [ -z "$repo_url" ]; then
            echo -e "${YELLOW}No repository provided. Aborted.${NC}"
            return
        fi
        read -p "Enter branch or commit hash [default: HEAD]: " commit_hash
        commit_hash=${commit_hash:-HEAD}

        echo -e "\nSelect review mode:"
        echo -e "  1) Incremental Commit / PR Diff"
        echo -e "  2) Full Repository Take-Home Project"
        read -p "Enter mode [1 or 2, default: 1]: " mode_choice
        if [ "$mode_choice" = "2" ]; then
            mode="full_repo"
        else
            mode="diff"
        fi
    fi

    echo ""
    python -m src.cli.review_repo --repo "$repo_url" --commit "$commit_hash" --runner both --mode "$mode"
}

inspect_traces_action() {
    show_header
    echo -e "${BOLD}${CYAN}📜 TRAJECTORY & TRACE DOSSIERS INSPECTOR${NC}\n"

    local trace_files=()
    while IFS= read -r -d $'\0' file; do
        trace_files+=("$file")
    done < <(find trajectories traces -maxdepth 1 \( -name "*.md" -o -name "*.jsonl" -o -name "*.json" \) -print0 2>/dev/null | sort -z -r)

    if [ ${#trace_files[@]} -eq 0 ]; then
        echo -e "${YELLOW}No trace files found in ./trajectories/ or ./traces/. Run a benchmark first.${NC}"
        return
    fi

    echo -e "${BOLD}Latest generated trace reports (showing top 15):${NC}"
    local count=0
    for file in "${trace_files[@]}"; do
        count=$((count + 1))
        local size
        size=$(ls -lh "$file" | awk '{print $5}')
        echo -e "  ${CYAN}$count)${NC} ${file} ${DIM}(${size})${NC}"
        if [ $count -ge 15 ]; then
            break
        fi
    done
    echo ""
    read -p "Enter trace number to view [1-$count, default: 1] (or 0 to cancel): " file_choice
    file_choice=${file_choice:-1}

    if [ "$file_choice" -eq 0 ] || [ "$file_choice" -gt "$count" ]; then
        return
    fi

    local selected_file="${trace_files[$((file_choice - 1))]}"
    echo -e "\n${BOLD}${MAGENTA}--- Displaying ${selected_file} ---${NC}\n"

    if [[ "$selected_file" == *.md ]]; then
        python -c "
import sys
from rich.console import Console
from rich.markdown import Markdown

with open('$selected_file', 'r', encoding='utf-8') as f:
    Console().print(Markdown(f.read()))
" 2>/dev/null || cat "$selected_file"
    elif [[ "$selected_file" == *.json ]]; then
        python -c "
import json, sys
from rich.console import Console
from rich.syntax import Syntax

with open('$selected_file', 'r', encoding='utf-8') as f:
    data = json.dumps(json.load(f), indent=2)
    Console().print(Syntax(data, 'json', theme='monokai', line_numbers=True))
" 2>/dev/null || cat "$selected_file"
    else
        cat "$selected_file"
    fi
}

run_tests_action() {
    echo -e "${CYAN}Running Automated Pytest Test Suite...${NC}\n"
    pytest -v "$@"
}

run_dashboard_action() {
    local port="${1:-8000}"
    echo -e "${CYAN}🚀 Starting Django Web Dashboard on ${BLUE}http://127.0.0.1:${port}${NC}..."
    echo -e "${YELLOW}Press [Ctrl+C] to stop the web server when done.${NC}\n"
    python manage.py runserver "127.0.0.1:${port}"
}

reinstall_deps_action() {
    echo -e "${CYAN}🔄 Syncing and reinstalling all project dependencies in .venv...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt --force-reinstall
    echo -e "${GREEN}[✓] Environment dependencies synchronized successfully!${NC}"
}

clean_action() {
    echo -e "${YELLOW}🧹 Cleaning cache files, bytecode and temporary test directories...${NC}"
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache .ruff_cache
    echo -e "${GREEN}[✓] Cleanup complete!${NC}"
}

show_cli_help() {
    echo -e "${BOLD}micro1 Frontier Engineering Challenge 2026 — CLI Runner${NC}"
    echo ""
    echo -e "${BOLD}Usage:${NC} ./run.sh [COMMAND] [ARGS...]"
    echo ""
    echo -e "${BOLD}Available Commands:${NC}"
    echo -e "  ${GREEN}(none)${NC}                     Launch interactive terminal menu"
    echo -e "  ${GREEN}baseline [CASE_NUM]${NC}        Run Baseline evaluation on a single case (1-20)"
    echo -e "  ${GREEN}advanced [CASE_NUM]${NC}        Run Advanced FSM evaluation on a single case (1-20)"
    echo -e "  ${GREEN}benchmark [RUNNER] [LIMIT]${NC} Run benchmark (e.g. ./run.sh benchmark both 2)"
    echo -e "  ${GREEN}review <REPO_URL> [COMMIT]${NC} Review custom Git repository or Take-Home project"
    echo -e "  ${GREEN}dashboard [PORT]${NC}           Launch Django Web Dashboard (default port: 8000)"
    echo -e "  ${GREEN}web / server${NC}               Alias for dashboard"
    echo -e "  ${GREEN}test [PYTEST_ARGS...]${NC}      Run automated pytest test suite"
    echo -e "  ${GREEN}traces${NC}                     Inspect latest trajectory reports and dossiers"
    echo -e "  ${GREEN}setup / install${NC}            Initialize virtualenv and install dependencies"
    echo -e "  ${GREEN}clean${NC}                      Clean caches and temporary files"
    echo -e "  ${GREEN}key / config / env${NC}         Configure or update GROQ_API_KEY in .env"
    echo -e "  ${GREEN}help / --help / -h${NC}         Display this help message"
    echo ""
}

# ------------------------------------------------------------------------------
# 4. Main Entry Point: Direct Command vs Interactive Menu
# ------------------------------------------------------------------------------
ensure_environment

# If CLI arguments were provided, execute directly without opening the menu
if [ $# -gt 0 ]; then
    cmd="$1"
    shift
    case "$cmd" in
        baseline)
            run_baseline_action "$@"
            ;;
        advanced)
            run_advanced_action "$@"
            ;;
        benchmark|bench)
            run_benchmark_action "$@"
            ;;
        review)
            run_custom_review_action "$@"
            ;;
        traces|trace|trajectory|trajectories)
            inspect_traces_action
            ;;
        key|keys|config|env)
            configure_keys_action
            ;;
        test|tests|pytest)
            run_tests_action "$@"
            ;;
        dashboard|web|server)
            run_dashboard_action "$@"
            ;;
        setup|install)
            reinstall_deps_action
            ;;
        clean)
            clean_action
            ;;
        help|--help|-h)
            show_cli_help
            ;;
        *)
            echo -e "${RED}[ERROR] Unknown command: '$cmd'${NC}"
            show_cli_help
            exit 1
            ;;
    esac
    exit 0
fi

# Interactive Menu Loop
while true; do
    show_header
    show_menu
    read -p "Enter choice [0-10]: " choice
    echo ""

    case "$choice" in
        1)
            run_baseline_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        2)
            run_advanced_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        3)
            run_benchmark_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        4)
            run_custom_review_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        5)
            inspect_traces_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        6)
            configure_keys_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        7)
            run_tests_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        8)
            run_dashboard_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        9)
            reinstall_deps_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        10)
            clean_action
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        0)
            echo -e "${GREEN}Thank you for evaluating the micro1 Frontier Engineering Challenge! Goodbye! 🚀${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option '$choice'. Please choose between 0 and 10.${NC}"
            sleep 1
            ;;
    esac
done

