# Log Explorer

A powerful tool for analyzing application logs in microservice architectures, leveraging Claude 3.7 Sonnet to provide intelligent insights for on-call engineers.

## Overview

Log Explorer is a Python-based CLI tool that helps on-call engineers quickly analyze application logs when alerts fire. It connects to Kubernetes or Prometheus, fetches relevant logs based on filters, and uses Claude 3.7 Sonnet to:

- Summarize errors and issues
- Identify affected services
- Detect patterns in error occurrences
- Suggest potential root causes
- Recommend specific places to investigate
- Identify related trace IDs for further debugging

## Key Features

- **Intelligent Analysis**: Leverages Claude 3.7 Sonnet for deep log analysis and insights
- **Flexible Log Sources**: Works with both Kubernetes logs and Prometheus metrics
- **Powerful Filtering**: Filter by application, time range, log level, and message content
- **Concise Summaries**: Get actionable insights quickly during critical incidents
- **AWS Bedrock Integration**: Uses AWS Bedrock for secure AI inference
- **Organized Output**: All analysis reports are saved in the `log_analysis/` directory

## Quick Start

1. **Setup the environment**:
   ```
   ./setup_environment.sh
   ```

2. **Run the tool**:
   ```
   ./run_log_explorer.sh --app your-app-name --time-range 1h --log-type error
   ```

3. **View the analysis** in your terminal and in the saved output file

4. **Force environment recreation** (if needed):
   ```
   ./setup_environment.sh --force
   ```

## Requirements

- Python 3.6+
- AWS credentials with Bedrock access
- Kubernetes access (if using Kubernetes logs)
- Prometheus endpoint access (if using Prometheus)

## Use Cases

- **On-call Response**: Quickly assess the situation when alerts fire
- **Incident Investigation**: Identify patterns and root causes of issues
- **System Monitoring**: Regularly check for potential problems before they escalate
- **Post-Incident Analysis**: Review logs after incidents for preventative measures

## Documentation

For detailed usage instructions, see the [HOW-TO.md](HOW-TO.md) guide.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.