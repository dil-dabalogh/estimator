# AWS Authentication and Networking Guide for Bedrock Orchestrator

The `orchestrator_unified.py` script supports multiple AWS authentication methods and invocation modes. Choose the one that best fits your corporate environment.

**Note**: To use Bedrock, you must configure the provider. Either:
- Set `LLM_PROVIDER=bedrock` environment variable, or
- Create `orchestrator.conf` with `[provider] provider=bedrock` (see `orchestrator.conf.example`)

## Invocation Modes

The script supports two invocation modes:

1. **Direct Model Invocation** (default): Calls Bedrock models directly using `bedrock-runtime`
   - Use `--model` with a model ID (e.g., `anthropic.claude-3-sonnet-20240229-v1:0`)
   - Requires `bedrock:InvokeModel` permission

2. **Bedrock Agent Invocation**: Calls a Bedrock Agent using `bedrock-agent-runtime`
   - Use `--agent-id` and `--agent-alias-id` 
   - Requires `bedrock:InvokeAgent` permission
   - Agent alias must be deployed and active

## Option 1: AWS SSO (Recommended for Corporate Environments)

AWS SSO (now called AWS IAM Identity Center) is the recommended method for corporate environments as it provides centralized access management and automatic credential rotation.

### Setup Steps

1. **Configure AWS SSO** (one-time setup):
   ```bash
   aws configure sso
   ```
   
   You'll be prompted for:
   - SSO start URL (e.g., `https://your-company.awsapps.com/start`)
   - SSO region (e.g., `us-east-1`)
   - SSO account ID
   - SSO role name
   - Default region (e.g., `us-east-1`)
   - Default output format (e.g., `json`)
   - Profile name (e.g., `bedrock-dev`)

2. **Login to SSO** (required periodically, typically every 8-12 hours):
   ```bash
   aws sso login --profile bedrock-dev
   ```
   
   This opens a browser for authentication. After successful login, credentials are cached locally.

3. **Set the profile** (for the current session):
   ```bash
   export AWS_PROFILE=bedrock-dev
   ```

4. **Run the orchestrator**:
   ```bash
   python scripts/orchestrator_unified.py run "<confluence-url>" --name "MyFeature" --config orchestrator.conf
   ```

### Benefits of SSO
- ✅ Centralized access management
- ✅ Automatic credential rotation
- ✅ No need to manage long-lived access keys
- ✅ Better security compliance
- ✅ Works seamlessly with boto3

### Re-authentication
SSO sessions typically expire after 8-12 hours. When you get authentication errors, simply run:
```bash
aws sso login --profile bedrock-dev
```

---

## Option 2: Access Keys (Environment Variables)

If SSO is not available, you can use traditional access keys.

### Setup Steps

1. **Get access keys** from your AWS administrator or IAM console

2. **Set environment variables**:
   ```bash
   export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
   export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
   export AWS_REGION="us-east-1"
   ```

3. **Run the orchestrator**:
   ```bash
   python scripts/orchestrator_unified.py run "<confluence-url>" --name "MyFeature" --config orchestrator.conf
   ```

### Security Note
⚠️ **Never commit access keys to version control!** Consider using:
- `.env` files (with `.gitignore`)
- Secret management tools (AWS Secrets Manager, HashiCorp Vault)
- Environment variable management tools

---

## Option 3: AWS Profile (Non-SSO)

If you have multiple AWS accounts or roles configured via `~/.aws/credentials`:

1. **Set the profile**:
   ```bash
   export AWS_PROFILE=my-profile
   export AWS_REGION=us-east-1
   ```

2. **Run the orchestrator**:
   ```bash
   python scripts/orchestrator_unified.py run "<confluence-url>" --name "MyFeature" --config orchestrator.conf
   ```

---

## Option 4: IAM Role (EC2/ECS/Lambda)

When running on AWS infrastructure (EC2, ECS, Lambda), the script automatically uses the IAM role attached to the instance/task/function. No additional configuration needed beyond setting `AWS_REGION`.

---

## Diligent VPC/Networking Considerations

### For Private Subnets in Workload VPC

If your script runs in a private subnet within Diligent's Workload VPC (without public internet egress), you **must** have VPC interface endpoints configured:

#### Required VPC Endpoints

1. **For Direct Model Invocation** (`--model`):
   - Service: `com.amazonaws.<region>.bedrock-runtime`
   - Enable **Private DNS** on the endpoint

2. **For Agent Invocation** (`--agent-id`):
   - Service: `com.amazonaws.<region>.bedrock-agent-runtime` (required)
   - Service: `com.amazonaws.<region>.bedrock-runtime` (if agent calls models directly)
   - Enable **Private DNS** on all endpoints

#### Why Private DNS is Critical

