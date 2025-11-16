# AWS Bedrock Agent Setup and Testing Guide

This guide covers the setup, configuration, and testing of the AWS Bedrock Agent with MCP integration for the Estimation Tool.

## Overview

The Estimation Tool now supports using a specialized AWS Bedrock Agent instead of direct model invocation. The agent:
- Combines Business Analyst and Engineering Manager personas
- Routes tasks automatically between BA analysis and PERT estimation
- Integrates with Atlassian (Confluence/Jira) and Glean via MCP
- Provides consistent, high-quality software estimates

## Prerequisites

1. AWS CLI installed and configured with appropriate credentials
2. AWS account with Bedrock access enabled
3. IAM permissions to create and manage Bedrock Agents
4. Access to Atlassian (Confluence/Jira) with API credentials
5. Access to Glean MCP endpoint

## Setup Instructions

### Step 1: Create the Bedrock Agent

Run the agent creation script:

```bash
cd infrastructure
./create-bedrock-agent.sh
```

This script will:
1. Create a new Bedrock Agent with the combined BA/Engineer instruction prompt
2. Configure the agent with Claude 3.5 Sonnet foundation model
3. Set up IAM roles for agent execution
4. Create a production alias for the agent
5. Output the Agent ID and Alias ID for configuration

**Expected Output:**
```
========================================
Bedrock Agent Setup Complete!
========================================

Agent Details:
  Agent ID: XXXXXXXXXX
  Agent Alias ID: YYYYYYYYYY
  Region: us-west-2

Next Steps:
1. Update your CloudFormation parameters:
   - BedrockAgentId=XXXXXXXXXX
   - BedrockAgentAliasId=YYYYYYYYYY
```

**Save these values** - you'll need them for deployment.

### Step 2: Update CloudFormation Configuration

The CloudFormation template has been updated with new parameters for Bedrock Agent support. When deploying, you can now specify:

```yaml
Parameters:
  BedrockAgentId: XXXXXXXXXX           # From Step 1
  BedrockAgentAliasId: YYYYYYYYYY     # From Step 1
  BedrockModel: ""                     # Leave empty when using agent
```

### Step 3: Deploy the Updated Stack

Deploy the stack with the agent configuration:

```bash
cd infrastructure
./deploy.sh
```

During the guided deployment, provide:
- **LLMProvider**: `bedrock`
- **BedrockAgentId**: `<Agent ID from Step 1>`
- **BedrockAgentAliasId**: `<Agent Alias ID from Step 1>`
- **BedrockModel**: Leave empty or provide a fallback model
- **BedrockRegion**: `us-west-2` (or your preferred region)
- **AtlassianURL**: Your Atlassian instance URL
- **AtlassianEmail**: Your Atlassian email
- **AtlassianToken**: Your Atlassian API token

## Configuration Options

### Environment Variables

The system recognizes these environment variables (set via CloudFormation or Lambda):

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LLM_PROVIDER` | Provider type | Yes | `openai` |
| `BEDROCK_AGENT_ID` | Bedrock Agent ID | When using agent | - |
| `BEDROCK_AGENT_ALIAS_ID` | Bedrock Agent Alias ID | When using agent | - |
| `BEDROCK_MODEL` | Fallback model ID | No | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `BEDROCK_REGION` | AWS region | No | Uses Lambda's region |
| `ATLASSIAN_URL` | Atlassian instance URL | Yes | - |
| `ATLASSIAN_USER_EMAIL` | Atlassian user email | Yes | - |
| `ATLASSIAN_API_TOKEN` | Atlassian API token | Yes | - |

### Behavioral Configuration

When both `BEDROCK_AGENT_ID` and `BEDROCK_AGENT_ALIAS_ID` are set:
- The system uses the Bedrock Agent instead of direct model invocation
- The agent handles task routing (BA vs PERT) automatically
- MCP tools are available for Atlassian and Glean integration

When only `BEDROCK_MODEL` is set:
- The system uses direct Bedrock model invocation
- No MCP integration
- Uses the original BA/Engineer persona files separately

## Testing

### Local Testing with AWS CLI

Test the agent directly using AWS CLI:

```bash
# Source the agent configuration
source infrastructure/bedrock-agent-config.sh

