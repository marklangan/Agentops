import asyncio
import json

import pytest

from agentops.agents.orchestrator import PlanError
from agentops.llm import FakeLLM
from agentops.messages import MessageType
from agentops.system import build_system


def responder(system: str, prompt: str) -> str:
    if "orchestrator (planner)" in system:
        return json.dumps({"steps": [
            {"agent": "kubernetes", "instruction": "review manifest"},
            {"agent": "security", "instruction": "security review"},
        ]})
    if "orchestrator of a team" in system:
        return "final answer"
    return "agent output"


def test_full_run_plans_dispatches_and_synthesises():
    async def scenario():
        orch = build_system(FakeLLM(responder))
        await orch.start()
        try:
            result = await orch.run("Review my deployment")
        finally:
            await orch.stop()

        assert [s.agent for s in result.steps] == ["kubernetes", "security"]
        assert all(s.ok for s in result.steps)
        assert result.answer == "final answer"
        # 2 tasks out, 2 results back
        types = [m.type for m in orch.bus.history]
        assert types.count(MessageType.TASK) == 2
        assert types.count(MessageType.RESULT) == 2

    asyncio.run(scenario())


def test_second_step_sees_first_step_result():
    llm = FakeLLM(responder)

    async def scenario():
        orch = build_system(llm)
        await orch.start()
        try:
            await orch.run("task")
        finally:
            await orch.stop()

    asyncio.run(scenario())
    security_prompt = next(p for s, p in llm.calls if "security agent" in s)
    assert "agent output" in security_prompt


def test_agent_failure_becomes_error_message():
    def boom(system, prompt):
        if "kubernetes agent" in system:
            raise RuntimeError("model down")
        return responder(system, prompt)

    async def scenario():
        orch = build_system(FakeLLM(boom))
        await orch.start()
        try:
            result = await orch.run("task")
        finally:
            await orch.stop()
        assert result.steps[0].ok is False
        assert "model down" in result.steps[0].result

    asyncio.run(scenario())


def test_plan_with_unknown_agent_is_rejected():
    orch = build_system(FakeLLM())
    with pytest.raises(PlanError):
        orch._parse_plan('{"steps": [{"agent": "chef", "instruction": "cook"}]}')


def test_plan_tolerates_code_fences():
    orch = build_system(FakeLLM())
    steps = orch._parse_plan('```json\n{"steps": [{"agent": "ci", "instruction": "x"}]}\n```')
    assert steps[0].agent == "ci"
