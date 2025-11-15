#!/bin/bash

# Diagnostic script to check Lambda authorizer setup

set -e

STACK_NAME="estimation-tool-api"
AWS_REGION="us-west-2"

echo "========================================="
echo "Lambda Authorizer Diagnostics"
echo "========================================="
echo ""

echo "Step 1: Checking if authorizer Lambda exists..."
AUTH_FUNCTION=$(aws cloudformation describe-stack-resources \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'StackResources[?LogicalResourceId==`IPAuthorizerFunction`].PhysicalResourceId' \
  --output text 2>&1)

if [ $? -ne 0 ] || [ -z "$AUTH_FUNCTION" ]; then
  echo "❌ Authorizer Lambda NOT found in stack"
  echo "The IPAuthorizerFunction resource doesn't exist."
  echo "Did the deployment succeed? Check CloudFormation console."
  exit 1
fi

echo "✓ Authorizer Lambda found: $AUTH_FUNCTION"
echo ""

echo "Step 2: Checking authorizer environment variables..."
aws lambda get-function-configuration \
  --function-name $AUTH_FUNCTION \
  --region $AWS_REGION \
  --query 'Environment.Variables.ALLOWED_IP_RANGES' \
  --output text

echo ""

echo "Step 3: Checking API Gateway authorizer configuration..."
API_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text | cut -d'/' -f3 | cut -d'.' -f1)

echo "API ID: $API_ID"
echo ""

AUTHORIZERS=$(aws apigatewayv2 get-authorizers \
  --api-id $API_ID \
  --region $AWS_REGION \
  --output json)

echo "Authorizers configured:"
echo "$AUTHORIZERS" | jq -r '.Items[] | "  Name: \(.Name), Type: \(.AuthorizerType), URI: \(.AuthorizerUri)"'
echo ""

echo "Step 4: Checking if authorizer is set as default..."
API_CONFIG=$(aws apigatewayv2 get-api \
  --api-id $API_ID \
  --region $AWS_REGION \
  --output json)

echo "$API_CONFIG" | jq '{ApiId, Name, RouteSelectionExpression}'
echo ""

echo "Step 5: Checking routes and their authorizers..."
aws apigatewayv2 get-routes \
  --api-id $API_ID \
  --region $AWS_REGION \
  --query 'Items[].[RouteKey,AuthorizerId,AuthorizationType]' \
  --output table

echo ""
echo "Step 6: Recent authorizer invocations (last 10 minutes)..."
aws logs tail /aws/lambda/$AUTH_FUNCTION \
  --since 10m \
  --region $AWS_REGION \
  2>&1 || echo "No recent logs found"

echo ""
echo "Step 7: Testing API endpoint..."
API_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text)

echo "API URL: $API_URL"
echo "Making test request..."
curl -v $API_URL/health 2>&1 | grep -E "(HTTP|x-amzn-RequestId|Forbidden|Unauthorized)"

echo ""
echo "========================================="
echo "Diagnostic Complete"
echo "========================================="

