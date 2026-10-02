from __future__ import annotations

from typing import Literal

from pydantic import Field

from careops.contracts.base import EvidenceId, FrozenModel

FindingStatus = Literal["flagged", "informational"]


class EvidenceItem(FrozenModel):
    """One deterministic finding. The catalog defines its meaning; this carries the value."""

    evidence_id: EvidenceId
    domain: str = Field(min_length=1, max_length=40)
    signal: str = Field(min_length=1, max_length=180)
    value: str = Field(min_length=1, max_length=500)
    unit: str | None = None
    status: FindingStatus
    interpretation: str = Field(min_length=1, max_length=500)
