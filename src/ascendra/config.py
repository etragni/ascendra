"""ascendra.yaml: a shared `llm:` section plus one section per target (`kubernetes:`, `linux:`...)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class LLMConfig(BaseModel):
    provider: str = "anthropic"  # anthropic | openai (any OpenAI-compatible endpoint: vLLM, Ollama, ...)
    model: str | None = None
    base_url: str | None = None


class Config(BaseModel):
    model_config = ConfigDict(extra="allow")

    llm: LLMConfig = Field(default_factory=LLMConfig)

    def section(self, target: str) -> dict[str, Any]:
        return (self.model_extra or {}).get(target) or {}

    @classmethod
    def load(cls, path: Path | None) -> Config:
        if path is None:
            return cls()
        return cls.model_validate(yaml.safe_load(path.read_text()) or {})
