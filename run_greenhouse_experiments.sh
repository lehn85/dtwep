#!/usr/bin/env bash

# ANSI Color Codes for beautiful terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}======================================================================${NC}"
echo -e "${MAGENTA}${BOLD}        AGRIVOLTAIC GREENHOUSE DIGITAL TWIN - EXPERIMENT RUNNER${NC}"
echo -e "${CYAN}${BOLD}======================================================================${NC}"
echo ""

# Ensure common paths on Windows/Linux are included in PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Check if uv is installed
if ! command -v uv &> /dev/null && ! command -v uv.exe &> /dev/null; then
    echo -e "${RED}${BOLD}[ERROR]${NC} 'uv' package manager could not be found."
    echo -e "Please install 'uv' before running experiments: https://docs.astral.sh/uv/"
    exit 1
fi

# Function to run an experiment and track status
run_exp() {
    local exp_num=$1
    local exp_name=$2
    local exp_script=$3
    shift 3
    
    echo -e "${BLUE}${BOLD}[RUNNING]${NC} ${BOLD}Experiment ${exp_num}: ${exp_name}${NC}"
    echo -e "Command: uv run python ${exp_script} $*"
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    
    start_time=$(date +%s)
    uv run python "$exp_script" "$@"
    exit_code=$?
    end_time=$(date +%s)
    
    duration=$((end_time - start_time))
    
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}${BOLD}[SUCCESS]${NC} Experiment ${exp_num} completed in ${duration}s."
        eval "STATUS_${exp_num}=\"${GREEN}PASSED (${duration}s)${NC}\""
    else
        echo -e "${RED}${BOLD}[FAILED]${NC} Experiment ${exp_num} failed with exit code ${exit_code} after ${duration}s."
        eval "STATUS_${exp_num}=\"${RED}FAILED (${duration}s)${NC}\""
    fi
    echo ""
}

# Default status values
STATUS_1="${YELLOW}SKIPPED${NC}"
STATUS_2="${YELLOW}SKIPPED${NC}"
STATUS_3="${YELLOW}SKIPPED${NC}"

# Menu selection
show_menu() {
    echo -e "${BOLD}Select Benchmark Experiment:${NC}"
    echo -e "  ${BOLD}1)${NC} Exp 1: Initial Calibration Benchmark (Model A vs Baseline vs Calibrated Model B & Speedup)"
    echo -e "  ${BOLD}2)${NC} Exp 2: Multi-Scenario Cross-Validation (Multi-Scenario Model A vs Model B)"
    echo -e "  ${BOLD}3)${NC} Exp 3: Physical Degradation Tracking Benchmark (Recalibration under Model A Degradation)"
    echo -e "  ${BOLD}5)${NC} Run ${BOLD}ALL${NC} Experiments Sequentially"
    echo -e "  ${BOLD}q)${NC} Quit"
    echo ""
    read -p "Enter your choice [1, 2, 3, 5 or q]: " choice
    echo ""
}

# Run based on arguments or choice
choice=$1

if [ -z "$choice" ]; then
    show_menu
fi

case "$choice" in
    1)
        run_exp "1" "Initial Calibration Benchmark" "cases/greenhouse/exp1_initial_calibration.py"
        ;;
    2)
        run_exp "2" "Scenario Simulation Benchmark" "cases/greenhouse/exp2_scenario_simulation.py"
        ;;
    3)
        run_exp "3" "Periodic Recalibration Benchmark" "cases/greenhouse/exp3_recalibration.py"
        ;;
    5|all|"")
        echo -e "${YELLOW}${BOLD}[INFO] Running all benchmark experiments sequentially...${NC}\n"
        run_exp "1" "Initial Calibration Benchmark" "cases/greenhouse/exp1_initial_calibration.py" "--force-model-a"
        run_exp "2" "Scenario Simulation Benchmark" "cases/greenhouse/exp2_scenario_simulation.py"
        run_exp "3" "Periodic Recalibration Benchmark" "cases/greenhouse/exp3_recalibration.py"
        ;;
    q|Q)
        echo -e "${YELLOW}Exited.${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}[ERROR] Invalid choice.${NC}"
        exit 1
        ;;
esac

# Print Summary Table
echo -e "${CYAN}${BOLD}======================================================================${NC}"
echo -e "${MAGENTA}${BOLD}                     EXPERIMENT RUN SUMMARY${NC}"
echo -e "${CYAN}${BOLD}======================================================================${NC}"
printf "${BOLD}%-40s | %-20s${NC}\n" "Experiment Name" "Status"
echo -e "------------------------------------------------------------"
printf "%-40s | %b\n" "Exp 1: Initial Calibration Benchmark" "$STATUS_1"
printf "%-40s | %b\n" "Exp 2: Multi-Scenario Cross-Validation" "$STATUS_2"
printf "%-40s | %b\n" "Exp 3: Recalibration Capability" "$STATUS_3"
echo -e "${CYAN}${BOLD}======================================================================${NC}"
echo -e "${GREEN}${BOLD}Completed!${NC} Results, plots, and metrics are saved in '${BOLD}results/greenhouse/${NC}'."

