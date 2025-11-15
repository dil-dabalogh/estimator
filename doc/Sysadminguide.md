# System Administrator Guide

## Table of Contents

1. [Quick Start for AWS Bedrock](#quick-start-for-aws-bedrock)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [AWS Account Setup](#aws-account-setup)
5. [IAM Permissions Configuration](#iam-permissions-configuration)
6. [AWS Bedrock Configuration](#aws-bedrock-configuration)
7. [Backend Deployment](#backend-deployment)
8. [Frontend Deployment](#frontend-deployment)
9. [Network and VPC Considerations](#network-and-vpc-considerations)
10. [Security Configuration](#security-configuration)
11. [Monitoring and Observability](#monitoring-and-observability)
12. [Troubleshooting](#troubleshooting)
13. [Cost Optimization](#cost-optimization)

---

## Quick Start for AWS Bedrock

For experienced AWS administrators who want to deploy quickly with AWS Bedrock:

### 5-Minute Setup Checklist

1. **Enable Bedrock Model Access** (AWS Console):
   - Navigate to AWS Bedrock → Model access
   - Request access to "Anthropic Claude 3 Sonnet"
   - Wait for approval (usually instant)

2. **Verify AWS CLI is configured**:
   ```bash
   aws sts get-caller-identity
   aws bedrock list-foundation-models --region us-west-2
   ```

3. **Deploy with SAM** (environment variables are set via `--parameter-overrides`):
   ```bash
   cd infrastructure
   sam build --template template.yaml
   sam deploy --guided \
     --template template.yaml \
     --stack-name estimation-tool-api \
     --capabilities CAPABILITY_IAM \
     --parameter-overrides \
       LLMProvider=bedrock \
       BedrockRegion=us-west-2 \
       BedrockModel=anthropic.claude-3-sonnet-20240229-v1:0 \
       OpenAIApiKey="" \
       AtlassianURL=https://your-company.atlassian.net/wiki \
       AtlassianEmail=your-email@company.com \
       AtlassianToken=your-atlassian-token
   ```
   
   **Note**: The `--parameter-overrides` values become Lambda environment variables. Alternatively, use `sam deploy --guided` without the overrides and you'll be prompted for each parameter interactively.

4. **Note the API Gateway URL** from outputs and configure frontend

5. **Test the deployment**:
   ```bash
   curl https://YOUR_API_URL/health
   ```

For detailed setup instructions, continue reading below.

---

## Architecture Overview

### Component Interaction Flow

```
┌─────────────────┐
│   User Browser  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Frontend (S3 + CloudFront)                                 │
│  - React/TypeScript SPA                                      │
│  - Static hosting on S3                                      │
│  - Optional CloudFront CDN                                   │
└────────┬────────────────────────────────────────────────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────────────────────────────┐
│  API Gateway (HTTP API)                                      │
│  - REST endpoints                                            │
│  - CORS configuration                                        │
│  - Request routing                                           │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Lambda Function (Python 3.11)                              │
│  - FastAPI application via Mangum                            │
│  - 2048 MB memory, 900s timeout                             │
│  - Estimation logic & workflow orchestration                 │
│  ├─────────────────────────────────────────────────────────┤
│  │  IAM Execution Role                                      │
│  │  - CloudWatch Logs write                                 │
│  │  - Bedrock InvokeModel permission                        │
│  └─────────────────────────────────────────────────────────┘
└────┬────────────────────────────────┬────────────────────────┘
     │                                │
     │                                │
     ▼                                ▼
┌──────────────────────┐    ┌────────────────────────────────┐
│  AWS Bedrock         │    │  External Services             │
│  - Claude 3 Models   │    │  - Confluence API              │
│  - Model inference   │    │  - Jira API (via Atlassian)    │
│  - IAM-based auth    │    │  - HTTP/HTTPS requests         │
└──────────────────────┘    └────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  CloudWatch                                                   │
│  - Lambda logs & metrics                                      │
│  - Bedrock API call logs (via CloudTrail)                    │
│  - Performance monitoring                                     │
│  - Cost tracking                                              │
└──────────────────────────────────────────────────────────────┘
```

### Key Services Used

- **AWS Lambda**: Serverless compute for backend application
- **API Gateway**: HTTP API for REST endpoints
- **AWS Bedrock**: Managed LLM service (Claude models)
- **S3**: Static website hosting for frontend
- **CloudFront** (optional): CDN for frontend distribution
- **CloudWatch**: Logging and monitoring
- **IAM**: Identity and access management
- **CloudFormation/SAM**: Infrastructure as code deployment

---

## Prerequisites

### Required Tools and Access

1. **AWS Account**
   - Active AWS account with billing enabled
   - Access to create resources (Lambda, API Gateway, Bedrock, etc.)
   - AWS Bedrock service available in your region

2. **AWS CLI** (version 2.x recommended)
   ```bash
   # Check installation
   aws --version
   # Should output: aws-cli/2.x.x or higher
   
   # Configure credentials
   aws configure
   # Or use AWS SSO:
   aws configure sso
   ```

3. **AWS SAM CLI** (version 1.100+)
   ```bash
   # Check installation
   sam --version
   # Should output: SAM CLI, version 1.100.0 or higher
   
   # Install if needed:
   # macOS: brew install aws-sam-cli
   # Windows: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
   # Linux: Follow AWS documentation
   ```

4. **Python 3.11+**
   ```bash
   python3 --version
   # Should output: Python 3.11.x or higher
   ```

5. **Node.js 18+ and npm**
   ```bash
   node --version  # Should be v18.x or higher
   npm --version   # Should be 9.x or higher
   ```

6. **Atlassian API Access**
   - Atlassian instance URL (e.g., `https://company.atlassian.net/wiki`)
   - User email with API access
   - API token (generate at: https://id.atlassian.com/manage-profile/security/api-tokens)

7. **AWS Credentials Configuration**

   Choose one of the following methods:

   **Option A: IAM User with Access Keys**
   ```bash
   aws configure
   # Enter: AWS Access Key ID, Secret Access Key, region, output format
   ```

   **Option B: AWS SSO (Recommended for Organizations)**
   ```bash
   aws configure sso
   # Follow prompts for SSO start URL, region, account, role
   
   # Login when needed:
   aws sso login --profile your-profile-name
   
   # Set profile for session:
   export AWS_PROFILE=your-profile-name
   ```

   **Verify Configuration**
   ```bash
   # Check identity
   aws sts get-caller-identity
   
   # Output should show:
   # {
   #   "UserId": "AIDAXXXXXXXXXXXXXXXXX",
   #   "Account": "123456789012",
   #   "Arn": "arn:aws:iam::123456789012:user/your-name"
   # }
   ```

---

## AWS Account Setup

### Step 1: Verify AWS Service Availability

Before deploying, ensure the following services are available in your target AWS region:

1. **Check Bedrock Availability**
   ```bash
   # List available Bedrock models in your region
   aws bedrock list-foundation-models --region us-west-2
   
   # Verify Anthropic Claude models are listed
   aws bedrock list-foundation-models \
     --region us-west-2 \
     --query 'modelSummaries[?contains(modelId, `anthropic.claude`)].modelId' \
     --output table
   ```

   **Supported Bedrock Regions** (as of 2024):
   - `us-east-1` (US East, N. Virginia)
   - `us-west-2` (US West, Oregon) - **Recommended**
   - `ap-southeast-1` (Singapore)
   - `eu-central-1` (Frankfurt)
   - `eu-west-3` (Paris)
   
   Check AWS documentation for the latest regional availability.

2. **Check Service Quotas**
   ```bash
   # Check Lambda quotas
   aws service-quotas get-service-quota \
     --service-code lambda \
     --quota-code L-B99A9384 \
     --region us-west-2
   
   # Check Bedrock quotas (may require console access)
   ```

   **Default Lambda Limits** (sufficient for this application):
   - Concurrent executions: 1,000
   - Function timeout: 900 seconds (15 minutes)
   - Memory: Up to 10,240 MB

### Step 2: Prepare Deployment Artifacts Storage

SAM requires an S3 bucket for deployment artifacts:

```bash
# Create S3 bucket for SAM artifacts (one-time setup)
aws s3 mb s3://estimation-tool-sam-artifacts-$(aws sts get-caller-identity --query Account --output text) --region us-west-2

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
  --bucket estimation-tool-sam-artifacts-$(aws sts get-caller-identity --query Account --output text) \
  --versioning-configuration Status=Enabled
```

---

## IAM Permissions Configuration

### Overview

Two types of IAM permissions are required:

1. **Deployment User/Role**: Permissions to deploy the application (CloudFormation, Lambda, API Gateway, IAM role creation)
2. **Lambda Execution Role**: Permissions for the Lambda function to run (Bedrock access, CloudWatch Logs)

### Deployment User/Role Permissions

The user or role performing the deployment needs the following permissions:

**Managed Policies** (attach to deployment user/role):
- `AWSCloudFormationFullAccess` or equivalent CloudFormation permissions
- `AWSLambda_FullAccess` or equivalent Lambda permissions
- `AmazonAPIGatewayAdministrator` or equivalent API Gateway permissions
- `IAMFullAccess` (required for SAM to create execution role) or limited IAM role creation permissions

**Minimal Custom Policy** (if you prefer least privilege):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:GetTemplateSummary",
        "cloudformation:ListStackResources"
      ],
      "Resource": "arn:aws:cloudformation:*:*:stack/estimation-tool-api/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:DeleteFunction",
        "lambda:GetFunction",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:ListTags",
        "lambda:TagResource",
        "lambda:UntagResource"
      ],
      "Resource": "arn:aws:lambda:*:*:function:estimation-tool-api-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "apigateway:POST",
        "apigateway:GET",
        "apigateway:PATCH",
        "apigateway:DELETE",
        "apigateway:PUT"
      ],
      "Resource": "arn:aws:apigateway:*::/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy"
      ],
      "Resource": "arn:aws:iam::*:role/estimation-tool-api-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::estimation-tool-sam-artifacts-*",
        "arn:aws:s3:::estimation-tool-sam-artifacts-*/*",
        "arn:aws:s3:::aws-sam-cli-managed-default-*",
        "arn:aws:s3:::aws-sam-cli-managed-default-*/*"
      ]
    }
  ]
}
```

**Attach the Policy**:
```bash
# If using IAM user
aws iam put-user-policy \
  --user-name your-deployment-user \
  --policy-name EstimationToolDeploymentPolicy \
  --policy-document file://deployment-policy.json

# Or create as managed policy
aws iam create-policy \
  --policy-name EstimationToolDeploymentPolicy \
  --policy-document file://deployment-policy.json
```

### Lambda Execution Role Permissions

The SAM template automatically creates the Lambda execution role, but you need to ensure it has the correct permissions. The template should include (and already does):

**Required Permissions**:

1. **CloudWatch Logs** (for application logging):
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "logs:CreateLogGroup",
       "logs:CreateLogStream",
       "logs:PutLogEvents"
     ],
     "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/estimation-tool-api-*:*"
   }
   ```

2. **AWS Bedrock** (for LLM inference):
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "bedrock:InvokeModel"
     ],
     "Resource": [
       "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
       "arn:aws:bedrock:*::foundation-model/amazon.titan-*"
     ]
   }
   ```

3. **AWS Bedrock Agent** (optional, only if using agents):
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "bedrock:InvokeAgent"
     ],
     "Resource": "arn:aws:bedrock:*:*:agent-alias/*"
   }
   ```

**Verification**: After deployment, verify the execution role:

```bash
# Get the Lambda function's role ARN
ROLE_ARN=$(aws lambda get-function \
  --function-name estimation-tool-api-EstimationFunction-XXXXX \
  --query 'Configuration.Role' \
  --output text)

# List attached policies
aws iam list-attached-role-policies \
  --role-name $(echo $ROLE_ARN | cut -d'/' -f2)

# Check inline policies
aws iam list-role-policies \
  --role-name $(echo $ROLE_ARN | cut -d'/' -f2)
```

**Update SAM Template** (if needed):

Add this to the Lambda function resource in `infrastructure/template.yaml`:

```yaml
EstimationFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... existing properties ...
    Policies:
      - AWSLambdaBasicExecutionRole
      - Statement:
          - Effect: Allow
            Action:
              - bedrock:InvokeModel
            Resource:
              - arn:aws:bedrock:*::foundation-model/anthropic.claude-*
              - arn:aws:bedrock:*::foundation-model/amazon.titan-*
          - Effect: Allow
            Action:
              - bedrock:InvokeAgent
            Resource:
              - arn:aws:bedrock:*:*:agent-alias/*
```

---

## AWS Bedrock Configuration

### Step 1: Enable Model Access

AWS Bedrock requires explicit model access grants before you can use foundation models.

**Using AWS Console** (Recommended for first-time setup):

1. **Navigate to Bedrock Console**:
   - Sign in to AWS Console
   - Go to the AWS Bedrock service
   - Select your target region (e.g., `us-west-2`)

2. **Request Model Access**:
   - Click on "Model access" in the left sidebar
   - Click "Manage model access" or "Request model access"
   - Find "Anthropic" section and expand it
   - Select the following models:
     - ✓ Anthropic Claude 3 Sonnet
     - ✓ Anthropic Claude 3 Haiku (optional, for faster/cheaper responses)
     - ✓ Anthropic Claude 3 Opus (optional, for highest quality)
   - Click "Request model access" or "Save changes"

3. **Wait for Approval**:
   - Most models (especially Claude) are approved instantly
   - Some models may require use-case submission and approval within 1-2 business days
   - You'll see "Access granted" status when ready

4. **Verify Access**:
   ```bash
   # List models you have access to
   aws bedrock list-foundation-models \
     --region us-west-2 \
     --query 'modelSummaries[?modelId contains @, `anthropic.claude`]' \
     --output table
   ```

**Using AWS CLI** (Alternative):

Model access requests cannot be automated via CLI. Use the console for initial setup.

### Step 2: Choose Your Model

**Recommended Models for This Application**:

| Model ID | Model Name | Context Window | Best For | Cost (Relative) |
|----------|-----------|----------------|----------|-----------------|
| `anthropic.claude-3-sonnet-20240229-v1:0` | Claude 3 Sonnet | 200K tokens | **Recommended**: Balanced performance and cost | Medium |
| `anthropic.claude-3-haiku-20240307-v1:0` | Claude 3 Haiku | 200K tokens | Fast responses, lower cost | Low |
| `anthropic.claude-3-opus-20240229-v1:0` | Claude 3 Opus | 200K tokens | Highest quality, complex reasoning | High |

**Default Configuration**: The template defaults to Claude 3 Sonnet, which provides excellent quality for technical estimation tasks.

**To Find Latest Model IDs**:
```bash
# List all available Anthropic Claude models
aws bedrock list-foundation-models \
  --region us-west-2 \
  --by-provider anthropic \
  --query 'modelSummaries[].{ModelId:modelId, Name:modelName}' \
  --output table

# Get detailed model information
aws bedrock get-foundation-model \
  --model-identifier anthropic.claude-3-sonnet-20240229-v1:0 \
  --region us-west-2
```

### Step 3: Model Configuration Parameters

The application supports the following Bedrock configurations:

**Environment Variables** (set during deployment):

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LLM_PROVIDER` | LLM provider type | `openai` | `bedrock` |
| `BEDROCK_REGION` | AWS region for Bedrock (optional) | Lambda's AWS_REGION | `us-west-2` |
| `BEDROCK_MODEL` | Bedrock model ID | `anthropic.claude-3-sonnet-20240229-v1:0` | See table above |
| `BEDROCK_TEMPERATURE` | Sampling temperature (0.0-1.0) | `0.2` | `0.2` (deterministic), `0.7` (creative) |
| `BEDROCK_AGENT_ID` | (Optional) Bedrock Agent ID | - | `AGENT123ABC` |
| `BEDROCK_AGENT_ALIAS_ID` | (Optional) Agent Alias ID | - | `ALIAS456DEF` |

**Temperature Guidelines**:
- `0.0-0.3`: Deterministic, consistent responses (recommended for estimation)
- `0.4-0.7`: Balanced creativity and consistency
- `0.8-1.0`: Highly creative, variable responses (not recommended for this use case)

### Step 4: Bedrock Agents (Optional Advanced Configuration)

Bedrock Agents provide enhanced capabilities with action groups, knowledge bases, and function calling. Use this if you need:
- Integration with additional AWS services
- Custom function calling
- Knowledge base integration
- Multi-step reasoning workflows

**Agent Setup** (if needed):

1. **Create Agent in Bedrock Console**:
   - Navigate to Bedrock → Agents
   - Click "Create agent"
   - Configure agent with foundation model
   - Add action groups and knowledge bases as needed
   - Save agent

2. **Create Agent Alias**:
   - In the agent details, go to "Aliases"
   - Click "Create alias"
   - Enter alias name (e.g., `prod`, `v1`)
   - Deploy the alias
   - Note the Agent ID and Alias ID

3. **Configure in Deployment**:
   ```bash
   # Deploy with agent configuration
   sam deploy --guided \
     --parameter-overrides \
       LLMProvider=bedrock \
       BedrockRegion=us-west-2 \
       BedrockAgentId=YOUR_AGENT_ID \
       BedrockAgentAliasId=YOUR_ALIAS_ID
   ```

**Note**: When using agents, the `BEDROCK_MODEL` parameter is optional (the agent's configured model is used).

### Step 5: Regional Considerations

**Latency Optimization**:
- Deploy Lambda and use Bedrock in the same region
- Choose region closest to your users
- US West 2 (Oregon) typically has the broadest Bedrock model availability

**Compliance and Data Residency**:
- Check your organization's data residency requirements
- Bedrock processes data within the specified region
- AWS does not use Bedrock API data to train models (as of 2024)

**Multi-Region Deployment**:
If you need multi-region deployment:
1. Deploy separate stacks in each region
2. Use Route 53 or CloudFront for global routing
3. Ensure model access is enabled in all target regions

---

## Backend Deployment

### Pre-Deployment Checklist

Before deploying, ensure you have completed:

- [ ] AWS CLI configured with valid credentials
- [ ] AWS SAM CLI installed
- [ ] Target region supports AWS Bedrock
- [ ] Bedrock model access granted (Claude models)
- [ ] IAM permissions configured for deployment
- [ ] Atlassian credentials ready (URL, email, API token)
- [ ] S3 bucket for SAM artifacts created (or will be auto-created)

### Where Do I Set Environment Variables?

**Quick Answer**: You don't set environment variables directly. Instead, you set **SAM template parameters** during deployment, which SAM automatically converts to Lambda environment variables.

**Three Ways to Set Parameters**:

1. **Interactive (Recommended for first time)**:
   ```bash
   sam deploy --guided
   # You'll be prompted for each parameter
   ```

2. **Command Line**:
   ```bash
   sam deploy --parameter-overrides \
     LLMProvider=bedrock \
     BedrockRegion=us-west-2 \
     AtlassianURL=https://... \
     AtlassianEmail=user@example.com \
     AtlassianToken=xxx
   ```

3. **Configuration File** (`infrastructure/samconfig.toml`):
   ```toml
   parameter_overrides = [
     "LLMProvider=bedrock",
     "BedrockRegion=us-west-2",
     "AtlassianURL=https://...",
     ...
   ]
   ```

See Step 3 below for detailed examples of each method.

### Step 1: Prepare Environment

```bash
# Clone or navigate to project directory
cd /path/to/estimation-project

# Verify backend dependencies
cd backend
pip install -r requirements.txt --dry-run
cd ..

# Navigate to infrastructure directory
cd infrastructure
```

### Step 2: Build the Application

```bash
# Build with SAM
sam build --template template.yaml

# Output should show:
# Building codeuri: ../backend
# Running PythonPipBuilder:ResolveDependencies
# Build Succeeded
```

**Troubleshooting Build Issues**:
- If build fails, ensure Python 3.11 is available
- Check that all dependencies in `backend/requirements.txt` are valid
- Use `--use-container` flag if local Python version differs:
  ```bash
  sam build --template template.yaml --use-container
  ```

### Step 3: Deploy with AWS Bedrock Configuration

**Understanding Environment Variables**

The SAM template accepts **Parameters** (defined in `infrastructure/template.yaml`) that are automatically converted to Lambda environment variables. You can set these parameters in three ways:

1. **Interactive mode** (`--guided`) - prompts for each parameter
2. **Command-line** (`--parameter-overrides`) - pass parameters directly
3. **Configuration file** (`samconfig.toml`) - store parameters for reuse

**Option A: Guided Deployment (First Time) - Recommended**

This interactive mode prompts you for all required parameters:

```bash
sam deploy --guided \
  --template template.yaml \
  --stack-name estimation-tool-api \
  --capabilities CAPABILITY_IAM
```

You will be prompted for parameters. Enter the following for Bedrock:

```
Parameter LLMProvider [openai]: bedrock
Parameter OpenAIApiKey []: (leave empty, press Enter)
Parameter OpenAIModel [gpt-4]: (leave default or press Enter)
Parameter BedrockRegion [us-west-2]: us-west-2
Parameter BedrockModel [anthropic.claude-3-sonnet-20240229-v1:0]: (press Enter for default)
Parameter AtlassianURL []: https://your-company.atlassian.net/wiki
Parameter AtlassianEmail []: your-email@company.com
Parameter AtlassianToken []: your-atlassian-api-token
```

SAM will then prompt:
```
Confirm changes before deploy [Y/n]: Y
Allow SAM CLI IAM role creation [Y/n]: Y
Save arguments to configuration file [Y/n]: Y
SAM configuration file [samconfig.toml]: (press Enter)
SAM configuration environment [default]: (press Enter)
```

**Note**: When you save arguments to the configuration file, subsequent deployments will use those saved values automatically.

**Option B: Non-Interactive Deployment (Subsequent Deploys)**

After first deployment, use saved configuration:

```bash
sam deploy --template template.yaml
```

Or specify parameters explicitly:

```bash
sam deploy \
  --template template.yaml \
  --stack-name estimation-tool-api \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LLMProvider=bedrock \
    BedrockRegion=us-west-2 \
    BedrockModel=anthropic.claude-3-sonnet-20240229-v1:0 \
    OpenAIApiKey="" \
    AtlassianURL=https://your-company.atlassian.net/wiki \
    AtlassianEmail=your-email@company.com \
    AtlassianToken=your-atlassian-api-token \
  --no-confirm-changeset
```

**Option C: Using samconfig.toml**

Create or update `infrastructure/samconfig.toml`:

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
  "BedrockRegion=us-west-2",
  "BedrockModel=anthropic.claude-3-sonnet-20240229-v1:0",
  "OpenAIApiKey=",
  "AtlassianURL=https://your-company.atlassian.net/wiki",
  "AtlassianEmail=your-email@company.com",
  "AtlassianToken=your-atlassian-api-token"
]
```

Then deploy:
```bash
sam deploy --config-file samconfig.toml
```

**Summary: Where Environment Variables Are Set**

| Parameter Name | Environment Variable in Lambda | How to Set |
|----------------|-------------------------------|------------|
| `LLMProvider` | `LLM_PROVIDER` | `--guided` prompt or `--parameter-overrides LLMProvider=bedrock` |
| `OpenAIApiKey` | `OPENAI_API_KEY` | `--guided` prompt or `--parameter-overrides OpenAIApiKey=sk-xxx` |
| `OpenAIModel` | `OPENAI_MODEL` | `--guided` prompt or `--parameter-overrides OpenAIModel=gpt-4` |
| `BedrockRegion` | `BEDROCK_REGION` | `--guided` prompt or `--parameter-overrides BedrockRegion=us-west-2` |
| `BedrockModel` | `BEDROCK_MODEL` | `--guided` prompt or `--parameter-overrides BedrockModel=anthropic.claude-3-sonnet-20240229-v1:0` |
| `AtlassianURL` | `ATLASSIAN_URL` | `--guided` prompt or `--parameter-overrides AtlassianURL=https://...` |
| `AtlassianEmail` | `ATLASSIAN_USER_EMAIL` | `--guided` prompt or `--parameter-overrides AtlassianEmail=user@example.com` |
| `AtlassianToken` | `ATLASSIAN_API_TOKEN` | `--guided` prompt or `--parameter-overrides AtlassianToken=xxx` |

**Key Points**:
- Parameters are defined in `infrastructure/template.yaml` (lines 11-44)
- They are mapped to Lambda environment variables in the `EstimationFunction` resource (lines 65-74)
- You don't set environment variables directly; you set **SAM parameters** which become environment variables
- The mapping happens automatically during deployment

### Step 4: Monitor Deployment

SAM will display progress as it creates resources:

```
Deploying with following values
===============================
Stack name                   : estimation-tool-api
Region                       : us-west-2
Confirm changeset            : True
Capabilities                 : ["CAPABILITY_IAM"]
Parameter overrides          : {"LLMProvider": "bedrock", ...}

Initiating deployment
=====================

CloudFormation stack changeset
-------------------------------------------------
Operation    LogicalResourceId                ResourceType
-------------------------------------------------
+ Add        EstimationApi                    AWS::Serverless::HttpApi
+ Add        EstimationFunctionRole           AWS::IAM::Role
+ Add        EstimationFunction               AWS::Serverless::Function
-------------------------------------------------

Changeset created successfully. 

Deploy this changeset? [y/N]: y

2024-01-15 10:30:00 - Waiting for stack create/update to complete

CloudFormation events from stack operations
-------------------------------------------------
ResourceStatus               ResourceType                 LogicalResourceId
-------------------------------------------------
CREATE_IN_PROGRESS          AWS::IAM::Role               EstimationFunctionRole
CREATE_COMPLETE             AWS::IAM::Role               EstimationFunctionRole
CREATE_IN_PROGRESS          AWS::Lambda::Function        EstimationFunction
CREATE_COMPLETE             AWS::Lambda::Function        EstimationFunction
CREATE_IN_PROGRESS          AWS::ApiGatewayV2::Api       EstimationApi
CREATE_COMPLETE             AWS::ApiGatewayV2::Api       EstimationApi
CREATE_COMPLETE             AWS::CloudFormation::Stack   estimation-tool-api
-------------------------------------------------

Successfully created/updated stack - estimation-tool-api in us-west-2
```

### Step 5: Note the API Gateway URL

After successful deployment, SAM outputs the API endpoint:

```
CloudFormation outputs from deployed stack
-------------------------------------------------
Outputs
-------------------------------------------------
Key                 EstimationApiUrl
Description         API Gateway endpoint URL
Value               https://abc123xyz.execute-api.us-west-2.amazonaws.com
-------------------------------------------------
```

**Save this URL** - you'll need it for frontend configuration.

You can also retrieve it later:
```bash
aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text
```

### Step 6: Post-Deployment Verification

**Test Lambda Function**:
```bash
# Get function name
FUNCTION_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name estimation-tool-api \
  --query 'StackResources[?ResourceType==`AWS::Lambda::Function`].PhysicalResourceId' \
  --output text)

# Check function configuration
aws lambda get-function-configuration --function-name $FUNCTION_NAME

# Verify environment variables include Bedrock settings
aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --query 'Environment.Variables' \
  --output json
```

**Test API Endpoint**:
```bash
# Get API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text)

# Test health endpoint (if available)
curl $API_URL/health

# Or test root endpoint
curl $API_URL/
```

**Check CloudWatch Logs**:
```bash
# Get log group name
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

# Tail recent logs
aws logs tail $LOG_GROUP --follow

# Or view in console
echo "View logs at: https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups/log-group/$LOG_GROUP"
```

**Verify Bedrock Connectivity**:

Invoke the Lambda function with a test event to verify Bedrock access:

```bash
# Create test event
cat > test-event.json <<EOF
{
  "httpMethod": "GET",
  "path": "/health",
  "headers": {},
  "body": ""
}
EOF

# Invoke function
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload file://test-event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# Check response
cat response.json

# Check logs for any Bedrock initialization messages
aws logs tail $LOG_GROUP --since 5m
```

If you see errors related to Bedrock:
- Check that model access is granted
- Verify IAM execution role has `bedrock:InvokeModel` permission
- Ensure the region and model ID are correct

### Alternative: Manual Deployment (Without SAM)

If SAM is not available, you can deploy manually:

1. **Create Lambda deployment package**:
   ```bash
   cd backend
   pip install -r requirements.txt -t package/
   cp *.py package/
   cd package
   zip -r ../lambda-deployment.zip .
   cd ..
   ```

2. **Create IAM execution role**:
   ```bash
   # Create trust policy
   cat > trust-policy.json <<EOF
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"Service": "lambda.amazonaws.com"},
       "Action": "sts:AssumeRole"
     }]
   }
   EOF
   
   # Create role
   aws iam create-role \
     --role-name EstimationToolLambdaRole \
     --assume-role-policy-document file://trust-policy.json
   
   # Attach basic execution policy
   aws iam attach-role-policy \
     --role-name EstimationToolLambdaRole \
     --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
   
   # Create and attach Bedrock policy
   cat > bedrock-policy.json <<EOF
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["bedrock:InvokeModel"],
       "Resource": "arn:aws:bedrock:*::foundation-model/*"
     }]
   }
   EOF
   
   aws iam put-role-policy \
     --role-name EstimationToolLambdaRole \
     --policy-name BedrockAccess \
     --policy-document file://bedrock-policy.json
   ```

3. **Create Lambda function**:
   ```bash
   aws lambda create-function \
     --function-name estimation-tool-api \
     --runtime python3.11 \
     --role arn:aws:iam::YOUR_ACCOUNT_ID:role/EstimationToolLambdaRole \
     --handler lambda_handler.handler \
     --zip-file fileb://lambda-deployment.zip \
     --timeout 900 \
     --memory-size 2048 \
     --environment Variables='{
       "LLM_PROVIDER":"bedrock",
       "AWS_REGION":"us-west-2",
       "BEDROCK_MODEL":"anthropic.claude-3-sonnet-20240229-v1:0",
       "ATLASSIAN_URL":"https://your-company.atlassian.net/wiki",
       "ATLASSIAN_USER_EMAIL":"your-email@company.com",
       "ATLASSIAN_API_TOKEN":"your-token"
     }'
   ```

4. **Create API Gateway HTTP API**:
   ```bash
   # Create API
   API_ID=$(aws apigatewayv2 create-api \
     --name estimation-tool-api \
     --protocol-type HTTP \
     --cors-configuration AllowOrigins='*',AllowMethods='GET,POST,OPTIONS',AllowHeaders='*' \
     --query 'ApiId' \
     --output text)
   
   # Create integration
   INTEGRATION_ID=$(aws apigatewayv2 create-integration \
     --api-id $API_ID \
     --integration-type AWS_PROXY \
     --integration-uri arn:aws:lambda:us-west-2:YOUR_ACCOUNT_ID:function:estimation-tool-api \
     --payload-format-version 2.0 \
     --query 'IntegrationId' \
     --output text)
   
   # Create route
   aws apigatewayv2 create-route \
     --api-id $API_ID \
     --route-key 'ANY /{proxy+}' \
     --target integrations/$INTEGRATION_ID
   
   # Create default stage
   aws apigatewayv2 create-stage \
     --api-id $API_ID \
     --stage-name '$default' \
     --auto-deploy
   
   # Add Lambda permission
   aws lambda add-permission \
     --function-name estimation-tool-api \
     --statement-id apigateway-invoke \
     --action lambda:InvokeFunction \
     --principal apigateway.amazonaws.com \
     --source-arn "arn:aws:execute-api:us-west-2:YOUR_ACCOUNT_ID:$API_ID/*/*"
   
   # Get API endpoint
   echo "API URL: https://$API_ID.execute-api.us-west-2.amazonaws.com"
   ```

---

## Frontend Deployment

### Step 1: Configure Environment

Create `frontend/.env` with the API URL from backend deployment:

```bash
cd frontend

# Create .env file
cat > .env <<EOF
VITE_API_BASE_URL=https://YOUR_API_ID.execute-api.us-west-2.amazonaws.com
EOF
```

Replace `YOUR_API_ID` with the actual API Gateway ID from the backend deployment output.

### Step 2: Build Frontend

```bash
# Install dependencies
npm install

# Build for production
npm run build

# Output will be in the 'dist' directory
```

**Verify Build**:
```bash
ls -lh dist/
# Should show index.html, assets/, and other static files
```

### Step 3: Deploy to S3

```bash
# Create S3 bucket (must be globally unique)
BUCKET_NAME="estimation-tool-frontend-$(aws sts get-caller-identity --query Account --output text)"
aws s3 mb s3://$BUCKET_NAME --region us-west-2

# Enable static website hosting
aws s3 website s3://$BUCKET_NAME \
  --index-document index.html \
  --error-document index.html

# Upload build artifacts
aws s3 sync dist/ s3://$BUCKET_NAME --delete

# Make bucket publicly readable
cat > bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
  }]
}
EOF

aws s3api put-bucket-policy \
  --bucket $BUCKET_NAME \
  --policy file://bucket-policy.json

# Get website URL
echo "Frontend URL: http://$BUCKET_NAME.s3-website-us-west-2.amazonaws.com"
```

**Access the Application**:
```
http://estimation-tool-frontend-123456789012.s3-website-us-west-2.amazonaws.com
```

### Step 4: Optional - CloudFront Distribution

For better performance, HTTPS, and custom domain:

```bash
# Create CloudFront distribution
cat > cloudfront-config.json <<EOF
{
  "CallerReference": "estimation-tool-$(date +%s)",
  "Comment": "Estimation Tool Frontend",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "S3-$BUCKET_NAME",
      "DomainName": "$BUCKET_NAME.s3-website-us-west-2.amazonaws.com",
      "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "http-only"
      }
    }]
  },
  "DefaultRootObject": "index.html",
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-$BUCKET_NAME",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "Compress": true,
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {"Forward": "none"}
    },
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000
  },
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [{
      "ErrorCode": 404,
      "ResponsePagePath": "/index.html",
      "ResponseCode": "200",
      "ErrorCachingMinTTL": 300
    }]
  }
}
EOF

# Create distribution
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json

# Note: CloudFront deployment takes 10-15 minutes
# Get distribution domain name from output or console
```

**Custom Domain** (optional):
1. Request SSL certificate in ACM (us-east-1 region for CloudFront)
2. Add alternate domain names (CNAMEs) to CloudFront distribution
3. Update Route 53 or your DNS provider with CNAME/Alias record

### Frontend Update Workflow

To update the frontend after changes:

```bash
cd frontend

# Make your changes...

# Rebuild
npm run build

# Sync to S3
aws s3 sync dist/ s3://$BUCKET_NAME --delete

# If using CloudFront, invalidate cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

---

## Network and VPC Considerations

### Default Configuration (Recommended)

By default, Lambda functions run in an AWS-managed VPC with:
- Full internet access
- Access to all AWS services via public endpoints
- No additional networking configuration required

**This is the recommended configuration** for this application because:
- Lambda can access Bedrock via public endpoints
- Lambda can access external Atlassian APIs
- No VPC endpoint costs
- Simpler setup and maintenance

### VPC Deployment (Advanced)

If your organization requires Lambda to run in a specific VPC (e.g., for compliance, network isolation, or access to private resources):

#### Requirements

1. **VPC with at least 2 private subnets** (in different AZs for high availability)
2. **NAT Gateway or NAT Instance** (for outbound internet access to Atlassian API)
3. **VPC Interface Endpoints** for AWS services:
   - `com.amazonaws.<region>.bedrock-runtime` (required)
   - `com.amazonaws.<region>.bedrock-agent-runtime` (if using agents)
   - `com.amazonaws.<region>.logs` (recommended for CloudWatch)

#### VPC Endpoint Setup

**Create Bedrock Runtime Endpoint**:

```bash
# Get your VPC and subnet IDs
VPC_ID="vpc-xxxxxxxx"
SUBNET_IDS="subnet-aaaaaaaa,subnet-bbbbbbbb"
SECURITY_GROUP_ID="sg-xxxxxxxx"

# Create VPC endpoint for Bedrock Runtime
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-west-2.bedrock-runtime \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $SECURITY_GROUP_ID \
  --private-dns-enabled

# Create VPC endpoint for Bedrock Agent Runtime (if using agents)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-west-2.bedrock-agent-runtime \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $SECURITY_GROUP_ID \
  --private-dns-enabled

# Create VPC endpoint for CloudWatch Logs (recommended)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-west-2.logs \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $SECURITY_GROUP_ID \
  --private-dns-enabled
```

#### Security Group Configuration

The security group for VPC endpoints must allow:

```json
{
  "IpPermissions": [
    {
      "IpProtocol": "tcp",
      "FromPort": 443,
      "ToPort": 443,
      "IpRanges": [{"CidrIp": "10.0.0.0/16", "Description": "VPC CIDR"}]
    }
  ]
}
```

Or via CLI:
```bash
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.0.0/16
```

#### Update SAM Template for VPC

Add VPC configuration to the Lambda function in `infrastructure/template.yaml`:

```yaml
EstimationFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... existing properties ...
    VpcConfig:
      SubnetIds:
        - subnet-aaaaaaaa
        - subnet-bbbbbbbb
      SecurityGroupIds:
        - sg-xxxxxxxx
```

**Important**: When Lambda is in a VPC:
- Add `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface` permissions to execution role
- Ensure NAT Gateway or NAT Instance exists for internet access (Atlassian API calls)
- Cold starts will be slower (ENI attachment takes 10-30 seconds)

#### Private DNS Verification

Verify that Private DNS is enabled on VPC endpoints:

```bash
# List VPC endpoints
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'VpcEndpoints[?ServiceName contains `bedrock`].[VpcEndpointId,ServiceName,PrivateDnsEnabled]' \
  --output table

# Private DNS must be 'True' for endpoints to work correctly
```

**Testing from Lambda**:

After deployment, check CloudWatch Logs for Bedrock connectivity. If you see timeout errors:
1. Verify VPC endpoints exist and Private DNS is enabled
2. Check security groups allow port 443
3. Verify route tables include endpoints
4. Test DNS resolution from Lambda (using test invocation with `nslookup` or similar)

### Network Architecture Diagrams

**Default (No VPC)**:
```
Lambda (AWS-managed VPC)
  │
  ├─→ Bedrock (public endpoint via internet)
  ├─→ Atlassian API (public internet)
  └─→ CloudWatch Logs (AWS backbone)
```

**With VPC and Endpoints**:
```
Lambda (Private Subnets)
  │
  ├─→ VPC Endpoint (bedrock-runtime) ──→ Bedrock
  ├─→ VPC Endpoint (logs) ──→ CloudWatch Logs
  └─→ NAT Gateway ──→ Internet Gateway ──→ Atlassian API
```

### Cost Considerations

**VPC Endpoint Costs**:
- Interface Endpoint: ~$7.20/month per endpoint per AZ
- Data processing: ~$0.01/GB
- For 2 AZs with Bedrock + Logs endpoints: ~$28.80/month minimum

**NAT Gateway Costs**:
- ~$32.40/month per NAT Gateway
- Data processing: ~$0.045/GB

**Recommendation**: Use default (no VPC) unless you have specific requirements.

---

## Security Configuration

### Secrets Management

**Never store sensitive credentials in code or environment variables visible in console.**

#### Option 1: AWS Secrets Manager (Recommended)

**Store Atlassian Credentials**:
```bash
# Create secret
aws secretsmanager create-secret \
  --name estimation-tool/atlassian \
  --description "Atlassian API credentials" \
  --secret-string '{
    "url":"https://your-company.atlassian.net/wiki",
    "email":"your-email@company.com",
    "token":"your-atlassian-api-token"
  }' \
  --region us-west-2

