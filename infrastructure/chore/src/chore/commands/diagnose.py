"""Diagnostic commands for troubleshooting deployments."""

import typer
from pathlib import Path
from chore.cli import diagnose_app
from chore.core.console import console, success, error, warning, info, section


@diagnose_app.command("build")
def diagnose_build():
    """
    Diagnose the SAM build artifacts to verify all dependencies are present.
    """
    section("Diagnosing SAM Build Artifacts")
    
    # Navigate to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    build_dir = project_root / ".aws-sam" / "build"
    
    if not build_dir.exists():
        error(f"Build directory not found: {build_dir}")
        error("Please run 'sam build' or 'chore deploy backend' first")
        raise typer.Exit(1)
    
    info(f"Build directory: {build_dir}")
    console.print()
    
    # Check EstimationFunction
    estimation_func_dir = build_dir / "EstimationFunction"
    if not estimation_func_dir.exists():
        error("EstimationFunction build directory not found")
        raise typer.Exit(1)
    
    success(f"EstimationFunction directory found: {estimation_func_dir}")
    console.print()
    
    # List all top-level items
    section("Top-level items in EstimationFunction build:")
    items = sorted(estimation_func_dir.iterdir())
    for item in items:
        if item.is_dir():
            console.print(f"  [blue]DIR [/blue] {item.name}/")
        else:
            console.print(f"  [green]FILE[/green] {item.name}")
    console.print()
    
    # Check for critical dependencies
    section("Checking critical dependencies:")
    
    required_packages = [
        "mangum",
        "fastapi",
        "pydantic",
        "uvicorn",
        "boto3",
        "openai",
        "requests"
    ]
    
    missing_packages = []
    found_packages = []
    
    for package in required_packages:
        # Check if package directory exists
        package_found = False
        for item in estimation_func_dir.iterdir():
            if item.name.lower().startswith(package.lower()):
                package_found = True
                found_packages.append(package)
                success(f"  {package:<15} FOUND ({item.name})")
                break
        
        if not package_found:
            missing_packages.append(package)
            error(f"  {package:<15} MISSING")
    
    console.print()
    
    # Check for Python handler files
    section("Checking handler files:")
    
    handler_files = [
        "lambda_handler.py",
        "app.py",
        "authorizer.py",
        "websocket_handlers.py"
    ]
    
    for handler in handler_files:
        handler_path = estimation_func_dir / handler
        if handler_path.exists():
            success(f"  {handler:<25} EXISTS")
        else:
            error(f"  {handler:<25} MISSING")
    
    console.print()
    
    # Summary
    section("Diagnosis Summary:")
    
    if missing_packages:
        error(f"Found {len(missing_packages)} missing package(s): {', '.join(missing_packages)}")
        error("The deployment will likely fail due to missing dependencies")
        console.print()
        info("Possible solutions:")
        console.print("  1. Clean and rebuild: rm -rf .aws-sam && sam build --use-container")
        console.print("  2. Verify backend/requirements.txt includes all required packages")
        console.print("  3. Check SAM CLI version: sam --version")
        raise typer.Exit(1)
    else:
        success(f"All {len(required_packages)} required packages found")
        success("Build artifacts look healthy")
        console.print()
        info("You can proceed with deployment: chore deploy backend")
