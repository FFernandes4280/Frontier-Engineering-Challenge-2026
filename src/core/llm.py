"""Unified LLM interface with token, cost and latency tracking."""

import os
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import litellm


class LLMResponse(BaseModel):
    """Structured response from LLM call including tracking metadata."""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    raw_response: Optional[Any] = Field(default=None, exclude=True)


class LLMClient:
    """Robust LLM client supporting OpenAI, Anthropic, Gemini, etc."""

    def __init__(self, default_model: Optional[str] = None):
        self.default_model = default_model or os.getenv("DEFAULT_MODEL", "gpt-4o")
        litellm.drop_params = True

    async def acomplete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Any] = None,
        **kwargs
    ) -> LLMResponse:
        """Async completion with precise token, cost and latency calculation."""
        selected_model = model or self.default_model
        start_time = time.perf_counter()

        params: Dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }

        if tools:
            params["tools"] = tools
        if response_format:
            params["response_format"] = response_format

        try:
            response = await litellm.acompletion(**params)
            latency_ms = (time.perf_counter() - start_time) * 1000

            content = response.choices[0].message.content or ""
            tool_calls = None
            if hasattr(response.choices[0].message, "tool_calls") and response.choices[0].message.tool_calls:
                tool_calls = [tc.model_dump() if hasattr(tc, "model_dump") else dict(tc) for tc in response.choices[0].message.tool_calls]

            usage = getattr(response, "usage", None)
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else prompt_tokens + completion_tokens

            # Calculate cost via LiteLLM cost tracker
            try:
                cost_usd = litellm.completion_cost(completion_response=response)
            except Exception:
                cost_usd = 0.0

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                model=selected_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                raw_response=response
            )

        except Exception as e:
            fallback_model = os.getenv("FALLBACK_MODEL")
            if fallback_model and fallback_model != selected_model:
                params["model"] = fallback_model
                response = await litellm.acompletion(**params)
                latency_ms = (time.perf_counter() - start_time) * 1000
                content = response.choices[0].message.content or ""
                return LLMResponse(
                    content=content,
                    model=fallback_model,
                    latency_ms=latency_ms,
                    raw_response=response
                )
            raise e