# Get secret ARN (for reference)
aws secretsmanager describe-secret \
  --secret-id estimation-tool/atlassian \
  --query 'ARN' \
  --output text
```

**Update Lambda to Use Secrets**:

1. Add Secrets Manager permission to Lambda execution role:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "secretsmanager:GetSecretValue"
     ],
     "Resource": "arn:aws:secretsmanager:us-west-2:*:secret:estimation-tool/*"
   }
   ```

2. Update `backend/config.py` to retrieve from Secrets Manager:
   ```python
   import boto3
   import json
   
   def load_config() -> AppConfig:
       # ... existing code ...
       
       # Load Atlassian credentials from Secrets Manager
       if os.getenv("USE_SECRETS_MANAGER", "false").lower() == "true":
           secrets_client = boto3.client('secretsmanager', region_name=os.getenv("AWS_REGION"))
           secret_response = secrets_client.get_secret_value(SecretId="estimation-tool/atlassian")
           secret_data = json.loads(secret_response['SecretString'])
           
           atlassian_url = secret_data.get("url")
           atlassian_email = secret_data.get("email")
           atlassian_token = secret_data.get("token")
       else:
           # Fallback to environment variables
           atlassian_url = os.getenv("ATLASSIAN_URL")
           atlassian_email = os.getenv("ATLASSIAN_USER_EMAIL")
           atlassian_token = os.getenv("ATLASSIAN_API_TOKEN")
       
       # ... rest of config ...
   ```

