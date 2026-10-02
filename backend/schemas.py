from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssessmentType = Literal["overall", "clinical", "care_gap", "utilization", "navigation"]


class MemberReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100, description="Member identifier.")


class AssessmentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AssessmentType = Field(
        default="overall", description="Overall or focused assessment type."
    )


class AssessmentOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(default="", max_length=700, description="Optional operator focus.")
    fresh: bool = Field(
        default=False,
        description="Force a new run. By default an existing valid saved result is returned.",
    )


class CreateAssessmentRequest(BaseModel):
    """Small public request contract; runtime mechanics remain private."""

    model_config = ConfigDict(extra="forbid")

    member: MemberReference
    assessment: AssessmentSelection = Field(default_factory=AssessmentSelection)
    options: AssessmentOptions = Field(default_factory=AssessmentOptions)
