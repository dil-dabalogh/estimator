#!/bin/bash

set -e

echo "Building and deploying Estimation Tool API..."

cd "$(dirname "$0")/.."

sam build --template infrastructure/template.yaml

sam deploy \
  --guided \
  --template infrastructure/template.yaml \
  --stack-name estimation-tool-api \
  --capabilities CAPABILITY_IAM

echo "Deployment complete!"
echo "Note: Update frontend/.env with the API URL from outputs"

