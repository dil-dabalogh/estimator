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
  --no-ip-filter     Deploy without IP filtering (public access)
  --help             Show this help message

Examples:
  $0                                                    # Deploy with IP filtering from stack
  $0 --api-url https://api.example.com                  # Use custom API URL
  $0 --no-ip-filter                                     # Deploy without IP restrictions

EOF
    exit 1
}

API_URL=""
USE_IP_FILTER=true

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
        --no-ip-filter)
            USE_IP_FILTER=false
            shift
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

if [ "$USE_IP_FILTER" = true ]; then
    echo "Fetching IP whitelist from CloudFormation stack..."
    ALLOWED_IPS=$(aws cloudformation describe-stacks \
      --stack-name "$STACK_NAME" \
      --region "$AWS_REGION" \
      --query 'Stacks[0].Parameters[?ParameterKey==`AllowedIPRanges`].ParameterValue' \
      --output text 2>&1)
    
    if [ $? -ne 0 ] || [ -z "$ALLOWED_IPS" ]; then
        echo "WARNING: Could not retrieve IP whitelist from stack"
        echo "Deploying with public access. Use manage-ip-whitelist.sh to configure IPs."
        ALLOWED_IPS=""
    fi
    
    if [ "$ALLOWED_IPS" = "127.0.0.1/32" ] || [ -z "$ALLOWED_IPS" ]; then
        echo "WARNING: IP whitelist is set to deny all (127.0.0.1/32)"
        echo "Frontend will not be accessible. Use manage-ip-whitelist.sh to add your IP."
        echo ""
        read -p "Continue anyway? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Deployment aborted."
            exit 0
        fi
    fi
    
    if [ -n "$ALLOWED_IPS" ] && [ "$ALLOWED_IPS" != "127.0.0.1/32" ]; then
        echo "Applying IP-filtered bucket policy..."
        echo "Allowed IPs: $ALLOWED_IPS"
        
        IFS=',' read -ra IP_ARRAY <<< "$ALLOWED_IPS"
        IP_JSON=$(printf ',"%s"' "${IP_ARRAY[@]}")
        IP_JSON="[${IP_JSON:1}]"
        
        cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "IPFilteredPublicRead",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
    "Condition": {
      "IpAddress": {
        "aws:SourceIp": ${IP_JSON}
      }
    }
  }]
}
EOF
    else
        echo "Applying public access bucket policy (no IP filtering)..."
        cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
  }]
}
EOF
    fi
else
    echo "Applying public access bucket policy (--no-ip-filter)..."
    cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
  }]
}
EOF
fi

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false \
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

if [ "$USE_IP_FILTER" = true ] && [ -n "$ALLOWED_IPS" ] && [ "$ALLOWED_IPS" != "127.0.0.1/32" ]; then
    echo "IP Filtering: ENABLED"
    echo "Allowed IPs: $ALLOWED_IPS"
    echo ""
    echo "Note: Only these IP addresses can access the frontend."
    echo "Use manage-ip-whitelist.sh to add more IPs."
elif [ "$USE_IP_FILTER" = true ]; then
    echo "IP Filtering: DENY ALL"
    echo "Use manage-ip-whitelist.sh to add your IP before accessing the frontend."
else
    echo "IP Filtering: DISABLED (Public Access)"
fi
echo ""
echo "To update IP whitelist (affects both API and frontend):"
echo "  cd infrastructure"
echo "  ./manage-ip-whitelist.sh add-current"
echo "  ./deploy-frontend.sh  # Re-run to update bucket policy"
echo ""

