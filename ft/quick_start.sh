#!/bin/bash
# Quick Start Script for GVPO Training
# This script provides easy commands for common GVPO training tasks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        GVPO Training Quick Start                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print usage
usage() {
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 [command] [options]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  test          - Run tests to verify installation"
    echo "  validate      - Validate configuration without training"
    echo "  train         - Start GVPO training"
    echo "  train-small   - Start training with reduced batch size (for testing)"
    echo "  dry-run       - Show training command without executing"
    echo "  check         - Check prerequisites and setup"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 test"
    echo "  $0 validate"
    echo "  $0 train"
    echo "  $0 train algorithm.gvpo_beta=0.15"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking Prerequisites...${NC}"
    echo ""

    # Check Python
    if command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        echo -e "  ${GREEN}✓${NC} Python: $PYTHON_VERSION"
    else
        echo -e "  ${RED}✗${NC} Python not found"
        exit 1
    fi

    # Check CUDA
    if command -v nvidia-smi &> /dev/null; then
        GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
        echo -e "  ${GREEN}✓${NC} CUDA GPUs: $GPU_COUNT"
    else
        echo -e "  ${YELLOW}⚠${NC} nvidia-smi not found (CPU mode)"
    fi

    # Check required Python packages
    echo ""
    echo -e "${BLUE}Checking Python Packages...${NC}"

    packages=("torch" "transformers" "pyyaml")
    all_installed=true

    for package in "${packages[@]}"; do
        if python -c "import $package" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $package"
        else
            echo -e "  ${RED}✗${NC} $package (install with: pip install $package)"
            all_installed=false
        fi
    done

    # Check data directory
    echo ""
    echo -e "${BLUE}Checking Data Directory...${NC}"
    if [ -d "$PROJECT_DIR/data" ]; then
        echo -e "  ${GREEN}✓${NC} Data directory exists"
    else
        echo -e "  ${YELLOW}⚠${NC} Data directory not found at $PROJECT_DIR/data"
    fi

    # Check config file
    echo ""
    echo -e "${BLUE}Checking Configuration...${NC}"
    if [ -f "$SCRIPT_DIR/config_gvpo.yaml" ]; then
        echo -e "  ${GREEN}✓${NC} Configuration file exists"
    else
        echo -e "  ${RED}✗${NC} Configuration file not found"
        exit 1
    fi

    echo ""
    if [ "$all_installed" = true ]; then
        echo -e "${GREEN}✓ All prerequisites satisfied${NC}"
    else
        echo -e "${YELLOW}⚠ Some prerequisites missing - please install them${NC}"
    fi
    echo ""
}

# Function to run tests
run_tests() {
    echo -e "${BLUE}Running GVPO Tests...${NC}"
    echo ""
    cd "$PROJECT_DIR"
    python ft/test_gvpo.py
}

# Function to validate config
validate_config() {
    echo -e "${BLUE}Validating Configuration...${NC}"
    echo ""
    cd "$PROJECT_DIR"
    python ft/train_gvpo.py --validate-only
}

# Function to run training
run_training() {
    echo -e "${BLUE}Starting GVPO Training...${NC}"
    echo ""
    cd "$PROJECT_DIR"
    python ft/train_gvpo.py "$@"
}

# Function to run training with small batch (for testing)
run_training_small() {
    echo -e "${BLUE}Starting GVPO Training (Small Batch)...${NC}"
    echo ""
    cd "$PROJECT_DIR"
    python ft/train_gvpo.py \
        data.train_batch_size=4 \
        actor_rollout_ref.rollout.n=2 \
        trainer.total_epochs=1 \
        "$@"
}

# Function to dry run
dry_run() {
    echo -e "${BLUE}Dry Run (Command Only)...${NC}"
    echo ""
    cd "$PROJECT_DIR"
    python ft/train_gvpo.py --dry-run "$@"
}

# Main script logic
case "${1:-}" in
    test)
        run_tests
        ;;
    validate)
        validate_config
        ;;
    train)
        shift
        run_training "$@"
        ;;
    train-small)
        shift
        run_training_small "$@"
        ;;
    dry-run)
        shift
        dry_run "$@"
        ;;
    check)
        check_prerequisites
        ;;
    help|--help|-h|"")
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        usage
        exit 1
        ;;
esac
