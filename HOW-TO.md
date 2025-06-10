# Log Explorer - How To Guide

This guide provides detailed instructions for setting up and using the Log Explorer tool to analyze application logs in a microservice architecture.

## Prerequisites

Before using the Log Explorer tool, ensure you have the following:

1. **Python 3.6+** installed on your system
2. **AWS credentials** configured with access to Bedrock
3. **Kubernetes access** to the clusters where your applications are running
4. **Required Python packages** (see Installation section)

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd log_explorer
   ```

2. Setup the Python environment using the provided script:
   ```
   ./setup_environment.sh
   ```
   This will:
   - Create a Python virtual environment in the `venv` directory
   - Install all required dependencies from requirements.txt
   - Verify the installation

3. If you need to recreate the environment:
   ```
   ./setup_environment.sh --force
   ```

## Configuration

The Log Explorer tool can be configured via command-line arguments or environment variables. The main configuration options include:

### Environment Variables

For AWS authentication and configuration, you can set these environment variables:

- `AWS_REGION`: The AWS region to use (e.g., "eu-west-1")
- `AWS_BEDROCK_INFERENCE_PROFILE`: The ARN of your Bedrock inference profile
- `AWS_ACCESS_KEY_ID`: Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
- `AWS_SESSION_TOKEN`: Your AWS session token (if using temporary credentials)

### Command-Line Arguments

Command-line arguments will override environment variables if both are provided:

- AWS Region (defaults to AWS_REGION environment variable or "eu-west-1")
- AWS Bedrock Inference Profile ARN (defaults to AWS_BEDROCK_INFERENCE_PROFILE environment variable)
- Log source (Kubernetes or Prometheus)

No additional configuration files are required as the tool uses existing Kubernetes and AWS configurations from your environment.

## Basic Usage

The basic syntax for running the Log Explorer is:

```bash
./run_log_explorer.sh --app <app-name> [options]
```

This wrapper script automatically activates the virtual environment before running the Python script.

### Required Arguments

- `--app, -a`: Name of the application to fetch logs for

### Optional Arguments

- `--time-range, -t`: Time range to search (default: "1h", format: "10m", "1h", "2d")
- `--message, -m`: Filter logs containing specific text
- `--log-type, -l`: Filter by log level (error, warning, info, debug)
- `--source, -s`: Source for logs (kubernetes or prometheus)
- `--region, -r`: AWS region for Bedrock (default: eu-west-1)
- `--profile, -p`: AWS Bedrock inference profile ARN
- `--no-ssl-verify`: Disable SSL certificate verification for Kubernetes/Prometheus API calls

## Examples

### Basic Example - Get Last Hour's Error Logs

```bash
./run_log_explorer.sh --app payment-service --log-type error
```

### Searching with Time Range and Message Filter

```bash
./run_log_explorer.sh --app user-service --time-range 3h --message "timeout"
```

### Using Prometheus as Log Source

```bash
./run_log_explorer.sh --app inventory-service --source prometheus --time-range 1d
```

### Using Environment Variables for AWS Credentials

```bash
# Set environment variables
export AWS_REGION=eu-west-1
export AWS_BEDROCK_INFERENCE_PROFILE=arn:aws:bedrock:eu-west-1:123456789012:inference-profile/my-profile
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_SESSION_TOKEN=AQoDYXdzEJr...EXAMPLETOKEN

# Run the tool (no need to specify region or profile)
./run_log_explorer.sh --app payment-service --log-type error
```

## Understanding the Output

The tool provides a comprehensive analysis of the logs, organized into several sections:

1. **Summary of Errors**: Overview of the main issues found
2. **Affected Services**: Which services are experiencing problems
3. **Pattern Detection**: Any patterns in how or when errors occur
4. **Potential Root Causes**: Likely causes of the identified issues
5. **Investigation Areas**: Specific code or systems to look into
6. **Related Trace IDs**: Trace IDs that might help with debugging

The analysis is displayed in the terminal and also saved to a timestamped file in the `log_analysis/` directory.

## Troubleshooting

### Common Issues

1. **AWS Bedrock Access Error**:
   - Ensure your AWS credentials are properly configured
   - Verify you have access to the Bedrock service
   - Note: The tool now automatically tests the Bedrock connection on startup
   - If the "inferenceProfile" parameter causes errors, it will automatically skip it
   - To troubleshoot further, check the AWS policy associated with your credentials to ensure it has bedrock:ListFoundationModels and bedrock-runtime:InvokeModel permissions

2. **Kubernetes Access Error**:
   - Check your kubeconfig file is properly configured
   - Ensure you have permissions to access the pods in the namespace
   - Verify the application name matches a deployed service
   - If you encounter SSL certificate verification errors, try running with `--no-ssl-verify` option

3. **No Logs Found**:
   - Try increasing the time range
   - Check if the application name is correct
   - Verify the log type (some applications might not have "error" logs)

## Advanced Usage

### Integration with Alert Systems

You can integrate the Log Explorer with OpsGenie or other alert systems by creating a webhook that triggers the script when an alert fires.

Example shell script for OpsGenie integration:

```bash
#!/bin/bash
APP_NAME=$(echo $ALERT_DETAILS | jq -r '.app_name')
./run_log_explorer.sh --app $APP_NAME --log-type error --time-range 1h
```

### Scheduling Regular Log Analysis

You can use cron to schedule regular log analysis:

```
# Run log analysis for critical services every hour
0 * * * * /path/to/run_log_explorer.sh --app critical-service --log-type error --time-range 1h
```

## Provided Scripts

The Log Explorer comes with several utility scripts to help you manage the environment and run the tool.

### setup_environment.sh

This script handles the creation and management of the Python virtual environment.

```bash
./setup_environment.sh [options]
```

Options:
- `-f, --force`: Force recreation of the virtual environment
- `-h, --help`: Show help message

The script performs the following tasks:
- Checks for Python 3.6+ installation
- Verifies pip and virtualenv are available
- Creates a virtual environment in the `venv` directory
- Installs all dependencies from requirements.txt
- Verifies the installation was successful

### run_log_explorer.sh

This is a wrapper script that handles activating the virtual environment before running the Python script.

```bash
./run_log_explorer.sh [options]
```

Options are the same as for the main Python script:
- `-a, --app APP_NAME`: Application name to search for (required)
- `-t, --time-range RANGE`: Time range (e.g., '10m', '1h', '2d')
- `-m, --message TEXT`: Filter logs containing this message
- `-l, --log-type TYPE`: Filter by log level
- `-s, --source SOURCE`: Source for logs (kubernetes or prometheus)
- `-r, --region REGION`: AWS region for Bedrock
- `-h, --help`: Show help message

The script will automatically create the virtual environment if it doesn't exist.

## Extending the Tool

The Log Explorer tool is designed to be extensible. You can modify the script to:

1. Add support for additional log sources
2. Customize the prompts sent to Claude
3. Add more filtering options
4. Implement result visualization

See the comments in the source code for guidance on extending specific components.