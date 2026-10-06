# agentops

Specialised AI agents (Kubernetes, Terraform, CI, Security) that coordinate over a message bus
to complete multi-step DevOps tasks. Python, Claude API, Docker. See [BRIEF.md](BRIEF.md).

## Quick start

```bash
make install                 # creates .venv and installs with dev deps
cp .env.example .env         # add your ANTHROPIC_API_KEY
make test
make demo                    # offline run with FakeLLM

.venv/bin/agentops "Review this deployment for production readiness" \
  -f examples/deployment.yaml --trace
```

## Docker

```bash
docker compose build
docker compose run --rm agentops "Review for prod" -f examples/deployment.yaml --trace
```

## Layout

```
src/agentops/
  messages.py         message protocol
  bus.py              in-process message bus
  llm.py              ClaudeLLM + FakeLLM
  system.py           wires everything together
  cli.py              command line entry point
  agents/
    base.py           worker agent loop
    orchestrator.py   plan -> dispatch -> synthesise
    specialists.py    kubernetes, terraform, ci, security
tests/                offline tests using FakeLLM
examples/             sample configs for agents to review
```
