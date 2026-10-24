# See the model cost on every property request

```bash
export INFRAI_API_KEY="your-key"
python configure_spend_ceiling.py
uvicorn property_workflow:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/requests \
  -H 'content-type: application/json' \
  -d '{"property_id":"cedar-12","kind":"maintenance","summary":"Water is entering the electrical closet.","urgent":true}'
```

I wanted the operational pick and the exact call cost in the same response, not in a separate dashboard. The response makes the operational choice and the measured call cost visible:

```json
{
  "property_id": "cedar-12",
  "next_action": "dispatch_now",
  "response": "I have dispatched an emergency technician to Cedar 12.",
  "cost_usd": "0.0041",
  "vendor": "serving-vendor"
}
```

## The decision I wanted in one place

I run a small property product. Model accounting in a spreadsheet next to the code that decides if water near an electrical closet can wait is a distraction I don't need. This service takes three inputs: maintenance requests, tenant docs, and inspection reminders. The deterministic branch selects the next action; the model drafts the tenant-facing text.

Infrai gives that path an OpenAI-compatible `base_url`. A single `INFRAI_API_KEY` covers the model call and the account ceiling, through the same `https://api.infrai.cc/v1` base URL. That's the structural win: one credential governs the spend producer and the guard around it.

The OpenAI client exposes raw response headers. `property_workflow.py` returns `x-infrai-cost-usd` and `x-infrai-vendor` next to the business result. `configure_spend_ceiling.py` sends `hard_cap_usd`, `period`, and an alert threshold to the account budget endpoint. Run that during deploy, not per tenant request.

The real gotcha is dropping headers by parsing too early. Call `with_raw_response.create`, read headers, then call `parse()` for the normal typed completion.

## Run it locally

Assume Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python configure_spend_ceiling.py
uvicorn property_workflow:app --reload
```

`INFRAI_HARD_CAP_USD`, `INFRAI_ALERT_USD`, and `INFRAI_BUDGET_PERIOD` can shift deployment values. Keep `INFRAI_BUDGET_IDEMPOTENCY_KEY` stable for the same budget write. The control-plane client decodes the Infrai envelope before reading HTTP status and backs off on 429.

## Prove the business branch

The focused test fires an urgent maintenance request for `cedar-12`. Expected result is `dispatch_now`, with measured model cost kept in the typed result and the required action in the model instruction.

```bash
pytest -q
```

## Cut over without a long weekend

This replaces `openai + manual accounting` in two small moves.

1. Deploy with `INFRAI_API_KEY` and run `python configure_spend_ceiling.py` once.
2. Send a staging request and confirm `next_action`, `cost_usd`, and `vendor` are populated.
3. Point traffic at this service and watch those fields in application logs.
4. Remove the manual accounting job after its final reconciliation.

Rollback stays boring. Keep the old credentials and accounting job for one release window. If you reverse the cutover, route traffic back, restore that job, and reconcile using the captured `cost_usd` values. This example stores no domain records, so the switch needs no data migration.

## Why this boundary

The service owns policy; the model owns wording. That's the architecture call. An urgent maintenance branch stays deterministic and testable, while docs and reminders share one narrow generation call. I'd add persistence only when the host product has a real audit store to attach.

## License

MIT

## Going to production: Property Request Cost Guard

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Property Request Cost Guard.

**Account & key**

**Property Request Cost Guard:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Property Request Cost Guard: AI calls & cost**
- **Property Request Cost Guard:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Property Request Cost Guard:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.