3. Update SAM template to set environment variable:
   ```yaml
   Environment:
     Variables:
       USE_SECRETS_MANAGER: "true"
       # Remove ATLASSIAN_URL, ATLASSIAN_USER_EMAIL, ATLASSIAN_API_TOKEN
   ```

#### Option 2: AWS Systems Manager Parameter Store

Alternative to Secrets Manager (no additional cost for standard parameters):

```bash
# Store parameters
aws ssm put-parameter \
  --name /estimation-tool/atlassian/url \
  --value "https://your-company.atlassian.net/wiki" \
  --type String

aws ssm put-parameter \
  --name /estimation-tool/atlassian/email \
  --value "your-email@company.com" \
  --type String

aws ssm put-parameter \
  --name /estimation-tool/atlassian/token \
  --value "your-atlassian-api-token" \
  --type SecureString
```

### IAM Best Practices

1. **Principle of Least Privilege**:
   - Lambda execution role should only have permissions it needs
   - Limit Bedrock resource access to specific model ARNs
   - Use resource-based policies where applicable

2. **Separate Roles**:
   - Deployment role (for SAM/CloudFormation)
   - Lambda execution role (for runtime)
   - Do not reuse admin roles

3. **Condition Keys** (optional for enhanced security):
   ```json
   {
     "Effect": "Allow",
     "Action": "bedrock:InvokeModel",
     "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
     "Condition": {
       "StringEquals": {
         "aws:RequestedRegion": "us-west-2"
       }
     }
   }
   ```

