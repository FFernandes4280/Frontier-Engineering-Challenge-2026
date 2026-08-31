"""Unified LLM interface with multi-model fallback pool and accurate Groq Cloud cost accounting."""

import asyncio
import logging
import os
import time
from typing import Any

import litellm
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(".env")

# Suppress internal LiteLLM debug noise
litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

# Published Groq Cloud token pricing ($ per token)
GROQ_MODEL_PRICING: dict[str, dict[str, float]] = {
    "groq/llama-3.3-70b-versatile": {"input": 0.00000059, "output": 0.00000079},
    "groq/llama-3.1-8b-instant":    {"input": 0.00000005, "output": 0.00000008},
    "groq/openai/gpt-oss-120b":     {"input": 0.00000015, "output": 0.00000060},
    "groq/openai/gpt-oss-20b":      {"input": 0.000000075, "output": 0.00000030},
}


class MissingAPIKeyError(ValueError):
    """Raised when no valid LLM API key is configured."""


def validate_api_keys() -> str:
    """Validates that at least one real API key is configured in the environment."""
    for key_var, provider in [
        ("GROQ_API_KEY", "Groq Cloud"),
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
        "👉 Set GROQ_API_KEY=gsk_... or GEMINI_API_KEY=AIzaSy... inside your .env file."
    )


class LLMResponse(BaseModel):
    """Structured response from LLM call including tracking metadata."""
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    raw_response: Any | None = Field(default=None, exclude=True)


class LLMClient:
    """Robust LLM client with automatic rotation across candidate model pool and accurate cost calculation."""

    def __init__(self, default_model: str | None = None):
        self.default_model = default_model or os.getenv("DEFAULT_MODEL", "groq/openai/gpt-oss-20b")
        litellm.drop_params = True

    async def acomplete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
        response_format: Any | None = None,
        **kwargs
    ) -> LLMResponse:
        """Execute async completion rotating through fallback models without hanging."""
        validate_api_keys()

        requested_model = model or self.default_model
        candidate_models = [
            requested_model,
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/openai/gpt-oss-120b",
            "groq/openai/gpt-oss-20b"
        ]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        start_time = time.perf_counter()

        for current_model in candidate_models:
            params: dict[str, Any] = {
                "model": current_model,
                "messages": messages,
                "temperature": temperature,
                "num_retries": 0,
                "timeout": 12,
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

                # Calculate accurate cost based on Groq Cloud pricing
                rates = GROQ_MODEL_PRICING.get(current_model, {"input": 0.00000015, "output": 0.00000060})
                cost_usd = (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])

                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    model=current_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    raw_response=response
                )
            except RateLimitError as e:
                # Fast failover: if current model is rate-limited on Groq TPM, immediately try next candidate model
                continue
            except Exception as e:
                # Try next model on provider error
                continue

        raise Exception("All configured LLM providers failed to return a response.")
