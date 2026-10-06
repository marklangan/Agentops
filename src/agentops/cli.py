"""Command line entry point.

Examples:
  agentops "Review this deployment for production readiness" -f examples/deployment.yaml
  agentops --fake "Anything"      # offline demo, no API key needed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from agentops.llm import ClaudeLLM, FakeLLM
from agentops.system import build_system


def _fake_responder(system: str, prompt: str) -> str:
    if "orchestrator (planner)" in system:
        return json.dumps({"steps": [
            {"agent": "kubernetes", "instruction": "Review the manifest."},
            {"agent": "security", "instruction": "Check for security issues."},
        ]})
    return f"(fake output) {system.split(',')[0]}"


def _build_task(task: str, files: list[str]) -> str:
    for path in files:
        task += f"\n\n--- {path} ---\n{Path(path).read_text()}"
    return task


async def _main(args: argparse.Namespace) -> None:
    llm = FakeLLM(_fake_responder) if args.fake else ClaudeLLM()
    orchestrator = build_system(llm)
    await orchestrator.start()
    try:
        result = await orchestrator.run(_build_task(args.task, args.file))
    finally:
        await orchestrator.stop()

    print("\n=== PLAN ===")
    for i, step in enumerate(result.steps, 1):
        mark = "ok" if step.ok else "FAILED"
        print(f"{i}. [{step.agent}] {step.instruction} ({mark})")
    if args.trace:
        print("\n=== MESSAGE TRACE ===")
        for m in orchestrator.bus.history:
            print(f"{m.sender:>12} -> {m.recipient:<12} {m.type.value:<6} {m.correlation_id}")
    print("\n=== ANSWER ===\n" + result.answer)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="agentops", description=__doc__.splitlines()[0])
    parser.add_argument("task", help="what you want the agent team to do")
    parser.add_argument("-f", "--file", action="append", default=[], help="attach a file")
    parser.add_argument("--fake", action="store_true", help="use FakeLLM (no API calls)")
    parser.add_argument("--trace", action="store_true", help="print the message log")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()