4. **MFA for Deployment** (recommended):
   - Require MFA for deployment user/role
   - Use AWS SSO with MFA enforcement

### API Gateway Security

**Throttling** (prevent abuse):
```bash
# Set throttling limits on API Gateway stage
API_ID=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text | cut -d'/' -f3 | cut -d'.' -f1)

aws apigatewayv2 update-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --throttle-settings RateLimit=100,BurstLimit=200
```

**API Keys** (optional, for authenticated access):
1. Create API key in API Gateway console
2. Create usage plan with throttle limits
3. Associate API key with usage plan
4. Update frontend to include API key in headers

**AWS WAF** (optional, for additional protection):
```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name estimation-tool-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json \
  --region us-west-2

# Associate with API Gateway
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-west-2:ACCOUNT:regional/webacl/estimation-tool-waf/ID \
  --resource-arn arn:aws:apigateway:us-west-2::/restapis/$API_ID/stages/$default
```

### Data Privacy and Compliance

**AWS Bedrock Data Handling**:
- AWS does not use customer data from Bedrock API calls to train foundation models
- Data is processed within the specified AWS region
- Data is not stored by Bedrock after processing (ephemeral)

**Opt-Out Configuration**:
No additional configuration is needed. Bedrock has data privacy protections by default.

**Regional Compliance**:
- Choose regions that meet your data residency requirements
- Consult AWS Compliance documentation for certifications (GDPR, SOC 2, etc.)