Without Private DNS enabled:
- DNS queries resolve to public endpoints
- Requests timeout because private subnets lack internet egress
- You'll see connection errors or timeouts

#### VPC Endpoint Configuration Checklist

- [ ] VPC interface endpoints created for required services
- [ ] Private DNS enabled on all Bedrock endpoints
- [ ] Security groups allow outbound traffic to endpoints
- [ ] Route tables configured (endpoints should be automatically added)
- [ ] Endpoint policies allow necessary actions (`bedrock:InvokeModel` or `bedrock:InvokeAgent`)

#### Testing from Private Subnet

```bash
# Verify endpoint resolution
nslookup bedrock-runtime.us-west-2.amazonaws.com
# Should resolve to private IP (e.g., 10.x.x.x) if Private DNS is enabled

# Test connectivity
aws bedrock-runtime invoke-model --model-id anthropic.claude-3-sonnet-20240229-v1:0 ...
```

### For Public Subnets

If running from a public subnet with internet gateway:
- No VPC endpoints required
- Standard AWS SDK will use public endpoints
- Ensure security groups allow outbound HTTPS (443)

### Model Access Requirements

- **Anthropic Models**: May require a one-time use-case submission form (per org/account) before first use
- **Other Models**: Generally auto-enabled in 2025+, but verify in Bedrock console
- **Agent Models**: Ensure the model your agent uses is enabled in the account/region

---

## Troubleshooting

### "Failed to initialize Bedrock client"
- **Check credentials**: Run `aws sts get-caller-identity` to verify your credentials work
- **Check region**: Ensure `AWS_REGION` is set correctly
- **Check SSO session**: If using SSO, run `aws sso login --profile <profile>` to refresh

### "AccessDeniedException" or "UnauthorizedOperation"
- **Check permissions**: 
  - For direct model: IAM user/role needs `bedrock:InvokeModel` permission
  - For agents: IAM user/role needs `bedrock:InvokeAgent` permission
- **Check endpoint policies**: If using VPC endpoints, ensure endpoint policy allows the action
- **Check model access**: Ensure the Bedrock model is available in your region and account
- **Check SSO permissions**: Verify your SSO role has the necessary Bedrock permissions
- **Check agent status**: For agents, ensure the alias is deployed and active

### "ResourceNotFoundException" (Agents)
- **Verify agent IDs**: Check `agentId` and `agentAliasId` are correct
- **Check alias status**: Agent alias must be deployed and active (check Bedrock console)
- **Check region**: Ensure agent is in the same region as `AWS_REGION`

### Timeouts/DNS Issues in VPC
- **Check VPC endpoints**: Ensure interface endpoints exist for `bedrock-runtime` and/or `bedrock-agent-runtime`
- **Check Private DNS**: Verify Private DNS is enabled on VPC endpoints
- **Check subnet**: If in private subnet, you MUST have VPC endpoints; public subnets can use internet gateway
- **Test DNS resolution**: `nslookup bedrock-runtime.<region>.amazonaws.com` should resolve to private IP if Private DNS enabled

### "Model not found" or "Model not accessible"
- **Check model ID**: Verify the model ID format (e.g., `anthropic.claude-3-sonnet-20240229-v1:0`)
- **Check region**: Some models are only available in specific regions
- **Request model access**: Some Bedrock models require explicit access request in AWS Console

---

## Quick Reference

```bash
# SSO (recommended)
aws sso login --profile bedrock-dev
export AWS_PROFILE=bedrock-dev
export AWS_REGION=us-west-2

# Access Keys
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION=us-west-2

# Verify credentials
aws sts get-caller-identity

# Run orchestrator - Direct Model
python scripts/orchestrator_unified.py run "<url>" \
  --name "MyFeature" \
  --config orchestrator.conf \
  --model "anthropic.claude-3-sonnet-20240229-v1:0"

# Run orchestrator - Bedrock Agent
python scripts/orchestrator_unified.py run "<url>" \
  --name "MyFeature" \
  --config orchestrator.conf \
  --agent-id "AGENT_ID" \
  --agent-alias-id "ALIAS_ID"
```

## Example: Using Bedrock Agent

```bash
# Set up environment
export AWS_PROFILE=bedrock-dev
export AWS_REGION=us-west-2
export BEDROCK_AGENT_ID="YOUR_AGENT_ID"
export BEDROCK_AGENT_ALIAS_ID="YOUR_ALIAS_ID"

# Or pass directly
python scripts/orchestrator_unified.py run "<confluence-url>" \
  --name "MyFeature" \
  --config orchestrator.conf \
  --agent-id "$BEDROCK_AGENT_ID" \
  --agent-alias-id "$BEDROCK_AGENT_ALIAS_ID"
```

