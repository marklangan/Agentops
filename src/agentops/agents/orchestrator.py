"""The orchestrator: plans a task, dispatches steps to specialists, then synthesises.

Flow for one run:
  1. PLAN      ask the LLM to split the task into steps, each assigned to an agent
  2. DISPATCH  send each step as a TASK message and await the matching reply
  3. SYNTHESISE combine the step results into one final answer

Steps currently run in order, and each step sees earlier results as context.
Milestone 3 in BRIEF.md turns this into a dependency graph run in parallel.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from agentops.agents.base import Agent
from agentops.bus import MessageBus
from agentops.llm import LLM
from agentops.messages import Message, MessageType

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """You are the orchestrator (planner) of a team of DevOps agents.
Break the user's task into a short list of steps (1 to 6). Assign each step to exactly
one agent from this list:

{agents}

Respond with ONLY a JSON object, no prose and no code fences, in this shape:
{{"steps": [{{"agent": "<agent name>", "instruction": "<what that agent should do>"}}]}}
"""

SYNTH_PROMPT = """You are the orchestrator of a team of DevOps agents. You have the
original task and each agent's output. Write the final answer for the user: merge
overlapping points, resolve conflicts, and finish with a short prioritised action list."""


class PlanError(ValueError):
    pass


@dataclass
class Step:
    agent: str
    instruction: str
    result: str | None = None
    ok: bool | None = None


@dataclass
class RunResult:
    task: str
    steps: list[Step] = field(default_factory=list)
    answer: str = ""


class Orchestrator:
    name = "orchestrator"

    def __init__(
        self,
        bus: MessageBus,
        llm: LLM,
        agents: list[Agent],
        step_timeout: float = 180.0,
    ) -> None:
        self.bus = bus
        self.llm = llm
        self.agents = {a.name: a for a in agents}
        self.step_timeout = step_timeout
        self.inbox = bus.register(self.name)
        self._pending: dict[str, asyncio.Future[Message]] = {}
        self._listener: asyncio.Task | None = None

    # lifecycle -------------------------------------------------------------

    async def start(self) -> None:
        for agent in self.agents.values():
            await agent.start()
        self._listener = asyncio.create_task(self._listen(), name="orchestrator:listen")

    async def stop(self) -> None:
        if self._listener:
            self._listener.cancel()
        for agent in self.agents.values():
            await agent.stop()

    async def _listen(self) -> None:
        """Route replies back to whoever is waiting on that correlation id."""
        while True:
            message = await self.inbox.get()
            future = self._pending.pop(message.correlation_id, None)
            if future and not future.done():
                future.set_result(message)
            else:
                logger.warning("Unexpected message %s from %s", message.id, message.sender)

    # public API ------------------------------------------------------------

    async def run(self, task: str) -> RunResult:
        result = RunResult(task=task, steps=await self.plan(task))

        for i, step in enumerate(result.steps, start=1):
            context = self._context(result.steps[: i - 1])
            prompt = f"Overall task:\n{task}\n\n{context}Your step:\n{step.instruction}"
            reply = await self.ask(step.agent, prompt)
            step.ok = reply.type == MessageType.RESULT
            step.result = reply.content

        result.answer = await self.synthesise(result)
        return result

    async def plan(self, task: str) -> list[Step]:
        roster = "\n".join(f"- {a.name}: {a.description}" for a in self.agents.values())
        raw = await self.llm.complete(PLANNER_PROMPT.format(agents=roster), task)
        return self._parse_plan(raw)

    async def ask(self, agent: str, content: str) -> Message:
        message = Message(
            sender=self.name, recipient=agent, type=MessageType.TASK, content=content
        )
        future: asyncio.Future[Message] = asyncio.get_running_loop().create_future()
        self._pending[message.correlation_id] = future
        await self.bus.send(message)
        try:
            return await asyncio.wait_for(future, timeout=self.step_timeout)
        except TimeoutError:
            self._pending.pop(message.correlation_id, None)
            return message.reply(f"Timed out after {self.step_timeout}s", MessageType.ERROR)

    async def synthesise(self, result: RunResult) -> str:
        body = f"Task:\n{result.task}\n\n" + self._context(result.steps)
        return await self.llm.complete(SYNTH_PROMPT, body)

    # helpers ---------------------------------------------------------------

    def _parse_plan(self, raw: str) -> list[Step]:
        text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PlanError(f"Planner did not return valid JSON: {raw[:200]}") from exc

        steps = []
        for item in data.get("steps", []):
            agent = item.get("agent")
            if agent not in self.agents:
                raise PlanError(f"Plan uses unknown agent '{agent}'")
            steps.append(Step(agent=agent, instruction=item.get("instruction", "")))
        if not steps:
            raise PlanError("Planner returned no steps")
        return steps

    @staticmethod
    def _context(steps: list[Step]) -> str:
        if not steps:
            return ""
        parts = []
        for s in steps:
            status = "ok" if s.ok else "failed"
            parts.append(f"[{s.agent} | {status}] {s.instruction}\n{s.result}")
        return "Results so far:\n" + "\n\n".join(parts) + "\n\n"
