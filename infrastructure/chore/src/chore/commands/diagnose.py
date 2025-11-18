"""Diagnostic commands for API, authorizer, and Bedrock."""

import typer
import requests
from datetime import datetime, timedelta
from rich.table import Table
from rich.syntax import Syntax
from chore.cli import diagnose_app
from chore.core.console import console, success, error, warning, info, header, section
from chore.core.config import get_config
from chore.core.aws import get_aws_client


@diagnose_app.command("api")
def diagnose_api():
    """
    Diagnose API health and configuration.
    
    Replaces: diagnose-api-health.sh
    """
    header("API Health Endpoint Diagnostics")
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    stack_name = config.stack_name
    
    section("Step 1: Checking if stack exists")
    stack = aws_client.get_stack(stack_name)
    
    if not stack:
        error(f"Stack '{stack_name}' not found")
        info("Available stacks:")
        try:
            stacks = aws_client.cfn.list_stacks(
                StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE"]
            )
            for s in stacks.get("StackSummaries", []):
                console.print(f"  - {s['StackName']}")
        except Exception:
            pass
        raise typer.Exit(1)
    
    status = stack["StackStatus"]
    success(f"Stack status: {status}")
    console.print()
    
    section("Step 2: Getting API URL")
    api_url = aws_client.get_stack_output(stack_name, "EstimationApiUrl")
    
    if not api_url:
        error("Could not get API URL from stack outputs")
        raise typer.Exit(1)
    
    info(f"API URL: {api_url}")
    console.print()
    
    section("Step 3: Getting Lambda function name")
    try:
        response = aws_client.cfn.describe_stack_resources(
            StackName=stack_name,
            LogicalResourceId="EstimationFunction",
        )
        function_name = response["StackResources"][0]["PhysicalResourceId"]
        success(f"Lambda function: {function_name}")
    except Exception:
        error("Lambda function not found in stack")
        raise typer.Exit(1)
    
    console.print()
    
    section("Step 4: Checking Lambda function configuration")
    lambda_config = aws_client.get_lambda_config(function_name)
    
    if lambda_config:
        table = Table(show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Runtime", lambda_config.get("Runtime", "N/A"))
        table.add_row("Handler", lambda_config.get("Handler", "N/A"))
        table.add_row("Memory Size", str(lambda_config.get("MemorySize", "N/A")))
        table.add_row("Timeout", str(lambda_config.get("Timeout", "N/A")))
        table.add_row("Last Modified", lambda_config.get("LastModified", "N/A"))
        
        console.print(table)
    
    console.print()
    
    section("Step 5: Checking Lambda environment variables")
    if lambda_config and "Environment" in lambda_config:
        env_vars = lambda_config["Environment"].get("Variables", {})
        table = Table(show_header=True)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in env_vars.items():
            if any(sensitive in key.upper() for sensitive in ["TOKEN", "KEY", "SECRET", "PASSWORD"]):
                table.add_row(key, "***REDACTED***")
            else:
                table.add_row(key, value)
        
        console.print(table)
    
    console.print()
    
    section("Step 6: Getting recent Lambda error logs")
    info("Checking for errors in the last 10 minutes...")
    
    error_logs = aws_client.get_lambda_logs(
        function_name=function_name,
        filter_pattern="ERROR",
        limit=20,
        minutes=10,
    )
    
    if error_logs:
        for log in error_logs[:20]:
            timestamp = datetime.fromtimestamp(log["timestamp"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"[red]{timestamp}[/red] {log['message']}")
    else:
        success("No error logs found")
    
    console.print()
    
    section("Step 7: Getting recent Lambda invocation logs")
    info("Recent logs (last 10 minutes)...")
    
    all_logs = aws_client.get_lambda_logs(
        function_name=function_name,
        limit=50,
        minutes=10,
    )
    
    if all_logs:
        for log in all_logs[:50]:
            message = log["message"].rstrip()
            if "ERROR" in message:
                console.print(f"[red]{message}[/red]")
            elif "WARNING" in message or "WARN" in message:
                console.print(f"[yellow]{message}[/yellow]")
            else:
                console.print(message)
    else:
        info("No recent logs found")
    
    console.print()
    
    section("Step 8: Testing health endpoint")
    info(f"Testing: {api_url}/health")
    console.print()
    
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        status_code = response.status_code
        
        if status_code == 200:
            success(f"Health endpoint is working! (HTTP {status_code})")
            console.print(f"Response: {response.text}")
        elif status_code == 403:
            error("403 Forbidden - IP address is not whitelisted")
            console.print()
            try:
                current_ip_response = requests.get("https://checkip.amazonaws.com", timeout=5)
                current_ip = current_ip_response.text.strip()
                info(f"Your current IP: {current_ip}")
                console.print()
                info("To allow your IP:")
                console.print("  chore ip add-current")
            except Exception:
                pass
        elif status_code == 500:
            error("500 Internal Server Error - Lambda execution error")
            console.print()
            info("Check the logs above for details. Common issues:")
            console.print("  - Missing required environment variables")
            console.print("  - Python import errors")
            console.print("  - Missing dependencies in Lambda layer")
        else:
            warning(f"Unexpected HTTP status: {status_code}")
            console.print(f"Response: {response.text}")
    
    except requests.exceptions.RequestException as e:
        error(f"Request failed: {e}")
    
    console.print()
    header("Diagnostic Complete")


@diagnose_app.command("authorizer")
def diagnose_authorizer():
    """
    Diagnose Lambda authorizer setup.
    
    Replaces: diagnose-authorizer.sh
    """
    header("Lambda Authorizer Diagnostics")
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    stack_name = config.stack_name
    
    section("Step 1: Checking if authorizer Lambda exists")
    
    try:
        response = aws_client.cfn.describe_stack_resources(
            StackName=stack_name,
            LogicalResourceId="IPAuthorizerFunction",
        )
        auth_function = response["StackResources"][0]["PhysicalResourceId"]
        success(f"Authorizer Lambda found: {auth_function}")
    except Exception:
        error("Authorizer Lambda NOT found in stack")
        error("The IPAuthorizerFunction resource doesn't exist.")
        error("Did the deployment succeed? Check CloudFormation console.")
        raise typer.Exit(1)
    
    console.print()
    
    section("Step 2: Checking authorizer environment variables")
    lambda_config = aws_client.get_lambda_config(auth_function)
    
    if lambda_config and "Environment" in lambda_config:
        env_vars = lambda_config["Environment"].get("Variables", {})
        allowed_ips = env_vars.get("ALLOWED_IP_RANGES", "")
        
        console.print(f"ALLOWED_IP_RANGES = '{allowed_ips}'")
        console.print()
        
        if not allowed_ips or allowed_ips == "None":
            error("ALLOWED_IP_RANGES environment variable is NOT SET")
            console.print()
            info("Showing all environment variables:")
            
            table = Table(show_header=True)
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="white")
            
            for key, value in env_vars.items():
                table.add_row(key, value)
            
            console.print(table)
        else:
            success("ALLOWED_IP_RANGES is configured")
    
    console.print()
    
    section("Step 3: Checking API Gateway authorizer configuration")
    
    api_url = aws_client.get_stack_output(stack_name, "EstimationApiUrl")
    if not api_url:
        error("Could not get API URL")
        raise typer.Exit(1)
    
    api_id = api_url.split("/")[2].split(".")[0]
    info(f"API ID: {api_id}")
    console.print()
    
    try:
        apigw = aws_client.cfn._client_config.__dict__
        apigw_client = aws_client.cfn._client_config._user_provided_options.get("region_name", config.region)
        import boto3
        apigw_v2 = boto3.client("apigatewayv2", region_name=config.region)
        
        authorizers = apigw_v2.get_authorizers(ApiId=api_id)
        
        if authorizers.get("Items"):
            info("Authorizers configured:")
            table = Table(show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="white")
            table.add_column("URI", style="white")
            
            for auth in authorizers["Items"]:
                table.add_row(
                    auth.get("Name", "N/A"),
                    auth.get("AuthorizerType", "N/A"),
                    auth.get("AuthorizerUri", "N/A"),
                )
            
            console.print(table)
        else:
            warning("No authorizers configured")
    except Exception as e:
        warning(f"Could not check API Gateway authorizers: {e}")
    
    console.print()
    
    section("Step 4: Checking routes and their authorizers")
    
    try:
        routes = apigw_v2.get_routes(ApiId=api_id)
        
        if routes.get("Items"):
            table = Table(show_header=True)
            table.add_column("Route Key", style="cyan")
            table.add_column("Authorizer ID", style="white")
            table.add_column("Authorization Type", style="white")
            
            for route in routes["Items"]:
                table.add_row(
                    route.get("RouteKey", "N/A"),
                    route.get("AuthorizerId", "None"),
                    route.get("AuthorizationType", "NONE"),
                )
            
            console.print(table)
    except Exception as e:
        warning(f"Could not check routes: {e}")
    
    console.print()
    
    section("Step 5: Recent authorizer invocations")
    info("Checking logs from last 10 minutes...")
    
    logs = aws_client.get_lambda_logs(
        function_name=auth_function,
        limit=50,
        minutes=10,
    )
    
    if logs:
        for log in logs:
            console.print(log["message"].rstrip())
    else:
        info("No recent logs found")
    
    console.print()
    
    section("Step 6: Testing API endpoint")
    info(f"API URL: {api_url}")
    info("Making test request...")
    
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        console.print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            success("API is accessible")
        elif response.status_code == 403:
            error("Forbidden - Authorizer is blocking the request")
            info("Your IP may not be whitelisted")
        else:
            warning(f"Unexpected status: {response.status_code}")
    except Exception as e:
        error(f"Request failed: {e}")
    
    console.print()
    header("Diagnostic Complete")


@diagnose_app.command("bedrock")
def diagnose_bedrock():
    """
    Diagnose and fix Bedrock Agent issues.
    
    Replaces: diagnose-bedrock-agent.sh
    """
    header("Bedrock Agent Diagnostics and Fix")
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    bedrock_agent_id = config.parameter_overrides.get("BedrockAgentId")
    
    if not bedrock_agent_id:
        error("BedrockAgentId not found in configuration")
        error("Run 'chore bedrock setup' to create a Bedrock Agent first")
        raise typer.Exit(1)
    
    info(f"Agent ID: {bedrock_agent_id}")
    info(f"Region: {config.region}")
    console.print()
    
    section("Step 1: Check Agent Status")
    
    agent = aws_client.get_agent(bedrock_agent_id)
    
    if not agent:
        error("Agent not found")
        raise typer.Exit(1)
    
    agent_name = agent.get("agentName")
    agent_status = agent.get("agentStatus")
    agent_role_arn = agent.get("agentResourceRoleArn")
    foundation_model = agent.get("foundationModel")
    
    info(f"Agent Name: {agent_name}")
    info(f"Agent Status: {agent_status}")
    info(f"Foundation Model: {foundation_model}")
    info(f"Execution Role: {agent_role_arn}")
    console.print()
    
    if agent_status != "PREPARED":
        warning(f"Agent is NOT in PREPARED state! Current status: {agent_status}")
        console.print()
        info("Preparing agent now...")
        
        if aws_client.prepare_agent(bedrock_agent_id):
            if aws_client.wait_for_agent_prepared(bedrock_agent_id):
                success("Agent is now PREPARED!")
            else:
                error("Agent preparation timed out or failed")
                raise typer.Exit(1)
        else:
            raise typer.Exit(1)
    else:
        success("Agent is PREPARED")
    
    console.print()
    
    section("Step 2: Check Agent Execution Role")
    
    role_name = agent_role_arn.split("/")[-1]
    info(f"Role Name: {role_name}")
    
    try:
        role = aws_client.iam.get_role(RoleName=role_name)
        success("Role exists")
        
        console.print()
        info("Checking attached policies...")
        
        attached_policies = aws_client.iam.list_attached_role_policies(RoleName=role_name)
        
        if attached_policies.get("AttachedPolicies"):
            table = Table(show_header=True)
            table.add_column("Policy Name", style="cyan")
            table.add_column("Policy ARN", style="white")
            
            for policy in attached_policies["AttachedPolicies"]:
                table.add_row(policy["PolicyName"], policy["PolicyArn"])
            
            console.print(table)
        else:
            warning("No attached policies found")
        
        console.print()
        info("Checking inline policies...")
        
        inline_policies = aws_client.iam.list_role_policies(RoleName=role_name)
        
        if inline_policies.get("PolicyNames"):
            for policy_name in inline_policies["PolicyNames"]:
                success(f"Inline policy: {policy_name}")
        else:
            info("No inline policies")
    
    except Exception as e:
        error(f"Could not check role: {e}")
    
    console.print()
    header("Diagnostic Complete")

