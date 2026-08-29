#!/usr/bin/env bash
# ==============================================================================
# Frontier Engineering Challenge 2026 - Interactive CLI Runner
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
    echo -e "  ${GREEN}1)${NC} 🧪 Run Baseline Solution (Single-prompt / Naive)"
    echo -e "  ${GREEN}2)${NC} 🤖 Run Advanced Solution (FSM Multi-Agent + Verifier)"
    echo -e "  ${GREEN}3)${NC} 📊 Run Complete Benchmark (Baseline vs Advanced on 10+ Cases)"
    echo -e "  ${GREEN}4)${NC} 🔍 Inspect Trajectories & Traces (Rich Terminal Viewer)"
    echo -e "  ${GREEN}5)${NC} 📦 Setup / Install Dependencies"
    echo -e "  ${GREEN}6)${NC} 🧹 Clean temporary files and traces"
    echo -e "  ${RED}0)${NC} 🚪 Exit"
    echo ""
}

check_env

while true; do
    show_header
    show_menu
    read -p "Enter choice [0-6]: " choice
    echo ""

    case $choice in
        1)
            echo -e "${CYAN}Running Baseline Solution...${NC}"
            python3 -m eval.harness --runner baseline
            read -p "Press [Enter] to continue..."
            ;;
        2)
            echo -e "${CYAN}Running Advanced Solution (FSM Agent)...${NC}"
            python3 -m eval.harness --runner advanced
            read -p "Press [Enter] to continue..."
            ;;
        3)
            echo -e "${CYAN}Running Full Comparative Benchmark (10+ cases)...${NC}"
            python3 -m eval.harness --runner both
            read -p "Press [Enter] to continue..."
            ;;
        4)
            echo -e "${CYAN}Launching Trace Viewer...${NC}"
            python3 -m src.tracing.viewer
            read -p "Press [Enter] to continue..."
            ;;
        5)
            echo -e "${CYAN}Installing dependencies from requirements.txt...${NC}"
            pip install -r requirements.txt
            read -p "Press [Enter] to continue..."
            ;;
        6)
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
