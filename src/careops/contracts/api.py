from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from careops.contracts.decisions import CareOpsDecisionContract


class ApiAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    status: Literal["ready", "review", "blocked"]
    priority: Literal["low", "medium", "high", "critical"]


class ApiMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str


class ApiDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    why_it_matters: str
    next_step: str


class ApiFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    finding: str
    value: str
    unit: str | None = None
    meaning: str


class ApiAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str
    action: str
    supported_by: list[str] = Field(default_factory=list)


class ApiHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: str
    message: str


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment: ApiAssessment
    member: ApiMember
    decision: ApiDecision
    findings: list[ApiFinding]
    actions: list[ApiAction]
    handoffs: list[ApiHandoff]


def build_api_response(contract: CareOpsDecisionContract) -> AssessmentResponse:
    return AssessmentResponse(
        assessment=ApiAssessment(
            id=contract.decision_id,
            type=contract.scope,
            status=contract.status.lower(),
            priority=contract.priority.lower(),
        ),
        member=ApiMember(id=contract.member_id),
        decision=ApiDecision(
            summary=contract.summary,
            why_it_matters=contract.why_it_matters,
            next_step=contract.next_step,
        ),
        findings=[
            ApiFinding(
                evidence_id=item.evidence_id,
                finding=item.signal,
                value=item.value,
                unit=item.unit,
                meaning=item.interpretation,
            )
            for item in contract.evidence
            if item.status == "flagged"
        ],
        actions=[
            ApiAction(
                owner=item.owner,
                action=item.action,
                supported_by=item.evidence_refs,
            )
            for item in sorted(contract.actions, key=lambda action: action.sequence)
        ],
        handoffs=[
            ApiHandoff(audience=audience, message=message)
            for audience, message in contract.handoffs.items()
        ],
    )
