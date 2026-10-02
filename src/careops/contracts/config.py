from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from careops.contracts.base import ContractModel, EvidenceId


class LabRule(ContractModel):
    direction: Literal["high", "low"]
    cutoff: float
    note: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    evidence_id: EvidenceId


class VitalCheck(ContractModel):
    field: str = Field(min_length=1)
    label: str = Field(min_length=1)
    operator: Literal["gt", "lt", "outside"]
    cutoff: float | list[float]
    unit: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_cutoff(self) -> VitalCheck:
        if self.operator == "outside":
            if not isinstance(self.cutoff, list) or len(self.cutoff) != 2:
                raise ValueError("An outside check requires exactly two cut-off values.")
        elif isinstance(self.cutoff, list):
            raise ValueError("This operator requires a scalar cut-off.")
        return self


class VitalRules(ContractModel):
    evidence_id: EvidenceId
    checks: dict[str, VitalCheck] = Field(min_length=1)


class CareGapRules(ContractModel):
    overdue_days: int = Field(ge=0)
    overdue_evidence_id: EvidenceId
    missed_evidence_id: EvidenceId


class UtilizationRules(ContractModel):
    ed_window_days: int = Field(gt=0)
    inpatient_window_days: int = Field(gt=0)
    ed_min_visits: int = Field(ge=0)
    inpatient_min_admissions: int = Field(ge=0)
    ed_evidence_id: EvidenceId
    inpatient_evidence_id: EvidenceId
    ed_unit: str = Field(min_length=1)
    inpatient_unit: str = Field(min_length=1)


class ThresholdPolicies(ContractModel):
    labs: dict[str, LabRule]
    vitals: VitalRules
    care_gaps: CareGapRules
    utilization: UtilizationRules


class RiskTier(ContractModel):
    min_findings: int = Field(ge=0)
    tier: Literal["Low", "Medium", "High", "Critical"]


class EvidenceDefinition(ContractModel):
    domain: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    lifecycle: Literal["Active", "Draft", "Retired"] = "Active"
    priority_relevant: bool = True


class PatternDefinition(ContractModel):
    name: str = Field(min_length=1)
    required_all: list[str] = Field(default_factory=list)
    required_any: list[str] = Field(default_factory=list)
    also_any: list[str] = Field(default_factory=list)
    diagnoses_any: list[str] = Field(default_factory=list)
    implication: str = Field(min_length=1)
    pathway: str = Field(min_length=1)
    workflows: list[str] = Field(default_factory=list)
    recommended_actions: list[dict[str, str]] = Field(default_factory=list)


class ScopeDefinition(ContractModel):
    name: str = Field(min_length=1)
    short_name: str = ""
    mode: Literal["overall", "specialist"]
    agent: str = Field(min_length=1)
    tools: list[str] = Field(min_length=1)
    handoffs: list[str] = Field(min_length=1, max_length=4)
    description: str = Field(min_length=1)


class PolicyConfig(ContractModel):
    revision: int = Field(ge=1)
    risk_tiers: list[RiskTier]
    threshold_policies: ThresholdPolicies
    evidence_catalog: dict[str, EvidenceDefinition]
    decision_patterns: dict[str, PatternDefinition]
    tools: dict[str, dict[str, Any]]
    agents: dict[str, dict[str, Any]]
    scopes: dict[str, ScopeDefinition]
    audiences: dict[str, str]
    tool_dependencies: dict[str, list[str]] = Field(default_factory=dict)
