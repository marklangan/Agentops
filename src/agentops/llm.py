"""LLM clients.

Agents depend on the small LLM protocol rather than the Anthropic SDK directly,
so tests can run offline with FakeLLM.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Protocol

DEFAULT_MODEL = "claude-sonnet-5-5"


class LLM(Protocol):
    async def complete(self, system: str, prompt: str) -> str: ...


class ClaudeLLM:
    def __init__(self, model: str | None = None, max_tokens: int = 2048) -> None:
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from the environment
        self.model = model or os.getenv("AGENTOPS_MODEL", DEFAULT_MODEL)
        self.max_tokens = max_tokens

    async def complete(self, system: str, prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class FakeLLM:
    """Deterministic stand-in for tests and offline demos."""

    def __init__(self, responder: Callable[[str, str], str] | None = None) -> None:
        self.responder = responder or (lambda system, prompt: "ok")
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        return self.responder(system, prompt)
