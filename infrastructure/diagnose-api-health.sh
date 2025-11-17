#!/bin/bash

set -e

STACK_NAME="estimation-tool-api"
AWS_REGION="us-west-2"

echo "========================================="
echo "API Health Endpoint Diagnostics"
echo "========================================="
echo ""

echo "Step 1: Checking if stack exists..."
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].StackStatus' \
  --output text 2>&1)

if [ $? -ne 0 ]; then
  echo "❌ Stack '$STACK_NAME' not found"
  echo "Available stacks:"
  aws cloudformation list-stacks \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
    --region $AWS_REGION \
    --query 'StackSummaries[].StackName' \
    --output table
  exit 1
fi

echo "✓ Stack status: $STACK_STATUS"
echo ""

echo "Step 2: Getting API URL..."
API_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text)

if [ -z "$API_URL" ]; then
  echo "❌ Could not get API URL from stack outputs"
  exit 1
fi

echo "API URL: $API_URL"
echo ""

echo "Step 3: Getting Lambda function name..."
FUNCTION_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'StackResources[?LogicalResourceId==`EstimationFunction`].PhysicalResourceId' \
  --output text)

if [ -z "$FUNCTION_NAME" ]; then
  echo "❌ Lambda function not found in stack"
  exit 1
fi

echo "Lambda function: $FUNCTION_NAME"
echo ""

echo "Step 4: Checking Lambda function configuration..."
aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --region $AWS_REGION \
  --query '{Runtime:Runtime,Handler:Handler,MemorySize:MemorySize,Timeout:Timeout,LastModified:LastModified}' \
  --output json

echo ""

echo "Step 5: Checking Lambda environment variables..."
ENV_VARS=$(aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --region $AWS_REGION \
  --query 'Environment.Variables' \
  --output json)

echo "$ENV_VARS" | jq 'to_entries | map({key: .key, value: (if (.key | contains("TOKEN") or contains("KEY")) then "***REDACTED***" else .value end)}) | from_entries'
echo ""

echo "Step 6: Getting recent Lambda error logs..."
echo "Checking for errors in the last 10 minutes..."
aws logs filter-log-events \
  --log-group-name "/aws/lambda/$FUNCTION_NAME" \
  --region $AWS_REGION \
  --start-time $(($(date +%s) * 1000 - 600000)) \
  --filter-pattern "ERROR" \
  --query 'events[*].[timestamp,message]' \
  --output text | head -20 || echo "No error logs found"

echo ""

echo "Step 7: Getting recent Lambda invocation logs..."
aws logs tail /aws/lambda/$FUNCTION_NAME \
  --since 10m \
  --region $AWS_REGION \
  --format short \
  2>&1 | head -50 || echo "No recent logs found"

echo ""

echo "Step 8: Testing health endpoint..."
echo "Testing: $API_URL/health"
echo ""

RESPONSE=$(curl -v -s -w "\n\nHTTP_STATUS:%{http_code}" $API_URL/health 2>&1)
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d':' -f2)

echo "$RESPONSE"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Health endpoint is working!"
elif [ "$HTTP_STATUS" = "403" ]; then
  echo "❌ 403 Forbidden - IP address is not whitelisted"
  echo ""
  echo "Your current IP:"
  curl -s https://checkip.amazonaws.com
  echo ""
  echo "To allow your IP, update the AllowedIPRanges parameter:"
  echo "  cd infrastructure && sam deploy --parameter-overrides AllowedIPRanges=\"\$(curl -s https://checkip.amazonaws.com)/32\""
elif [ "$HTTP_STATUS" = "500" ]; then
  echo "❌ 500 Internal Server Error - Lambda execution error"
  echo ""
  echo "Check the logs above for details. Common issues:"
  echo "  - Missing required environment variables"
  echo "  - Python import errors"
  echo "  - Missing dependencies in Lambda layer"
  echo ""
  echo "To see full logs:"
  echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"
else
  echo "❓ Unexpected HTTP status: $HTTP_STATUS"
fi

echo ""
echo "========================================="
echo "Diagnostic Complete"
echo "========================================="

