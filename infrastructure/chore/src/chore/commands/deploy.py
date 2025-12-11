"""Deployment commands for backend and frontend."""

import typer
import shutil
import json
from pathlib import Path
from typing import Optional
from chore.cli import deploy_app
from chore.core.console import console, success, error, warning, info, header, section
from chore.core.config import get_config
from chore.core.aws import get_aws_client
from chore.core.shell import run_command, run_sam_build, run_sam_deploy, run_npm_build


@deploy_app.command("backend")
def deploy_backend(
    mode: str = typer.Argument(
        "config",
        help="Deployment mode: 'config' (use samconfig.toml) or 'guided' (interactive)",
    ),
    env: str = typer.Option(
        "dev",
        "--env",
        "-e",
        help="Environment from samconfig.toml (e.g., 'dev', 'default')",
    ),
):
    """
    Deploy the backend API using AWS SAM.
    
    Replaces: deploy.sh
    """
    header("Building and Deploying Estimation Tool API")
    
    # Navigate from: .../infrastructure/chore/src/chore/commands/deploy.py
    # To: .../Estimation (project root)
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    infrastructure_dir = project_root / "infrastructure"
    template_path = infrastructure_dir / "template.yaml"
    
    if not template_path.exists():
        error(f"Template not found: {template_path}")
        raise typer.Exit(1)
    
    if mode not in ["config", "guided"]:
        error("Invalid deployment mode. Use 'config' or 'guided'")
        raise typer.Exit(1)
    
    if mode == "guided":
        section("Running GUIDED deployment (interactive)")
        
        info("Step 1: Building Lambda package...")
        if not run_sam_build(str(template_path), use_container=True, cwd=str(project_root)):
            error("SAM build failed")
            raise typer.Exit(1)
        
        console.print()
        info("Step 2: Deploying with guided prompts...")
        
        cmd = [
            "sam", "deploy",
            "--guided",
            "--template", str(template_path),
            "--stack-name", "estimation-tool-api",
            "--capabilities", "CAPABILITY_IAM",
        ]
        
        exit_code, _, _ = run_command(cmd, cwd=str(project_root))
        if exit_code != 0:
            error("Deployment failed")
            raise typer.Exit(1)
    
    else:  # config mode
        section("Running CONFIG-BASED deployment (using samconfig.toml)")
        
        try:
            config = get_config(env)
        except Exception as e:
            error(f"Failed to load config: {e}")
            raise typer.Exit(1)
        
        info(f"Using environment: {env}")
        info(f"Stack name: {config.stack_name}")
        info(f"Region: {config.region}")
        console.print()
        
        info("Step 1: Cleaning previous build artifacts...")
        build_dir = project_root / ".aws-sam" / "build"
        cache_dir = project_root / ".aws-sam" / "cache"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        
        console.print()
        info("Step 2: Building Lambda package with dependencies...")
        if not run_sam_build(str(template_path), use_container=True, cwd=str(project_root)):
            error("SAM build failed")
            raise typer.Exit(1)
        
        console.print()
        info("Step 3: Verifying build artifacts...")
        
        estimation_func_dir = project_root / ".aws-sam" / "build" / "EstimationFunction"
        if not estimation_func_dir.exists():
            error("Build directory not found")
            raise typer.Exit(1)
        
        mangum_found = any(
            item.name.startswith("mangum") for item in estimation_func_dir.iterdir()
        )
        
        if mangum_found:
            success("mangum found in build")
        else:
            error("mangum NOT FOUND - deployment will fail!")
            raise typer.Exit(1)
        
        console.print()
        info(f"Step 4: Deploying using samconfig.toml [{env}] profile...")
        
        built_template = project_root / ".aws-sam" / "build" / "template.yaml"
        if not run_sam_deploy(
            config_env=env,
            template_file=str(built_template),
            stack_name=config.stack_name,
            region=config.region,
            cwd=str(project_root),
        ):
            error("Deployment failed")
            raise typer.Exit(1)
    
    console.print()
    header("Deployment Complete!")
    console.print()
    
    try:
        config = get_config(env) if mode == "config" else get_config("default")
        aws_client = get_aws_client(config.region)
        api_url = aws_client.get_stack_output(config.stack_name, "EstimationApiUrl")
        
        if api_url:
            console.print(f"[bold]API URL:[/bold] {api_url}")
            console.print()
            console.print("[bold]Test health endpoint:[/bold]")
            console.print(f"  curl {api_url}/health")
            console.print()
            console.print("[bold]Update frontend configuration:[/bold]")
            console.print(f"  VITE_API_BASE_URL={api_url}")
    except Exception:
        pass
    
    console.print()
    info("Note: If you see import errors, ensure all dependencies are in backend/requirements.txt")


