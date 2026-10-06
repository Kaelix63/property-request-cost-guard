"""Set the account ceiling used by the property workflow."""

import os

from account_control import set_budget
from property_workflow import BASE_URL


def main() -> None:
    result = set_budget(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url=BASE_URL,
        hard_cap_usd=float(os.environ.get("INFRAI_HARD_CAP_USD", "25")),
        alert_threshold_usd=float(os.environ.get("INFRAI_ALERT_USD", "20")),
        period=os.environ.get("INFRAI_BUDGET_PERIOD", "monthly"),
        idempotency_key=os.environ.get(
            "INFRAI_BUDGET_IDEMPOTENCY_KEY", "property-service-monthly-budget"
        ),
    )
    print("Account ceiling configured:", result)


if __name__ == "__main__":
    main()
