#!/bin/bash

# Script to manually set up AWS WAF for IP whitelisting on HTTP API Gateway
# Run this after deploying the API with SAM

set -e  # Exit on error
set -u  # Exit on undefined variable

# Enable verbose output
set -x

# Configuration
ALLOWED_IPS=${1:-"0.0.0.0/0"}  # Default: allow all
STACK_NAME="estimation-tool-api"

echo "========================================="
echo "Setting up WAF for API Gateway"
echo "========================================="
echo "Allowed IP ranges: $ALLOWED_IPS"
echo ""

# Get AWS region
echo "Step 1: Getting AWS configuration..."
# Try multiple methods to get the region
AWS_REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null)}
AWS_REGION=${AWS_REGION:-$(aws configure get region --profile default 2>/dev/null)}
AWS_REGION=${AWS_REGION:-"us-west-2"}  # Default fallback

if [ -z "$AWS_REGION" ]; then
  echo "ERROR: Could not determine AWS region"
  echo "Please set AWS_REGION environment variable or configure aws cli"
  exit 1
fi
echo "Region: $AWS_REGION"

# Get AWS account
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT" ]; then
  echo "ERROR: Could not get AWS account ID"
  exit 1
fi
echo "Account: $AWS_ACCOUNT"
echo ""

# Get the API Gateway ID from CloudFormation stack
echo "Step 2: Getting API Gateway ID from CloudFormation..."
API_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text 2>&1)

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to get CloudFormation stack outputs"
  echo "Make sure the stack '$STACK_NAME' exists and is deployed"
  exit 1
fi

API_ID=$(echo "$API_URL" | cut -d'/' -f3 | cut -d'.' -f1)
if [ -z "$API_ID" ]; then
  echo "ERROR: Could not extract API ID from URL: $API_URL"
  exit 1
fi

echo "API ID: $API_ID"
echo "API URL: $API_URL"
echo ""

# Convert comma-separated IPs to array
echo "Step 3: Preparing IP addresses..."
IFS=',' read -ra IP_ARRAY <<< "$ALLOWED_IPS"
echo "IP addresses to whitelist: ${IP_ARRAY[@]}"
echo ""

# Check if IP Set already exists
echo "Step 4: Checking for existing IP Set..."
EXISTING_IP_SET=$(aws wafv2 list-ip-sets \
  --scope REGIONAL \
  --region $AWS_REGION \
  --query "IPSets[?Name=='EstimationToolAllowedIPs'].Id" \
  --output text)

if [ -n "$EXISTING_IP_SET" ]; then
  echo "ERROR: IP Set 'EstimationToolAllowedIPs' already exists (ID: $EXISTING_IP_SET)"
  echo "To update existing IP ranges, use ./update-waf-ips.sh instead"
  echo "Or delete the existing WAF first"
  exit 1
fi
echo "No existing IP Set found - proceeding with creation"
echo ""

# Create IP Set
echo "Step 5: Creating IP Set..."
IP_SET_RESPONSE=$(aws wafv2 create-ip-set \
  --name EstimationToolAllowedIPs \
  --scope REGIONAL \
  --ip-address-version IPV4 \
  --addresses "${IP_ARRAY[@]}" \
  --region $AWS_REGION \
  --output json 2>&1)

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to create IP Set"
  echo "$IP_SET_RESPONSE"
  exit 1
fi

IP_SET_ARN=$(echo $IP_SET_RESPONSE | jq -r '.Summary.ARN')
IP_SET_ID=$(echo $IP_SET_RESPONSE | jq -r '.Summary.Id')

if [ -z "$IP_SET_ID" ] || [ "$IP_SET_ID" = "null" ]; then
  echo "ERROR: Could not get IP Set ID from response"
  echo "$IP_SET_RESPONSE"
  exit 1
fi

echo "✓ IP Set created successfully"
echo "  ID: $IP_SET_ID"
echo "  ARN: $IP_SET_ARN"
echo ""

# Wait for IP Set to propagate (avoid race condition)
echo "Waiting 5 seconds for IP Set to propagate..."
sleep 5
echo ""

