from __future__ import annotations

from typing import Any

import pandas as pd

from careops.domains.evidence.catalog import evidence_meta


def assess(member_id: str, claims: pd.DataFrame, policy: dict[str, Any]) -> dict[str, Any]:
    thresholds = policy.get("threshold_policies", {}).get("utilization", {}) or {}
    if claims.empty or "patient_id" not in claims.columns:
        return {"available": False, "recent_ed": 0, "recent_inpatient": 0}

    rows = claims.loc[claims["patient_id"].astype(str).eq(str(member_id))].copy()
    if rows.empty:
        return {"available": True, "recent_ed": 0, "recent_inpatient": 0}

    service_dates = pd.to_datetime(rows["service_date"], errors="coerce")
    reference = service_dates.max()
    if pd.isna(reference):
        return {"available": True, "recent_ed": 0, "recent_inpatient": 0}

    ed_count = int(
        (
            (service_dates >= reference - pd.Timedelta(days=int(thresholds["ed_window_days"])))
            & rows["service_type"].eq("Emergency Department")
        ).sum()
    )
    inpatient_count = int(
        (
            (
                service_dates
                >= reference - pd.Timedelta(days=int(thresholds["inpatient_window_days"]))
            )
            & rows["service_type"].eq("Inpatient Admission")
        ).sum()
    )
    return {
        "available": True,
        "recent_ed": ed_count,
        "recent_inpatient": inpatient_count,
        "ed_flagged": ed_count >= int(thresholds["ed_min_visits"]),
        "inpatient_flagged": inpatient_count >= int(thresholds["inpatient_min_admissions"]),
    }


def build_evidence(
    member_id: str, claims: pd.DataFrame, policy: dict[str, Any]
) -> list[dict[str, Any]]:
    result = assess(member_id, claims, policy)
    thresholds = policy["threshold_policies"]["utilization"]
    items: list[dict[str, Any]] = []

    if result.get("ed_flagged"):
        evidence_id = str(thresholds["ed_evidence_id"])
        meta = evidence_meta(policy, evidence_id)
        items.append(
            {
                "evidence_id": evidence_id,
                "domain": meta["domain"],
                "signal": meta["name"],
                "value": str(result["recent_ed"]),
                "unit": str(thresholds["ed_unit"]),
                "status": "flagged",
                "interpretation": meta["description"],
            }
        )

    if result.get("inpatient_flagged"):
        evidence_id = str(thresholds["inpatient_evidence_id"])
        meta = evidence_meta(policy, evidence_id)
        items.append(
            {
                "evidence_id": evidence_id,
                "domain": meta["domain"],
                "signal": meta["name"],
                "value": str(result["recent_inpatient"]),
                "unit": str(thresholds["inpatient_unit"]),
                "status": "flagged",
                "interpretation": meta["description"],
            }
        )

    return items
