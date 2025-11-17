#!/bin/bash

set -e

echo "========================================="
echo "Creating AWS Bedrock Agent for Estimation Tool"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AWS_REGION="${AWS_REGION:-us-west-2}"
AGENT_NAME="${AGENT_NAME:-estimation-tool-agent}"
FOUNDATION_MODEL="${FOUNDATION_MODEL:-anthropic.claude-3-5-sonnet-20241022-v2:0}"
AGENT_ALIAS="${AGENT_ALIAS:-production}"

INSTRUCTION_FILE="$PROJECT_ROOT/personas/combined_agent_instruction.txt"

if [ ! -f "$INSTRUCTION_FILE" ]; then
    echo "ERROR: Instruction file not found: $INSTRUCTION_FILE"
    exit 1
fi

echo "Configuration:"
echo "  Region: $AWS_REGION"
echo "  Agent Name: $AGENT_NAME"
echo "  Foundation Model: $FOUNDATION_MODEL"
echo "  Alias: $AGENT_ALIAS"
echo ""

AGENT_INSTRUCTION=$(cat "$INSTRUCTION_FILE")

echo "Step 1: Creating Bedrock Agent..."
CREATE_RESPONSE=$(aws bedrock-agent create-agent \
    --agent-name "$AGENT_NAME" \
    --foundation-model "$FOUNDATION_MODEL" \
    --instruction "$AGENT_INSTRUCTION" \
    --agent-resource-role-arn "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/service-role/AmazonBedrockExecutionRoleForAgents_EstimationTool" \
    --description "Specialized agent for software estimation with BA and Engineering Manager personas. Integrates with Atlassian and Glean via MCP." \
    --idle-session-ttl-in-seconds 600 \
    --region "$AWS_REGION" \
    --output json 2>&1 || {
        echo "Note: If role doesn't exist, creating it..."
        
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        ROLE_NAME="AmazonBedrockExecutionRoleForAgents_EstimationTool"
        
        cat > /tmp/bedrock-agent-trust-policy.json <<EOF
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
          "aws:SourceAccount": "$ACCOUNT_ID"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock:$AWS_REGION:$ACCOUNT_ID:agent/*"
        }
      }
    }
  ]
}
EOF

        cat > /tmp/bedrock-agent-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:$AWS_REGION::foundation-model/$FOUNDATION_MODEL"
      ]
    }
  ]
}
EOF

        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/bedrock-agent-trust-policy.json \
            --description "Execution role for Bedrock Agent - Estimation Tool" \
            --region "$AWS_REGION" || echo "Role may already exist"
        
        aws iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "BedrockModelInvokePolicy" \
            --policy-document file:///tmp/bedrock-agent-policy.json \
            --region "$AWS_REGION"
        
        echo "Waiting 10 seconds for role to propagate..."
        sleep 10
        
        CREATE_RESPONSE=$(aws bedrock-agent create-agent \
            --agent-name "$AGENT_NAME" \
            --foundation-model "$FOUNDATION_MODEL" \
            --instruction "$AGENT_INSTRUCTION" \
            --agent-resource-role-arn "arn:aws:iam::$ACCOUNT_ID:role/service-role/$ROLE_NAME" \
            --description "Specialized agent for software estimation with BA and Engineering Manager personas. Integrates with Atlassian and Glean via MCP." \
            --idle-session-ttl-in-seconds 600 \
            --region "$AWS_REGION" \
            --output json)
    })

AGENT_ID=$(echo "$CREATE_RESPONSE" | jq -r '.agent.agentId')
AGENT_STATUS=$(echo "$CREATE_RESPONSE" | jq -r '.agent.agentStatus')

if [ -z "$AGENT_ID" ] || [ "$AGENT_ID" = "null" ]; then
    echo "ERROR: Failed to create agent"
    echo "$CREATE_RESPONSE"
    exit 1
fi

echo "Agent created successfully!"
echo "  Agent ID: $AGENT_ID"
echo "  Status: $AGENT_STATUS"
echo ""

echo "Step 2: Configuring MCP Action Groups..."
echo ""

echo "Step 2a: Creating Atlassian MCP Action Group..."

cat > /tmp/atlassian-mcp-schema.json <<'EOF'
{
  "openapi": "3.0.0",
  "info": {
    "title": "Atlassian MCP API",
    "version": "1.0.0",
    "description": "MCP tools for accessing Atlassian Confluence and Jira"
  },
  "paths": {
    "/confluence/page": {
      "get": {
        "summary": "Get Confluence page content",
        "description": "Retrieve the content of a Confluence page by URL or page ID",
        "operationId": "getConfluencePage",
        "parameters": [
          {
            "name": "url",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            },
            "description": "Confluence page URL or page ID"
          }
        ],
        "responses": {
          "200": {
            "description": "Page content retrieved successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "title": {
                      "type": "string"
                    },
                    "content": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/jira/issue": {
      "get": {
        "summary": "Get Jira issue details",
        "description": "Retrieve details of a Jira issue by key or URL",
        "operationId": "getJiraIssue",
        "parameters": [
          {
            "name": "url",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            },
            "description": "Jira issue URL or key"
          }
        ],
        "responses": {
          "200": {
            "description": "Issue details retrieved successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "key": {
                      "type": "string"
                    },
                    "summary": {
                      "type": "string"
                    },
                    "description": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/search": {
      "get": {
        "summary": "Search Confluence and Jira",
        "description": "Search across Confluence pages and Jira issues",
        "operationId": "searchAtlassian",
        "parameters": [
          {
            "name": "query",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            },
            "description": "Search query"
          }
        ],
        "responses": {
          "200": {
            "description": "Search results",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "results": {
                      "type": "array",
                      "items": {
                        "type": "object"
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
EOF

echo "Note: MCP Action Groups require Lambda functions as executors."
echo "The current Bedrock Agent API does not support direct MCP SSE connections."
echo "You will need to create Lambda functions that proxy to the MCP endpoints."
echo ""
echo "For now, creating action group structure (Lambda ARN to be added manually)..."
echo ""

echo "Step 3: Preparing the agent..."
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
echo "Step 4: Creating agent alias..."
ALIAS_RESPONSE=$(aws bedrock-agent create-agent-alias \
    --agent-id "$AGENT_ID" \
    --agent-alias-name "$AGENT_ALIAS" \
    --description "Production alias for estimation tool agent" \
    --region "$AWS_REGION" \
    --output json)

AGENT_ALIAS_ID=$(echo "$ALIAS_RESPONSE" | jq -r '.agentAlias.agentAliasId')

echo "Agent alias created successfully!"
echo "  Alias ID: $AGENT_ALIAS_ID"
echo ""

echo "========================================="
echo "Bedrock Agent Setup Complete!"
echo "========================================="
echo ""
echo "Agent Details:"
echo "  Agent ID: $AGENT_ID"
echo "  Agent Alias ID: $AGENT_ALIAS_ID"
echo "  Region: $AWS_REGION"
echo ""
echo "Next Steps:"
echo "1. Update your CloudFormation parameters:"
echo "   - BedrockAgentId=$AGENT_ID"
echo "   - BedrockAgentAliasId=$AGENT_ALIAS_ID"
echo ""
echo "2. Set environment variables (or update infrastructure/template.yaml):"
echo "   export BEDROCK_AGENT_ID=$AGENT_ID"
echo "   export BEDROCK_AGENT_ALIAS_ID=$AGENT_ALIAS_ID"
echo ""
echo "3. Deploy the updated stack:"
echo "   cd infrastructure && ./deploy.sh"
echo ""
echo "4. For MCP integration, you will need to:"
echo "   - Create Lambda functions to proxy MCP requests"
echo "   - Add action groups to the agent with Lambda executors"
echo "   - Run ./configure-mcp-action-groups.sh (to be created)"
echo ""

cat > "$SCRIPT_DIR/bedrock-agent-config.sh" <<EOF
#!/bin/bash
export BEDROCK_AGENT_ID=$AGENT_ID
export BEDROCK_AGENT_ALIAS_ID=$AGENT_ALIAS_ID
export AWS_REGION=$AWS_REGION
EOF

chmod +x "$SCRIPT_DIR/bedrock-agent-config.sh"
echo "Agent configuration saved to: $SCRIPT_DIR/bedrock-agent-config.sh"
echo "Source this file to set environment variables: source $SCRIPT_DIR/bedrock-agent-config.sh"

