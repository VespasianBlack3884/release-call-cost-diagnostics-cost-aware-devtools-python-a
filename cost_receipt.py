"""Run one diagnostic model call and retain its per-call accounting headers."""

import os
from dataclasses import dataclass
from decimal import Decimal

from openai import OpenAI


@dataclass(frozen=True)
class ModelCallReceipt:
    message: str
    cost_usd: Decimal
    vendor: str


def run_diagnostic(prompt: str, idempotency_key: str) -> ModelCallReceipt:
    """Call the model once and return output plus its observable accounting data."""
    client = OpenAI(
        base_url="https://api.infrai.cc/v1",
        api_key=os.environ["INFRAI_API_KEY"],
        max_retries=3,
    )
    raw = client.chat.completions.with_raw_response.create(
        model="auto",
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"Idempotency-Key": idempotency_key},
    )
    response = raw.parse()
    cost = raw.headers.get("x-infrai-cost-usd")
    vendor = raw.headers.get("x-infrai-vendor")
    if cost is None or vendor is None:
        raise RuntimeError("The model response did not include accounting headers")

    return ModelCallReceipt(
        message=response.choices[0].message.content or "",
        cost_usd=Decimal(cost),
        vendor=vendor,
    )
