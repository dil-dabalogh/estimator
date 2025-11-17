#!/bin/bash

set -e

echo "========================================="
echo "Building and Deploying Estimation Tool API"
echo "========================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Determine deployment mode
DEPLOYMENT_MODE="${1:-config}"  # Default to config-based deployment

if [ "$DEPLOYMENT_MODE" = "guided" ]; then
  echo "Running GUIDED deployment (interactive)..."
  echo ""
  
  echo "Step 1: Building Lambda package..."
  sam build \
    --template infrastructure/template.yaml \
    --use-container
  
  echo ""
  echo "Step 2: Deploying with guided prompts..."
  sam deploy \
    --guided \
    --template infrastructure/template.yaml \
    --stack-name estimation-tool-api \
    --capabilities CAPABILITY_IAM

elif [ "$DEPLOYMENT_MODE" = "config" ]; then
  echo "Running CONFIG-BASED deployment (using samconfig.toml)..."
  echo ""
  
  echo "Step 1: Cleaning previous build artifacts..."
  rm -rf .aws-sam/build .aws-sam/cache
  
  echo "Step 2: Building Lambda package with dependencies..."
  sam build \
    --template infrastructure/template.yaml \
    --use-container
  
  echo ""
  echo "Step 3: Verifying build artifacts..."
  echo "Build directory contents:"
  ls -la .aws-sam/build/ || echo "Build directory not found"
  echo ""
  echo "Checking for mangum in EstimationFunction:"
  if ls .aws-sam/build/EstimationFunction/ | grep -q mangum; then
    echo "✓ mangum found in build"
  else
    echo "✗ mangum NOT FOUND - deployment will fail!"
    exit 1
  fi
  
  echo ""
  echo "Step 4: Deploying using samconfig.toml [dev] profile..."
  sam deploy \
    --config-env dev \
    --template-file .aws-sam/build/template.yaml \
    --stack-name estimation-tool-api \
    --capabilities CAPABILITY_IAM \
    --force-upload \
    --no-confirm-changeset
  
else
  echo "ERROR: Invalid deployment mode: $DEPLOYMENT_MODE"
  echo "Usage: $0 [guided|config]"
  echo "  guided - Interactive guided deployment"
  echo "  config - Use samconfig.toml configuration (default)"
  exit 1
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""

# Get and display API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name estimation-tool-api \
  --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -n "$API_URL" ]; then
  echo "API URL: $API_URL"
  echo ""
  echo "Test health endpoint:"
  echo "  curl $API_URL/health"
  echo ""
  echo "Update frontend configuration:"
  echo "  VITE_API_BASE_URL=$API_URL"
fi

echo ""
echo "Note: If you see import errors, ensure all dependencies are in backend/requirements.txt"

