from __future__ import annotations

import re
import threading
from pathlib import Path

import pandas as pd

from careops.contracts.decisions import CareOpsDecisionContract
from careops.contracts.runs import RunFrames, empty_frames, frames_from_contract, normalize

_LOCK = threading.RLock()
_SAFE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


class RunStore:
    """Stores every agent's runs separately.

    Layout::

        data/runs/<agent_key>/runs.parquet
        data/runs/<agent_key>/findings.parquet
        data/runs/<agent_key>/actions.parquet

    Each agent owns its own folder. Stored results are never used as *input* to a new run;
    they are only retrieved (to show an existing result) or reviewed. Single-process, file-backed
    storage is sufficient for the POC; a database would replace this class unchanged.
    """

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "runs"

    # ------------------------------------------------------------------ write
    def save(self, contract: CareOpsDecisionContract) -> None:
        agent_dir = self._agent_dir(contract.execution.agent_key)
        frames = frames_from_contract(contract)
        with _LOCK:
            agent_dir.mkdir(parents=True, exist_ok=True)
            for table, fresh in frames.items():
                path = agent_dir / f"{table}.parquet"
                if path.exists():
                    fresh = pd.concat([pd.read_parquet(path), fresh], ignore_index=True)
                temp = path.with_suffix(".tmp")
                normalize(table, fresh).to_parquet(temp, index=False)
                temp.replace(path)

    # ------------------------------------------------------------------- read
    def get(self, run_id: str) -> CareOpsDecisionContract | None:
        for agent_dir in self._agent_dirs():
            path = agent_dir / "runs.parquet"
            if not path.exists():
                continue
            match = pd.read_parquet(
                path,
                columns=["run_id", "contract_json"],
                filters=[("run_id", "==", run_id)],
            )
            if not match.empty:
                return CareOpsDecisionContract.model_validate_json(match.iloc[0]["contract_json"])
        return None

    def find_reusable(
        self,
        agent_key: str,
        scope: str,
        member_id: str,
        context_fingerprint: str,
        policy_fingerprint: str,
    ) -> CareOpsDecisionContract | None:
        """Newest saved run for this member + review whose inputs are unchanged.

        A stored result is only reusable if the member's data and the policy still hash to the
        same fingerprints it was produced from, and it was not withheld by validation.
        """
        path = self._agent_dir(agent_key) / "runs.parquet"
        if not path.exists():
            return None
        with _LOCK:
            rows = pd.read_parquet(
                path,
                columns=[
                    "scope",
                    "member_id",
                    "status",
                    "context_fingerprint",
                    "policy_fingerprint",
                    "created_at",
                    "contract_json",
                ],
            )
        rows = rows.loc[
            rows["scope"].astype(str).eq(scope)
            & rows["member_id"].astype(str).eq(str(member_id))
            & rows["context_fingerprint"].astype(str).eq(context_fingerprint)
            & rows["policy_fingerprint"].astype(str).eq(policy_fingerprint)
            & rows["status"].astype(str).ne("BLOCKED")
        ]
        if rows.empty:
            return None
        newest = rows.sort_values("created_at", ascending=False).iloc[0]
        return CareOpsDecisionContract.model_validate_json(newest["contract_json"])

    def frames(self, agent_key: str | None = None) -> RunFrames:
        """All stored runs as typed DataFrames, newest first. Optionally one agent only."""
        dirs = [self._agent_dir(agent_key)] if agent_key else self._agent_dirs()
        parts: dict[str, list[pd.DataFrame]] = {"runs": [], "findings": [], "actions": []}
        for agent_dir in dirs:
            for table in parts:
                path = agent_dir / f"{table}.parquet"
                if path.exists():
                    parts[table].append(pd.read_parquet(path))
        if not any(parts.values()):
            return empty_frames()

        def combine(table: str) -> pd.DataFrame:
            frame = normalize(table, pd.concat(parts[table], ignore_index=True))
            return frame.sort_values("created_at", ascending=False, ignore_index=True)

        return RunFrames(
            runs=combine("runs"), findings=combine("findings"), actions=combine("actions")
        )

    # ---------------------------------------------------------------- helpers
    def _agent_dir(self, agent_key: str) -> Path:
        if not _SAFE_KEY.match(agent_key):
            raise ValueError(f"Invalid agent key: {agent_key!r}")
        return self.root / agent_key

    def _agent_dirs(self) -> list[Path]:
        if not self.root.exists():
            return []
        return sorted(path for path in self.root.iterdir() if path.is_dir())
