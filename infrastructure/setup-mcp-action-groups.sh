#!/bin/bash

set -e

echo "========================================="
echo "Configure MCP Action Groups for Bedrock Agent"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/bedrock-agent-config.sh" ]; then
    source "$SCRIPT_DIR/bedrock-agent-config.sh"
    echo "Loaded configuration from bedrock-agent-config.sh"
else
    echo "ERROR: bedrock-agent-config.sh not found"
    echo "Run ./create-bedrock-agent.sh first"
    exit 1
fi

AGENT_ID="${BEDROCK_AGENT_ID}"
AWS_REGION="${AWS_REGION:-us-west-2}"

if [ -z "$AGENT_ID" ]; then
    echo "ERROR: BEDROCK_AGENT_ID not set"
    exit 1
fi

echo "Configuration:"
echo "  Agent ID: $AGENT_ID"
echo "  Region: $AWS_REGION"
echo ""

echo "IMPORTANT NOTE:"
echo "==============="
echo ""
echo "AWS Bedrock Agents do NOT support direct connections to MCP SSE endpoints."
echo "Action groups require Lambda functions as executors."
echo ""
echo "To integrate with MCP endpoints (Atlassian and Glean), you need to:"
echo ""
echo "1. Create Lambda functions that proxy requests to the MCP endpoints:"
echo "   - Lambda function for Atlassian MCP (https://mcp.atlassian.com/v1/sse)"
echo "   - Lambda function for Glean MCP (https://diligent-be.glean.com/mcp/default)"
echo ""
echo "2. Configure the Lambda functions with:"
echo "   - MCP endpoint URL in environment variables"
echo "   - Authentication credentials (from CloudFormation parameters)"
echo "   - Network configuration (VPC if required)"
echo ""
echo "3. Create action groups that use these Lambda functions as executors"
echo ""
echo "4. Define OpenAPI schemas for the action groups"
echo ""
echo "This script provides templates for these Lambda functions."
echo ""

read -p "Continue to generate Lambda function templates? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

LAMBDA_DIR="$SCRIPT_DIR/../backend/mcp_proxies"
mkdir -p "$LAMBDA_DIR"

echo "Creating Lambda function template for Atlassian MCP..."

cat > "$LAMBDA_DIR/atlassian_mcp_proxy.py" <<'EOF'
import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any

MCP_ENDPOINT = os.environ.get("ATLASSIAN_MCP_ENDPOINT", "https://mcp.atlassian.com/v1/sse")
ATLASSIAN_URL = os.environ["ATLASSIAN_URL"]
ATLASSIAN_EMAIL = os.environ["ATLASSIAN_USER_EMAIL"]
ATLASSIAN_TOKEN = os.environ["ATLASSIAN_API_TOKEN"]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Proxy Lambda function for Atlassian MCP action group.
    Routes Bedrock Agent requests to the Atlassian MCP endpoint.
    """
    
    action = event.get("actionGroup", "")
    api_path = event.get("apiPath", "")
    http_method = event.get("httpMethod", "GET")
    parameters = event.get("parameters", [])
    request_body = event.get("requestBody", {})
    
    print(f"Action: {action}, Path: {api_path}, Method: {http_method}")
    print(f"Parameters: {json.dumps(parameters)}")
    
    try:
        if api_path == "/confluence/page":
            url = None
            for param in parameters:
                if param.get("name") == "url":
                    url = param.get("value")
                    break
            
            if not url:
                return error_response("Missing required parameter: url")
            
            return fetch_confluence_page(url)
        
        elif api_path == "/jira/issue":
            url = None
            for param in parameters:
                if param.get("name") == "url":
                    url = param.get("value")
                    break
            
            if not url:
                return error_response("Missing required parameter: url")
            
            return fetch_jira_issue(url)
        
        elif api_path == "/search":
            query = None
            for param in parameters:
                if param.get("name") == "query":
                    query = param.get("value")
                    break
            
            if not query:
                return error_response("Missing required parameter: query")
            
            return search_atlassian(query)
        
        else:
            return error_response(f"Unknown API path: {api_path}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(str(e))


def fetch_confluence_page(url: str) -> Dict[str, Any]:
    """Fetch Confluence page content."""
    # This is a simplified example - integrate with your confluence_client module
    import sys
    sys.path.insert(0, '/opt/python')  # Lambda layer path
    
    from confluence_client import parse_confluence_config, fetch_confluence_page_markdown
    
    cfg = parse_confluence_config(ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
    title, content = fetch_confluence_page_markdown(cfg, url)
    
    return success_response({
        "title": title,
        "content": content,
        "url": url
    })


def fetch_jira_issue(url: str) -> Dict[str, Any]:
    """Fetch Jira issue details."""
    import sys
    sys.path.insert(0, '/opt/python')
    
    from confluence_client import parse_confluence_config, fetch_jira_issue_markdown
    
    cfg = parse_confluence_config(ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
    title, content = fetch_jira_issue_markdown(cfg, url)
    
    return success_response({
        "key": title,
        "content": content,
        "url": url
    })


def search_atlassian(query: str) -> Dict[str, Any]:
    """Search across Atlassian."""
    # Implement search functionality
    # This would require integration with Confluence and Jira search APIs
    
    return success_response({
        "query": query,
        "results": [],
        "message": "Search functionality to be implemented"
    })


def success_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """Return success response for Bedrock Agent."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "atlassian-mcp",
            "apiPath": "/",
            "httpMethod": "GET",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(body)
                }
            }
        }
    }