# Test agent invocation
aws bedrock-agent-runtime invoke-agent \
  --agent-id "$BEDROCK_AGENT_ID" \
  --agent-alias-id "$BEDROCK_AGENT_ALIAS_ID" \
  --session-id "$(uuidgen)" \
  --input-text "Analyze this Confluence page: https://your-instance.atlassian.net/wiki/spaces/..." \
  --region "$AWS_REGION" \
  /tmp/agent-response.txt

# View the response
cat /tmp/agent-response.txt
```

### Python Testing Script

Create a test script to invoke the agent via boto3:

```python
import boto3
import uuid
import json
import base64

# Configuration
agent_id = "XXXXXXXXXX"  # Your Agent ID
agent_alias_id = "YYYYYYYYYY"  # Your Agent Alias ID
region = "us-west-2"

# Create client
client = boto3.client("bedrock-agent-runtime", region_name=region)

# Test input
test_input = """
Analyze this requirement and provide a BA estimation analysis:
Confluence Link: https://your-instance.atlassian.net/wiki/spaces/PROJECT/pages/123456789
"""

# Invoke agent
session_id = uuid.uuid4().hex
response = client.invoke_agent(
    agentId=agent_id,
    agentAliasId=agent_alias_id,
    sessionId=session_id,
    inputText=test_input,
    enableTrace=False
)

# Parse response
parts = []
for event in response.get("completion", []):
    if "chunk" in event:
        chunk = event["chunk"]
        if "bytes" in chunk:
            decoded = base64.b64decode(chunk["bytes"])
            parts.append(decoded.decode("utf-8"))

output = "".join(parts)
print("Agent Response:")
print(output)
```

### Integration Testing

Test the full API flow:

```bash
# Get your API endpoint from CloudFormation outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text)

# Test BA analysis
curl -X POST "${API_URL}/estimate" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-instance.atlassian.net/wiki/spaces/PROJECT/pages/123456789",
    "ballpark": null
  }'

# Test with ballpark constraint
curl -X POST "${API_URL}/estimate" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-instance.atlassian.net/wiki/spaces/PROJECT/pages/123456789",
    "ballpark": "30 manweeks"
  }'
```

### Expected Output Format

#### BA Analysis Output

The agent should produce a markdown document with this structure:

```markdown
# Requirement Analysis for ROM Estimation

## Source
- Confluence Page: [link]
- Related JIRA Tickets: [list]

## Business Context
...

## Functional Scope
...

## Non-Functional Considerations
...

## System and Data Dependencies
...

## Uncertainties and Open Questions
- **UNCERTAINTY**: [item]
...

## Suggested Breakdown for Estimation
...

## Risks and Constraints
...

## Appendix
### Glossary
...
### Additional Links
...
```

#### PERT Estimation Output

```markdown
## PERT Estimate: [Project Name]

### Metadata
- **Date**: 2025-11-16
- **Scope**: [scope]
- **Unit**: manweeks
...

### Task Breakdown
| ID | Task | O | M | P | E | σ | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Feature X | 2 | 4 | 8 | 4 | 1.0 | ... |
...

**Grand Total: X manweeks**

### Rollup
...

### Notes and Rationale
...
```

## Troubleshooting

### Agent Not Found

**Error**: `Agent with id XXXXXXXXXX not found`

**Solution**:
1. Verify the agent was created: `aws bedrock-agent get-agent --agent-id XXXXXXXXXX --region us-west-2`
2. Check the agent status: should be `PREPARED`
3. Verify the agent alias exists

### Permission Denied

**Error**: `AccessDeniedException` or `User is not authorized`

**Solution**:
1. Check Lambda execution role has Bedrock permissions
2. Verify IAM policy includes:
   - `bedrock:InvokeAgent`
   - `bedrock:InvokeModel`
3. Ensure agent resource role has proper trust relationship

### Agent Returns Empty Response

**Issue**: Agent invocation succeeds but returns empty string

**Solution**:
1. Check agent preparation status: `aws bedrock-agent get-agent --agent-id XXXXXXXXXX`
2. Enable trace in invoke-agent call: `enableTrace=True`
3. Review CloudWatch logs for agent runtime
4. Verify the instruction prompt is loaded correctly

### MCP Connection Failures

**Issue**: Agent cannot access Atlassian or Glean

**Note**: The current Bedrock Agent implementation requires Lambda functions as executors for action groups. Direct SSE MCP connections are not yet supported by AWS Bedrock Agents.

**Workaround**:
1. Create Lambda functions that proxy requests to MCP endpoints
2. Add action groups to the agent with Lambda executors
3. Configure authentication headers in Lambda environment

## Updating the Agent

### Update Agent Instructions

To update the agent's instruction prompt:

```bash
# Edit the instruction file
vim personas/combined_agent_instruction.txt

