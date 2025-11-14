"""
LLM Provider Abstraction Layer

This module provides a unified interface for different LLM providers (OpenAI, Bedrock)
to eliminate code duplication and allow easy switching between providers.
"""

from __future__ import annotations

import abc
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    provider: str  # "openai" or "bedrock"
    model: Optional[str] = None
    agent_id: Optional[str] = None
    agent_alias_id: Optional[str] = None
    temperature: float = 0.2


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""
    
    @abc.abstractmethod
    def generate_text(
        self,
        system_prompt: str,
        user_messages: list[str],
        config: LLMConfig,
        ballpark: Optional[str] = None,
    ) -> str:
        """
        Generate text using the LLM provider.
        
        Args:
            system_prompt: System-level instructions/persona
            user_messages: List of user messages to send
            config: LLM configuration
            ballpark: Optional ballpark estimate to guide generation
            
        Returns:
            Generated text content
        """
        pass
    
    @abc.abstractmethod
    def get_client(self) -> Any:
        """Get the underlying client object."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self._OpenAI = OpenAI
        except ImportError:
            raise RuntimeError(
                "openai package not available. Install dependencies: pip install openai"
            )
    
    def get_client(self) -> Any:
        return self._client
    
    def generate_text(
        self,
        system_prompt: str,
        user_messages: list[str],
        config: LLMConfig,
        ballpark: Optional[str] = None,
    ) -> str:
        if not config.model:
            raise ValueError("OpenAI provider requires model to be set in config")
        
        # Combine user messages
        combined_user_content = "\n\n".join(user_messages)
        
        create_kwargs = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_user_content},
            ],
        }
        
        # Set temperature (lower for more deterministic output, except for GPT-5)
        if not config.model.lower().startswith("gpt-5"):
            create_kwargs["temperature"] = config.temperature
        
        resp = self._client.chat.completions.create(**create_kwargs)
        content = resp.choices[0].message.content or ""
        return content.strip()


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider implementation (supports direct models and agents)."""
    
    def __init__(self, region: str):
        try:
            import boto3
            from botocore.exceptions import ClientError, BotoCoreError
            self._boto3 = boto3
            self._ClientError = ClientError
            self._BotoCoreError = BotoCoreError
        except ImportError:
            raise RuntimeError(
                "boto3 package not available. Install dependencies: pip install boto3"
            )
        
        self._region = region
        self._runtime_client: Optional[Any] = None
        self._agent_client: Optional[Any] = None
    
    def _get_runtime_client(self) -> Any:
        """Get bedrock-runtime client."""
        if self._runtime_client is None:
            self._runtime_client = self._boto3.client("bedrock-runtime", region_name=self._region)
        return self._runtime_client
    
    def _get_agent_client(self) -> Any:
        """Get bedrock-agent-runtime client."""
        if self._agent_client is None:
            self._agent_client = self._boto3.client("bedrock-agent-runtime", region_name=self._region)
        return self._agent_client
    
    def get_client(self) -> Any:
        """Get the appropriate client based on usage."""
        return self._get_runtime_client()
    
    def _invoke_model(
        self,
        model_id: str,
        system_prompt: str,
        user_messages: list[str],
        temperature: float,
    ) -> str:
        """Invoke Bedrock model directly."""
        import json
        import base64
        
        client = self._get_runtime_client()
        is_claude = "anthropic.claude" in model_id.lower() or "claude" in model_id.lower()
        
        if is_claude:
            # Anthropic Claude models use the messages API
            combined_user_content = "\n\n".join(user_messages)
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": combined_user_content,
                    }
                ],
            }
        else:
            # Other models (Titan, Llama, etc.)
            combined_text = f"{system_prompt}\n\n" + "\n\n".join(user_messages)
            if "amazon.titan" in model_id.lower():
                request_body = {
                    "inputText": combined_text,
                    "textGenerationConfig": {
                        "maxTokenCount": 8192,
                        "temperature": temperature,
                    },
                }
            else:
                request_body = {
                    "prompt": combined_text,
                    "max_tokens": 8192,
                    "temperature": temperature,
                }
        
        try:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                accept="application/json",
                contentType="application/json",
            )
            
            response_body = json.loads(response["body"].read())
            
            if is_claude:
                if "content" in response_body and len(response_body["content"]) > 0:
                    text_parts = []
                    for block in response_body["content"]:
                        if block.get("type") == "text" and "text" in block:
                            text_parts.append(block["text"])
                    return "\n".join(text_parts) if text_parts else ""
                else:
                    raise RuntimeError("Unexpected Claude response format: no content found")
            else:
                if "results" in response_body and len(response_body["results"]) > 0:
                    return response_body["results"][0].get("outputText", "")
                elif "completion" in response_body:
                    return response_body["completion"]
                elif "generation" in response_body:
                    return response_body["generation"]
                else:
                    raise RuntimeError(
                        f"Unexpected response format for model {model_id}. "
                        f"Response keys: {list(response_body.keys())}"
                    )
        except self._ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise RuntimeError(
                f"Bedrock API error ({error_code}): {error_msg}. "
                f"Model: {model_id}, Region: {self._region}"
            )
    
    def _invoke_agent(
        self,
        agent_id: str,
        agent_alias_id: str,
        system_prompt: str,
        user_messages: list[str],
    ) -> str:
        """Invoke Bedrock Agent."""
        import json
        import uuid
        import base64
        
        client = self._get_agent_client()
        session_id = uuid.uuid4().hex
        
        # Combine system prompt and user messages
        combined_prompt = f"{system_prompt}\n\n" + "\n\n".join(user_messages)
        
        try:
            response = client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=combined_prompt,
                enableTrace=False,
            )
            
            # Stream response chunks from the completion event stream
            parts = []
            for event in response.get("completion", []):
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        try:
                            decoded_bytes = base64.b64decode(chunk["bytes"])
                            parts.append(decoded_bytes.decode("utf-8"))
                        except (UnicodeDecodeError, base64.binascii.Error):
                            try:
                                decoded_bytes = base64.b64decode(chunk["bytes"])
                                parts.append(decoded_bytes.decode("utf-8", errors="replace"))
                            except Exception:
                                pass
                    elif "text" in chunk:
                        parts.append(chunk["text"])
            
            return "".join(parts) if parts else ""
        except self._ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise RuntimeError(
                f"Bedrock Agent API error ({error_code}): {error_msg}. "
                f"Agent: {agent_id}, Alias: {agent_alias_id}, Region: {self._region}. "
                f"Ensure the agent alias is deployed and active, and you have bedrock:InvokeAgent permission."
            )
    
    def generate_text(
        self,
        system_prompt: str,
        user_messages: list[str],
        config: LLMConfig,
        ballpark: Optional[str] = None,
    ) -> str:
        # Use agent if provided, otherwise use direct model invocation
        if config.agent_id and config.agent_alias_id:
            return self._invoke_agent(
                agent_id=config.agent_id,
                agent_alias_id=config.agent_alias_id,
                system_prompt=system_prompt,
                user_messages=user_messages,
            )
        else:
            if not config.model:
                raise ValueError("Bedrock provider requires either model or agent_id/agent_alias_id to be set")
            return self._invoke_model(
                model_id=config.model,
                system_prompt=system_prompt,
                user_messages=user_messages,
                temperature=config.temperature,
            )

