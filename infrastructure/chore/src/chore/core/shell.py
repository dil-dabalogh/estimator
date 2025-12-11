"""Shell command execution utilities."""

import subprocess
from typing import Optional, List, Dict
from rich.live import Live
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from chore.core.console import console, error


def run_command(
    command: str | List[str],
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    capture_output: bool = False,
    show_output: bool = True,
) -> tuple[int, str, str]:
    """
    Execute a shell command with optional output capture.
    
    Args:
        command: Command string or list of command parts
        cwd: Working directory for command execution
        env: Environment variables
        capture_output: If True, capture stdout/stderr instead of streaming
        show_output: If True, show output in real-time (only when capture_output=False)
    
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    if isinstance(command, str):
        cmd_list = command.split()
    else:
        cmd_list = command
    
    if capture_output:
        result = subprocess.run(
            cmd_list,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr
    
    if show_output:
        process = subprocess.Popen(
            cmd_list,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        stdout_lines = []
        if process.stdout:
            for line in process.stdout:
                console.print(line.rstrip())
                stdout_lines.append(line)
        
        process.wait()
        return process.returncode, ''.join(stdout_lines), ''
    else:
        result = subprocess.run(
            cmd_list,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode, '', ''


def run_sam_build(
    template_path: str,
    use_container: bool = True,
    cwd: Optional[str] = None,
) -> bool:
    """
    Run SAM build command.
    
    Args:
        template_path: Path to SAM template
        use_container: Whether to use container for build
        cwd: Working directory
    
    Returns:
        True if successful, False otherwise
    """
    cmd = ["sam", "build", "--template", template_path]
    if use_container:
        cmd.append("--use-container")
    
    exit_code, _, _ = run_command(cmd, cwd=cwd)
    return exit_code == 0


def run_sam_deploy(
    config_env: str,
    template_file: str,
    stack_name: str,
    region: str,
    cwd: Optional[str] = None,
    guided: bool = False,
    parameter_overrides: Optional[Dict[str, str]] = None,
) -> bool:
    """
    Run SAM deploy command.
    
    Args:
        config_env: Config environment (e.g., 'dev', 'default')
        template_file: Path to built template
        stack_name: CloudFormation stack name
        region: AWS region
        cwd: Working directory
        guided: Whether to use guided mode
        parameter_overrides: Optional dict of parameter overrides
    
    Returns:
        True if successful, False otherwise
    """
    if guided:
        cmd = [
            "sam", "deploy",
            "--guided",
            "--template", template_file,
            "--stack-name", stack_name,
            "--capabilities", "CAPABILITY_IAM",
        ]
    else:
        cmd = [
            "sam", "deploy",
            "--config-env", config_env,
            "--template-file", template_file,
            "--stack-name", stack_name,
            "--capabilities", "CAPABILITY_IAM",
            "--resolve-s3",
            "--force-upload",
            "--no-confirm-changeset",
            "--region", region,
        ]
        
        # Only pass parameter overrides if explicitly provided (for overriding specific parameters)
        # When using --config-env, SAM CLI automatically reads parameters from samconfig.toml
        # Passing --parameter-overrides would replace all config file parameters, so we only
        # use it when we want to override specific parameters (not when using all config params)
        if parameter_overrides:
            # Check if this is a partial override (fewer params than typically in config)
            # For now, we'll only pass overrides if explicitly needed
            # In most cases, we should let SAM CLI read from config file
            param_list = []
            for key, value in parameter_overrides.items():
                # Handle empty values
                if value == "":
                    param_list.append(f"{key}=")
                else:
                    # For CommaDelimitedList, don't quote - SAM handles them correctly
                    # Only quote values with spaces (not commas, as those are valid for lists)
                    if " " in str(value):
                        param_list.append(f'{key}="{value}"')
                    else:
                        param_list.append(f"{key}={value}")
            cmd.extend(["--parameter-overrides", " ".join(param_list)])
    
    exit_code, _, _ = run_command(cmd, cwd=cwd)
    return exit_code == 0


def run_npm_build(cwd: str) -> bool:
    """
    Run npm build command.
    
    Args:
        cwd: Working directory (frontend directory)
    
    Returns:
        True if successful, False otherwise
    """
    exit_code, _, _ = run_command(["npm", "run", "build"], cwd=cwd)
    return exit_code == 0

