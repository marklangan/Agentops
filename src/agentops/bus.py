"""In-process message bus.

Each registered agent gets its own asyncio.Queue as an inbox. The bus keeps a
full history so a run can be traced end to end. The public interface
(register / send / trace) is deliberately small so it can later be swapped for
a Redis or NATS backed bus without touching the agents.
"""

from __future__ import annotations

import asyncio
import logging

from agentops.messages import Message

logger = logging.getLogger(__name__)


class MessageBus:
    def __init__(self) -> None:
        self._inboxes: dict[str, asyncio.Queue[Message]] = {}
        self.history: list[Message] = []

    def register(self, name: str) -> asyncio.Queue[Message]:
        if name in self._inboxes:
            raise ValueError(f"Agent '{name}' is already registered")
        inbox: asyncio.Queue[Message] = asyncio.Queue()
        self._inboxes[name] = inbox
        return inbox

    @property
    def agents(self) -> list[str]:
        return list(self._inboxes)

    async def send(self, message: Message) -> None:
        if message.recipient not in self._inboxes:
            raise KeyError(f"Unknown recipient '{message.recipient}'")
        self.history.append(message)
        logger.info(
            "%s -> %s [%s] %s",
            message.sender,
            message.recipient,
            message.type.value,
            message.correlation_id,
        )
        await self._inboxes[message.recipient].put(message)

    def trace(self, correlation_id: str | None = None) -> list[Message]:
        if correlation_id is None:
            return list(self.history)
        return [m for m in self.history if m.correlation_id == correlation_id]
