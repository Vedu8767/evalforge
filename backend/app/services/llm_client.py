"""
Unified LLM Client — supports OpenAI, Anthropic, Ollama, and Groq
Compatible with openai SDK v2.x (installed on Render)
"""
import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx
from app.models.orm import ModelEndpoint
from app.services.auth import decrypt_api_key


@dataclass
class LLMResponse:
    content: str
    latency_ms: int
    tokens_used: int
    model: str
    error: Optional[str] = None


async def call_llm(
    prompt: str,
    endpoint: ModelEndpoint,
    system_override: Optional[str] = None,
) -> LLMResponse:
    try:
        api_key = decrypt_api_key(endpoint.api_key_encrypted)
    except Exception:
        api_key = "dummy"

    system_prompt = system_override or endpoint.system_prompt or "You are a helpful assistant."
    start = time.monotonic()

    try:
        if endpoint.provider == "anthropic":
            return await _call_anthropic(prompt, system_prompt, endpoint, api_key, start)
        elif endpoint.provider == "ollama" or (endpoint.base_url and "11434" in endpoint.base_url):
            return await _call_ollama(prompt, system_prompt, endpoint, start)
        else:
            # OpenAI / Groq / any OpenAI-compatible API
            return await _call_openai_compat(prompt, system_prompt, endpoint, api_key, start)
    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        return LLMResponse(content="", latency_ms=latency_ms, tokens_used=0,
                           model=endpoint.model_name, error=str(e))


async def _call_openai_compat(prompt, system_prompt, endpoint, api_key, start) -> LLMResponse:
    """
    Calls any OpenAI-compatible API including Groq.
    Uses httpx directly to avoid openai SDK version compatibility issues.
    """
    base_url = endpoint.base_url.rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": endpoint.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": endpoint.temperature,
        "max_tokens": endpoint.max_tokens,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    latency_ms = int((time.monotonic() - start) * 1000)

    # Parse response — same format for OpenAI, Groq, Together, etc.
    choices = data.get("choices", [])
    content = ""
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content", "") or ""

    usage = data.get("usage", {})
    tokens = usage.get("total_tokens", 0) or (
        usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    )

    return LLMResponse(
        content=content,
        latency_ms=latency_ms,
        tokens_used=tokens,
        model=data.get("model", endpoint.model_name),
    )


async def _call_ollama(prompt, system_prompt, endpoint, start) -> LLMResponse:
    """Call Ollama via its native API — no API key needed."""
    base = endpoint.base_url.rstrip("/").replace("/v1", "")
    url = f"{base}/api/chat"

    payload = {
        "model": endpoint.model_name,
        "stream": False,
        "options": {
            "temperature": endpoint.temperature,
            "num_predict": endpoint.max_tokens,
        },
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    latency_ms = int((time.monotonic() - start) * 1000)
    content = data.get("message", {}).get("content", "")
    tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

    return LLMResponse(
        content=content,
        latency_ms=latency_ms,
        tokens_used=tokens,
        model=endpoint.model_name,
    )


async def _call_anthropic(prompt, system_prompt, endpoint, api_key, start) -> LLMResponse:
    """Call Anthropic Claude API."""
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=endpoint.model_name,
        max_tokens=endpoint.max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    latency_ms = int((time.monotonic() - start) * 1000)
    return LLMResponse(
        content=response.content[0].text if response.content else "",
        latency_ms=latency_ms,
        tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        model=response.model,
    )


async def call_llm_n_times(prompt, endpoint, n=3) -> list[LLMResponse]:
    """Run same prompt N times concurrently — for self-consistency checks."""
    return await asyncio.gather(*[call_llm(prompt, endpoint) for _ in range(n)])
