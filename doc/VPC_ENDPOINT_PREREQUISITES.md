# VPC Endpoint Prerequisites Guide

This document outlines what information you need to gather before implementing VPN-only access restriction.

## Required Information

### 1. VPC ID Where Diligent VPN is Configured

**What you need**: The VPC ID (format: `vpc-xxxxxxxxxxxxxxxxx`) where your Diligent VPN connects.

**How to find it**:

**Option A: AWS Console**
1. Go to AWS Console → VPC → Your VPCs
2. Look for VPCs with tags like "Diligent", "Workload", or your organization name
3. Note the VPC ID

**Option B: AWS CLI**
```bash
# List all VPCs
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' --output table

# Filter by tag (if tagged)
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=*Diligent*" --query 'Vpcs[*].[VpcId,CidrBlock]' --output table
```

**Option C: Ask Your IT/Network Team**
- Ask: "What is the VPC ID for the Diligent Workload VPC where VPN users connect?"
- They should provide: `vpc-xxxxxxxxxxxxxxxxx`

**What to provide**: Just the VPC ID string (e.g., `vpc-0123456789abcdef0`)

---

### 2. API Gateway VPC Endpoint

**What you need**: Determine if an API Gateway VPC endpoint exists, or if one needs to be created.

**How to check if it exists**:

**Option A: AWS Console**
1. Go to AWS Console → VPC → Endpoints
2. Filter by service name: `com.amazonaws.<region>.execute-api`
   - For us-west-2: `com.amazonaws.us-west-2.execute-api`
3. Check if any endpoints exist in your VPC
4. Note the VPC Endpoint ID (format: `vpce-xxxxxxxxxxxxxxxxx`)

**Option B: AWS CLI**
```bash
# Replace VPC_ID with your VPC ID from step 1
VPC_ID="vpc-xxxxxxxxxxxxxxxxx"
REGION="us-west-2"

# Check for existing API Gateway VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=com.amazonaws.$REGION.execute-api" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,ServiceName]' \
  --output table
```

**If endpoint exists**:
- Provide the VPC Endpoint ID: `vpce-xxxxxxxxxxxxxxxxx`
- Verify it's in "available" state

**If endpoint does NOT exist**:
- We will need to create it (requires VPC ID, subnet IDs, security group ID)
- See "Creating VPC Endpoints" section below

**What to provide**: 
- VPC Endpoint ID if it exists: `vpce-xxxxxxxxxxxxxxxxx`
- OR indicate "needs to be created"

---

### 3. S3 VPC Endpoint

**What you need**: Determine if an S3 VPC endpoint exists. S3 can use either:
- **Gateway Endpoint** (free, preferred for S3) - format: `vpce-xxxxxxxxxxxxxxxxx`
- **Interface Endpoint** (costs money) - format: `vpce-xxxxxxxxxxxxxxxxx`

**How to check if it exists**:

**Option A: AWS Console**
1. Go to AWS Console → VPC → Endpoints
2. Filter by service name: `com.amazonaws.<region>.s3`
   - For us-west-2: `com.amazonaws.us-west-2.s3`
3. Check if any endpoints exist in your VPC
4. Note the VPC Endpoint ID and type (Gateway or Interface)

**Option B: AWS CLI**
```bash
# Replace VPC_ID with your VPC ID from step 1
VPC_ID="vpc-xxxxxxxxxxxxxxxxx"
REGION="us-west-2"

# Check for existing S3 VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=com.amazonaws.$REGION.s3" \
  --query 'VpcEndpoints[*].[VpcEndpointId,VpcEndpointType,State,ServiceName]' \
  --output table
```

**If endpoint exists**:
- Provide the VPC Endpoint ID: `vpce-xxxxxxxxxxxxxxxxx`
- Note the type (Gateway or Interface)

**If endpoint does NOT exist**:
- We will create a Gateway Endpoint (free, recommended for S3)
- Requires: VPC ID and route table IDs

**What to provide**:
- VPC Endpoint ID if it exists: `vpce-xxxxxxxxxxxxxxxxx`
- OR indicate "needs to be created"

---

### 4. VPC Endpoint Security Groups (If Using Interface Endpoints)

**What you need**: Security group IDs attached to VPC interface endpoints.

**Note**: Gateway endpoints (for S3) don't use security groups, so skip this if using Gateway endpoint.

**How to find security groups**:

**Option A: AWS Console**
1. Go to AWS Console → VPC → Endpoints
2. Click on your API Gateway VPC endpoint
3. Go to "Security" tab
4. Note the Security Group IDs (format: `sg-xxxxxxxxxxxxxxxxx`)

