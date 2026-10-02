from __future__ import annotations

import json
from typing import Any

from careops.contracts.decisions import DecisionSynthesis, ToolSelection
from careops.infrastructure.ai import LLMRuntime
from careops.orchestration.prompts import router_prompt, synthesis_prompt


class LLMOrchestrator:
    def __init__(self, runtime: LLMRuntime) -> None:
        self.runtime = runtime

    def select_tools(
        self,
        member: dict[str, Any],
        instruction: str,
        tools: dict[str, Any],
    ) -> ToolSelection:
        payload = {
            "instruction": instruction
            or "Select the minimum useful capabilities for this overall member assessment.",
            "member": {
                "id": member.get("patient_id"),
                "diagnosis": member.get("diagnosis"),
            },
            "available_capabilities": tools,
        }
        return self.runtime.structured_invoke(
            router_prompt(tools),
            json.dumps(payload, default=str, separators=(",", ":")),
            ToolSelection,
        )

    def synthesize(
        self,
        member: dict[str, Any],
        evidence: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        supporting_context: dict[str, Any],
        assessment_name: str,
        agent_name: str,
        allowed_handoffs: list[str],
        instruction: str,
    ) -> DecisionSynthesis:
        payload = {
            "assessment": assessment_name,
            "instruction": instruction,
            "member": {
                "id": member.get("patient_id"),
                "name": member.get("patient_name"),
                "diagnosis": member.get("diagnosis"),
            },
            "evidence": evidence,
            "matched_patterns": patterns,
            "supporting_context": supporting_context,
            "allowed_handoffs": allowed_handoffs,
        }
        return self.runtime.structured_invoke(
            synthesis_prompt(assessment_name, agent_name, allowed_handoffs, patterns),
            json.dumps(payload, default=str, separators=(",", ":")),
            DecisionSynthesis,
        )
