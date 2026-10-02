from __future__ import annotations

from typing import Any

import pandas as pd

from careops.domains.evidence.catalog import evidence_meta


def _matches(value: float, operator: str, cutoff: object) -> bool:
    if operator == "gt":
        return value > float(cutoff)
    if operator == "lt":
        return value < float(cutoff)
    if operator == "outside":
        low, high = cutoff
        return value < float(low) or value > float(high)
    raise ValueError(f"Unsupported threshold operator: {operator}")


def assess_lab(patient: pd.Series, policy: dict[str, Any]) -> dict[str, Any]:
    test_value = patient.get("lab_test")
    numeric_value = pd.to_numeric(patient.get("lab_value"), errors="coerce")
    test = "" if test_value is None or pd.isna(test_value) else str(test_value).strip()
    if not test or pd.isna(numeric_value):
        return {"available": False, "flagged": False}

    spec = (policy.get("threshold_policies", {}).get("labs", {}) or {}).get(test)
    if not spec:
        return {
            "available": True,
            "flagged": False,
            "test": test,
            "value": float(numeric_value),
        }

    numeric = float(numeric_value)
    operator = "gt" if spec["direction"] == "high" else "lt"
    return {
        "available": True,
        "flagged": _matches(numeric, operator, spec["cutoff"]),
        "test": test,
        "value": numeric,
        "unit": str(spec["unit"]),
        "direction": str(spec["direction"]),
        "note": str(spec["note"]),
        "evidence_id": str(spec["evidence_id"]),
    }


def assess_vitals(patient: pd.Series, policy: dict[str, Any]) -> dict[str, Any]:
    thresholds = policy.get("threshold_policies", {}).get("vitals", {}) or {}
    checks: list[dict[str, Any]] = []
    for spec in (thresholds.get("checks", {}) or {}).values():
        value = pd.to_numeric(patient.get(spec["field"]), errors="coerce")
        if pd.isna(value):
            continue
        numeric = float(value)
        if _matches(numeric, str(spec["operator"]), spec["cutoff"]):
            checks.append(
                {
                    "label": str(spec["label"]),
                    "value": numeric,
                    "unit": str(spec["unit"]),
                }
            )
    return {
        "available": bool(checks),
        "flagged": bool(checks),
        "checks": checks,
        "evidence_id": str(thresholds["evidence_id"]),
    }


def build_evidence(patient: pd.Series, policy: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    lab = assess_lab(patient, policy)
    if lab.get("flagged"):
        evidence_id = str(lab["evidence_id"])
        meta = evidence_meta(policy, evidence_id)
        items.append(
            {
                "evidence_id": evidence_id,
                "domain": meta["domain"],
                "signal": f"{lab['test']} {'above' if lab['direction'] == 'high' else 'below'} threshold",
                "value": f"{lab['value']:g}",
                "unit": lab["unit"],
                "status": "flagged",
                "interpretation": lab["note"],
            }
        )

    vitals = assess_vitals(patient, policy)
    if vitals.get("flagged"):
        evidence_id = str(vitals["evidence_id"])
        meta = evidence_meta(policy, evidence_id)
        value = "; ".join(
            f"{item['label']} {item['value']:g} {item['unit']}" for item in vitals["checks"]
        )
        items.append(
            {
                "evidence_id": evidence_id,
                "domain": meta["domain"],
                "signal": meta["name"],
                "value": value,
                "unit": "mixed",
                "status": "flagged",
                "interpretation": meta["description"],
            }
        )

    return items
