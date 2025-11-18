"""Main CLI application using Typer."""

import typer
from rich.console import Console

app = typer.Typer(
    name="chore",
    help="Infrastructure management tool for Estimation Tool",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command("interactive")
def interactive_mode():
    """Launch interactive menu mode."""
    from chore.interactive import run_interactive_mode
    run_interactive_mode()


# Create sub-typer apps
deploy_app = typer.Typer(
    name="deploy",
    help="Deployment commands for backend and frontend",
    no_args_is_help=True,
)

diagnose_app = typer.Typer(
    name="diagnose",
    help="Diagnostic commands for API, authorizer, and Bedrock",
    no_args_is_help=True,
)

bedrock_app = typer.Typer(
    name="bedrock",
    help="Bedrock Agent management commands",
    no_args_is_help=True,
)

ip_app = typer.Typer(
    name="ip",
    help="IP whitelist management commands",
    no_args_is_help=True,
)

# Import command modules to register them with the sub-apps
# This must happen after the apps are created but before they're added to main app
import chore.commands.deploy
import chore.commands.diagnose
import chore.commands.bedrock
import chore.commands.ip_whitelist

# Add sub-apps to main app
app.add_typer(deploy_app, name="deploy")
app.add_typer(diagnose_app, name="diagnose")
app.add_typer(bedrock_app, name="bedrock")
app.add_typer(ip_app, name="ip")


if __name__ == "__main__":
    app()

