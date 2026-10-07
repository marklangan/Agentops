"""Specialist DevOps agents.

Each one is an LLM with a focused system prompt. Milestone 2 in BRIEF.md gives
them real tools (kubeconform, terraform validate, trivy, actionlint).
"""

from agentops.agents.base import Agent

_COMMON = (
    "You are one agent in a team coordinated by an orchestrator. "
    "Do only the part of the task that matches your speciality. "
    "Be concrete: give file snippets, commands and specific findings, not general advice. "
    "If something is outside your area, say so in one line."
)


class KubernetesAgent(Agent):
    name = "kubernetes"
    description = "Writes and reviews Kubernetes manifests and Helm charts (AKS focused)."
    system_prompt = (
        "You are the kubernetes agent, an expert in Kubernetes, Helm and Azure AKS. "
        "You check resource requests and limits, probes, rollout strategy, RBAC and labels. "
        + _COMMON
    )


class TerraformAgent(Agent):
    name = "terraform"
    description = "Writes and reviews Terraform for Azure infrastructure."
    system_prompt = (
        "You are the terraform agent, an expert in Terraform on Azure (azurerm provider). "
        "You care about state, modules, variables, tagging and least privilege. "
        + _COMMON
    )


class CIAgent(Agent):
    name = "ci"
    description = "Designs and fixes GitHub Actions CI/CD pipelines."
    system_prompt = (
        "You are the ci agent, an expert in GitHub Actions. "
        "You focus on caching, job parallelism, environments, secrets handling and speed. "
        + _COMMON
    )


class SecurityAgent(Agent):
    name = "security"
    description = "Reviews configs and pipelines for security issues (Trivy style findings)."
    system_prompt = (
        "You are the security agent. You review manifests, IaC and pipelines for "
        "misconfigurations, exposed secrets, image risks and privilege escalation. "
        "Rate each finding as HIGH, MEDIUM or LOW. "
        + _COMMON
    )
