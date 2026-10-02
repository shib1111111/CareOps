from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from careops.contracts.base import FrozenModel
from careops.contracts.evidence import EvidenceItem

RiskLevel = Literal["Low", "Medium", "High", "Critical"]
DecisionStatus = Literal["READY", "REVIEW", "BLOCKED"]
ActionOwner = Literal["Care Team", "Care Navigator", "Health Plan", "Member", "Human Review"]

RISK_ORDER: tuple[str, ...] = ("Low", "Medium", "High", "Critical")


# --------------------------------------------------------------------------------------
# LLM-facing schemas. Kept as plain, inline-enum models so structured output stays simple.
# --------------------------------------------------------------------------------------
class ToolSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_tools: list[str] = Field(min_length=1, max_length=8)
    routing_reason: str = Field(min_length=1, max_length=500)


class ReasoningItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conclusion: str = Field(min_length=1, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=500)
    owner: ActionOwner
    sequence: int = Field(ge=1, le=8)
    rationale: str = Field(min_length=1, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)


class DecisionSynthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1600)
    why_it_matters: str = Field(min_length=1, max_length=1000)
    rationale: list[ReasoningItem] = Field(min_length=1, max_length=6)
    next_step: str = Field(min_length=1, max_length=500)
    actions: list[ActionItem] = Field(min_length=1, max_length=8)
    handoffs: dict[str, str] = Field(min_length=1, max_length=4)


# --------------------------------------------------------------------------------------
# Persisted decision contract. Immutable and fully typed.
# --------------------------------------------------------------------------------------
class WorkflowRouting(FrozenModel):
    clinical_followup: bool = False
    care_gap_outreach: bool = False
    utilization_review: bool = False
    navigation_review: bool = False


class InternalValidation(FrozenModel):
    status: DecisionStatus
    referenced_evidence_ids: list[str] = Field(default_factory=list)


class PatternRef(FrozenModel):
    """A configured evidence pattern that matched this member."""

    id: str
    name: str
    pathway: str
    implication: str


class ExecutionInfo(FrozenModel):
    """How the run was executed. Supports auditing and the run-history tables."""

    agent_key: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    route: Literal["overall", "specialist"]
    model: str | None = None  # stored for audit only; never shown in the UI or API
    llm_calls: int = Field(ge=0, le=2)
    duration_ms: int = Field(ge=0)
    routing_reason: str | None = None


class CareOpsDecisionContract(FrozenModel):
    decision_id: str
    scope: str
    member_id: str
    status: DecisionStatus
    priority: RiskLevel
    summary: str
    why_it_matters: str
    rationale: list[ReasoningItem]
    next_step: str
    actions: list[ActionItem]
    evidence: list[EvidenceItem]
    handoffs: dict[str, str]
    routing: WorkflowRouting
    patterns: list[PatternRef] = Field(default_factory=list)
    validation: InternalValidation
    execution: ExecutionInfo
    context_fingerprint: str
    policy_fingerprint: str
    evaluated_tools: list[str] = Field(default_factory=list)
    supporting_context: dict[str, object] = Field(default_factory=dict)
    created_at: datetime

    @property
    def flagged(self) -> list[EvidenceItem]:
        return [item for item in self.evidence if item.status == "flagged"]
