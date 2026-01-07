"""
LLM Integration Client

Provides unified interface for LLM interactions supporting:
- Local LLM via LM Studio (OpenAI-compatible API)
- OpenAI API
- Anthropic API

Used by LangGraph agents for SEO analysis, content generation, and planning.
"""

import json
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
from enum import Enum
from dataclasses import dataclass
import httpx
from pydantic import BaseModel

from app.config import settings


class LLMProvider(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Message(BaseModel):
    role: str  # system, user, assistant
    content: str


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class LLMStreamChunk(BaseModel):
    content: str
    is_final: bool = False


@dataclass
class LLMConfig:
    provider: LLMProvider
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 120.0


class LLMClient:
    """Unified LLM client supporting multiple providers."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        if config is None:
            config = LLMConfig(
                provider=LLMProvider(settings.LLM_PROVIDER),
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL,
            )
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers=self._get_headers(),
            )
        return self._client
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        
        if self.config.provider == LLMProvider.OPENAI:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.provider == LLMProvider.ANTHROPIC:
            headers["x-api-key"] = self.config.api_key
            headers["anthropic-version"] = "2023-06-01"
        elif self.config.provider == LLMProvider.LOCAL:
            if self.config.api_key and self.config.api_key != "not-needed":
                headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        return headers
    
    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Send chat completion request."""
        
        if self.config.provider == LLMProvider.ANTHROPIC:
            return await self._chat_anthropic(messages, temperature, max_tokens)
        else:
            return await self._chat_openai_compatible(
                messages, temperature, max_tokens, json_mode
            )
    
    async def _chat_openai_compatible(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Chat using OpenAI-compatible API (works with LM Studio and OpenAI)."""
        
        client = await self._get_client()
        url = f"{self.config.base_url}/chat/completions"
        
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.config.model),
            usage=data.get("usage"),
            finish_reason=choice.get("finish_reason"),
        )
    
    async def _chat_anthropic(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Chat using Anthropic API."""
        
        client = await self._get_client()
        url = f"{self.config.base_url}/messages"
        
        # Extract system message if present
        system_message = None
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_message = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})
        
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": chat_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        if system_message:
            payload["system"] = system_message
        
        if temperature is not None:
            payload["temperature"] = temperature
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        content = data["content"][0]["text"] if data.get("content") else ""
        return LLMResponse(
            content=content,
            model=data.get("model", self.config.model),
            usage={
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            finish_reason=data.get("stop_reason"),
        )
    
    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream chat completion response."""
        
        if self.config.provider == LLMProvider.ANTHROPIC:
            async for chunk in self._stream_anthropic(messages, temperature, max_tokens):
                yield chunk
        else:
            async for chunk in self._stream_openai_compatible(
                messages, temperature, max_tokens
            ):
                yield chunk
    
    async def _stream_openai_compatible(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream using OpenAI-compatible API."""
        
        client = await self._get_client()
        url = f"{self.config.base_url}/chat/completions"
        
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield LLMStreamChunk(content="", is_final=True)
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield LLMStreamChunk(content=content)
                    except json.JSONDecodeError:
                        continue
    
    async def _stream_anthropic(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream using Anthropic API."""
        
        client = await self._get_client()
        url = f"{self.config.base_url}/messages"
        
        system_message = None
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_message = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})
        
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": chat_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        
        if system_message:
            payload["system"] = system_message
        
        if temperature is not None:
            payload["temperature"] = temperature
        
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    try:
                        event = json.loads(data)
                        if event["type"] == "content_block_delta":
                            text = event.get("delta", {}).get("text", "")
                            if text:
                                yield LLMStreamChunk(content=text)
                        elif event["type"] == "message_stop":
                            yield LLMStreamChunk(content="", is_final=True)
                    except json.JSONDecodeError:
                        continue
    
    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON output following a schema."""
        
        schema_str = json.dumps(schema, indent=2)
        
        if system_prompt is None:
            system_prompt = "You are a helpful assistant that outputs valid JSON."
        
        full_prompt = f"""{prompt}

Output your response as valid JSON following this schema:
```json
{schema_str}
```

Respond with ONLY valid JSON, no other text."""
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=full_prompt),
        ]
        
        # Use JSON mode if available (OpenAI)
        json_mode = self.config.provider in [LLMProvider.OPENAI, LLMProvider.LOCAL]
        
        response = await self.chat(messages, json_mode=json_mode, temperature=0.3)
        
        # Parse JSON from response
        content = response.content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        return json.loads(content.strip())
    
    async def health_check(self) -> bool:
        """Check if LLM service is available."""
        try:
            client = await self._get_client()
            
            if self.config.provider == LLMProvider.ANTHROPIC:
                # Anthropic doesn't have a models endpoint, so do minimal request
                return True
            else:
                # OpenAI-compatible models endpoint
                url = f"{self.config.base_url}/models"
                response = await client.get(url, timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions for common SEO tasks

async def analyze_seo_issues(
    client: LLMClient,
    url: str,
    issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Analyze SEO issues and provide recommendations."""
    
    issues_text = json.dumps(issues, indent=2)
    
    prompt = f"""Analyze the following SEO issues found on {url} and provide:
1. A priority ranking of issues to fix
2. Specific recommendations for each issue
3. Estimated impact on SEO performance

Issues found:
{issues_text}
"""
    
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "priority_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "severity": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "estimated_impact": {"type": "string"},
                    },
                },
            },
            "quick_wins": {"type": "array", "items": {"type": "string"}},
            "overall_score": {"type": "number"},
        },
    }
    
    return await client.generate_json(
        prompt,
        schema,
        system_prompt="You are an expert SEO analyst providing actionable recommendations.",
    )


async def generate_content_brief(
    client: LLMClient,
    keyword: str,
    competitors: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a content brief for a target keyword."""
    
    competitors_text = json.dumps(competitors, indent=2)
    
    prompt = f"""Create a comprehensive content brief for targeting the keyword: "{keyword}"

Competitor analysis:
{competitors_text}

The brief should include content structure, key points to cover, and differentiation strategies.
"""
    
    schema = {
        "type": "object",
        "properties": {
            "title_suggestions": {"type": "array", "items": {"type": "string"}},
            "meta_description": {"type": "string"},
            "target_word_count": {"type": "number"},
            "content_outline": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "key_points": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "keywords_to_include": {"type": "array", "items": {"type": "string"}},
            "internal_linking_suggestions": {"type": "array", "items": {"type": "string"}},
            "differentiation_angle": {"type": "string"},
        },
    }
    
    return await client.generate_json(
        prompt,
        schema,
        system_prompt="You are an expert content strategist specializing in SEO-optimized content.",
    )


async def cluster_keywords(
    client: LLMClient,
    keywords: List[str],
) -> Dict[str, Any]:
    """Cluster keywords by search intent and topic."""
    
    keywords_text = "\n".join(f"- {kw}" for kw in keywords)
    
    prompt = f"""Analyze and cluster the following keywords by search intent and topic similarity:

{keywords_text}

Group them into logical clusters for content planning.
"""
    
    schema = {
        "type": "object",
        "properties": {
            "clusters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "intent": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "recommended_content_type": {"type": "string"},
                    },
                },
            },
        },
    }
    
    return await client.generate_json(
        prompt,
        schema,
        system_prompt="You are an expert in keyword research and search intent analysis.",
    )


# Default client instance
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the default LLM client."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
