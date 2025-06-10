#!/bin/bash

# setup_environment.sh - Script to create and configure the Python virtual environment

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration
VENV_DIR="venv"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements.txt"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Help function
show_help() {
    echo "Log Explorer - Environment Setup"
    echo ""
    echo "This script creates and configures a Python virtual environment"
    echo "for the Log Explorer tool."
    echo ""
    echo "Usage: ./setup_environment.sh [options]"
    echo ""
    echo "Options:"
    echo "  -f, --force       Force recreation of the virtual environment"
    echo "  -h, --help        Show this help message and exit"
}

# Check Python version
check_python_version() {
    echo -e "${YELLOW}Checking Python version...${NC}"
    
    if command -v python3 &>/dev/null; then
        PYTHON_VERSION=$(python3 --version)
        echo -e "${GREEN}Found Python: ${PYTHON_VERSION}${NC}"
        
        # Extract version number and check if it's at least 3.6
        PYTHON_MAJOR_MINOR=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
        PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
        
        if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 6 ]); then
            echo -e "${RED}Error: Python 3.6+ is required. Found ${PYTHON_MAJOR_MINOR}${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Error: Python 3 not found. Please install Python 3.6 or later.${NC}"
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    echo -e "${YELLOW}Checking pip installation...${NC}"
    
    if ! python3 -m pip --version &>/dev/null; then
        echo -e "${RED}Error: pip is not installed. Please install pip for Python 3.${NC}"
        exit 1
    else
        echo -e "${GREEN}Found pip.${NC}"
    fi
}

# Check if virtual environment module is installed
check_venv_module() {
    echo -e "${YELLOW}Checking virtualenv support...${NC}"
    
    if ! python3 -c "import venv" &>/dev/null; then
        echo -e "${RED}Error: Python venv module not found. Please install it.${NC}"
        echo "On Ubuntu/Debian: sudo apt-get install python3-venv"
        echo "On Fedora: sudo dnf install python3-virtualenv"
        echo "On macOS: pip3 install virtualenv"
        exit 1
    else
        echo -e "${GREEN}Found virtualenv support.${NC}"
    fi
}

# Create virtual environment
create_venv() {
    echo -e "${YELLOW}Setting up virtual environment...${NC}"
    
    # Create virtual environment if it doesn't exist or force is specified
    if [ ! -d "$VENV_DIR" ] || [ "$FORCE_RECREATE" = true ]; then
        if [ -d "$VENV_DIR" ] && [ "$FORCE_RECREATE" = true ]; then
            echo -e "${YELLOW}Removing existing virtual environment...${NC}"
            rm -rf "$VENV_DIR"
        fi
        
        echo -e "${YELLOW}Creating new virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
    else
        echo -e "${GREEN}Virtual environment already exists.${NC}"
    fi
}

# Install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    
    # Activate virtual environment
    source "${VENV_DIR}/bin/activate"
    
    # Upgrade pip
    echo -e "${YELLOW}Upgrading pip...${NC}"
    pip install --upgrade pip
    
    # Install dependencies from requirements.txt
    echo -e "${YELLOW}Installing required packages...${NC}"
    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install -r "$REQUIREMENTS_FILE"
        echo -e "${GREEN}All packages installed successfully.${NC}"
    else
        echo -e "${RED}Error: requirements.txt not found at ${REQUIREMENTS_FILE}${NC}"
        exit 1
    fi
}

# Verify installation
verify_installation() {
    echo -e "${YELLOW}Verifying installation...${NC}"
    
    # Activate virtual environment if not activated
    if [[ "$VIRTUAL_ENV" != *"$VENV_DIR"* ]]; then
        source "${VENV_DIR}/bin/activate"
    fi
    
    # Check if key packages are installed
    if python -c "import boto3, pandas, requests, tabulate" &>/dev/null; then
        echo -e "${GREEN}All required packages verified.${NC}"
    else
        echo -e "${RED}Error: Some required packages are missing.${NC}"
        exit 1
    fi
}

# Main execution
main() {
    FORCE_RECREATE=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--force)
                FORCE_RECREATE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo -e "${GREEN}=== Log Explorer - Environment Setup ===${NC}"
    
    # Run checks
    check_python_version
    check_pip
    check_venv_module
    
    # Setup environment
    create_venv
    install_dependencies
    verify_installation
    
    echo -e "${GREEN}=== Environment setup completed successfully ===${NC}"
    echo ""
    echo -e "${YELLOW}To activate the virtual environment, run:${NC}"
    echo "source ${VENV_DIR}/bin/activate"
    echo ""
    echo -e "${YELLOW}To run the log explorer:${NC}"
    echo "./run_log_explorer.sh --app <app-name> [options]"
}

# Run main
main "$@"