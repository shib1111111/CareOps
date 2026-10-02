from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from careops.domains.care_gaps.service import build_evidence as build_care_gap_evidence
from careops.domains.clinical.service import build_evidence as build_clinical_evidence
from careops.domains.plan.service import assess as assess_plan
from careops.domains.utilization.service import build_evidence as build_utilization_evidence


@dataclass(frozen=True)
class ToolContext:
    patient: pd.Series
    member_id: str
    policy: dict[str, Any]
    claims: pd.DataFrame
    enrollment: pd.DataFrame


ToolHandler = Callable[[ToolContext], tuple[list[dict[str, Any]], dict[str, Any]]]


def _clinical(ctx: ToolContext) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return build_clinical_evidence(ctx.patient, ctx.policy), {}


def _care_gap(ctx: ToolContext) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return build_care_gap_evidence(ctx.patient, ctx.policy), {}


def _utilization(ctx: ToolContext) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return build_utilization_evidence(ctx.member_id, ctx.claims, ctx.policy), {}


def _plan(ctx: ToolContext) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return [], {"plan": assess_plan(ctx.member_id, ctx.enrollment)}


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "clinical_assessment": _clinical,
    "care_gap_assessment": _care_gap,
    "utilization_assessment": _utilization,
    "plan_context": _plan,
}


def expand_dependencies(selected_tools: list[str], policy: dict[str, Any]) -> list[str]:
    dependencies = policy.get("tool_dependencies", {}) or {}
    ordered: list[str] = []

    def visit(tool: str) -> None:
        for dependency in dependencies.get(tool, []):
            visit(str(dependency))
        if tool not in ordered:
            ordered.append(tool)

    for tool in selected_tools:
        visit(tool)
    return ordered


def run_tools(
    selected_tools: list[str],
    ctx: ToolContext,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    evaluated: list[str] = []
    evidence: list[dict[str, Any]] = []
    context: dict[str, Any] = {}

    for name in expand_dependencies(selected_tools, ctx.policy):
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            raise ValueError(f"Tool '{name}' is not registered.")
        evaluated.append(name)
        new_evidence, new_context = handler(ctx)
        evidence.extend(new_evidence)
        context.update(new_context)

    return evaluated, _dedupe_evidence(evidence), context


def _dedupe_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[object, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (
            item.get("evidence_id"),
            item.get("signal"),
            item.get("value"),
            item.get("unit"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
