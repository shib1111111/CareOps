"""Shared Pydantic foundations for every CareOps contract."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

# Stable business identifier for a finding, e.g. CLN-001, GAP-002, UTL-001.
EvidenceId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}-\d{3}$"),
]


class ContractModel(BaseModel):
    """Strict by default: unknown fields are rejected and text is trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FrozenModel(ContractModel):
    """Immutable contract. Used for anything that is persisted or audited."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
