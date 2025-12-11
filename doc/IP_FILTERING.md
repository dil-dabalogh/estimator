# IP Filtering Guide

> **DEPRECATED**: This guide is deprecated. IP filtering has been replaced with VPC endpoint-based access control.
> 
> **Migration**: See `doc/VPC_ENDPOINT_ACCESS.md` for the new access control method.
> 
> The `AllowedIPRanges` parameter and `chore ip` commands are deprecated and will be removed in a future version.

---

# IP Filtering Guide (Deprecated)

This guide explains how IP filtering **used to work** in the Estimation Tool. This method has been replaced with VPC endpoint-based access control.

## Overview

The Estimation Tool implements IP-based access control at multiple levels to ensure only authorized networks can access the application:

- **API Gateway (HTTP)**: Filters all REST API requests
- **WebSocket API**: Filters WebSocket connections
- **S3 Frontend**: Filters static website access via bucket policy

All three layers use the same IP whitelist, managed through a single CloudFormation parameter.

## Architecture

```
User Browser (IP: X.X.X.X)
    │
    ├─→ HTTP API → Lambda Authorizer → Check IP → Allow/Deny
    │
    ├─→ WebSocket API → Lambda Authorizer → Check IP → Allow/Deny
    │
    └─→ S3 Frontend → Bucket Policy → Check IP → Allow/Deny
```

### How It Works

1. **Backend API (HTTP + WebSocket)**:
   - Lambda authorizer function checks incoming request's source IP
   - Compares against allowed IP ranges from environment variable
   - Returns allow/deny decision to API Gateway
   - Denied requests receive 403 Forbidden

2. **Frontend (S3)**:
   - S3 bucket policy includes IP condition
   - AWS checks source IP before serving files
   - Denied requests receive 403 Forbidden

3. **Internal AWS Communication**:
   - Lambda to Bedrock: Uses IAM roles, not affected by IP filtering
   - Lambda to DynamoDB: Uses IAM roles, not affected by IP filtering
   - API Gateway to Lambda: Internal AWS network, not affected

## Managing IP Whitelist

### Quick Start

```bash
cd infrastructure

# Add your current IP to whitelist
./manage-ip-whitelist.sh add-current

# View current whitelist
./manage-ip-whitelist.sh list
```

### Command Reference

#### Add Current IP

Automatically detects and adds your current public IP:

```bash
./manage-ip-whitelist.sh add-current
```

This is the most common operation. Use it when:
- Setting up access for the first time
- Your IP address changes (dynamic IP)
- Adding access from a new location

#### Add Specific IP or Range

Add a specific IP address or CIDR range:

```bash
# Add single IP
./manage-ip-whitelist.sh add 203.0.113.45

# Add single IP in CIDR notation
./manage-ip-whitelist.sh add 203.0.113.45/32

# Add IP range (entire /24 network = 256 IPs)
./manage-ip-whitelist.sh add 203.0.113.0/24

# Add IP range (entire /16 network = 65,536 IPs)
./manage-ip-whitelist.sh add 10.0.0.0/16
```

Use cases:
- Adding office network IP range
- Adding VPN exit IP
- Adding known static IPs for team members

#### Remove All IPs (Deny All)

Remove all IPs from whitelist, effectively blocking all access:

```bash
./manage-ip-whitelist.sh remove-all
```

This sets the whitelist to `127.0.0.1/32` (localhost only), denying all external access.

Use when:
- Taking application offline for maintenance
- Security incident response
- Temporarily disabling public access

**Warning**: After running this, you must add IPs back to restore access.

#### List Current Whitelist

View the current IP whitelist:

```bash
./manage-ip-whitelist.sh list
```

Output example:
```
Current IP Whitelist
=========================================

Whitelist: 203.0.113.45/32,198.51.100.0/24

Individual IPs/Ranges:
  - 203.0.113.45/32
  - 198.51.100.0/24
```

### Update Process

When you modify the IP whitelist:

1. Script updates CloudFormation stack parameter `AllowedIPRanges`
2. CloudFormation updates Lambda authorizer environment variable
3. Lambda authorizer reads new value on next invocation
4. Changes take effect within 1-2 minutes

**Important**: After updating IPs, you must also redeploy the frontend to update the S3 bucket policy:

```bash
# Update IP whitelist
./manage-ip-whitelist.sh add 203.0.113.45

# Update frontend bucket policy to match
./deploy-frontend.sh
```

## CIDR Notation Reference

CIDR (Classless Inter-Domain Routing) notation specifies IP ranges using a base IP and prefix length.

### Format

```
IP_ADDRESS/PREFIX_LENGTH
```

- **IP_ADDRESS**: Base IP address (e.g., `192.168.1.0`)
- **PREFIX_LENGTH**: Number of fixed bits (0-32)

### Common CIDR Ranges

