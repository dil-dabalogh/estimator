#!/bin/bash

set -e

echo "========================================="
echo "Bedrock Agent Diagnostics and Fix"
echo "========================================="
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
ACCOUNT_ID="568475829330"

echo "Configuration:"
echo "  Agent ID: $AGENT_ID"
echo "  Region: $AWS_REGION"
echo "  Account: $ACCOUNT_ID"
echo ""

echo "========================================="
echo "Step 1: Check Agent Status"
echo "========================================="
echo ""

AGENT_INFO=$(aws bedrock-agent get-agent \
    --agent-id "$AGENT_ID" \
    --region "$AWS_REGION" \
    --output json)

AGENT_STATUS=$(echo "$AGENT_INFO" | jq -r '.agent.agentStatus')
AGENT_NAME=$(echo "$AGENT_INFO" | jq -r '.agent.agentName')
AGENT_ROLE_ARN=$(echo "$AGENT_INFO" | jq -r '.agent.agentResourceRoleArn')
FOUNDATION_MODEL=$(echo "$AGENT_INFO" | jq -r '.agent.foundationModel')

echo "Agent Name: $AGENT_NAME"
echo "Agent Status: $AGENT_STATUS"
echo "Foundation Model: $FOUNDATION_MODEL"
echo "Execution Role: $AGENT_ROLE_ARN"
echo ""

if [ "$AGENT_STATUS" != "PREPARED" ]; then
    echo "❌ Agent is NOT in PREPARED state!"
    echo "   Current status: $AGENT_STATUS"
    echo ""
    echo "Preparing agent now..."
    
    aws bedrock-agent prepare-agent \
        --agent-id "$AGENT_ID" \
        --region "$AWS_REGION" \
        --output json > /dev/null
    
    echo "Waiting for agent to be prepared (this may take 30-60 seconds)..."
    
    for i in {1..20}; do
        sleep 3
        STATUS=$(aws bedrock-agent get-agent \
            --agent-id "$AGENT_ID" \
            --region "$AWS_REGION" \
            --query 'agent.agentStatus' \
            --output text)
        
        echo "  Check $i/20: $STATUS"
        
        if [ "$STATUS" = "PREPARED" ]; then
            echo "✅ Agent is now PREPARED!"
            AGENT_STATUS="PREPARED"
            break
        fi
    done
    
    if [ "$AGENT_STATUS" != "PREPARED" ]; then
        echo "❌ Agent preparation timed out. Check AWS console for details."
        exit 1
    fi
else
    echo "✅ Agent is PREPARED"
fi

echo ""
echo "========================================="
echo "Step 2: Check Agent Execution Role"
echo "========================================="
echo ""

# Extract full role name including path (e.g., service-role/RoleName)
ROLE_NAME_WITH_PATH=$(echo "$AGENT_ROLE_ARN" | sed 's|arn:aws:iam::[0-9]*:role/||')
ROLE_NAME=$(echo "$ROLE_NAME_WITH_PATH" | rev | cut -d'/' -f1 | rev)

echo "Role ARN: $AGENT_ROLE_ARN"
echo "Role Name (with path): $ROLE_NAME_WITH_PATH"
echo "Role Name: $ROLE_NAME"
echo ""

echo "Getting role details..."

# Try to get the role - first without path, then search for it
ROLE_INFO=$(aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null || echo "NOT_FOUND")

