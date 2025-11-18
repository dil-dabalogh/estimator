# Chore CLI - Infrastructure Management Tool

A modern Python CLI/TUI tool for managing the Estimation Tool infrastructure on AWS.

## Overview

Chore CLI provides a unified interface for deploying, managing, and diagnosing the Estimation Tool infrastructure. It replaces the collection of shell scripts with a cohesive Python-based tool that supports both direct command invocation and interactive menu navigation.

## Installation

1. Install dependencies:

```bash
cd infrastructure/chore
pip install -r requirements.txt
```

2. Run the tool:

```bash
cd infrastructure
python -m chore --help
```

For convenience, you can create an alias:

```bash
alias chore='python -m chore'
```

Or install in development mode:

```bash
cd infrastructure
pip install -e chore/
```

## Usage

### Direct Command Mode

Execute commands directly from the command line:

```bash
# Deploy commands
python -m chore deploy backend config
python -m chore deploy backend guided
python -m chore deploy frontend

# IP whitelist management
python -m chore ip list
python -m chore ip add-current
python -m chore ip add 192.168.1.5
python -m chore ip remove 192.168.1.5
python -m chore ip remove-all

# Diagnostics
python -m chore diagnose api
python -m chore diagnose authorizer
python -m chore diagnose bedrock

# Bedrock agent management
python -m chore bedrock setup
python -m chore bedrock update
python -m chore bedrock test
python -m chore bedrock permissions
```

### Interactive Mode

Launch the interactive TUI menu:

```bash
python -m chore --interactive
# or
python -m chore -i
```

The interactive mode provides a menu-driven interface for all commands with guided prompts for parameters.

## Command Reference

### Deploy Commands

#### `chore deploy backend [config|guided]`

Deploy the backend API using AWS SAM.

- `config` mode: Uses settings from `samconfig.toml` (default)
- `guided` mode: Interactive guided deployment

**Options:**
- `--env, -e TEXT`: Environment from samconfig.toml (default: dev)

**Example:**
```bash
python -m chore deploy backend config --env dev
```

#### `chore deploy frontend`

Deploy the frontend to S3 with optional IP filtering.

**Options:**
- `--api-url TEXT`: Override API URL (default: fetch from CloudFormation)
- `--no-ip-filter`: Deploy without IP filtering (public access)
- `--bucket TEXT`: Override S3 bucket name

**Example:**
```bash
python -m chore deploy frontend --no-ip-filter
```

### IP Whitelist Commands

#### `chore ip list`

Show the current IP whitelist from CloudFormation.

#### `chore ip add-current`

Automatically detect and add your current IP address to the whitelist.

#### `chore ip add <IP|CIDR>`

Add a specific IP address or CIDR range to the whitelist.

**Example:**
```bash
python -m chore ip add 192.168.1.5
python -m chore ip add 10.0.0.0/24
```

#### `chore ip remove <IP|CIDR>`

Remove a specific IP address or CIDR range from the whitelist.

**Example:**
```bash
python -m chore ip remove 192.168.1.5
```

#### `chore ip remove-all`

Remove all IPs from the whitelist (deny all external access). Requires confirmation.

### Diagnostic Commands

#### `chore diagnose api`

Diagnose API health and configuration:
- Check stack status
- Test API URL
- Display Lambda configuration
- Show recent error logs
- Test health endpoint

#### `chore diagnose authorizer`

Diagnose Lambda authorizer setup:
- Check authorizer Lambda configuration
- Verify environment variables
- Check API Gateway authorizer configuration
- View recent authorization logs

#### `chore diagnose bedrock`

Diagnose and auto-fix Bedrock Agent issues:
- Check agent status and preparation
- Verify IAM role permissions
- Validate foundation model access
- Automatically prepare agent if needed

### Bedrock Agent Commands

#### `chore bedrock setup`

Create a new Bedrock Agent with personas from `personas/combined_agent_instruction.txt`.

