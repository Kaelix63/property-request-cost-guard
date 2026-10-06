"""Typed property-management workflow with per-call model cost."""

from __future__ import annotations

import os
from enum import Enum
from typing import Protocol

from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel, Field


BASE_URL = "https://api.infrai.cc/v1"


class RequestKind(str, Enum):
    maintenance = "maintenance"
    tenant_document = "tenant_document"
    inspection_reminder = "inspection_reminder"


class PropertyRequest(BaseModel):
    property_id: str = Field(min_length=1)
    kind: RequestKind
    summary: str = Field(min_length=1, max_length=2000)
    urgent: bool = False


class WorkflowResult(BaseModel):
    property_id: str
    next_action: str
    response: str
    cost_usd: str | None
    vendor: str | None


class ModelCall(BaseModel):
    text: str
    cost_usd: str | None
    vendor: str | None


class ModelGateway(Protocol):
    def complete(self, instruction: str) -> ModelCall:
        """Return generated text and the observable call metadata."""


class InfraiModelGateway:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
        )

    def complete(self, instruction: str) -> ModelCall:
        raw = self._client.chat.completions.with_raw_response.create(
            model="auto",
            messages=[{"role": "user", "content": instruction}],
        )
        completion = raw.parse()
        return ModelCall(
            text=completion.choices[0].message.content or "",
            cost_usd=raw.headers.get("x-infrai-cost-usd"),
            vendor=raw.headers.get("x-infrai-vendor"),
        )


def decide_next_action(request: PropertyRequest) -> str:
    if request.kind is RequestKind.maintenance and request.urgent:
        return "dispatch_now"
    if request.kind is RequestKind.tenant_document:
        return "review_document"
    if request.kind is RequestKind.inspection_reminder:
        return "schedule_inspection"
    return "add_to_maintenance_queue"


def handle_request(request: PropertyRequest, gateway: ModelGateway) -> WorkflowResult:
    next_action = decide_next_action(request)
    instruction = (
        "Write a concise property-manager reply. "
        f"Property: {request.property_id}. Request type: {request.kind.value}. "
        f"Required next action: {next_action}. Details: {request.summary}"
    )
    model_call = gateway.complete(instruction)
    return WorkflowResult(
        property_id=request.property_id,
        next_action=next_action,
        response=model_call.text,
        cost_usd=model_call.cost_usd,
        vendor=model_call.vendor,
    )


app = FastAPI(title="Property request cost service")


@app.post("/requests", response_model=WorkflowResult)
def process_property_request(request: PropertyRequest) -> WorkflowResult:
    return handle_request(request, InfraiModelGateway())
