"""Developer-facing release diagnostic service."""

from decimal import Decimal
from typing import Literal

from fastapi import FastAPI, HTTPException
from openai import APIStatusError
from pydantic import BaseModel, Field

from cost_receipt import ModelCallReceipt, run_diagnostic


class BuildEvent(BaseModel):
    build_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    failed_checks: list[str] = Field(default_factory=list)


class ReleaseOperation(BaseModel):
    release_id: str = Field(min_length=1)
    environment: Literal["staging", "production"]
    diagnostic_budget_usd: Decimal = Field(gt=0)


class DiagnosticRequest(BaseModel):
    build: BuildEvent
    release: ReleaseOperation


class DiagnosticResult(BaseModel):
    release_id: str
    decision: Literal["continue", "review"]
    reason: str
    model_message: str
    model_cost_usd: Decimal
    model_vendor: str


def decide_release(
    request: DiagnosticRequest, receipt: ModelCallReceipt
) -> DiagnosticResult:
    """Make the spend boundary visible in the release workflow."""
    within_budget = receipt.cost_usd <= request.release.diagnostic_budget_usd
    decision: Literal["continue", "review"] = "continue" if within_budget else "review"
    reason = (
        "diagnostic call is within the release budget"
        if within_budget
        else "diagnostic call exceeded the release budget"
    )
    return DiagnosticResult(
        release_id=request.release.release_id,
        decision=decision,
        reason=reason,
        model_message=receipt.message,
        model_cost_usd=receipt.cost_usd,
        model_vendor=receipt.vendor,
    )


app = FastAPI(title="Release cost diagnostics")


@app.post("/release/diagnostics", response_model=DiagnosticResult)
def diagnose_release(request: DiagnosticRequest) -> DiagnosticResult:
    failed = ", ".join(request.build.failed_checks) or "none"
    prompt = (
        "Summarize this build for a release engineer in two sentences. "
        f"Build {request.build.build_id} on branch {request.build.branch}; "
        f"failed checks: {failed}."
    )
    try:
        receipt = run_diagnostic(prompt, request.release.release_id)
    except APIStatusError as exc:
        if 400 <= exc.status_code < 500:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        raise
    return decide_release(request, receipt)
