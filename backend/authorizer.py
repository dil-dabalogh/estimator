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
    """
    ip_ranges_str = os.getenv("ALLOWED_IP_RANGES", "0.0.0.0/0")
    
    if ip_ranges_str == "0.0.0.0/0":
        # Allow all - no restrictions
        return [ipaddress.IPv4Network("0.0.0.0/0")]
    
    ranges = []
    for cidr in ip_ranges_str.split(","):
        cidr = cidr.strip()
        try:
            ranges.append(ipaddress.IPv4Network(cidr))
        except ValueError as e:
            print(f"Warning: Invalid CIDR block '{cidr}': {e}")
    
    return ranges


def is_ip_allowed(source_ip: str, allowed_ranges: list[ipaddress.IPv4Network]) -> bool:
    """Check if source IP is in any of the allowed ranges."""
    try:
        ip_addr = ipaddress.IPv4Address(source_ip)
        for network in allowed_ranges:
            if ip_addr in network:
                return True
        return False
    except ValueError:
        # Invalid IP address
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda authorizer handler for HTTP API Gateway.
    
    Expected event structure for HTTP API:
    {
        "version": "2.0",
        "type": "REQUEST",
        "routeArn": "arn:aws:execute-api:...",
        "identitySource": [".."],
        "requestContext": {
            "http": {
                "sourceIp": "192.168.1.1",
                ...
            },
            ...
        },
        ...
    }
    """
    # Get source IP from request context
    source_ip = event.get("requestContext", {}).get("http", {}).get("sourceIp", "")
    
    if not source_ip:
        print("ERROR: No source IP found in request")
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
    
    print(f"Source IP: {source_ip}, Allowed: {is_allowed}")
    
    return {
        "isAuthorized": is_allowed,
        "context": {
            "sourceIp": source_ip,
            "allowed": str(is_allowed)
        }
    }

