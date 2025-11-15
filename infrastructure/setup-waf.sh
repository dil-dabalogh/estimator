#!/bin/bash

# Script to manually set up AWS WAF for IP whitelisting on HTTP API Gateway
# Run this after deploying the API with SAM

set -e

# Configuration
ALLOWED_IPS=${1:-"0.0.0.0/0"}  # Default: allow all
STACK_NAME="estimation-tool-api"

echo "Setting up WAF for API Gateway..."
echo "Allowed IP ranges: $ALLOWED_IPS"

# Get the API Gateway ID from CloudFormation stack
API_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text | cut -d'/' -f3 | cut -d'.' -f1)

AWS_REGION=$(aws configure get region)
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

echo "API ID: $API_ID"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT"

# Convert comma-separated IPs to array
IFS=',' read -ra IP_ARRAY <<< "$ALLOWED_IPS"

# Create IP Set
echo "Creating IP Set..."
IP_SET_RESPONSE=$(aws wafv2 create-ip-set \
  --name EstimationToolAllowedIPs \
  --scope REGIONAL \
  --ip-address-version IPV4 \
  --addresses "${IP_ARRAY[@]}" \
  --region $AWS_REGION \
  --output json)

IP_SET_ARN=$(echo $IP_SET_RESPONSE | jq -r '.Summary.ARN')
IP_SET_ID=$(echo $IP_SET_RESPONSE | jq -r '.Summary.Id')

echo "IP Set created: $IP_SET_ID"

# Create Web ACL
echo "Creating Web ACL..."
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
  --output json)

WAF_ARN=$(echo $WAF_RESPONSE | jq -r '.Summary.ARN')
WAF_ID=$(echo $WAF_RESPONSE | jq -r '.Summary.Id')

echo "Web ACL created: $WAF_ID"

# Associate WAF with API Gateway
# For HTTP API, we need to get the actual stage ARN
echo "Getting API Gateway stage ARN..."
STAGE_ARN=$(aws apigatewayv2 get-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --query 'StageArn' \
  --output text \
  --region $AWS_REGION)

echo "Stage ARN: $STAGE_ARN"

echo "Associating WAF with API Gateway..."
aws wafv2 associate-web-acl \
  --web-acl-arn $WAF_ARN \
  --resource-arn "$STAGE_ARN" \
  --region $AWS_REGION

echo ""
echo "✅ WAF setup complete!"
echo ""
echo "WAF ID: $WAF_ID"
echo "IP Set ID: $IP_SET_ID"
echo ""
echo "Your API is now restricted to IP ranges: $ALLOWED_IPS"
echo ""
echo "To update IP ranges later:"
echo "  ./infrastructure/update-waf-ips.sh \"IP1/32,IP2/24\""