def error_response(message: str) -> Dict[str, Any]:
    """Return error response for Bedrock Agent."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "atlassian-mcp",
            "apiPath": "/",
            "httpMethod": "GET",
            "httpStatusCode": 400,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": message})
                }
            }
        }
    }
EOF

echo "Creating Lambda function template for Glean MCP..."

cat > "$LAMBDA_DIR/glean_mcp_proxy.py" <<'EOF'
import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any

MCP_ENDPOINT = os.environ.get("GLEAN_MCP_ENDPOINT", "https://diligent-be.glean.com/mcp/default")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Proxy Lambda function for Glean MCP action group.
    Routes Bedrock Agent requests to the Glean MCP endpoint.
    """
    
    action = event.get("actionGroup", "")
    api_path = event.get("apiPath", "")
    http_method = event.get("httpMethod", "GET")
    parameters = event.get("parameters", [])
    
    print(f"Action: {action}, Path: {api_path}, Method: {http_method}")
    print(f"Parameters: {json.dumps(parameters)}")
    
    try:
        if api_path == "/search":
            query = None
            for param in parameters:
                if param.get("name") == "query":
                    query = param.get("value")
                    break
            
            if not query:
                return error_response("Missing required parameter: query")
            
            return search_glean(query)
        
        else:
            return error_response(f"Unknown API path: {api_path}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(str(e))


def search_glean(query: str) -> Dict[str, Any]:
    """Search company knowledge via Glean."""
    
    # TODO: Implement actual Glean MCP integration
    # This requires proper authentication and MCP protocol handling
    
    headers = {
        "Content-Type": "application/json",
        # Add authentication headers as needed
    }
    
    # Example request to Glean MCP endpoint
    # Actual implementation depends on Glean's MCP protocol
    
    return success_response({
        "query": query,
        "results": [],
        "message": "Glean integration to be implemented"
    })


def success_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """Return success response for Bedrock Agent."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "glean-mcp",
            "apiPath": "/",
            "httpMethod": "GET",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(body)
                }
            }
        }
    }


def error_response(message: str) -> Dict[str, Any]:
    """Return error response for Bedrock Agent."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "glean-mcp",
            "apiPath": "/",
            "httpMethod": "GET",
            "httpStatusCode": 400,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": message})
                }
            }
        }
    }
EOF

echo ""
echo "Lambda function templates created in: $LAMBDA_DIR"
echo ""
echo "Next steps:"
echo "1. Review and customize the Lambda functions"
echo "2. Add the Lambda functions to your CloudFormation template"
echo "3. Create action groups for the agent using these Lambda functions"
echo "4. Test the integration"
echo ""
echo "Example CloudFormation for Lambda:"
cat <<'YAML'

  AtlassianMCPProxyFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ../backend/mcp_proxies
      Handler: atlassian_mcp_proxy.lambda_handler
      Runtime: python3.11
      Timeout: 30
      Layers:
        - !Ref BackendDependenciesLayer
      Environment:
        Variables:
          ATLASSIAN_MCP_ENDPOINT: https://mcp.atlassian.com/v1/sse
          ATLASSIAN_URL: !Ref AtlassianURL
          ATLASSIAN_USER_EMAIL: !Ref AtlassianEmail
          ATLASSIAN_API_TOKEN: !Ref AtlassianToken
      Policies:
        - Statement:
            - Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource: "*"

YAML

echo ""
echo "Add action groups with AWS CLI:"
echo ""
echo "aws bedrock-agent create-agent-action-group \\"
echo "  --agent-id $AGENT_ID \\"
echo "  --agent-version DRAFT \\"
echo "  --action-group-name atlassian-mcp \\"
echo "  --action-group-executor lambda=arn:aws:lambda:REGION:ACCOUNT:function:FUNCTION_NAME \\"
echo "  --api-schema file://atlassian-mcp-schema.json \\"
echo "  --region $AWS_REGION"
echo ""

echo "Done!"