if [ "$ROLE_INFO" = "NOT_FOUND" ]; then
    echo "Role not found with simple name, searching all roles..."
    
    # List all roles and find the one matching the ARN
    ALL_ROLES=$(aws iam list-roles --output json)
    ROLE_INFO=$(echo "$ALL_ROLES" | jq -r --arg arn "$AGENT_ROLE_ARN" '.Roles[] | select(.Arn == $arn)')
    
    if [ -z "$ROLE_INFO" ] || [ "$ROLE_INFO" = "null" ]; then
        echo "❌ Role does not exist in IAM!"
        echo ""
        echo "Creating the execution role for the agent..."
        
        # Create trust policy for Bedrock
        TRUST_POLICY_DOC=$(cat <<'EOFT'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "ACCOUNT_ID_PLACEHOLDER"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock:REGION_PLACEHOLDER:ACCOUNT_ID_PLACEHOLDER:agent/*"
        }
      }
    }
  ]
}
EOFT
)
        
        # Replace placeholders
        TRUST_POLICY_DOC=$(echo "$TRUST_POLICY_DOC" | sed "s/ACCOUNT_ID_PLACEHOLDER/$ACCOUNT_ID/g" | sed "s/REGION_PLACEHOLDER/$AWS_REGION/g")
        
        # Create the role
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --path "/service-role/" \
            --assume-role-policy-document "$TRUST_POLICY_DOC" \
            --description "Execution role for Bedrock Agent - Estimation Tool"
        
        echo "✅ Role created successfully"
        echo ""
        
        # Add Bedrock model invocation permission immediately
        BEDROCK_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${AWS_REGION}::foundation-model/${FOUNDATION_MODEL}",
        "arn:aws:bedrock:${AWS_REGION}::foundation-model/*"
      ]
    }
  ]
}
EOF
)
        
        aws iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "BedrockModelInvokePolicy" \
            --policy-document "$BEDROCK_POLICY"
        
        echo "✅ Added Bedrock permissions to role"
        echo ""
        
        # Update agent to use this role
        echo "Updating agent with the new role..."
        aws bedrock-agent update-agent \
            --agent-id "$AGENT_ID" \
            --agent-name "$AGENT_NAME" \
            --foundation-model "$FOUNDATION_MODEL" \
            --instruction "$(cat $SCRIPT_DIR/../personas/combined_agent_instruction.txt)" \
            --agent-resource-role-arn "$AGENT_ROLE_ARN" \
            --region "$AWS_REGION" \
            --output json > /dev/null
        
        echo "✅ Agent updated with new role"
        
        # Set flag to skip permission check since we just added it
        HAS_BEDROCK_PERMISSION=true
        
        # Get the role info now
        ROLE_INFO=$(aws iam get-role --role-name "$ROLE_NAME" --output json)
        TRUST_POLICY=$(echo "$ROLE_INFO" | jq -r '.Role.AssumeRolePolicyDocument')
    else
        echo "✅ Found role in IAM"
        TRUST_POLICY=$(echo "$ROLE_INFO" | jq -r '.AssumeRolePolicyDocument')
    fi
else
    echo "✅ Found role"
    TRUST_POLICY=$(echo "$ROLE_INFO" | jq -r '.Role.AssumeRolePolicyDocument')
fi

echo "$TRUST_POLICY" | jq '.'
echo ""

echo "Checking role policies..."
INLINE_POLICIES=$(aws iam list-role-policies \
    --role-name "$ROLE_NAME" \
    --query 'PolicyNames' \
    --output text 2>/dev/null || echo "")

ATTACHED_POLICIES=$(aws iam list-attached-role-policies \
    --role-name "$ROLE_NAME" \
    --query 'AttachedPolicies[].PolicyName' \
    --output text 2>/dev/null || echo "")

echo "Inline Policies: $INLINE_POLICIES"
echo "Attached Policies: $ATTACHED_POLICIES"
echo ""

# Check if the role has the required Bedrock permissions
echo "Checking for Bedrock model invocation permissions..."

HAS_BEDROCK_PERMISSION=false

if [ -n "$INLINE_POLICIES" ]; then
    for policy_name in $INLINE_POLICIES; do
        echo "  Checking inline policy: $policy_name"
        POLICY_DOC=$(aws iam get-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "$policy_name" \
            --query 'PolicyDocument' \
            --output json)
        
        if echo "$POLICY_DOC" | grep -q "bedrock:InvokeModel"; then
            echo "    ✅ Found bedrock:InvokeModel permission"
            HAS_BEDROCK_PERMISSION=true
        fi
    done
fi

if [ "$HAS_BEDROCK_PERMISSION" = "false" ]; then
    echo ""
    echo "❌ Role does NOT have bedrock:InvokeModel permission!"
    echo ""
    echo "Adding Bedrock invocation policy to role..."
    
    POLICY_DOCUMENT=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${AWS_REGION}::foundation-model/${FOUNDATION_MODEL}",
        "arn:aws:bedrock:${AWS_REGION}::foundation-model/*"
      ]
    }
  ]
}
EOF
)
    
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "BedrockModelInvokePolicy" \
        --policy-document "$POLICY_DOCUMENT"
    
    echo "✅ Policy added successfully!"
    echo ""
    echo "Re-preparing agent to pick up new permissions..."
    
    aws bedrock-agent prepare-agent \
        --agent-id "$AGENT_ID" \
        --region "$AWS_REGION" \
        --output json > /dev/null
    
    echo "Waiting for agent to be prepared..."
    sleep 10
    
    for i in {1..10}; do
        STATUS=$(aws bedrock-agent get-agent \
            --agent-id "$AGENT_ID" \
            --region "$AWS_REGION" \
            --query 'agent.agentStatus' \
            --output text)
        
        if [ "$STATUS" = "PREPARED" ]; then
            echo "✅ Agent re-prepared successfully!"
            break
        fi
        
        sleep 3
    done
else
    echo "✅ Role has Bedrock invocation permissions"
fi

echo ""
echo "========================================="
echo "Step 3: Test Foundation Model Access"
echo "========================================="
echo ""

echo "Checking if foundation model $FOUNDATION_MODEL is available..."

# List available models
AVAILABLE_MODELS=$(aws bedrock list-foundation-models \
    --region "$AWS_REGION" \
    --query "modelSummaries[?modelId=='$FOUNDATION_MODEL'].modelId" \
    --output text 2>/dev/null || echo "")

if [ -n "$AVAILABLE_MODELS" ]; then
    echo "✅ Foundation model is available in $AWS_REGION"
else
    echo "⚠️  Could not verify model availability"
    echo "   You may need to request access to the model in the Bedrock console"
    echo ""
    echo "   Go to: https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/modelaccess"
fi

echo ""
echo "========================================="
echo "Step 4: Check Agent Alias"
echo "========================================="
echo ""

AGENT_ALIAS_ID="${BEDROCK_AGENT_ALIAS_ID}"
echo "Checking alias: $AGENT_ALIAS_ID"

ALIAS_INFO=$(aws bedrock-agent get-agent-alias \
    --agent-id "$AGENT_ID" \
    --agent-alias-id "$AGENT_ALIAS_ID" \
    --region "$AWS_REGION" \
    --output json 2>/dev/null || echo "{}")

ALIAS_STATUS=$(echo "$ALIAS_INFO" | jq -r '.agentAlias.agentAliasStatus // "NOT_FOUND"')

if [ "$ALIAS_STATUS" = "PREPARED" ]; then
    echo "✅ Agent alias is PREPARED"
elif [ "$ALIAS_STATUS" = "NOT_FOUND" ]; then
    echo "❌ Agent alias not found!"
    echo "   Creating alias..."
    
    aws bedrock-agent create-agent-alias \
        --agent-id "$AGENT_ID" \
        --agent-alias-name "production" \
        --region "$AWS_REGION" \
        --output json > /tmp/alias-create.json
    
    NEW_ALIAS_ID=$(cat /tmp/alias-create.json | jq -r '.agentAlias.agentAliasId')
    echo "✅ New alias created: $NEW_ALIAS_ID"
    echo ""
    echo "⚠️  Update bedrock-agent-config.sh with new alias ID:"
    echo "   export BEDROCK_AGENT_ALIAS_ID=$NEW_ALIAS_ID"
else
    echo "Alias status: $ALIAS_STATUS"
fi

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo ""
echo "Agent ID: $AGENT_ID"
echo "Agent Status: $AGENT_STATUS"
echo "Agent Role: $ROLE_NAME"
echo "Alias ID: $AGENT_ALIAS_ID"
echo ""

if [ "$AGENT_STATUS" = "PREPARED" ]; then
    echo "✅ Agent is ready to use!"
    echo ""
    echo "Test with:"
    echo "  python3 test_bedrock_agent.py"
    echo ""
else
    echo "❌ Agent is not ready. Check the errors above."
fi