**Audit Logging**:
Enable CloudTrail to log all Bedrock API calls:

```bash
# CloudTrail should already be enabled in most AWS accounts
# Verify Bedrock events are captured:
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::Bedrock::Model \
  --max-results 10
```

### SSL/TLS

- API Gateway provides SSL/TLS by default (AWS-managed certificates)
- CloudFront provides SSL/TLS for frontend
- All communication is encrypted in transit

### Dependency Scanning

Regularly scan Python dependencies for vulnerabilities:

```bash
cd backend

# Install safety
pip install safety

# Check for known vulnerabilities
safety check -r requirements.txt

# Update dependencies as needed
pip list --outdated
```

---

## Monitoring and Observability

### CloudWatch Logs

**Lambda Logs**:

All Lambda execution logs are automatically sent to CloudWatch Logs:

```bash
# Get log group name
FUNCTION_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name estimation-tool-api \
  --query 'StackResources[?ResourceType==`AWS::Lambda::Function`].PhysicalResourceId' \
  --output text)

LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

# Tail logs in real-time
aws logs tail $LOG_GROUP --follow

# View recent errors
aws logs tail $LOG_GROUP --since 1h --filter-pattern "ERROR"

# View Bedrock-related logs
aws logs tail $LOG_GROUP --since 1h --filter-pattern "bedrock"
```

