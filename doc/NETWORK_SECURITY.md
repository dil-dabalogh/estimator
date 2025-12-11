# Network Security Configuration

## Overview

The Estimation Tool uses **VPC endpoint-based access control** to restrict access to the Diligent VPN network only. Both the frontend (S3) and backend (API Gateway) are completely inaccessible from the public internet.

## Current Implementation: VPC Endpoint Access Control

**Access Control Method**: VPC endpoints with resource policies

### How It Works

1. **VPC Endpoints**: Created automatically by CloudFormation
   - API Gateway VPC Interface Endpoint
   - S3 VPC Gateway Endpoint

2. **Resource Policies**: Restrict access to VPC endpoints only
   - API Gateway: Resource policy denies all except from VPC endpoint
   - S3: Bucket policy denies all except from VPC endpoint

3. **Public Access Block**: S3 bucket blocks all public access

4. **Automatic Deployment**: Endpoints are created and configured during stack deployment

## Step 1: Gather VPC Configuration

You need the following information from your VPC:

1. **VPC ID**: The VPC where Diligent VPN is configured
2. **VPC CIDR Block**: The CIDR block for the VPC (e.g., `10.0.0.0/16`)
3. **Subnet IDs**: At least 2 subnets in different availability zones (for API Gateway endpoint)
4. **Security Group ID**: Security group for the API Gateway endpoint
5. **Route Table IDs**: All route tables in the VPC (for S3 Gateway endpoint)

See `doc/VPC_ENDPOINT_PREREQUISITES.md` for detailed instructions on gathering this information.

## Step 2: Deploy with VPC Endpoint Configuration

Deploy the API with VPC endpoint parameters:

```bash
cd infrastructure
chore deploy backend
```

Or using SAM directly:

```bash
sam build --use-container
sam deploy --guided
```

When prompted, provide:
- `VpcId`: Your VPC ID
- `VpcCidrBlock`: Your VPC CIDR block
- `ApiGatewaySubnetIds`: Comma-separated subnet IDs
- `ApiGatewaySecurityGroupId`: Security group ID
- `S3RouteTableIds`: Comma-separated route table IDs

**Example:**

```bash
Parameter VpcId []: vpc-xxxxxxxxxxxxxxxxx
Parameter VpcCidrBlock []: 10.0.0.0/16
Parameter ApiGatewaySubnetIds []: subnet-xxxxxxxxxxxxxxxxx,subnet-yyyyyyyyyyyyyyyyy
Parameter ApiGatewaySecurityGroupId []: sg-xxxxxxxxxxxxxxxxx
Parameter S3RouteTableIds []: rtb-xxxxxxxxxxxxxxxxx,rtb-yyyyyyyyyyyyyyyyy,rtb-zzzzzzzzzzzzzzzzzz,rtb-wwwwwwwwwwwwwwwwww
```

**Note**: For easier deployment, create `infrastructure/samconfig.toml` from `samconfig.toml.example` with your actual values. This file is in `.gitignore` and will not be committed.

Or use `--parameter-overrides`:

```bash
sam deploy --parameter-overrides \
  VpcId=vpc-xxxxxxxxxxxxxxxxx \
  VpcCidrBlock=10.0.0.0/16 \
  ApiGatewaySubnetIds=subnet-xxxxxxxxxxxxxxxxx,subnet-yyyyyyyyyyyyyyyyy \
  ApiGatewaySecurityGroupId=sg-xxxxxxxxxxxxxxxxx \
  S3RouteTableIds=rtb-xxxxxxxxxxxxxxxxx,rtb-yyyyyyyyyyyyyyyyy,rtb-zzzzzzzzzzzzzzzzzz,rtb-wwwwwwwwwwwwwwwwww \
  LLMProvider=bedrock \
  ...
```

## Step 3: Verify VPC Endpoint Access

### Test from VPN
```bash
# Get your API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text)

# Should succeed (200 OK) when connected to VPN
curl $API_URL/health
```

### Test from Public Internet (Should Fail)
```bash
# Disconnect VPN or test from different network
# Should be blocked (403 Forbidden)
curl $API_URL/health
```

## Step 4: Verify VPC Endpoint Configuration

After deployment, verify that VPC endpoints are created and configured correctly. See the [VPC Endpoint Access Guide](./VPC_ENDPOINT_ACCESS.md) for detailed verification steps.

## Security Best Practices

1. ✅ **Keep VPC configuration secure** - Never commit `samconfig.toml` to version control
2. ✅ **Use VPC endpoints** - Ensures access only from VPN network
3. ✅ **Monitor CloudWatch logs** for access issues
4. ✅ **Verify endpoint state** - Ensure endpoints are in "available" state
5. ✅ **Test access** from both VPN and public internet to verify restrictions
6. ✅ **Document VPC configuration** - Keep track of VPC IDs, subnets, and security groups
7. ✅ **Regular security reviews** - Review access patterns and endpoint configurations

## Related Documentation

- [IP Filtering Guide](./IP_FILTERING.md) - Detailed IP management and troubleshooting
- [System Administrator Guide](./Sysadminguide.md) - General deployment
- [Environment Variables Guide](./ENVIRONMENT_VARIABLES.md) - Configuration

