#!/bin/bash

set -e

echo "========================================="
echo "Updating AWS Bedrock Agent Instructions"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$SCRIPT_DIR/bedrock-agent-config.sh" ]; then
    source "$SCRIPT_DIR/bedrock-agent-config.sh"
    echo "Loaded configuration from bedrock-agent-config.sh"
else
    echo "WARNING: bedrock-agent-config.sh not found"
    echo "Please set environment variables or provide them as arguments"
fi

AGENT_ID="${BEDROCK_AGENT_ID:-$1}"
AWS_REGION="${AWS_REGION:-${2:-us-west-2}}"

if [ -z "$AGENT_ID" ]; then
    echo "ERROR: AGENT_ID not provided"
    echo "Usage: $0 <agent-id> [region]"
    echo "Or set BEDROCK_AGENT_ID environment variable"
    exit 1
fi

INSTRUCTION_FILE="$PROJECT_ROOT/personas/combined_agent_instruction.txt"

if [ ! -f "$INSTRUCTION_FILE" ]; then
    echo "ERROR: Instruction file not found: $INSTRUCTION_FILE"
    exit 1
fi

echo "Configuration:"
echo "  Agent ID: $AGENT_ID"
echo "  Region: $AWS_REGION"
echo "  Instruction File: $INSTRUCTION_FILE"
echo ""

AGENT_INSTRUCTION=$(cat "$INSTRUCTION_FILE")

echo "Step 1: Getting current agent details..."
CURRENT_AGENT=$(aws bedrock-agent get-agent \
    --agent-id "$AGENT_ID" \
    --region "$AWS_REGION" \
    --output json)

AGENT_NAME=$(echo "$CURRENT_AGENT" | jq -r '.agent.agentName')
FOUNDATION_MODEL=$(echo "$CURRENT_AGENT" | jq -r '.agent.foundationModel')
AGENT_ROLE=$(echo "$CURRENT_AGENT" | jq -r '.agent.agentResourceRoleArn')

echo "  Agent Name: $AGENT_NAME"
echo "  Foundation Model: $FOUNDATION_MODEL"
echo "  Role: $AGENT_ROLE"
echo ""

echo "Step 2: Updating agent with new instructions..."
aws bedrock-agent update-agent \
    --agent-id "$AGENT_ID" \
    --agent-name "$AGENT_NAME" \
    --foundation-model "$FOUNDATION_MODEL" \
    --instruction "$AGENT_INSTRUCTION" \
    --agent-resource-role-arn "$AGENT_ROLE" \
    --description "Specialized agent for software estimation with BA and Engineering Manager personas. Integrates with Atlassian and Glean via MCP." \
    --idle-session-ttl-in-seconds 600 \
    --region "$AWS_REGION" \
    --output json > /dev/null

echo "Agent updated successfully!"
echo ""

echo "Step 3: Preparing updated agent..."
aws bedrock-agent prepare-agent \
    --agent-id "$AGENT_ID" \
    --region "$AWS_REGION" \
    --output json > /dev/null

echo "Waiting for agent to be prepared..."
sleep 5

PREPARED=false
for i in {1..12}; do
    STATUS=$(aws bedrock-agent get-agent \
        --agent-id "$AGENT_ID" \
        --region "$AWS_REGION" \
        --query 'agent.agentStatus' \
        --output text)
    
    echo "  Status check $i/12: $STATUS"
    
    if [ "$STATUS" = "PREPARED" ]; then
        PREPARED=true
        break
    fi
    
    sleep 5
done

if [ "$PREPARED" = "false" ]; then
    echo "WARNING: Agent preparation is taking longer than expected"
    echo "Check status with: aws bedrock-agent get-agent --agent-id $AGENT_ID --region $AWS_REGION"
else
    echo "Agent prepared successfully!"
fi

echo ""
echo "========================================="
echo "Agent Update Complete!"
echo "========================================="
echo ""
echo "The agent instructions have been updated and the agent is ready to use."
echo ""
echo "To test the agent, you can use:"
echo "  aws bedrock-agent-runtime invoke-agent \\"
echo "    --agent-id $AGENT_ID \\"
echo "    --agent-alias-id \$AGENT_ALIAS_ID \\"
echo "    --session-id \$(uuidgen) \\"
echo "    --input-text 'Test query' \\"
echo "    --region $AWS_REGION"

