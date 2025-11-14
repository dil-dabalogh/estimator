# Environment Variables Configuration Guide

## Quick Answer

**Where do I set environment variables when deploying to AWS?**

You **don't set environment variables directly**. Instead, you set **SAM CloudFormation Parameters** during deployment, which are automatically converted to Lambda environment variables.

## Three Methods to Set Parameters

### Method 1: Interactive Mode (Recommended for First Deployment)

```bash
cd infrastructure
sam build
sam deploy --guided
```

SAM will prompt you for each parameter:

```
Parameter LLMProvider [openai]: bedrock
Parameter OpenAIApiKey []: (leave empty for Bedrock)
Parameter OpenAIModel [gpt-4]: (leave default)
Parameter AWSRegionBedrock [us-west-2]: us-west-2
Parameter BedrockModel [anthropic.claude-3-sonnet-20240229-v1:0]: (press Enter)
Parameter AtlassianURL []: https://your-company.atlassian.net/wiki
Parameter AtlassianEmail []: your-email@company.com
Parameter AtlassianToken []: your-api-token
```

After the first deployment, SAM saves these values to `samconfig.toml` for future deployments.

### Method 2: Command Line (Non-Interactive)

```bash
cd infrastructure
sam build
sam deploy \
  --template template.yaml \
  --stack-name estimation-tool-api \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LLMProvider=bedrock \
    AWSRegionBedrock=us-west-2 \
    BedrockModel=anthropic.claude-3-sonnet-20240229-v1:0 \
    OpenAIApiKey="" \
    AtlassianURL=https://your-company.atlassian.net/wiki \
    AtlassianEmail=your-email@company.com \
    AtlassianToken=your-atlassian-token
```

### Method 3: Configuration File

Create or edit `infrastructure/samconfig.toml`:

```toml
version = 0.1
[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "estimation-tool-api"
resolve_s3 = true
s3_prefix = "estimation-tool-api"
region = "us-west-2"
capabilities = "CAPABILITY_IAM"
parameter_overrides = [
  "LLMProvider=bedrock",
  "AWSRegionBedrock=us-west-2",
  "BedrockModel=anthropic.claude-3-sonnet-20240229-v1:0",
  "OpenAIApiKey=",
  "AtlassianURL=https://your-company.atlassian.net/wiki",
  "AtlassianEmail=your-email@company.com",
  "AtlassianToken=your-atlassian-token"
]
```

Then deploy:

```bash
cd infrastructure
sam build
sam deploy --config-file samconfig.toml
```

## Parameter to Environment Variable Mapping

| SAM Parameter | Lambda Environment Variable | Description | Example Value |
|---------------|---------------------------|-------------|---------------|
| `LLMProvider` | `LLM_PROVIDER` | LLM provider to use | `bedrock` or `openai` |
| `OpenAIApiKey` | `OPENAI_API_KEY` | OpenAI API key | `sk-...` (leave empty for Bedrock) |
| `OpenAIModel` | `OPENAI_MODEL` | OpenAI model name | `gpt-4` |
| `AWSRegionBedrock` | `AWS_REGION` | AWS region for Bedrock | `us-west-2` |
| `BedrockModel` | `BEDROCK_MODEL` | Bedrock model ID | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `AtlassianURL` | `ATLASSIAN_URL` | Confluence base URL | `https://company.atlassian.net/wiki` |
| `AtlassianEmail` | `ATLASSIAN_USER_EMAIL` | Atlassian user email | `user@company.com` |
| `AtlassianToken` | `ATLASSIAN_API_TOKEN` | Atlassian API token | Generated from Atlassian |

## How It Works

1. **You define Parameters** in `infrastructure/template.yaml` (lines 15-48)
2. **You set Parameter values** during deployment using one of the three methods above
3. **SAM creates CloudFormation stack** with your parameter values
4. **CloudFormation passes parameters** to Lambda as environment variables via the `Environment.Variables` section (lines 72-79 in template.yaml)
5. **Lambda function reads** environment variables at runtime using `os.getenv()` in Python

## Viewing Current Environment Variables

After deployment, you can view the Lambda function's environment variables:

```bash
# Get the function name
FUNCTION_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name estimation-tool-api \
  --query 'StackResources[?ResourceType==`AWS::Lambda::Function`].PhysicalResourceId' \
  --output text)

# View environment variables
aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --query 'Environment.Variables' \
  --output json
```

## Updating Environment Variables

To update environment variables after initial deployment:

### Option 1: Using SAM (Recommended)

```bash
cd infrastructure
sam deploy --parameter-overrides \
  LLMProvider=bedrock \
  BedrockModel=anthropic.claude-3-haiku-20240307-v1:0  # Changed to Haiku
```

### Option 2: Using AWS CLI (Direct Update)

```bash
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --environment "Variables={
    LLM_PROVIDER=bedrock,
    AWS_REGION=us-west-2,
    BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0,
    ATLASSIAN_URL=https://your-company.atlassian.net/wiki,
    ATLASSIAN_USER_EMAIL=user@company.com,
    ATLASSIAN_API_TOKEN=your-token
  }"
```

**Note**: Using SAM is recommended because it maintains consistency with your Infrastructure as Code.

## Common Issues

### Issue: "Where do I set environment variables in AWS Console?"

**Answer**: While you *can* manually edit Lambda environment variables in the AWS Console, **this is not recommended** because:
- Changes will be overwritten on next SAM deployment
- No version control or audit trail
- Inconsistent with Infrastructure as Code practices

Always set parameters through SAM deployment.

### Issue: "My changes to template.yaml Parameters aren't taking effect"

**Answer**: You need to redeploy after changing `template.yaml`:

```bash
cd infrastructure
sam build
sam deploy
```

If you previously saved parameters to `samconfig.toml`, SAM will use those. To change parameters, either:
- Edit `samconfig.toml` directly, or
- Run `sam deploy --guided` to re-enter parameters, or
- Use `--parameter-overrides` to override specific values

### Issue: "I'm getting 'Parameter validation failed' errors"

**Answer**: Ensure:
- All required parameters are provided
- Parameter values match allowed values (e.g., `LLMProvider` must be `openai` or `bedrock`)
- No typos in parameter names (they are case-sensitive)

## Security Best Practices

### For Production Deployments

1. **Use AWS Secrets Manager** instead of passing sensitive values as parameters:

```yaml
# In template.yaml, add permission to read secrets
Policies:
  - Statement:
    - Effect: Allow
      Action:
        - secretsmanager:GetSecretValue
      Resource: arn:aws:secretsmanager:*:*:secret:estimation-tool/*
```

2. **Store secrets in Secrets Manager**:

```bash
aws secretsmanager create-secret \
  --name estimation-tool/atlassian \
  --secret-string '{
    "url":"https://your-company.atlassian.net/wiki",
    "email":"your-email@company.com",
    "token":"your-token"
  }'
```

3. **Update code to read from Secrets Manager** instead of environment variables (see `backend/config.py`)

### For Development

- Use `samconfig.toml` but add it to `.gitignore`
- Or use environment variables in your shell before running `sam deploy`
- Never commit credentials to version control

## Related Documentation

- [Sysadminguide.md](./Sysadminguide.md) - Complete deployment guide
- [infrastructure/template.yaml](./infrastructure/template.yaml) - SAM template with parameter definitions
- [AWS SAM Parameters Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-specification-template-anatomy-globals.html)