# Create Web ACL
echo "Step 6: Creating Web ACL..."
WAF_RESPONSE=$(aws wafv2 create-web-acl \
  --name EstimationToolWAF \
  --scope REGIONAL \
  --default-action Block={} \
  --rules '[
    {
      "Name": "AllowCompanyIPs",
      "Priority": 0,
      "Statement": {
        "IPSetReferenceStatement": {
          "ARN": "'"$IP_SET_ARN"'"
        }
      },
      "Action": {
        "Allow": {}
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "AllowCompanyIPs"
      }
    }
  ]' \
  --visibility-config '{
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "EstimationToolWAF"
  }' \
  --region $AWS_REGION \
  --output json 2>&1)

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to create Web ACL"
  echo "$WAF_RESPONSE"
  echo ""
  echo "Cleaning up - deleting IP Set..."
  aws wafv2 delete-ip-set \
    --scope REGIONAL \
    --id $IP_SET_ID \
    --name EstimationToolAllowedIPs \
    --lock-token $(aws wafv2 get-ip-set --scope REGIONAL --id $IP_SET_ID --name EstimationToolAllowedIPs --region $AWS_REGION --query 'LockToken' --output text) \
    --region $AWS_REGION
  exit 1
fi

WAF_ARN=$(echo $WAF_RESPONSE | jq -r '.Summary.ARN')
WAF_ID=$(echo $WAF_RESPONSE | jq -r '.Summary.Id')

if [ -z "$WAF_ID" ] || [ "$WAF_ID" = "null" ]; then
  echo "ERROR: Could not get Web ACL ID from response"
  echo "$WAF_RESPONSE"
  exit 1
fi

echo "✓ Web ACL created successfully"
echo "  ID: $WAF_ID"
echo "  ARN: $WAF_ARN"
echo ""

# Associate WAF with API Gateway
# For HTTP API, construct the stage ARN manually (HTTP APIs don't return StageArn in get-stage)
echo "Step 7: Constructing API Gateway stage ARN..."

# Verify the stage exists first
STAGE_CHECK=$(aws apigatewayv2 get-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --region $AWS_REGION 2>&1)

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to verify API Gateway stage exists"
  echo "$STAGE_CHECK"
  exit 1
fi

# Construct the ARN manually for HTTP API
STAGE_ARN="arn:aws:apigateway:${AWS_REGION}::/apis/${API_ID}/stages/\$default"

echo "✓ Stage ARN constructed"
echo "  ARN: $STAGE_ARN"
echo ""

echo "Step 8: Associating WAF with API Gateway..."
ASSOC_RESPONSE=$(aws wafv2 associate-web-acl \
  --web-acl-arn $WAF_ARN \
  --resource-arn "$STAGE_ARN" \
  --region $AWS_REGION 2>&1)

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to associate WAF with API Gateway"
  echo "$ASSOC_RESPONSE"
  echo ""
  echo "The WAF and IP Set were created but not associated."
  echo "You may need to associate manually or delete and try again."
  exit 1
fi

echo "✓ WAF associated with API Gateway successfully"
echo ""

# Verify association
echo "Step 9: Verifying WAF association..."
VERIFY=$(aws wafv2 get-web-acl-for-resource \
  --resource-arn "$STAGE_ARN" \
  --region $AWS_REGION \
  --query 'WebACL.Name' \
  --output text 2>&1)

if [ "$VERIFY" = "EstimationToolWAF" ]; then
  echo "✓ Association verified successfully"
else
  echo "WARNING: Could not verify association (but may have succeeded)"
  echo "Response: $VERIFY"
fi

echo ""
echo "========================================="
echo "✅ WAF SETUP COMPLETE!"
echo "========================================="
echo ""
echo "WAF Details:"
echo "  WAF ID: $WAF_ID"
echo "  IP Set ID: $IP_SET_ID"
echo "  Region: $AWS_REGION"
echo ""
echo "Your API is now restricted to IP ranges: $ALLOWED_IPS"
echo ""
echo "To test:"
echo "  With allowed IP: curl $API_URL/health"
echo "  Without allowed IP: Should get 403 Forbidden"
echo ""
echo "To update IP ranges later:"
echo "  ./update-waf-ips.sh \"IP1/32,IP2/24\""
echo ""