@deploy_app.command("frontend")
def deploy_frontend(
    api_url: Optional[str] = typer.Option(
        None,
        "--api-url",
        help="Override API URL (default: fetch from CloudFormation)",
    ),
    bucket: Optional[str] = typer.Option(
        None,
        "--bucket",
        help="Override S3 bucket name",
    ),
):
    """
    Deploy the frontend to S3.
    
    Replaces: deploy-frontend.sh
    """
    header("Deploy Frontend to S3")
    
    # Navigate from: .../infrastructure/chore/src/chore/commands/deploy.py
    # To: .../Estimation (project root)
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        error(f"Frontend directory not found: {frontend_dir}")
        raise typer.Exit(1)
    
    config = get_config("default")
    aws_client = get_aws_client(config.region)
    account_id = aws_client.get_account_id()
    
    bucket_name = bucket or f"estimation-tool-frontend-{account_id}"
    stack_name = config.stack_name
    
    if not api_url:
        info("Fetching API URL from CloudFormation stack...")
        api_url = aws_client.get_stack_output(stack_name, "EstimationApiUrl")
        
        if not api_url:
            error(f"Could not retrieve API URL from stack '{stack_name}'")
            error("Please provide --api-url manually or ensure the backend stack is deployed")
            raise typer.Exit(1)
        
        success(f"API URL: {api_url}")
    
    websocket_url = aws_client.get_stack_output(stack_name, "WebSocketApiUrl")
    if websocket_url:
        info(f"WebSocket URL: {websocket_url}")
    
    info(f"S3 Bucket: {bucket_name}")
    console.print()
    
    section("Step 1: Building frontend")
    
    env_file = frontend_dir / ".env.production"
    env_file.write_text(f"VITE_API_BASE_URL={api_url}\n")
    
    info("Building with production configuration...")
    if not run_npm_build(str(frontend_dir)):
        error("Frontend build failed")
        raise typer.Exit(1)
    
    success("Build completed successfully")
    console.print()
    
    section("Step 2: Setting up S3 bucket")
    
    if not aws_client.bucket_exists(bucket_name):
        info(f"Creating S3 bucket: {bucket_name}")
        if not aws_client.create_bucket(bucket_name):
            raise typer.Exit(1)
        
        info("Enabling versioning...")
        aws_client.s3.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Enabled"},
        )
    else:
        info(f"Bucket already exists: {bucket_name}")
    
    info("Configuring bucket for static website hosting...")
    aws_client.s3.put_bucket_website(
        Bucket=bucket_name,
        WebsiteConfiguration={
            "IndexDocument": {"Suffix": "index.html"},
            "ErrorDocument": {"Key": "index.html"},
        },
    )
    
    console.print()
    section("Step 3: Uploading frontend files")
    
    dist_dir = frontend_dir / "dist"
    if not dist_dir.exists():
        error("dist directory not found. Build may have failed.")
        raise typer.Exit(1)
    
    cmd = [
        "aws", "s3", "sync", str(dist_dir), f"s3://{bucket_name}",
        "--delete",
        "--region", config.region,
        "--cache-control", "public, max-age=31536000, immutable",
        "--exclude", "index.html",
    ]
    run_command(cmd, cwd=str(frontend_dir))
    
    cmd = [
        "aws", "s3", "cp", str(dist_dir / "index.html"), f"s3://{bucket_name}/index.html",
        "--region", config.region,
        "--cache-control", "no-cache, no-store, must-revalidate",
    ]
    run_command(cmd, cwd=str(frontend_dir))
    
    success("Upload completed")
    console.print()
    
    section("Step 4: Configuring bucket policy")
    
    info("Fetching S3 VPC endpoint ID from CloudFormation stack...")
    s3_vpc_endpoint_id = aws_client.get_stack_output(stack_name, "S3VpcEndpointId")
    
    if not s3_vpc_endpoint_id:
        error("Could not retrieve S3 VPC endpoint ID from stack")
        error("Ensure the backend stack is deployed with VPC endpoints")
        raise typer.Exit(1)
    
    info(f"S3 VPC Endpoint ID: {s3_vpc_endpoint_id}")
    
    vpc_cidr = aws_client.get_stack_parameter(stack_name, "VpcCidrBlock")
    if not vpc_cidr:
        warning("VPC CIDR not found, using endpoint-only policy")
        vpc_cidr = None
    
    info("Applying VPC endpoint-based bucket policy...")
    
    policy_statements = [
        {
            "Sid": "DenyAllExceptVpcEndpoint",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
            "Condition": {
                "StringNotEquals": {
                    "aws:SourceVpce": s3_vpc_endpoint_id
                }
            }
        },
        {
            "Sid": "AllowVpcEndpointAccess",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceVpce": s3_vpc_endpoint_id
                }
            }
        }
    ]
    
    if vpc_cidr:
        policy_statements.insert(1, {
            "Sid": "DenyNonVpcCidr",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
            "Condition": {
                "StringNotLike": {
                    "aws:SourceIp": f"{vpc_cidr}/*"
                }
            }
        })
    
    policy = {
        "Version": "2012-10-17",
        "Statement": policy_statements
    }
    
    aws_client.s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    
    aws_client.put_bucket_policy(bucket_name, json.dumps(policy))
    success("Bucket policy applied")
    console.print()
    
    website_url = f"http://{bucket_name}.s3-website-{config.region}.amazonaws.com"
    
    header("Frontend Deployment Complete")
    console.print()
    console.print(f"[bold]Frontend URL:[/bold] {website_url}")
    console.print(f"[bold]API URL:[/bold] {api_url}")
    if websocket_url:
        console.print(f"[bold]WebSocket URL:[/bold] {websocket_url}")
    console.print()
    info("Access restricted to VPC endpoint only")
    info(f"S3 VPC Endpoint: {s3_vpc_endpoint_id}")