**Options:**
- `--name TEXT`: Agent name (default: estimation-tool-agent)
- `--model TEXT`: Foundation model (default: anthropic.claude-3-5-sonnet-20241022-v2:0)

**Example:**
```bash
python -m chore bedrock setup --name my-agent
```

#### `chore bedrock update`

Update agent instructions from persona files and re-prepare the agent.

**Options:**
- `--agent-id TEXT`: Agent ID (reads from config if not provided)

#### `chore bedrock permissions`

Check IAM permissions for Bedrock Agent testing. Provides guidance on required permissions.

#### `chore bedrock test`

Test Bedrock Agent invocation with a sample prompt.

**Options:**
- `--agent-id TEXT`: Agent ID (reads from config if not provided)
- `--alias-id TEXT`: Agent alias ID (reads from config if not provided)
- `--prompt TEXT`: Test prompt (default: "Hello, can you help me estimate a project?")

**Example:**
```bash
python -m chore bedrock test --prompt "Estimate a REST API project"
```

#### `chore bedrock setup-mcp`

Configure MCP (Model Context Protocol) action groups. Currently a placeholder - use the shell script instead.

## Configuration

The tool reads configuration from `infrastructure/samconfig.toml`:

- Stack name
- AWS region
- Deployment parameters
- Bedrock agent IDs

Default environment is `dev`. Use `--env` flag to specify a different environment.

## Architecture

```
infrastructure/chore/
├── __init__.py              # Package metadata
├── __main__.py              # Entry point for python -m chore
├── cli.py                   # Main Typer application
├── interactive.py           # Interactive TUI menu
├── commands/                # Command modules
│   ├── deploy.py            # Deployment commands
│   ├── ip_whitelist.py      # IP management
│   ├── diagnose.py          # Diagnostic commands
│   └── bedrock.py           # Bedrock agent commands
└── core/                    # Core utilities
    ├── aws.py               # AWS API wrappers (boto3)
    ├── config.py            # Configuration parsing
    ├── shell.py             # Shell command execution
    └── console.py           # Rich console utilities
```

## Development

### Adding New Commands

1. Create a new command module in `commands/`
2. Define command group in `cli.py`
3. Add menu item to `interactive.py`

### Testing

Run basic validation:

```bash
python -m chore --help
python -m chore deploy --help
```

## Migration from Shell Scripts

The shell scripts in `infrastructure/` are kept for backward compatibility. The chore tool provides equivalent functionality:

| Shell Script | Chore Command |
|--------------|---------------|
| `deploy.sh` | `chore deploy backend` |
| `deploy-frontend.sh` | `chore deploy frontend` |
| `manage-ip-whitelist.sh` | `chore ip` subcommands |
| `diagnose-api-health.sh` | `chore diagnose api` |
| `diagnose-authorizer.sh` | `chore diagnose authorizer` |
| `diagnose-bedrock-agent.sh` | `chore diagnose bedrock` |
| `setup-bedrock-agent.sh` | `chore bedrock setup` |
| `update-bedrock-agent.sh` | `chore bedrock update` |
| `test_bedrock_agent.py` | `chore bedrock test` |

## Troubleshooting

### Module Not Found

If you get import errors, make sure you're running from the correct directory:

```bash
cd infrastructure
python -m chore --help
```

### AWS Credentials

The tool uses boto3 which reads credentials from:
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- AWS credentials file (`~/.aws/credentials`)
- IAM role (if running on EC2/ECS/Lambda)

### Permission Errors

Ensure your AWS user/role has the necessary permissions:
- CloudFormation operations
- Lambda operations
- S3 operations (for frontend deployment)
- Bedrock operations (for agent management)
- IAM operations (for role creation/verification)

## Future Enhancements

- Full MCP action group setup implementation
- Unit tests with mocked AWS services
- Configuration validation
- Deployment history tracking
- Rollback functionality
- Multi-region support

