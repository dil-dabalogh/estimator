# Network Security Configuration

## Overview

By default, the Estimation Tool API is **publicly accessible from anywhere in the world**. This document explains how to restrict access to your company network or VPN.

## Current Implementation: Lambda Authorizer for IP Whitelisting

**Important**: HTTP API Gateway (API Gateway v2) does NOT support AWS WAF association. Instead, this application uses a **Lambda Authorizer** for IP-based access control.

## How It Works

1. **Lambda Authorizer Function**: A lightweight Lambda function that checks the request's source IP
2. **IP Range Configuration**: Allowed IP ranges are set via the `AllowedIPRanges` parameter during deployment
3. **Automatic Authorization**: API Gateway invokes the authorizer for every request
4. **Allow/Deny Decision**: The authorizer returns `isAuthorized: true/false` based on IP check
5. **Caching**: Authorization results are cached for 5 minutes to reduce Lambda invocations

## Step 1: Find Your Company's Public IP Addresses

### Option A: Find Your Current IP

```bash
# Your current public IP
curl https://checkip.amazonaws.com
```

### Option B: Get Your Company's IP Ranges

Contact your IT/Network team to get:
- Office public IP addresses or CIDR ranges
- VPN exit IP addresses or CIDR ranges

**Examples:**
- Single IP: `203.0.113.45/32`
- IP Range: `203.0.113.0/24` (allows 203.0.113.0 - 203.0.113.255)
- Multiple ranges: `203.0.113.0/24,198.51.100.0/24`

## Step 2: Deploy with IP Restrictions

Deploy the API with your allowed IP ranges:

```bash
cd infrastructure
sam build --use-container
sam deploy --guided
```

When prompted for `AllowedIPRanges`:

**Examples:**

```bash
# Single IP (your current VPN IP)
Parameter AllowedIPRanges [0.0.0.0/0]: 62.216.248.197/32

# Office network range
Parameter AllowedIPRanges [0.0.0.0/0]: 203.0.113.0/24

# Multiple ranges (office + VPN)
Parameter AllowedIPRanges [0.0.0.0/0]: 203.0.113.0/24,198.51.100.0/24

# Allow all (no restrictions - default)
Parameter AllowedIPRanges [0.0.0.0/0]: (press Enter)
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

To update allowed IP ranges after deployment, redeploy with new parameter:

```bash
cd infrastructure
sam deploy --parameter-overrides \
  AllowedIPRanges="NEW_IP_RANGES"
```

**Note**: This redeploys the authorizer Lambda with updated IP ranges. The update takes just a few seconds.

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

## Cleanup Orphaned WAF Resources

If you created WAF resources using the old `setup-waf.sh` script, clean them up:

```bash
cd infrastructure
./cleanup-waf.sh
```

This deletes any orphaned WAF Web ACLs and IP Sets from failed script attempts.

## Security Best Practices

1. ✅ **Use specific IP ranges**, not 0.0.0.0/0
2. ✅ **Document your IP ranges** and keep them updated
3. ✅ **Monitor authorizer logs** for blocked requests
4. ✅ **Review access quarterly** and remove unused IPs
5. ✅ **Use /32 for single IPs**, broader ranges only when needed
6. ✅ **Test access** from both inside and outside allowed ranges
7. ✅ **Keep backup access** (e.g., admin IP range separate from office)

## Related Documentation

- [System Administrator Guide](./Sysadminguide.md) - General deployment
- [Environment Variables Guide](./ENVIRONMENT_VARIABLES.md) - Configuration