| CIDR | IP Count | Example Use Case |
|------|----------|------------------|
| `/32` | 1 | Single IP address (e.g., `203.0.113.45/32`) |
| `/31` | 2 | Point-to-point link |
| `/30` | 4 | Small subnet |
| `/29` | 8 | Very small network |
| `/28` | 16 | Small office |
| `/27` | 32 | Small network |
| `/26` | 64 | Medium subnet |
| `/25` | 128 | Medium subnet |
| `/24` | 256 | Typical small network (e.g., `192.168.1.0/24`) |
| `/16` | 65,536 | Large corporate network |
| `/8` | 16,777,216 | Very large network (Class A) |
| `/0` | 4,294,967,296 | All IP addresses (0.0.0.0/0 = internet) |

### Examples

**Single IP**:
```
203.0.113.45/32
```
Allows only `203.0.113.45`

**Office Network (256 IPs)**:
```
198.51.100.0/24
```
Allows `198.51.100.0` through `198.51.100.255`

**Corporate Network (65,536 IPs)**:
```
10.0.0.0/16
```
Allows `10.0.0.0` through `10.0.255.255`

**Multiple Ranges**:
```
203.0.113.45/32,198.51.100.0/24,10.0.0.0/16
```
Allows all three ranges above (comma-separated)

### CIDR Calculators

Online tools to help calculate CIDR ranges:
- https://www.ipaddressguide.com/cidr
- https://cidr.xyz/

## Deployment Workflows

### Initial Deployment

1. Deploy backend with IP filtering disabled (for setup):
```bash
cd infrastructure
sam build --template template.yaml
sam deploy --guided
# When prompted for AllowedIPRanges, enter: 0.0.0.0/0
```

2. Add your IP to whitelist:
```bash
./manage-ip-whitelist.sh add-current
```

3. Deploy frontend with IP filtering:
```bash
./deploy-frontend.sh
```

4. Test access from your IP

### Adding New Team Member

```bash
# Option 1: Team member adds their own IP (they need AWS access)
./manage-ip-whitelist.sh add-current

# Option 2: Admin adds team member's IP
./manage-ip-whitelist.sh add 203.0.113.99

# Update frontend bucket policy
./deploy-frontend.sh
```

### Office Network Setup

```bash
# Find your office network's public IP and CIDR range
# (Ask your network administrator)

# Add entire office network
./manage-ip-whitelist.sh add 198.51.100.0/24

# Update frontend
./deploy-frontend.sh
```

### Remote Work / VPN Setup

```bash
# If using VPN, add VPN exit IP
./manage-ip-whitelist.sh add 203.0.113.200/32

# Update frontend
./deploy-frontend.sh
```

### Emergency Access Restoration

If you're locked out (IP changed or accidentally removed):

1. **Via AWS Console** (requires AWS console access):
   - Go to CloudFormation → Stacks → estimation-tool-api
   - Update stack
   - Change `AllowedIPRanges` parameter to `0.0.0.0/0` (temporary)
   - Save and wait for update
   - Use `manage-ip-whitelist.sh` to add proper IPs
   - Redeploy frontend

2. **Via AWS CLI** (from any location with AWS credentials):
```bash
aws cloudformation update-stack \
  --stack-name estimation-tool-api \
  --use-previous-template \
  --parameters \
    ParameterKey=AllowedIPRanges,ParameterValue="0.0.0.0/0" \
    ParameterKey=LLMProvider,UsePreviousValue=true \
    ParameterKey=OpenAIApiKey,UsePreviousValue=true \
    ParameterKey=OpenAIModel,UsePreviousValue=true \
    ParameterKey=BedrockRegion,UsePreviousValue=true \
    ParameterKey=BedrockModel,UsePreviousValue=true \
    ParameterKey=BedrockAgentId,UsePreviousValue=true \
    ParameterKey=BedrockAgentAliasId,UsePreviousValue=true \
    ParameterKey=AtlassianURL,UsePreviousValue=true \
    ParameterKey=AtlassianEmail,UsePreviousValue=true \
    ParameterKey=AtlassianToken,UsePreviousValue=true \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

## Troubleshooting

### Problem: 403 Forbidden when accessing API

**Symptoms**:
- API returns 403 Forbidden
- Browser console shows CORS or network error
- Cannot load estimation tool

**Diagnosis**:
```bash
# Check current whitelist
./manage-ip-whitelist.sh list

# Check your current IP
curl https://checkip.amazonaws.com
```

**Solution**:
```bash
# If your IP is not in whitelist
./manage-ip-whitelist.sh add-current

# Wait 1-2 minutes for update to propagate
# Then retry accessing the API
```

### Problem: Frontend loads but API calls fail

**Symptoms**:
- Frontend HTML/CSS/JS loads fine
- API requests fail with 403
- S3 bucket policy allows your IP but API does not

**Cause**: IP whitelist updated but backend not synced

**Solution**:
```bash
# Verify whitelist matches between frontend and backend
./manage-ip-whitelist.sh list