**Log Retention** (set to reduce costs):
```bash
# Set retention to 30 days
aws logs put-retention-policy \
  --log-group-name $LOG_GROUP \
  --retention-in-days 30
```

### CloudWatch Metrics

**Lambda Metrics** (automatically available):
- Invocations
- Duration
- Errors
- Throttles
- Concurrent Executions

**View in Console**:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#metricsV2:graph=~();query=~'*7bAWS*2fLambda*2cFunctionName*7d
```

**Create Alarms**:
```bash
# Alarm on Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name estimation-tool-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --alarm-actions arn:aws:sns:us-west-2:ACCOUNT:alert-topic

# Alarm on Lambda duration (timeout warning)
aws cloudwatch put-metric-alarm \
  --alarm-name estimation-tool-lambda-duration \
  --alarm-description "Alert on long-running executions" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 600000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --alarm-actions arn:aws:sns:us-west-2:ACCOUNT:alert-topic
```

### Bedrock Metrics

**Via CloudWatch**:

Bedrock metrics are available in CloudWatch under the `AWS/Bedrock` namespace:

- `Invocations`: Number of model invocations
- `InvocationLatency`: Time to generate response
- `InvocationClientErrors`: 4xx errors
- `InvocationServerErrors`: 5xx errors

**View Bedrock Metrics**:
```bash
# Get invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=anthropic.claude-3-sonnet-20240229-v1:0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region us-west-2
```

**Token Usage Tracking**:

Bedrock doesn't expose token metrics directly in CloudWatch. To track token usage:

1. **Application-Level Logging**:
   Update `backend/llm_service.py` to log token usage from response metadata:
   ```python
   # In BedrockProvider._invoke_model method
   response = client.invoke_model(...)
   response_body = json.loads(response["body"].read())
   
   # Log usage metadata (Claude models include this)
   if "usage" in response_body:
       logger.info(f"Token usage: {response_body['usage']}")
   ```

2. **Parse from CloudWatch Logs**:
   Use CloudWatch Logs Insights to aggregate token usage:
   ```sql
   fields @timestamp, @message
   | filter @message like /Token usage:/
   | parse @message "Token usage: *" as usage_json
   | stats sum(usage_json.input_tokens) as total_input, 
           sum(usage_json.output_tokens) as total_output
   ```

### CloudWatch Logs Insights Queries

**Access Logs Insights**:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:logs-insights
```

**Useful Queries**:

1. **Find Bedrock Errors**:
   ```sql
   fields @timestamp, @message
   | filter @message like /bedrock/i and @message like /error/i
   | sort @timestamp desc
   | limit 100
   ```

2. **Execution Duration Analysis**:
   ```sql
   fields @timestamp, @duration
   | filter @type = "REPORT"
   | stats avg(@duration), max(@duration), min(@duration), count(*) by bin(5m)
   ```

3. **Memory Usage**:
   ```sql
   fields @timestamp, @memorySize, @maxMemoryUsed
   | filter @type = "REPORT"
   | stats max(@maxMemoryUsed) as peak_memory by bin(5m)
   ```

4. **Error Rate**:
   ```sql
   fields @timestamp, @message
   | filter @message like /ERROR/ or @message like /Exception/
   | stats count(*) as error_count by bin(5m)
   ```

5. **Bedrock Invocation Latency** (application-level):
   ```sql
   fields @timestamp, @message
   | filter @message like /Bedrock invocation/
   | parse @message "duration: * ms" as duration
   | stats avg(duration), max(duration), p90(duration), p99(duration)
   ```

### Cost Tracking

**Set up Cost Allocation Tags**:
```bash
# Tag Lambda function
aws lambda tag-resource \
  --resource $FUNCTION_ARN \
  --tags Project=EstimationTool,Environment=Production,CostCenter=Engineering

# Tag API Gateway (via CloudFormation stack tags)
aws cloudformation update-stack \
  --stack-name estimation-tool-api \
  --use-previous-template \
  --tags Key=Project,Value=EstimationTool Key=Environment,Value=Production
```

**Enable Cost Allocation Tags** in AWS Billing Console:
1. Go to Billing → Cost Allocation Tags
2. Activate tags: Project, Environment, CostCenter
3. Wait 24 hours for activation

**Create Billing Alarm**:
```bash
# Note: Billing metrics are only in us-east-1
aws cloudwatch put-metric-alarm \
  --alarm-name estimation-tool-monthly-cost \
  --alarm-description "Alert if monthly costs exceed threshold" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:billing-alerts \
  --region us-east-1
```

