from __future__ import annotations

from typing import Any

from careops.contracts.decisions import (
    CareOpsDecisionContract,
    DecisionSynthesis,
    ExecutionInfo,
    InternalValidation,
    PatternRef,
    WorkflowRouting,
)
from careops.contracts.evidence import EvidenceItem


def risk_from_evidence(items: list[EvidenceItem], policy: dict[str, Any]) -> str:
    catalog = policy.get("evidence_catalog", {}) or {}
    ids = {
        item.evidence_id
        for item in items
        if item.status == "flagged"
        and bool(catalog.get(item.evidence_id, {}).get("priority_relevant", True))
    }
    result = "Low"
    for tier in sorted(policy.get("risk_tiers", []), key=lambda row: int(row["min_findings"])):
        if len(ids) >= int(tier["min_findings"]):
            result = str(tier["tier"])
    return result


def matched_patterns(
    member: dict[str, Any],
    evidence: list[EvidenceItem],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    ids = {item.evidence_id for item in evidence if item.status == "flagged"}
    diagnoses = {
        part.strip().lower()
        for part in str(member.get("diagnosis") or "").split(",")
        if part.strip()
    }
    matches: list[dict[str, Any]] = []

    for pattern_id, pattern in (policy.get("decision_patterns") or {}).items():
        required_all = set(pattern.get("required_all", []))
        required_any = set(pattern.get("required_any", []))
        also_any = set(pattern.get("also_any", []))
        diagnosis_any = {item.lower() for item in pattern.get("diagnoses_any", [])}

        if required_all and not required_all.issubset(ids):
            continue
        if required_any and not required_any.intersection(ids):
            continue
        if also_any and not also_any.intersection(ids):
            continue
        if diagnosis_any and not diagnosis_any.intersection(diagnoses):
            continue
        if not any((required_all, required_any, also_any, diagnosis_any)):
            continue

        matches.append({"id": pattern_id, **pattern})

    return matches


def pattern_refs(patterns: list[dict[str, Any]]) -> list[PatternRef]:
    return [
        PatternRef(
            id=str(pattern["id"]),
            name=str(pattern["name"]),
            pathway=str(pattern["pathway"]),
            implication=str(pattern["implication"]),
        )
        for pattern in patterns
    ]


def routing_from_patterns(
    evidence: list[EvidenceItem],
    patterns: list[dict[str, Any]],
    policy: dict[str, Any],
) -> WorkflowRouting:
    enabled = {workflow for pattern in patterns for workflow in pattern.get("workflows", [])}
    return WorkflowRouting(
        clinical_followup="clinical_followup" in enabled,
        care_gap_outreach="care_gap_outreach" in enabled,
        utilization_review="utilization_review" in enabled,
        navigation_review="navigation_review" in enabled,
    )


def validate_synthesis(
    synthesis: DecisionSynthesis,
    evidence: list[EvidenceItem],
    allowed_handoffs: list[str],
) -> InternalValidation:
    valid_ids = {item.evidence_id for item in evidence}
    refs = {ref for item in synthesis.rationale for ref in item.evidence_refs}
    refs.update(ref for action in synthesis.actions for ref in action.evidence_refs)
    unknown = refs - valid_ids
    unexpected = set(synthesis.handoffs) - set(allowed_handoffs)
    missing = set(allowed_handoffs) - set(synthesis.handoffs)

    if unknown or unexpected or missing:
        return InternalValidation(
            status="BLOCKED",
            referenced_evidence_ids=sorted(refs & valid_ids),
        )
    return InternalValidation(
        status="READY",
        referenced_evidence_ids=sorted(refs & valid_ids),
    )


def build_contract(
    *,
    decision_id: str,
    scope: str,
    member_id: str,
    priority: str,
    synthesis: DecisionSynthesis,
    evidence: list[EvidenceItem],
    routing: WorkflowRouting,
    patterns: list[PatternRef],
    validation: InternalValidation,
    execution: ExecutionInfo,
    context_fingerprint: str,
    policy_fingerprint: str,
    evaluated_tools: list[str],
    supporting_context: dict[str, Any],
    created_at,
) -> CareOpsDecisionContract:
    return CareOpsDecisionContract(
        decision_id=decision_id,
        scope=scope,
        member_id=member_id,
        status=validation.status,
        priority=priority if validation.status != "BLOCKED" else "Low",
        summary=synthesis.summary,
        why_it_matters=synthesis.why_it_matters,
        rationale=synthesis.rationale,
        next_step=synthesis.next_step,
        actions=synthesis.actions,
        evidence=evidence,
        handoffs=synthesis.handoffs,
        routing=routing,
        patterns=patterns,
        validation=validation,
        execution=execution,
        context_fingerprint=context_fingerprint,
        policy_fingerprint=policy_fingerprint,
        evaluated_tools=evaluated_tools,
        supporting_context=supporting_context,
        created_at=created_at,
    )
