from __future__ import annotations

from typing import Any


def evidence_meta(policy: dict[str, Any], evidence_id: str) -> dict[str, Any]:
    """Stable business definition of an Evidence ID. The policy JSON is the only source."""
    try:
        return dict(policy["evidence_catalog"][evidence_id])
    except KeyError as exc:
        raise ValueError(
            f"Evidence ID '{evidence_id}' is not defined in the evidence catalog."
        ) from exc
