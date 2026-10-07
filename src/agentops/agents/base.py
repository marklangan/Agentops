"""Base class for worker agents.

A worker agent sits in a loop reading its inbox. For every TASK it receives it
calls handle() and sends the reply back over the bus. Subclasses usually only
need to set name, description and system_prompt.
"""

from __future__ import annotations

import asyncio
import logging

from agentops.bus import MessageBus
from agentops.llm import LLM
from agentops.messages import Message, MessageType

logger = logging.getLogger(__name__)


class Agent:
    name: str = "agent"
    description: str = "A generic agent."
    system_prompt: str = "You are a helpful assistant."

    def __init__(self, bus: MessageBus, llm: LLM) -> None:
        self.bus = bus
        self.llm = llm
        self.inbox = bus.register(self.name)
        self._loop_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._loop_task = asyncio.create_task(self._run(), name=f"agent:{self.name}")

    async def stop(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while True:
            message = await self.inbox.get()
            try:
                reply = await self.handle(message)
            except Exception as exc:  # report failures instead of crashing the loop
                logger.exception("%s failed on %s", self.name, message.id)
                reply = message.reply(f"{type(exc).__name__}: {exc}", MessageType.ERROR)
            if reply is not None:
                await self.bus.send(reply)
            self.inbox.task_done()

    async def handle(self, message: Message) -> Message | None:
        output = await self.llm.complete(self.system_prompt, message.content)
        return message.reply(output)
