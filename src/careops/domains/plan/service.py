from __future__ import annotations

from typing import Any

import pandas as pd


def assess(member_id: str, enrollment: pd.DataFrame) -> dict[str, Any]:
    if enrollment.empty:
        return {"available": False}
    rows = enrollment.loc[enrollment["patient_id"].astype(str).eq(str(member_id))]
    if rows.empty:
        return {"available": False}
    row = rows.iloc[0]
    return {
        "available": True,
        "plan_name": str(row.get("plan_name", "")),
        "product_type": str(row.get("product_type", "")),
        "coverage_status": str(row.get("coverage_status", "")),
        "benefit_variant": str(row.get("benefit_variant", "")),
        "csnp_enrolled": str(row.get("csnp_enrolled", "")),
    }
