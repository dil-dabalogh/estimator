# Deployment Steps for VPC Endpoint Access

This guide walks you through deploying the Estimation Tool behind VPC endpoints after the implementation.

## Prerequisites

You should have already gathered:
- VPC ID: `vpc-xxxxxxxxxxxxxxxxx`
- VPC CIDR: `10.0.0.0/16` (or your VPC's CIDR block)
- API Gateway Subnets: `subnet-xxxxxxxxxxxxxxxxx,subnet-yyyyyyyyyyyyyyyyy` (at least 2 in different AZs)
- API Gateway Security Group: `sg-xxxxxxxxxxxxxxxxx`
- S3 Route Tables: `rtb-xxxxxxxxxxxxxxxxx,rtb-yyyyyyyyyyyyyyyyy,rtb-zzzzzzzzzzzzzzzzzz,rtb-wwwwwwwwwwwwwwwwww` (all route tables in VPC)

## Step 1: Create Local samconfig.toml

The `samconfig.toml` file contains environment-specific values and should not be committed to version control. Create your local configuration:

```bash
cd infrastructure
cp samconfig.toml.example samconfig.toml
```

Then edit `samconfig.toml` and replace the placeholder values with your actual VPC configuration. See `samconfig.toml.example` for the template format.

**Important**: 
- Replace all placeholder values (e.g., `vpc-xxxxxxxxxxxxxxxxx`) with your actual AWS resource IDs
- The `samconfig.toml` file is already in `.gitignore` and will not be committed
- Keep your local `samconfig.toml` file secure and do not share it publicly

## Step 2: Deploy Backend Stack

The backend deployment will:
1. Create API Gateway VPC Interface Endpoint
2. Create S3 VPC Gateway Endpoint
3. Set resource policies on both APIs
4. Remove old authorizer resources

```bash
cd infrastructure
chore deploy backend
```

Or using SAM directly:

```bash
cd infrastructure
sam build --use-container
sam deploy --config-env dev
```

**Expected Output**:
- Stack deployment completes successfully
- VPC endpoints created (check CloudFormation outputs)
- API Gateway resource policies applied
- Old authorizer resources removed

**Verify VPC Endpoints Created**:
```bash
aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?contains(OutputKey, `VpcEndpoint`)].{Key:OutputKey,Value:OutputValue}' \
  --output table
```

You should see:
- `ApiGatewayVpcEndpointId`: `vpce-xxxxxxxxxxxxxxxxx`
- `S3VpcEndpointId`: `vpce-xxxxxxxxxxxxxxxxx`

## Step 3: Verify VPC Endpoint Status

Check that VPC endpoints are in "available" state:

```bash
# Get endpoint IDs from stack outputs
API_VPCE=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayVpcEndpointId`].OutputValue' \
  --output text)

S3_VPCE=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`S3VpcEndpointId`].OutputValue' \
  --output text)

# Check status
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids $API_VPCE $S3_VPCE \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State,PrivateDnsEnabled]' \
  --output table
```

Both endpoints should show:
- `State`: `available`
- `PrivateDnsEnabled`: `True` (for API Gateway endpoint)

## Step 4: Deploy Frontend

The frontend deployment will:
1. Fetch S3 VPC endpoint ID from stack outputs
2. Configure S3 bucket policy to allow only VPC endpoint access
3. Block all public access

```bash
cd infrastructure
chore deploy frontend
```

Or using the shell script:

```bash
cd infrastructure
./deploy-frontend.sh
```

**Expected Output**:
- Frontend builds successfully
- S3 bucket policy applied with VPC endpoint restrictions
- Public access fully blocked

## Step 5: Test Access from VPN

### Connect to Diligent VPN

Ensure you're connected to the Diligent VPN before testing.

### Test Frontend Access

1. Get the frontend URL from deployment output
2. Open in browser (while connected to VPN)
3. Should load normally

### Test API Access

```bash
# Get API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text)

# Test health endpoint
curl $API_URL/health
```

Should return: `{"status":"healthy"}`

### Test WebSocket

The WebSocket URL is also available from stack outputs. Test from your frontend application.

## Step 6: Verify Public Access is Blocked

### Disconnect from VPN

Disconnect from Diligent VPN to test public access blocking.

### Test Frontend (Should Fail)

```bash
# Get frontend URL
FRONTEND_URL="http://estimation-tool-frontend-ACCOUNT_ID.s3-website-us-west-2.amazonaws.com"

