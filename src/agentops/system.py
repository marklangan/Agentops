"""Wires the bus, LLM and agents together."""

from __future__ import annotations

from agentops.agents import SPECIALISTS, Orchestrator
from agentops.bus import MessageBus
from agentops.llm import LLM


def build_system(llm: LLM) -> Orchestrator:
    bus = MessageBus()
    agents = [cls(bus, llm) for cls in SPECIALISTS]
    return Orchestrator(bus, llm, agents)
