"""Run-record tables.

Every assessment run is flattened into three tidy ("one row = one fact") tables:

    runs      one row per run        -> filter, trend and audit
    findings  one row per finding    -> what was detected, with its evidence ID and value
    actions   one row per action     -> who has to do what

The Pydantic row models are the schema. They validate the data on the way in, and the dtype
maps below give every column an explicit pandas type, so the tables round-trip through Parquet
unchanged. `runs.contract_json` keeps the full decision contract for exact retrieval.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import Field

from careops.contracts.base import EvidenceId, FrozenModel
from careops.contracts.decisions import (
    RISK_ORDER,
    CareOpsDecisionContract,
    DecisionStatus,
    RiskLevel,
)


class RunRow(FrozenModel):
    run_id: str
    agent_key: str
    agent_name: str
    scope: str
    member_id: str
    status: DecisionStatus
    priority: RiskLevel
    flagged_count: int = Field(ge=0)
    patterns: str
    evaluated_tools: str
    model: str | None
    llm_calls: int = Field(ge=0, le=2)
    duration_ms: int = Field(ge=0)
    summary: str
    next_step: str
    context_fingerprint: str
    policy_fingerprint: str
    created_at: datetime
    contract_json: str


class FindingRow(FrozenModel):
    run_id: str
    agent_key: str
    member_id: str
    created_at: datetime
    evidence_id: EvidenceId
    domain: str
    signal: str
    value: str
    unit: str | None
    status: Literal["flagged", "informational"]
    interpretation: str


class ActionRow(FrozenModel):
    run_id: str
    agent_key: str
    member_id: str
    created_at: datetime
    sequence: int = Field(ge=1)
    owner: str
    action: str
    rationale: str
    evidence_refs: str


_RISK = pd.CategoricalDtype(categories=list(RISK_ORDER), ordered=True)
_STATUS = pd.CategoricalDtype(categories=["READY", "REVIEW", "BLOCKED"])
_UTC = "datetime64[ns, UTC]"

RUN_DTYPES: dict[str, object] = {
    "run_id": "string",
    "agent_key": "category",
    "agent_name": "string",
    "scope": "category",
    "member_id": "string",
    "status": _STATUS,
    "priority": _RISK,
    "flagged_count": "Int16",
    "patterns": "string",
    "evaluated_tools": "string",
    "model": "string",
    "llm_calls": "Int8",
    "duration_ms": "Int32",
    "summary": "string",
    "next_step": "string",
    "context_fingerprint": "string",
    "policy_fingerprint": "string",
    "created_at": _UTC,
    "contract_json": "string",
}
FINDING_DTYPES: dict[str, object] = {
    "run_id": "string",
    "agent_key": "category",
    "member_id": "string",
    "created_at": _UTC,
    "evidence_id": "category",
    "domain": "category",
    "signal": "string",
    "value": "string",
    "unit": "string",
    "status": "category",
    "interpretation": "string",
}
ACTION_DTYPES: dict[str, object] = {
    "run_id": "string",
    "agent_key": "category",
    "member_id": "string",
    "created_at": _UTC,
    "sequence": "Int8",
    "owner": "category",
    "action": "string",
    "rationale": "string",
    "evidence_refs": "string",
}

TABLES: dict[str, tuple[type[FrozenModel], dict[str, object]]] = {
    "runs": (RunRow, RUN_DTYPES),
    "findings": (FindingRow, FINDING_DTYPES),
    "actions": (ActionRow, ACTION_DTYPES),
}


@dataclass(frozen=True)
class RunFrames:
    runs: pd.DataFrame
    findings: pd.DataFrame
    actions: pd.DataFrame

    def items(self) -> Iterable[tuple[str, pd.DataFrame]]:
        yield "findings", self.findings
        yield "actions", self.actions
        yield "runs", self.runs  # the index table is written last


def normalize(table: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the declared column order and dtypes to a table."""
    model, dtypes = TABLES[table]
    columns = list(model.model_fields)
    out = frame.reindex(columns=columns).copy()
    out["created_at"] = pd.to_datetime(out["created_at"], utc=True)
    return out.astype({k: v for k, v in dtypes.items() if k != "created_at"}).astype(
        {"created_at": _UTC}
    )


def empty_frames() -> RunFrames:
    return RunFrames(
        runs=normalize("runs", pd.DataFrame(columns=list(RunRow.model_fields))),
        findings=normalize("findings", pd.DataFrame(columns=list(FindingRow.model_fields))),
        actions=normalize("actions", pd.DataFrame(columns=list(ActionRow.model_fields))),
    )


def _frame(table: str, rows: Iterable[FrozenModel]) -> pd.DataFrame:
    model, _ = TABLES[table]
    data = [row.model_dump() for row in rows]
    return normalize(table, pd.DataFrame(data, columns=list(model.model_fields)))


def frames_from_contract(contract: CareOpsDecisionContract) -> RunFrames:
    """Flatten one decision contract into its three validated tables."""
    base = {
        "run_id": contract.decision_id,
        "agent_key": contract.execution.agent_key,
        "member_id": contract.member_id,
        "created_at": contract.created_at,
    }
    run = RunRow(
        run_id=contract.decision_id,
        agent_key=contract.execution.agent_key,
        agent_name=contract.execution.agent_name,
        scope=contract.scope,
        member_id=contract.member_id,
        status=contract.status,
        priority=contract.priority,
        flagged_count=len(contract.flagged),
        patterns=", ".join(pattern.name for pattern in contract.patterns),
        evaluated_tools=", ".join(contract.evaluated_tools),
        model=contract.execution.model,
        llm_calls=contract.execution.llm_calls,
        duration_ms=contract.execution.duration_ms,
        summary=contract.summary,
        next_step=contract.next_step,
        context_fingerprint=contract.context_fingerprint,
        policy_fingerprint=contract.policy_fingerprint,
        created_at=contract.created_at,
        contract_json=contract.model_dump_json(),
    )
    findings = [
        FindingRow(
            **base,
            evidence_id=item.evidence_id,
            domain=item.domain,
            signal=item.signal,
            value=item.value,
            unit=item.unit,
            status=item.status,
            interpretation=item.interpretation,
        )
        for item in contract.evidence
    ]
    actions = [
        ActionRow(
            **base,
            sequence=item.sequence,
            owner=item.owner,
            action=item.action,
            rationale=item.rationale,
            evidence_refs=", ".join(item.evidence_refs),
        )
        for item in contract.actions
    ]
    return RunFrames(
        runs=_frame("runs", [run]),
        findings=_frame("findings", findings),
        actions=_frame("actions", actions),
    )
