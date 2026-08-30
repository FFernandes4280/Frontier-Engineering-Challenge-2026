#!/usr/bin/env bash
# ==============================================================================
# Frontier Engineering Challenge 2026 - Interactive CLI & Web Runner
# ==============================================================================

set -e

# Auto-activate venv if available
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Styling
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Ensure environment is ready
check_env() {
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        echo -e "${YELLOW}[!] .env not found. Creating from .env.example...${NC}"
        cp .env.example .env
    fi
}

show_header() {
    clear
    echo -e "${CYAN}${BOLD}==================================================================${NC}"
    echo -e "${MAGENTA}${BOLD}   🚀 micro1 Frontier Engineering Challenge 2026 — Interactive CLI ${NC}"
    echo -e "${CYAN}${BOLD}==================================================================${NC}"
    echo ""
}

show_menu() {
    echo -e "${BOLD}Select an action to execute:${NC}"
    echo -e "  ${GREEN}1)${NC} 🧪 Run Baseline on Single Repository (with full Step-by-Step trace)"
    echo -e "  ${GREEN}2)${NC} 🤖 Run Advanced Solution on Single Repository (FSM Multi-Agent)"
    echo -e "  ${GREEN}3)${NC} 📊 Run Complete Benchmark (Baseline vs Advanced on 10 Cases)"
    echo -e "  ${GREEN}4)${NC} 🌐 Review Custom Web Git Repository (e.g. GitHub URL)"
    echo -e "  ${GREEN}5)${NC} 📜 Inspect Trajectories & Traces (Rich Terminal Viewer)"
    echo -e "  ${GREEN}6)${NC} 🧪 Run Pytest Test Suite"
    echo -e "  ${GREEN}7)${NC} 🌐 Launch Django Web Dashboard (http://127.0.0.1:8000)"
    echo -e "  ${GREEN}8)${NC} 🧹 Clean temporary files and traces"
    echo -e "  ${RED}0)${NC} 🚪 Exit"
    echo ""
}

show_cases_menu() {
    echo -e "${BOLD}Select a benchmark repository to evaluate:${NC}"
    echo -e "  ${CYAN}1)${NC}  encode/starlette (Distributed In-Memory State Drift)"
    echo -e "  ${CYAN}2)${NC}  sqlalchemy/sqlalchemy (In-Memory Batch RAM Exhaustion)"
    echo -e "  ${CYAN}3)${NC}  pydantic/pydantic (Redundant Logic vs Reusable Modules)"
    echo -e "  ${CYAN}4)${NC}  encode/httpx (Async Event Loop Blocking I/O)"
    echo -e "  ${CYAN}5)${NC}  celery/celery (Balance Mutation Race Condition)"
    echo -e "  ${CYAN}6)${NC}  redis/redis-py (Thundering Herd Cache Stampede)"
    echo -e "  ${CYAN}7)${NC}  litestar-org/litestar (Atomic Distributed Token Bucket Rate Limiting)"
    echo -e "  ${CYAN}8)${NC}  pallets/werkzeug (Dynamic SQL Injection Vulnerability)"
    echo -e "  ${CYAN}9)${NC}  marshmallow-code/marshmallow (Public Response Contract Breaking Drift)"
    echo -e "  ${CYAN}10)${NC} encode/databases (The Reverse Lock Order Distributed Deadlock 🔥)"
    echo ""
}

check_env

while true; do
    show_header
    show_menu
    read -p "Enter choice [0-8]: " choice
    echo ""

    case $choice in
        1)
            show_header
            echo -e "${BOLD}${YELLOW}🧪 BASELINE EVALUATION (STEP-BY-STEP TRACE)${NC}\n"
            show_cases_menu
            read -p "Enter case number [1-10]: " case_num
            case_num=${case_num:-1}
            echo ""
            python3 -m eval.harness --runner baseline --case "$case_num" --verbose
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        2)
            show_header
            echo -e "${BOLD}${CYAN}🤖 ADVANCED FSM EVALUATION${NC}\n"
            show_cases_menu
            read -p "Enter case number [1-10]: " case_num
            case_num=${case_num:-1}
            echo ""
            python3 -m eval.harness --runner advanced --case "$case_num" --verbose
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        3)
            echo -e "${CYAN}Running Full Comparative Benchmark (10 cases)...${NC}"
            python3 -m eval.harness --runner both
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        4)
            echo -e "${CYAN}🌐 Review Custom Web Git Repository...${NC}"
            read -p "Enter Git Repository URL (e.g. https://github.com/FFernandes4280/development-tools): " repo_url
            read -p "Enter branch or commit hash [default: HEAD]: " commit_hash
            commit_hash=${commit_hash:-HEAD}
            python3 -m src.cli.review_repo --repo "$repo_url" --commit "$commit_hash" --runner both
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        5)
            echo -e "${CYAN}Launching Trace Viewer...${NC}"
            python3 -m src.tracing.viewer
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        6)
            echo -e "${CYAN}Running Automated Pytest Suite...${NC}"
            pytest -v
            echo ""
            read -p "Press [Enter] to continue..."
            ;;
        7)
            echo -e "${CYAN}🚀 Starting Django Web Dashboard on http://127.0.0.1:8000...${NC}"
            echo -e "${YELLOW}Press [Ctrl+C] to stop the web server when done.${NC}\n"
            python3 manage.py runserver 127.0.0.1:8000
            ;;
        8)
            echo -e "${YELLOW}Cleaning cache files and temporary traces...${NC}"
            find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            rm -rf .pytest_cache
            echo -e "${GREEN}Cleaned!${NC}"
            read -p "Press [Enter] to continue..."
            ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Try again.${NC}"
            sleep 1
            ;;
    esac
done
