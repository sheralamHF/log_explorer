#!/usr/bin/env python3
"""
Log Explorer Tool

This script retrieves and analyzes application logs from Kubernetes or Prometheus,
providing a summary of errors, potential issues, and insights using Claude 3.7 Sonnet.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
import time
import re
import boto3
import pandas as pd
import requests
from tabulate import tabulate
from typing import Dict, List, Optional, Tuple, Union, Any
import subprocess
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class LogExplorer:
    def __init__(self, region=None, profile_arn=None, disable_ssl_verify=False):
        """Initialize the LogExplorer with AWS Bedrock client."""
        # Use environment variables if available, otherwise use defaults
        self.region = region or os.environ.get("AWS_REGION", "eu-west-1")
        self.profile_arn = profile_arn or os.environ.get("AWS_BEDROCK_INFERENCE_PROFILE", 
            "arn:aws:bedrock:eu-west-1:951719175506:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0")
        self.disable_ssl_verify = disable_ssl_verify
        
        # Set the Claude model ID
        self.model_id = "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"
        
        # Create the Bedrock client using environment credentials when available
        try:
            session = boto3.Session(region_name=self.region)
            self.bedrock_client = session.client("bedrock-runtime")
            print(f"Successfully initialized Bedrock client in region: {self.region}")
        except Exception as e:
            print(f"Warning: Error initializing standard Bedrock client: {str(e)}")
            print("Falling back to direct boto3 client...")
            self.bedrock_client = boto3.client(
                service_name="bedrock-runtime", 
                region_name=self.region
            )
        
        # Test the AWS Bedrock connection
        self.test_bedrock_connection()
        
    def test_bedrock_connection(self):
        """Test the connection to AWS Bedrock and list available models."""
        try:
            print("\n=== Testing AWS Bedrock Connection ===")
            print(f"Using Claude model ID: {self.model_id}")
            print(f"Using inference profile: {self.profile_arn}")
            
            # Try direct API call to test connection
            try:
                print("\nTesting Claude API access...")
                
                # Create modified invoke parameters
                invoke_params = {
                    "body": json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Say hello"}]
                    }),
                    "contentType": "application/json",
                    "accept": "application/json"
                }
                
                # Try direct Claude API call
                from botocore.exceptions import ClientError
                
                # First, try using the modelId parameter
                try:
                    print("Testing standard modelId parameter...")
                    response = self.bedrock_client.invoke_model(
                        modelId=self.model_id,
                        **invoke_params
                    )
                    # If successful, keep using standard method
                    print("✓ Standard modelId parameter worked!")
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    error_msg = e.response.get('Error', {}).get('Message', '')
                    
                    if "ResourceNotFoundException" in str(e) or "not found" in str(e).lower():
                        print(f"✗ Model ID not recognized: {error_msg}")
                        print("Trying alternative approach with direct API call...")
                        
                        try:
                            # Try calling the model directly by endpoint
                            endpoint = f"bedrock-runtime.{self.region}.amazonaws.com"
                            path = f"/model/{self.model_id}/invoke"
                            
                            print(f"Custom approach would use: {endpoint}{path}")
                            print("However, for compatibility we're going to use standard models.")
                            print("Try one of these standard Claude models:")
                            std_models = [
                                "anthropic.claude-3-sonnet-20240229-v1:0",
                                "anthropic.claude-3-haiku-20240307-v1:0",
                                "anthropic.claude-v2",
                                "anthropic.claude-v2:1",
                                "anthropic.claude-instant-v1"
                            ]
                            
                            for idx, model in enumerate(std_models):
                                print(f"  {idx+1}. {model}")
                            
                            # Try the first standard model
                            print(f"\nTrying with standard model: {std_models[0]}...")
                            self.model_id = std_models[0]
                            response = self.bedrock_client.invoke_model(
                                modelId=self.model_id,
                                **invoke_params
                            )
                            print("✓ Standard model worked successfully!")
                        except Exception as inner_e:
                            print(f"✗ Alternative approach failed: {str(inner_e)}")
                            print("Check your AWS credentials and Bedrock access permissions.")
                            return
                    else:
                        print(f"✗ Unexpected error: {error_code} - {error_msg}")
                        return
                
                # Check if response is valid
                response_body = json.loads(response['body'].read().decode())
                if 'content' in response_body and len(response_body['content']) > 0:
                    print("✓ AWS Bedrock connection test successful!")
                    print(f"Response: {response_body['content'][0]['text'][:50]}...")
                else:
                    print(f"⚠ Unexpected response format: {response_body}")
            except Exception as e:
                print(f"✗ Test invocation failed: {str(e)}")
                print("Check your AWS credentials and Bedrock access permissions.")
                
            print("=====================================\n")
        except Exception as e:
            print(f"✗ AWS Bedrock connection test failed: {str(e)}")
            print("Will continue but analysis functionality may not work properly.")
    
    def custom_bedrock_invoke(self, prompt, max_tokens=4096):
        """
        Custom method to invoke AWS Bedrock Claude models using requests directly.
        This is a fallback for when boto3 doesn't support the desired model ID.
        
        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum number of tokens in the response
            
        Returns:
            The analysis text from Claude
        """
        try:
            print("\nAttempting custom AWS Bedrock API call...")
            
            # Try to use requests library for direct API call
            import requests
            from requests_aws4auth import AWS4Auth
            
            # Get AWS credentials from boto3
            session = boto3.Session(region_name=self.region)
            credentials = session.get_credentials()
            
            # Create the auth handler
            auth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                'bedrock',
                session_token=credentials.token
            )
            
            # Prepare the request URL and headers
            url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{self.model_id}/invoke"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            # Prepare the request body
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Send the request
            print(f"Sending request to: {url}")
            response = requests.post(url, auth=auth, headers=headers, json=body)
            
            # Check the response
            if response.status_code == 200:
                result = response.json()
                if 'content' in result and len(result['content']) > 0:
                    return result['content'][0]['text']
                else:
                    return f"Unexpected response format: {result}"
            else:
                return f"API call failed with status code {response.status_code}: {response.text}"
                
        except ImportError:
            print("requests_aws4auth not installed. Try: pip install requests-aws4auth")
            return "Error: Required Python packages not installed for custom API call."
        except Exception as e:
            return f"Custom API call failed: {str(e)}"
        
    def fetch_logs_from_kubernetes(self, 
                                  app_name: str, 
                                  time_range: str, 
                                  message_contains: Optional[str] = None, 
                                  log_type: Optional[str] = None, 
                                  limit: int = 500) -> List[Dict]:
        """
        Fetch logs from Kubernetes.
        
        Args:
            app_name: Name of the application to fetch logs for
            time_range: Time range in format "1h", "2d", etc.
            message_contains: Filter logs containing this text
            log_type: Type of logs (error, info, warn)
            limit: Maximum number of logs to fetch
            
        Returns:
            List of log entries as dictionaries
        """
        print(f"Fetching logs for app: {app_name}, time range: {time_range}...")
        
        # Parse the time range
        time_value = int(time_range[:-1])
        time_unit = time_range[-1].lower()
        
        if time_unit == 'h':
            start_time = datetime.now() - timedelta(hours=time_value)
            since_param = f"{time_value}h"
        elif time_unit == 'd':
            start_time = datetime.now() - timedelta(days=time_value)
            since_param = f"{time_value}d"
        elif time_unit == 'm':
            start_time = datetime.now() - timedelta(minutes=time_value)
            since_param = f"{time_value}m"
        else:
            raise ValueError(f"Unsupported time unit: {time_unit}. Use 'm' for minutes, 'h' for hours, 'd' for days.")
        
        logs = []
        
        try:
            # Method 1: Try using the kubernetes client library
            try:
                # Load kube config (from ~/.kube/config by default)
                if self.disable_ssl_verify:
                    print("SSL verification disabled for Kubernetes API calls")
                    # Create a configuration with SSL verification disabled
                    configuration = client.Configuration()
                    configuration.verify_ssl = False
                    configuration.debug = False
                    
                    try:
                        config.load_kube_config(client_configuration=configuration)
                        client.Configuration.set_default(configuration)
                        core_api = client.CoreV1Api()
                    except Exception as e:
                        raise Exception(f"Failed to initialize Kubernetes client with SSL verification disabled: {str(e)}")
                else:
                    try:
                        config.load_kube_config()
                        core_api = client.CoreV1Api()
                    except Exception as e:
                        print(f"Error loading default kubeconfig: {str(e)}")
                        print("Trying with SSL verification disabled...")
                        
                        # Create a configuration with SSL verification disabled
                        configuration = client.Configuration()
                        configuration.verify_ssl = False
                        configuration.debug = False
                        
                        # Try to load kube config with the custom configuration
                        try:
                            config.load_kube_config(client_configuration=configuration)
                            client.Configuration.set_default(configuration)
                            core_api = client.CoreV1Api()
                        except Exception as load_err:
                            raise Exception(f"Failed to initialize Kubernetes client: {str(load_err)}")
                
                print(f"Using Kubernetes Python client to fetch logs...")
                
                # Get pods with the specified app label
                selector = f"app={app_name}"
                # Support regex matching for app name
                if '*' in app_name or '.' in app_name:
                    # Convert glob pattern to regex if necessary
                    if '*' in app_name and '.' not in app_name:
                        pattern = app_name.replace('*', '.*')
                        selector = f"app~={pattern}"
                
                # List pods with the selector
                pods = core_api.list_pod_for_all_namespaces(label_selector=selector)
                
                if not pods.items:
                    print(f"No pods found with selector: {selector}")
                    return logs
                    
                print(f"Found {len(pods.items)} pods matching {selector}")
                
                # Fetch logs for each pod
                for pod in pods.items[:min(20, len(pods.items))]:  # Limit to 20 pods to avoid too many requests
                    try:
                        namespace = pod.metadata.namespace
                        pod_name = pod.metadata.name
                        
                        # Apply log type filter if specified
                        container_logs = ""
                        try:
                            container_logs = core_api.read_namespaced_pod_log(
                                name=pod_name,
                                namespace=namespace,
                                since_seconds=int(time.time() - start_time.timestamp()),
                                timestamps=True,
                                container=pod.spec.containers[0].name  # Use first container by default
                            )
                        except ApiException as e:
                            print(f"Error fetching logs for pod {pod_name}: {e}")
                            continue
                            
                        # Process log lines
                        for line in container_logs.split('\n'):
                            if not line.strip():
                                continue
                                
                            # Extract timestamp if possible
                            timestamp = None
                            message = line
                            
                            # Common timestamp formats in logs
                            timestamp_match = re.search(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line)
                            if timestamp_match:
                                timestamp_str = timestamp_match.group(0)
                                try:
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('T', ' '))
                                    # Remove timestamp from the message
                                    message = line[len(timestamp_str):].strip()
                                except ValueError:
                                    # Keep the original message if timestamp parsing fails
                                    pass
                            
                            # Apply message contains filter if specified
                            if message_contains and message_contains.lower() not in message.lower():
                                continue
                                
                            # Apply log type filter if specified (look for common patterns)
                            if log_type:
                                log_level = None
                                if re.search(r'\b(ERROR|ERR|ERRO|FATAL)\b', message, re.IGNORECASE):
                                    log_level = "error"
                                elif re.search(r'\b(WARN|WARNING)\b', message, re.IGNORECASE):
                                    log_level = "warning"
                                elif re.search(r'\b(INFO)\b', message, re.IGNORECASE):
                                    log_level = "info"
                                elif re.search(r'\b(DEBUG)\b', message, re.IGNORECASE):
                                    log_level = "debug"
                                
                                if log_level != log_type:
                                    continue
                            
                            # Create log entry
                            log_entry = {
                                "timestamp": timestamp.isoformat() if timestamp else None,
                                "pod": pod_name,
                                "namespace": namespace,
                                "message": message,
                                "app": app_name
                            }
                            
                            logs.append(log_entry)
                            
                            # Stop if we've reached the limit
                            if len(logs) >= limit:
                                break
                        
                        # Stop if we've reached the limit
                        if len(logs) >= limit:
                            break
                            
                    except Exception as e:
                        print(f"Error processing logs for pod {pod.metadata.name}: {str(e)}")
                
            except (config.config_exception.ConfigException, ApiException) as e:
                print(f"Error using Kubernetes client library: {str(e)}")
                print("Falling back to kubectl command...")
                
                # Method 2: Fall back to kubectl command
                try:
                    # Build kubectl command
                    kubectl_cmd = ["kubectl", "logs", "-l", f"app={app_name}", f"--since={since_param}"]
                    
                    # Add namespace if specified
                    # kubectl_cmd.extend(["-n", namespace])  # Uncomment and add namespace parameter if needed
                    
                    # Add tail limit
                    kubectl_cmd.extend(["--tail", str(limit)])
                    
                    print(f"Executing: {' '.join(kubectl_cmd)}")
                    
                    # Execute kubectl command
                    result = subprocess.run(kubectl_cmd, capture_output=True, text=True, check=False)
                    
                    if result.returncode != 0:
                        print(f"kubectl command failed: {result.stderr}")
                        return logs
                        
                    # Process the logs
                    pod_logs = result.stdout.strip().split('\n')
                    
                    for line in pod_logs:
                        if not line.strip():
                            continue
                            
                        # Apply message contains filter if specified
                        if message_contains and message_contains.lower() not in line.lower():
                            continue
                            
                        # Apply log type filter if specified
                        if log_type:
                            log_level = None
                            if re.search(r'\b(ERROR|ERR|ERRO|FATAL)\b', line, re.IGNORECASE):
                                log_level = "error"
                            elif re.search(r'\b(WARN|WARNING)\b', line, re.IGNORECASE):
                                log_level = "warning"
                            elif re.search(r'\b(INFO)\b', line, re.IGNORECASE):
                                log_level = "info"
                            elif re.search(r'\b(DEBUG)\b', line, re.IGNORECASE):
                                log_level = "debug"
                            
                            if log_level != log_type:
                                continue
                        
                        # Create log entry
                        log_entry = {
                            "timestamp": None,  # Timestamp extraction would require more parsing
                            "pod": "unknown",  # Pod name is not included in the default output
                            "message": line,
                            "app": app_name
                        }
                        
                        logs.append(log_entry)
                except Exception as e:
                    print(f"Error executing kubectl command: {str(e)}")
        
        except Exception as e:
            print(f"Error fetching logs: {str(e)}")
            
        print(f"Fetched {len(logs)} log entries")
        return logs
    
    def fetch_logs_from_prometheus(self, 
                                  app_name: str, 
                                  time_range: str,
                                  prometheus_url: str = "http://prometheus:9090",
                                  message_contains: Optional[str] = None, 
                                  log_type: Optional[str] = None) -> List[Dict]:
        """
        Fetch metrics and logs from Prometheus.
        
        Args:
            app_name: Name of the application to fetch logs for
            time_range: Time range in format "1h", "2d", etc.
            prometheus_url: URL of the Prometheus instance
            message_contains: Filter logs containing this text
            log_type: Type of logs (error, info, warn)
            
        Returns:
            List of log entries as dictionaries
        """
        print(f"Fetching metrics from Prometheus for app: {app_name}, time range: {time_range}...")
        
        # Parse the time range
        time_value = int(time_range[:-1])
        time_unit = time_range[-1].lower()
        
        # Calculate start and end times
        end_time = int(time.time())
        
        if time_unit == 'h':
            duration = f"{time_value}h"
            start_time = end_time - time_value * 3600
            step = "1m"  # 1 minute resolution for hours
        elif time_unit == 'd':
            duration = f"{time_value * 24}h"
            start_time = end_time - time_value * 86400
            step = "1h"  # 1 hour resolution for days
        elif time_unit == 'm':
            duration = f"{time_value}m"
            start_time = end_time - time_value * 60
            step = "15s"  # 15 seconds resolution for minutes
        else:
            raise ValueError(f"Unsupported time unit: {time_unit}. Use 'm' for minutes, 'h' for hours, 'd' for days.")
        
        logs = []
        
        try:
            # We'll fetch different types of metrics based on the log_type
            queries = []
            
            # Base query format with appropriate labels for the app
            base_query = f'{{app="{app_name}"}}'
            
            # For error logs/metrics
            if not log_type or log_type == 'error':
                # Look for error rate and error counts
                queries.append({
                    'name': 'error_rate',
                    'query': f'sum(rate(http_requests_total{base_query}[5m])) by (status_code, path) > 0'
                })
                queries.append({
                    'name': 'error_count',
                    'query': f'sum(increase(http_server_errors_total{base_query}[{duration}])) by (path, status_code)'
                })
                queries.append({
                    'name': 'exception_count',
                    'query': f'sum(increase(application_exceptions_total{base_query}[{duration}])) by (exception_type)'
                })
            
            # For request/response metrics (info level)
            if not log_type or log_type == 'info':
                queries.append({
                    'name': 'request_rate',
                    'query': f'sum(rate(http_requests_total{base_query}[5m])) by (path)'
                })
                queries.append({
                    'name': 'response_time',
                    'query': f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{base_query}[5m])) by (path, le))'
                })
            
            # For system metrics (warning level)
            if not log_type or log_type == 'warning':
                queries.append({
                    'name': 'memory_usage',
                    'query': f'sum(container_memory_usage_bytes{{container="{app_name}"}}) by (pod)'
                })
                queries.append({
                    'name': 'cpu_usage',
                    'query': f'sum(rate(container_cpu_usage_seconds_total{{container="{app_name}"}}[5m])) by (pod)'
                })
            
            # Fetch each metric query
            for query_def in queries:
                query_name = query_def['name']
                query = query_def['query']
                
                # Construct the query parameters
                query_params = {
                    'query': query,
                    'start': start_time,
                    'end': end_time,
                    'step': step,
                }
                
                try:
                    print(f"Querying Prometheus: {query}")
                    
                    # Make the API call to Prometheus, with SSL verification disabled if needed
                    verify_ssl = not self.disable_ssl_verify
                    response = requests.get(
                        f"{prometheus_url}/api/v1/query_range", 
                        params=query_params,
                        verify=verify_ssl
                    )
                    
                    # Check if the request was successful
                    if response.status_code == 200:
                        data = response.json()
                        if data['status'] == 'success':
                            result = data['data']['result']
                            
                            # Process the results
                            for series in result:
                                metric = series['metric']
                                values = series['values']
                                
                                # Create a more readable metric name
                                metric_str = ", ".join([f"{k}={v}" for k, v in metric.items() if k != '__name__'])
                                
                                # Process each data point
                                for timestamp, value in values:
                                    # Convert timestamp to datetime
                                    dt = datetime.fromtimestamp(timestamp)
                                    
                                    # Skip if the value is None or NaN
                                    if value is None or value == 'NaN':
                                        continue
                                        
                                    # Format the message
                                    message = f"{query_name}: {metric_str} = {value}"
                                    
                                    # Apply message contains filter if specified
                                    if message_contains and message_contains.lower() not in message.lower():
                                        continue
                                    
                                    # Create the log entry
                                    log_entry = {
                                        "timestamp": dt.isoformat(),
                                        "metric": query_name,
                                        "labels": metric,
                                        "value": value,
                                        "message": message,
                                        "app": app_name
                                    }
                                    
                                    logs.append(log_entry)
                        else:
                            print(f"Prometheus query failed: {data['error']}")
                    else:
                        print(f"Prometheus request failed with status code: {response.status_code}")
                        print(response.text)
                        
                except requests.RequestException as e:
                    print(f"Error querying Prometheus: {str(e)}")
                
                # Sleep briefly to avoid overwhelming the Prometheus server
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error fetching metrics from Prometheus: {str(e)}")
            
        print(f"Fetched {len(logs)} metrics from Prometheus")
        return logs

    def analyze_logs(self, logs: List[Dict]) -> str:
        """
        Analyze logs using Claude 3.7 Sonnet to generate insights.
        
        Args:
            logs: List of log entries
            
        Returns:
            String containing the analysis results
        """
        if not logs:
            return "No logs found to analyze."
        
        # Prepare logs for Claude
        logs_json = json.dumps(logs[:200], indent=2)  # Limit to 200 logs to stay within context limits
        
        # Create the prompt for Claude
        prompt = f"""
        I need you to analyze these logs from our microservice architecture and provide insights:

        ```json
        {logs_json}
        ```

        For this analysis, please:
        1. Summarize the main errors and issues
        2. Identify which services are most affected
        3. Detect any patterns in when or how errors occur
        4. Suggest potential root causes
        5. Recommend specific places in the code or systems to investigate
        6. List any related trace IDs that might be helpful for further investigation
        
        Present your findings in a clear, structured format that would help an on-call engineer quickly understand and address the issues.
        """
        
        # Call Claude via AWS Bedrock
        try:
            # Set up the invoke arguments using the model_id that was identified during initialization
            print(f"Analyzing logs with model: {self.model_id}")
            invoke_args = {
                "modelId": self.model_id,  # Using the tested Claude model
                "contentType": "application/json",
                "accept": "application/json",
                "body": json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            }
            
            # Check if we should try to use inference profile
            if self.profile_arn:
                print(f"Using Bedrock inference profile: {self.profile_arn}")
                # Since boto3 doesn't support inference profiles directly, we can try using it
                # but be prepared for it to fail
                try:
                    # Add inference profile if available
                    invoke_args["inferenceProfile"] = self.profile_arn
                except Exception as e:
                    print(f"Warning: Could not use inference profile: {str(e)}")
                    print("Continuing without inference profile...")
            
            try:
                # Try the standard boto3 invoke method first
                print("Attempting standard boto3 invoke_model...")
                response = self.bedrock_client.invoke_model(**invoke_args)
                
                # Parse and return response
                try:
                    response_body = json.loads(response['body'].read().decode())
                    return response_body['content'][0]['text']
                except KeyError:
                    # Handle different response formats
                    if 'body' in response and hasattr(response['body'], 'read'):
                        content = response['body'].read().decode()
                        return f"Claude response in unexpected format. Raw response: {content}"
                    else:
                        return f"Error parsing Claude response: {response}"
                
            except Exception as invoke_error:
                # If standard method fails, try our custom method
                print(f"Standard boto3 invoke failed: {str(invoke_error)}")
                print("Attempting custom direct API call...")
                
                # Try the custom direct API method
                return self.custom_bedrock_invoke(prompt)
            
        except Exception as e:
            error_msg = f"Error analyzing logs with Claude: {str(e)}"
            print(error_msg)
            print("Check if your AWS credentials are properly configured and have Bedrock access.")
            
            # Print helpful debugging information
            print("\nDebugging information:")
            print(f"AWS_REGION: {os.environ.get('AWS_REGION', 'Not set')}")
            print(f"AWS_BEDROCK_INFERENCE_PROFILE: {os.environ.get('AWS_BEDROCK_INFERENCE_PROFILE', 'Not set')}")
            print(f"AWS_ACCESS_KEY_ID: {'Set' if os.environ.get('AWS_ACCESS_KEY_ID') else 'Not set'}")
            print(f"AWS_SECRET_ACCESS_KEY: {'Set' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'Not set'}")
            print(f"AWS_SESSION_TOKEN: {'Set' if os.environ.get('AWS_SESSION_TOKEN') else 'Not set'}")
            
            # Check the boto3 version
            print(f"boto3 version: {boto3.__version__}")
            
            # Try a direct invocation with minimal parameters as a final fallback
            try:
                print("\nAttempting fallback invocation with minimal parameters...")
                
                # Create a fresh client
                simple_client = boto3.client('bedrock-runtime', region_name=self.region)
                
                # Try different model IDs for fallback
                fallback_models = [
                    "anthropic.claude-3-sonnet-20240229-v1:0",
                    "anthropic.claude-3-haiku-20240307-v1:0",
                    "anthropic.claude-v2:1",
                    "anthropic.claude-v2",
                    "anthropic.claude-instant-v1"
                ]
                
                print(f"Trying fallback models...")
                response = None
                
                for model in fallback_models:
                    try:
                        print(f"Attempting with model: {model}")
                        response = simple_client.invoke_model(
                            modelId=model,
                            body=json.dumps({
                                "anthropic_version": "bedrock-2023-05-31",
                                "max_tokens": 1000,
                                "messages": [{"role": "user", "content": "Summarize these logs briefly: " + json.dumps(logs[:5])}]
                            }),
                            contentType="application/json",
                            accept="application/json",
                        )
                        if response:
                            print(f"✓ Successful with model: {model}")
                            # Save the working model for future use
                            self.model_id = model
                            break
                    except Exception as me:
                        print(f"✗ Failed with model {model}: {str(me)}")
                
                if not response:
                    raise Exception("All fallback models failed")
                
                response_body = json.loads(response['body'].read().decode())
                print("Fallback successful! You can use this approach for your analysis.")
                return "ERROR WITH FULL ANALYSIS, BUT FALLBACK TEST WORKED. Please update the code based on debugging information and try again."
                
            except Exception as fallback_error:
                print(f"Fallback attempt also failed: {str(fallback_error)}")
            
            return error_msg

    def process_and_summarize_logs(self, 
                                  app_name: str, 
                                  time_range: str, 
                                  message_contains: Optional[str] = None, 
                                  log_type: Optional[str] = None,
                                  source: str = "kubernetes"):
        """
        Main function to process logs and provide a summary.
        
        Args:
            app_name: Name of the application
            time_range: Time range for logs (e.g., "1h", "2d")
            message_contains: Filter for logs containing this text
            log_type: Type of logs to filter (error, info, warn)
            source: Source of logs ("kubernetes" or "prometheus")
        """
        # Fetch logs from specified source
        logs = []
        if source.lower() == "kubernetes":
            logs = self.fetch_logs_from_kubernetes(
                app_name, time_range, message_contains, log_type
            )
        elif source.lower() == "prometheus":
            logs = self.fetch_logs_from_prometheus(
                app_name, time_range, message_contains=message_contains, log_type=log_type
            )
        else:
            print(f"Unknown log source: {source}. Please use 'kubernetes' or 'prometheus'.")
            return
        
        # Check if we got any logs
        if not logs:
            print(f"No logs found for {app_name} in the last {time_range}.")
            return
        
        # Print basic log stats
        print(f"\nFound {len(logs)} log entries for {app_name} in the last {time_range}.")
        
        # Analyze logs using Claude
        print("\nAnalyzing logs with Claude 3.7 Sonnet...")
        analysis = self.analyze_logs(logs)
        
        # Print analysis
        print("\n===== LOG ANALYSIS =====\n")
        print(analysis)
        print("\n=======================\n")
        
        # Optionally save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = "log_analysis"
        
        # Create log_analysis directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"Created directory: {log_dir}")
            
        filename = os.path.join(log_dir, f"{app_name}_{timestamp}.md")
        
        with open(filename, "w") as f:
            f.write(f"Log Analysis for {app_name} ({time_range}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(analysis)
            
        print(f"Analysis saved to {filename}")
        print(f"All log analyses are stored in the '{log_dir}/' directory")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Explore and analyze logs from Kubernetes or Prometheus.")
    
    parser.add_argument("--app", "-a", required=True, help="Application name to search for")
    parser.add_argument("--time-range", "-t", default="1h", 
                        help="Time range to search (e.g., '10m', '1h', '2d')")
    parser.add_argument("--message", "-m", help="Filter logs containing this message")
    parser.add_argument("--log-type", "-l", choices=["error", "warning", "info", "debug"],
                        help="Filter by log level")
    parser.add_argument("--source", "-s", choices=["kubernetes", "prometheus"], default="kubernetes",
                        help="Source for logs (kubernetes or prometheus)")
    parser.add_argument("--region", "-r", default=None, 
                        help="AWS region for Bedrock (defaults to AWS_REGION env var or eu-west-1)")
    parser.add_argument("--profile", "-p", default=None, 
                        help="AWS Bedrock inference profile ARN (defaults to AWS_BEDROCK_INFERENCE_PROFILE env var)")
    parser.add_argument("--no-ssl-verify", action="store_true",
                        help="Disable SSL certificate verification for Kubernetes API calls")
    
    args = parser.parse_args()
    
    # Create explorer and process logs
    explorer = LogExplorer(
        region=args.region, 
        profile_arn=args.profile, 
        disable_ssl_verify=args.no_ssl_verify
    )
    
    explorer.process_and_summarize_logs(
        app_name=args.app,
        time_range=args.time_range,
        message_contains=args.message,
        log_type=args.log_type,
        source=args.source
    )


if __name__ == "__main__":
    main()