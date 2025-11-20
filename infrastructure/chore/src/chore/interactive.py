"""Interactive menu mode for chore CLI."""

import questionary
from rich.console import Console
from rich.panel import Panel
from chore.core.console import header, section, info, success, error

console = Console()


def run_interactive_mode():
    """Launch interactive TUI menu."""
    header("Chore CLI - Interactive Mode")
    
    while True:
        console.print()
        choice = questionary.select(
            "Select a category:",
            choices=[
                "Deploy",
                "IP Management",
                "Tag Management",
                "Diagnose",
                "Bedrock Agent",
                "Exit",
            ],
        ).ask()
        
        if not choice or choice == "Exit":
            info("Goodbye!")
            break
        
        if choice == "Deploy":
            show_deploy_menu()
        elif choice == "IP Management":
            show_ip_menu()
        elif choice == "Tag Management":
            show_tag_menu()
        elif choice == "Diagnose":
            show_diagnose_menu()
        elif choice == "Bedrock Agent":
            show_bedrock_menu()


def show_deploy_menu():
    """Show deployment submenu."""
    section("Deploy")
    
    choice = questionary.select(
        "Select deployment action:",
        choices=[
            "Deploy Backend (config mode)",
            "Deploy Backend (guided mode)",
            "Deploy Frontend",
            "Back to Main Menu",
        ],
    ).ask()
    
    if not choice or choice == "Back to Main Menu":
        return
    
    if choice == "Deploy Backend (config mode)":
        from chore.commands.deploy import deploy_backend
        try:
            deploy_backend("config", env="dev")
        except Exception as e:
            error(f"Deployment failed: {e}")
    
    elif choice == "Deploy Backend (guided mode)":
        from chore.commands.deploy import deploy_backend
        try:
            deploy_backend("guided", env="dev")
        except Exception as e:
            error(f"Deployment failed: {e}")
    
    elif choice == "Deploy Frontend":
        from chore.commands.deploy import deploy_frontend
        
        use_defaults = questionary.confirm(
            "Use default settings (fetch API URL from CloudFormation, with IP filtering)?",
            default=True,
        ).ask()
        
        try:
            if use_defaults:
                deploy_frontend()
            else:
                api_url = questionary.text(
                    "API URL (leave empty to fetch from CloudFormation):",
                ).ask()
                
                no_ip_filter = questionary.confirm(
                    "Disable IP filtering?",
                    default=False,
                ).ask()
                
                deploy_frontend(
                    api_url=api_url if api_url else None,
                    no_ip_filter=no_ip_filter,
                )
        except Exception as e:
            error(f"Deployment failed: {e}")


def show_ip_menu():
    """Show IP management submenu."""
    section("IP Management")
    
    choice = questionary.select(
        "Select IP management action:",
        choices=[
            "List current whitelist",
            "Add current IP",
            "Add custom IP/CIDR",
            "Remove IP/CIDR",
            "Remove all IPs",
            "Back to Main Menu",
        ],
    ).ask()
    
    if not choice or choice == "Back to Main Menu":
        return
    
    if choice == "List current whitelist":
        from chore.commands.ip_whitelist import list_ips
        try:
            list_ips()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Add current IP":
        from chore.commands.ip_whitelist import add_current_ip
        try:
            add_current_ip()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Add custom IP/CIDR":
        ip_cidr = questionary.text(
            "Enter IP address or CIDR range:",
        ).ask()
        
        if ip_cidr:
            from chore.commands.ip_whitelist import add_ip
            try:
                add_ip(ip_cidr)
            except Exception as e:
                error(f"Failed: {e}")
    
    elif choice == "Remove IP/CIDR":
        ip_cidr = questionary.text(
            "Enter IP address or CIDR range to remove:",
        ).ask()
        
        if ip_cidr:
            from chore.commands.ip_whitelist import remove_ip
            try:
                remove_ip(ip_cidr)
            except Exception as e:
                error(f"Failed: {e}")
    
    elif choice == "Remove all IPs":
        from chore.commands.ip_whitelist import remove_all_ips
        try:
            remove_all_ips()
        except Exception as e:
            error(f"Failed: {e}")


