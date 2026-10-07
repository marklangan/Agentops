# CLAUDE.md

Context for Claude Code working in this repo.

## What this is
A learning/portfolio project: a multi-agent system for DevOps tasks. Read BRIEF.md for the
goals and milestone plan. Milestone 1 (skeleton) is done; work on later milestones in order
unless told otherwise.

## Commands
- Install: `make install`
- Tests: `make test` (must pass before any commit)
- Lint: `make lint`
- Offline demo: `make demo`

## Conventions
- Python 3.11+, async throughout, type hints on public functions.
- Agents never call each other directly. All communication goes through `MessageBus` using
  `Message`. Replies must keep the `correlation_id` (use `Message.reply`).
- Agent failures should become `MessageType.ERROR` replies, not unhandled exceptions.
- Every new feature gets a test that runs offline with `FakeLLM`. No real API calls in tests.
- The bus interface (`register`, `send`, `trace`) should stay stable so a Redis backend can
  drop in later.
- Model is set via `AGENTOPS_MODEL`; do not hardcode model names elsewhere.
- Agents are read/review only. Do not add anything that applies changes to real infrastructure.
- Do not use em dashes in docs or comments.

## Owner background
Owner is comfortable with Kubernetes, Terraform, AKS, GitHub Actions, Helm, Prometheus,
Grafana and Trivy. Explain agent/LLM design choices; skip basics of the DevOps tooling.
