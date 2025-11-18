"""Bedrock Agent management commands."""

import typer
import time
from pathlib import Path
from chore.cli import bedrock_app
from chore.core.console import console, success, error, warning, info, header, section
from chore.core.config import get_config, ConfigParser
from chore.core.aws import get_aws_client


@bedrock_app.command("setup")
def setup_agent(
    agent_name: str = typer.Option(
        "estimation-tool-agent",
        "--name",
        help="Name for the Bedrock Agent",
    ),
    foundation_model: str = typer.Option(
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "--model",
        help="Foundation model to use",
    ),
):
    """
    Create a new Bedrock Agent.
    
    Replaces: setup-bedrock-agent.sh
    """
    header("Creating AWS Bedrock Agent for Estimation Tool")
    
    # Navigate from: .../infrastructure/chore/src/chore/commands/bedrock.py
    # To: .../Estimation (project root)
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    instruction_file = project_root / "personas" / "combined_agent_instruction.txt"
    
    if not instruction_file.exists():
        error(f"Instruction file not found: {instruction_file}")
        raise typer.Exit(1)
    
    instruction = instruction_file.read_text()
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    account_id = aws_client.get_account_id()
    
    info("Configuration:")
    console.print(f"  Region: {config.region}")
    console.print(f"  Agent Name: {agent_name}")
    console.print(f"  Foundation Model: {foundation_model}")
    console.print()
    
    section("Step 1: Creating IAM execution role")
    
    role_name = "AmazonBedrockExecutionRoleForAgents_EstimationTool"
    role_path = "/service-role/"
    role_arn = f"arn:aws:iam::{account_id}:role{role_path}{role_name}"
    
    try:
        aws_client.iam.get_role(RoleName=role_name)
        info(f"Role already exists: {role_name}")
    except Exception:
        info(f"Creating role: {role_name}")
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {"aws:SourceAccount": account_id},
                        "ArnLike": {
                            "aws:SourceArn": f"arn:aws:bedrock:{config.region}:{account_id}:agent/*"
                        },
                    },
                }
            ],
        }
        
        import json
        
        try:
            aws_client.iam.create_role(
                RoleName=role_name,
                Path=role_path,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role for Bedrock Agent - Estimation Tool",
            )
            
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["bedrock:InvokeModel"],
                        "Resource": [
                            f"arn:aws:bedrock:{config.region}::foundation-model/{foundation_model}"
                        ],
                    }
                ],
            }
            
            aws_client.iam.put_role_policy(
                RoleName=role_name,
                PolicyName="BedrockModelInvokePolicy",
                PolicyDocument=json.dumps(policy_document),
            )
            
            success("Role created successfully")
            info("Waiting 10 seconds for role to propagate...")
            time.sleep(10)
        except Exception as e:
            error(f"Failed to create role: {e}")
            raise typer.Exit(1)
    
    console.print()
    
    section("Step 2: Creating Bedrock Agent")
    
    try:
        response = aws_client.bedrock.create_agent(
            agentName=agent_name,
            foundationModel=foundation_model,
            instruction=instruction,
            agentResourceRoleArn=role_arn,
            description="Specialized agent for software estimation with BA and Engineering Manager personas.",
            idleSessionTTLInSeconds=600,
        )
        
        agent = response["agent"]
        agent_id = agent["agentId"]
        agent_status = agent["agentStatus"]
        
        success("Agent created successfully!")
        info(f"Agent ID: {agent_id}")
        info(f"Status: {agent_status}")
        console.print()
        
    except Exception as e:
        error(f"Failed to create agent: {e}")
        raise typer.Exit(1)
    
    section("Step 3: Preparing agent")
    
    info("Preparing agent (this may take 30-60 seconds)...")
    
    if aws_client.prepare_agent(agent_id):
        if aws_client.wait_for_agent_prepared(agent_id, timeout=120):
            success("Agent prepared successfully!")
        else:
            warning("Agent preparation timed out, but agent was created")
    
    console.print()
    
    section("Step 4: Creating agent alias")
    
    try:
        alias_response = aws_client.bedrock.create_agent_alias(
            agentId=agent_id,
            agentAliasName="production",
            description="Production alias for estimation tool agent",
        )
        
        alias_id = alias_response["agentAlias"]["agentAliasId"]
        success(f"Agent alias created: {alias_id}")
        console.print()
        
    except Exception as e:
        error(f"Failed to create alias: {e}")
        raise typer.Exit(1)
    
    section("Step 5: Updating configuration")
    
    info("Agent IDs need to be added to samconfig.toml BedrockAgentId and BedrockAgentAliasId parameters")
    console.print()
    console.print(f"[bold]Agent ID:[/bold] {agent_id}")
    console.print(f"[bold]Alias ID:[/bold] {alias_id}")
    console.print()
    info("Update these values in infrastructure/samconfig.toml parameter_overrides")
    console.print()
    
    header("Bedrock Agent Setup Complete!")


