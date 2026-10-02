from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    name: str
    role: str
    purpose: str


def tool_catalog(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(policy.get("tools") or {})


def agent_catalog(policy: dict[str, Any]) -> dict[str, AgentDefinition]:
    return {
        key: AgentDefinition(
            key=key,
            name=str(value.get("name", key)),
            role=str(value.get("role", "Agent")),
            purpose=str(value.get("purpose", "Configured CareOps agent.")),
        )
        for key, value in (policy.get("agents") or {}).items()
    }