# Try to access
curl -I $FRONTEND_URL
```

**Expected**: `403 Forbidden`

### Test API (Should Fail)

```bash
# Try to access API
curl $API_URL/health
```

**Expected**: `403 Forbidden` or connection refused

## Step 7: Verify DNS Resolution (Optional)

From a machine connected to VPN, verify DNS resolves to private IPs:

```bash
# Should resolve to private IP (10.x.x.x) if Private DNS is enabled
nslookup execute-api.us-west-2.amazonaws.com
nslookup s3.us-west-2.amazonaws.com
```

If it resolves to public IPs, check that Private DNS is enabled on the API Gateway endpoint.

## Troubleshooting

### VPC Endpoints Not Created

**Symptoms**: Stack deployment fails or endpoints missing from outputs

**Solutions**:
1. Check CloudFormation stack events for errors
2. Verify VPC ID, subnet IDs, and security group IDs are correct
3. Ensure you have permissions to create VPC endpoints:
   ```bash
   aws iam get-user-policy --user-name YOUR_USER --policy-name YOUR_POLICY
   ```
4. Check route tables exist for S3 Gateway endpoint

### Cannot Access from VPN

**Symptoms**: 403 Forbidden even when connected to VPN

**Solutions**:
1. **Verify VPN Connection**:
   ```bash
   # Check if you can resolve AWS endpoints
   nslookup execute-api.us-west-2.amazonaws.com
   ```

2. **Check Endpoint State**:
   ```bash
   aws ec2 describe-vpc-endpoints \
     --vpc-endpoint-ids $API_VPCE \
     --query 'VpcEndpoints[0].State'
   ```
   Should be `available`

3. **Verify Private DNS**:
   ```bash
   aws ec2 describe-vpc-endpoints \
     --vpc-endpoint-ids $API_VPCE \
     --query 'VpcEndpoints[0].PrivateDnsEnabled'
   ```
   Should be `True`

4. **Check Security Group**:
   ```bash
   aws ec2 describe-security-groups \
     --group-ids sg-xxxxxxxxxxxxxxxxx \
     --query 'SecurityGroups[0].IpPermissions'
   ```
   Should allow inbound HTTPS (443) from VPC CIDR

### Resource Policy Not Applied

**Symptoms**: API accessible from public internet

**Solutions**:
1. Check CloudFormation custom resource status:
   ```bash
   aws cloudformation describe-stack-resources \
     --stack-name estimation-tool-api \
     --logical-resource-id ApiGatewayResourcePolicy \
     --query 'StackResources[0].ResourceStatus'
   ```

2. Check Lambda logs for resource policy handler:
   ```bash
   aws logs tail /aws/lambda/estimation-tool-api-ApiGatewayResourcePolicyFunction-* --follow
   ```

3. Manually verify resource policy:
   ```bash
   aws apigatewayv2 get-resource-policy --api-id $API_ID
   ```

### S3 Bucket Policy Issues

**Symptoms**: Frontend not accessible from VPN

**Solutions**:
1. Verify bucket policy:
   ```bash
   aws s3api get-bucket-policy --bucket estimation-tool-frontend-ACCOUNT_ID
   ```

2. Check public access block:
   ```bash
   aws s3api get-public-access-block --bucket estimation-tool-frontend-ACCOUNT_ID
   ```

3. Verify S3 VPC endpoint ID in bucket policy matches stack output

## Rollback Plan

If you need to rollback to IP whitelist:

1. **Restore Previous Template**: Check out previous commit
   ```bash
   git log --oneline infrastructure/template.yaml
   git checkout <previous-commit> -- infrastructure/template.yaml
   ```

2. **Update samconfig.toml**: Restore `AllowedIPRanges` parameter

3. **Redeploy**:
   ```bash
   chore deploy backend
   ```

4. **Clean Up**: Delete VPC endpoints manually if needed:
   ```bash
   aws ec2 delete-vpc-endpoint --vpc-endpoint-id $API_VPCE
   aws ec2 delete-vpc-endpoint --vpc-endpoint-id $S3_VPCE
   ```

## Next Steps After Successful Deployment

1. **Monitor**: Check CloudWatch logs for any access issues
2. **Document**: Update team documentation with new access method
3. **Clean Up**: Remove deprecated IP whitelist scripts (optional, after migration period)
4. **Test**: Perform full end-to-end testing from VPN

## Summary Checklist

- [ ] Updated `samconfig.toml` with VPC endpoint parameters
- [ ] Removed `AllowedIPRanges` from `samconfig.toml`
- [ ] Deployed backend stack successfully
- [ ] Verified VPC endpoints created and in "available" state
- [ ] Verified Private DNS enabled on API Gateway endpoint
- [ ] Deployed frontend successfully
- [ ] Tested access from VPN (frontend, API, WebSocket)
- [ ] Verified public access is blocked (disconnected from VPN)
- [ ] All tests passing




