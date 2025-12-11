# VPC Endpoint Access Control Guide

## Overview

The Estimation Tool uses VPC endpoints to restrict access to the Diligent VPN network only. Both the frontend (S3) and backend (API Gateway) are accessible exclusively through VPC endpoints, ensuring no public internet access.

## Architecture

```
Diligent VPN
    │
    ├─→ VPC Endpoint (API Gateway) ──→ API Gateway (HTTP + WebSocket)
    │
    └─→ VPC Endpoint (S3 Gateway) ──→ S3 Frontend
```

### How It Works

1. **API Gateway VPC Interface Endpoint**:
   - Created automatically by CloudFormation
   - Routes API requests through the VPC
   - Resource policies restrict access to VPC endpoint only

2. **S3 VPC Gateway Endpoint**:
   - Created automatically by CloudFormation
   - Routes S3 requests through the VPC
   - Bucket policy restricts access to VPC endpoint only

3. **Resource Policies**:
   - API Gateway: Resource policy denies all access except from VPC endpoint
   - S3: Bucket policy denies all access except from VPC endpoint
   - Both use `aws:SourceVpce` condition to validate VPC endpoint source

## Configuration

### Required Parameters

When deploying the stack, you must provide:

- `VpcId`: VPC ID where Diligent VPN is configured
- `VpcCidrBlock`: VPC CIDR block (e.g., `10.0.0.0/16`)
- `ApiGatewaySubnetIds`: Comma-separated list of subnet IDs (at least 2 in different AZs)
- `ApiGatewaySecurityGroupId`: Security group ID for API Gateway endpoint
- `S3RouteTableIds`: Comma-separated list of route table IDs (all route tables in VPC)

### Example Configuration

Create `infrastructure/samconfig.toml` from the template:

```bash
cd infrastructure
cp samconfig.toml.example samconfig.toml
```

Then update the `parameter_overrides` with your actual values:

```toml
parameter_overrides = "VpcId=vpc-xxxxxxxxxxxxxxxxx VpcCidrBlock=10.0.0.0/16 ApiGatewaySubnetIds=subnet-xxxxxxxxxxxxxxxxx,subnet-yyyyyyyyyyyyyyyyy ApiGatewaySecurityGroupId=sg-xxxxxxxxxxxxxxxxx S3RouteTableIds=rtb-xxxxxxxxxxxxxxxxx,rtb-yyyyyyyyyyyyyyyyy,rtb-zzzzzzzzzzzzzzzzzz,rtb-wwwwwwwwwwwwwwwwww ..."
```

**Note**: The `samconfig.toml` file is in `.gitignore` and will not be committed to version control.

## Deployment

### Backend Deployment

VPC endpoints are created automatically during backend deployment:

```bash
cd infrastructure
chore deploy backend
```

The stack will create:
- API Gateway VPC Interface Endpoint
- S3 VPC Gateway Endpoint
- Resource policies on both APIs

### Frontend Deployment

Frontend deployment automatically uses the S3 VPC endpoint:

```bash
cd infrastructure
chore deploy frontend
```

The deployment script:
- Fetches S3 VPC endpoint ID from stack outputs
- Configures S3 bucket policy to allow only VPC endpoint access
- Blocks all public access

## Accessing the Application

### From Diligent VPN

1. Connect to Diligent VPN
2. Access the frontend URL (provided after deployment)
3. The application will work normally

### From Public Internet

- **Frontend**: Returns 403 Forbidden
- **API**: Returns 403 Forbidden
- **WebSocket**: Connection refused

## Troubleshooting

### Cannot Access from VPN

1. **Verify VPN Connection**:
   ```bash
   # Check if you can resolve AWS service endpoints
   nslookup execute-api.us-west-2.amazonaws.com
   nslookup s3.us-west-2.amazonaws.com
   ```

2. **Check VPC Endpoints**:
   ```bash
   VPC_ID="vpc-xxxxxxxxxxxxxxxxx"
   aws ec2 describe-vpc-endpoints \
     --filters "Name=vpc-id,Values=$VPC_ID" \
     --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State]' \
     --output table
   ```

3. **Verify Endpoint State**:
   - Endpoints should be in "available" state
   - Private DNS should be enabled (for Interface endpoints)

4. **Check Security Groups**:
   ```bash
   # For API Gateway Interface endpoint
   aws ec2 describe-security-groups \
     --group-ids sg-xxxxxxxxxxxxxxxxx \
     --query 'SecurityGroups[0].IpPermissions'
   ```
   - Security group must allow inbound HTTPS (443) from VPC CIDR

### Endpoints Not Created

If endpoints are not created during deployment:

1. Check CloudFormation stack events for errors
2. Verify VPC ID, subnet IDs, and security group IDs are correct
3. Ensure you have permissions to create VPC endpoints
4. Check route tables exist for S3 Gateway endpoint

### DNS Resolution Issues

If DNS doesn't resolve to private IPs:

1. **Verify Private DNS**:
   ```bash
   aws ec2 describe-vpc-endpoints \
     --vpc-endpoint-ids vpce-xxxxxxxxxxxxxxxxx \
     --query 'VpcEndpoints[0].PrivateDnsEnabled'
   ```
   - Should return `True`

2. **Test DNS Resolution**:
   ```bash
   # From a machine in the VPC/VPN
   nslookup execute-api.us-west-2.amazonaws.com
   # Should resolve to private IP (10.x.x.x)
   ```

## Security Considerations

### VPC Endpoint Policies

- API Gateway endpoint policy: Allows all actions (endpoint-level)
- S3 Gateway endpoint policy: Allows all S3 actions (endpoint-level)
- Resource-level policies provide the actual access control

### Resource Policies

- API Gateway: Denies all except from VPC endpoint
- S3: Denies all except from VPC endpoint
- Both include VPC CIDR validation as additional check

### Public Access Block

S3 bucket has public access completely blocked:
- `BlockPublicAcls: true`
- `IgnorePublicAcls: true`
- `BlockPublicPolicy: true`
- `RestrictPublicBuckets: true`

## Cost Considerations

### VPC Endpoint Costs

- **API Gateway Interface Endpoint**: ~$7.20/month per endpoint per AZ
  - With 2 AZs: ~$14.40/month
- **S3 Gateway Endpoint**: Free (no charge)
- **Data Processing**: ~$0.01/GB for Interface endpoints

### Total Estimated Cost

- API Gateway endpoint (2 AZs): ~$14.40/month
- S3 Gateway endpoint: $0/month
- **Total**: ~$14.40/month minimum

## Migration from IP Whitelist

If you're migrating from IP whitelist:

1. Deploy new stack with VPC endpoint parameters
2. Test access from VPN
3. Verify public access is blocked
4. Remove old IP whitelist configuration

The old `AllowedIPRanges` parameter and `chore ip` commands are deprecated and will be removed in a future version.

