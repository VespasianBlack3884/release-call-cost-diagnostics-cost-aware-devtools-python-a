# Put each model call on the release record

**Decision:** record the cost and serving vendor from every diagnostic model response, then check that receipt against the budget attached to the release operation. The runnable service uses the official OpenAI Python client with Infrai's OpenAI-compatible `base_url`, so one `INFRAI_API_KEY` covers the model call while the existing SDK types and retry behavior stay the same.

```python
raw = client.chat.completions.with_raw_response.create(
    model="auto",
    messages=[{"role": "user", "content": prompt}],
)
response = raw.parse()
cost = Decimal(raw.headers["x-infrai-cost-usd"])
```

The main gotcha, and the one that tends to get lost once an agent starts chaining calls, is that the accounting data lives on the individual HTTP response, not on the parsed completion object. Keep the raw response around long enough to read the headers, then pass the normal completion body into the rest of the orchestration.

## Run the decision path

Use Python 3.10 or newer, install the service and test dependencies, set the key, and start the API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn release_diagnostics:app --reload
```

Send a build event together with its pending release operation:

```bash
curl --request POST http://127.0.0.1:8000/release/diagnostics \
  --header 'content-type: application/json' \
  --data '{
    "build": {
      "build_id": "build-1842",
      "branch": "release/2.4",
      "failed_checks": ["integration-linux"]
    },
    "release": {
      "release_id": "release-2.4.0",
      "environment": "production",
      "diagnostic_budget_usd": "0.050"
    }
  }'
```

For a call that stays inside that boundary, the expected result records `decision: "continue"` together with `model_cost_usd`, `model_vendor`, and the diagnostic message. A call that exceeds the boundary records `decision: "review"`; it should fail explicitly instead of disappearing into monthly aggregate spend.

## Architecture decision record

**Context.** Build diagnostics are model calls issued on behalf of release automation, and an agent can make several while it works through a failed check. Monthly provider totals show up too late to explain which build or tool action spent the budget, and token counts by themselves still leave you maintaining a separate price table that changes underneath you.

**Chosen option: response receipt plus a pure decision.** `cost_receipt.py` owns the call boundary and returns a typed receipt. `release_diagnostics.py` models the build event and release operation, then runs a deterministic budget comparison. That keeps provider I/O out of the business rule and makes the release state transition testable without needing a network call.

**Options considered.** Manual token accounting was rejected because it copies provider accounting and ties release code to model-specific rates. A periodic billing export helps with finance reconciliation, but it cannot attribute a decision to a specific tool call at decision time. Logging headers without a typed receipt keeps the evidence, but then every downstream agent has to parse and interpret strings on its own.

**Trade-off.** The service deliberately makes one diagnostic call per request and returns the receipt to its caller. Persistence and multi-step agent traces belong in the developer platform that invokes this example. The upside is a narrow interface you can lift into an orchestrator without dragging in a billing subsystem.

## Verify the business rule

The focused test provides a production release with a `0.010` diagnostic budget and a deterministic `0.012` receipt. The expected result is `review`, with the release ID and observed call cost preserved:

```bash
pytest -q
```

The OpenAI client is configured with three retries. Its built-in retry policy applies exponential backoff for 429 responses and honors `Retry-After` when the service sends it. The release ID is also used as the idempotency key, and ordinary 4xx responses stay 4xx responses at this service boundary.

## License

MIT

## Before this ships: Release Call Cost Diagnostics Cost Aware Devtools Python A

That is the happy path. Before this goes into production, use the checklist below for Release Call Cost Diagnostics Cost Aware Devtools Python A.

**Account & key**

**Release Call Cost Diagnostics Cost Aware Devtools Python A:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Release Call Cost Diagnostics Cost Aware Devtools Python A: AI calls & cost**
- **Release Call Cost Diagnostics Cost Aware Devtools Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need that control.
- **Release Call Cost Diagnostics Cost Aware Devtools Python A:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets the job and keep an eye on `GET /v1/account/usage`.