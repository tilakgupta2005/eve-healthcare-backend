import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    test_id: uuid.UUID
    centre_id: uuid.UUID
    appointment_time: datetime = Field(
        description="Must be in the future (UTC recommended)."
    )


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    test_id: uuid.UUID
    centre_id: uuid.UUID
    appointment_time: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime
    updated_at: datetime | None = None