def show_tag_menu():
    """Show tag management submenu."""
    section("Tag Management")
    
    choice = questionary.select(
        "Select tag management action:",
        choices=[
            "List all resources",
            "Add tag to all resources",
            "Add tag to selected resources",
            "Remove tag from all resources",
            "Remove tag from selected resources",
            "Back to Main Menu",
        ],
    ).ask()
    
    if not choice or choice == "Back to Main Menu":
        return
    
    if choice == "List all resources":
        from chore.commands.tag import list_tags
        try:
            list_tags()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Add tag to all resources":
        tag_str = questionary.text(
            "Enter tag in format key=value (e.g., do-not-nuke=true):",
        ).ask()
        
        if tag_str:
            from chore.commands.tag import add_tag
            try:
                add_tag(tag=tag_str, yes=False)
            except Exception as e:
                error(f"Failed: {e}")
    
    elif choice == "Add tag to selected resources":
        tag_str = questionary.text(
            "Enter tag in format key=value (e.g., do-not-nuke=true):",
        ).ask()
        
        if not tag_str:
            return
        
        # Parse and validate tag
        from chore.commands.tag import parse_tag, validate_tag
        key, value = parse_tag(tag_str)
        
        if not key or not value:
            error(f"Invalid tag format: {tag_str}")
            error("Expected format: key=value")
            return
        
        if not validate_tag(key, value):
            error(f"Invalid tag: {key}={value}")
            error("Key must be <= 128 chars, value must be <= 256 chars")
            return
        
        # Get resources and show selection
        from chore.core.config import get_config
        from chore.core.aws import get_aws_client
        from chore.commands.tag import select_resources_interactive
        
        try:
            config = get_config("default")
            aws_client = get_aws_client(config.region)
            resources = aws_client.get_stack_resources(config.stack_name)
            
            if not resources:
                error("No resources found in stack")
                return
            
            arns = select_resources_interactive(resources, aws_client, config)
            
            if not arns:
                info("No resources selected. Aborted.")
                return
            
            # Confirm and apply tags
            confirm = questionary.confirm(
                f"Apply tag '{key}={value}' to {len(arns)} selected resource(s)?",
                default=True,
            ).ask()
            
            if not confirm:
                info("Aborted.")
                return
            
            info("Applying tags...")
            result = aws_client.tag_resources(arns, {key: value})
            
            console.print()
            if result["successful"] > 0:
                success(f"Successfully tagged {result['successful']} resource(s)")
            
            if result["failed"] > 0:
                error(f"Failed to tag {result['failed']} resource(s)")
                if result.get("failed_resources"):
                    console.print()
                    console.print("[bold]Failed resources:[/bold]")
                    for arn, error_msg in result["failed_resources"].items():
                        console.print(f"  {arn}")
                        console.print(f"    Error: {error_msg}")
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Remove tag from all resources":
        tag_key = questionary.text(
            "Enter tag key to remove (e.g., do-not-nuke):",
        ).ask()
        
        if tag_key:
            from chore.commands.tag import remove_tag
            try:
                remove_tag(tag=tag_key, yes=False)
            except Exception as e:
                error(f"Failed: {e}")
    
    elif choice == "Remove tag from selected resources":
        tag_key = questionary.text(
            "Enter tag key to remove (e.g., do-not-nuke):",
        ).ask()
        
        if not tag_key:
            return
        
        # Get resources and show selection
        from chore.core.config import get_config
        from chore.core.aws import get_aws_client
        from chore.commands.tag import select_resources_interactive
        
        try:
            config = get_config("default")
            aws_client = get_aws_client(config.region)
            resources = aws_client.get_stack_resources(config.stack_name)
            
            if not resources:
                error("No resources found in stack")
                return
            
            arns = select_resources_interactive(resources, aws_client, config)
            
            if not arns:
                info("No resources selected. Aborted.")
                return
            
            # Confirm and remove tags
            confirm = questionary.confirm(
                f"Remove tag '{tag_key}' from {len(arns)} selected resource(s)?",
                default=True,
            ).ask()
            
            if not confirm:
                info("Aborted.")
                return
            
            info("Removing tags...")
            result = aws_client.untag_resources(arns, [tag_key])
            
            console.print()
            if result["successful"] > 0:
                success(f"Successfully removed tag from {result['successful']} resource(s)")
            
            if result["failed"] > 0:
                error(f"Failed to remove tag from {result['failed']} resource(s)")
                if result.get("failed_resources"):
                    console.print()
                    console.print("[bold]Failed resources:[/bold]")
                    for arn, error_msg in result["failed_resources"].items():
                        console.print(f"  {arn}")
                        console.print(f"    Error: {error_msg}")
        except Exception as e:
            error(f"Failed: {e}")