**Monitor Bedrock Costs**:
- View in Cost Explorer: Filter by service "AWS Bedrock"
- Group by model ID to see per-model costs
- Set up budget alerts for Bedrock usage

**Cost Breakdown** (estimated monthly, production usage):
| Service | Usage | Cost |
|---------|-------|------|
| Lambda (compute) | 1000 invocations @ 60s avg | ~$1.20 |
| Lambda (requests) | 1000 requests | $0.20 |
| API Gateway | 1000 requests | $1.00 |
| Bedrock (Claude 3 Sonnet) | 1M input tokens, 200K output | ~$6.00 |
| CloudWatch Logs | 1 GB ingested, 1 GB stored | $0.50 |
| S3 (frontend) | 10 GB storage, 100 GB transfer | $0.23 |
| **Total** | | **~$9.13** |

Actual costs will vary based on usage patterns.

---

## Troubleshooting

### Authentication and Permission Errors

#### AccessDeniedException from Bedrock

**Error**:
```
ClientError: An error occurred (AccessDeniedException) when calling the InvokeModel operation: 
User: arn:aws:sts::123456789012:assumed-role/estimation-tool-api-EstimationFunctionRole/estimation-tool-api 
is not authorized to perform: bedrock:InvokeModel on resource: 
arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0
```

**Solutions**:

1. **Verify IAM Role Permissions**:
   ```bash
   # Get Lambda function's role
   ROLE_ARN=$(aws lambda get-function \
     --function-name $FUNCTION_NAME \
     --query 'Configuration.Role' \
     --output text)
   
   ROLE_NAME=$(echo $ROLE_ARN | cut -d'/' -f2)
   
   # Check inline policies
   aws iam list-role-policies --role-name $ROLE_NAME
   
   # Get inline policy document
   aws iam get-role-policy \
     --role-name $ROLE_NAME \
     --policy-name PolicyName
   
   # Check managed policies
   aws iam list-attached-role-policies --role-name $ROLE_NAME
   ```

2. **Add Missing Permission**:
   ```bash
   # Create policy document
   cat > bedrock-permission.json <<EOF
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": "bedrock:InvokeModel",
       "Resource": "arn:aws:bedrock:*::foundation-model/*"
     }]
   }
   EOF
   
   # Add inline policy to role
   aws iam put-role-policy \
     --role-name $ROLE_NAME \
     --policy-name BedrockInvokeModel \
     --policy-document file://bedrock-permission.json
   ```

3. **Redeploy Lambda** (to pick up IAM changes):
   ```bash
   cd infrastructure
   sam deploy --template template.yaml
   ```

#### UnauthorizedException or Model Not Found

**Error**:
```
ResourceNotFoundException: Could not resolve the foundation model from the model identifier: anthropic.claude-3-sonnet-20240229-v1:0
```

**Solutions**:

1. **Check Model Access**:
   - Go to AWS Console → Bedrock → Model access
   - Verify "Anthropic Claude 3 Sonnet" shows "Access granted"
   - If "Access requested" or "Access denied", request access again

2. **Verify Model ID**:
   ```bash
   # List available models
   aws bedrock list-foundation-models \
     --region us-west-2 \
     --query 'modelSummaries[?contains(modelId, `anthropic`)].{ID:modelId,Name:modelName,Status:modelLifecycle.status}' \
     --output table
   
   # Check specific model
   aws bedrock get-foundation-model \
     --model-identifier anthropic.claude-3-sonnet-20240229-v1:0 \
     --region us-west-2
   ```

3. **Check Region**:
   - Ensure Lambda's `AWS_REGION` environment variable matches where model access is granted
   - Some models are only available in specific regions

### Timeout Issues

#### Lambda Timeout

**Error**:
```
Task timed out after 900.00 seconds
```

**Solutions**:

1. **Increase Lambda Timeout** (if needed beyond 900s, consider async processing):
   ```yaml
   # In infrastructure/template.yaml
   Globals:
     Function:
       Timeout: 900  # Already at maximum
   ```

2. **Optimize Bedrock Requests**:
   - Reduce temperature (faster inference)
   - Use smaller/faster models (Claude 3 Haiku instead of Sonnet)
   - Reduce input context size

3. **Implement Async Processing** (for very long tasks):
   - Use Step Functions for orchestration
   - Use SQS for queuing
   - Return immediately and notify via webhook/email

#### Bedrock Throttling

**Error**:
```
ThrottlingException: Rate exceeded
```

**Solutions**:

1. **Check Bedrock Quotas**:
   - Go to AWS Console → Service Quotas → AWS Bedrock
   - View current limits for:
     - Requests per minute
     - Tokens per minute
   
2. **Request Quota Increase**:
   - In Service Quotas console, request increase for Bedrock quotas
   - Default limits are usually sufficient for moderate use

3. **Implement Retry Logic with Exponential Backoff**:
   ```python
   # Already implemented in boto3 by default
   # To customize:
   from botocore.config import Config
   
   config = Config(
       retries={
           'max_attempts': 10,
           'mode': 'adaptive'
       }
   )
   
   client = boto3.client('bedrock-runtime', config=config)
   ```

### VPC Connectivity Issues

#### Timeout Connecting to Bedrock from VPC

**Error**:
```
ConnectTimeoutError: Connect timeout on endpoint URL
```

**Solutions**:

1. **Verify VPC Endpoints Exist**:
   ```bash
   aws ec2 describe-vpc-endpoints \
     --filters "Name=service-name,Values=com.amazonaws.us-west-2.bedrock-runtime" \
     --query 'VpcEndpoints[].{ID:VpcEndpointId,VPC:VpcId,State:State,PrivateDns:PrivateDnsEnabled}' \
     --output table
   ```

2. **Check Private DNS is Enabled**:
   ```bash
   # Private DNS must be 'True'
   aws ec2 describe-vpc-endpoints \
     --vpc-endpoint-ids vpce-xxxxxxxx \
     --query 'VpcEndpoints[0].PrivateDnsEnabled'
   ```

3. **Verify Security Group Rules**:
   ```bash
   # Get security groups attached to VPC endpoint
   SG_IDS=$(aws ec2 describe-vpc-endpoints \
     --vpc-endpoint-ids vpce-xxxxxxxx \
     --query 'VpcEndpoints[0].Groups[].GroupId' \
     --output text)
   
   # Check inbound rules (must allow port 443 from Lambda's security group or VPC CIDR)
   aws ec2 describe-security-groups \
     --group-ids $SG_IDS \
     --query 'SecurityGroups[].IpPermissions'
   ```

4. **Test DNS Resolution from Lambda**:
   Create a test Lambda function in the same VPC to verify DNS:
   ```python
   import socket
   def lambda_handler(event, context):
       try:
           ip = socket.gethostbyname('bedrock-runtime.us-west-2.amazonaws.com')
           return {'status': 'success', 'ip': ip}
       except Exception as e:
           return {'status': 'error', 'message': str(e)}
   ```
   
   If it resolves to a private IP (10.x.x.x), VPC endpoint is working.
   If it resolves to a public IP, Private DNS is not enabled.

### Model and Inference Errors

#### Invalid Request Format

**Error**:
```
ValidationException: Input validation failed
```

**Solutions**:

1. Check request body format matches model requirements
2. Verify `anthropic_version` is correct for Claude models
3. Ensure `max_tokens` is within model limits
4. Check system prompt and messages format

#### Model Returns Empty or Incomplete Response

**Possible Causes**:
- Token limit reached
- Content filter triggered
- Parsing error in response handler

**Solutions**:

1. **Increase max_tokens**:
   ```python
   # In backend/llm_service.py
   request_body = {
       # ...
       "max_tokens": 8192,  # Increase if needed
   }
   ```

2. **Check CloudWatch Logs** for raw response:
   ```bash
   aws logs tail $LOG_GROUP --since 10m --filter-pattern "response_body"
   ```

3. **Add Response Validation**:
   ```python
   if not text_parts:
       logger.error(f"Empty response from Bedrock: {response_body}")
       raise RuntimeError("Empty response from Bedrock model")
   ```

### CloudWatch Logs Not Appearing

**Solutions**:

1. **Check IAM Permissions**:
   ```bash
   # Lambda role must have CloudWatch Logs permissions
   aws iam get-role-policy \
     --role-name $ROLE_NAME \
     --policy-name CloudWatchLogsPolicy
   ```

