# Project Brief: agentops

## One line
A team of specialised Claude-powered agents (Kubernetes, Terraform, CI, Security) coordinated
by an orchestrator over a message bus, built to review and improve DevOps setups.

## Why
Single prompts give generic DevOps advice. Splitting the work across focused agents, with an
orchestrator that plans, routes and merges, gives more specific and checkable output. The
interesting engineering is the coordination layer: message passing, routing, failure handling,
tracing and (later) running agents as separate containers.

## Architecture (v0.1, in this repo)

```
            user task + files
                   |
             +-------------+   1. plan (LLM -> JSON steps)
             | Orchestrator|   3. synthesise final answer
             +-------------+
                   |  TASK / RESULT / ERROR messages
             +-------------+
             | Message Bus |   per-agent inboxes, full history for tracing
             +-------------+
        /        |        |         \
  kubernetes  terraform   ci     security      2. each step handled by one agent
```

- **Message protocol** (`messages.py`): `sender`, `recipient`, `type`, `content`,
  `correlation_id`. Replies keep the correlation id so the orchestrator can match them.
- **Bus** (`bus.py`): asyncio queues in-process. Small interface so it can be swapped for Redis.
- **Agents** (`agents/`): each runs its own async loop; failures come back as ERROR messages
  instead of crashing the run.
- **Orchestrator**: plan, dispatch sequentially (each step sees earlier results), synthesise.
- **LLM layer** (`llm.py`): `ClaudeLLM` for real runs, `FakeLLM` for tests and offline demos.

## Milestones

| # | Milestone | Done when |
|---|-----------|-----------|
| 1 | Skeleton: bus, agents, orchestrator, CLI, tests, Docker | **Done in this scaffold** |
| 2 | Real tools: agents call kubeconform, `terraform validate`, trivy, actionlint via Claude tool use | Security agent reports real trivy findings on the example manifest |
| 3 | DAG execution: planner emits dependencies, independent steps run in parallel | Two independent steps measurably overlap in time |
| 4 | Distributed bus: Redis Streams backend, each agent in its own container via compose | `docker compose up` runs 5 containers and a task completes across them |
| 5 | Critic loop: a reviewer agent can reject a step and send it back with feedback | At least one retry visible in the trace |
| 6 | Observability + evals: token/cost/latency per agent, Prometheus metrics, small eval set of known-bad configs | Grafana dashboard + eval score in CI |

Optional later: deploy to AKS with Helm, a small web UI showing the live message trace.

## Out of scope (for now)
Agents changing real infrastructure. Everything is read and review only until there is a
sandbox and an approval step.

## CV bullets this should support
- Designed an async message-passing layer with correlation-based request/reply routing
- Built an LLM orchestrator that plans, dispatches and merges work across specialist agents
- Gave agents real DevOps tooling via Claude tool use (trivy, terraform validate, kubeconform)
- Containerised each agent and ran them over Redis Streams with Docker Compose
