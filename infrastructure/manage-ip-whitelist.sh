#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

STACK_NAME="estimation-tool-api"
AWS_REGION="us-west-2"

show_usage() {
    cat << EOF
IP Whitelist Management for Estimation Tool API

Usage:
  $0 add-current              Add your current IP to whitelist
  $0 add <IP|CIDR>           Add specific IP or CIDR range to whitelist
  $0 remove-all              Remove all IPs (deny all access)
  $0 list                    Show current whitelist

Examples:
  $0 add-current                    # Add your current IP automatically
  $0 add 192.168.1.5                # Add single IP (converted to 192.168.1.5/32)
  $0 add 192.168.1.5/32             # Add single IP in CIDR notation
  $0 add 10.0.0.0/24                # Add IP range
  $0 remove-all                     # Remove all IPs (deny all access)
  $0 list                           # Show current whitelist

CIDR Notation:
  - Single IP: Use /32 suffix (e.g., 192.168.1.5/32)
  - IP Range: Use appropriate CIDR (e.g., 10.0.0.0/24 for 256 addresses)
  - Script auto-converts bare IPs to /32 format

EOF
    exit 1
}

normalize_ip() {
    local ip="$1"
    
    if [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        echo "${ip}/32"
    elif [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        echo "$ip"
    else
        echo ""
    fi
}

validate_cidr() {
    local cidr="$1"
    
    if [[ ! "$cidr" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        return 1
    fi
    
    local ip="${cidr%/*}"
    local mask="${cidr#*/}"
    
    IFS='.' read -ra octets <<< "$ip"
    for octet in "${octets[@]}"; do
        if [ "$octet" -gt 255 ] || [ "$octet" -lt 0 ]; then
            return 1
        fi
    done
    
    if [ "$mask" -gt 32 ] || [ "$mask" -lt 0 ]; then
        return 1
    fi
    
    return 0
}

get_existing_ips() {
    aws cloudformation describe-stacks \
      --stack-name "$STACK_NAME" \
      --region "$AWS_REGION" \
      --query 'Stacks[0].Parameters[?ParameterKey==`AllowedIPRanges`].ParameterValue' \
      --output text 2>&1
    
    if [ $? -ne 0 ]; then
        echo ""
        return 1
    fi
    return 0
}

update_stack_ips() {
    local new_ip_list="$1"
    
    echo "Updating CloudFormation stack..."
    echo "New whitelist: $new_ip_list"
    echo ""
    
    aws cloudformation update-stack \
      --stack-name "$STACK_NAME" \
      --use-previous-template \
      --parameters \
        "ParameterKey=AllowedIPRanges,ParameterValue=\"$new_ip_list\"" \
        "ParameterKey=LLMProvider,UsePreviousValue=true" \
        "ParameterKey=OpenAIApiKey,UsePreviousValue=true" \
        "ParameterKey=OpenAIModel,UsePreviousValue=true" \
        "ParameterKey=BedrockRegion,UsePreviousValue=true" \
        "ParameterKey=BedrockModel,UsePreviousValue=true" \
        "ParameterKey=BedrockAgentId,UsePreviousValue=true" \
        "ParameterKey=BedrockAgentAliasId,UsePreviousValue=true" \
        "ParameterKey=AtlassianURL,UsePreviousValue=true" \
        "ParameterKey=AtlassianEmail,UsePreviousValue=true" \
        "ParameterKey=AtlassianToken,UsePreviousValue=true" \
      --capabilities CAPABILITY_IAM \
      --region "$AWS_REGION"
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Stack update failed"
        exit 1
    fi
    
    echo ""
    echo "Stack update initiated. Waiting for completion..."
    echo "This usually takes 1-2 minutes..."
    echo ""
    
    aws cloudformation wait stack-update-complete \
      --stack-name "$STACK_NAME" \
      --region "$AWS_REGION"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "========================================="
        echo "IP Whitelist Updated Successfully"
        echo "========================================="
        echo ""
        echo "Updated whitelist: $new_ip_list"
        echo ""
    else
        echo ""
        echo "ERROR: Stack update failed or timed out"
        echo "Check the CloudFormation console for details:"
        echo "https://console.aws.amazon.com/cloudformation/home?region=$AWS_REGION#/stacks"
        exit 1
    fi
}

cmd_add_current() {
    echo "========================================="
    echo "Add Current IP to Whitelist"
    echo "========================================="
    echo ""
    
    echo "Getting your current IP address..."
    CURRENT_IP=$(curl -s https://checkip.amazonaws.com)
    
    if [ -z "$CURRENT_IP" ]; then
        echo "ERROR: Could not determine your IP address"
        echo "Please check your internet connection"
        exit 1
    fi
    
    echo "Your current IP: $CURRENT_IP"
    echo ""
    
    CURRENT_IP_CIDR="${CURRENT_IP}/32"
    
    echo "Retrieving existing IP whitelist from CloudFormation..."
    EXISTING_IPS=$(get_existing_ips)
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Could not retrieve stack parameters"
        echo "Make sure the stack '$STACK_NAME' exists in region $AWS_REGION"
        exit 1
    fi
    
    echo "Current whitelist: $EXISTING_IPS"
    echo ""
    
    if [[ "$EXISTING_IPS" == *"${CURRENT_IP}"* ]]; then
        echo "Your IP ($CURRENT_IP) is already whitelisted"
        echo "No update needed."
        exit 0
    fi
    
    if [ "$EXISTING_IPS" = "127.0.0.1/32" ] || [ -z "$EXISTING_IPS" ]; then
        NEW_IP_LIST="$CURRENT_IP_CIDR"
    else
        NEW_IP_LIST="${EXISTING_IPS},${CURRENT_IP_CIDR}"
    fi
    
    update_stack_ips "$NEW_IP_LIST"
    
    echo "Your IP ($CURRENT_IP) is now whitelisted."
    echo "You should now be able to access the API."
}

cmd_add_custom() {
    local input_ip="$1"
    
    if [ -z "$input_ip" ]; then
        echo "ERROR: IP address or CIDR range required"
        echo "Usage: $0 add <IP|CIDR>"
        exit 1
    fi
    
    echo "========================================="
    echo "Add IP/CIDR to Whitelist"
    echo "========================================="
    echo ""
    
    IP_CIDR=$(normalize_ip "$input_ip")
    
    if [ -z "$IP_CIDR" ]; then
        echo "ERROR: Invalid IP address or CIDR format: $input_ip"
        echo "Examples: 192.168.1.5 or 10.0.0.0/24"
        exit 1
    fi
    
    if ! validate_cidr "$IP_CIDR"; then
        echo "ERROR: Invalid CIDR notation: $IP_CIDR"
        exit 1
    fi
    
    echo "Normalized IP/CIDR: $IP_CIDR"
    echo ""
    
    echo "Retrieving existing IP whitelist from CloudFormation..."
    EXISTING_IPS=$(get_existing_ips)
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Could not retrieve stack parameters"
        echo "Make sure the stack '$STACK_NAME' exists in region $AWS_REGION"
        exit 1
    fi
    
    echo "Current whitelist: $EXISTING_IPS"
    echo ""
    
    if [[ "$EXISTING_IPS" == *"${IP_CIDR}"* ]]; then
        echo "IP/CIDR ($IP_CIDR) is already whitelisted"
        echo "No update needed."
        exit 0
    fi
    
    if [ "$EXISTING_IPS" = "127.0.0.1/32" ] || [ -z "$EXISTING_IPS" ]; then
        NEW_IP_LIST="$IP_CIDR"
    else
        NEW_IP_LIST="${EXISTING_IPS},${IP_CIDR}"
    fi
    
    update_stack_ips "$NEW_IP_LIST"
    
    echo "IP/CIDR ($IP_CIDR) is now whitelisted."
}

cmd_remove_all() {
    echo "========================================="
    echo "Remove All IPs from Whitelist"
    echo "========================================="
    echo ""
    echo "WARNING: This will deny all external access to the API."
    echo "Only localhost (127.0.0.1) will be able to access."
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    
    NEW_IP_LIST="127.0.0.1/32"
    
    update_stack_ips "$NEW_IP_LIST"
    
    echo "All IPs removed. Access is now denied to all external IPs."
    echo "Use '$0 add-current' to restore access from your current IP."
}

cmd_list() {
    echo "========================================="
    echo "Current IP Whitelist"
    echo "========================================="
    echo ""
    
    EXISTING_IPS=$(get_existing_ips)
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Could not retrieve stack parameters"
        echo "Make sure the stack '$STACK_NAME' exists in region $AWS_REGION"
        exit 1
    fi
    
    if [ "$EXISTING_IPS" = "127.0.0.1/32" ]; then
        echo "Whitelist: $EXISTING_IPS (DENY ALL - localhost only)"
    elif [ -z "$EXISTING_IPS" ]; then
        echo "Whitelist: (empty - no access)"
    else
        echo "Whitelist: $EXISTING_IPS"
        echo ""
        echo "Individual IPs/Ranges:"
        IFS=',' read -ra IP_ARRAY <<< "$EXISTING_IPS"
        for ip in "${IP_ARRAY[@]}"; do
            echo "  - $ip"
        done
    fi
    echo ""
}

if [ $# -eq 0 ]; then
    show_usage
fi

case "$1" in
    add-current)
        cmd_add_current
        ;;
    add)
        cmd_add_custom "$2"
        ;;
    remove-all)
        cmd_remove_all
        ;;
    list)
        cmd_list
        ;;
    *)
        show_usage
        ;;
esac

