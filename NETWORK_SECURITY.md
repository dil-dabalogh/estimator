# Network Security Configuration

## Overview

By default, the Estimation Tool API is **publicly accessible from anywhere in the world**. This document explains how to restrict access to your company network or VPN.

## Current Implementation: AWS WAF IP Whitelisting

The CloudFormation template includes AWS WAF (Web Application Firewall) with IP-based access control. This allows you to specify which IP addresses or IP ranges can access your API.

## How It Works

1. **IP Set**: Defines allowed IP addresses/ranges in CIDR notation
2. **WAF Web ACL**: Blocks all traffic by default, allows only IPs in the IP Set
3. **API Gateway Association**: WAF is attached to your API Gateway

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

### During Initial Deployment

```bash
cd infrastructure
sam build --use-container
sam deploy --guided
```

When prompted:
```
Parameter AllowedIPRanges [0.0.0.0/0]: 203.0.113.0/24,198.51.100.0/24
```

**Important**: `0.0.0.0/0` means "allow from anywhere" (no restrictions). Replace with your actual IP ranges.

### Update Existing Deployment

```bash
cd infrastructure
sam deploy --parameter-overrides \
  AllowedIPRanges="203.0.113.0/24,198.51.100.0/24"
```

## Step 3: Verify IP Restrictions

### Test from Allowed IP
```bash
# Should succeed (200 OK)
curl -I https://YOUR_API_GATEWAY_URL/health
```

### Test from Different IP (outside allowed range)
```bash
# Should be blocked (403 Forbidden)
curl -I https://YOUR_API_GATEWAY_URL/health
```

## Step 4: Update IP Ranges Later

To add or modify allowed IP ranges without full redeployment:

```bash
# Get your WAF IP Set ID
IP_SET_ID=$(aws wafv2 list-ip-sets --scope REGIONAL \
  --query "IPSets[?Name=='EstimationToolAllowedIPs'].Id" \
  --output text)

# Get current lock token
LOCK_TOKEN=$(aws wafv2 get-ip-set --scope REGIONAL --id $IP_SET_ID \
  --name EstimationToolAllowedIPs \
  --query 'LockToken' --output text)

# Update IP addresses
aws wafv2 update-ip-set \
  --scope REGIONAL \
  --id $IP_SET_ID \
  --name EstimationToolAllowedIPs \
  --addresses 203.0.113.0/24 198.51.100.0/24 192.0.2.0/24 \
  --lock-token $LOCK_TOKEN
```

## Common Scenarios

### Scenario 1: Office Network Only

```bash
AllowedIPRanges="203.0.113.0/24"
```

### Scenario 2: Office + VPN

```bash
AllowedIPRanges="203.0.113.0/24,198.51.100.0/24"
```

### Scenario 3: Multiple Offices

```bash
AllowedIPRanges="203.0.113.0/24,198.51.100.0/24,192.0.2.0/24"
```

### Scenario 4: Temporarily Allow All (Testing)

```bash
AllowedIPRanges="0.0.0.0/0"
```

**Warning**: This removes all restrictions. Use only for testing!

## WAF Monitoring

### View Blocked Requests

```bash
# Get WAF metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=Rule,Value=AllowCompanyIPs Name=WebACL,Value=EstimationToolWAF \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

### Check WAF Logs (Optional - requires setup)

To enable WAF logging:

```bash
# Create S3 bucket for WAF logs
aws s3 mb s3://estimation-tool-waf-logs-$(aws sts get-caller-identity --query Account --output text)

# Enable logging
aws wafv2 put-logging-configuration \
  --logging-configuration '{
    "ResourceArn": "arn:aws:wafv2:us-west-2:ACCOUNT_ID:regional/webacl/EstimationToolWAF/ID",
    "LogDestinationConfigs": ["arn:aws:s3:::estimation-tool-waf-logs-ACCOUNT_ID"]
  }'
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

**AWS WAF Pricing (as of 2024):**
- Web ACL: ~$5/month
- Rules: ~$1/month per rule
- Requests: ~$0.60 per million requests

**Estimated monthly cost**: ~$6-10 for typical usage

## Alternative Approaches (Not Implemented)

### Option 1: VPC Endpoint (Private API)
- Most secure
- Only accessible within your VPC
- Requires VPN or Direct Connect to access
- More complex setup

### Option 2: CloudFront with Geographic Restrictions
- Restrict by country
- Add IP whitelisting
- Includes CDN benefits
- Higher cost

### Option 3: API Keys
- Simple authentication
- Not IP-based
- Users need to include API key in requests
- Less secure than IP whitelisting

## Removing IP Restrictions

To make the API public again:

```bash
cd infrastructure
sam deploy --parameter-overrides AllowedIPRanges="0.0.0.0/0"
```

Or remove the WAF resources from `template.yaml` entirely.

## Security Best Practices

1. ✅ **Use specific IP ranges**, not 0.0.0.0/0
2. ✅ **Document your IP ranges** and keep them updated
3. ✅ **Monitor WAF metrics** for blocked requests
4. ✅ **Review access quarterly** and remove unused IPs
5. ✅ **Use /32 for single IPs**, broader ranges only when needed
6. ✅ **Test access** from both inside and outside allowed ranges
7. ✅ **Keep backup access** (e.g., admin IP range separate from office)

## Related Documentation

- [System Administrator Guide](./Sysadminguide.md) - General deployment
- [Environment Variables Guide](./ENVIRONMENT_VARIABLES.md) - Configuration