def show_diagnose_menu():
    """Show diagnostics submenu."""
    section("Diagnose")
    
    choice = questionary.select(
        "Select diagnostic target:",
        choices=[
            "Diagnose API Health",
            "Diagnose Authorizer",
            "Diagnose Bedrock Agent",
            "Back to Main Menu",
        ],
    ).ask()
    
    if not choice or choice == "Back to Main Menu":
        return
    
    if choice == "Diagnose API Health":
        from chore.commands.diagnose import diagnose_api
        try:
            diagnose_api()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Diagnose Authorizer":
        from chore.commands.diagnose import diagnose_authorizer
        try:
            diagnose_authorizer()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Diagnose Bedrock Agent":
        from chore.commands.diagnose import diagnose_bedrock
        try:
            diagnose_bedrock()
        except Exception as e:
            error(f"Failed: {e}")


def show_bedrock_menu():
    """Show Bedrock agent submenu."""
    section("Bedrock Agent")
    
    choice = questionary.select(
        "Select Bedrock action:",
        choices=[
            "Setup new agent",
            "Update agent instructions",
            "Check permissions",
            "Test agent",
            "Setup MCP action groups",
            "Back to Main Menu",
        ],
    ).ask()
    
    if not choice or choice == "Back to Main Menu":
        return
    
    if choice == "Setup new agent":
        from chore.commands.bedrock import setup_agent
        
        use_defaults = questionary.confirm(
            "Use default agent settings?",
            default=True,
        ).ask()
        
        try:
            if use_defaults:
                setup_agent()
            else:
                agent_name = questionary.text(
                    "Agent name:",
                    default="estimation-tool-agent",
                ).ask()
                
                foundation_model = questionary.text(
                    "Foundation model:",
                    default="anthropic.claude-3-5-sonnet-20241022-v2:0",
                ).ask()
                
                setup_agent(agent_name=agent_name, foundation_model=foundation_model)
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Update agent instructions":
        from chore.commands.bedrock import update_agent
        try:
            update_agent()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Check permissions":
        from chore.commands.bedrock import setup_permissions
        try:
            setup_permissions()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Test agent":
        from chore.commands.bedrock import test_agent
        
        custom_prompt = questionary.confirm(
            "Use custom prompt?",
            default=False,
        ).ask()
        
        try:
            if custom_prompt:
                prompt = questionary.text(
                    "Enter test prompt:",
                    default="Hello, can you help me estimate a project?",
                ).ask()
                test_agent(prompt=prompt)
            else:
                test_agent()
        except Exception as e:
            error(f"Failed: {e}")
    
    elif choice == "Setup MCP action groups":
        from chore.commands.bedrock import setup_mcp
        try:
            setup_mcp()
        except Exception as e:
            error(f"Failed: {e}")

