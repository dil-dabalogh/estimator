"""IP whitelist management commands."""

import typer
import re
import requests
from typing import Optional
from chore.cli import ip_app
from chore.core.console import console, success, error, warning, info, header, section
from chore.core.config import get_config
from chore.core.aws import get_aws_client


def normalize_ip(ip: str) -> Optional[str]:
    """
    Normalize IP address to CIDR notation.
    
    Args:
        ip: IP address or CIDR range
    
    Returns:
        Normalized CIDR string or None if invalid
    """
    bare_ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    cidr_pattern = r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"
    
    if re.match(bare_ip_pattern, ip):
        return f"{ip}/32"
    elif re.match(cidr_pattern, ip):
        return ip
    else:
        return None


def validate_cidr(cidr: str) -> bool:
    """
    Validate CIDR notation.
    
    Args:
        cidr: CIDR string to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not re.match(r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$", cidr):
        return False
    
    ip_part, mask = cidr.split("/")
    octets = ip_part.split(".")
    
    for octet in octets:
        if int(octet) > 255 or int(octet) < 0:
            return False
    
    mask_num = int(mask)
    if mask_num > 32 or mask_num < 0:
        return False
    
    return True


def get_current_ip() -> Optional[str]:
    """Get current public IP address."""
    try:
        response = requests.get("https://checkip.amazonaws.com", timeout=5)
        return response.text.strip()
    except Exception:
        return None


@ip_app.command("list")
def list_ips():
    """
    Show current IP whitelist.
    
    DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.
    This command is kept for backward compatibility but will be removed in a future version.
    """
    warning("DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.")
    warning("This command is deprecated and will be removed in a future version.")
    console.print()
    header("Current IP Whitelist (Deprecated)")
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    existing_ips = aws_client.get_stack_parameter(config.stack_name, "AllowedIPRanges")
    
    if not existing_ips:
        error(f"Could not retrieve IP whitelist from stack '{config.stack_name}'")
        error(f"Make sure the stack exists in region {config.region}")
        raise typer.Exit(1)
    
    if existing_ips == "127.0.0.1/32":
        warning(f"Whitelist: {existing_ips} (DENY ALL - localhost only)")
    else:
        console.print(f"[bold]Whitelist:[/bold] {existing_ips}")
        console.print()
        console.print("[bold]Individual IPs/Ranges:[/bold]")
        for ip in existing_ips.split(","):
            console.print(f"  - {ip}")
    
    console.print()


@ip_app.command("add-current")
def add_current_ip():
    """
    Add your current IP address to the whitelist.
    
    DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.
    This command is kept for backward compatibility but will be removed in a future version.
    """
    warning("DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.")
    warning("This command is deprecated and will be removed in a future version.")
    warning("Access is now controlled via VPC endpoints configured in the CloudFormation stack.")
    console.print()
    header("Add Current IP to Whitelist (Deprecated)")
    
    info("Getting your current IP address...")
    current_ip = get_current_ip()
    
    if not current_ip:
        error("Could not determine your IP address")
        error("Please check your internet connection")
        raise typer.Exit(1)
    
    success(f"Your current IP: {current_ip}")
    console.print()
    
    current_ip_cidr = f"{current_ip}/32"
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    info("Retrieving existing IP whitelist from CloudFormation...")
    existing_ips = aws_client.get_stack_parameter(config.stack_name, "AllowedIPRanges")
    
    if not existing_ips:
        error(f"Could not retrieve stack parameters from '{config.stack_name}'")
        raise typer.Exit(1)
    
    info(f"Current whitelist: {existing_ips}")
    console.print()
    
    if current_ip in existing_ips:
        success(f"Your IP ({current_ip}) is already whitelisted")
        info("No update needed.")
        return
    
    if existing_ips == "127.0.0.1/32" or not existing_ips:
        new_ip_list = current_ip_cidr
    else:
        new_ip_list = f"{existing_ips},{current_ip_cidr}"
    
    if aws_client.update_stack_parameters(
        config.stack_name,
        {"AllowedIPRanges": new_ip_list},
        wait=True,
    ):
        console.print()
        success(f"Your IP ({current_ip}) is now whitelisted.")
        info("You should now be able to access the API.")
    else:
        error("Failed to update IP whitelist")
        raise typer.Exit(1)


@ip_app.command("add")
def add_ip(
    ip_or_cidr: str = typer.Argument(..., help="IP address or CIDR range to add"),
):
    """
    Add a specific IP address or CIDR range to the whitelist.
    
    DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.
    This command is kept for backward compatibility but will be removed in a future version.
    """
    warning("DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.")
    warning("This command is deprecated and will be removed in a future version.")
    warning("Access is now controlled via VPC endpoints configured in the CloudFormation stack.")
    console.print()
    header("Add IP/CIDR to Whitelist (Deprecated)")
    
    ip_cidr = normalize_ip(ip_or_cidr)
    
    if not ip_cidr:
        error(f"Invalid IP address or CIDR format: {ip_or_cidr}")
        error("Examples: 192.168.1.5 or 10.0.0.0/24")
        raise typer.Exit(1)
    
    if not validate_cidr(ip_cidr):
        error(f"Invalid CIDR notation: {ip_cidr}")
        raise typer.Exit(1)
    
    info(f"Normalized IP/CIDR: {ip_cidr}")
    console.print()
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    info("Retrieving existing IP whitelist from CloudFormation...")
    existing_ips = aws_client.get_stack_parameter(config.stack_name, "AllowedIPRanges")
    
    if not existing_ips:
        error(f"Could not retrieve stack parameters from '{config.stack_name}'")
        raise typer.Exit(1)
    
    info(f"Current whitelist: {existing_ips}")
    console.print()
    
    if ip_cidr in existing_ips:
        success(f"IP/CIDR ({ip_cidr}) is already whitelisted")
        info("No update needed.")
        return
    
    if existing_ips == "127.0.0.1/32" or not existing_ips:
        new_ip_list = ip_cidr
    else:
        new_ip_list = f"{existing_ips},{ip_cidr}"
    
    if aws_client.update_stack_parameters(
        config.stack_name,
        {"AllowedIPRanges": new_ip_list},
        wait=True,
    ):
        console.print()
        success(f"IP/CIDR ({ip_cidr}) is now whitelisted.")
    else:
        error("Failed to update IP whitelist")
        raise typer.Exit(1)


@ip_app.command("remove")
def remove_ip(
    ip_or_cidr: str = typer.Argument(..., help="IP address or CIDR range to remove"),
):
    """
    Remove a specific IP address or CIDR range from the whitelist.
    
    DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.
    This command is kept for backward compatibility but will be removed in a future version.
    """
    warning("DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.")
    warning("This command is deprecated and will be removed in a future version.")
    warning("Access is now controlled via VPC endpoints configured in the CloudFormation stack.")
    console.print()
    header("Remove IP/CIDR from Whitelist (Deprecated)")
    
    ip_cidr = normalize_ip(ip_or_cidr)
    
    if not ip_cidr:
        error(f"Invalid IP address or CIDR format: {ip_or_cidr}")
        error("Examples: 192.168.1.5 or 10.0.0.0/24")
        raise typer.Exit(1)
    
    if not validate_cidr(ip_cidr):
        error(f"Invalid CIDR notation: {ip_cidr}")
        raise typer.Exit(1)
    
    info(f"Normalized IP/CIDR: {ip_cidr}")
    console.print()
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    info("Retrieving existing IP whitelist from CloudFormation...")
    existing_ips = aws_client.get_stack_parameter(config.stack_name, "AllowedIPRanges")
    
    if not existing_ips:
        error(f"Could not retrieve stack parameters from '{config.stack_name}'")
        raise typer.Exit(1)
    
    info(f"Current whitelist: {existing_ips}")
    console.print()
    
    if ip_cidr not in existing_ips:
        warning(f"IP/CIDR ({ip_cidr}) is not in the whitelist")
        info("No update needed.")
        return
    
    ip_list = [ip.strip() for ip in existing_ips.split(",")]
    ip_list = [ip for ip in ip_list if ip != ip_cidr]
    
    if not ip_list:
        new_ip_list = "127.0.0.1/32"
        warning("Whitelist would be empty after removal")
        warning("Setting to deny-all (127.0.0.1/32)")
    else:
        new_ip_list = ",".join(ip_list)
    
    if not typer.confirm(f"Remove {ip_cidr} from whitelist?"):
        info("Aborted.")
        return
    
    if aws_client.update_stack_parameters(
        config.stack_name,
        {"AllowedIPRanges": new_ip_list},
        wait=True,
    ):
        console.print()
        success(f"IP/CIDR ({ip_cidr}) removed from whitelist.")
        if new_ip_list == "127.0.0.1/32":
            warning("All external access is now denied.")
            info("Use 'chore ip add-current' to restore access.")
    else:
        error("Failed to update IP whitelist")
        raise typer.Exit(1)


@ip_app.command("remove-all")
def remove_all_ips():
    """
    Remove all IPs from the whitelist (deny all access).
    
    DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.
    This command is kept for backward compatibility but will be removed in a future version.
    """
    warning("DEPRECATED: IP whitelisting has been replaced with VPC endpoint-based access control.")
    warning("This command is deprecated and will be removed in a future version.")
    warning("Access is now controlled via VPC endpoints configured in the CloudFormation stack.")
    console.print()
    header("Remove All IPs from Whitelist (Deprecated)")
    
    warning("This will deny all external access to the API.")
    warning("Only localhost (127.0.0.1) will be able to access.")
    console.print()
    
    if not typer.confirm("Are you sure you want to continue?"):
        info("Aborted.")
        return
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    
    new_ip_list = "127.0.0.1/32"
    
    if aws_client.update_stack_parameters(
        config.stack_name,
        {"AllowedIPRanges": new_ip_list},
        wait=True,
    ):
        console.print()
        success("All IPs removed. Access is now denied to all external IPs.")
        info("Use 'chore ip add-current' to restore access from your current IP.")
    else:
        error("Failed to update IP whitelist")
        raise typer.Exit(1)

