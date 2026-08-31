"""Unified LLM interface supporting both Groq Cloud and Google Gemini with automatic failover and exact cost accounting."""

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

# Published token pricing ($ per token) for Groq Cloud and Google Gemini
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Google Gemini Models (Low Cost / High Throughput)
    "gemini/gemini-flash-latest":      {"input": 0.00000010, "output": 0.00000040},
    "gemini/gemini-flash-lite-latest": {"input": 0.000000075, "output": 0.00000030},
    "gemini/gemini-3.6-flash":         {"input": 0.00000010, "output": 0.00000040},
    "gemini/gemini-3.5-flash-lite":    {"input": 0.000000075, "output": 0.00000030},
    "gemini/gemini-2.0-flash":         {"input": 0.00000010, "output": 0.00000040},
    "gemini/gemini-2.0-flash-lite":    {"input": 0.000000075, "output": 0.00000030},
    # Groq Cloud Models (Ultra Fast / Low Latency)
    "groq/llama-3.3-70b-versatile":    {"input": 0.00000059, "output": 0.00000079},
    "groq/llama-3.1-8b-instant":       {"input": 0.00000005, "output": 0.00000008},
    "groq/openai/gpt-oss-120b":        {"input": 0.00000059, "output": 0.00000079},
    "groq/openai/gpt-oss-20b":         {"input": 0.00000005, "output": 0.00000008},
}

GROQ_MODEL_PRICING = MODEL_PRICING


class MissingAPIKeyError(ValueError):
    """Raised when no valid LLM API key is configured."""


def validate_api_keys() -> str:
    """Validates that at least one real API key is configured in the environment."""
    for key_var, provider in [
        ("GEMINI_API_KEY", "Google Gemini"),
        ("GROQ_API_KEY", "Groq Cloud")
    ]:
        val = os.getenv(key_var)
        if val and not val.startswith("your_") and not val.startswith("optional_") and len(val.strip()) > 10:
            return key_var
    raise MissingAPIKeyError(
        "❌ [CRITICAL CONFIGURATION ERROR] No valid API Key found in .env!\n"
        "To run live vetting and benchmarks, configure GROQ_API_KEY or GEMINI_API_KEY in your .env file."
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
    """Robust, provider-agnostic LLM client supporting Groq Cloud and Google Gemini seamlessly."""

    def __init__(self, default_model: str | None = None):
        self.default_model = default_model or os.getenv("DEFAULT_MODEL", "gemini/gemini-flash-latest")
        litellm.drop_params = True

    def _build_candidate_models(self, requested_model: str) -> list[str]:
        """Build an ordered list of candidate models based on available API keys."""
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        has_gemini = len(gemini_key) > 10 and not gemini_key.startswith("your_")
        has_groq = len(groq_key) > 10 and not groq_key.startswith("your_")

        candidates = []

        # 1. Normalize and prioritize requested model
        req = requested_model.lower().strip()
        if "flash-lite" in req or "-20b" in req or "-8b" in req:
            # Agile / lightweight tier
            if has_gemini:
                candidates.extend(["gemini/gemini-flash-lite-latest", "gemini/gemini-3.5-flash-lite"])
            if has_groq:
                candidates.extend(["groq/openai/gpt-oss-20b", "groq/llama-3.1-8b-instant"])
        else:
            # Frontier / heavy tier (default)
            if has_gemini:
                candidates.extend(["gemini/gemini-flash-latest", "gemini/gemini-3.6-flash"])
            if has_groq:
                candidates.extend(["groq/openai/gpt-oss-120b", "groq/llama-3.3-70b-versatile"])

        # Fallback pool
        if has_gemini:
            candidates.extend(["gemini/gemini-flash-latest", "gemini/gemini-flash-lite-latest"])
        if has_groq:
            candidates.extend(["groq/openai/gpt-oss-120b", "groq/openai/gpt-oss-20b"])

        # Deduplicate preserving order
        return list(dict.fromkeys(candidates))

    async def acomplete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
        response_format: Any | None = None,
        **kwargs
    ) -> LLMResponse:
        """Execute async completion across Gemini / Groq candidate models with fast failover."""
        validate_api_keys()

        requested_model = model or self.default_model
        candidate_models = self._build_candidate_models(requested_model)

        start_time = time.perf_counter()

        for current_model in candidate_models:
            params: dict[str, Any] = {
                "model": current_model,
                "messages": messages,
                "temperature": temperature,
                "num_retries": 0,
                "timeout": 15,
                **kwargs
            }
            if current_model.startswith("gemini"):
                params["api_key"] = os.getenv("GEMINI_API_KEY")
            elif current_model.startswith("groq"):
                params["api_key"] = os.getenv("GROQ_API_KEY")

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

                # Calculate accurate cost based on model pricing
                rates = MODEL_PRICING.get(current_model, {"input": 0.00000010, "output": 0.00000040})
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
            except RateLimitError:
                continue
            except Exception:
                continue

        raise Exception("All configured LLM providers (Gemini/Groq) failed to return a response.")
