"""Unified LLM interface with strict API key validation and real token/cost tracking."""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import litellm
from dotenv import load_dotenv

load_dotenv()

# Suppress internal LiteLLM debug noise
litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.ERROR)


class MissingAPIKeyError(ValueError):
    """Raised when no valid LLM API key is configured."""
    pass


def validate_api_keys() -> str:
    """Validates that at least one real API key is configured."""
    for key_var, provider in [
        ("GEMINI_API_KEY", "Google Gemini"),
        ("OPENAI_API_KEY", "OpenAI"),
        ("ANTHROPIC_API_KEY", "Anthropic")
    ]:
        val = os.getenv(key_var)
        if val and not val.startswith("your_") and not val.startswith("optional_") and len(val.strip()) > 10:
            return key_var
    raise MissingAPIKeyError(
        "❌ [CRITICAL CONFIGURATION ERROR] No valid API Key found in .env!\n"
        "To run live vetting and benchmarks, you must configure a real API key.\n"
        "👉 Get a free Gemini API Key at: https://aistudio.google.com/app/apikey\n"
        "Then set GEMINI_API_KEY=AIzaSy... inside your .env file."
    )


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
        self.default_model = default_model or os.getenv("DEFAULT_MODEL", "gemini/gemini-1.5-flash")
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
        """Execute async completion strictly using real LLM API with cost and token tracking."""
        validate_api_keys()

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
