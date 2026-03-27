"""LLM provider interface for bounded, observable LLM interactions.

All LLM-dependent pipeline steps must go through this interface.
Prompts and responses are logged for auditability.
LLM steps are optional and replaceable via configuration.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    """Structured response from an LLM call."""
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers used in the pipeline.

    Implementations must:
    - Log prompt and response for each call
    - Be replaceable via configuration
    - Handle failures gracefully (return empty response, don't crash pipeline)
    """

    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.0) -> LLMResponse:
        """Send a prompt and return structured response."""
        ...

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        ...


class NullLLMProvider:
    """No-op LLM provider for when LLM extraction is disabled.

    Returns empty responses. Used as the default when
    extraction.llm.enabled is false in config.
    """

    @property
    def model_name(self) -> str:
        return "null"

    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.0) -> LLMResponse:
        logger.debug(
            "LLM call skipped (null provider): %s",
            json.dumps({"prompt_length": len(prompt), "system_length": len(system)}),
        )
        return LLMResponse(text="", model="null")
