from __future__ import annotations

import abc
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str
    model: Optional[str] = None
    agent_id: Optional[str] = None
    agent_alias_id: Optional[str] = None
    temperature: float = 0.2


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate_text(
        self,
        system_prompt: str,
        user_messages: list[str],
        config: LLMConfig,
        ballpark: Optional[str] = None,
    ) -> str:
        pass
    
    @abc.abstractmethod
    def get_client(self) -> Any:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self._OpenAI = OpenAI
        except ImportError:
            raise RuntimeError("openai package not available")
    
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
            raise ValueError("OpenAI provider requires model")
        
        combined_user_content = "\n\n".join(user_messages)
        
        create_kwargs = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_user_content},
            ],
        }
        
        if not config.model.lower().startswith("gpt-5"):
            create_kwargs["temperature"] = config.temperature
        
        print(f"OpenAI: Calling model {config.model} with {len(system_prompt)} char system prompt and {len(combined_user_content)} char user content")
        
        resp = self._client.chat.completions.create(**create_kwargs)
        content = resp.choices[0].message.content or ""
        
        print(f"OpenAI: Received response with {len(content)} chars, finish_reason: {resp.choices[0].finish_reason}")
        
        if not content or len(content.strip()) < 50:
            print(f"OpenAI: WARNING - Response is too short or empty. Raw content: {repr(content[:200])}")
        
        return content.strip()


class BedrockProvider(LLMProvider):
    def __init__(self, region: str):
        try:
            import boto3
            import os
            from botocore.exceptions import ClientError, BotoCoreError
            self._boto3 = boto3
            self._ClientError = ClientError
            self._BotoCoreError = BotoCoreError
            self._os = os
        except ImportError:
            raise RuntimeError("boto3 package not available")
        
        self._region = region
        self._runtime_client: Optional[Any] = None
        self._agent_client: Optional[Any] = None
    
    def _get_session(self):
        """Get a boto3 session with profile support."""
        profile = self._os.getenv("AWS_PROFILE")
        if profile:
            return self._boto3.Session(profile_name=profile)
        return self._boto3.Session()
    
    def _get_runtime_client(self) -> Any:
        if self._runtime_client is None:
            session = self._get_session()
            self._runtime_client = session.client("bedrock-runtime", region_name=self._region)
        return self._runtime_client
    
    def _get_agent_client(self) -> Any:
        if self._agent_client is None:
            session = self._get_session()
            self._agent_client = session.client("bedrock-agent-runtime", region_name=self._region)
        return self._agent_client
    
    def get_client(self) -> Any:
        return self._get_runtime_client()
    
    def _invoke_model(
        self,
        model_id: str,
        system_prompt: str,
        user_messages: list[str],
        temperature: float,
    ) -> str:
        import json
        
        client = self._get_runtime_client()
        is_claude = "anthropic.claude" in model_id.lower() or "claude" in model_id.lower()
        
        if is_claude:
            combined_user_content = "\n\n".join(user_messages)
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": combined_user_content}],
            }
        else:
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
        
        combined_content = "\n\n".join(user_messages) if is_claude else f"{system_prompt}\n\n" + "\n\n".join(user_messages)
        print(f"Bedrock: Invoking model {model_id} with {len(combined_content)} char input")
        
        try:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                accept="application/json",
                contentType="application/json",
            )
            
            response_body = json.loads(response["body"].read())
            
            result_text = ""
            if is_claude:
                if "content" in response_body and len(response_body["content"]) > 0:
                    text_parts = []
                    for block in response_body["content"]:
                        if block.get("type") == "text" and "text" in block:
                            text_parts.append(block["text"])
                    result_text = "\n".join(text_parts) if text_parts else ""
                    print(f"Bedrock Claude: Received {len(result_text)} chars, stop_reason: {response_body.get('stop_reason', 'unknown')}")
                else:
                    raise RuntimeError("Unexpected Claude response format")
            else:
                if "results" in response_body and len(response_body["results"]) > 0:
                    result_text = response_body["results"][0].get("outputText", "")
                elif "completion" in response_body:
                    result_text = response_body["completion"]
                elif "generation" in response_body:
                    result_text = response_body["generation"]
                else:
                    raise RuntimeError(f"Unexpected response format for model {model_id}")
                print(f"Bedrock {model_id}: Received {len(result_text)} chars")
            
            if not result_text or len(result_text.strip()) < 50:
                print(f"Bedrock: WARNING - Response is too short or empty. Raw content: {repr(result_text[:200])}")
            
            return result_text
        except self._ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise RuntimeError(f"Bedrock API error ({error_code}): {error_msg}")
    
    def _invoke_agent(
        self,
        agent_id: str,
        agent_alias_id: str,
        system_prompt: str,
        user_messages: list[str],
    ) -> str:
        import json
        import uuid
        import base64
        
        client = self._get_agent_client()
        session_id = uuid.uuid4().hex
        combined_prompt = f"{system_prompt}\n\n" + "\n\n".join(user_messages)
        
        print(f"Bedrock Agent: Invoking agent {agent_id} with {len(combined_prompt)} char input")
        
        try:
            response = client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=combined_prompt,
                enableTrace=False,
            )
            
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
            
            result_text = "".join(parts) if parts else ""
            print(f"Bedrock Agent: Received {len(result_text)} chars from {len(parts)} chunks")
            
            if not result_text or len(result_text.strip()) < 50:
                print(f"Bedrock Agent: WARNING - Response is too short or empty. Raw content: {repr(result_text[:200])}")
            
            return result_text
        except self._ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise RuntimeError(f"Bedrock Agent API error ({error_code}): {error_msg}")
    
    def generate_text(
        self,
        system_prompt: str,
        user_messages: list[str],
        config: LLMConfig,
        ballpark: Optional[str] = None,
    ) -> str:
        if config.agent_id and config.agent_alias_id:
            return self._invoke_agent(
                agent_id=config.agent_id,
                agent_alias_id=config.agent_alias_id,
                system_prompt=system_prompt,
                user_messages=user_messages,
            )
        else:
            if not config.model:
                raise ValueError("Bedrock provider requires model or agent_id/agent_alias_id")
            return self._invoke_model(
                model_id=config.model,
                system_prompt=system_prompt,
                user_messages=user_messages,
                temperature=config.temperature,
            )

