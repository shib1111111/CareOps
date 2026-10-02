from __future__ import annotations

from typing import Any

import pandas as pd

from careops.domains.evidence.catalog import evidence_meta


def assess(patient: pd.Series, policy: dict[str, Any]) -> dict[str, Any]:
    thresholds = policy.get("threshold_policies", {}).get("care_gaps", {}) or {}
    days = pd.to_numeric(patient.get("days_since_last_visit"), errors="coerce")
    missed = str(patient.get("missed_last_appointment") or "").strip().lower() == "yes"
    overdue = not pd.isna(days) and int(days) >= int(thresholds["overdue_days"])
    return {
        "overdue": overdue,
        "missed": missed,
        "days": None if pd.isna(days) else int(days),
    }


def build_evidence(patient: pd.Series, policy: dict[str, Any]) -> list[dict[str, Any]]:
    result = assess(patient, policy)
    thresholds = policy["threshold_policies"]["care_gaps"]
    items: list[dict[str, Any]] = []

    if result["overdue"]:
        evidence_id = str(thresholds["overdue_evidence_id"])
        meta = evidence_meta(policy, evidence_id)
        items.append(
            {
                "evidence_id": evidence_id,
                "domain": meta["domain"],
                "signal": meta["name"],
                "value": str(result["days"]),
                "unit": "days",
                "status": "flagged",
                "interpretation": meta["description"],
            }
        )

    if result["missed"]:
        evidence_id = str(thresholds["missed_evidence_id"])
        meta = evidence_meta(policy, evidence_id)
        items.append(
            {
                "evidence_id": evidence_id,
                "domain": meta["domain"],
                "signal": meta["name"],
                "value": "Yes",
                "unit": None,
                "status": "flagged",
                "interpretation": meta["description"],
            }
        )

    return items
