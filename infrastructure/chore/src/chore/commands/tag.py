"""Tag management commands for AWS resources."""

import typer
import questionary
from typing import Optional, List, Dict, Any
from chore.cli import tag_app
from chore.core.console import console, success, error, warning, info, header, section
from chore.core.config import get_config
from chore.core.aws import get_aws_client


def parse_tag(tag_str: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse tag string in key=value format.
    
    Args:
        tag_str: Tag string in format "key=value"
    
    Returns:
        Tuple of (key, value) or (None, None) if invalid
    """
    if "=" not in tag_str:
        return None, None
    
    parts = tag_str.split("=", 1)
    if len(parts) != 2:
        return None, None
    
    key = parts[0].strip()
    value = parts[1].strip()
    
    if not key or not value:
        return None, None
    
    return key, value


def validate_tag(key: str, value: str) -> bool:
    """
    Validate tag key and value.
    
    AWS tag constraints:
    - Keys can be up to 128 characters
    - Values can be up to 256 characters
    - Allowed characters: letters, numbers, spaces, and +=._:/@-
    
    Args:
        key: Tag key
        value: Tag value
    
    Returns:
        True if valid, False otherwise
    """
    if not key or len(key) > 128:
        return False
    
    if not value or len(value) > 256:
        return False
    
    return True


def select_resources_interactive(
    resources: List[Dict[str, Any]],
    aws_client,
    config,
) -> List[str]:
    """
    Interactive selection of resources using questionary.
    
    Args:
        resources: List of resource dictionaries
        aws_client: AWS client instance
        config: Configuration object
    
    Returns:
        List of selected resource ARNs
    """
    # Filter to taggable resources only
    taggable_resources = [
        r for r in resources
        if aws_client.is_taggable_resource(r["ResourceType"])
    ]
    
    if not taggable_resources:
        warning("No taggable resources found in stack")
        return []
    
    # Build choices for questionary
    choices = []
    resource_map = {}
    
    for resource in taggable_resources:
        logical_id = resource["LogicalResourceId"]
        resource_type = resource["ResourceType"]
        physical_id = resource.get("PhysicalResourceId", "N/A")
        
        # Truncate long physical IDs
        display_physical_id = physical_id
        if len(display_physical_id) > 50:
            display_physical_id = display_physical_id[:47] + "..."
        
        # Create display name
        display_name = f"{logical_id} ({resource_type})"
        
        choices.append({
            "name": display_name,
            "value": logical_id,
        })
        
        resource_map[logical_id] = resource
    
    console.print()
    selected_ids = questionary.checkbox(
        "Select resources to tag:",
        choices=choices,
    ).ask()
    
    if selected_ids is None:
        # User cancelled (Ctrl+C)
        return []
    
    if not selected_ids:
        return []
    
    # Convert logical IDs to ARNs
    arns = []
    for logical_id in selected_ids:
        resource = resource_map[logical_id]
        physical_id = resource.get("PhysicalResourceId", "")
        resource_type = resource.get("ResourceType", "")
        
        # Construct ARN if needed
        if not physical_id:
            continue
        
        if not physical_id.startswith("arn:"):
            if resource_type.startswith("AWS::Lambda::"):
                arn = f"arn:aws:lambda:{config.region}:{aws_client.get_account_id()}:function:{physical_id}"
            elif resource_type.startswith("AWS::DynamoDB::"):
                arn = f"arn:aws:dynamodb:{config.region}:{aws_client.get_account_id()}:table/{physical_id}"
            elif resource_type.startswith("AWS::ApiGatewayV2::"):
                arn = f"arn:aws:apigateway:{config.region}::/apis/{physical_id}"
            else:
                arn = physical_id
        else:
            arn = physical_id
        
        arns.append(arn)
    
    return arns


@tag_app.command("list")
def list_tags(
    resource: Optional[str] = typer.Option(
        None,
        "--resource",
        "-r",
        help="Specific resource ARN or logical ID to show tags for",
    ),
    env: str = typer.Option(
        "default",
        "--env",
        "-e",
        help="Environment from samconfig.toml (e.g., 'dev', 'default')",
    ),
):
    """
    List tags on stack resources.
    
    If --resource is not specified, shows all resources in the stack.
    """
    header("Resource Tags")
    
    config = get_config(env)
    aws_client = get_aws_client(config.region)
    
    info(f"Stack: {config.stack_name}")
    info(f"Region: {config.region}")
    console.print()
    
    if resource:
        section(f"Tags for resource: {resource}")
        
        # If resource is a logical ID, we need to get the ARN
        if not resource.startswith("arn:"):
            resources = aws_client.get_stack_resources(config.stack_name)
            found = False
            for res in resources:
                if res["LogicalResourceId"] == resource:
                    resource = res.get("PhysicalResourceId", "")
                    found = True
                    break
            
            if not found:
                error(f"Resource '{resource}' not found in stack")
                raise typer.Exit(1)
        
        tags = aws_client.get_resource_tags(resource)
        
        if tags:
            for key, value in tags.items():
                console.print(f"  {key} = {value}")
        else:
            info("No tags found on this resource")
    
    else:
        section("All stack resources")
        
        resources = aws_client.get_stack_resources(config.stack_name)
        arns = aws_client.get_resource_arns(config.stack_name)
        
        if not resources:
            warning("No resources found in stack")
            return
        
        info(f"Found {len(resources)} resources in stack")
        info(f"Found {len(arns)} taggable resources")
        console.print()
        
        for resource_info in resources:
            logical_id = resource_info["LogicalResourceId"]
            resource_type = resource_info["ResourceType"]
            physical_id = resource_info.get("PhysicalResourceId", "N/A")
            
            console.print(f"[bold]{logical_id}[/bold]")
            console.print(f"  Type: {resource_type}")
            console.print(f"  Physical ID: {physical_id}")
            console.print()


@tag_app.command("add")
def add_tag(
    tag: str = typer.Argument(..., help="Tag in format 'key=value' (e.g., 'do-not-nuke=true')"),
    resource: Optional[str] = typer.Option(
        None,
        "--resource",
        "-r",
        help="Specific resource ARN or logical ID to tag (if not specified, tags all resources)",
    ),
    env: str = typer.Option(
        "default",
        "--env",
        "-e",
        help="Environment from samconfig.toml (e.g., 'dev', 'default')",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode: select resources to tag",
    ),
):
    """
    Add a tag to stack resources.
    
    Examples:
    
      chore tag add do-not-nuke=true                  # Tag all resources
      
      chore tag add Environment=production -r MyLambda  # Tag specific resource
      
      chore tag add do-not-nuke=true --interactive    # Interactive selection
    """
    header("Add Resource Tag")
    
    # Parse tag
    key, value = parse_tag(tag)
    
    if not key or not value:
        error(f"Invalid tag format: {tag}")
        error("Expected format: key=value (e.g., 'do-not-nuke=true')")
        raise typer.Exit(1)
    
    if not validate_tag(key, value):
        error(f"Invalid tag: {key}={value}")
        error("Key must be <= 128 chars, value must be <= 256 chars")
        raise typer.Exit(1)
    
    info(f"Tag to add: {key} = {value}")
    console.print()
    
    config = get_config(env)
    aws_client = get_aws_client(config.region)
    
    info(f"Stack: {config.stack_name}")
    info(f"Region: {config.region}")
    console.print()
    
    if interactive and resource:
        error("Cannot use --interactive with --resource")
        error("Use --interactive for selecting multiple resources, or --resource for a specific resource")
        raise typer.Exit(1)
    
    if interactive:
        section("Interactive resource selection")
        
        resources = aws_client.get_stack_resources(config.stack_name)
        
        if not resources:
            warning("No resources found in stack")
            return
        
        arns = select_resources_interactive(resources, aws_client, config)
        
        if not arns:
            info("No resources selected. Aborted.")
            return
        
        info(f"Selected {len(arns)} resource(s)")
        console.print()
        
        if not yes:
            if not typer.confirm(f"Apply tag '{key}={value}' to {len(arns)} selected resource(s)?"):
                info("Aborted.")
                return
    
    elif resource:
        section(f"Tagging specific resource: {resource}")
        
        # If resource is a logical ID, convert to ARN
        if not resource.startswith("arn:"):
            resources = aws_client.get_stack_resources(config.stack_name)
            found = False
            for res in resources:
                if res["LogicalResourceId"] == resource:
                    physical_id = res.get("PhysicalResourceId", "")
                    resource_type = res.get("ResourceType", "")
                    info(f"Found resource: {physical_id} ({resource_type})")
                    
                    # Construct ARN if needed
                    if not physical_id.startswith("arn:"):
                        if resource_type.startswith("AWS::Lambda::"):
                            resource = f"arn:aws:lambda:{config.region}:{aws_client.get_account_id()}:function:{physical_id}"
                        elif resource_type.startswith("AWS::DynamoDB::"):
                            resource = f"arn:aws:dynamodb:{config.region}:{aws_client.get_account_id()}:table/{physical_id}"
                        else:
                            resource = physical_id
                    else:
                        resource = physical_id
                    
                    found = True
                    break
            
            if not found:
                error(f"Resource '{resource}' not found in stack")
                raise typer.Exit(1)
        
        arns = [resource]
    
    else:
        section("Tagging all stack resources")
        
        arns = aws_client.get_resource_arns(config.stack_name)
        
        if not arns:
            warning("No taggable resources found in stack")
            return
        
        info(f"Found {len(arns)} taggable resources")
        console.print()
        
        if not yes:
            if not typer.confirm(f"Apply tag '{key}={value}' to all {len(arns)} resources?"):
                info("Aborted.")
                return
    
    console.print()
    info("Applying tags...")
    
    result = aws_client.tag_resources(arns, {key: value})
    
    console.print()
    
    if result["successful"] > 0:
        success(f"Successfully tagged {result['successful']} resource(s)")
    
    if result["failed"] > 0:
        warning(f"Failed to tag {result['failed']} resource(s)")
        
        if result.get("failed_resources"):
            console.print()
            console.print("[bold]Failed resources:[/bold]")
            for arn, error_msg in result["failed_resources"].items():
                console.print(f"  {arn}")
                console.print(f"    Error: {error_msg}")
    
    if result["successful"] == 0 and result["failed"] > 0:
        raise typer.Exit(1)


@tag_app.command("remove")
def remove_tag(
    tag: str = typer.Argument(..., help="Tag key to remove (e.g., 'do-not-nuke')"),
    resource: Optional[str] = typer.Option(
        None,
        "--resource",
        "-r",
        help="Specific resource ARN or logical ID to untag (if not specified, untags all resources)",
    ),
    env: str = typer.Option(
        "default",
        "--env",
        "-e",
        help="Environment from samconfig.toml (e.g., 'dev', 'default')",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode: select resources to untag",
    ),
):
    """
    Remove a tag from stack resources.
    
    Examples:
    
      chore tag remove do-not-nuke                  # Remove from all resources
      
      chore tag remove Environment -r MyLambda      # Remove from specific resource
      
      chore tag remove do-not-nuke --interactive    # Interactive selection
    """
    header("Remove Resource Tag")
    
    tag_key = tag.strip()
    
    if not tag_key:
        error("Tag key cannot be empty")
        raise typer.Exit(1)
    
    info(f"Tag key to remove: {tag_key}")
    console.print()
    
    config = get_config(env)
    aws_client = get_aws_client(config.region)
    
    info(f"Stack: {config.stack_name}")
    info(f"Region: {config.region}")
    console.print()
    
    if interactive and resource:
        error("Cannot use --interactive with --resource")
        error("Use --interactive for selecting multiple resources, or --resource for a specific resource")
        raise typer.Exit(1)
    
    if interactive:
        section("Interactive resource selection")
        
        resources = aws_client.get_stack_resources(config.stack_name)
        
        if not resources:
            warning("No resources found in stack")
            return
        
        arns = select_resources_interactive(resources, aws_client, config)
        
        if not arns:
            info("No resources selected. Aborted.")
            return
        
        info(f"Selected {len(arns)} resource(s)")
        console.print()
        
        if not yes:
            if not typer.confirm(f"Remove tag '{tag_key}' from {len(arns)} selected resource(s)?"):
                info("Aborted.")
                return
    
    elif resource:
        section(f"Removing tag from specific resource: {resource}")
        
        # If resource is a logical ID, convert to ARN
        if not resource.startswith("arn:"):
            resources = aws_client.get_stack_resources(config.stack_name)
            found = False
            for res in resources:
                if res["LogicalResourceId"] == resource:
                    physical_id = res.get("PhysicalResourceId", "")
                    resource_type = res.get("ResourceType", "")
                    info(f"Found resource: {physical_id} ({resource_type})")
                    
                    # Construct ARN if needed
                    if not physical_id.startswith("arn:"):
                        if resource_type.startswith("AWS::Lambda::"):
                            resource = f"arn:aws:lambda:{config.region}:{aws_client.get_account_id()}:function:{physical_id}"
                        elif resource_type.startswith("AWS::DynamoDB::"):
                            resource = f"arn:aws:dynamodb:{config.region}:{aws_client.get_account_id()}:table/{physical_id}"
                        else:
                            resource = physical_id
                    else:
                        resource = physical_id
                    
                    found = True
                    break
            
            if not found:
                error(f"Resource '{resource}' not found in stack")
                raise typer.Exit(1)
        
        arns = [resource]
    
    else:
        section("Removing tag from all stack resources")
        
        arns = aws_client.get_resource_arns(config.stack_name)
        
        if not arns:
            warning("No taggable resources found in stack")
            return
        
        info(f"Found {len(arns)} taggable resources")
        console.print()
        
        if not yes:
            if not typer.confirm(f"Remove tag '{tag_key}' from all {len(arns)} resources?"):
                info("Aborted.")
                return
    
    console.print()
    info("Removing tags...")
    
    result = aws_client.untag_resources(arns, [tag_key])
    
    console.print()
    
    if result["successful"] > 0:
        success(f"Successfully removed tag from {result['successful']} resource(s)")
    
    if result["failed"] > 0:
        warning(f"Failed to remove tag from {result['failed']} resource(s)")
        
        if result.get("failed_resources"):
            console.print()
            console.print("[bold]Failed resources:[/bold]")
            for arn, error_msg in result["failed_resources"].items():
                console.print(f"  {arn}")
                console.print(f"    Error: {error_msg}")
    
    if result["successful"] == 0 and result["failed"] > 0:
        raise typer.Exit(1)

