.PHONY: install test lint demo docker

install:
	python -m venv .venv && .venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check src tests

demo:
	.venv/bin/agentops --fake --trace "Review this deployment" -f examples/deployment.yaml

docker:
	docker compose build
