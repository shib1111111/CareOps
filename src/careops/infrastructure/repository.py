from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from careops.contracts.config import PolicyConfig
from careops.contracts.data import (
    CLAIM_COLUMNS,
    CLAIM_DATE_COLUMNS,
    CLAIM_NUMERIC_COLUMNS,
    DATE_COLUMNS,
    ENROLLMENT_COLUMNS,
    NUMERIC_COLUMNS,
    PATIENT_COLUMNS,
)


class DataRepository:
    """Fresh file-backed adapters for the POC; business policy is owned by JSON."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def patients(self) -> pd.DataFrame:
        df = self._read_required("patients.csv")
        missing = set(PATIENT_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"patients.csv is missing columns: {sorted(missing)}")
        df = df[PATIENT_COLUMNS].copy()
        for col in DATE_COLUMNS:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        for col in NUMERIC_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def claims(self) -> pd.DataFrame:
        path = self.data_dir / "claims.csv"
        if not path.exists():
            return pd.DataFrame(columns=CLAIM_COLUMNS)
        df = pd.read_csv(path)
        missing = set(CLAIM_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"claims.csv is missing columns: {sorted(missing)}")
        df = df[CLAIM_COLUMNS].copy()
        for col in CLAIM_DATE_COLUMNS:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        for col in CLAIM_NUMERIC_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def enrollment(self) -> pd.DataFrame:
        path = self.data_dir / "member_enrollment.csv"
        if not path.exists():
            return pd.DataFrame(columns=ENROLLMENT_COLUMNS)
        df = pd.read_csv(path, dtype=str).fillna("")
        missing = set(ENROLLMENT_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"member_enrollment.csv is missing columns: {sorted(missing)}")
        return df[ENROLLMENT_COLUMNS].copy()

    def rules(self) -> dict[str, Any]:
        path = self.data_dir / "careops_policy.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return self.validate_policy(raw).model_dump(mode="json")

    def save_rules(self, rules: dict[str, Any]) -> None:
        validated = self.validate_policy(rules)
        path = self.data_dir / "careops_policy.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(validated.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(path)

    def reset_rules(self) -> None:
        source = self.data_dir / "careops_policy.example.json"
        self.save_rules(json.loads(source.read_text(encoding="utf-8")))

    @staticmethod
    def validate_policy(rules: dict[str, Any]) -> PolicyConfig:
        validated = PolicyConfig.model_validate(rules)
        evidence_ids = set(validated.evidence_catalog)
        tool_names = set(validated.tools)

        for scope_name, scope in validated.scopes.items():
            if scope.agent not in validated.agents:
                raise ValueError(f"Scope '{scope_name}' references unknown agent '{scope.agent}'.")
            missing_tools = set(scope.tools) - tool_names
            if missing_tools:
                raise ValueError(
                    f"Scope '{scope_name}' references unknown tools: {sorted(missing_tools)}"
                )
            missing_audiences = set(scope.handoffs) - set(validated.audiences)
            if missing_audiences:
                raise ValueError(
                    f"Scope '{scope_name}' references unknown audiences: {sorted(missing_audiences)}"
                )

        for pattern_name, pattern in validated.decision_patterns.items():
            referenced = (
                set(pattern.required_all) | set(pattern.required_any) | set(pattern.also_any)
            )
            unknown = referenced - evidence_ids
            if unknown:
                raise ValueError(
                    f"Pattern '{pattern_name}' references unknown evidence IDs: {sorted(unknown)}"
                )

        for tool_name, dependencies in validated.tool_dependencies.items():
            if tool_name not in tool_names:
                raise ValueError(f"Dependency map references unknown tool '{tool_name}'.")
            unknown = set(dependencies) - tool_names
            if unknown:
                raise ValueError(f"Tool '{tool_name}' has unknown dependencies: {sorted(unknown)}")

        threshold_data = validated.threshold_policies.model_dump(mode="json")
        for rule_name, rule in threshold_data["labs"].items():
            if rule["evidence_id"] not in evidence_ids:
                raise ValueError(
                    f"Lab rule '{rule_name}' references unknown evidence ID '{rule['evidence_id']}'."
                )

        referenced_threshold_ids = {
            threshold_data["vitals"]["evidence_id"],
            threshold_data["care_gaps"]["overdue_evidence_id"],
            threshold_data["care_gaps"]["missed_evidence_id"],
            threshold_data["utilization"]["ed_evidence_id"],
            threshold_data["utilization"]["inpatient_evidence_id"],
        }
        unknown_threshold_ids = referenced_threshold_ids - evidence_ids
        if unknown_threshold_ids:
            raise ValueError(
                f"Threshold policy references unknown evidence IDs: {sorted(unknown_threshold_ids)}"
            )

        known_workflows = {
            "clinical_followup",
            "care_gap_outreach",
            "utilization_review",
            "navigation_review",
        }
        for pattern_name, pattern in validated.decision_patterns.items():
            unknown = set(pattern.workflows) - known_workflows
            if unknown:
                raise ValueError(
                    f"Pattern '{pattern_name}' references unknown workflows: {sorted(unknown)}"
                )

        return validated

    def member_record(self, member_id: str) -> dict[str, Any]:
        df = self.patients()
        rows = df.loc[df.patient_id.astype(str).eq(str(member_id))]
        if rows.empty:
            raise KeyError(f"Member {member_id} was not found.")
        row = rows.iloc[0].copy()
        for key in DATE_COLUMNS:
            if pd.notna(row[key]):
                row[key] = pd.Timestamp(row[key]).strftime("%Y-%m-%d")
        return row.to_dict()

    def member_fingerprint(
        self,
        member_id: str,
        patient: dict[str, Any],
        claims: pd.DataFrame,
        enrollment: pd.DataFrame,
    ) -> str:
        claim_rows = claims.loc[claims["patient_id"].astype(str).eq(str(member_id))]
        enrollment_rows = enrollment.loc[enrollment["patient_id"].astype(str).eq(str(member_id))]
        normalized = {
            "patient": patient,
            "claims": claim_rows.fillna("").astype(str).to_dict(orient="records"),
            "enrollment": enrollment_rows.fillna("").astype(str).to_dict(orient="records"),
        }
        return hashlib.sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()[:20]

    @staticmethod
    def rules_hash(rules: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(rules, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()[:16]

    def _read_required(self, filename: str) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / filename)
