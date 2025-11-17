#!/bin/bash

set -e

echo "========================================="
echo "Update IP Whitelist for Estimation API"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

STACK_NAME="estimation-tool-api"
AWS_REGION="us-west-2"

# Get current IP
echo "Getting your current IP address..."
CURRENT_IP=$(curl -s https://checkip.amazonaws.com)

if [ -z "$CURRENT_IP" ]; then
    echo "❌ ERROR: Could not determine your IP address"
    echo "Please check your internet connection"
    exit 1
fi

echo "✅ Your current IP: $CURRENT_IP"
echo ""

# Get existing IPs from stack
echo "Retrieving existing IP whitelist from CloudFormation..."
EXISTING_IPS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Parameters[?ParameterKey==`AllowedIPRanges`].ParameterValue' \
  --output text 2>&1)

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Could not retrieve stack parameters"
    echo "Make sure the stack '$STACK_NAME' exists in region $AWS_REGION"
    exit 1
fi

echo "Current whitelist: $EXISTING_IPS"
echo ""

# Check if IP is already in the list
if [[ $EXISTING_IPS == *"${CURRENT_IP}"* ]]; then
    echo "✅ Your IP ($CURRENT_IP) is already whitelisted!"
    echo "No update needed."
    exit 0
fi

# Add new IP to the list
if [ "$EXISTING_IPS" = "0.0.0.0/0" ]; then
    echo "⚠️  WARNING: Current setting allows all IPs (0.0.0.0/0)"
    echo "This will replace it with specific IPs only."
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    NEW_IP_LIST="${CURRENT_IP}/32"
else
    NEW_IP_LIST="${EXISTING_IPS},${CURRENT_IP}/32"
fi

echo "New whitelist: $NEW_IP_LIST"
echo ""

# Update the stack
echo "Updating CloudFormation stack..."
echo "This will update only the AllowedIPRanges parameter."
echo ""

aws cloudformation update-stack \
  --stack-name $STACK_NAME \
  --use-previous-template \
  --parameters \
    ParameterKey=AllowedIPRanges,ParameterValue="$NEW_IP_LIST" \
    ParameterKey=LLMProvider,UsePreviousValue=true \
    ParameterKey=OpenAIApiKey,UsePreviousValue=true \
    ParameterKey=OpenAIModel,UsePreviousValue=true \
    ParameterKey=BedrockRegion,UsePreviousValue=true \
    ParameterKey=BedrockModel,UsePreviousValue=true \
    ParameterKey=BedrockAgentId,UsePreviousValue=true \
    ParameterKey=BedrockAgentAliasId,UsePreviousValue=true \
    ParameterKey=AtlassianURL,UsePreviousValue=true \
    ParameterKey=AtlassianEmail,UsePreviousValue=true \
    ParameterKey=AtlassianToken,UsePreviousValue=true \
  --capabilities CAPABILITY_IAM \
  --region $AWS_REGION

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Stack update failed"
    exit 1
fi

echo ""
echo "Stack update initiated. Waiting for completion..."
echo "This usually takes 1-2 minutes..."
echo ""

aws cloudformation wait stack-update-complete \
  --stack-name $STACK_NAME \
  --region $AWS_REGION

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ IP Whitelist Updated Successfully!"
    echo "========================================="
    echo ""
    echo "Updated whitelist: $NEW_IP_LIST"
    echo ""
    echo "Your IP ($CURRENT_IP) is now whitelisted."
    echo "You should now be able to access the API."
else
    echo ""
    echo "❌ Stack update failed or timed out"
    echo "Check the CloudFormation console for details:"
    echo "https://console.aws.amazon.com/cloudformation/home?region=$AWS_REGION#/stacks"
    exit 1
fi

