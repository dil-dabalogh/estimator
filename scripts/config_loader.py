"""
Configuration Loader

Loads configuration from a config file (INI format) with sections for [openai] and [bedrock].
Environment variables can override config file values.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Import will be resolved at runtime
try:
    from scripts.llm_providers import LLMConfig
except ImportError:
    # Fallback for when running as module
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from llm_providers import LLMConfig


@dataclass
class AppConfig:
    """Application configuration."""
    provider: str  # "openai" or "bedrock"
    llm_config: LLMConfig
    # Provider-specific credentials (not in LLMConfig to avoid exposing secrets)
    openai_api_key: Optional[str] = None
    bedrock_region: Optional[str] = None
    # Atlassian config (can come from env or config file)
    atlassian_url: Optional[str] = None
    atlassian_email: Optional[str] = None
    atlassian_token: Optional[str] = None


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Load configuration from file and environment variables.
    
    Config file format (INI):
    [provider]
    provider = openai  # or bedrock
    
    [openai]
    api_key = your-key-here  # or use OPENAI_API_KEY env var
    model = gpt-5
    temperature = 0.2
    
    [bedrock]
    region = us-west-2  # or use AWS_REGION env var
    model = anthropic.claude-3-sonnet-20240229-v1:0
    # OR for agents:
    # agent_id = YOUR_AGENT_ID
    # agent_alias_id = YOUR_ALIAS_ID
    temperature = 0.2
    
    [atlassian]
    url = https://your-domain.atlassian.net/wiki
    email = you@company.com
    token = your-token  # or use ATLASSIAN_API_TOKEN env var
    
    Environment variables override config file values.
    """
    config = configparser.ConfigParser()
    
    # Default config file location
    if config_path is None:
        repo_root = Path(__file__).resolve().parents[1]
        config_path = repo_root / "orchestrator.conf"
    
    # Load config file if it exists
    if config_path.exists():
        config.read(config_path)
    
    # Determine provider (from config file or env, default to openai)
    provider = (
        os.getenv("LLM_PROVIDER")
        or config.get("provider", "provider", fallback="openai")
        or "openai"
    ).lower()
    
    if provider not in ["openai", "bedrock"]:
        raise ValueError(f"Invalid provider: {provider}. Must be 'openai' or 'bedrock'")
    
    # Load LLM-specific config
    openai_api_key = None
    bedrock_region = None
    
    if provider == "openai":
        openai_api_key = (
            os.getenv("OPENAI_API_KEY")
            or config.get("openai", "api_key", fallback=None)
        )
        if not openai_api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY env var or api_key in [openai] section"
            )
        
        model = (
            os.getenv("OPENAI_MODEL")
            or config.get("openai", "model", fallback="gpt-5")
        )
        
        temperature = float(
            os.getenv("OPENAI_TEMPERATURE")
            or config.get("openai", "temperature", fallback="0.2")
        )
        
        llm_config = LLMConfig(
            provider="openai",
            model=model,
            temperature=temperature,
        )
        
    else:  # bedrock
        bedrock_region = (
            os.getenv("AWS_REGION")
            or config.get("bedrock", "region", fallback=None)
        )
        if not bedrock_region:
            raise ValueError(
                "AWS region not found. Set AWS_REGION env var or region in [bedrock] section"
            )
        
        model = (
            os.getenv("BEDROCK_MODEL")
            or config.get("bedrock", "model", fallback=None)
        )
        
        agent_id = (
            os.getenv("BEDROCK_AGENT_ID")
            or config.get("bedrock", "agent_id", fallback=None)
        )
        
        agent_alias_id = (
            os.getenv("BEDROCK_AGENT_ALIAS_ID")
            or config.get("bedrock", "agent_alias_id", fallback=None)
        )
        
        if not model and not (agent_id and agent_alias_id):
            # Default to a common Claude model
            model = "anthropic.claude-3-sonnet-20240229-v1:0"
        
        temperature = float(
            os.getenv("BEDROCK_TEMPERATURE")
            or config.get("bedrock", "temperature", fallback="0.2")
        )
        
        llm_config = LLMConfig(
            provider="bedrock",
            model=model,
            agent_id=agent_id,
            agent_alias_id=agent_alias_id,
            temperature=temperature,
        )
    
    # Load Atlassian config (prefer env vars, fallback to config file)
    atlassian_url = (
        os.getenv("ATLASSIAN_URL")
        or os.getenv("CONFLUENCE_BASE_URL")
        or config.get("atlassian", "url", fallback=None)
    )
    
    atlassian_email = (
        os.getenv("ATLASSIAN_USER_EMAIL")
        or os.getenv("CONFLUENCE_EMAIL")
        or config.get("atlassian", "email", fallback=None)
    )
    
    atlassian_token = (
        os.getenv("ATLASSIAN_API_TOKEN")
        or os.getenv("ATLASSIAN_API_KEY")
        or os.getenv("CONFLUENCE_API_TOKEN")
        or config.get("atlassian", "token", fallback=None)
    )
    
    return AppConfig(
        provider=provider,
        llm_config=llm_config,
        openai_api_key=openai_api_key,
        bedrock_region=bedrock_region,
        atlassian_url=atlassian_url,
        atlassian_email=atlassian_email,
        atlassian_token=atlassian_token,
    )

