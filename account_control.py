"""Small Infrai control-plane client for the account spend ceiling."""

from __future__ import annotations

import time
from typing import Any

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(f"{code} (HTTP {status_code})")
        self.code = code
        self.detail = detail
        self.status_code = status_code


def set_budget(
    *,
    api_key: str,
    base_url: str,
    hard_cap_usd: float,
    period: str,
    idempotency_key: str,
    alert_threshold_usd: float | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "hard_cap_usd": hard_cap_usd,
        "period": period,
        "idempotency_key": idempotency_key,
    }
    if alert_threshold_usd is not None:
        body["alert_threshold_usd"] = alert_threshold_usd

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15.0) as client:
        for attempt in range(4):
            response = client.request(
                method="PUT",
                url=f"{base_url}/account/budget/set",
                headers=headers,
                json=body,
            )
            try:
                envelope = response.json()
            except ValueError:
                if response.status_code >= 500:
                    response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    str(detail.get("code", "unknown")),
                    detail,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
    raise RuntimeError("Infrai retry limit reached")
