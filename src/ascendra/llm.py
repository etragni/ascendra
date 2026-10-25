"""Minimal, provider-agnostic LLM client. Agents only ever ask for structured JSON.

Providers:
  anthropic : Claude via the Anthropic Messages API (ANTHROPIC_API_KEY)
  openai    : any OpenAI-compatible endpoint, e.g. vLLM or Ollama for fully on-prem / sovereign setups
              (ASCENDRA_LLM_BASE_URL, optional ASCENDRA_LLM_API_KEY)
"""
from __future__ import annotations

import json
import os
import re
from typing import Protocol

import httpx

from ascendra.config import LLMConfig

DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "llama3.1"}


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    name: str

    def complete_json(self, system: str, user: str) -> dict: ...


def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("model did not return a JSON object")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"invalid JSON from model: {e}") from e


class AnthropicLLM:
    def __init__(self, model: str, api_key: str, base_url: str | None = None) -> None:
        self.model, self.api_key = model, api_key
        self.base_url = (base_url or "https://api.anthropic.com").rstrip("/")
        self.name = f"anthropic:{model}"

    def complete_json(self, system: str, user: str) -> dict:
        resp = httpx.post(
            f"{self.base_url}/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": self.model, "max_tokens": 4096, "system": system,
                  "messages": [{"role": "user", "content": user}]},
            timeout=180,
        )
        if resp.status_code >= 400:
            raise LLMError(f"Anthropic API {resp.status_code}: {resp.text[:300]}")
        text = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        return extract_json(text)


class OpenAICompatibleLLM:
    def __init__(self, model: str, base_url: str, api_key: str | None = None) -> None:
        self.model, self.base_url, self.api_key = model, base_url.rstrip("/"), api_key
        self.name = f"openai-compatible:{model}"

    def complete_json(self, system: str, user: str) -> dict:
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={"model": self.model, "temperature": 0.1,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=300,
        )
        if resp.status_code >= 400:
            raise LLMError(f"LLM endpoint {resp.status_code}: {resp.text[:300]}")
        return extract_json(resp.json()["choices"][0]["message"]["content"])


def build_llm(cfg: LLMConfig) -> LLM | None:
    """Returns None when no LLM is configured; agents then fall back to deterministic heuristics."""
    provider = os.getenv("ASCENDRA_LLM_PROVIDER", cfg.provider)
    model = os.getenv("ASCENDRA_LLM_MODEL", cfg.model or DEFAULT_MODELS.get(provider, ""))
    base_url = os.getenv("ASCENDRA_LLM_BASE_URL", cfg.base_url or "")
    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        return AnthropicLLM(model, key, base_url or None) if key else None
    if provider == "openai":
        return OpenAICompatibleLLM(model, base_url, os.getenv("ASCENDRA_LLM_API_KEY")) if base_url else None
    raise LLMError(f"unknown LLM provider: {provider}")
