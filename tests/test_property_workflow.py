from property_workflow import ModelCall, PropertyRequest, RequestKind, handle_request


class RecordingGateway:
    def __init__(self) -> None:
        self.instruction = ""

    def complete(self, instruction: str) -> ModelCall:
        self.instruction = instruction
        return ModelCall(text="Technician dispatch recorded.", cost_usd="0.0041", vendor="demo")


def test_urgent_maintenance_is_dispatched_and_cost_is_visible() -> None:
    gateway = RecordingGateway()
    request = PropertyRequest(
        property_id="cedar-12",
        kind=RequestKind.maintenance,
        summary="Water is entering the electrical closet.",
        urgent=True,
    )

    result = handle_request(request, gateway)

    assert result.next_action == "dispatch_now"
    assert result.cost_usd == "0.0041"
    assert "Required next action: dispatch_now" in gateway.instruction