2. **Check Log Group Exists**:
   ```bash
   aws logs describe-log-groups \
     --log-group-name-prefix /aws/lambda/
   ```

3. **Verify Lambda is Running**:
   ```bash
   # Check recent invocations
   aws lambda get-function \
     --function-name $FUNCTION_NAME \
     --query 'Configuration.LastUpdateStatus'
   ```

### API Gateway Errors

#### CORS Errors in Browser

**Error**:
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Solutions**:

1. **Verify CORS Configuration** in API Gateway:
   ```bash
   aws apigatewayv2 get-api \
     --api-id $API_ID \
     --query 'CorsConfiguration'
   ```

2. **Update CORS Settings**:
   ```yaml
   # In infrastructure/template.yaml
   EstimationApi:
     Type: AWS::Serverless::HttpApi
     Properties:
       CorsConfiguration:
         AllowOrigins:
           - "*"  # Or specific domain: "https://yourdomain.com"
         AllowMethods:
           - GET
           - POST
           - PUT
           - DELETE
           - OPTIONS
         AllowHeaders:
           - "*"
         MaxAge: 300
   ```

3. **Redeploy**:
   ```bash
   cd infrastructure
   sam deploy --template template.yaml
   ```

#### 502 Bad Gateway

**Possible Causes**:
- Lambda function error/crash
- Lambda timeout
- Invalid response format from Lambda

**Solutions**:

1. **Check Lambda Logs**:
   ```bash
   aws logs tail $LOG_GROUP --since 10m --filter-pattern "ERROR"
   ```

2. **Test Lambda Directly**:
   ```bash
   aws lambda invoke \
     --function-name $FUNCTION_NAME \
     --payload '{"httpMethod":"GET","path":"/"}' \
     --cli-binary-format raw-in-base64-out \
     response.json
   
   cat response.json
   ```

3. **Check Lambda Response Format**:
   Ensure Lambda returns proper format for API Gateway:
   ```python
   return {
       "statusCode": 200,
       "headers": {"Content-Type": "application/json"},
       "body": json.dumps({"message": "success"})
   }
   ```

### Cost Overruns

**Symptoms**:
- Unexpectedly high AWS bill
- Bedrock costs higher than anticipated

**Investigation**:

1. **Check Bedrock Usage**:
   ```bash
   # In AWS Console → Cost Explorer
   # Filter by: Service = AWS Bedrock
   # Group by: Usage Type (to see token usage)
   ```

2. **Analyze Lambda Invocations**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Invocations \
     --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
     --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 86400 \
     --statistics Sum
   ```

3. **Check for Runaway Processes**:
   ```bash
   # Look for unusually long durations
   aws logs tail $LOG_GROUP --since 24h --filter-pattern "REPORT" | grep "Duration"
   ```

**Solutions**:

1. **Set Budget Alerts** (if not already done)
2. **Optimize Prompts** to reduce token usage
3. **Use Smaller Models** (Claude Haiku instead of Sonnet)
4. **Implement Request Throttling** in application
5. **Add Usage Logging** to track per-user/per-request costs

### General Debugging Steps

1. **Check CloudWatch Logs First**:
   ```bash
   aws logs tail $LOG_GROUP --follow
   ```

2. **Verify Environment Variables**:
   ```bash
   aws lambda get-function-configuration \
     --function-name $FUNCTION_NAME \
     --query 'Environment.Variables'
   ```

3. **Test Lambda Directly** (bypass API Gateway):
   ```bash
   aws lambda invoke \
     --function-name $FUNCTION_NAME \
     --payload file://test-event.json \
     response.json
   ```

4. **Enable Debug Logging**:
   Add environment variable:
   ```bash
   aws lambda update-function-configuration \
     --function-name $FUNCTION_NAME \
     --environment 'Variables={LOG_LEVEL=DEBUG,...}'
   ```

5. **Check AWS Service Health**:
   - https://health.aws.amazon.com/health/status
   - Check for service disruptions in your region

---

## Cost Optimization

### Lambda Cost Optimization

1. **Right-Size Memory Allocation**:
   - Monitor actual memory usage in CloudWatch
   - Lambda memory affects CPU allocation (and cost)
   - Start with 2048 MB, reduce if avg usage < 50%
   
   ```bash
   # Check memory usage
   aws logs tail $LOG_GROUP --since 24h --filter-pattern "REPORT" | grep "Max Memory Used"
   
   # Update if needed
   aws lambda update-function-configuration \
     --function-name $FUNCTION_NAME \
     --memory-size 1536
   ```

2. **Reduce Execution Time**:
   - Optimize code and dependencies
   - Use faster Bedrock models (Claude 3 Haiku)
   - Cache frequently accessed data

3. **Use Provisioned Concurrency** (if high traffic):
   - Eliminates cold starts
   - Fixed cost vs pay-per-invocation
   - Only if frequent, predictable traffic

### Bedrock Cost Optimization

1. **Choose Right Model**:
   - **Development**: Claude 3 Haiku (lowest cost)
   - **Production**: Claude 3 Sonnet (balanced)
   - **High-Quality**: Claude 3 Opus (highest cost)

2. **Optimize Prompts**:
   - Minimize input tokens (concise prompts)
   - Request shorter outputs when possible
   - Remove unnecessary context

3. **Cache Results** (if applicable):
   - Store estimation results in DynamoDB or S3
   - Return cached results for duplicate requests

4. **Monitor Token Usage**:
   ```bash
   # Add token logging in application
   # Aggregate from CloudWatch Logs
   aws logs tail $LOG_GROUP --since 24h --filter-pattern "Token usage"
   ```

### CloudWatch Logs Cost Optimization

1. **Set Log Retention**:
   ```bash
   aws logs put-retention-policy \
     --log-group-name $LOG_GROUP \
     --retention-in-days 7  # Or 14, 30, etc.
   ```

2. **Reduce Log Verbosity**:
   - Use INFO level in production (not DEBUG)
   - Log only essential information

3. **Use S3 for Long-Term Storage**:
   - Export old logs to S3 (cheaper storage)
   - Set lifecycle policy to archive to Glacier

### API Gateway Cost Optimization

- HTTP API is cheaper than REST API (already using HTTP API)
- No significant optimization needed for low-moderate traffic

### General Cost Optimization

1. **Enable Cost Allocation Tags**:
   - Tag all resources with Project, Environment
   - Track costs by tag in Cost Explorer

2. **Set Up Budgets**:
   ```bash
   # Create monthly budget
   aws budgets create-budget \
     --account-id $(aws sts get-caller-identity --query Account --output text) \
     --budget file://budget.json \
     --notifications-with-subscribers file://notifications.json
   ```

3. **Review Costs Monthly**:
   - Use AWS Cost Explorer
   - Identify and eliminate unused resources
   - Optimize high-cost services

4. **Consider Reserved Capacity** (for sustained workloads):
   - Savings Plans for Lambda
   - Reserved pricing for predictable usage

### Estimated Cost Breakdown

**Low Usage** (100 requests/month):
- Lambda: $0.20
- API Gateway: $0.10
- Bedrock: $0.60
- CloudWatch: $0.10
- S3: $0.02
- **Total**: ~$1.02/month

**Moderate Usage** (1,000 requests/month):
- Lambda: $2.00
- API Gateway: $1.00
- Bedrock: $6.00
- CloudWatch: $0.50
- S3: $0.23
- **Total**: ~$9.73/month

**High Usage** (10,000 requests/month):
- Lambda: $20.00
- API Gateway: $10.00
- Bedrock: $60.00
- CloudWatch: $2.00
- S3: $0.50
- **Total**: ~$92.50/month

**Note**: Actual costs vary based on:
- Average Lambda execution time
- Prompt/response token counts
- Model choice (Haiku vs Sonnet vs Opus)
- Data transfer volumes

---

## Additional Resources

### AWS Documentation

- [AWS Bedrock User Guide](https://docs.aws.amazon.com/bedrock/)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [API Gateway HTTP API Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)

### Support

- **AWS Support**: Open support case in AWS Console
- **Bedrock Model Access Issues**: Contact AWS support
- **Application Issues**: Check CloudWatch Logs first

### Best Practices

- Regular security audits
- Monthly cost reviews
- Dependency updates
- Backup configuration files
- Document custom modifications

---

**Document Version**: 2.0  
**Last Updated**: 2024  
**Maintained By**: System Administrators
