#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

STACK_NAME="estimation-tool-api"
AWS_REGION="us-west-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="estimation-tool-frontend-${ACCOUNT_ID}"

show_usage() {
    cat << EOF
Frontend Deployment Script for Estimation Tool

Usage:
  $0 [OPTIONS]

Options:
  --api-url URL      Override API URL (default: fetch from CloudFormation)
  --bucket NAME      Override S3 bucket name (default: estimation-tool-frontend-ACCOUNT_ID)
  --help             Show this help message

Examples:
  $0                                                    # Deploy with VPC endpoint access
  $0 --api-url https://api.example.com                  # Use custom API URL

EOF
    exit 1
}

API_URL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --bucket)
            BUCKET_NAME="$2"
            shift 2
            ;;
        --help)
            show_usage
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            show_usage
            ;;
    esac
done

echo "========================================="
echo "Deploy Frontend to S3"
echo "========================================="
echo ""

if [ -z "$API_URL" ]; then
    echo "Fetching API URL from CloudFormation stack..."
    API_URL=$(aws cloudformation describe-stacks \
      --stack-name "$STACK_NAME" \
      --region "$AWS_REGION" \
      --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
      --output text 2>&1)
    
    if [ $? -ne 0 ] || [ -z "$API_URL" ]; then
        echo "ERROR: Could not retrieve API URL from stack '$STACK_NAME'"
        echo "Please provide --api-url manually or ensure the backend stack is deployed"
        exit 1
    fi
    
    echo "API URL: $API_URL"
fi

WEBSOCKET_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketApiUrl`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -n "$WEBSOCKET_URL" ]; then
    echo "WebSocket URL: $WEBSOCKET_URL"
fi

echo "S3 Bucket: $BUCKET_NAME"
echo ""

echo "Step 1: Building frontend..."
cd "$PROJECT_ROOT/frontend"

cat > .env.production <<EOF
VITE_API_BASE_URL=$API_URL
EOF

echo "Building with production configuration..."
npm run build

if [ $? -ne 0 ]; then
    echo "ERROR: Frontend build failed"
    exit 1
fi

echo "Build completed successfully"
echo ""

echo "Step 2: Setting up S3 bucket..."

if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: $BUCKET_NAME"
    aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
    
    echo "Enabling versioning..."
    aws s3api put-bucket-versioning \
      --bucket "$BUCKET_NAME" \
      --versioning-configuration Status=Enabled \
      --region "$AWS_REGION"
else
    echo "Bucket already exists: $BUCKET_NAME"
fi

echo "Configuring bucket for static website hosting..."
aws s3 website "s3://$BUCKET_NAME" \
  --index-document index.html \
  --error-document index.html \
  --region "$AWS_REGION"

echo ""
echo "Step 3: Uploading frontend files..."
aws s3 sync dist/ "s3://$BUCKET_NAME" \
  --delete \
  --region "$AWS_REGION" \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"

aws s3 cp dist/index.html "s3://$BUCKET_NAME/index.html" \
  --region "$AWS_REGION" \
  --cache-control "no-cache, no-store, must-revalidate"

echo "Upload completed"
echo ""

echo "Step 4: Configuring bucket policy..."

echo "Fetching S3 VPC endpoint ID from CloudFormation stack..."
S3_VPC_ENDPOINT_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`S3VpcEndpointId`].OutputValue' \
  --output text 2>&1)

if [ $? -ne 0 ] || [ -z "$S3_VPC_ENDPOINT_ID" ]; then
    echo "ERROR: Could not retrieve S3 VPC endpoint ID from stack '$STACK_NAME'"
    echo "Ensure the backend stack is deployed with VPC endpoints"
    exit 1
fi

echo "S3 VPC Endpoint ID: $S3_VPC_ENDPOINT_ID"

VPC_CIDR=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Parameters[?ParameterKey==`VpcCidrBlock`].ParameterValue' \
  --output text 2>&1)

echo "Applying VPC endpoint-based bucket policy..."

if [ -n "$VPC_CIDR" ] && [ "$VPC_CIDR" != "None" ]; then
    cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAllExceptVpcEndpoint",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringNotEquals": {
          "aws:SourceVpce": "${S3_VPC_ENDPOINT_ID}"
        }
      }
    },
    {
      "Sid": "DenyNonVpcCidr",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringNotLike": {
          "aws:SourceIp": "${VPC_CIDR}/*"
        }
      }
    },
    {
      "Sid": "AllowVpcEndpointAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringEquals": {
          "aws:SourceVpce": "${S3_VPC_ENDPOINT_ID}"
        }
      }
    }
  ]
}
EOF
else
    cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAllExceptVpcEndpoint",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringNotEquals": {
          "aws:SourceVpce": "${S3_VPC_ENDPOINT_ID}"
        }
      }
    },
    {
      "Sid": "AllowVpcEndpointAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringEquals": {
          "aws:SourceVpce": "${S3_VPC_ENDPOINT_ID}"
        }
      }
    }
  ]
}
EOF
fi

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
  --region "$AWS_REGION"

aws s3api put-bucket-policy \
  --bucket "$BUCKET_NAME" \
  --policy file:///tmp/bucket-policy.json \
  --region "$AWS_REGION"

rm /tmp/bucket-policy.json

echo "Bucket policy applied"
echo ""

WEBSITE_URL="http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"

echo "========================================="
echo "Frontend Deployment Complete"
echo "========================================="
echo ""
echo "Frontend URL: $WEBSITE_URL"
echo "API URL: $API_URL"
if [ -n "$WEBSOCKET_URL" ]; then
    echo "WebSocket URL: $WEBSOCKET_URL"
fi
echo ""
echo "Access restricted to VPC endpoint only"
echo "S3 VPC Endpoint: $S3_VPC_ENDPOINT_ID"
echo ""

