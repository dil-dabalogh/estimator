#!/bin/bash

# Script to clean up orphaned WAF resources
# Use this to remove WAF resources created by previous failed attempts

set -e

AWS_REGION=${AWS_REGION:-"us-west-2"}

echo "Cleaning up WAF resources..."
echo "Region: $AWS_REGION"
echo ""

# Get WAF ID
WAF_ID=$(aws wafv2 list-web-acls --scope REGIONAL --region $AWS_REGION \
  --query "WebACLs[?Name=='EstimationToolWAF'].Id" --output text)

# Get IP Set ID
IP_SET_ID=$(aws wafv2 list-ip-sets --scope REGIONAL --region $AWS_REGION \
  --query "IPSets[?Name=='EstimationToolAllowedIPs'].Id" --output text)

if [ -n "$WAF_ID" ]; then
  echo "Deleting Web ACL: $WAF_ID"
  
  # Get lock token
  WAF_LOCK=$(aws wafv2 get-web-acl \
    --scope REGIONAL \
    --id $WAF_ID \
    --name EstimationToolWAF \
    --region $AWS_REGION \
    --query 'LockToken' \
    --output text)
  
  aws wafv2 delete-web-acl \
    --scope REGIONAL \
    --id $WAF_ID \
    --name EstimationToolWAF \
    --lock-token $WAF_LOCK \
    --region $AWS_REGION
  
  echo "✓ Web ACL deleted"
else
  echo "No Web ACL found"
fi

if [ -n "$IP_SET_ID" ]; then
  echo "Deleting IP Set: $IP_SET_ID"
  
  # Get lock token
  IP_LOCK=$(aws wafv2 get-ip-set \
    --scope REGIONAL \
    --id $IP_SET_ID \
    --name EstimationToolAllowedIPs \
    --region $AWS_REGION \
    --query 'LockToken' \
    --output text)
  
  aws wafv2 delete-ip-set \
    --scope REGIONAL \
    --id $IP_SET_ID \
    --name EstimationToolAllowedIPs \
    --lock-token $IP_LOCK \
    --region $AWS_REGION
  
  echo "✓ IP Set deleted"
else
  echo "No IP Set found"
fi

echo ""
echo "✅ Cleanup complete"

