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
Parameter VpcId []: vpc-0debf6fec89321668
Parameter VpcCidrBlock []: 10.0.0.0/16
Parameter ApiGatewaySubnetIds []: subnet-0d0461af8faa47862,subnet-00709cdde2bfc1cad
Parameter ApiGatewaySecurityGroupId []: sg-0d767bd8c679a2c59
Parameter S3RouteTableIds []: rtb-0d7b4aa83ad8d4a37,rtb-098de2a98588c76c3,rtb-02bf8cba75a7cb133,rtb-0ed6e958148479c62
```

Or use `--parameter-overrides`:

```bash
sam deploy --parameter-overrides \
  AllowedIPRanges="62.216.248.197/32" \
  LLMProvider=bedrock \
  ...
```

## Step 3: Verify IP Restrictions

### Test from Allowed IP
```bash
# Get your API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text)

# Should succeed (200 OK)
curl $API_URL/health
```

### Test from Different IP (outside allowed range)
```bash
# Disconnect VPN or test from different network
# Should be blocked (403 Forbidden with "Unauthorized" message)
curl $API_URL/health
```

## Step 4: Update IP Ranges Later

### Quick Method: Using IP Management Script (Recommended)

```bash
cd infrastructure

# Add your current IP
./manage-ip-whitelist.sh add-current

# Add specific IP or range
./manage-ip-whitelist.sh add 203.0.113.45

# View current whitelist
./manage-ip-whitelist.sh list

# Remove all IPs (deny all)
./manage-ip-whitelist.sh remove-all
```

See the [IP Filtering Guide](./IP_FILTERING.md) for detailed usage and examples.

### Manual Method: CloudFormation Update

To update allowed IP ranges manually:

```bash
cd infrastructure
sam deploy --parameter-overrides \
  AllowedIPRanges="NEW_IP_RANGES"
```

**Note**: The script method is preferred as it automatically handles all parameters and updates both backend and frontend.

## Common Scenarios

### Scenario 1: Office Network Only

```bash
sam deploy --parameter-overrides AllowedIPRanges="203.0.113.0/24"
```

### Scenario 2: Office + VPN

```bash
sam deploy --parameter-overrides AllowedIPRanges="203.0.113.0/24,198.51.100.0/24"
```

### Scenario 3: Multiple Offices

```bash
sam deploy --parameter-overrides AllowedIPRanges="203.0.113.0/24,198.51.100.0/24,192.0.2.0/24"
```

### Scenario 4: Just Your Current IP (Testing)

```bash
MY_IP=$(curl -s https://checkip.amazonaws.com)
sam deploy --parameter-overrides AllowedIPRanges="$MY_IP/32"
```

## Monitoring Blocked Requests

### View Authorizer Logs in CloudWatch

Blocked requests are logged by the Lambda authorizer:

```bash
# Get authorizer function name
AUTH_FUNCTION=$(aws cloudformation describe-stack-resources \
  --stack-name estimation-tool-api \
  --query 'StackResources[?LogicalResourceId==`IPAuthorizerFunction`].PhysicalResourceId' \
  --output text)

# View recent logs
aws logs tail /aws/lambda/$AUTH_FUNCTION --since 1h

# View blocked requests
aws logs tail /aws/lambda/$AUTH_FUNCTION --since 1h --filter-pattern "Allowed: False"
```

### CloudWatch Logs Insights Query

```sql
fields @timestamp, @message
| filter @message like /Source IP:/
| parse @message "Source IP: *, Allowed: *" as sourceIp, allowed
| stats count() by sourceIp, allowed
| sort count desc
```

## Troubleshooting

### Issue: "403 Forbidden" from Allowed IP

**Causes:**
1. IP range is incorrect (check CIDR notation)
2. Your actual public IP differs from what you think
3. NAT or proxy is changing your IP

**Solution:**
```bash
# Check your actual public IP
curl https://checkip.amazonaws.com

# Add it to allowed ranges
# Use /32 for single IP: 203.0.113.45/32
```

### Issue: Can't Access After Enabling WAF

**Quick Fix - Temporarily Allow All:**
```bash
cd infrastructure
sam deploy --parameter-overrides AllowedIPRanges="0.0.0.0/0"
```

Then find your correct IP and redeploy with proper ranges.

### Issue: VPN Users Can't Access

Your VPN might use dynamic IPs. Solutions:

1. **Get VPN exit IP range** from IT team
2. **Use wider CIDR range** (e.g., /24 instead of /32)
3. **Add multiple VPN exit IPs** to the list

## Cost Considerations

**Lambda Authorizer Pricing (as of 2024):**
- Lambda invocations: First 1M requests/month free, then $0.20 per 1M
- Lambda duration: Minimal (< 10ms per authorization)
- Authorization caching: Results cached for 5 minutes (reduces invocations)

**Estimated monthly cost**: 
- Low usage (1,000 requests): $0.00 (within free tier)
- Moderate usage (100,000 requests): ~$0.02
- High usage (1M requests): ~$0.20

**Much cheaper than AWS WAF** (~$6-10/month)

## Alternative Approaches (Not Implemented)

### Option 1: AWS WAF + CloudFront
- **Why not direct WAF**: HTTP APIs don't support WAF association
- **CloudFront workaround**: Put CloudFront in front of API Gateway, attach WAF to CloudFront
- Pros: Full WAF features, DDoS protection
- Cons: Higher cost (~$6-10/month for WAF + CloudFront), more complex setup

### Option 2: Convert to REST API + WAF
- Convert from HTTP API (v2) to REST API (v1)
- REST APIs support direct WAF association
- Pros: Native WAF support
- Cons: REST APIs are more expensive, require template changes

### Option 3: VPC Endpoint (Private API)
- Most secure
- Only accessible within your VPC
- Requires VPN or Direct Connect to access
- More complex setup

### Option 4: API Keys
- Simple authentication
- Not IP-based
- Users need to include API key in requests
- Less secure than IP whitelisting

## Removing IP Restrictions

To make the API publicly accessible again:

```bash
cd infrastructure
sam deploy --parameter-overrides AllowedIPRanges="0.0.0.0/0"
```

This redeploys the authorizer with no IP restrictions (allows all IPs).

## Security Best Practices

1. ✅ **Use specific IP ranges**, not 0.0.0.0/0
2. ✅ **Document your IP ranges** and keep them updated
3. ✅ **Monitor authorizer logs** for blocked requests
4. ✅ **Review access quarterly** and remove unused IPs
5. ✅ **Use /32 for single IPs**, broader ranges only when needed
6. ✅ **Test access** from both inside and outside allowed ranges
7. ✅ **Keep backup access** (e.g., admin IP range separate from office)

## Related Documentation

- [IP Filtering Guide](./IP_FILTERING.md) - Detailed IP management and troubleshooting
- [System Administrator Guide](./Sysadminguide.md) - General deployment
- [Environment Variables Guide](./ENVIRONMENT_VARIABLES.md) - Configuration

