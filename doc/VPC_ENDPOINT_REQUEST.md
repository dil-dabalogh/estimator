# VPC Endpoint Creation Request

## Request Summary

We need two VPC endpoints created in the shared VPC `vpc-0debf6fec89321668` (us-west-2) to enable secure access to our Estimation Tool application.

## Required Endpoints

### 1. API Gateway VPC Interface Endpoint

**Purpose**: Enable private access to API Gateway (HTTP and WebSocket APIs) from within the VPC.

**Specifications**:
- **Service Name**: `com.amazonaws.us-west-2.execute-api`
- **VPC ID**: `vpc-0debf6fec89321668`
- **Type**: Interface
- **Subnets**: 
  - `subnet-0d0461af8faa47862` (us-west-2a)
  - `subnet-00709cdde2bfc1cad` (us-west-2b)
  - At least 2 subnets in different Availability Zones (we have 2 provided)
- **Security Group**: `sg-0d767bd8c679a2c59`
  - **Important**: Security group must allow inbound HTTPS (port 443) from VPC CIDR `10.0.0.0/16`
- **Private DNS**: Enabled (required for proper DNS resolution)
- **Policy**: Allow all actions (endpoint-level policy)

**AWS CLI Command** (for reference):
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0debf6fec89321668 \
  --service-name com.amazonaws.us-west-2.execute-api \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-0d0461af8faa47862 subnet-00709cdde2bfc1cad \
  --security-group-ids sg-0d767bd8c679a2c59 \
  --private-dns-enabled \
  --region us-west-2
```

### 2. S3 VPC Gateway Endpoint

**Purpose**: Enable private access to S3 buckets from within the VPC.

**Specifications**:
- **Service Name**: `com.amazonaws.us-west-2.s3`
- **VPC ID**: `vpc-0debf6fec89321668`
- **Type**: Gateway
- **Route Tables**: All route tables in the VPC
  - `rtb-0d7b4aa83ad8d4a37`
  - `rtb-098de2a98588c76c3`
  - `rtb-02bf8cba75a7cb133`
  - `rtb-0ed6e958148479c62`
- **Policy**: Allow all S3 actions (endpoint-level policy)

**AWS CLI Command** (for reference):
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0debf6fec89321668 \
  --service-name com.amazonaws.us-west-2.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids rtb-0d7b4aa83ad8d4a37 rtb-098de2a98588c76c3 rtb-02bf8cba75a7cb133 rtb-0ed6e958148479c62 \
  --region us-west-2
```

## Security Group Configuration

**Security Group**: `sg-0d767bd8c679a2c59`

**Required Inbound Rule**:
- **Type**: HTTPS (TCP)
- **Port**: 443
- **Source**: `10.0.0.0/16` (VPC CIDR block)

This rule is required for the API Gateway Interface endpoint to function properly.

## After Creation

Once the endpoints are created, please provide:
1. **API Gateway VPC Interface Endpoint ID** (format: `vpce-xxxxxxxxxxxxxxxxx`)
2. **S3 VPC Gateway Endpoint ID** (format: `vpce-yyyyyyyyyyyyyyyyy`)

We will use these endpoint IDs in our CloudFormation deployment configuration.

## Verification

After creation, you can verify the endpoints with:

```bash
# Check API Gateway endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-0debf6fec89321668" \
            "Name=service-name,Values=com.amazonaws.us-west-2.execute-api" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,ServiceName]' \
  --output table \
  --region us-west-2

# Check S3 endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-0debf6fec89321668" \
            "Name=service-name,Values=com.amazonaws.us-west-2.s3" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,ServiceName]' \
  --output table \
  --region us-west-2
```

## Cost Impact

- **API Gateway Interface Endpoint**: ~$7.20/month per endpoint per AZ
  - With 2 AZs: ~$14.40/month
  - Data processing: ~$0.01/GB
- **S3 Gateway Endpoint**: Free (no charge)

**Total estimated cost**: ~$14.40/month minimum

## Questions?

If you have any questions or need clarification on any of these requirements, please let us know.

