"""Rich console utilities for formatting output."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def success(message: str):
    """Display a success message."""
    console.print(f"[green][✓][/green] {message}")


def error(message: str):
    """Display an error message."""
    console.print(f"[red][X][/red] {message}")


def warning(message: str):
    """Display a warning message."""
    console.print(f"[yellow][!][/yellow] {message}")


def info(message: str):
    """Display an info message."""
    console.print(f"[blue][i][/blue] {message}")


def header(message: str):
    """Display a header."""
    console.print()
    console.print(Panel(Text(message, justify="center"), border_style="cyan"))
    console.print()


def section(message: str):
    """Display a section header."""
    console.print()
    console.print(f"[bold cyan]{message}[/bold cyan]")
    console.print("=" * len(message))
    console.print()

