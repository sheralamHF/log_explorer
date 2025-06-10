#!/bin/bash

# run_log_explorer.sh - Script to run the log explorer tool with proper environment setup

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration
VENV_DIR="venv"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
LOG_EXPLORER_SCRIPT="${SCRIPT_DIR}/log_explorer.py"

# Help function
show_help() {
    echo "Log Explorer Tool"
    echo "Usage: ./run_log_explorer.sh [options]"
    echo ""
    echo "Options:"
    echo "  -a, --app APP_NAME       Application name to search for (required)"
    echo "  -t, --time-range RANGE   Time range (e.g., '10m', '1h', '2d') (default: 1h)"
    echo "  -m, --message TEXT       Filter logs containing this message"
    echo "  -l, --log-type TYPE      Filter by log level (error, warning, info, debug)"
    echo "  -s, --source SOURCE      Source for logs (kubernetes or prometheus) (default: kubernetes)"
    echo "  -r, --region REGION      AWS region for Bedrock (default: eu-west-1)"
    echo "  --no-ssl-verify          Disable SSL certificate verification for Kubernetes/Prometheus API calls"
    echo "  -h, --help               Show this help message and exit"
    echo ""
    echo "Example:"
    echo "  ./run_log_explorer.sh --app payment-service --time-range 3h --log-type error"
}

# Check if the virtual environment exists, create it if it doesn't
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Virtual environment not found. Creating one..."
        python3 -m venv "$VENV_DIR"
        source "${VENV_DIR}/bin/activate"
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        source "${VENV_DIR}/bin/activate"
    fi
}

# Parse arguments and pass them to the Python script
parse_and_run() {
    # Initialize variables
    ARGS=""
    APP_NAME=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -a|--app)
                APP_NAME="$2"
                ARGS="${ARGS} --app \"$2\""
                shift 2
                ;;
            -t|--time-range)
                ARGS="${ARGS} --time-range \"$2\""
                shift 2
                ;;
            -m|--message)
                ARGS="${ARGS} --message \"$2\""
                shift 2
                ;;
            -l|--log-type)
                ARGS="${ARGS} --log-type \"$2\""
                shift 2
                ;;
            -s|--source)
                ARGS="${ARGS} --source \"$2\""
                shift 2
                ;;
            -r|--region)
                ARGS="${ARGS} --region \"$2\""
                shift 2
                ;;
            --no-ssl-verify)
                ARGS="${ARGS} --no-ssl-verify"
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Check if app name was provided
    if [ -z "$APP_NAME" ]; then
        echo "Error: Application name (--app) is required."
        show_help
        exit 1
    fi
    
    # Make sure the script is executable
    chmod +x "$LOG_EXPLORER_SCRIPT"
    
    # Run the script with all arguments
    echo "Running Log Explorer..."
    
    # Print a message if AWS environment variables are detected
    if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        echo "AWS credentials detected in environment."
    fi
    if [ -n "$AWS_BEDROCK_INFERENCE_PROFILE" ]; then
        echo "Using AWS Bedrock inference profile from environment: $AWS_BEDROCK_INFERENCE_PROFILE"
    fi
    if [ -n "$AWS_REGION" ]; then
        echo "Using AWS region from environment: $AWS_REGION"
    fi
    
    # Pass all environment variables to the Python process
    eval "python ${LOG_EXPLORER_SCRIPT} ${ARGS}"
}

# Main execution
main() {
    # Check if help is requested
    if [[ "$1" == "-h" || "$1" == "--help" || $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    # Setup environment
    check_venv
    
    # Run with arguments
    parse_and_run "$@"
}

# Run main with all arguments
main "$@"