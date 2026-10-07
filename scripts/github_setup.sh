#!/usr/bin/env bash
# One-off setup: creates the GitHub repo, labels, milestones, issues and branch protection.
# Safe to re-run: existing labels, milestones and issues are skipped.
# Usage: ./scripts/github_setup.sh [repo-name] [public|private]
set -euo pipefail

REPO_NAME="${1:-agentops}"
VISIBILITY="${2:-public}"

command -v gh >/dev/null || { echo "Install the GitHub CLI first: https://cli.github.com"; exit 1; }
gh auth status >/dev/null || { echo "Run 'gh auth login' first"; exit 1; }

# 1. Repo ---------------------------------------------------------------------
if ! git remote get-url origin >/dev/null 2>&1; then
  gh repo create "$REPO_NAME" "--$VISIBILITY" --source=. --remote=origin --push \
    --description "Multi-agent AI system for DevOps tasks. Python, Claude API, Docker."
else
  git push -u origin main
fi
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
echo "Repo: $REPO"

gh repo edit "$REPO" \
  --enable-issues --enable-squash-merge \
  --enable-merge-commit=false --enable-rebase-merge=false \
  --delete-branch-on-merge \
  --add-topic multi-agent --add-topic llm --add-topic claude --add-topic devops --add-topic python

# 2. Labels -------------------------------------------------------------------
label() { gh label create "$1" --color "$2" --description "$3" --force -R "$REPO" >/dev/null; }
label "agent"         "1d76db" "Specialist agents"
label "orchestration" "5319e7" "Planner, routing, message bus"
label "tools"         "0e8a16" "Real DevOps tool integrations"
label "infra"         "c5def5" "Docker, compose, deployment"
label "observability" "fbca04" "Metrics, tracing, evals"
label "docs"          "bfdadc" "Documentation"
echo "Labels done"

# 3. Milestones ---------------------------------------------------------------
existing_ms="$(gh api "repos/$REPO/milestones?state=all&per_page=100" -q '.[].title')"
milestone() {
  if ! grep -qxF "$1" <<<"$existing_ms"; then
    gh api "repos/$REPO/milestones" -f title="$1" -f description="$2" >/dev/null
  fi
}
milestone "M2: Real tools"          "Agents call trivy, terraform validate, kubeconform, actionlint via Claude tool use"
milestone "M3: DAG execution"       "Planner emits dependencies; independent steps run in parallel"
milestone "M4: Distributed bus"     "Redis Streams backend, one container per agent"
milestone "M5: Critic loop"         "Reviewer agent can reject a step and request a retry"
milestone "M6: Observability+evals" "Token/cost/latency metrics, Prometheus, Grafana, eval set in CI"
echo "Milestones done"

# 4. Issues -------------------------------------------------------------------
existing_issues="$(gh issue list -R "$REPO" --state all --limit 500 --json title -q '.[].title')"
issue() { # title, milestone, labels, body
  if ! grep -qxF "$1" <<<"$existing_issues"; then
    gh issue create -R "$REPO" --title "$1" --milestone "$2" --label "$3" --body "$4" >/dev/null
    echo "  + $1"
  fi
}

issue "Add tool-use support to the Agent base class" "M2: Real tools" "agent,tools" \
"Let agents declare tools and run the Claude tool-use loop (call, execute, return result, continue).

- [ ] Tool definition + registry on Agent
- [ ] Loop with a max-iterations guard
- [ ] FakeLLM support for scripted tool calls in tests"

issue "Security agent runs trivy config scans" "M2: Real tools" "agent,tools" \
"Security agent runs \`trivy config\` on attached files in a temp dir and reasons over real findings.

Done when it reports the privileged container and hardcoded password in examples/deployment.yaml from trivy output."

issue "Kubernetes agent validates manifests with kubeconform" "M2: Real tools" "agent,tools" \
"Run kubeconform on manifests and feed results to the agent."

issue "Terraform agent runs terraform fmt/validate" "M2: Real tools" "agent,tools" \
"Run \`terraform fmt -check\` and \`terraform validate\` (no backend, no apply) on attached .tf files."

issue "CI agent lints workflows with actionlint" "M2: Real tools" "agent,tools" \
"Run actionlint on attached GitHub Actions workflows."

issue "Install tool binaries in the Docker image" "M2: Real tools" "infra,tools" \
"Pin versions of trivy, kubeconform, terraform and actionlint in the Dockerfile."

issue "Planner emits step dependencies" "M3: DAG execution" "orchestration" \
"Extend the plan JSON with \`depends_on\` and validate it is acyclic."

issue "Run independent steps in parallel" "M3: DAG execution" "orchestration" \
"Execute ready steps with asyncio.gather. Test proves two independent steps overlap in time."

issue "Redis Streams message bus backend" "M4: Distributed bus" "orchestration,infra" \
"Implement the register/send/trace interface on Redis Streams. In-memory bus stays the default."

issue "One container per agent in docker compose" "M4: Distributed bus" "infra" \
"Each agent runs as its own service; \`docker compose up\` completes a task across containers."

issue "Reviewer agent with reject-and-retry" "M5: Critic loop" "agent,orchestration" \
"Reviewer checks each step result; on reject the step is re-sent with feedback (max retries configurable). Retry visible in trace."

issue "Per-agent token, cost and latency tracking" "M6: Observability+evals" "observability" \
"Record usage per message and include it in the trace output."

issue "Prometheus metrics and Grafana dashboard" "M6: Observability+evals" "observability,infra" \
"Expose metrics endpoint; add Prometheus + Grafana to compose with a provisioned dashboard."

issue "Eval set of known-bad configs" "M6: Observability+evals" "observability" \
"A folder of configs with expected findings, a scorer, and a CI job that runs it on demand."
echo "Issues done"

# 5. Branch protection (needs a public repo or a paid plan for private repos) ---
if gh api -X PUT "repos/$REPO/branches/main/protection" --input - >/dev/null 2>&1 <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["test"] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
then
  echo "Branch protection on main: CI 'test' must pass before merging"
else
  echo "Skipped branch protection (private repo on free plan?). Set it later in Settings > Branches."
fi

echo "All set: https://github.com/$REPO"
