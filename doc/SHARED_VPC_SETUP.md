# Shared VPC Setup Guide

## Overview

If your VPC is shared via AWS Resource Access Manager (RAM), CloudFormation cannot create VPC endpoints directly. You must use existing VPC endpoints that were created by the VPC owner account.

## Error Message

If you see this error during deployment:

```
CREATE_FAILED: AWS::EC2::VPCEndpoint - This operation does not support shared VPCs.
```

This means your VPC is shared and you need to use existing endpoints.

## Solution: Use Existing VPC Endpoints

### Step 1: Find Existing VPC Endpoints

Ask your VPC owner or AWS administrator for the VPC endpoint IDs, or find them yourself:

```bash
# Find API Gateway VPC Interface Endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-xxxxxxxxxxxxxxxxx" \
            "Name=service-name,Values=com.amazonaws.us-west-2.execute-api" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,ServiceName]' \
  --output table

# Find S3 VPC Gateway Endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-xxxxxxxxxxxxxxxxx" \
            "Name=service-name,Values=com.amazonaws.us-west-2.s3" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,ServiceName]' \
  --output table
```

### Step 2: Update samconfig.toml

Edit your `infrastructure/samconfig.toml` file to use existing endpoints:

```toml
[dev.deploy.parameters]
parameter_overrides = "VpcId=vpc-xxxxxxxxxxxxxxxxx VpcCidrBlock=10.0.0.0/16 ExistingApiGatewayVpcEndpointId=vpce-xxxxxxxxxxxxxxxxx ExistingS3VpcEndpointId=vpce-yyyyyyyyyyyyyyyyy LLMProvider=bedrock OpenAIModel=gpt-5 BedrockRegion=us-west-2 BedrockModel=anthropic.claude-3-5-sonnet-20241022-v2:0 BedrockAgentId= BedrockAgentAliasId= AtlassianURL=https://your-company.atlassian.net AtlassianEmail=your-email@company.com"
```

**Important**: 
- Leave `ApiGatewaySubnetIds`, `ApiGatewaySecurityGroupId`, and `S3RouteTableIds` empty (or omit them)
- Provide `ExistingApiGatewayVpcEndpointId` and `ExistingS3VpcEndpointId` with the actual endpoint IDs

### Step 3: Deploy

Deploy as usual:

```bash
cd infrastructure
chore deploy backend
```

## If Endpoints Don't Exist

If the VPC endpoints don't exist yet, you have two options:

### Option A: Request VPC Owner to Create Endpoints

Ask the VPC owner account to create:
1. **API Gateway VPC Interface Endpoint**:
   - Service: `com.amazonaws.us-west-2.execute-api`
   - Type: Interface
   - Subnets: At least 2 in different AZs
   - Security Group: Must allow HTTPS (443) from VPC CIDR
   - Private DNS: Enabled

2. **S3 VPC Gateway Endpoint**:
   - Service: `com.amazonaws.us-west-2.s3`
   - Type: Gateway
   - Route Tables: All route tables in the VPC

### Option B: Use a Non-Shared VPC

If possible, use a VPC that is not shared, and the template will create the endpoints automatically.

## Verification

After deployment, verify the endpoints are being used:

```bash
# Check stack outputs
aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?contains(OutputKey, `VpcEndpoint`)].{Key:OutputKey,Value:OutputValue}' \
  --output table
```

The endpoint IDs in the outputs should match the existing endpoints you provided.

## Troubleshooting

### Endpoint Not Found

If you get an error that the endpoint doesn't exist:
1. Verify the endpoint ID is correct
2. Ensure the endpoint is in the same region as your stack
3. Check that the endpoint is in "available" state:
   ```bash
   aws ec2 describe-vpc-endpoints \
     --vpc-endpoint-ids vpce-xxxxxxxxxxxxxxxxx \
     --query 'VpcEndpoints[0].State'
   ```

### Wrong VPC

Ensure the endpoints are in the same VPC you're deploying to:
```bash
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-xxxxxxxxxxxxxxxxx \
  --query 'VpcEndpoints[0].VpcId'
```

## Related Documentation

- [VPC Endpoint Access Guide](./VPC_ENDPOINT_ACCESS.md)
- [Deployment Steps](./DEPLOYMENT_STEPS_VPC.md)

