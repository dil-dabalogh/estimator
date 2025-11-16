#!/usr/bin/env python3
"""
Test script for AWS Bedrock Agent invocation.
Uses boto3 to invoke the agent and display the response.
"""

import os
import sys
import json
import uuid
import base64
import boto3
from pathlib import Path

# Load configuration from bedrock-agent-config.sh if available
config_file = Path(__file__).parent / "bedrock-agent-config.sh"
if config_file.exists():
    print(f"Loading configuration from {config_file}")
    with open(config_file) as f:
        for line in f:
            if line.startswith("export "):
                line = line.replace("export ", "").strip()
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key] = val

# Get configuration
AGENT_ID = os.environ.get("BEDROCK_AGENT_ID")
AGENT_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID")
REGION = os.environ.get("AWS_REGION", "us-west-2")

if not AGENT_ID or not AGENT_ALIAS_ID:
    print("ERROR: BEDROCK_AGENT_ID and BEDROCK_AGENT_ALIAS_ID must be set")
    print("\nUsage:")
    print("  1. Run: source bedrock-agent-config.sh")
    print("  2. Run: python3 test_bedrock_agent.py")
    print("\nOr set environment variables manually:")
    print("  export BEDROCK_AGENT_ID=your-agent-id")
    print("  export BEDROCK_AGENT_ALIAS_ID=your-agent-alias-id")
    sys.exit(1)

print(f"Agent ID: {AGENT_ID}")
print(f"Agent Alias ID: {AGENT_ALIAS_ID}")
print(f"Region: {REGION}")
print()

# Test input
if len(sys.argv) > 1:
    test_input = " ".join(sys.argv[1:])
else:
    test_input = """
Please provide a brief BA analysis for the following requirement:

We need to add a new feature to display user activity logs in the dashboard.
Users should be able to filter by date range, user, and activity type.
The logs should be exportable to CSV.
    """.strip()

print("=" * 80)
print("Test Input:")
print("=" * 80)
print(test_input)
print()

# Create Bedrock Agent Runtime client
print("Creating Bedrock Agent Runtime client...")
try:
    client = boto3.client("bedrock-agent-runtime", region_name=REGION)
    print("Client created successfully")
except Exception as e:
    print(f"ERROR: Failed to create client: {e}")
    print("\nMake sure you have:")
    print("  1. boto3 installed: pip install boto3")
    print("  2. AWS credentials configured")
    print("  3. Appropriate IAM permissions")
    sys.exit(1)

# Invoke agent
print("\nInvoking agent...")
session_id = uuid.uuid4().hex
print(f"Session ID: {session_id}")

try:
    response = client.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=test_input,
        enableTrace=False
    )
    
    print("Agent invoked successfully")
    print()
    
except Exception as e:
    print(f"ERROR: Failed to invoke agent: {e}")
    print("\nCommon issues:")
    print("  1. Agent not found - check BEDROCK_AGENT_ID")
    print("  2. Alias not found - check BEDROCK_AGENT_ALIAS_ID")
    print("  3. Agent not prepared - run: aws bedrock-agent prepare-agent --agent-id <id>")
    print("  4. Permission denied - check IAM permissions")
    sys.exit(1)

# Parse response
print("=" * 80)
print("Agent Response:")
print("=" * 80)

parts = []
completion = response.get("completion")

if completion:
    # The response is an event stream
    for event in completion:
        if "chunk" in event:
            chunk = event["chunk"]
            
            # Handle bytes (raw bytes, not base64)
            if "bytes" in chunk:
                try:
                    # The bytes are already decoded by boto3, just need to convert to string
                    raw_bytes = chunk["bytes"]
                    
                    # If it's already a string, use it directly
                    if isinstance(raw_bytes, str):
                        text = raw_bytes
                    # If it's bytes, decode to UTF-8
                    elif isinstance(raw_bytes, bytes):
                        text = raw_bytes.decode("utf-8", errors="replace")
                    else:
                        # Fallback: convert to string
                        text = str(raw_bytes)
                    
                    parts.append(text)
                    print(text, end="", flush=True)
                except Exception as e:
                    print(f"\n[Error decoding chunk: {e}]", file=sys.stderr)
                    # Debug: show the raw chunk
                    print(f"[Debug: chunk type={type(chunk.get('bytes'))}, chunk={chunk}]", file=sys.stderr)
            
            # Handle text directly
            elif "text" in chunk:
                text = chunk["text"]
                parts.append(text)
                print(text, end="", flush=True)

print()
print()

full_response = "".join(parts)

if not full_response:
    print("WARNING: Agent returned empty response")
    print("\nTroubleshooting:")
    print("  1. Check agent status with: aws bedrock-agent get-agent --agent-id <id>")
    print("  2. Review CloudWatch logs for the agent")
    print("  3. Enable trace mode for debugging")
else:
    print("=" * 80)
    print(f"Response length: {len(full_response)} characters")
    print("=" * 80)

# Save response to file
output_file = Path("/tmp/bedrock_agent_response.txt")
with open(output_file, "w") as f:
    f.write(full_response)
print(f"\nResponse saved to: {output_file}")

print("\nTest completed successfully!")

