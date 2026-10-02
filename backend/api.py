from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

_ROOT = Path(__file__).resolve().parents[1]
for _path in (_ROOT, _ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from fastapi import FastAPI, HTTPException, Request, Response  # noqa: E402

from backend.schemas import CreateAssessmentRequest  # noqa: E402
from careops.application.service import CareOpsService  # noqa: E402
from careops.contracts.api import AssessmentResponse, build_api_response  # noqa: E402

API_ROOT = "/api/v1"

app = FastAPI(
    title="CareOps Decision API",
    description="Business-facing API for creating and retrieving member assessments.",
)
service = CareOpsService()


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or f"req-{uuid4().hex[:12]}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "careops"}


@app.get("/ready")
def readiness() -> dict[str, str]:
    try:
        service.population()
        service.rules()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="CareOps is not ready.") from exc
    return {"status": "ready", "service": "careops"}


@app.post(f"{API_ROOT}/assessments", response_model=AssessmentResponse)
def create_assessment(
    body: CreateAssessmentRequest,
    request: Request,
    response: Response,
) -> AssessmentResponse:
    try:
        contract, _reused = service.assess(
            body.member.id,
            scope=body.assessment.type,
            instruction=body.options.instruction,
            fresh=body.options.fresh,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail="The assessment could not be completed."
        ) from exc

    response.headers["X-Request-ID"] = request.state.request_id
    return build_api_response(contract)


@app.get(f"{API_ROOT}/assessments/{{assessment_id}}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: str,
    request: Request,
    response: Response,
) -> AssessmentResponse:
    contract = service.get_saved_decision(assessment_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    response.headers["X-Request-ID"] = request.state.request_id
    return build_api_response(contract)
