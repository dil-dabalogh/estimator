"""
Lambda authorizer for IP-based access control on HTTP API Gateway.
This authorizer checks if the request's source IP is in the allowed list.
"""

import os
import ipaddress
from typing import Dict, Any


def get_allowed_ip_ranges() -> list[ipaddress.IPv4Network]:
    """
    Get allowed IP ranges from environment variable.
    Format: Comma-separated CIDR blocks (e.g., "192.168.1.0/24,10.0.0.0/8")
    Special cases:
    - "0.0.0.0/0": Allow all (no restrictions)
    - "127.0.0.1/32" or empty: Deny all external access (localhost only)
    """
    ip_ranges_str = os.getenv("ALLOWED_IP_RANGES", "127.0.0.1/32")
    
    if not ip_ranges_str or ip_ranges_str.strip() == "":
        print("INFO: Empty IP whitelist - denying all access")
        return []
    
    ip_ranges_str = ip_ranges_str.strip()
    
    if ip_ranges_str == "0.0.0.0/0":
        print("WARNING: IP whitelist allows all IPs (0.0.0.0/0) - no restrictions")
        return [ipaddress.IPv4Network("0.0.0.0/0")]
    
    ranges = []
    for cidr in ip_ranges_str.split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            ranges.append(ipaddress.IPv4Network(cidr))
        except ValueError as e:
            print(f"WARNING: Invalid CIDR block '{cidr}': {e}")
    
    if not ranges:
        print("WARNING: No valid IP ranges configured - denying all access")
    
    return ranges


def is_ip_allowed(source_ip: str, allowed_ranges: list[ipaddress.IPv4Network]) -> bool:
    """Check if source IP is in any of the allowed ranges."""
    if not allowed_ranges:
        return False
    
    try:
        ip_addr = ipaddress.IPv4Address(source_ip)
        for network in allowed_ranges:
            if ip_addr in network:
                return True
        return False
    except ValueError:
        print(f"ERROR: Invalid IP address format: {source_ip}")
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda authorizer handler for HTTP API Gateway and WebSocket API.
    
    Expected event structure for HTTP API (version 2.0):
    {
        "version": "2.0",
        "type": "REQUEST",
        "requestContext": {
            "http": {
                "sourceIp": "192.168.1.1",
                ...
            },
            ...
        },
        ...
    }
    
    Expected event structure for WebSocket API (version 1.0):
    {
        "type": "REQUEST",
        "methodArn": "arn:aws:execute-api:...",
        "requestContext": {
            "identity": {
                "sourceIp": "192.168.1.1",
                ...
            },
            ...
        },
        ...
    }
    """
    # Determine source IP based on protocol (HTTP API vs WebSocket)
    request_context = event.get("requestContext", {})
    
    # Try HTTP API format first (version 2.0)
    source_ip = request_context.get("http", {}).get("sourceIp", "")
    
    # Fall back to WebSocket format (version 1.0)
    if not source_ip:
        source_ip = request_context.get("identity", {}).get("sourceIp", "")
    
    # Final fallback: check connectionId for WebSocket
    if not source_ip and "connectionId" in request_context:
        source_ip = request_context.get("identity", {}).get("sourceIp", "")
    
    if not source_ip:
        print(f"ERROR: No source IP found in request. Event: {event}")
        return {
            "isAuthorized": False,
            "context": {
                "reason": "No source IP"
            }
        }
    
    # Get allowed IP ranges
    allowed_ranges = get_allowed_ip_ranges()
    
    # Check if IP is allowed
    is_allowed = is_ip_allowed(source_ip, allowed_ranges)
    
    protocol = "WebSocket" if "connectionId" in request_context else "HTTP"
    print(f"Protocol: {protocol}, Source IP: {source_ip}, Allowed: {is_allowed}")
    
    return {
        "isAuthorized": is_allowed,
        "context": {
            "sourceIp": source_ip,
            "allowed": str(is_allowed),
            "protocol": protocol
        }
    }

