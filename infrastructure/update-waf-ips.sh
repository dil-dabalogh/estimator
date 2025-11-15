#!/bin/bash

# Script to update allowed IP ranges in existing WAF
# Usage: ./update-waf-ips.sh "IP1/32,IP2/24,IP3/24"

set -e

ALLOWED_IPS=${1}

if [ -z "$ALLOWED_IPS" ]; then
  echo "Usage: $0 \"IP1/32,IP2/24,IP3/24\""
  echo ""
  echo "Example:"
  echo "  $0 \"62.216.248.197/32\""
  echo "  $0 \"62.216.248.0/24,198.51.100.0/24\""
  exit 1
fi

echo "Updating WAF IP ranges to: $ALLOWED_IPS"

AWS_REGION=$(aws configure get region)

# Convert comma-separated IPs to array
IFS=',' read -ra IP_ARRAY <<< "$ALLOWED_IPS"

# Get IP Set ID
IP_SET_ID=$(aws wafv2 list-ip-sets --scope REGIONAL --region $AWS_REGION \
  --query "IPSets[?Name=='EstimationToolAllowedIPs'].Id" \
  --output text)

if [ -z "$IP_SET_ID" ]; then
  echo "Error: IP Set 'EstimationToolAllowedIPs' not found"
  echo "Run ./infrastructure/setup-waf.sh first"
  exit 1
fi

echo "IP Set ID: $IP_SET_ID"

# Get lock token
LOCK_TOKEN=$(aws wafv2 get-ip-set \
  --scope REGIONAL \
  --id $IP_SET_ID \
  --name EstimationToolAllowedIPs \
  --region $AWS_REGION \
  --query 'LockToken' \
  --output text)

# Update IP Set
aws wafv2 update-ip-set \
  --scope REGIONAL \
  --id $IP_SET_ID \
  --name EstimationToolAllowedIPs \
  --addresses "${IP_ARRAY[@]}" \
  --lock-token $LOCK_TOKEN \
  --region $AWS_REGION

echo "✅ IP ranges updated successfully"
echo "New allowed IPs: $ALLOWED_IPS"