@bedrock_app.command("update")
def update_agent(
    agent_id: str = typer.Option(
        None,
        "--agent-id",
        help="Agent ID (reads from config if not provided)",
    ),
):
    """
    Update Bedrock Agent instructions.
    
    Replaces: update-bedrock-agent.sh
    """
    header("Update Bedrock Agent Instructions")
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    if not agent_id:
        agent_id = config.parameter_overrides.get("BedrockAgentId")
    
    if not agent_id:
        error("BedrockAgentId not found in configuration")
        error("Provide --agent-id or run 'chore bedrock setup' first")
        raise typer.Exit(1)
    
    # Navigate from: .../infrastructure/chore/src/chore/commands/bedrock.py
    # To: .../Estimation (project root)
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    instruction_file = project_root / "personas" / "combined_agent_instruction.txt"
    
    if not instruction_file.exists():
        error(f"Instruction file not found: {instruction_file}")
        raise typer.Exit(1)
    
    instruction = instruction_file.read_text()
    
    info(f"Agent ID: {agent_id}")
    info(f"Region: {config.region}")
    console.print()
    
    section("Step 1: Getting current agent configuration")
    
    agent = aws_client.get_agent(agent_id)
    if not agent:
        error("Agent not found")
        raise typer.Exit(1)
    
    info(f"Agent Name: {agent.get('agentName')}")
    info(f"Current Status: {agent.get('agentStatus')}")
    console.print()
    
    section("Step 2: Updating agent instructions")
    
    try:
        aws_client.bedrock.update_agent(
            agentId=agent_id,
            agentName=agent.get("agentName"),
            foundationModel=agent.get("foundationModel"),
            instruction=instruction,
            agentResourceRoleArn=agent.get("agentResourceRoleArn"),
        )
        success("Agent instructions updated")
        console.print()
    except Exception as e:
        error(f"Failed to update agent: {e}")
        raise typer.Exit(1)
    
    section("Step 3: Re-preparing agent")
    
    info("Preparing agent with new instructions...")
    
    if aws_client.prepare_agent(agent_id):
        if aws_client.wait_for_agent_prepared(agent_id):
            success("Agent prepared successfully!")
        else:
            warning("Agent preparation timed out")
    else:
        error("Failed to prepare agent")
        raise typer.Exit(1)
    
    console.print()
    header("Agent Update Complete!")


@bedrock_app.command("permissions")
def setup_permissions():
    """
    Grant IAM permissions for Bedrock Agent testing.
    
    Replaces: setup-bedrock-agent-permissions.sh
    """
    header("Setup Bedrock Agent Permissions")
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    info("This command verifies that your IAM user/role has the necessary permissions")
    info("to test and invoke Bedrock Agents.")
    console.print()
    
    section("Checking current identity")
    
    try:
        identity = aws_client.sts.get_caller_identity()
        user_arn = identity["Arn"]
        account_id = identity["Account"]
        
        info(f"Current identity: {user_arn}")
        info(f"Account ID: {account_id}")
        console.print()
    except Exception as e:
        error(f"Failed to get identity: {e}")
        raise typer.Exit(1)
    
    section("Required permissions")
    
    console.print("Your IAM user/role needs the following permissions:")
    console.print("  - bedrock:InvokeAgent")
    console.print("  - bedrock:GetAgent")
    console.print("  - bedrock:ListAgents")
    console.print("  - bedrock:PrepareAgent")
    console.print()
    
    info("You can attach the 'AmazonBedrockFullAccess' managed policy")
    info("or create a custom policy with these specific permissions.")
    console.print()
    
    warning("Note: This command does not automatically modify IAM policies.")
    warning("Please work with your AWS administrator to ensure proper permissions.")


@bedrock_app.command("test")
def test_agent(
    agent_id: str = typer.Option(
        None,
        "--agent-id",
        help="Agent ID (reads from config if not provided)",
    ),
    alias_id: str = typer.Option(
        None,
        "--alias-id",
        help="Agent alias ID (reads from config if not provided)",
    ),
    prompt: str = typer.Option(
        "Hello, can you help me estimate a project?",
        "--prompt",
        help="Test prompt to send to the agent",
    ),
):
    """
    Test Bedrock Agent invocation.
    
    Replaces: test_bedrock_agent.py
    """
    header("Test Bedrock Agent Invocation")
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    if not agent_id:
        agent_id = config.parameter_overrides.get("BedrockAgentId")
    if not alias_id:
        alias_id = config.parameter_overrides.get("BedrockAgentAliasId")
    
    if not agent_id or not alias_id:
        error("Agent ID and Alias ID must be provided or configured")
        error("Run 'chore bedrock setup' first or provide --agent-id and --alias-id")
        raise typer.Exit(1)
    
    info(f"Agent ID: {agent_id}")
    info(f"Alias ID: {alias_id}")
    info(f"Region: {config.region}")
    console.print()
    
    section("Invoking agent")
    
    info(f"Prompt: {prompt}")
    console.print()
    
    try:
        import boto3
        bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=config.region)
        
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=f"test-session-{int(time.time())}",
            inputText=prompt,
        )
        
        info("Response:")
        console.print()
        
        for event in response["completion"]:
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    text = chunk["bytes"].decode("utf-8")
                    console.print(text, end="")
        
        console.print()
        console.print()
        success("Agent invocation successful!")
        
    except Exception as e:
        error(f"Failed to invoke agent: {e}")
        raise typer.Exit(1)
    
    console.print()
    header("Test Complete!")


@bedrock_app.command("setup-mcp")
def setup_mcp():
    """
    Configure MCP (Model Context Protocol) action groups.
    
    Replaces: setup-mcp-action-groups.sh
    
    Note: This is a placeholder for future implementation.
    MCP action groups require additional Lambda functions and API schemas.
    """
    header("Setup MCP Action Groups")
    
    warning("MCP action group setup is not yet fully implemented in the chore tool.")
    warning("Please use the shell script for now:")
    console.print()
    console.print("  cd infrastructure")
    console.print("  ./setup-mcp-action-groups.sh")
    console.print()
    info("This feature will be completed in a future update.")

