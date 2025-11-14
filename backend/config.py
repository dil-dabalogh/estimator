import os
from typing import Optional
from dataclasses import dataclass
from llm_service import LLMConfig


@dataclass
class AppConfig:
    provider: str
    llm_config: LLMConfig
    openai_api_key: Optional[str] = None
    bedrock_region: Optional[str] = None
    atlassian_url: Optional[str] = None
    atlassian_email: Optional[str] = None
    atlassian_token: Optional[str] = None


def load_config() -> AppConfig:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider not in ["openai", "bedrock"]:
        raise ValueError(f"Invalid provider: {provider}")
    
    openai_api_key = None
    bedrock_region = None
    
    if provider == "openai":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OpenAI API key not found")
        
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        
        llm_config = LLMConfig(
            provider="openai",
            model=model,
            temperature=temperature,
        )
    else:
        bedrock_region = os.getenv("AWS_REGION")
        if not bedrock_region:
            raise ValueError("AWS region not found")
        
        model = os.getenv("BEDROCK_MODEL")
        agent_id = os.getenv("BEDROCK_AGENT_ID")
        agent_alias_id = os.getenv("BEDROCK_AGENT_ALIAS_ID")
        
        if not model and not (agent_id and agent_alias_id):
            model = "anthropic.claude-3-sonnet-20240229-v1:0"
        
        temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0.2"))
        
        llm_config = LLMConfig(
            provider="bedrock",
            model=model,
            agent_id=agent_id,
            agent_alias_id=agent_alias_id,
            temperature=temperature,
        )
    
    atlassian_url = os.getenv("ATLASSIAN_URL")
    atlassian_email = os.getenv("ATLASSIAN_USER_EMAIL")
    atlassian_token = os.getenv("ATLASSIAN_API_TOKEN")
    
    return AppConfig(
        provider=provider,
        llm_config=llm_config,
        openai_api_key=openai_api_key,
        bedrock_region=bedrock_region,
        atlassian_url=atlassian_url,
        atlassian_email=atlassian_email,
        atlassian_token=atlassian_token,
    )