# Update the agent
./infrastructure/update-bedrock-agent.sh
```

The script will:
1. Load current agent configuration
2. Update the instruction prompt
3. Prepare the agent with new instructions
4. Wait for preparation to complete

### Update Foundation Model

To change the foundation model:

```bash
aws bedrock-agent update-agent \
  --agent-id "$BEDROCK_AGENT_ID" \
  --agent-name "estimation-tool-agent" \
  --foundation-model "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --instruction "$(cat personas/combined_agent_instruction.txt)" \
  --agent-resource-role-arn "<role-arn>" \
  --region us-west-2

aws bedrock-agent prepare-agent \
  --agent-id "$BEDROCK_AGENT_ID" \
  --region us-west-2
```

## Monitoring and Observability

### CloudWatch Logs

Monitor agent invocations via CloudWatch:
- Log Group: `/aws/lambda/estimation-tool-api-EstimationFunction-*`
- Filter for: `Bedrock Agent API` or `invoke_agent`

### Metrics to Monitor

Key metrics for agent performance:
- Invocation count and success rate
- Average response time
- Error rate by error type
- Token usage (if metered)

### Cost Optimization

Tips for managing costs:
1. Use agent aliases for versioning (avoid recreating agents)
2. Set appropriate idle session TTL (default: 600 seconds)
3. Monitor token usage in CloudWatch
4. Consider using provisioned throughput for high-volume usage

## Migration from Direct Model to Agent

### Gradual Migration

To migrate from direct model invocation to agent:

1. **Deploy with both options**: Keep `BEDROCK_MODEL` as fallback
2. **Test with agent**: Set `BEDROCK_AGENT_ID` and `BEDROCK_AGENT_ALIAS_ID`
3. **Monitor results**: Compare quality and performance
4. **Switch fully**: Remove fallback model configuration

### Rollback Procedure

If issues occur, roll back quickly:

```bash
# Option 1: Update environment variables
aws lambda update-function-configuration \
  --function-name estimation-tool-api-EstimationFunction-XXXXX \
  --environment Variables="{LLM_PROVIDER=bedrock,BEDROCK_MODEL=anthropic.claude-3-sonnet-20240229-v1:0,...}"

# Option 2: Redeploy stack with previous parameters
cd infrastructure
./deploy.sh  # Use previous parameter values
```

## Next Steps

1. **MCP Integration**: Implement Lambda proxy functions for MCP endpoints
2. **Action Groups**: Add Atlassian and Glean action groups to agent
3. **Fine-tuning**: Adjust instruction prompt based on output quality
4. **Monitoring**: Set up CloudWatch dashboards for agent metrics
5. **Cost Analysis**: Review usage and optimize where needed

## Support and Resources

- AWS Bedrock Documentation: https://docs.aws.amazon.com/bedrock/
- Bedrock Agents Guide: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- MCP Protocol: https://modelcontextprotocol.io/
- Project Documentation: `doc/` directory

## Known Limitations

1. **MCP Direct Connection**: Bedrock Agents cannot directly connect to SSE MCP endpoints
   - Requires Lambda proxy functions as intermediaries
   - Action groups must use Lambda executors

2. **System Prompt Handling**: Agents combine system prompt with user input
   - May affect prompt engineering compared to direct model invocation
   - Test thoroughly to ensure output quality

3. **Streaming**: Current implementation uses non-streaming responses
   - Can be updated to support streaming if needed

4. **Session Management**: Agent uses session IDs for context
   - Current implementation creates new session per request
   - Could be extended for conversation continuity

## Security Considerations

1. **IAM Permissions**: Follow principle of least privilege
2. **API Tokens**: Store Atlassian tokens in AWS Secrets Manager
3. **Network Security**: Use VPC endpoints for Bedrock if required
4. **Audit Logging**: Enable CloudTrail for agent API calls
5. **Data Privacy**: Review data handling in agent conversations

