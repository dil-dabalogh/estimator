#!/bin/bash

set -e

echo "========================================="
echo "Grant IAM Permissions for Bedrock Agent Testing"
echo "========================================="
echo ""

# Check who you are
echo "Current AWS Identity:"
aws sts get-caller-identity

USER_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

echo ""
echo "User/Role ARN: $USER_ARN"
echo "Account ID: $ACCOUNT_ID"
echo ""

# Load agent configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/bedrock-agent-config.sh" ]; then
    source "$SCRIPT_DIR/bedrock-agent-config.sh"
else
    echo "ERROR: bedrock-agent-config.sh not found"
    exit 1
fi

AGENT_ID="${BEDROCK_AGENT_ID}"
AWS_REGION="${AWS_REGION:-us-west-2}"

echo "Agent ID: $AGENT_ID"
echo "Region: $AWS_REGION"
echo ""

# Check if using IAM user or role
if [[ $USER_ARN == *":user/"* ]]; then
    IAM_TYPE="user"
    IAM_NAME=$(echo "$USER_ARN" | cut -d'/' -f2)
    echo "Detected IAM User: $IAM_NAME"
elif [[ $USER_ARN == *":assumed-role/"* ]]; then
    IAM_TYPE="role"
    IAM_NAME=$(echo "$USER_ARN" | cut -d'/' -f2)
    echo "Detected IAM Role: $IAM_NAME"
else
    echo "ERROR: Could not determine IAM type"
    exit 1
fi

echo ""
echo "Creating IAM policy for Bedrock Agent access..."

POLICY_NAME="BedrockAgentInvokePolicy"

POLICY_DOCUMENT=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:agent/${AGENT_ID}",
        "arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:agent-alias/${AGENT_ID}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agent:GetAgent",
        "bedrock-agent:ListAgents"
      ],
      "Resource": "*"
    }
  ]
}
EOF
)

echo "$POLICY_DOCUMENT" > /tmp/bedrock-agent-policy.json

if [ "$IAM_TYPE" = "user" ]; then
    echo "Attaching inline policy to user: $IAM_NAME"
    aws iam put-user-policy \
        --user-name "$IAM_NAME" \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/bedrock-agent-policy.json
    echo "Policy attached successfully!"
else
    echo "For IAM roles, you need to attach the policy manually."
    echo "Policy document saved to: /tmp/bedrock-agent-policy.json"
    echo ""
    echo "To attach to role, run:"
    echo "aws iam put-role-policy \\"
    echo "  --role-name $IAM_NAME \\"
    echo "  --policy-name $POLICY_NAME \\"
    echo "  --policy-document file:///tmp/bedrock-agent-policy.json"
fi

echo ""
echo "========================================="
echo "Checking Agent Status"
echo "========================================="
echo ""

echo "Getting agent details..."
AGENT_STATUS=$(aws bedrock-agent get-agent \
    --agent-id "$AGENT_ID" \
    --region "$AWS_REGION" \
    --query 'agent.agentStatus' \
    --output text 2>&1 || echo "ERROR")

if [ "$AGENT_STATUS" = "ERROR" ]; then
    echo "Could not retrieve agent status (you may not have permission yet)"
else
    echo "Agent Status: $AGENT_STATUS"
    
    if [ "$AGENT_STATUS" != "PREPARED" ]; then
        echo ""
        echo "WARNING: Agent is not in PREPARED state!"
        echo "Run: ./update-bedrock-agent.sh to prepare it"
    fi
fi

echo ""
echo "========================================="
echo "Checking Agent Execution Role"
echo "========================================="
echo ""

# Get the agent's execution role
AGENT_ROLE=$(aws bedrock-agent get-agent \
    --agent-id "$AGENT_ID" \
    --region "$AWS_REGION" \
    --query 'agent.agentResourceRoleArn' \
    --output text 2>/dev/null || echo "")

if [ -n "$AGENT_ROLE" ] && [ "$AGENT_ROLE" != "None" ]; then
    echo "Agent Execution Role: $AGENT_ROLE"
    ROLE_NAME=$(echo "$AGENT_ROLE" | cut -d'/' -f2)
    
    echo ""
    echo "Checking if role has Bedrock model invocation permissions..."
    
    ROLE_POLICIES=$(aws iam list-role-policies \
        --role-name "$ROLE_NAME" \
        --query 'PolicyNames' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$ROLE_POLICIES" ]; then
        echo "Inline policies attached: $ROLE_POLICIES"
    else
        echo "No inline policies found"
    fi
    
    echo ""
    echo "To view the role's policy:"
    echo "aws iam get-role-policy --role-name $ROLE_NAME --policy-name BedrockModelInvokePolicy"
else
    echo "Could not retrieve agent execution role"
fi

echo ""
echo "========================================="
echo "Next Steps"
echo "========================================="
echo ""
echo "1. Wait a few seconds for IAM permissions to propagate"
echo "2. Test the agent again:"
echo "   python3 test_bedrock_agent.py"
echo ""
echo "If still getting access denied, check:"
echo "   - Agent status is PREPARED"
echo "   - Agent execution role has bedrock:InvokeModel permission"
echo "   - Foundation model is available in your region"
echo ""

