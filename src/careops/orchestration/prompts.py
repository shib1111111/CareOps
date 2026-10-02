from __future__ import annotations

import json
from typing import Any


def router_prompt(tools: dict[str, Any]) -> str:
    return f"""
You are the CareOps Supervisor Agent.

For an overall member assessment, select the minimum useful deterministic capabilities from this configured catalog:
{json.dumps(tools, indent=2)}

Choose capabilities only from the catalog. Do not invent member facts, clinical conclusions or priority.
Return only the ToolSelection schema.
""".strip()


def synthesis_prompt(
    assessment_name: str,
    agent_name: str,
    allowed_handoffs: list[str],
    patterns: list[dict[str, Any]],
) -> str:
    return f"""
You are the {agent_name} producing a {assessment_name}.

Use only the supplied member context, deterministic evidence and configured pattern implications.
Do not create facts that are not present. Do not calculate or override priority. The application owns priority.
Only reference Evidence IDs that appear in the evidence list.
Create hand-off messages only for these audiences: {allowed_handoffs}.
The audience list is policy-controlled; you are writing the messages, not selecting the audiences.
Keep rationale concise and tied to evidence IDs. Do not provide chain-of-thought.

Configured patterns:
{json.dumps(patterns, indent=2)}
""".strip()
