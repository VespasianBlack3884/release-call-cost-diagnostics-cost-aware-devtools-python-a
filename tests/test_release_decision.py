from decimal import Decimal

from cost_receipt import ModelCallReceipt
from release_diagnostics import (
    BuildEvent,
    DiagnosticRequest,
    ReleaseOperation,
    decide_release,
)


def test_release_moves_to_review_when_diagnostic_exceeds_budget() -> None:
    request = DiagnosticRequest(
        build=BuildEvent(
            build_id="build-1842",
            branch="release/2.4",
            failed_checks=["integration-linux"],
        ),
        release=ReleaseOperation(
            release_id="release-2.4.0",
            environment="production",
            diagnostic_budget_usd=Decimal("0.010"),
        ),
    )
    receipt = ModelCallReceipt(
        message="The Linux integration check needs review.",
        cost_usd=Decimal("0.012"),
        vendor="example-vendor",
    )

    result = decide_release(request, receipt)

    assert result.decision == "review"
    assert result.release_id == "release-2.4.0"
    assert result.model_cost_usd == Decimal("0.012")
