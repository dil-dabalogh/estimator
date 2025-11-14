# System Administrator Guide

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- AWS SAM CLI installed
- Node.js 18+ and npm
- Python 3.11+
- Access to Atlassian (Confluence/Jira) API
- OpenAI API key or AWS Bedrock access

## Backend Deployment

### Step 1: Prepare Environment Variables

The Lambda function requires the following environment variables:

**LLM Configuration:**
- `LLM_PROVIDER`: `openai` or `bedrock`
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI)
- `OPENAI_MODEL`: Model name (default: `gpt-4`)
- `AWS_REGION`: AWS region for Bedrock (if using Bedrock)
- `BEDROCK_MODEL`: Bedrock model ID (if using Bedrock)

**Atlassian Configuration:**
- `ATLASSIAN_URL`: Your Atlassian instance URL (e.g., `https://company.atlassian.net/wiki`)
- `ATLASSIAN_USER_EMAIL`: Atlassian user email
- `ATLASSIAN_API_TOKEN`: Atlassian API token

### Step 2: Deploy Backend with SAM

```bash
# Navigate to infrastructure directory
cd infrastructure

# Build the application
sam build --template template.yaml

# Deploy with guided prompts
sam deploy --guided --template template.yaml --stack-name estimation-tool-api --capabilities CAPABILITY_IAM
```

During guided deployment, you'll be prompted for:
- Stack name (default: estimation-tool-api)
- AWS region
- Parameter values (LLM provider, API keys, etc.)
- Confirmation for IAM role creation

### Step 3: Note the API URL

After deployment, SAM will output the API Gateway URL:

```
Outputs:
EstimationApiUrl: https://xxxxx.execute-api.region.amazonaws.com
```

Save this URL for frontend configuration.

### Alternative: Manual Deployment

If not using SAM, deploy manually:

1. Create a Lambda function with Python 3.11 runtime
2. Set memory to 2048 MB
3. Set timeout to 900 seconds
4. Package backend code and dependencies
5. Upload to Lambda
6. Create API Gateway HTTP API
7. Configure routes for `/{proxy+}` to Lambda
8. Enable CORS

## Frontend Deployment

### Step 1: Configure Environment

Create `frontend/.env` with the API URL:

```
VITE_API_BASE_URL=https://xxxxx.execute-api.region.amazonaws.com
```

### Step 2: Build Frontend

```bash
cd frontend
npm install
npm run build
```

### Step 3: Deploy to S3

```bash
# Create S3 bucket
aws s3 mb s3://estimation-tool-frontend

# Enable static website hosting
aws s3 website s3://estimation-tool-frontend --index-document index.html

# Upload build artifacts
aws s3 sync dist/ s3://estimation-tool-frontend --delete

# Make public
aws s3api put-bucket-policy --bucket estimation-tool-frontend --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::estimation-tool-frontend/*"
  }]
}'
```

### Optional: CloudFront Distribution

For better performance and custom domain:

1. Create CloudFront distribution
2. Set origin to S3 bucket
3. Configure SSL certificate
4. Update DNS records

## Monitoring

### CloudWatch Logs

Lambda logs are automatically sent to CloudWatch Logs:
- Log group: `/aws/lambda/estimation-tool-api`
- Check for errors and performance issues

### CloudWatch Metrics

Monitor:
- Lambda invocations
- Duration
- Errors
- Throttles

### API Gateway Metrics

Monitor:
- Request count
- 4XX errors
- 5XX errors
- Latency

## Security Considerations

1. Store sensitive credentials in AWS Secrets Manager
2. Update Lambda IAM role with least privilege
3. Enable API Gateway throttling
4. Consider VPC deployment for internal use
5. Enable CloudTrail for audit logging
6. Use WAF for additional protection

## Troubleshooting

### Lambda Timeouts

- Increase timeout (max 900 seconds)
- Increase memory allocation
- Check LLM provider response times

### Out of Memory

- Increase Lambda memory (recommended: 2048 MB)
- Monitor memory usage in CloudWatch

### Cold Starts

- Consider provisioned concurrency for production
- Optimize dependencies and imports

### CORS Issues

- Verify CORS configuration in API Gateway
- Check frontend is sending correct Origin header

## Cost Optimization

- Use appropriate Lambda memory size
- Enable CloudWatch Logs retention
- Monitor LLM API usage
- Consider reserved capacity for high usage