# If different, the backend may not have updated yet
# Wait 1-2 minutes or check CloudFormation stack status
aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].StackStatus'
```

### Problem: Frontend doesn't load (403 on S3)

**Symptoms**:
- Cannot load frontend at all
- S3 returns 403 Forbidden for index.html
- API works fine

**Cause**: S3 bucket policy not updated after IP whitelist change

**Solution**:
```bash
# Redeploy frontend to update bucket policy
./deploy-frontend.sh
```

### Problem: WebSocket connection fails

**Symptoms**:
- HTTP API works
- Frontend loads
- WebSocket connection rejected

**Cause**: WebSocket authorizer not attached or IP not whitelisted

**Solution**:
```bash
# Verify IP is whitelisted
./manage-ip-whitelist.sh list

# Check CloudWatch Logs for WebSocket authorizer
aws logs tail /aws/lambda/estimation-tool-api-IPAuthorizerFunction-* \
  --follow \
  --filter-pattern "WebSocket"

# If needed, redeploy backend
cd infrastructure
sam build --template template.yaml
sam deploy
```

### Problem: IP whitelist shows 127.0.0.1/32

**Symptoms**:
- All external access denied
- Only localhost can access
- `manage-ip-whitelist.sh list` shows `127.0.0.1/32`

**Cause**: Whitelist set to deny-all mode (default or after `remove-all`)

**Solution**:
```bash
# Add your current IP
./manage-ip-whitelist.sh add-current

# Update frontend
./deploy-frontend.sh
```

### Problem: Dynamic IP keeps changing

**Symptoms**:
- Access works, then stops working hours/days later
- IP address changes frequently
- Home/residential ISP with dynamic IP

**Solutions**:

1. **Add IP range** (if your ISP assigns from a predictable block):
```bash
# Find your IP range from your ISP
# Example: ISP assigns from 203.0.113.0 to 203.0.113.255
./manage-ip-whitelist.sh add 203.0.113.0/24
```

2. **Use VPN with static IP**:
- Subscribe to VPN service with static IP option
- Add VPN exit IP to whitelist
- Always connect via VPN

3. **Temporarily allow all** (NOT RECOMMENDED for production):
```bash
# Only for development/testing
aws cloudformation update-stack \
  --stack-name estimation-tool-api \
  --use-previous-template \
  --parameters \
    ParameterKey=AllowedIPRanges,ParameterValue="0.0.0.0/0" \
    ...other parameters...
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

### Problem: Office network IP unknown

**Solution**:

1. From within office network:
```bash
curl https://checkip.amazonaws.com
```

2. Or ask IT department for:
   - Public IP address or range
   - VPN exit IP (if applicable)
   - Firewall/gateway public IP

3. Add to whitelist:
```bash
./manage-ip-whitelist.sh add <OFFICE_IP>
```

## Security Best Practices

### 1. Use Minimal IP Ranges

- Add only necessary IP addresses/ranges
- Avoid `0.0.0.0/0` (allow all) in production
- Use `/32` for single IPs, not broader ranges unless needed

### 2. Document IP Assignments

Maintain a record of what each IP/range represents:

```
# Example IP whitelist documentation
203.0.113.45/32    - John Doe (home)
198.51.100.0/24    - Office Network
10.0.0.0/16        - Corporate VPN
203.0.113.200/32   - CI/CD Server
```

### 3. Regular Audits

Periodically review and clean up whitelist:

```bash
# Monthly review
./manage-ip-whitelist.sh list

# Remove IPs for former employees or decommissioned infrastructure
# Then redeploy backend and frontend
```

### 4. Emergency Access Plan

Ensure at least 2 people can restore access via:
- AWS Console access
- AWS CLI access with proper credentials
- Knowledge of emergency procedures above

### 5. Monitor Access Logs

Check CloudWatch Logs for denied access attempts:

```bash
# View recent authorization denials
aws logs tail /aws/lambda/estimation-tool-api-IPAuthorizerFunction-* \
  --since 1h \
  --filter-pattern "Allowed: False"
```

### 6. Combine with Other Security

IP filtering is one layer. Also use:
- AWS IAM for infrastructure access
- Atlassian API token for Confluence/Jira
- Bedrock IAM permissions for LLM access
- CloudTrail for audit logging

## Advanced Configuration

### Custom Stack Name

If your CloudFormation stack has a different name:

```bash
# Edit manage-ip-whitelist.sh
# Change line: STACK_NAME="estimation-tool-api"
# To: STACK_NAME="your-custom-stack-name"
```

### Different AWS Region

If deploying to a different region:

```bash
# Edit manage-ip-whitelist.sh
# Change line: AWS_REGION="us-west-2"
# To: AWS_REGION="your-region"
```

### Multiple Environments

For dev/staging/prod environments, use separate stacks:

```bash
# Modify scripts for each environment
STACK_NAME="estimation-tool-api-dev"
STACK_NAME="estimation-tool-api-staging"
STACK_NAME="estimation-tool-api-prod"
```

Each can have different IP whitelists.

## See Also

- [Network Security Guide](NETWORK_SECURITY.md) - Overall network security architecture
- [System Administrator Guide](Sysadminguide.md) - Full deployment guide
- [README](../README.md) - Project overview

