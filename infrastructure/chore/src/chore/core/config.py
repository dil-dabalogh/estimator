"""Configuration parsing utilities for samconfig.toml."""

import toml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DeployConfig:
    """Deployment configuration from samconfig.toml."""
    stack_name: str
    region: str
    capabilities: str
    resolve_s3: bool
    s3_prefix: str
    confirm_changeset: bool
    parameter_overrides: Dict[str, str]
    disable_rollback: bool = False


class ConfigParser:
    """Parse and manage samconfig.toml configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config parser with optional config path."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "samconfig.toml"
        
        self.config_path = config_path
        self._config: Optional[Dict[str, Any]] = None
    
    def _load(self):
        """Load config from file."""
        if self._config is None:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            self._config = toml.load(self.config_path)
    
    def get_deploy_config(self, env: str = "default") -> DeployConfig:
        """Get deployment configuration for specified environment."""
        self._load()
        
        deploy_params = self._config.get(env, {}).get("deploy", {}).get("parameters", {})
        global_params = self._config.get(env, {}).get("global", {}).get("parameters", {})
        
        if not deploy_params:
            raise ValueError(f"No deploy configuration found for environment: {env}")
        
        param_overrides = self._parse_parameter_overrides(
            deploy_params.get("parameter_overrides", "")
        )
        
        return DeployConfig(
            stack_name=deploy_params.get("stack_name", "estimation-tool-api"),
            region=global_params.get("region", "us-west-2"),
            capabilities=deploy_params.get("capabilities", "CAPABILITY_IAM"),
            resolve_s3=deploy_params.get("resolve_s3", True),
            s3_prefix=deploy_params.get("s3_prefix", "estimation-tool-api"),
            confirm_changeset=deploy_params.get("confirm_changeset", True),
            parameter_overrides=param_overrides,
            disable_rollback=deploy_params.get("disable_rollback", False),
        )
    
    def _parse_parameter_overrides(self, overrides_str: str) -> Dict[str, str]:
        """Parse parameter overrides string into dictionary."""
        params = {}
        
        if not overrides_str:
            return params
        
        parts = []
        current = []
        in_quotes = False
        
        for char in overrides_str:
            if char == '"':
                in_quotes = not in_quotes
                current.append(char)
            elif char == ' ' and not in_quotes:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)
        
        if current:
            parts.append(''.join(current))
        
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                value = value.strip('"')
                params[key] = value
        
        return params
    
    def get_available_envs(self) -> list[str]:
        """Get list of available environment configurations."""
        self._load()
        envs = []
        for key in self._config.keys():
            if isinstance(self._config[key], dict) and "deploy" in self._config[key]:
                envs.append(key)
        return envs


def get_config(env: str = "default") -> DeployConfig:
    """Get deployment configuration for environment."""
    parser = ConfigParser()
    return parser.get_deploy_config(env)

