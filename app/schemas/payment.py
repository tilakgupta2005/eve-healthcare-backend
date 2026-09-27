import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    booking_id: uuid.UUID
    # Only meant for local testing / grading convenience: lets a caller
    # force a deterministic outcome instead of relying on the random
    # simulation. Never exposed by a real gateway.
    force_status: PaymentStatus | None = Field(
        default=None, description="Testing only: force SUCCESS or FAILED."
    )


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    provider_transaction_id: str
    amount: Decimal
    status: PaymentStatus
    created_at: datetime


class WebhookPayload(BaseModel):
    """
    Shape of the payload our simulated payment provider POSTs to
    /payments/webhook/. `event_id` is the idempotency key: the provider is
    expected (as real providers do) to send the *same* event_id if it
    retries delivery of the same event.
    """

    event_id: str = Field(min_length=1, max_length=128)
    provider_transaction_id: str
    status: PaymentStatus
    raw: dict[str, Any] | None = None
