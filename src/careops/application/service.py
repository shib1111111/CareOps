from __future__ import annotations

import uuid
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import pandas as pd

from careops.contracts.decisions import CareOpsDecisionContract, ExecutionInfo
from careops.contracts.evidence import EvidenceItem
from careops.contracts.runs import RunFrames
from careops.domains.decisions.service import (
    build_contract,
    matched_patterns,
    pattern_refs,
    risk_from_evidence,
    routing_from_patterns,
    validate_synthesis,
)
from careops.infrastructure.ai import LLMRuntime
from careops.infrastructure.config import DATA_DIR
from careops.infrastructure.persistence import RunStore
from careops.infrastructure.repository import DataRepository
from careops.orchestration.agent import ToolContext, run_tools
from careops.orchestration.catalog import agent_catalog, tool_catalog
from careops.orchestration.llm import LLMOrchestrator


class CareOpsService:
    """Application service shared by the Streamlit workspace and the public API."""

    def __init__(
        self,
        repository: DataRepository | None = None,
        store: RunStore | None = None,
    ) -> None:
        self.repository = repository or DataRepository(DATA_DIR)
        self.store = store or RunStore(DATA_DIR)
        self._runtime: LLMRuntime | None = None

    # ------------------------------------------------------------------ data
    def population(self) -> pd.DataFrame:
        return self.repository.patients()

    def claims(self) -> pd.DataFrame:
        return self.repository.claims()

    def enrollment(self) -> pd.DataFrame:
        return self.repository.enrollment()

    def rules(self) -> dict[str, Any]:
        return self.repository.rules()

    def member_record(self, member_id: str) -> dict[str, Any]:
        return self.repository.member_record(member_id)

    def save_rules(self, rules: dict[str, Any]) -> None:
        self.repository.save_rules(rules)

    def reset_rules(self) -> None:
        self.repository.reset_rules()

    # ------------------------------------------------------------ run history
    def saved_runs(self, agent_key: str | None = None) -> RunFrames:
        return self.store.frames(agent_key)

    def get_saved_decision(self, assessment_id: str) -> CareOpsDecisionContract | None:
        return self.store.get(assessment_id)

    # --------------------------------------------------------------- analysis
    def assess(
        self,
        member_id: str,
        *,
        scope: str = "overall",
        instruction: str = "",
        fresh: bool = False,
    ) -> tuple[CareOpsDecisionContract, bool]:
        """Return ``(result, reused)``.

        Unless ``fresh`` is set, an already-saved result for this member and review is returned
        as-is (no model call) when the member's data and the policy are unchanged since it was
        produced. A custom ``instruction`` always runs fresh, because it changes what is asked.
        """
        if not fresh and not instruction.strip():
            saved = self.find_saved(member_id, scope)
            if saved is not None:
                return saved, True
        return self.analyze(member_id, scope=scope, instruction=instruction), False

    def find_saved(self, member_id: str, scope: str) -> CareOpsDecisionContract | None:
        """Newest saved result for this member + review that is still valid for current inputs."""
        policy = self.rules()
        scope_def = self._scope(policy, scope)
        self._patient_series(member_id)  # raises KeyError for an unknown member
        fingerprint = self.repository.member_fingerprint(
            member_id, self.member_record(member_id), self.claims(), self.enrollment()
        )
        return self.store.find_reusable(
            scope_def["agent"], scope, member_id, fingerprint, self.repository.rules_hash(policy)
        )

    def analyze(
        self,
        member_id: str,
        *,
        scope: str = "overall",
        instruction: str = "",
    ) -> CareOpsDecisionContract:
        """Always run one fresh assessment and store it under the agent that produced it.

        Every run reads the current member data and policy. Nothing from a previous run,
        by any agent, is used as input.
        """
        started = perf_counter()
        policy = self.rules()
        scope_def = self._scope(policy, scope)
        agent_key = scope_def["agent"]
        agent = agent_catalog(policy)[agent_key]

        patient = self._patient_series(member_id)
        member = self.member_record(member_id)
        claims = self.claims()
        enrollment = self.enrollment()
        context_fingerprint = self.repository.member_fingerprint(
            member_id, member, claims, enrollment
        )
        policy_fingerprint = self.repository.rules_hash(policy)

        runtime = self._runtime or LLMRuntime()
        self._runtime = runtime
        llm = LLMOrchestrator(runtime)

        # 1. Which deterministic capabilities to run.
        routing_reason: str | None = None
        if scope_def["mode"] == "overall":
            selection = llm.select_tools(member, instruction, tool_catalog(policy))
            tools = self._valid_tools(selection.selected_tools, policy)
            routing_reason = selection.routing_reason
        else:
            tools = list(scope_def["tools"])

        # 2. Deterministic evaluation -> evidence.
        evaluated_tools, evidence, supporting_context = run_tools(
            tools, ToolContext(patient, member_id, policy, claims, enrollment)
        )
        evidence_models = [EvidenceItem.model_validate(item) for item in evidence]
        patterns = matched_patterns(member, evidence_models, policy)
        priority = risk_from_evidence(evidence_models, policy)
        allowed_handoffs = list(scope_def["handoffs"])

        # 3. AI synthesis, then guardrail validation.
        synthesis = llm.synthesize(
            member,
            [item.model_dump(mode="json") for item in evidence_models],
            patterns,
            supporting_context,
            scope_def["name"],
            agent.name,
            allowed_handoffs,
            instruction,
        )
        validation = validate_synthesis(synthesis, evidence_models, allowed_handoffs)

        execution = ExecutionInfo(
            agent_key=agent_key,
            agent_name=agent.name,
            route=scope_def["mode"],
            model=runtime.model,
            llm_calls=2 if scope_def["mode"] == "overall" else 1,
            duration_ms=round((perf_counter() - started) * 1000),
            routing_reason=routing_reason,
        )
        contract = build_contract(
            decision_id=f"assessment-{uuid.uuid4().hex[:10]}",
            scope=scope,
            member_id=member_id,
            priority=priority,
            synthesis=synthesis,
            evidence=evidence_models,
            routing=routing_from_patterns(evidence_models, patterns, policy),
            patterns=pattern_refs(patterns),
            validation=validation,
            execution=execution,
            context_fingerprint=context_fingerprint,
            policy_fingerprint=policy_fingerprint,
            evaluated_tools=evaluated_tools,
            supporting_context=supporting_context,
            created_at=datetime.now(UTC),
        )
        self.store.save(contract)
        return contract

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _valid_tools(selected: list[str], policy: dict[str, Any]) -> list[str]:
        configured = set(policy.get("tools", {}))
        valid = [tool for tool in dict.fromkeys(selected) if tool in configured]
        if not valid:
            valid = list(policy.get("scopes", {}).get("overall", {}).get("tools", []))
        return valid

    @staticmethod
    def _scope(policy: dict[str, Any], scope: str) -> dict[str, Any]:
        try:
            return policy["scopes"][scope]
        except KeyError as exc:
            supported = ", ".join(policy.get("scopes", {}))
            raise ValueError(
                f"Unsupported assessment type '{scope}'. Available: {supported}."
            ) from exc

    def _patient_series(self, member_id: str) -> pd.Series:
        rows = self.repository.patients()
        matched = rows.loc[rows["patient_id"].astype(str).eq(str(member_id))]
        if matched.empty:
            raise KeyError(f"Member {member_id} was not found.")
        return matched.iloc[0]