**Option B: AWS CLI**
```bash
# Replace VPC_ENDPOINT_ID with your endpoint ID
VPC_ENDPOINT_ID="vpce-xxxxxxxxxxxxxxxxx"

# Get security groups for endpoint
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids $VPC_ENDPOINT_ID \
  --query 'VpcEndpoints[0].Groups[*].GroupId' \
  --output text
```

**What to provide**: Security group ID(s): `sg-xxxxxxxxxxxxxxxxx` (comma-separated if multiple)

---

### 5. Additional Information for Creating VPC Endpoints (If Needed)

If endpoints don't exist, you'll need:

#### For API Gateway Interface Endpoint:
- **VPC ID**: From step 1
- **Subnet IDs**: At least 2 subnets in different AZs (format: `subnet-xxxxxxxxxxxxxxxxx`)
- **Security Group ID**: Existing security group or create new one

**How to find subnet IDs**:
```bash
VPC_ID="vpc-xxxxxxxxxxxxxxxxx"

# List subnets in VPC
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].[SubnetId,AvailabilityZone,CidrBlock]' \
  --output table
```

#### For S3 Gateway Endpoint:
- **VPC ID**: From step 1
- **Route Table IDs**: Route tables for subnets that need S3 access

**How to find route table IDs**:
```bash
VPC_ID="vpc-xxxxxxxxxxxxxxxxx"

# List route tables in VPC
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[*].[RouteTableId,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

---

## Testing VPN Connectivity

Before proceeding, verify you can access AWS resources from the VPN:

**Test 1: Verify VPN Connection**
```bash
# From a machine connected to Diligent VPN
# Check if you can resolve AWS service endpoints
nslookup execute-api.us-west-2.amazonaws.com
nslookup s3.us-west-2.amazonaws.com
```

**Test 2: Verify VPC Endpoint Access (If Endpoints Exist)**
```bash
# Test API Gateway endpoint (if exists)
# This should resolve to a private IP (10.x.x.x) if Private DNS is enabled
nslookup execute-api.us-west-2.amazonaws.com

# Test S3 endpoint (if exists)
nslookup s3.us-west-2.amazonaws.com
```

**Test 3: Verify AWS CLI Access**
```bash
# From VPN-connected machine
aws sts get-caller-identity
aws ec2 describe-vpcs --region us-west-2
```

---

## Information Checklist

Before starting implementation, gather:

- [ ] **VPC ID**: `vpc-xxxxxxxxxxxxxxxxx`
- [ ] **API Gateway VPC Endpoint ID** (if exists): `vpce-xxxxxxxxxxxxxxxxx` OR "needs creation"
- [ ] **S3 VPC Endpoint ID** (if exists): `vpce-xxxxxxxxxxxxxxxxx` OR "needs creation"
- [ ] **Security Group IDs** (for interface endpoints): `sg-xxxxxxxxxxxxxxxxx`
- [ ] **Subnet IDs** (if creating endpoints): `subnet-xxxxxxxxxxxxxxxxx` (at least 2)
- [ ] **Route Table IDs** (if creating S3 gateway endpoint): `rtb-xxxxxxxxxxxxxxxxx`
- [ ] **VPC CIDR Block** (optional, for additional validation): `10.0.0.0/16`

---

## What to Provide

Once you have the information, provide it in this format:

```
VPC ID: vpc-0123456789abcdef0
API Gateway VPC Endpoint: vpce-abcdef1234567890 (exists) OR "create new"
S3 VPC Endpoint: vpce-9876543210fedcba (exists) OR "create new"
Security Groups: sg-0123456789abcdef0
Subnets (if creating): subnet-aaa111,subnet-bbb222
Route Tables (if creating S3 endpoint): rtb-ccc333,rtb-ddd444
VPC CIDR (optional): 10.0.0.0/16
```

---

## If You Don't Have Access

If you don't have AWS Console or CLI access to gather this information:

1. **Contact your IT/Network team** and ask for:
   - VPC ID for Diligent Workload VPC
   - Whether API Gateway and S3 VPC endpoints exist
   - If endpoints exist, their IDs
   - If endpoints don't exist, whether they can create them

2. **Provide them with this document** so they know what information is needed

3. **Alternative**: If you have AWS SSO/console access but limited permissions:
   - Ask for read-only access to VPC service
   - Or ask them to run the CLI commands above and share the output

---

## Next Steps

Once you have all the information:
1. Share it with the implementation team
2. We'll update the CloudFormation template with the correct values
3. We'll create VPC endpoints if they don't exist
4. We'll test connectivity from VPN

